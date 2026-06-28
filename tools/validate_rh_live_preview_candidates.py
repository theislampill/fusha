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
CONTEXT_SUBJECT_HINTS = {"they", "people", "he", "she", "it", "we"}
CONTEXT_OBJECT_HINTS = {"them", "you", "us", "me", "him", "her"}
TOKEN_SUBJECT_ROLES = {"subject_pronoun"}
TOKEN_OBJECT_ROLES = {"object_pronoun"}


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


def words(text):
    return set(re.findall(r"[A-Za-z]+", str(text or "").lower()))


def has_context_source(row):
    return any((
        row.get("context_subject_source"),
        row.get("context_object_source"),
        row.get("context_governor_source"),
        row.get("context_attachment_source"),
    ))


def has_token_internal_source(row, hints):
    roles = {str(segment.get("role") or "") for segment in row.get("segments") or []}
    if hints & CONTEXT_SUBJECT_HINTS and not roles & TOKEN_SUBJECT_ROLES:
        return False
    if hints & CONTEXT_OBJECT_HINTS and not roles & TOKEN_OBJECT_ROLES:
        return False
    return bool(hints)


def load_fixture_rows(source_fixture):
    rows = []
    fixture_path = os.path.join(ROOT, source_fixture)
    with io.open(fixture_path, encoding="utf-8") as handle:
        for fixture_lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((fixture_lineno, json.loads(line)))
            except Exception as exc:
                rows.append((fixture_lineno, {"__json_error__": str(exc)}))
    return rows


def validate_renderer_fixture_link(row, path, lineno, errors):
    source_fixture = str(row.get("source_renderer_fixture") or "")
    if not source_fixture.startswith("qamus/examples/rich_cert_") or not source_fixture.endswith(".jsonl"):
        _err(errors, path, lineno, "source_renderer_fixture must be a committed rich_cert fixture path")
        return
    fixture_path = os.path.join(ROOT, source_fixture)
    if not os.path.exists(fixture_path):
        _err(errors, path, lineno, "source_renderer_fixture must exist")
        return

    fixture_rows = load_fixture_rows(source_fixture)
    bad_json = [fixture_lineno for fixture_lineno, fixture_row in fixture_rows if "__json_error__" in fixture_row]
    if bad_json:
        _err(errors, path, lineno, "source_renderer_fixture has invalid JSON at lines " + ", ".join(str(n) for n in bad_json))
        return
    quran_loc = row.get("quran_loc")
    wbw_loc = row.get("wbw_loc")
    matches = [
        fixture_row for _fixture_lineno, fixture_row in fixture_rows
        if fixture_row.get("quran_loc") == quran_loc and fixture_row.get("wbw_loc") == wbw_loc
    ]
    if len(matches) != 1:
        _err(errors, path, lineno, "source_renderer_fixture must contain exactly one matching quran/wbw row")
        return

    fixture = matches[0]
    parse_key = fixture.get("parse_key")
    if not isinstance(parse_key, str) or not parse_key.strip():
        _err(errors, path, lineno, "matching renderer fixture row must expose parse_key for tooltip display")
    elif not parse_key.isascii():
        _err(errors, path, lineno, "matching renderer fixture parse_key must be compact ASCII")
    if fixture.get("surface") != row.get("surface"):
        _err(errors, path, lineno, "matching renderer fixture surface must equal preview surface")
    if fixture.get("live_renderer_claim") is not False:
        _err(errors, path, lineno, "matching renderer fixture must not claim live renderer support")
    if fixture.get("renderer_status") != "fixture_not_live":
        _err(errors, path, lineno, "matching renderer fixture status must be fixture_not_live")
    if fixture.get("surface_text_invariant") != "segments_concat_equals_surface":
        _err(errors, path, lineno, "matching renderer fixture must preserve segments_concat_equals_surface")

    fixture_segments = fixture.get("segments") or []
    preview_segments = row.get("segments") or []
    if "".join(str(seg.get("surface") or "") for seg in fixture_segments) != row.get("surface"):
        _err(errors, path, lineno, "matching renderer fixture segment surfaces must concatenate to preview surface")
    if len(fixture_segments) != len(preview_segments):
        _err(errors, path, lineno, "matching renderer fixture segment count must match preview segments")
    else:
        for index, (fixture_segment, preview_segment) in enumerate(zip(fixture_segments, preview_segments)):
            if fixture_segment.get("surface") != preview_segment.get("surface"):
                _err(errors, path, lineno, f"matching renderer fixture segment[{index}].surface must match preview")
            if fixture_segment.get("role") != preview_segment.get("role"):
                _err(errors, path, lineno, f"matching renderer fixture segment[{index}].role must match preview")

    fixture_display = fixture.get("display") or {}
    preview_display = row.get("display") or {}
    if fixture_display.get("palette") != "qamus-grammar-v1":
        _err(errors, path, lineno, "matching renderer fixture display.palette must be qamus-grammar-v1")
    if fixture_display.get("segments") != preview_display.get("segments"):
        _err(errors, path, lineno, "matching renderer fixture display.segments must match preview display.segments")
    leaked = leaks(fixture)
    if leaked:
        _err(errors, path, lineno, "matching renderer fixture leaks forbidden label: " + ", ".join(leaked))


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

    validate_renderer_fixture_link(row, path, lineno, errors)

    public_preview = row.get("public_preview") or {}
    if public_preview.get("src") != "qamus":
        _err(errors, path, lineno, "public_preview.src must be qamus")
    if public_preview.get("kind") != "authored":
        _err(errors, path, lineno, "public_preview.kind must be authored")
    if public_preview.get("lang") != "en":
        _err(errors, path, lineno, "public_preview.lang must be en")
    if not public_preview.get("gloss"):
        _err(errors, path, lineno, "public_preview.gloss is required")
    token_contribution = str(row.get("token_contribution_gloss") or "").strip()
    contextual_gloss = str(row.get("contextual_phrase_gloss") or public_preview.get("gloss") or "").strip()
    if not token_contribution:
        _err(errors, path, lineno, "token_contribution_gloss is required")
    if not contextual_gloss:
        _err(errors, path, lineno, "contextual_phrase_gloss is required")
    if contextual_gloss and public_preview.get("gloss") != contextual_gloss:
        _err(errors, path, lineno, "public_preview.gloss must equal contextual_phrase_gloss")
    context_differs = bool(token_contribution and contextual_gloss and token_contribution != contextual_gloss)
    if context_differs:
        if row.get("adjacent_context_required") is not True:
            _err(errors, path, lineno, "contextual gloss that differs from token contribution requires adjacent_context_required=true")
        locs = row.get("adjacent_context_locs")
        if not isinstance(locs, list) or not locs:
            _err(errors, path, lineno, "contextual gloss that differs from token contribution requires adjacent_context_locs")
        if not row.get("contextual_gloss_certification_state"):
            _err(errors, path, lineno, "contextual gloss that differs from token contribution requires contextual_gloss_certification_state")
        context_sources = [
            row.get("context_subject_source"),
            row.get("context_object_source"),
            row.get("context_governor_source"),
            row.get("context_attachment_source"),
        ]
        if not any(context_sources):
            _err(errors, path, lineno, "contextual gloss that differs from token contribution requires a context_*_source field")
    context_hints = words(contextual_gloss) & (CONTEXT_SUBJECT_HINTS | CONTEXT_OBJECT_HINTS)
    if context_hints and not has_context_source(row) and not has_token_internal_source(row, context_hints):
        _err(errors, path, lineno, "contextual gloss adds subject/object wording without token-internal or adjacent context source")

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
                {"class": "qg-article", "label": "ART", "role": "definite_article", "segment_index": 1},
                {"class": "qg-noun", "label": "STEM", "role": "stem", "segment_index": 2},
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
            {"gloss_contribution": "the", "role": "definite_article", "surface": "ٱل"},
            {"gloss_contribution": "trees", "role": "stem", "surface": "شَّجَرُ"},
        ],
        "service_restart_allowed": False,
        "source_renderer_fixture": "qamus/examples/rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl",
        "surface": "وَٱلشَّجَرُ",
        "surface_text_invariant": "segments_concat_equals_surface",
        "token_contribution_gloss": "and + host",
        "contextual_phrase_gloss": "and + host",
        "adjacent_context_required": False,
        "adjacent_context_locs": [],
        "context_subject_source": None,
        "context_object_source": None,
        "context_governor_source": None,
        "context_attachment_source": None,
        "contextual_gloss_certification_state": "word_level_or_token_internal",
        "wbw_loc": "wbw:22:18:17",
        "wbw_rebuild_allowed": False,
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sample.jsonl")
        dump_jsonl(path, [row])
        count, errors = validate_file(path)
        if errors or count != 1:
            raise SystemExit("self-test failed: " + "; ".join(errors))
        bad = dict(row)
        bad["quran_loc"] = "quran:22:18:18"
        bad["wbw_loc"] = "wbw:22:18:18"
        dump_jsonl(path, [bad])
        count, errors = validate_file(path)
        if not any("source_renderer_fixture must contain exactly one matching quran/wbw row" in error for error in errors):
            raise SystemExit("self-test failed: missing fixture-link failure")
        context_row = dict(row)
        context_row["quran_loc"] = "quran:33:63:1"
        context_row["wbw_loc"] = "wbw:33:63:1"
        context_row["preview_id"] = "rh-live-00-preview:wbw_33_63_1"
        context_row["public_preview"] = {"gloss": "the people ask you", "kind": "authored", "lang": "en", "src": "qamus"}
        context_row["surface"] = "يَسْأَلُكَ"
        context_row["segments"] = [
            {"gloss_contribution": "imperfect marker", "role": "verb_prefix", "surface": "يَ"},
            {"gloss_contribution": "ask", "role": "stem", "surface": "سْأَلُ"},
            {"gloss_contribution": "you", "role": "object_pronoun", "surface": "كَ"},
        ]
        context_row["display"] = {
            "palette": "qamus-grammar-v1",
            "segments": [
                {"class": "qg-verb", "label": "PFX", "role": "verb_prefix", "segment_index": 0},
                {"class": "qg-verb", "label": "STEM", "role": "stem", "segment_index": 1},
                {"class": "qg-pronoun", "label": "PRON", "role": "object_pronoun", "segment_index": 2},
            ],
        }
        context_row["source_renderer_fixture"] = "qamus/examples/rich_cert_vn_rich_cert_00_renderer_fixture.sample.jsonl"
        context_row["token_contribution_gloss"] = "ask you"
        context_row["contextual_phrase_gloss"] = "the people ask you"
        context_row["adjacent_context_required"] = True
        context_row["adjacent_context_locs"] = ["quran:33:63:2", "wbw:33:63:2"]
        context_row["context_subject_source"] = "النَّاسُ at quran:33:63:2 / wbw:33:63:2"
        context_row["context_object_source"] = "suffix كَ at quran:33:63:1 / wbw:33:63:1"
        context_row["contextual_gloss_certification_state"] = "certified_not_applied_context_supported"
        dump_jsonl(path, [context_row])
        count, errors = validate_file(path)
        if errors or count != 1:
            raise SystemExit("self-test failed: context row rejected: " + "; ".join(errors))
        bad_context = dict(context_row)
        bad_context["adjacent_context_locs"] = []
        dump_jsonl(path, [bad_context])
        count, errors = validate_file(path)
        if not any("requires adjacent_context_locs" in error for error in errors):
            raise SystemExit("self-test failed: missing adjacent context locs regression was not caught")
        hidden_context = dict(context_row)
        hidden_context["token_contribution_gloss"] = "the people ask you"
        hidden_context["contextual_phrase_gloss"] = "the people ask you"
        hidden_context["public_preview"] = {"gloss": "the people ask you", "kind": "authored", "lang": "en", "src": "qamus"}
        hidden_context["adjacent_context_required"] = False
        hidden_context["adjacent_context_locs"] = []
        hidden_context["context_subject_source"] = None
        hidden_context["context_object_source"] = None
        dump_jsonl(path, [hidden_context])
        count, errors = validate_file(path)
        if not any("without token-internal or adjacent context source" in error for error in errors):
            raise SystemExit("self-test failed: unsupported contextual subject regression was not caught")
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
