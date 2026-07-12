#!/usr/bin/env python3
"""Red-first tests for the T3/T2 tier due-process writer."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import tier_due_process as subject  # noqa: E402


def current(rows: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        result[row["fact_id"]] = row
    return result


class DeterministicOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = subject.load_inputs(ROOT / ".lane-inputs")
        cls.morphology = subject.load_morphology()
        cls.surfaces = subject.load_location_surfaces()

    def test_all_61_authoritative_host_verdicts_pass_the_winning_host_check(self) -> None:
        checks = [
            subject.deterministic_winning_host_check(
                verdict, self.morphology, self.surfaces[verdict["canonical_location"]]
            )
            for verdict in self.inputs["dh_verdicts"]
            if verdict["verdict"] in {"t3_host_a", "t3_host_b"}
        ]
        self.assertEqual(61, len(checks))
        self.assertTrue(all(check["passed"] for check in checks))
        self.assertEqual(
            61,
            sum(check["method"] in {"documented_form", "root_derivation", "noun_convention"}
                for check in checks),
        )

    def test_unrelated_winning_host_fails_closed(self) -> None:
        verdict = copy.deepcopy(self.inputs["dh_verdicts"][0])
        verdict["chosen_host_id"] = "e0eccd6b35ed"
        verdict["chosen_host_headword"] = "بَال"
        verdict["host_a"] = {
            "id": "e0eccd6b35ed", "headword": "بَال", "root": "ب ا ل", "section": "noun"
        }
        result = subject.deterministic_winning_host_check(
            verdict, self.morphology, self.surfaces[verdict["canonical_location"]]
        )
        self.assertFalse(result["passed"])
        self.assertEqual("t4_packet_deterministic_fail", result["annotation"])


class EndToEndTests(unittest.TestCase):
    def test_double_run_is_identical_and_arithmetic_is_exact(self) -> None:
        first = subject.build(ROOT / ".lane-inputs")
        second = subject.build(ROOT / ".lane-inputs")
        self.assertEqual(first.output_bytes(), second.output_bytes())
        self.assertEqual(
            {"t3_host_a": 51, "t3_host_b": 10, "t4_packet": 5,
             "deterministic_pass": 61, "deterministic_fail": 0, "lillahi_t2": 6},
            first.report["gate_counts"],
        )
        self.assertEqual(
            [3669, 3765], first.report["ledger_arithmetic"]["rebind_cert"]["physical_rows"]
        )
        self.assertEqual(
            {"certified": 1234, "rejected": 10, "review_required": 14},
            first.report["ledger_arithmetic"]["rebind_cert"]["current_state_counts_after"],
        )
        self.assertEqual(
            [2974, 2998], first.report["ledger_arithmetic"]["funcword_cert"]["physical_rows"]
        )
        self.assertEqual(
            {"certified": 894, "rejected": 6, "review_required": 149},
            first.report["ledger_arithmetic"]["funcword_cert"]["current_state_counts_after"],
        )

    def test_lifecycle_shapes_preserve_losing_votes_and_t4_annotations(self) -> None:
        built = subject.build(ROOT / ".lane-inputs")
        rebind_current = current(built.rebind_rows)
        funcword_current = current(built.funcword_rows)

        rebind_states = Counter(row["certification_state"] for row in rebind_current.values())
        funcword_states = Counter(row["certification_state"] for row in funcword_current.values())
        self.assertEqual(Counter(certified=1234, review_required=14, rejected=10), rebind_states)
        self.assertEqual(Counter(certified=894, review_required=149, rejected=6), funcword_states)

        t4_rows = [
            row for row in rebind_current.values()
            if any(item.get("annotation") == "t4_packet" for item in row["exceptions"])
        ]
        self.assertEqual(5, len(t4_rows))
        self.assertTrue(all(row["certification_state"] == "review_required" for row in t4_rows))

        lillahi = [
            row for row in funcword_current.values()
            if row["certification_state"] == "certified"
            and any(item.get("t2_normalized") is True for item in row["exceptions"])
            and row["candidate_or_value"]["value"].get("taxonomy_category") == "preposition"
        ]
        self.assertEqual(6, len(lillahi))
        self.assertTrue(all("ssot_citation" in row["exceptions"][-1] for row in lillahi))

    def test_writer_outputs_only_two_ledgers_and_report(self) -> None:
        built = subject.build(ROOT / ".lane-inputs")
        self.assertEqual(
            {
                "qamus/indexes/largelexicon/fact-ledger/rebind-cert/ledger.jsonl",
                "qamus/indexes/largelexicon/fact-ledger/funcword-cert/ledger.jsonl",
                "qamus/indexes/largelexicon/fact-ledger/tier-due-process.report.json",
            },
            set(built.output_bytes()),
        )
        self.assertEqual("byte_stable", built.report["protected_surface_assertion"]["observed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
