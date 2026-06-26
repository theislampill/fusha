#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for Phase 4 gloss adjudication response reconciliation."""
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


def request_row():
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


def response_row():
    return {
        "id": "phase4-gloss-adjudication-response:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "phase": "phase4_gloss_adjudication_response",
        "source_adjudication_request_id": "phase4-gloss-adjudication:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
        "identity": {
            "quran_locs": ["quran:2:178:22"],
            "wbw_locs": ["wbw:2:178:22"],
            "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
            "surface_sample": "بِٱلْمَعْرُوفِ",
        },
        "decision": "select",
        "selected_concise_authored_gloss": "in a recognized manner",
        "selection_source": "candidate",
        "adjudication_reason": "Preserves the bāʾ manner relation without over-specifying the legal context.",
        "safe_scope_after_adjudication": "token_only",
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


def main():
    validator = load_tool("validate_phase4_gloss_adjudication_responses")
    reconciler = load_tool("reconcile_phase4_gloss_adjudication_responses")
    with tempfile.TemporaryDirectory(prefix="phase4-gloss-adjudication-response-") as td:
        requests = os.path.join(td, "requests.jsonl")
        responses = os.path.join(td, "responses.jsonl")
        certified = os.path.join(td, "certified.jsonl")
        unresolved = os.path.join(td, "unresolved.jsonl")
        write_jsonl(requests, [request_row()])
        write_jsonl(responses, [response_row()])

        count, errors = validator.validate(responses, request_path=requests)
        assert count == 1, errors
        assert not errors, errors

        summary = reconciler.reconcile_files(requests, responses, certified, unresolved)
        assert summary["certified_rows"] == 1, summary
        assert summary["unresolved_rows"] == 0, summary
        assert summary["apply_allowed"] is False
        rows = read_jsonl(certified)
        assert rows[0]["phase"] == "phase4_gloss_adjudication_reconciled"
        assert rows[0]["status"] == "certified_not_applied"
        assert rows[0]["public_hover"] == {"gloss": "in a recognized manner", "src": "qamus", "kind": "authored", "lang": "en"}
        assert rows[0]["identity"]["wbw_locs"] == ["wbw:2:178:22"]
        assert rows[0]["apply_policy"]["live_mutation_allowed"] is False

        bad = response_row()
        bad["selected_concise_authored_gloss"] = "QAC says in a fair way"
        write_jsonl(responses, [bad])
        count, errors = validator.validate(responses, request_path=requests)
        assert count == 1
        assert any("selected_concise_authored_gloss leaks forbidden label" in err for err in errors), errors

    print("Phase 4 gloss adjudication response reconciliation self-test OK")


if __name__ == "__main__":
    main()
