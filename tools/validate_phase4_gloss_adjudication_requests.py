#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Phase 4 exact-addressed gloss wording adjudication requests."""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-gloss-adjudication-request.schema.json")
REQ = re.compile(r"^phase4-gloss-adjudication:queue_parse_[0-9a-f]+$")
TWO_VOTE = re.compile(r"^phase4-two-vote:queue_parse_[0-9a-f]+$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
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
)
REQUIRED = [
    "id",
    "phase",
    "source_two_vote_request_id",
    "source_unresolved_reason",
    "parse_id",
    "identity",
    "candidate_glosses",
    "shared_reason_agreement_key",
    "vote_summaries",
    "allowed_next_step",
    "requested_output",
    "public_boundary",
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


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(value):
    return " ".join(str(value or "").strip().split())


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def public_text_leaks(value):
    text = compact(value).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def public_boundary_errors(boundary):
    errors = []
    if not isinstance(boundary, dict):
        return ["public_boundary must be an object"]
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_text_allowed": False,
        "external_source_names_public_allowed": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            errors.append("public_boundary.%s must be %r" % (key, value))
    blob = json.dumps(boundary, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in blob:
            errors.append("public_boundary leaks forbidden label %r" % label)
    return errors


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    source_id = str(row.get("source_two_vote_request_id") or "")
    parse_id = str(row.get("parse_id") or "")
    if not REQ.match(row_id):
        _err(errors, line_no, "id must be phase4-gloss-adjudication:queue_parse_<hash>")
    if not TWO_VOTE.match(source_id):
        _err(errors, line_no, "source_two_vote_request_id must be phase4-two-vote:queue_parse_<hash>")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    if row_id and source_id and row_id != source_id.replace("phase4-two-vote:", "phase4-gloss-adjudication:"):
        _err(errors, line_no, "id must derive from source_two_vote_request_id")
    if parse_id and source_id and source_id != "phase4-two-vote:queue_%s" % parse_id.replace(":", "_"):
        _err(errors, line_no, "source_two_vote_request_id must derive from parse_id")

    if row.get("phase") != "phase4_gloss_adjudication_request":
        _err(errors, line_no, "phase must be phase4_gloss_adjudication_request")
    if row.get("source_unresolved_reason") != "gloss_wording_disagreement":
        _err(errors, line_no, "source_unresolved_reason must be gloss_wording_disagreement")
    if row.get("allowed_next_step") != "owner_or_scholar_gloss_adjudication_only":
        _err(errors, line_no, "allowed_next_step is invalid")

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

    glosses = row.get("candidate_glosses") or []
    if not isinstance(glosses, list) or len(glosses) < 2:
        _err(errors, line_no, "candidate_glosses must contain at least two options")
        glosses = []
    compacted = [compact(item) for item in glosses]
    if len(set(compacted)) != len(compacted):
        _err(errors, line_no, "candidate_glosses must be unique after whitespace compaction")
    for gloss in compacted:
        if not gloss:
            _err(errors, line_no, "candidate_gloss must be non-empty")
        leaks = public_text_leaks(gloss)
        if leaks:
            _err(errors, line_no, "candidate_gloss leaks forbidden label %r" % leaks[0])

    reason = compact(row.get("shared_reason_agreement_key"))
    if not re.match(r"^[a-z0-9][a-z0-9-]+$", reason):
        _err(errors, line_no, "shared_reason_agreement_key is invalid")
    summaries = row.get("vote_summaries") or []
    if not isinstance(summaries, list) or len(summaries) < 2:
        _err(errors, line_no, "vote_summaries must contain at least two votes")
        summaries = []
    for summary in summaries:
        if not isinstance(summary, dict):
            _err(errors, line_no, "vote_summaries items must be objects")
            continue
        if summary.get("decision") != "approve":
            _err(errors, line_no, "gloss adjudication only accepts approved vote summaries")
        if compact(summary.get("gloss")) not in compacted:
            _err(errors, line_no, "vote summary gloss must be one candidate_gloss")
        if compact(summary.get("reason_agreement_key")) != reason:
            _err(errors, line_no, "vote summary reason must match shared_reason_agreement_key")

    requested = row.get("requested_output") or {}
    if not isinstance(requested, dict):
        _err(errors, line_no, "requested_output must be an object")
        requested = {}
    expected_requested = {
        "selected_concise_authored_gloss": "",
        "adjudication_reason": "",
        "safe_scope_after_adjudication": "token_only | parse_family_after_impact_preview | pending",
    }
    for key, value in expected_requested.items():
        if requested.get(key) != value:
            _err(errors, line_no, "requested_output.%s must be %r" % (key, value))

    for msg in public_boundary_errors(row.get("public_boundary")):
        _err(errors, line_no, msg)
    policy = row.get("apply_policy") or {}
    if not isinstance(policy, dict):
        _err(errors, line_no, "apply_policy must be an object")
        policy = {}
    for key in ("apply_allowed", "live_mutation_allowed", "closure_claim_allowed",
                "component_candidates_can_certify", "raw_surface_identity_allowed",
                "parse_key_primary_identity"):
        if policy.get(key) is not False:
            _err(errors, line_no, "apply_policy.%s must be false" % key)
    if "quran:S:A:W" not in str(policy.get("identity") or ""):
        _err(errors, line_no, "apply_policy.identity must preserve exact token identity")


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero Phase 4 gloss adjudication request rows")
    return count, errors


def sample_row():
    return {
        "id": "phase4-gloss-adjudication:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "phase": "phase4_gloss_adjudication_request",
        "source_two_vote_request_id": "phase4-two-vote:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "source_unresolved_reason": "gloss_wording_disagreement",
        "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
        "identity": {
            "quran_locs": ["quran:2:178:22"],
            "wbw_locs": ["wbw:2:178:22"],
            "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
            "surface_sample": "بِٱلْمَعْرُوفِ",
        },
        "candidate_glosses": ["in a recognized manner", "with recognized fairness"],
        "shared_reason_agreement_key": "preposition-governed-nominal-manner",
        "vote_summaries": [
            {"lens": "sarf-primary", "decision": "approve", "gloss": "in a recognized manner",
             "reason_agreement_key": "preposition-governed-nominal-manner", "blocker_if_rejected": ""},
            {"lens": "nahw-primary", "decision": "approve", "gloss": "with recognized fairness",
             "reason_agreement_key": "preposition-governed-nominal-manner", "blocker_if_rejected": ""},
        ],
        "allowed_next_step": "owner_or_scholar_gloss_adjudication_only",
        "requested_output": {
            "selected_concise_authored_gloss": "",
            "adjudication_reason": "",
            "safe_scope_after_adjudication": "token_only | parse_family_after_impact_preview | pending",
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
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-gloss-adjudication-validate-") as td:
        path = os.path.join(td, "requests.jsonl")
        write_jsonl(path, [sample_row()])
        count, errors = validate(path)
        if count != 1 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
        bad = sample_row()
        bad["candidate_glosses"] = ["QAC says with fairness", "with fairness"]
        write_jsonl(path, [bad])
        _count, errors = validate(path)
        if not any("candidate_gloss leaks forbidden label" in err for err in errors):
            print("SELF-TEST FAIL: expected public leak rejection")
            return 1
    print("PASS — Phase 4 gloss adjudication request validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("requests_jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.requests_jsonl:
        parser.error("requests_jsonl is required unless --self-test is used")
    count, errors = validate(args.requests_jsonl)
    print("checked %d Phase 4 gloss adjudication request rows" % count)
    if errors:
        print("FAIL")
        for err in errors:
            print("- %s" % err)
        raise SystemExit(1)
    print("PASS — Phase 4 gloss adjudication requests are exact-addressed and review-only")


if __name__ == "__main__":
    main()
