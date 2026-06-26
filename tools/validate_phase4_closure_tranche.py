#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Phase 4 dry-run closure tranche rows.

The tranche planner is allowed to make the next closure-review batch easier to
work, but it is not an apply tool. Rows must stay exact-addressed, review-only,
and source-clean.
"""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-closure-tranche.schema.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
TRANCHE = re.compile(r"^phase4-tranche:queue_parse_[0-9a-f]+$")
QUEUE = re.compile(r"^queue:parse_[0-9a-f]+$")
QAMUS = re.compile(r"^qamus:")
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
)
REQUIRED = [
    "id",
    "phase",
    "source_review_pack_id",
    "parse_id",
    "lane",
    "priority",
    "allowed_next_step",
    "scope",
    "recommended_action",
    "required_gate",
    "required_evidence",
    "impact_preview_required",
    "identity",
    "candidate_evidence",
    "gate_reasons",
    "apply_policy",
]


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except Exception as exc:
                yield line_no, {"__json_error__": str(exc)}


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    source_id = str(row.get("source_review_pack_id") or "")
    parse_id = str(row.get("parse_id") or "")
    if not TRANCHE.match(row_id):
        _err(errors, line_no, "id must be phase4-tranche:queue_parse_<hash>")
    if not QUEUE.match(source_id):
        _err(errors, line_no, "source_review_pack_id must be queue:parse_<hash>")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    expected_id = "phase4-tranche:%s" % source_id.replace(":", "_")
    if row_id and source_id and row_id != expected_id:
        _err(errors, line_no, "id must derive from source_review_pack_id")
    if parse_id and source_id and source_id != "queue:%s" % parse_id.replace(":", "_"):
        _err(errors, line_no, "source_review_pack_id must derive from parse_id")

    if row.get("phase") != "phase4_dry_run":
        _err(errors, line_no, "phase must be phase4_dry_run")
    if row.get("allowed_next_step") != "review_only":
        _err(errors, line_no, "allowed_next_step must be review_only")
    if row.get("impact_preview_required") is not True:
        _err(errors, line_no, "impact_preview_required must be true")
    if not isinstance(row.get("priority"), int) or row.get("priority") < 1:
        _err(errors, line_no, "priority must be a positive integer")
    if not row.get("required_evidence"):
        _err(errors, line_no, "required_evidence must be non-empty")
    if not row.get("gate_reasons"):
        _err(errors, line_no, "gate_reasons must be non-empty")

    identity = row.get("identity") or {}
    if not isinstance(identity, dict):
        _err(errors, line_no, "identity must be an object")
        identity = {}
    quran_locs = identity.get("quran_locs") or []
    wbw_locs = identity.get("wbw_locs") or []
    if len(quran_locs) != len(wbw_locs):
        _err(errors, line_no, "quran_locs and wbw_locs must have matching counts")
    for loc in quran_locs:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad quran loc %r" % loc)
    for loc in wbw_locs:
        if not WBW.match(str(loc)):
            _err(errors, line_no, "bad wbw loc %r" % loc)
    if identity.get("parse_id") != row.get("parse_id"):
        _err(errors, line_no, "identity.parse_id must match parse_id")

    evidence = row.get("candidate_evidence") or {}
    if not isinstance(evidence, dict):
        _err(errors, line_no, "candidate_evidence must be an object")
        evidence = {}
    for entry in evidence.get("whole_token_candidates") or []:
        if not isinstance(entry, str) or not QAMUS.match(entry):
            _err(errors, line_no, "whole_token_candidates must be qamus:*")
    for entry in evidence.get("component_candidates") or []:
        if not isinstance(entry, str) or not QAMUS.match(entry):
            _err(errors, line_no, "component_candidates must be qamus:*")

    lane = row.get("lane")
    if lane == "propagation_safe_candidate" and evidence.get("component_candidates"):
        _err(errors, line_no, "component candidates cannot appear in propagation_safe_candidate tranche")
    if evidence.get("component_candidates") and row.get("required_gate") in {"auto_safe", "auto_safe_after_preview"}:
        _err(errors, line_no, "component candidates cannot weaken a tranche to auto-safe gate")
    if lane == "two_vote_required" and row.get("required_gate") != "two_vote_required":
        _err(errors, line_no, "two_vote_required tranche must require two_vote_required")

    policy = row.get("apply_policy") or {}
    if not isinstance(policy, dict):
        _err(errors, line_no, "apply_policy must be an object")
        policy = {}
    expected_policy = {
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
        "component_candidates_can_certify": False,
        "raw_surface_identity_allowed": False,
        "parse_key_primary_identity": False,
    }
    for key, value in expected_policy.items():
        if policy.get(key) is not value:
            _err(errors, line_no, "apply_policy.%s must be %r" % (key, value))
    if "quran:S:A:W" not in str(policy.get("identity") or "") or "wbw:S:A:W" not in str(policy.get("identity") or ""):
        _err(errors, line_no, "apply_policy.identity must name quran/wbw exact identities")
    if policy.get("public_boundary") != "src=qamus, kind=authored, lang=en; no external provenance":
        _err(errors, line_no, "apply_policy.public_boundary must be source-clean")
    public_blob = json.dumps(policy, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in public_blob:
            _err(errors, line_no, "apply_policy leaks forbidden label %r" % label)


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero Phase 4 tranche rows")
    return count, errors


def sample_rows():
    policy = {
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
        "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
        "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
        "component_candidates_can_certify": False,
        "raw_surface_identity_allowed": False,
        "parse_key_primary_identity": False,
    }
    return [
        {
            "id": "phase4-tranche:queue_parse_c0ffee12",
            "phase": "phase4_dry_run",
            "source_review_pack_id": "queue:parse_c0ffee12",
            "parse_id": "parse:c0ffee12",
            "lane": "two_vote_required",
            "priority": 1,
            "allowed_next_step": "review_only",
            "scope": "token_or_family_after_votes",
            "recommended_action": "build two-vote review packet with source-addressed reasoning",
            "required_gate": "two_vote_required",
            "required_evidence": [
                "two independent sarf/nahw checks agreeing on conclusion and reason",
                "exact quran:S:A:W and wbw:S:A:W trace",
                "public hover remains qamus/authored/en",
            ],
            "impact_preview_required": True,
            "identity": {
                "quran_locs": ["quran:22:18:17"],
                "wbw_locs": ["wbw:22:18:17"],
                "parse_id": "parse:c0ffee12",
                "surface_sample": "وَٱلشَّجَرُ",
            },
            "candidate_evidence": {
                "whole_token_candidates": [],
                "whole_token_candidate_joins": [],
                "component_candidates": ["qamus:p:waw", "qamus:p:al", "qamus:n:tree"],
                "component_candidate_joins": [
                    {"entry": "qamus:p:waw", "join_status": ["source:rich_wbw_segment", "role:conjunction", "segment_text:وَ", "token_loc:quran:22:18:17"]}
                ],
            },
            "gate_reasons": ["grammar_trigger:function_particle", "parse_gate:two_vote_required"],
            "apply_policy": policy,
        },
        {
            "id": "phase4-tranche:queue_parse_abcdef12",
            "phase": "phase4_dry_run",
            "source_review_pack_id": "queue:parse_abcdef12",
            "parse_id": "parse:abcdef12",
            "lane": "propagation_safe_candidate",
            "priority": 2,
            "allowed_next_step": "review_only",
            "scope": "parse_key_family_readonly_preview",
            "recommended_action": "preview exact token family before any append-only propagation",
            "required_gate": "auto_safe_after_preview",
            "required_evidence": [
                "exact whole-token candidate join",
                "family impact preview before any apply",
                "targeted public no-leak readback plan",
            ],
            "impact_preview_required": True,
            "identity": {
                "quran_locs": ["quran:22:18:12", "quran:29:22:5"],
                "wbw_locs": ["wbw:22:18:12", "wbw:29:22:5"],
                "parse_id": "parse:abcdef12",
                "surface_sample": "ٱلْأَرْضِ",
            },
            "candidate_evidence": {
                "whole_token_candidates": ["qamus:n:earth"],
                "whole_token_candidate_joins": [{"entry": "qamus:n:earth", "join_status": ["exact:strict_surface"]}],
                "component_candidates": [],
                "component_candidate_joins": [],
            },
            "gate_reasons": ["parse_gate:auto_safe", "requires_pre_apply_family_preview"],
            "apply_policy": policy,
        },
    ]


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-tranche-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        rows = sample_rows()
        with io.open(good, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        bad_row = dict(rows[0])
        bad_row["required_gate"] = "auto_safe_after_preview"
        with io.open(bad, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(bad_row, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(good)
        if count != 2 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        count, errors = validate(bad)
        if count != 1 or not any("component candidates cannot weaken" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
    print("PASS — Phase 4 dry-run closure tranche validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.jsonl:
        parser.error("jsonl path is required unless --self-test is used")
    count, errors = validate(args.jsonl)
    print("checked %d Phase 4 tranche rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — Phase 4 dry-run closure tranche is exact-addressed and review-only")


if __name__ == "__main__":
    main()
