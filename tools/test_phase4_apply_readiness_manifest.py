#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for the Phase 4 pre-apply readiness manifest."""
import importlib.util
import io
import json
import os
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_tool(name):
    path = ROOT / "tools" / ("%s.py" % name)
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, row):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(row, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def plan_row():
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


def main():
    builder = load_tool("build_phase4_apply_readiness_manifest")
    validator = load_tool("validate_phase4_apply_readiness_manifest")
    with tempfile.TemporaryDirectory(prefix="phase4-apply-readiness-") as td:
        plan_path = os.path.join(td, "hover-decision-plan.jsonl")
        manifest_path = os.path.join(td, "apply-readiness.json")
        write_jsonl(plan_path, [plan_row()])

        manifest = builder.build_manifest(plan_path, manifest_path)
        assert manifest["phase"] == "phase4_apply_readiness_manifest"
        assert manifest["status"] == "pre_apply_not_authorized"
        assert manifest["source_plan"]["row_count"] == 1
        assert manifest["apply_policy"]["apply_authorized"] is False
        assert manifest["apply_policy"]["live_mutation_allowed"] is False
        assert manifest["apply_policy"]["closure_claim_allowed"] is False
        assert manifest["required_gates"]["append_only_ledger"]["required"] is True
        assert manifest["required_gates"]["backup"]["required"] is True
        assert manifest["required_gates"]["rebuild"]["required"] is True
        assert manifest["required_gates"]["health_check"]["required"] is True
        assert manifest["required_gates"]["targeted_public_readback"]["required"] is True
        assert manifest["required_gates"]["public_boundary_scan"]["required"] is True
        assert manifest["rollback"]["required"] is True
        assert manifest["sample_tokens"][0]["wbw_loc"] == "wbw:22:18:17"

        written = read_json(manifest_path)
        count, errors = validator.validate(manifest_path, plan_path)
        assert count == 1, errors
        assert not errors, errors
        assert written["source_plan"]["sha256"] == manifest["source_plan"]["sha256"]

        bad = dict(written)
        bad["apply_policy"] = dict(written["apply_policy"])
        bad["apply_policy"]["apply_authorized"] = True
        bad_path = os.path.join(td, "bad-apply.json")
        write_json(bad_path, bad)
        _count, errors = validator.validate(bad_path, plan_path)
        assert any("apply_policy.apply_authorized must be false" in err for err in errors), errors

        bad = dict(written)
        bad["required_gates"] = dict(written["required_gates"])
        bad["required_gates"]["backup"] = {"required": False, "status": "not_required"}
        bad_path = os.path.join(td, "bad-gate.json")
        write_json(bad_path, bad)
        _count, errors = validator.validate(bad_path, plan_path)
        assert any("required_gates.backup.required must be true" in err for err in errors), errors

        bad = dict(written)
        bad["truth_owners"] = dict(written["truth_owners"])
        bad["truth_owners"]["live_wbw_lookup"] = "/srv/private/live/wbw-lookup.json"
        bad_path = os.path.join(td, "bad-path.json")
        write_json(bad_path, bad)
        _count, errors = validator.validate(bad_path, plan_path)
        assert any("manifest contains forbidden public/private label" in err for err in errors), errors

    print("Phase 4 apply-readiness manifest self-test OK")


if __name__ == "__main__":
    main()
