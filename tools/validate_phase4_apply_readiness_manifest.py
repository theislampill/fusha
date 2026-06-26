#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a Phase 4 apply-readiness manifest.

The manifest is not an apply authorization. It proves that a future apply would
need exact-addressed, reversible gates before live mutation can be considered.
"""
import argparse
import hashlib
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-apply-readiness-manifest.schema.json")
MANIFEST_ID = re.compile(r"^phase4-apply-readiness:[0-9a-f]{16}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
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
REQUIRED_GATES = (
    "append_only_ledger",
    "backup",
    "rebuild",
    "validation",
    "health_check",
    "targeted_public_readback",
    "public_boundary_scan",
    "rollback_rehearsal",
)
FALSE_POLICY_FIELDS = (
    "apply_authorized",
    "apply_allowed",
    "live_mutation_allowed",
    "wbw_rebuild_allowed",
    "service_restart_allowed",
    "mirror_sync_allowed",
    "closure_claim_allowed",
    "parse_key_primary_identity",
    "raw_surface_identity_allowed",
    "component_candidates_can_certify",
)


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, row):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(row, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_text_leaks(row):
    text = json.dumps(row, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def _err(errors, msg):
    errors.append(msg)


def validate_required_gates(row, errors):
    gates = row.get("required_gates") or {}
    if not isinstance(gates, dict):
        _err(errors, "required_gates must be an object")
        gates = {}
    for gate in REQUIRED_GATES:
        if gate not in gates:
            _err(errors, "required_gates.%s is missing" % gate)
            continue
        item = gates.get(gate) or {}
        if item.get("required") is not True:
            _err(errors, "required_gates.%s.required must be true" % gate)
        if item.get("status") != "not_run":
            _err(errors, "required_gates.%s.status must be not_run" % gate)
        if not str(item.get("evidence_required") or "").strip():
            _err(errors, "required_gates.%s.evidence_required must be non-empty" % gate)


def validate_policy(row, errors):
    policy = row.get("apply_policy") or {}
    if not isinstance(policy, dict):
        _err(errors, "apply_policy must be an object")
        policy = {}
    for field in FALSE_POLICY_FIELDS:
        if policy.get(field) is not False:
            _err(errors, "apply_policy.%s must be false" % field)
    if policy.get("decision_plan_only") is not True:
        _err(errors, "apply_policy.decision_plan_only must be true")


def validate_public_boundary(row, errors):
    boundary = row.get("public_boundary") or {}
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            _err(errors, "public_boundary.%s must be %r" % (key, value))


def validate_plan_match(row, plan_jsonl, errors):
    if not plan_jsonl:
        return
    if not os.path.exists(plan_jsonl):
        _err(errors, "plan_jsonl does not exist: %s" % plan_jsonl)
        return
    rows = list(iter_jsonl(plan_jsonl))
    source = row.get("source_plan") or {}
    if source.get("sha256") != sha256_file(plan_jsonl):
        _err(errors, "source_plan.sha256 does not match plan_jsonl")
    if source.get("row_count") != len(rows):
        _err(errors, "source_plan.row_count does not match plan_jsonl")


def validate(path, plan_jsonl=None):
    errors = []
    if not os.path.exists(SCHEMA):
        _err(errors, "schema missing: %s" % SCHEMA)
    try:
        row = read_json(path)
    except Exception as exc:
        return 0, ["bad JSON: %s" % exc]

    if not MANIFEST_ID.match(str(row.get("id") or "")):
        _err(errors, "id must be phase4-apply-readiness:<16 hex chars>")
    if row.get("phase") != "phase4_apply_readiness_manifest":
        _err(errors, "phase must be phase4_apply_readiness_manifest")
    if row.get("status") != "pre_apply_not_authorized":
        _err(errors, "status must be pre_apply_not_authorized")
    if row.get("generated_by") != "tools/build_phase4_apply_readiness_manifest.py":
        _err(errors, "generated_by must name the builder")

    source = row.get("source_plan") or {}
    if not SHA256.match(str(source.get("sha256") or "")):
        _err(errors, "source_plan.sha256 must be a sha256 hex digest")
    if not isinstance(source.get("row_count"), int) or source.get("row_count") <= 0:
        _err(errors, "source_plan.row_count must be positive")
    if source.get("plan_id_count") != source.get("row_count"):
        _err(errors, "source_plan.plan_id_count must equal row_count")
    if source.get("wbw_loc_count") != source.get("row_count"):
        _err(errors, "source_plan.wbw_loc_count must equal row_count")
    if source.get("quran_loc_count") != source.get("row_count"):
        _err(errors, "source_plan.quran_loc_count must equal row_count")
    if "/" in str(source.get("artifact") or "") or "\\" in str(source.get("artifact") or ""):
        _err(errors, "source_plan.artifact must be a basename, not a path")

    truth = row.get("truth_owners") or {}
    for key in ("hover_decision_plan", "live_wbw_lookup", "live_entries", "token_decision_ledger", "public_render"):
        if not str(truth.get(key) or "").strip():
            _err(errors, "truth_owners.%s must be non-empty" % key)

    validate_policy(row, errors)
    validate_public_boundary(row, errors)
    validate_required_gates(row, errors)

    rollback = row.get("rollback") or {}
    if rollback.get("required") is not True:
        _err(errors, "rollback.required must be true")
    if rollback.get("status") != "not_run":
        _err(errors, "rollback.status must be not_run")
    if rollback.get("strategy") != "append_only_revert_or_restore_backup":
        _err(errors, "rollback.strategy must be append_only_revert_or_restore_backup")

    sample_tokens = row.get("sample_tokens") or []
    if not sample_tokens:
        _err(errors, "sample_tokens must be non-empty")
    for idx, token in enumerate(sample_tokens, 1):
        if not str(token.get("quran_loc") or "").startswith("quran:"):
            _err(errors, "sample_tokens[%d].quran_loc is invalid" % idx)
        if not str(token.get("wbw_loc") or "").startswith("wbw:"):
            _err(errors, "sample_tokens[%d].wbw_loc is invalid" % idx)
        hover = token.get("public_hover") or {}
        if hover.get("src") != "qamus" or hover.get("kind") != "authored" or hover.get("lang") != "en":
            _err(errors, "sample_tokens[%d].public_hover must be source-clean" % idx)

    abort_conditions = row.get("abort_conditions") or []
    if len(abort_conditions) < 6:
        _err(errors, "abort_conditions must include the future apply stop rules")
    leaks = manifest_text_leaks(row)
    if leaks:
        _err(errors, "manifest contains forbidden public/private label %r" % leaks[0])
    validate_plan_match(row, plan_jsonl, errors)
    return 1, errors


def sample_plan_row():
    return {
        "id": "phase4-hover-decision-plan:22_18_17:c0ffee12",
        "phase": "phase4_hover_decision_plan",
        "source_phase": "phase4_two_vote_reconciled",
        "source_certified_id": "phase4-two-vote:queue_parse_c0ffee12",
        "source_certified_ids": ["phase4-two-vote:queue_parse_c0ffee12"],
        "status": "planned_not_applied",
        "parse_id": "parse:c0ffee12",
        "identity": {"quran_loc": "quran:22:18:17", "wbw_loc": "wbw:22:18:17", "parse_id": "parse:c0ffee12", "surface_sample": "وَٱلشَّجَرُ"},
        "public_hover": {"gloss": "and + the trees", "src": "qamus", "kind": "authored", "lang": "en"},
        "token_decision_preview": {"loc": "22:18:17", "gloss": "and + the trees", "src": "qamus", "kind": "authored", "lang": "en"},
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
    import build_phase4_apply_readiness_manifest as builder

    with tempfile.TemporaryDirectory(prefix="phase4-apply-readiness-validate-") as td:
        plan = os.path.join(td, "plan.jsonl")
        manifest = os.path.join(td, "manifest.json")
        write_jsonl(plan, [sample_plan_row()])
        builder.build_manifest(plan, manifest)
        count, errors = validate(manifest, plan)
        if count != 1 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
        bad = read_json(manifest)
        bad["apply_policy"]["apply_authorized"] = True
        bad_path = os.path.join(td, "bad.json")
        write_json(bad_path, bad)
        _count, errors = validate(bad_path, plan)
        if not any("apply_policy.apply_authorized must be false" in err for err in errors):
            print("SELF-TEST FAIL: expected apply_authorized rejection")
            return 1
    print("PASS — Phase 4 apply-readiness manifest validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", nargs="?")
    parser.add_argument("--plan-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.manifest_json:
        parser.error("manifest_json is required unless --self-test is used")
    count, errors = validate(args.manifest_json, args.plan_jsonl)
    print("checked %d Phase 4 apply-readiness manifest" % count)
    if errors:
        print("FAIL")
        for err in errors:
            print("- %s" % err)
        raise SystemExit(1)
    print("PASS — Phase 4 apply-readiness manifest is source-only and non-mutating")


if __name__ == "__main__":
    main()
