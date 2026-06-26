#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Phase 4 hover decision plan rows.

These rows are review-only previews for a future append-only apply path. They
must never be treated as live token-decision ledger rows.
"""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-hover-decision-plan.schema.json")
PLAN = re.compile(r"^phase4-hover-decision-plan:(\d{1,3}_\d{1,3}_\d{1,3}):([0-9a-f]+)$")
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
)
REQUIRED = [
    "id",
    "phase",
    "source_phase",
    "source_certified_id",
    "source_certified_ids",
    "status",
    "parse_id",
    "identity",
    "public_hover",
    "token_decision_preview",
    "safe_scope",
    "reason_agreement_key",
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


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def public_text_leaks(value):
    text = json.dumps(value, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def bare_loc(address, prefix):
    if not isinstance(address, str) or not address.startswith(prefix + ":"):
        return ""
    return address[len(prefix) + 1:]


def validate_public_hover(row, line_no, errors):
    hover = row.get("public_hover") or {}
    if not isinstance(hover, dict):
        _err(errors, line_no, "public_hover must be an object")
        hover = {}
    expected = {"src": "qamus", "kind": "authored", "lang": "en"}
    for key, value in expected.items():
        if hover.get(key) != value:
            _err(errors, line_no, "public_hover.%s must be %r" % (key, value))
    if not compact(hover.get("gloss")):
        _err(errors, line_no, "public_hover.gloss must be non-empty")
    leaks = public_text_leaks(hover)
    if leaks:
        _err(errors, line_no, "public_hover leaks forbidden label %r" % leaks[0])


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
        "append_only_ledger_required",
        "requires_backup_rebuild_health_readback_before_apply",
    )
    for key in true_fields:
        if policy.get(key) is not True:
            _err(errors, line_no, "apply_policy.%s must be true" % key)
    if "quran:S:A:W" not in str(policy.get("identity") or "") or "wbw:S:A:W" not in str(policy.get("identity") or ""):
        _err(errors, line_no, "apply_policy.identity must name exact quran/wbw identities")
    if policy.get("public_boundary") != "src=qamus, kind=authored, lang=en; no external provenance":
        _err(errors, line_no, "apply_policy.public_boundary must be source-clean")


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    match = PLAN.match(row_id)
    if not match:
        _err(errors, line_no, "id must be phase4-hover-decision-plan:<S_A_W>:<parsehash>")
    parse_id = str(row.get("parse_id") or "")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    elif match and match.group(2) != parse_id.replace("parse:", ""):
        _err(errors, line_no, "id parse hash must match parse_id")

    if row.get("phase") != "phase4_hover_decision_plan":
        _err(errors, line_no, "phase must be phase4_hover_decision_plan")
    if row.get("source_phase") not in ("phase4_two_vote_reconciled", "phase4_gloss_adjudication_reconciled"):
        _err(errors, line_no, "source_phase is invalid")
    if row.get("status") != "planned_not_applied":
        _err(errors, line_no, "status must be planned_not_applied")
    if row.get("safe_scope") not in ("token_only", "parse_family_after_impact_preview", "pending"):
        _err(errors, line_no, "safe_scope is invalid")
    if not compact(row.get("source_certified_id")):
        _err(errors, line_no, "source_certified_id must be non-empty")
    source_ids = row.get("source_certified_ids") or []
    if not isinstance(source_ids, list) or not source_ids:
        _err(errors, line_no, "source_certified_ids must be non-empty")
    elif row.get("source_certified_id") not in source_ids:
        _err(errors, line_no, "source_certified_id must be included in source_certified_ids")
    if not compact(row.get("reason_agreement_key")):
        _err(errors, line_no, "reason_agreement_key must be non-empty")

    identity = row.get("identity") or {}
    if not isinstance(identity, dict):
        _err(errors, line_no, "identity must be an object")
        identity = {}
    quran_loc = identity.get("quran_loc")
    wbw_loc = identity.get("wbw_loc")
    if not QURAN.match(str(quran_loc or "")):
        _err(errors, line_no, "bad quran loc %r" % quran_loc)
    if not WBW.match(str(wbw_loc or "")):
        _err(errors, line_no, "bad wbw loc %r" % wbw_loc)
    if identity.get("parse_id") != parse_id:
        _err(errors, line_no, "identity.parse_id must match parse_id")
    if match and wbw_loc and match.group(1) != bare_loc(wbw_loc, "wbw").replace(":", "_"):
        _err(errors, line_no, "id loc must derive from wbw_loc")

    validate_public_hover(row, line_no, errors)
    preview = row.get("token_decision_preview") or {}
    if not isinstance(preview, dict):
        _err(errors, line_no, "token_decision_preview must be an object")
        preview = {}
    hover = row.get("public_hover") or {}
    if preview.get("loc") != bare_loc(wbw_loc, "wbw"):
        _err(errors, line_no, "token_decision_preview.loc must derive from wbw_loc")
    for key in ("gloss", "src", "kind", "lang"):
        if preview.get(key) != hover.get(key):
            _err(errors, line_no, "token_decision_preview.%s must match public_hover.%s" % (key, key))
    leaks = public_text_leaks(preview)
    if leaks:
        _err(errors, line_no, "token_decision_preview leaks forbidden label %r" % leaks[0])
    validate_policy(row, line_no, errors)


def validate(path):
    errors = []
    count = 0
    wbw_seen = {}
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
        if isinstance(row, dict):
            wbw = ((row.get("identity") or {}).get("wbw_loc"))
            if wbw:
                if wbw in wbw_seen:
                    _err(errors, line_no, "duplicate wbw_loc %s also seen at line %d" % (wbw, wbw_seen[wbw]))
                wbw_seen[wbw] = line_no
    if count == 0:
        errors.append("zero Phase 4 hover decision plan rows")
    return count, errors


def sample_row():
    return {
        "id": "phase4-hover-decision-plan:22_18_17:c0ffee12",
        "phase": "phase4_hover_decision_plan",
        "source_phase": "phase4_two_vote_reconciled",
        "source_certified_id": "phase4-two-vote:queue_parse_c0ffee12",
        "source_certified_ids": [
            "phase4-two-vote:queue_parse_c0ffee12",
            "phase4-two-vote-response:queue_parse_c0ffee12:sarf-primary",
            "phase4-two-vote-response:queue_parse_c0ffee12:nahw-primary",
        ],
        "status": "planned_not_applied",
        "parse_id": "parse:c0ffee12",
        "identity": {
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "parse_id": "parse:c0ffee12",
            "surface_sample": "وَٱلشَّجَرُ",
        },
        "public_hover": {
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "token_decision_preview": {
            "loc": "22:18:17",
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "safe_scope": "token_only",
        "reason_agreement_key": "conj-definite-noun-coordinated-list",
        "apply_policy": {
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "closure_claim_allowed": False,
            "append_only_ledger_required": True,
            "requires_backup_rebuild_health_readback_before_apply": True,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
            "component_candidates_can_certify": False,
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
        },
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-hover-decision-plan-validate-") as td:
        path = os.path.join(td, "plan.jsonl")
        write_jsonl(path, [sample_row()])
        count, errors = validate(path)
        if count != 1 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
        bad = sample_row()
        bad["public_hover"]["gloss"] = "QAC says and the trees"
        bad["token_decision_preview"]["gloss"] = "QAC says and the trees"
        write_jsonl(path, [bad])
        _count, errors = validate(path)
        if not any("public_hover leaks forbidden label" in err for err in errors):
            print("SELF-TEST FAIL: expected public leak rejection")
            return 1
    print("PASS — Phase 4 hover decision plan validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan_jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.plan_jsonl:
        parser.error("plan_jsonl is required unless --self-test is used")
    count, errors = validate(args.plan_jsonl)
    print("checked %d Phase 4 hover decision plan rows" % count)
    if errors:
        print("FAIL")
        for err in errors:
            print("- %s" % err)
        raise SystemExit(1)
    print("PASS — Phase 4 hover decision plan is exact-addressed and review-only")


if __name__ == "__main__":
    main()
