#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate repo-only rich-hover certification tranche artifacts.

These rows sit between rich metadata samples and any future owner-gated apply
plan. They must never become live decisions by accident: every row keeps exact
token identity, source-clean public payload fields, explicit gates, and
non-apply policy flags.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable


CERT_STATES = {
    "rich_certified",
    "preview_only",
    "token_only_override",
    "pending",
    "blocked",
    "no_op",
    "renderer_requirement",
}

REQUIRED_CERT_FIELDS = {
    "tranche_id",
    "source_record",
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_gloss",
    "source_decision_state",
    "certification_state",
    "parse_key",
    "segment_roles",
    "public_payload",
    "gates",
    "segment_surface_exact",
    "component_candidates_can_certify",
    "parse_key_primary_identity",
    "may_apply_live",
    "next_action",
}

REQUIRED_GATE_FIELDS = {
    "address",
    "public_boundary",
    "sarf",
    "nahw",
    "learner",
    "source_two_vote",
    "renderer",
    "owner",
}

LEAK_TERMS = (
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


def _load_jsonl(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: row must be an object")
            row["_line"] = lineno
            rows.append(row)
    return rows


def _public_leaks(value: object) -> list[str]:
    text = json.dumps(value, ensure_ascii=False).lower()
    return [term for term in LEAK_TERMS if term in text]


def validate_certification(path: str) -> list[str]:
    errors: list[str] = []
    rows = _load_jsonl(path)
    if not rows:
        return [f"{path}: no certification rows"]

    seen: set[tuple[str, str]] = set()
    state_counts: dict[str, int] = {}
    for row in rows:
        lineno = row.pop("_line")
        missing = REQUIRED_CERT_FIELDS - set(row)
        if missing:
            errors.append(f"{path}:{lineno}: missing fields: {', '.join(sorted(missing))}")
            continue

        pair = (row.get("quran_loc"), row.get("wbw_loc"))
        if pair in seen:
            errors.append(f"{path}:{lineno}: duplicate quran/wbw pair {pair!r}")
        seen.add(pair)

        if not str(row.get("quran_loc") or "").startswith("quran:"):
            errors.append(f"{path}:{lineno}: quran_loc must start with quran:")
        if not str(row.get("wbw_loc") or "").startswith("wbw:"):
            errors.append(f"{path}:{lineno}: wbw_loc must start with wbw:")
        if not isinstance(row.get("segment_roles"), list) or not row["segment_roles"]:
            errors.append(f"{path}:{lineno}: segment_roles must be a nonempty list")

        state = row.get("certification_state")
        state_counts[state] = state_counts.get(state, 0) + 1
        if state not in CERT_STATES:
            errors.append(f"{path}:{lineno}: unknown certification_state {state!r}")

        public = row.get("public_payload") or {}
        if public.get("src") != "qamus":
            errors.append(f"{path}:{lineno}: public_payload.src must be qamus")
        if public.get("kind") != "authored":
            errors.append(f"{path}:{lineno}: public_payload.kind must be authored")
        if public.get("lang") != "en":
            errors.append(f"{path}:{lineno}: public_payload.lang must be en")
        for term in _public_leaks(public):
            errors.append(f"{path}:{lineno}: public payload leaks {term!r}")

        gates = row.get("gates") or {}
        missing_gates = REQUIRED_GATE_FIELDS - set(gates)
        if missing_gates:
            errors.append(f"{path}:{lineno}: missing gates: {', '.join(sorted(missing_gates))}")
        if gates.get("address") != "pass":
            errors.append(f"{path}:{lineno}: address gate must pass")
        if gates.get("public_boundary") != "pass":
            errors.append(f"{path}:{lineno}: public boundary gate must pass")
        if gates.get("owner") != "not_authorized":
            errors.append(f"{path}:{lineno}: owner gate must be not_authorized in repo-only samples")

        if row.get("may_apply_live") is not False:
            errors.append(f"{path}:{lineno}: may_apply_live must be false")
        if row.get("component_candidates_can_certify") is not False:
            errors.append(f"{path}:{lineno}: component candidates must not certify whole tokens")
        if row.get("parse_key_primary_identity") is not False:
            errors.append(f"{path}:{lineno}: parse_key must not be primary identity")
        if row.get("segment_surface_exact") is not True:
            errors.append(f"{path}:{lineno}: segment_surface_exact must be true")

        if state == "rich_certified":
            required_pass = ("sarf", "nahw", "learner", "source_two_vote", "renderer")
            for gate in required_pass:
                if gates.get(gate) != "pass":
                    errors.append(f"{path}:{lineno}: rich_certified requires {gate}=pass")
            if row.get("source_decision_state") in {"pending", "blocked"}:
                errors.append(f"{path}:{lineno}: pending source row cannot be rich_certified")
        elif state in {"preview_only", "pending", "blocked", "renderer_requirement", "token_only_override"}:
            if gates.get("source_two_vote") == "pass" and state == "preview_only":
                errors.append(f"{path}:{lineno}: preview_only should not have completed source_two_vote gate")

    if not any(state in state_counts for state in ("preview_only", "pending", "blocked", "renderer_requirement")):
        errors.append(f"{path}: expected at least one non-certified review state")
    return errors


def validate_evidence(path: str, cert_rows: list[dict] | None = None) -> list[str]:
    errors: list[str] = []
    rows = _load_jsonl(path)
    if not rows:
        return [f"{path}: no evidence rows"]
    cert_pairs = {
        (row.get("quran_loc"), row.get("wbw_loc"))
        for row in cert_rows or []
    }
    for row in rows:
        lineno = row.pop("_line")
        pair = (row.get("quran_loc"), row.get("wbw_loc"))
        if cert_pairs and pair not in cert_pairs:
            errors.append(f"{path}:{lineno}: evidence row has no matching cert row {pair!r}")
        if row.get("public_exposable") is not False:
            errors.append(f"{path}:{lineno}: evidence public_exposable must be false")
        if row.get("public_boundary") != "internal_only":
            errors.append(f"{path}:{lineno}: evidence public_boundary must be internal_only")
        if not row.get("internal_evidence_labels"):
            errors.append(f"{path}:{lineno}: evidence labels must be nonempty")
    return errors


def validate_renderer(path: str, cert_rows: list[dict] | None = None) -> list[str]:
    errors: list[str] = []
    rows = _load_jsonl(path)
    if not rows:
        return [f"{path}: no renderer rows"]
    cert_pairs = {
        (row.get("quran_loc"), row.get("wbw_loc"))
        for row in cert_rows or []
    }
    for row in rows:
        lineno = row.pop("_line")
        pair = (row.get("quran_loc"), row.get("wbw_loc"))
        if cert_pairs and pair not in cert_pairs:
            errors.append(f"{path}:{lineno}: renderer row has no matching cert row {pair!r}")
        if row.get("live_renderer_claim") is not False:
            errors.append(f"{path}:{lineno}: live_renderer_claim must be false")
        if row.get("renderer_status") != "fixture_not_live":
            errors.append(f"{path}:{lineno}: renderer_status must be fixture_not_live")
        if row.get("surface_text_invariant") != "segments_concat_equals_surface":
            errors.append(f"{path}:{lineno}: renderer invariant must protect exact surface text")
        segments = row.get("segments") or []
        if not segments:
            errors.append(f"{path}:{lineno}: renderer segments must be nonempty")
        if "".join(str(segment.get("surface") or "") for segment in segments) != row.get("surface"):
            errors.append(f"{path}:{lineno}: renderer segment surfaces must concatenate to surface")
        display = row.get("display") or {}
        if display.get("palette") != "qamus-grammar-v1":
            errors.append(f"{path}:{lineno}: display.palette must be qamus-grammar-v1")
        if len(display.get("segments") or []) != len(segments):
            errors.append(f"{path}:{lineno}: display.segments must align with segments")
    return errors


def self_test() -> int:
    good = {
        "tranche_id": "P-RICH-CERT-SELFTEST",
        "source_record": "sample:1",
        "quran_loc": "quran:2:9:5",
        "wbw_loc": "wbw:2:9:5",
        "surface": "وَمَا",
        "current_gloss": "and not",
        "source_decision_state": "rich_candidate",
        "certification_state": "preview_only",
        "parse_key": "CONJ+MA:NEG",
        "segment_roles": ["prefix_conjunction", "negative_particle"],
        "public_payload": {"gloss": "and not", "src": "qamus", "kind": "authored", "lang": "en"},
        "gates": {
            "address": "pass",
            "public_boundary": "pass",
            "sarf": "pass",
            "nahw": "two_vote_required",
            "learner": "pass",
            "source_two_vote": "required_not_complete",
            "renderer": "fixture_not_live",
            "owner": "not_authorized",
        },
        "segment_surface_exact": True,
        "component_candidates_can_certify": False,
        "parse_key_primary_identity": False,
        "may_apply_live": False,
        "next_action": "two-vote review before certification",
    }
    bad = dict(good)
    bad["public_payload"] = dict(good["public_payload"], informed_by="QAC")
    bad["may_apply_live"] = True
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        fh.write(json.dumps(good, ensure_ascii=False) + "\n")
        good_path = fh.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        fh.write(json.dumps(bad, ensure_ascii=False) + "\n")
        bad_path = fh.name
    try:
        good_errors = validate_certification(good_path)
        bad_errors = validate_certification(bad_path)
    finally:
        os.unlink(good_path)
        os.unlink(bad_path)
    if good_errors:
        print("\n".join(good_errors))
        return 1
    if not any("may_apply_live" in err for err in bad_errors):
        print("self-test failed: live-apply flag was accepted")
        return 1
    if not any("public payload leaks" in err for err in bad_errors):
        print("self-test failed: public leak was accepted")
        return 1
    print("RICH HOVER CERTIFICATION SELF-TEST OK")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("certification_jsonl", nargs="?")
    ap.add_argument("--evidence-jsonl")
    ap.add_argument("--renderer-jsonl")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.certification_jsonl:
        ap.error("certification_jsonl is required unless --self-test is used")

    errors = validate_certification(args.certification_jsonl)
    cert_rows = _load_jsonl(args.certification_jsonl)
    for row in cert_rows:
        row.pop("_line", None)
    if args.evidence_jsonl:
        errors.extend(validate_evidence(args.evidence_jsonl, cert_rows))
    if args.renderer_jsonl:
        errors.extend(validate_renderer(args.renderer_jsonl, cert_rows))
    if errors:
        print("\n".join(errors))
        return 1
    print("PASS rich-hover certification: %s" % args.certification_jsonl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
