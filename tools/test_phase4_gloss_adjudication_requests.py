#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for Phase 4 gloss wording adjudication requests."""
import importlib.util
import io
import json
import os
import pathlib
import sys
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


def unresolved_row():
    return {
        "phase": "phase4_two_vote_unresolved",
        "source_request_id": "phase4-two-vote:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
        "identity": {
            "quran_locs": ["quran:2:178:22"],
            "wbw_locs": ["wbw:2:178:22"],
            "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
            "surface_sample": "بِٱلْمَعْرُوفِ",
        },
        "unresolved_reason": "gloss_wording_disagreement",
        "responses_seen": ["nahw-primary", "sarf-primary"],
        "vote_summaries": [
            {
                "lens": "sarf-primary",
                "decision": "approve",
                "gloss": "in a recognized manner",
                "reason_agreement_key": "preposition-governed-nominal-manner",
                "blocker_if_rejected": "",
            },
            {
                "lens": "nahw-primary",
                "decision": "approve",
                "gloss": "with recognized fairness",
                "reason_agreement_key": "preposition-governed-nominal-manner",
                "blocker_if_rejected": "",
            },
        ],
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
    builder = load_tool("build_phase4_gloss_adjudication_requests")
    validator = load_tool("validate_phase4_gloss_adjudication_requests")
    with tempfile.TemporaryDirectory(prefix="phase4-gloss-adjudication-") as td:
        unresolved = os.path.join(td, "unresolved.jsonl")
        out = os.path.join(td, "gloss-adjudication.jsonl")
        write_jsonl(unresolved, [unresolved_row()])
        summary = builder.build_requests(unresolved, out)
        assert summary["rows"] == 1, summary
        assert summary["apply_allowed"] is False
        assert summary["live_mutation_allowed"] is False
        assert summary["closure_claim_allowed"] is False

        count, errors = validator.validate(out)
        assert count == 1, errors
        assert not errors, errors
        row = read_jsonl(out)[0]
        assert row["id"] == "phase4-gloss-adjudication:queue_parse_e5e4e1aeb56a7fdd636257b0"
        assert row["phase"] == "phase4_gloss_adjudication_request"
        assert row["source_unresolved_reason"] == "gloss_wording_disagreement"
        assert row["identity"]["quran_locs"] == ["quran:2:178:22"]
        assert row["candidate_glosses"] == ["in a recognized manner", "with recognized fairness"]
        assert row["shared_reason_agreement_key"] == "preposition-governed-nominal-manner"
        assert row["allowed_next_step"] == "owner_or_scholar_gloss_adjudication_only"
        assert row["requested_output"]["selected_concise_authored_gloss"] == ""
        assert row["public_boundary"]["src"] == "qamus"
        assert row["public_boundary"]["kind"] == "authored"
        assert row["public_boundary"]["lang"] == "en"
        assert row["apply_policy"]["apply_allowed"] is False
        assert row["apply_policy"]["component_candidates_can_certify"] is False

        bad = dict(row)
        bad["candidate_glosses"] = ["QAC says with fairness", "with fairness"]
        write_jsonl(out, [bad])
        count, errors = validator.validate(out)
        assert count == 1
        assert any("candidate_gloss leaks forbidden label" in err for err in errors), errors

    print("Phase 4 gloss adjudication request self-test OK")


if __name__ == "__main__":
    main()
