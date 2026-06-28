#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate RH-LIVE-00 admin/renderer preview candidate rows.

This is a repo-only guard for preview planning. It deliberately does not inspect
or mutate the live Qamus app, WBW lookup, service state, or hover ledger.
"""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
FORBIDDEN_PUBLIC_LABELS = (
    "informed_by",
    "mcp",
    "qac",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
)
FALSE_POLICY_FIELDS = (
    "public_exposable",
    "live_mutation_allowed",
    "wbw_rebuild_allowed",
    "service_restart_allowed",
    "mirror_sync_allowed",
    "hover_ledger_mutation_allowed",
    "may_apply_live",
    "public_rollout_allowed",
    "live_renderer_claim",
)
REQUIRED_DOM_ASSERTIONS = {
    "token_text_content_equals_surface",
    "atomic_arabic_word_no_inserted_spaces",
    "no_segment_layout_gap_inside_token",
    "visible_role_coloring_present",
    "tooltip_parse_key_present",
    "tooltip_segment_rows_present",
    "no_public_provenance_leak",
}


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                yield lineno, json.loads(line)


def dump_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _err(errors, path, lineno, msg):
    errors.append(f"{path}:{lineno}: {msg}")


def leaks(row):
    blob = json.dumps(row, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in blob]


def validate_row(row, path, lineno, errors):
    if row.get("preview_stage") != "RH-LIVE-00":
        _err(errors, path, lineno, "preview_stage must be RH-LIVE-00")
    if row.get("preview_status") != "admin_renderer_preview_candidate":
        _err(errors, path, lineno, "preview_status must be admin_renderer_preview_candidate")
    if row.get("admin_only") is not True or row.get("read_only") is not True:
        _err(errors, path, lineno, "row must be admin_only and read_only")
    if row.get("owner_authorization_required") is not True:
        _err(errors, path, lineno, "owner_authorization_required must be true")
    for field in FALSE_POLICY_FIELDS:
        if row.get(field) is not False:
            _err(errors, path, lineno, f"{field} must be false")

    quran_loc = str(row.get("quran_loc") or "")
    wbw_loc = str(row.get("wbw_loc") or "")
    if not QURAN.match(quran_loc):
        _err(errors, path, lineno, "quran_loc must be quran:S:A:W")
    if not WBW.match(wbw_loc):
        _err(errors, path, lineno, "wbw_loc must be wbw:S:A:W")
    if quran_loc and wbw_loc and wbw_loc != "wbw:" + quran_loc.split(":", 1)[1]:
        _err(errors, path, lineno, "wbw_loc must match quran_loc")

    source_fixture = str(row.get("source_renderer_fixture") or "")
    if not source_fixture.startswith("qamus/examples/rich_cert_") or not source_fixture.endswith(".jsonl"):
        _err(errors, path, lineno, "source_renderer_fixture must be a committed rich_cert fixture path")
    elif not os.path.exists(os.path.join(ROOT, source_fixture)):
        _err(errors, path, lineno, "source_renderer_fixture must exist")

    public_preview = row.get("public_preview") or {}
    if public_preview.get("src") != "qamus":
        _err(errors, path, lineno, "public_preview.src must be qamus")
    if public_preview.get("kind") != "authored":
        _err(errors, path, lineno, "public_preview.kind must be authored")
    if public_preview.get("lang") != "en":
        _err(errors, path, lineno, "public_preview.lang must be en")
    if not public_preview.get("gloss"):
        _err(errors, path, lineno, "public_preview.gloss is required")

    surface = row.get("surface")
    segments = row.get("segments") or []
    if not isinstance(surface, str) or not surface:
        _err(errors, path, lineno, "surface must be non-empty string")
    if not isinstance(segments, list) or not segments:
        _err(errors, path, lineno, "segments must be non-empty array")
        segments = []
    if "".join(str(seg.get("surface") or "") for seg in segments) != surface:
        _err(errors, path, lineno, "segment surfaces must concatenate exactly to surface")
    if row.get("surface_text_invariant") != "segments_concat_equals_surface":
        _err(errors, path, lineno, "surface_text_invariant must be segments_concat_equals_surface")

    display = row.get("display") or {}
    display_segments = display.get("segments") or []
    if display.get("palette") != "qamus-grammar-v1":
        _err(errors, path, lineno, "display.palette must be qamus-grammar-v1")
    if len(display_segments) != len(segments):
        _err(errors, path, lineno, "display.segments length must match segments")
    for index, seg in enumerate(display_segments):
        if seg.get("segment_index") != index:
            _err(errors, path, lineno, "display.segments indices must be contiguous from 0")
        if not str(seg.get("class") or "").startswith("qg-"):
            _err(errors, path, lineno, "display segment class must start with qg-")

    assertions = set(row.get("required_dom_assertions") or [])
    missing = sorted(REQUIRED_DOM_ASSERTIONS - assertions)
    if missing:
        _err(errors, path, lineno, "required_dom_assertions missing " + ", ".join(missing))

    if row.get("certification_state") not in ("pending", "token_only_override", "preview_only"):
        _err(errors, path, lineno, "certification_state must remain pending/token_only_override/preview_only")
    if row.get("next_gate") not in (
        "owner_authorized_admin_preview",
        "component_only_blocker_resolution",
        "exact_address_two_vote",
        "function_attachment_review",
    ):
        _err(errors, path, lineno, "next_gate is not an allowed RH-LIVE preview gate")

    leaked = leaks(row)
    if leaked:
        _err(errors, path, lineno, "forbidden public/internal label leaked: " + ", ".join(leaked))


def validate_file(path):
    errors = []
    count = 0
    for lineno, row in iter_jsonl(path):
        count += 1
        validate_row(row, path, lineno, errors)
    if count == 0:
        errors.append(f"{path}: no rows")
    return count, errors


def self_test():
    row = {
        "admin_only": True,
        "certification_state": "preview_only",
        "display": {
            "palette": "qamus-grammar-v1",
            "segments": [
                {"class": "qg-particle", "label": "CONJ", "role": "prefix_conjunction", "segment_index": 0},
                {"class": "qg-noun", "label": "STEM", "role": "stem", "segment_index": 1},
            ],
        },
        "hover_ledger_mutation_allowed": False,
        "live_mutation_allowed": False,
        "live_renderer_claim": False,
        "may_apply_live": False,
        "mirror_sync_allowed": False,
        "next_gate": "owner_authorized_admin_preview",
        "owner_authorization_required": True,
        "preview_id": "rh-live-00-preview:test",
        "preview_stage": "RH-LIVE-00",
        "preview_status": "admin_renderer_preview_candidate",
        "public_exposable": False,
        "public_preview": {"gloss": "and + host", "kind": "authored", "lang": "en", "src": "qamus"},
        "public_rollout_allowed": False,
        "quran_loc": "quran:22:18:17",
        "read_only": True,
        "required_dom_assertions": sorted(REQUIRED_DOM_ASSERTIONS),
        "segments": [
            {"gloss_contribution": "and", "role": "prefix_conjunction", "surface": "وَ"},
            {"gloss_contribution": "host", "role": "stem", "surface": "شَّجَرُ"},
        ],
        "service_restart_allowed": False,
        "source_renderer_fixture": "qamus/examples/rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl",
        "surface": "وَشَّجَرُ",
        "surface_text_invariant": "segments_concat_equals_surface",
        "wbw_loc": "wbw:22:18:17",
        "wbw_rebuild_allowed": False,
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sample.jsonl")
        dump_jsonl(path, [row])
        count, errors = validate_file(path)
        if errors or count != 1:
            raise SystemExit("self-test failed: " + "; ".join(errors))
    print("RH-LIVE preview candidate self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.jsonl:
        parser.error("provide at least one JSONL file or --self-test")
    total = 0
    errors = []
    for path in args.jsonl:
        count, file_errors = validate_file(path)
        total += count
        errors.extend(file_errors)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"RH-LIVE preview candidates OK - {total} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
