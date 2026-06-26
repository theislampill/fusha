#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for Phase 4 certified hover decision planning."""
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


def read_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def apply_policy():
    return {
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
        "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
        "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
        "component_candidates_can_certify": False,
        "raw_surface_identity_allowed": False,
        "parse_key_primary_identity": False,
    }


def two_vote_certified():
    return {
        "phase": "phase4_two_vote_reconciled",
        "source_request_id": "phase4-two-vote:queue_parse_c0ffee12",
        "parse_id": "parse:c0ffee12",
        "identity": {
            "parse_id": "parse:c0ffee12",
            "quran_locs": ["quran:22:18:17"],
            "surface_sample": "وَٱلشَّجَرُ",
            "wbw_locs": ["wbw:22:18:17"],
        },
        "public_hover": {
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "vote_response_ids": [
            "phase4-two-vote-response:queue_parse_c0ffee12:sarf-primary",
            "phase4-two-vote-response:queue_parse_c0ffee12:nahw-primary",
        ],
        "reason_agreement_key": "conj-definite-noun-coordinated-list",
        "safe_scope_after_vote": "token_only",
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
        "apply_policy": apply_policy(),
        "component_candidates_used_as_certification": False,
        "status": "certified_not_applied",
    }


def gloss_adjudication_certified():
    return {
        "phase": "phase4_gloss_adjudication_reconciled",
        "source_adjudication_request_id": "phase4-gloss-adjudication:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "source_two_vote_request_id": "phase4-two-vote:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
        "identity": {
            "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
            "quran_locs": ["quran:2:178:22"],
            "surface_sample": "بِٱلْمَعْرُوفِ",
            "wbw_locs": ["wbw:2:178:22"],
        },
        "public_hover": {
            "gloss": "in a recognized manner",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "adjudication_response_id": "phase4-gloss-adjudication-response:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "selection_source": "candidate",
        "adjudication_reason": "Preserves the bāʾ manner relation without over-specifying context.",
        "reason_agreement_key": "preposition-governed-nominal-manner",
        "safe_scope_after_adjudication": "token_only",
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
        "apply_policy": apply_policy(),
        "status": "certified_not_applied",
    }


def main():
    builder = load_tool("build_phase4_hover_decision_plan")
    validator = load_tool("validate_phase4_hover_decision_plan")
    with tempfile.TemporaryDirectory(prefix="phase4-hover-decision-plan-") as td:
        certified = os.path.join(td, "certified.jsonl")
        plan = os.path.join(td, "plan.jsonl")
        write_jsonl(certified, [two_vote_certified(), gloss_adjudication_certified()])

        summary = builder.build_plan(certified, plan)
        assert summary["source_rows"] == 2, summary
        assert summary["planned_rows"] == 2, summary
        assert summary["apply_allowed"] is False
        assert summary["live_mutation_allowed"] is False
        assert summary["closure_claim_allowed"] is False

        count, errors = validator.validate(plan)
        assert count == 2, errors
        assert not errors, errors

        rows = read_jsonl(plan)
        by_wbw = {row["identity"]["wbw_loc"]: row for row in rows}
        tree = by_wbw["wbw:22:18:17"]
        assert tree["status"] == "planned_not_applied"
        assert tree["public_hover"] == {"gloss": "and + the trees", "src": "qamus", "kind": "authored", "lang": "en"}
        assert tree["token_decision_preview"] == {"loc": "22:18:17", "gloss": "and + the trees", "src": "qamus", "kind": "authored", "lang": "en"}
        assert tree["source_phase"] == "phase4_two_vote_reconciled"
        assert tree["safe_scope"] == "token_only"
        assert tree["apply_policy"]["append_only_ledger_required"] is True
        assert tree["apply_policy"]["requires_backup_rebuild_health_readback_before_apply"] is True
        assert tree["apply_policy"]["apply_allowed"] is False
        assert tree["apply_policy"]["parse_key_primary_identity"] is False

        manner = by_wbw["wbw:2:178:22"]
        assert manner["source_phase"] == "phase4_gloss_adjudication_reconciled"
        assert manner["token_decision_preview"]["loc"] == "2:178:22"

        bad = two_vote_certified()
        bad["public_hover"]["gloss"] = "QAC says and the trees"
        write_jsonl(certified, [bad])
        summary = builder.build_plan(certified, plan)
        assert summary["planned_rows"] == 1, summary
        count, errors = validator.validate(plan)
        assert count == 1
        assert any("public_hover leaks forbidden label" in err for err in errors), errors

    print("Phase 4 hover decision plan self-test OK")


if __name__ == "__main__":
    main()
