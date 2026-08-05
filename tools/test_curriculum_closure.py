#!/usr/bin/env python3
"""Focused fail-closed tests for L1-L6 operationalization closure."""

from __future__ import annotations

import copy
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import curriculum_closure as closure
import build_unit_dispositions
import build_curriculum_absorption
import select_tranche
import validate_curriculum_l1l6


def dimension(name: str, satisfied: bool, **evidence) -> dict:
    return {
        "dimension": name,
        "satisfied": satisfied,
        "evidence": evidence,
    }


class CurriculumClosureTests(unittest.TestCase):
    def test_all_non_occurrence_dimensions_are_required(self):
        dimensions = [
            dimension("machine_execution", True),
            dimension("runtime_misconceptions", False, missing=["mc-2"]),
            dimension("error_fixtures", True),
            dimension("consumer_bindings", True),
            dimension("occurrence_grounding", True),
        ]

        result = closure.close_from_dimensions(dimensions)

        self.assertFalse(result["fully_operationalized"])
        self.assertEqual(result["incomplete_dimensions"], ["runtime_misconceptions"])

    def test_parked_occurrence_dimension_does_not_launder_other_gaps(self):
        dimensions = [
            dimension("machine_execution", True),
            dimension("runtime_misconceptions", True),
            dimension("error_fixtures", True),
            dimension("consumer_bindings", False, missing_lessons=["L2"]),
            {
                "dimension": "occurrence_grounding",
                "satisfied": True,
                "disposition": "parked",
                "state": "evidence_blocked",
            },
        ]

        result = closure.close_from_dimensions(dimensions)

        self.assertFalse(result["fully_operationalized"])
        self.assertEqual(result["incomplete_dimensions"], ["consumer_bindings"])

    def test_parked_occurrence_closure_has_an_honest_distinct_basis(self):
        dimensions = [
            dimension("machine_execution", True),
            dimension("runtime_misconceptions", True),
            dimension("error_fixtures", True),
            dimension("consumer_bindings", True),
            {
                "dimension": "occurrence_grounding",
                "satisfied": True,
                "disposition": "parked",
                "state": "evidence_blocked",
            },
        ]

        result = closure.close_from_dimensions(dimensions)

        self.assertTrue(result["fully_operationalized"])
        self.assertTrue(result["occurrence_grounding_parked"])
        self.assertTrue(
            result["fully_operationalized_basis"].startswith(
                "all_non_occurrence_dimensions_satisfied_"
                "occurrence_grounding_parked:sha256:"
            )
        )

    def test_empty_runtime_and_fixture_denominators_are_marked_vacuous(self):
        runtime = closure._runtime_dimension("u-none", [], [], set())
        fixtures = closure._error_fixture_dimension(
            "u-none", ["L-none"], [], []
        )

        self.assertTrue(runtime["satisfied_vacuously"])
        self.assertEqual(
            runtime["satisfaction_basis"],
            "vacuous_no_required_misconceptions",
        )
        self.assertTrue(fixtures["satisfied_vacuously"])
        self.assertEqual(
            fixtures["satisfaction_basis"],
            "vacuous_no_expected_error_rows",
        )

    def test_live_tranche_001_closes_only_five_narrow_units(self):
        report = closure.build()
        by_id = {row["unit_id"]: row for row in report["units"]}

        closed = {
            unit_id
            for unit_id, row in by_id.items()
            if row["fully_operationalized"]
        }
        self.assertEqual(
            closed,
            {
                "cu-definite-article-assimilation",
                "cu-grapheme-inventory-and-confusables",
                "cu-nunation-support-orthography",
                "cu-orthographic-connectivity-classes",
                "cu-short-vowel-diacritics-and-vocalization-state",
            },
        )
        self.assertEqual(
            by_id["u-s06"]["dimensions"]["runtime_misconceptions"]["covered"],
            65,
        )
        self.assertEqual(
            by_id["u-s06"]["dimensions"]["runtime_misconceptions"]["total"],
            141,
        )
        self.assertEqual(
            by_id["u-s01"]["dimensions"]["runtime_misconceptions"]["covered"],
            16,
        )
        self.assertEqual(
            by_id["u-n01"]["dimensions"]["runtime_misconceptions"]["covered"],
            92,
        )
        for unit_id in ("u-s06", "u-s01", "u-n01"):
            self.assertIn(
                "runtime_misconceptions",
                by_id[unit_id]["incomplete_dimensions"],
            )

    def test_unit_disposition_builder_consumes_closure_truth(self):
        rows, meta = build_unit_dispositions.build()
        closed = {
            row["unit_id"] for row in rows if row["fully_operationalized"]
        }

        self.assertEqual(len(closed), 5)
        self.assertEqual(meta["units_fully_operationalized"], 5)
        self.assertEqual(meta["units_partially_operationalized"], 3)
        self.assertEqual(
            meta["units_closed_with_parked_occurrence_grounding"], 0
        )
        self.assertGreater(meta["units_closed_with_vacuous_dimensions"], 0)
        self.assertEqual(meta["lessons_fully_operationalized"], 4)
        lesson_truth = closure.lesson_closure_truth(rows)
        self.assertEqual(
            lesson_truth["fully_operationalized_lesson_ids"],
            ["L1.M1.01", "L1.M1.02", "L1.M1.03", "L1.M1.07"],
        )

    def test_selector_preserves_tranche_001_membership_after_partial_closure(self):
        dispositions, _ = build_unit_dispositions.build()
        inputs = replace(
            select_tranche.load_inputs(),
            unit_dispositions=dispositions,
        )

        tranche, burndown = select_tranche.build_artifacts(inputs)

        self.assertEqual(
            [row["unit_id"] for row in tranche["units"]],
            list(closure.TRANCHE_001_UNIT_IDS),
        )
        self.assertEqual(tranche["closure"]["units_fully_operationalized"], 5)
        self.assertEqual(tranche["closure"]["units_still_partial"], 3)
        self.assertEqual(
            burndown["current_tranche"]["units_fully_operationalized"], 5
        )
        self.assertNotIn("baseline", burndown)
        self.assertNotIn("plan", burndown)
        self.assertEqual(
            burndown["current_state"]["lessons_by_disposition"],
            {
                "fully_operationalized": 4,
                "not_applicable_with_reason": 1,
                "open": 172,
                "partially_operationalized_real_consumer": 49,
            },
        )
        self.assertEqual(
            burndown["current_state"]["lessons_with_real_consumer_partial_evidence"],
            49,
        )
        self.assertEqual(
            burndown["current_state"]["units_by_disposition"],
            {
                "blocked": 0,
                "candidate_or_open": 118,
                "closed": 5,
                "real_consumer_partial": 43,
            },
        )
        self.assertEqual(
            burndown["current_state"]["unit_overlays"][
                "parked_occurrence_grounding"
            ],
            105,
        )
        self.assertEqual(
            burndown["current_tranche"]["fully_operationalized_lesson_ids"],
            ["L1.M1.01", "L1.M1.02", "L1.M1.03", "L1.M1.07"],
        )
        self.assertEqual(burndown["forecast"]["future_tranches_total"], 22)
        self.assertEqual(
            burndown["forecast"]["parked_occurrence_grounding_units"], 105
        )
        self.assertIn(
            "parking is not occurrence evidence",
            burndown["forecast"]["assumption"],
        )
        self.assertEqual(
            burndown["forecast"][
                "projected_total_fully_operationalized_lessons"
            ],
            225,
        )
        self.assertEqual(
            burndown["forecast"]["tranches"][0]["tranche_number"], 2
        )

    def test_absorption_builder_records_four_fully_closed_lessons(self):
        dispositions, _ = build_unit_dispositions.build()
        ledger, _, _, _, readiness = build_curriculum_absorption.build(
            build_curriculum_absorption.load(),
            unit_dispositions=dispositions,
        )
        by_lesson = {row["lesson_id"]: row for row in ledger}

        self.assertEqual(readiness["lessons_fully_operationalized"], 4)
        self.assertEqual(readiness["lessons_partially_operationalized"], 49)
        self.assertTrue(
            by_lesson["L1.M1.01"]["consumer_operationalization"][
                "fully_operationalized"
            ]
        )
        self.assertTrue(
            by_lesson["L1.M1.01"]["runtime_tutor_evidence"][
                "mapped_unit_closure_reached"
            ]
        )
        self.assertEqual(
            by_lesson["L1.M1.01"]["runtime_tutor_evidence"][
                "mapped_unit_closure_basis"
            ],
            "all_mapped_canonical_units_fully_operationalized",
        )
        self.assertNotIn(
            "lesson_content_fully_operationalized",
            by_lesson["L1.M1.01"]["runtime_tutor_evidence"],
        )
        self.assertFalse(
            by_lesson["L1.M1.04"]["consumer_operationalization"][
                "fully_operationalized"
            ]
        )

    def test_validator_independently_rejects_a_laundered_unit_closure(self):
        dispositions, _ = build_unit_dispositions.build()
        lesson_units = closure._jsonl(
            closure.BASE / "canonical" / "lesson-unit-map.jsonl"
        )
        errors = []
        _, closed_lessons = (
            validate_curriculum_l1l6.derive_operationalization_closure(
                dispositions, lesson_units, errors
            )
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(closed_lessons), 4)

        mutated = copy.deepcopy(dispositions)
        closed_row = next(
            row for row in mutated if row["fully_operationalized"]
        )
        closed_row["closure_dimensions"]["consumer_bindings"][
            "satisfied"
        ] = False
        errors = []
        validate_curriculum_l1l6.derive_operationalization_closure(
            mutated, lesson_units, errors
        )
        self.assertTrue(
            any("declared closure True != independent False" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
