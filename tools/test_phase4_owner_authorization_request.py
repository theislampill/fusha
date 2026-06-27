#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for source-only Phase 4 owner authorization requests."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_SAMPLE = os.path.join(ROOT, "qamus", "examples", "phase4_hover_decision_plan.sample.jsonl")
MANIFEST_BUILDER = os.path.join(ROOT, "tools", "build_phase4_apply_readiness_manifest.py")
DRAFT_BUILDER = os.path.join(ROOT, "tools", "build_phase4_draft_token_decision_ledger.py")
BUILDER = os.path.join(ROOT, "tools", "build_phase4_owner_authorization_request.py")
VALIDATOR = os.path.join(ROOT, "tools", "validate_phase4_owner_authorization_request.py")
SAMPLE_OUT = os.path.join(ROOT, "qamus", "examples", "phase4_owner_authorization_request.sample.json")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", env=env, capture_output=True)


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, row):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(row, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def main():
    assert os.path.exists(MANIFEST_BUILDER), "apply-readiness builder missing"
    assert os.path.exists(DRAFT_BUILDER), "draft ledger builder missing"
    assert os.path.exists(BUILDER), "owner authorization request builder missing"
    assert os.path.exists(VALIDATOR), "owner authorization request validator missing"
    manifest_builder = load_module(MANIFEST_BUILDER, "phase4_apply_readiness_manifest_builder")
    draft_builder = load_module(DRAFT_BUILDER, "phase4_draft_token_decision_builder")
    request_builder = load_module(BUILDER, "phase4_owner_authorization_request_builder")
    validator = load_module(VALIDATOR, "phase4_owner_authorization_request_validator")

    with tempfile.TemporaryDirectory(prefix="phase4-owner-auth-test-") as td:
        manifest_path = os.path.join(td, "apply-readiness-manifest.json")
        draft_path = os.path.join(td, "draft-token-decision-ledger.jsonl")
        request_path = os.path.join(td, "owner-authorization-request.json")
        manifest_builder.build_manifest(PLAN_SAMPLE, manifest_path)
        draft_builder.build_draft_ledger(PLAN_SAMPLE, draft_path)

        request = request_builder.build_request(manifest_path, draft_path, request_path)
        assert request["phase"] == "phase4_owner_authorization_request"
        assert request["status"] == "owner_review_required_not_authorized"
        assert request["owner_authorization"]["required"] is True
        assert request["owner_authorization"]["status"] == "not_provided"
        assert request["owner_authorization"]["authorized_by"] is None
        assert request["owner_authorization"]["authorized_at"] is None
        assert request["apply_policy"]["apply_allowed"] is False
        assert request["apply_policy"]["live_mutation_allowed"] is False
        assert request["apply_policy"]["closure_claim_allowed"] is False
        assert request["source_artifacts"]["apply_readiness_manifest"]["status"] == "pre_apply_not_authorized"
        assert request["source_artifacts"]["draft_token_decision_ledger"]["row_count"] == 2
        assert request["public_boundary"]["src"] == "qamus"
        assert request["public_boundary"]["kind"] == "authored"
        assert request["public_boundary"]["lang"] == "en"
        assert request["sample_decisions"][0]["token_decision"]["src"] == "qamus"
        assert request["sample_decisions"][0]["token_decision"]["kind"] == "authored"
        assert request["sample_decisions"][0]["token_decision"]["lang"] == "en"

        count, errors = validator.validate(request_path, manifest_path, draft_path)
        assert count == 1, errors
        assert not errors, errors

        excluded_manifest_path = os.path.join(td, "apply-readiness-with-exclusion.json")
        tranche_path = os.path.join(td, "source-tranche.jsonl")
        excluded_request_path = os.path.join(td, "owner-request-with-exclusion.json")
        blocked = {
            "id": "phase4-tranche:queue_parse_333333333333333333333333",
            "parse_id": "parse:333333333333333333333333",
            "identity": {
                "quran_locs": ["quran:86:14:1"],
                "wbw_locs": ["wbw:86:14:1"],
                "parse_id": "parse:333333333333333333333333",
                "surface_sample": "وَمَا",
            },
            "lane": "quarantine_collision",
            "required_gate": "human_review_required",
            "recommended_action": "quarantine until candidate collision is resolved by exact-token nahw/sarf review",
        }
        manifest_builder.write_jsonl(tranche_path, [blocked])
        excluded_manifest = manifest_builder.build_manifest(PLAN_SAMPLE, excluded_manifest_path, source_tranche_jsonl=tranche_path)
        request = request_builder.build_request(excluded_manifest_path, draft_path, excluded_request_path)
        assert request["excluded_tranche_rows"] == excluded_manifest["excluded_tranche_rows"]
        assert request["excluded_tranche_rows"]["excluded_count"] == 1
        count, errors = validator.validate(excluded_request_path, excluded_manifest_path, draft_path)
        assert count == 1, errors
        assert not errors, errors

        bad = read_json(excluded_request_path)
        del bad["excluded_tranche_rows"]
        bad_path = os.path.join(td, "bad-missing-excluded.json")
        write_json(bad_path, bad)
        _count, errors = validator.validate(bad_path, excluded_manifest_path, draft_path)
        assert any("excluded_tranche_rows must be copied" in err for err in errors), errors

        bad = read_json(request_path)
        bad["owner_authorization"]["status"] = "approved"
        bad["apply_policy"]["apply_allowed"] = True
        bad_path = os.path.join(td, "bad-approved.json")
        write_json(bad_path, bad)
        _count, errors = validator.validate(bad_path, manifest_path, draft_path)
        assert any("owner_authorization.status must be not_provided" in err for err in errors), errors
        assert any("apply_policy.apply_allowed must be false" in err for err in errors), errors

        bad = read_json(request_path)
        bad["sample_decisions"][0]["token_decision"]["gloss"] = "copied from QAC"
        bad_path = os.path.join(td, "bad-leak.json")
        write_json(bad_path, bad)
        _count, errors = validator.validate(bad_path, manifest_path, draft_path)
        assert any("forbidden public/private label" in err for err in errors), errors

    built = run([sys.executable, BUILDER, "--manifest-json", manifest_path, "--draft-ledger-jsonl", draft_path, "--out-json", SAMPLE_OUT])
    assert built.returncode != 0, "temp paths must not be used after cleanup"

    with tempfile.TemporaryDirectory(prefix="phase4-owner-auth-sample-") as td:
        manifest_path = os.path.join(td, "apply-readiness-manifest.json")
        draft_path = os.path.join(td, "draft-token-decision-ledger.jsonl")
        manifest_builder.build_manifest(PLAN_SAMPLE, manifest_path)
        draft_builder.build_draft_ledger(PLAN_SAMPLE, draft_path)
        built = run([sys.executable, BUILDER, "--manifest-json", manifest_path, "--draft-ledger-jsonl", draft_path, "--out-json", SAMPLE_OUT])
        assert built.returncode == 0, built.stderr or built.stdout
        checked = run([sys.executable, VALIDATOR, SAMPLE_OUT, "--manifest-json", manifest_path, "--draft-ledger-jsonl", draft_path])
        assert checked.returncode == 0, checked.stderr or checked.stdout

    print("Phase 4 owner authorization request self-test OK")


if __name__ == "__main__":
    main()
