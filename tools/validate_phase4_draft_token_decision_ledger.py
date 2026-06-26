#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate source-only Phase 4 draft token-decision ledger rows."""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-draft-token-decision-ledger.schema.json")
ROW_ID = re.compile(r"^phase4-draft-token-decision:(\d{1,3}_\d{1,3}_\d{1,3}):([0-9a-f]+)$")
PLAN_ID = re.compile(r"^phase4-hover-decision-plan:(\d{1,3}_\d{1,3}_\d{1,3}):([0-9a-f]+)$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
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
REQUIRED = [
    "id",
    "phase",
    "status",
    "identity",
    "token_decision",
    "plan_lineage",
    "safe_scope",
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
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(value):
    return " ".join(str(value or "").strip().split())


def bare_wbw_loc(wbw_loc):
    if not isinstance(wbw_loc, str) or not wbw_loc.startswith("wbw:"):
        return ""
    return wbw_loc.replace("wbw:", "", 1)


def public_text_leaks(value):
    text = json.dumps(value, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def load_plan(path):
    by_id = {}
    by_wbw = {}
    if not path:
        return by_id, by_wbw
    for line_no, row in iter_jsonl(path):
        row_id = row.get("id") if isinstance(row, dict) else None
        wbw = ((row.get("identity") or {}).get("wbw_loc")) if isinstance(row, dict) else None
        if row_id:
            by_id[row_id] = (line_no, row)
        if wbw:
            by_wbw[wbw] = (line_no, row)
    return by_id, by_wbw


def validate_policy(row, line_no, errors):
    policy = row.get("apply_policy") or {}
    if not isinstance(policy, dict):
        _err(errors, line_no, "apply_policy must be an object")
        policy = {}
    false_fields = (
        "apply_allowed",
        "live_mutation_allowed",
        "closure_claim_allowed",
        "component_candidates_can_certify",
        "raw_surface_identity_allowed",
        "parse_key_primary_identity",
    )
    for key in false_fields:
        if policy.get(key) is not False:
            _err(errors, line_no, "apply_policy.%s must be false" % key)
    true_fields = (
        "draft_only",
        "append_only_ledger_required",
        "backup_required",
        "rebuild_required",
        "validation_required",
        "health_check_required",
        "targeted_public_readback_required",
        "public_boundary_scan_required",
        "rollback_required",
    )
    for key in true_fields:
        if policy.get(key) is not True:
            _err(errors, line_no, "apply_policy.%s must be true" % key)


def validate_public_boundary(row, line_no, errors):
    boundary = row.get("public_boundary") or {}
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "internal_provenance_public": False,
        "external_source_names_public": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            _err(errors, line_no, "public_boundary.%s must be %r" % (key, value))


def validate_row(row, line_no, errors, plan_by_id=None):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    match = ROW_ID.match(row_id)
    if not match:
        _err(errors, line_no, "id must be phase4-draft-token-decision:<S_A_W>:<parsehash>")
    if row.get("phase") != "phase4_draft_token_decision_ledger":
        _err(errors, line_no, "phase must be phase4_draft_token_decision_ledger")
    if row.get("status") != "draft_not_applied":
        _err(errors, line_no, "status must be draft_not_applied")
    if row.get("safe_scope") not in ("token_only", "parse_family_after_impact_preview", "pending"):
        _err(errors, line_no, "safe_scope is invalid")

    identity = row.get("identity") or {}
    quran_loc = identity.get("quran_loc")
    wbw_loc = identity.get("wbw_loc")
    parse_id = identity.get("parse_id")
    if not QURAN.match(str(quran_loc or "")):
        _err(errors, line_no, "bad quran_loc %r" % quran_loc)
    if not WBW.match(str(wbw_loc or "")):
        _err(errors, line_no, "bad wbw_loc %r" % wbw_loc)
    if not PARSE.match(str(parse_id or "")):
        _err(errors, line_no, "bad parse_id %r" % parse_id)
    if match and wbw_loc and match.group(1) != bare_wbw_loc(wbw_loc).replace(":", "_"):
        _err(errors, line_no, "id loc must derive from wbw_loc")
    if match and parse_id and match.group(2) != str(parse_id).replace("parse:", ""):
        _err(errors, line_no, "id parse hash must match identity.parse_id")

    token = row.get("token_decision") or {}
    if token.get("loc") != bare_wbw_loc(wbw_loc):
        _err(errors, line_no, "token_decision.loc must derive from wbw_loc")
    if not compact(token.get("gloss")):
        _err(errors, line_no, "token_decision.gloss must be non-empty")
    for key, value in (("src", "qamus"), ("kind", "authored"), ("lang", "en")):
        if token.get(key) != value:
            _err(errors, line_no, "token_decision.%s must be %r" % (key, value))
    leaks = public_text_leaks(token)
    if leaks:
        _err(errors, line_no, "token_decision leaks forbidden label %r" % leaks[0])

    lineage = row.get("plan_lineage") or {}
    source_plan_id = lineage.get("source_plan_id")
    plan_match = PLAN_ID.match(str(source_plan_id or ""))
    if not plan_match:
        _err(errors, line_no, "plan_lineage.source_plan_id must be a hover decision plan id")
    elif match and plan_match.groups() != match.groups():
        _err(errors, line_no, "draft id must derive from source plan id")
    if not compact(lineage.get("source_certified_id")):
        _err(errors, line_no, "plan_lineage.source_certified_id must be non-empty")
    source_ids = lineage.get("source_certified_ids") or []
    if not isinstance(source_ids, list) or not source_ids:
        _err(errors, line_no, "plan_lineage.source_certified_ids must be non-empty")
    elif lineage.get("source_certified_id") not in source_ids:
        _err(errors, line_no, "source_certified_id must be included in source_certified_ids")
    if lineage.get("source_phase") not in ("phase4_two_vote_reconciled", "phase4_gloss_adjudication_reconciled"):
        _err(errors, line_no, "plan_lineage.source_phase is invalid")
    if not compact(lineage.get("reason_agreement_key")):
        _err(errors, line_no, "plan_lineage.reason_agreement_key must be non-empty")

    if plan_by_id is not None and source_plan_id in plan_by_id:
        _plan_line, plan = plan_by_id[source_plan_id]
        plan_identity = plan.get("identity") or {}
        plan_preview = plan.get("token_decision_preview") or {}
        if plan_identity.get("quran_loc") != quran_loc:
            _err(errors, line_no, "quran_loc differs from source plan")
        if plan_identity.get("wbw_loc") != wbw_loc:
            _err(errors, line_no, "wbw_loc differs from source plan")
        if plan_identity.get("parse_id") != parse_id:
            _err(errors, line_no, "parse_id differs from source plan")
        for key in ("loc", "gloss", "src", "kind", "lang"):
            if token.get(key) != plan_preview.get(key):
                _err(errors, line_no, "token_decision.%s differs from source plan preview" % key)
    elif plan_by_id is not None:
        _err(errors, line_no, "source plan id not found in plan_jsonl")

    validate_public_boundary(row, line_no, errors)
    validate_policy(row, line_no, errors)


def validate(path, plan_jsonl=None):
    errors = []
    count = 0
    loc_seen = {}
    plan_by_id, _plan_by_wbw = load_plan(plan_jsonl) if plan_jsonl else ({}, {})
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors, plan_by_id=plan_by_id if plan_jsonl else None)
        token = (row.get("token_decision") or {}) if isinstance(row, dict) else {}
        loc = token.get("loc")
        if loc:
            if loc in loc_seen:
                _err(errors, line_no, "duplicate token_decision.loc %s also seen at line %d" % (loc, loc_seen[loc]))
            loc_seen[loc] = line_no
    if count == 0:
        errors.append("zero Phase 4 draft token-decision rows")
    return count, errors


def sample_row():
    return {
        "id": "phase4-draft-token-decision:22_18_17:c0ffee12",
        "phase": "phase4_draft_token_decision_ledger",
        "status": "draft_not_applied",
        "identity": {
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "parse_id": "parse:c0ffee12",
            "surface_sample": "وَٱلشَّجَرُ",
        },
        "token_decision": {
            "loc": "22:18:17",
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "plan_lineage": {
            "source_plan_id": "phase4-hover-decision-plan:22_18_17:c0ffee12",
            "source_phase": "phase4_two_vote_reconciled",
            "source_certified_id": "phase4-two-vote:queue_parse_c0ffee12",
            "source_certified_ids": [
                "phase4-two-vote:queue_parse_c0ffee12",
                "phase4-two-vote-response:queue_parse_c0ffee12:sarf-primary",
                "phase4-two-vote-response:queue_parse_c0ffee12:nahw-primary",
            ],
            "reason_agreement_key": "conj-definite-noun-coordinated-list",
        },
        "safe_scope": "token_only",
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "internal_provenance_public": False,
            "external_source_names_public": False,
        },
        "apply_policy": {
            "draft_only": True,
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "closure_claim_allowed": False,
            "append_only_ledger_required": True,
            "backup_required": True,
            "rebuild_required": True,
            "validation_required": True,
            "health_check_required": True,
            "targeted_public_readback_required": True,
            "public_boundary_scan_required": True,
            "rollback_required": True,
            "component_candidates_can_certify": False,
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
        },
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-draft-token-decision-validate-") as td:
        good = os.path.join(td, "good.jsonl")
        write_jsonl(good, [sample_row()])
        count, errors = validate(good)
        if count != 1 or errors:
            raise AssertionError(errors)
        bad = os.path.join(td, "bad.jsonl")
        row = sample_row()
        row["apply_policy"]["apply_allowed"] = True
        write_jsonl(bad, [row])
        _count, bad_errors = validate(bad)
        if not bad_errors:
            raise AssertionError("validator accepted apply_allowed=true")
    print("PASS — Phase 4 draft token-decision ledger validator self-test")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft_jsonl", nargs="?")
    parser.add_argument("--plan-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.draft_jsonl:
        parser.error("draft_jsonl is required unless --self-test is used")
    count, errors = validate(args.draft_jsonl, plan_jsonl=args.plan_jsonl)
    if errors:
        for err in errors:
            print("ERROR: %s" % err)
        return 1
    print("checked %d Phase 4 draft token-decision rows" % count)
    print("PASS — Phase 4 draft token-decision ledger is source-only and non-mutating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
