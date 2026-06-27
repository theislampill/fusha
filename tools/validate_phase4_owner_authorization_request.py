#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a source-only Phase 4 owner authorization request."""
import argparse
import hashlib
import io
import json
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-owner-authorization-request.schema.json")
REQUEST_ID = re.compile(r"^phase4-owner-authorization-request:[0-9a-f]{16}$")
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
FALSE_POLICY_FIELDS = (
    "apply_allowed",
    "live_mutation_allowed",
    "wbw_rebuild_allowed",
    "service_restart_allowed",
    "mirror_sync_allowed",
    "closure_claim_allowed",
)


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


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


def leaks(row):
    text = json.dumps(row, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def _err(errors, msg):
    errors.append(msg)


def validate_source_artifacts(row, manifest_json, draft_ledger_jsonl, errors):
    source = row.get("source_artifacts") or {}
    manifest = source.get("apply_readiness_manifest") or {}
    draft = source.get("draft_token_decision_ledger") or {}
    if "/" in str(manifest.get("artifact") or "") or "\\" in str(manifest.get("artifact") or ""):
        _err(errors, "source_artifacts.apply_readiness_manifest.artifact must be a basename")
    if "/" in str(draft.get("artifact") or "") or "\\" in str(draft.get("artifact") or ""):
        _err(errors, "source_artifacts.draft_token_decision_ledger.artifact must be a basename")
    if not SHA256.match(str(manifest.get("sha256") or "")):
        _err(errors, "source_artifacts.apply_readiness_manifest.sha256 must be sha256")
    if not SHA256.match(str(draft.get("sha256") or "")):
        _err(errors, "source_artifacts.draft_token_decision_ledger.sha256 must be sha256")
    if manifest.get("status") != "pre_apply_not_authorized":
        _err(errors, "source_artifacts.apply_readiness_manifest.status must be pre_apply_not_authorized")
    if manifest_json:
        if not os.path.exists(manifest_json):
            _err(errors, "manifest_json missing: %s" % manifest_json)
        else:
            manifest_row = read_json(manifest_json)
            if manifest.get("sha256") != sha256_file(manifest_json):
                _err(errors, "apply_readiness_manifest sha256 mismatch")
            if manifest.get("id") != manifest_row.get("id"):
                _err(errors, "apply_readiness_manifest id mismatch")
    if draft_ledger_jsonl:
        if not os.path.exists(draft_ledger_jsonl):
            _err(errors, "draft_ledger_jsonl missing: %s" % draft_ledger_jsonl)
        else:
            rows = list(iter_jsonl(draft_ledger_jsonl))
            if draft.get("sha256") != sha256_file(draft_ledger_jsonl):
                _err(errors, "draft_token_decision_ledger sha256 mismatch")
            if draft.get("row_count") != len(rows):
                _err(errors, "draft_token_decision_ledger row_count mismatch")
            decision_ids = {row.get("id") for row in rows if row.get("id")}
            quran_locs = {(row.get("identity") or {}).get("quran_loc") for row in rows if (row.get("identity") or {}).get("quran_loc")}
            wbw_locs = {(row.get("identity") or {}).get("wbw_loc") for row in rows if (row.get("identity") or {}).get("wbw_loc")}
            if draft.get("decision_id_count") != len(decision_ids):
                _err(errors, "draft_token_decision_ledger decision_id_count mismatch")
            if draft.get("quran_loc_count") != len(quran_locs):
                _err(errors, "draft_token_decision_ledger quran_loc_count mismatch")
            if draft.get("wbw_loc_count") != len(wbw_locs):
                _err(errors, "draft_token_decision_ledger wbw_loc_count mismatch")


def validate_owner_authorization(row, errors):
    owner = row.get("owner_authorization") or {}
    if owner.get("required") is not True:
        _err(errors, "owner_authorization.required must be true")
    if owner.get("status") != "not_provided":
        _err(errors, "owner_authorization.status must be not_provided")
    if owner.get("authorized_by") is not None:
        _err(errors, "owner_authorization.authorized_by must be null")
    if owner.get("authorized_at") is not None:
        _err(errors, "owner_authorization.authorized_at must be null")
    if owner.get("authorized_scope") != "none":
        _err(errors, "owner_authorization.authorized_scope must be none")


def validate_policy(row, errors):
    policy = row.get("apply_policy") or {}
    if policy.get("source_only") is not True:
        _err(errors, "apply_policy.source_only must be true")
    if policy.get("owner_authorization_required") is not True:
        _err(errors, "apply_policy.owner_authorization_required must be true")
    for field in FALSE_POLICY_FIELDS:
        if policy.get(field) is not False:
            _err(errors, "apply_policy.%s must be false" % field)


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


def validate_samples(row, errors):
    samples = row.get("sample_decisions") or []
    if not samples:
        _err(errors, "sample_decisions must be non-empty")
    for idx, sample in enumerate(samples, 1):
        identity = sample.get("identity") or {}
        token = sample.get("token_decision") or {}
        if not str(identity.get("quran_loc") or "").startswith("quran:"):
            _err(errors, "sample_decisions[%d].identity.quran_loc is invalid" % idx)
        if not str(identity.get("wbw_loc") or "").startswith("wbw:"):
            _err(errors, "sample_decisions[%d].identity.wbw_loc is invalid" % idx)
        if token.get("src") != "qamus" or token.get("kind") != "authored" or token.get("lang") != "en":
            _err(errors, "sample_decisions[%d].token_decision must be source-clean" % idx)


def validate_excluded_tranche_rows(row, manifest_json, errors):
    excluded = row.get("excluded_tranche_rows")
    manifest_excluded = None
    if manifest_json and os.path.exists(manifest_json):
        manifest_row = read_json(manifest_json)
        manifest_excluded = manifest_row.get("excluded_tranche_rows")
    if manifest_excluded and excluded is None:
        _err(errors, "excluded_tranche_rows must be copied from apply-readiness manifest")
        return
    if excluded is None:
        return
    if not isinstance(excluded, dict):
        _err(errors, "excluded_tranche_rows must be an object")
        return
    if manifest_json and os.path.exists(manifest_json) and excluded != manifest_excluded:
        _err(errors, "excluded_tranche_rows must match apply-readiness manifest")

    source = excluded.get("source_tranche") or {}
    if "/" in str(source.get("artifact") or "") or "\\" in str(source.get("artifact") or ""):
        _err(errors, "excluded_tranche_rows.source_tranche.artifact must be a basename")
    if not SHA256.match(str(source.get("sha256") or "")):
        _err(errors, "excluded_tranche_rows.source_tranche.sha256 must be sha256")
    if not isinstance(source.get("row_count"), int) or source.get("row_count") <= 0:
        _err(errors, "excluded_tranche_rows.source_tranche.row_count must be positive")

    excluded_count = excluded.get("excluded_count")
    if not isinstance(excluded_count, int) or excluded_count < 0:
        _err(errors, "excluded_tranche_rows.excluded_count must be a non-negative integer")
        excluded_count = 0
    by_lane = excluded.get("excluded_by_lane") or {}
    by_gate = excluded.get("excluded_by_gate") or {}
    if not all(isinstance(value, int) for value in by_lane.values()):
        _err(errors, "excluded_tranche_rows.excluded_by_lane values must be integers")
    elif sum(by_lane.values()) != excluded_count:
        _err(errors, "excluded_tranche_rows.excluded_by_lane must sum to excluded_count")
    if not all(isinstance(value, int) for value in by_gate.values()):
        _err(errors, "excluded_tranche_rows.excluded_by_gate values must be integers")
    elif sum(by_gate.values()) != excluded_count:
        _err(errors, "excluded_tranche_rows.excluded_by_gate must sum to excluded_count")

    sample_excluded = excluded.get("sample_excluded") or []
    if excluded_count and not sample_excluded:
        _err(errors, "excluded_tranche_rows.sample_excluded must be non-empty when excluded_count is positive")
    for idx, sample in enumerate(sample_excluded, 1):
        if not str(sample.get("parse_id") or "").startswith("parse:"):
            _err(errors, "excluded_tranche_rows.sample_excluded[%d].parse_id is invalid" % idx)
        if not sample.get("quran_locs"):
            _err(errors, "excluded_tranche_rows.sample_excluded[%d].quran_locs must be non-empty" % idx)
        if not sample.get("wbw_locs"):
            _err(errors, "excluded_tranche_rows.sample_excluded[%d].wbw_locs must be non-empty" % idx)
        if not str(sample.get("lane") or "").strip():
            _err(errors, "excluded_tranche_rows.sample_excluded[%d].lane must be non-empty" % idx)
        if not str(sample.get("required_gate") or "").strip():
            _err(errors, "excluded_tranche_rows.sample_excluded[%d].required_gate must be non-empty" % idx)
        if not str(sample.get("recommended_action") or "").strip():
            _err(errors, "excluded_tranche_rows.sample_excluded[%d].recommended_action must be non-empty" % idx)


def validate(path, manifest_json=None, draft_ledger_jsonl=None):
    errors = []
    if not os.path.exists(SCHEMA):
        _err(errors, "schema missing: %s" % SCHEMA)
    try:
        row = read_json(path)
    except Exception as exc:
        return 0, ["bad JSON: %s" % exc]
    if not REQUEST_ID.match(str(row.get("id") or "")):
        _err(errors, "id must be phase4-owner-authorization-request:<16 hex chars>")
    if row.get("phase") != "phase4_owner_authorization_request":
        _err(errors, "phase must be phase4_owner_authorization_request")
    if row.get("status") != "owner_review_required_not_authorized":
        _err(errors, "status must be owner_review_required_not_authorized")
    if row.get("generated_by") != "tools/build_phase4_owner_authorization_request.py":
        _err(errors, "generated_by must name the builder")
    validate_source_artifacts(row, manifest_json, draft_ledger_jsonl, errors)
    validate_owner_authorization(row, errors)
    validate_policy(row, errors)
    validate_public_boundary(row, errors)
    validate_samples(row, errors)
    validate_excluded_tranche_rows(row, manifest_json, errors)
    if len(row.get("required_before_live_apply") or []) < 8:
        _err(errors, "required_before_live_apply must list all future apply gates")
    found = leaks(row)
    if found:
        _err(errors, "request contains forbidden public/private label %r" % found[0])
    return 1, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_json")
    parser.add_argument("--manifest-json")
    parser.add_argument("--draft-ledger-jsonl")
    args = parser.parse_args()
    count, errors = validate(args.request_json, args.manifest_json, args.draft_ledger_jsonl)
    print("checked %d Phase 4 owner authorization request" % count)
    if errors:
        print("FAIL")
        for err in errors:
            print("- %s" % err)
        raise SystemExit(1)
    print("PASS — Phase 4 owner authorization request is source-only and not authorized")


if __name__ == "__main__":
    main()
