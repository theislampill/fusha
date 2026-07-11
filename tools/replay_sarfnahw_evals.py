#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replay the four RM-28 sarf/nahw eval-fixture contract groups."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(relpath):
    with (ROOT / relpath).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def replay_morphology():
    data = rows("sarf/evals/morphology-candidate-lattice.jsonl")
    require(len(data) == 7, "morphology lattice must contain 7 cases")
    require(len({row["id"] for row in data}) == len(data), "morphology ids must be unique")
    require(all(row.get("decision") == "pending" for row in data), "morphology cases must preserve pending")
    require(all(row.get("keep_ambiguity") is True for row in data), "morphology cases must preserve ambiguity")
    require(all(row.get("forbid_fabricated_root") is True for row in data), "fabricated roots must stay forbidden")
    require(all(row.get("expected_min_candidates", 0) >= 1 for row in data), "every morphology case needs a candidate")
    return len(data)


def replay_deploy_mechanics():
    data = rows("sarf/evals/combining-mark-byte-exact-eval.jsonl") + rows(
        "sarf/evals/surfacemap-wbw-absent-eval.jsonl"
    )
    require(len(data) == 4, "deploy-mechanics group must contain 4 cases")
    require(len({row["id"] for row in data}) == len(data), "deploy-mechanics ids must be unique")
    require(all(row.get("decision") and row.get("correct") and row.get("reason") for row in data),
            "deploy-mechanics cases need decision, correction, and reason")
    require({row["id"] for row in data} == {"CMBX-001", "CMBX-002", "SMAP-001", "SMAP-002"},
            "deploy-mechanics case set drifted")
    require(all(row.get("procedure_links") for row in data), "deploy-mechanics cases need procedure links")
    return len(data)


def replay_governor():
    data = rows("nahw/evals/governor-dependency-lattice.jsonl")
    by_id = {row["id"]: row for row in data}
    require(len(data) == 7 and len(by_id) == 7, "governor lattice must contain 7 unique cases")
    require(all(row.get("auto_safe_forbidden") is True for row in data), "governor cases must forbid auto-safe")
    require(by_id["GDL-001"].get("expected_decision") == "resolved", "visible ending control must resolve")
    require(by_id["GDL-002"].get("expected_decision") == "pending", "unvoweled control must stay pending")
    require(by_id["GDL-003"].get("pp_attachment") == "unresolved", "PP attachment must stay unresolved")
    require(by_id["GDL-004"].get("keep_idafa_ambiguity") is True, "idafa ambiguity must be preserved")
    return len(data)


def replay_wrong_reasoning():
    data = rows("nahw/evals/irab-right-answer-wrong-reason.jsonl")
    by_id = {row["id"]: row for row in data}
    require(len(data) == 6 and len(by_id) == 6, "wrong-reasoning group must contain 6 unique cases")
    require(all(row.get("gate") in {"auto_safe", "two_vote_required", "human_source_review_required"}
                for row in data), "wrong-reasoning gates must be known")
    for case_id in ("RWR-001", "RWR-002", "RWR-003", "RWR-004", "RWR-005"):
        require(by_id[case_id].get("right_answer_wrong_reason") is True, case_id + " must remain a trap")
        require(by_id[case_id].get("verdict") == "governor_not_justified", case_id + " must reject its governor")
    require(by_id["RWR-006"].get("right_answer_wrong_reason") is False, "RWR-006 must remain the justified control")
    require(by_id["RWR-006"].get("verdict") == "governor_justified", "RWR-006 governor must remain justified")
    return len(data)


REPLAYS = {
    "morphology": replay_morphology,
    "deploy-mechanics": replay_deploy_mechanics,
    "governor": replay_governor,
    "wrong-reasoning": replay_wrong_reasoning,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=sorted(REPLAYS))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    selected = sorted(REPLAYS) if args.self_test or not args.group else [args.group]
    total = sum(REPLAYS[name]() for name in selected)
    print("RM-28 EVAL REPLAY PASS — groups=%s rows=%d" % (",".join(selected), total))


if __name__ == "__main__":
    main()
