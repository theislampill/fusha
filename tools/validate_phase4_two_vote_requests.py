#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate exact-addressed Phase 4 two-vote request packets."""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-two-vote-request.schema.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
REQ = re.compile(r"^phase4-two-vote:queue_parse_[0-9a-f]+$")
TRANCHE = re.compile(r"^phase4-tranche:queue_parse_[0-9a-f]+$")
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
    "source_tranche_id",
    "parse_id",
    "lane",
    "required_gate",
    "allowed_next_step",
    "identity",
    "candidate_evidence",
    "gate_reasons",
    "required_evidence",
    "vote_lenses",
    "requested_output",
    "public_boundary",
    "apply_policy",
    "cannot_certify_from",
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


def _forbidden_public_text(row):
    public = {
        "requested_output": row.get("requested_output"),
        "public_boundary": row.get("public_boundary"),
        "apply_policy": row.get("apply_policy"),
    }
    return json.dumps(public, ensure_ascii=False).lower()


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    source_id = str(row.get("source_tranche_id") or "")
    parse_id = str(row.get("parse_id") or "")
    if not REQ.match(row_id):
        _err(errors, line_no, "id must be phase4-two-vote:queue_parse_<hash>")
    if not TRANCHE.match(source_id):
        _err(errors, line_no, "source_tranche_id must be phase4-tranche:queue_parse_<hash>")
    if row_id and source_id and row_id != source_id.replace("phase4-tranche:", "phase4-two-vote:"):
        _err(errors, line_no, "id must derive from source_tranche_id")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    if parse_id and source_id and source_id != "phase4-tranche:queue_%s" % parse_id.replace(":", "_"):
        _err(errors, line_no, "source_tranche_id must derive from parse_id")

    if row.get("phase") != "phase4_two_vote_request":
        _err(errors, line_no, "phase must be phase4_two_vote_request")
    if row.get("lane") != "two_vote_required":
        _err(errors, line_no, "lane must be two_vote_required")
    if row.get("required_gate") != "two_vote_required":
        _err(errors, line_no, "required_gate must be two_vote_required")
    if row.get("allowed_next_step") != "two_vote_review_only":
        _err(errors, line_no, "allowed_next_step must be two_vote_review_only")

    identity = row.get("identity") or {}
    if not isinstance(identity, dict):
        _err(errors, line_no, "identity must be an object")
        identity = {}
    quran_locs = identity.get("quran_locs") or []
    wbw_locs = identity.get("wbw_locs") or []
    if not quran_locs:
        _err(errors, line_no, "identity.quran_locs must be non-empty")
    if not wbw_locs:
        _err(errors, line_no, "identity.wbw_locs must be non-empty")
    if len(quran_locs) != len(wbw_locs):
        _err(errors, line_no, "quran_locs and wbw_locs must have matching counts")
    for loc in quran_locs:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad quran loc %r" % loc)
    for loc in wbw_locs:
        if not WBW.match(str(loc)):
            _err(errors, line_no, "bad wbw loc %r" % loc)
    if identity.get("parse_id") != parse_id:
        _err(errors, line_no, "identity.parse_id must match parse_id")

    evidence = row.get("candidate_evidence") or {}
    if not isinstance(evidence, dict):
        _err(errors, line_no, "candidate_evidence must be an object")
        evidence = {}
    if evidence.get("component_candidates_can_certify") is not False:
        _err(errors, line_no, "component_candidates_can_certify must be false")
    for entry in evidence.get("whole_token_candidates") or []:
        if not isinstance(entry, str) or not QAMUS.match(entry):
            _err(errors, line_no, "whole_token_candidates must be qamus:* strings")
    for entry in evidence.get("component_candidates") or []:
        if not isinstance(entry, str) or not QAMUS.match(entry):
            _err(errors, line_no, "component_candidates must be qamus:* strings")
    for join in evidence.get("component_candidate_joins") or []:
        blob = json.dumps(join, ensure_ascii=False)
        if "source:" not in blob:
            _err(errors, line_no, "component candidate joins must preserve source provenance")
        if "role:" not in blob:
            _err(errors, line_no, "component candidate joins must preserve role provenance")
        if "segment_text:" not in blob:
            _err(errors, line_no, "component candidate joins must preserve segment text provenance")
        if "token_loc:quran:" not in blob:
            _err(errors, line_no, "component candidate joins must preserve token loc provenance")

    if row.get("vote_lenses") != ["sarf-primary", "nahw-primary"]:
        _err(errors, line_no, "vote_lenses must be sarf-primary + nahw-primary")
    requested = row.get("requested_output") or {}
    if requested.get("decision") != "approve | reject | pending":
        _err(errors, line_no, "requested_output.decision contract is wrong")
    if requested.get("safe_scope_after_vote") != "token_only | parse_family_after_impact_preview | pending":
        _err(errors, line_no, "requested_output.safe_scope_after_vote contract is wrong")
    for key in ("concise_authored_gloss", "sarf_reasoning", "nahw_reasoning", "reason_agreement_key", "blocker_if_rejected"):
        if requested.get(key) != "":
            _err(errors, line_no, "requested_output.%s must be blank template text" % key)

    public = row.get("public_boundary") or {}
    expected_public = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_text_allowed": False,
        "external_source_names_public_allowed": False,
    }
    for key, value in expected_public.items():
        actual = public.get(key)
        if actual != value:
            _err(errors, line_no, "public_boundary.%s must be %r" % (key, value))

    policy = row.get("apply_policy") or {}
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

    cannot = row.get("cannot_certify_from") or []
    for required in ("component_candidates", "rich_wbw_segment_candidates", "raw_surface", "norm_only", "parse_key_alone"):
        if required not in cannot:
            _err(errors, line_no, "cannot_certify_from missing %s" % required)

    public_blob = _forbidden_public_text(row)
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in public_blob:
            _err(errors, line_no, "public fields leak forbidden label %r" % label)


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero Phase 4 two-vote request rows")
    return count, errors


def sample_row():
    return {
        "id": "phase4-two-vote:queue_parse_c0ffee12",
        "phase": "phase4_two_vote_request",
        "source_tranche_id": "phase4-tranche:queue_parse_c0ffee12",
        "parse_id": "parse:c0ffee12",
        "lane": "two_vote_required",
        "required_gate": "two_vote_required",
        "allowed_next_step": "two_vote_review_only",
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
            "component_candidates_can_certify": False,
        },
        "gate_reasons": ["grammar_trigger:function_particle", "parse_gate:two_vote_required"],
        "required_evidence": [
            "two independent sarf/nahw checks agreeing on conclusion and reason",
            "exact quran:S:A:W and wbw:S:A:W trace",
            "public hover remains qamus/authored/en",
        ],
        "vote_lenses": ["sarf-primary", "nahw-primary"],
        "requested_output": {
            "decision": "approve | reject | pending",
            "concise_authored_gloss": "",
            "sarf_reasoning": "",
            "nahw_reasoning": "",
            "reason_agreement_key": "",
            "blocker_if_rejected": "",
            "safe_scope_after_vote": "token_only | parse_family_after_impact_preview | pending",
        },
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
        "apply_policy": {
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "closure_claim_allowed": False,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
            "component_candidates_can_certify": False,
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
        },
        "cannot_certify_from": [
            "component_candidates",
            "rich_wbw_segment_candidates",
            "raw_surface",
            "norm_only",
            "parse_key_alone",
        ],
    }


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-two-vote-validate-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        row = sample_row()
        write_jsonl(good, [row])
        count, errors = validate(good)
        if count != 1 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        bad_row = dict(row)
        bad_row["required_gate"] = "auto_safe_after_preview"
        bad_row["candidate_evidence"] = dict(row["candidate_evidence"])
        bad_row["candidate_evidence"]["component_candidates_can_certify"] = True
        write_jsonl(bad, [bad_row])
        count, errors = validate(bad)
        if count != 1:
            print("SELF-TEST FAIL bad count:", count)
            return 1
        if not any("required_gate must be two_vote_required" in err for err in errors):
            print("SELF-TEST FAIL bad gate:", errors)
            return 1
        if not any("component_candidates_can_certify must be false" in err for err in errors):
            print("SELF-TEST FAIL bad component certifier:", errors)
            return 1
    print("PASS — Phase 4 two-vote request validator self-test")
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
    print("checked %d Phase 4 two-vote request rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — Phase 4 two-vote requests are exact-addressed and review-only")


if __name__ == "__main__":
    main()
