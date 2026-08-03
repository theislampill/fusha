#!/usr/bin/env python3
"""Focused regression tests for L1-L6 consumer-accounting truth."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import build_curriculum_absorption as absorption
import build_unit_dispositions as dispositions


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

EXPECTED_LEVEL_DENOMINATORS = {
    "L1": 39,
    "L2": 32,
    "L3": 37,
    "L4": 40,
    "L5": 40,
    "L6": 38,
}
EXPECTED_CANDIDATE_RUNTIME_UNITS = {
    "cu-definite-article-assimilation",
    "u-n07",
    "u-s01",
    "u-s03",
    "u-s04",
    "u-s05",
    "u-s08",
    "u-s09",
}


def _jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ConsumerTruthTests(unittest.TestCase):
    def test_readiness_separates_runtime_fixture_and_candidate_drill_evidence(self):
        ledger, _sections, _completeness, _queues, readiness = absorption.build(
            absorption.load()
        )

        self.assertEqual(readiness["source_lessons"], 226)
        self.assertEqual(
            readiness["lesson_denominators_by_level"], EXPECTED_LEVEL_DENOMINATORS
        )
        self.assertEqual(readiness["lessons_mapped_to_tutor_drills"], 0)
        self.assertEqual(
            readiness["lessons_indirectly_linked_to_runtime_tutor_drills"], 27
        )

        runtime = readiness["ordinary_tutor_runtime"]
        self.assertEqual(runtime["drill_key_rows"], 14)
        self.assertEqual(runtime["emittable_knowledge_components"], 7)
        self.assertEqual(runtime["indirectly_linked_lessons"], 27)
        self.assertEqual(runtime["explicit_canonical_unit_bindings"], 0)
        self.assertFalse(runtime["lesson_content_operationalized"])

        candidate = readiness["candidate_drill_packets"]
        self.assertEqual(candidate["rows"], 834)
        self.assertEqual(candidate["runtime_integrated"], 0)

        self.assertEqual(
            readiness["state_histogram"]["candidate_fixture_harness_exercised"],
            8,
        )
        self.assertNotIn("consumer_exercised", readiness["state_histogram"])
        self.assertEqual(
            sum(
                bool(row["runtime_tutor_evidence"]["indirect_lesson_link"])
                for row in ledger
            ),
            27,
        )

        for train in ("train_d", "train_e"):
            linkage = readiness["other_train_l1l6_linkage"][train]
            self.assertEqual(linkage["explicit_lesson_bindings"], 0)
            self.assertEqual(linkage["explicit_unit_bindings"], 0)

    def test_unit_dispositions_keep_runtime_unit_mapping_candidate_only(self):
        rows, meta = dispositions.build()
        mapped = {
            row["unit_id"]
            for row in rows
            if "candidate_runtime_behavioral_mapping" in row["states"]
        }

        self.assertEqual(mapped, EXPECTED_CANDIDATE_RUNTIME_UNITS)
        self.assertEqual(
            meta["state_participation"]["candidate_runtime_behavioral_mapping"],
            8,
        )
        self.assertEqual(meta["explicit_runtime_unit_bindings"], 0)
        for row in rows:
            if row["unit_id"] in EXPECTED_CANDIDATE_RUNTIME_UNITS:
                evidence = row["runtime_behavioral_evidence"]
                self.assertFalse(evidence["authoritative_unit_binding"])
                self.assertEqual(evidence["mapping_state"], "candidate_unproven")
            else:
                self.assertNotIn("runtime_behavioral_evidence", row)

    def test_sarf_crosswalk_derivational_count_tracks_executable_bank(self):
        rows = {
            row["row_id"]: row
            for row in _jsonl(BASE / "crosswalk" / "sarf-crosswalk.jsonl")
        }
        executable_rows = len(
            _jsonl(ROOT / "sarf" / "evals" / "derivational-template-carve-eval.jsonl")
        )

        self.assertEqual(executable_rows, 31)
        self.assertEqual(
            rows["xs-04"]["consumer_evidence_counts"][
                "derivational_template_carve_rows"
            ],
            executable_rows,
        )


if __name__ == "__main__":
    unittest.main()
