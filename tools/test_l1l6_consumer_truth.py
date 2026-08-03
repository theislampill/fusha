#!/usr/bin/env python3
"""Focused regression tests for L1-L6 consumer-accounting truth."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import build_curriculum_absorption as absorption
import build_unit_dispositions as dispositions
import validate_curriculum_l1l6 as validator


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
def _jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ConsumerTruthTests(unittest.TestCase):
    def test_readiness_separates_runtime_fixture_and_candidate_drill_evidence(self):
        ctx = absorption.load()
        expected_runtime = absorption.ordinary_tutor_runtime_truth(ctx)
        ledger, _sections, _completeness, _queues, readiness = absorption.build(ctx)

        self.assertEqual(readiness["source_lessons"], 226)
        self.assertEqual(
            readiness["lesson_denominators_by_level"], EXPECTED_LEVEL_DENOMINATORS
        )
        self.assertEqual(readiness["lessons_mapped_to_tutor_drills"], 0)
        self.assertEqual(
            readiness["lessons_indirectly_linked_to_runtime_tutor_drills"],
            expected_runtime["indirectly_linked_lessons"],
        )

        runtime = readiness["ordinary_tutor_runtime"]
        self.assertEqual(runtime["drill_key_rows"], expected_runtime["drill_key_rows"])
        self.assertEqual(
            runtime["emittable_knowledge_components"],
            expected_runtime["emittable_knowledge_components"],
        )
        self.assertEqual(
            runtime["indirectly_linked_lessons"],
            expected_runtime["indirectly_linked_lessons"],
        )
        self.assertEqual(runtime["explicit_canonical_unit_bindings"], 0)
        self.assertFalse(runtime["lesson_content_operationalized"])

        candidate = readiness["candidate_drill_packets"]
        drill_meta = json.loads(
            (BASE / "drills-candidates" / "drill-candidates.meta.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(candidate["rows"], drill_meta["rows"])
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
            expected_runtime["indirectly_linked_lessons"],
        )

        for train in ("train_d", "train_e"):
            linkage = readiness["other_train_l1l6_linkage"][train]
            self.assertEqual(linkage["explicit_lesson_bindings"], 0)
            self.assertEqual(linkage["explicit_unit_bindings"], 0)

    def test_unit_dispositions_do_not_infer_runtime_unit_bindings(self):
        rows, meta = dispositions.build()
        self.assertEqual(meta["explicit_runtime_unit_bindings"], 0)
        for row in rows:
            self.assertNotIn("candidate_runtime_behavioral_mapping", row["states"])
            self.assertNotIn("runtime_behavioral_evidence", row)

    def test_runtime_validator_accepts_future_internally_consistent_counts(self):
        derived = {
            "drill_key_rows": 15,
            "emittable_knowledge_components": 8,
            "indirectly_linked_lessons": 28,
            "explicit_lesson_bindings": 0,
            "explicit_canonical_unit_bindings": 0,
        }
        readiness = {
            "lessons_mapped_to_tutor_drills": 0,
            "lessons_indirectly_linked_to_runtime_tutor_drills": 28,
            "ordinary_tutor_runtime": dict(derived),
            "candidate_drill_packets": {"rows": 900, "runtime_integrated": 0},
        }
        errors = []

        validator.check_runtime_truth_consistency(
            readiness,
            derived,
            {"rows": 900, "runtime_integrated": 0},
            errors,
        )

        self.assertEqual(errors, [])

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
