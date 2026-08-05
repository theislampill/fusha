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
            dimension("behavioral_coverage", True),
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
            dimension("behavioral_coverage", True),
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
            dimension("behavioral_coverage", True),
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
        behavioral = closure._behavioral_coverage_dimension(
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
        self.assertTrue(behavioral["satisfied_vacuously"])
        self.assertEqual(
            behavioral["satisfaction_basis"],
            "vacuous_no_expected_error_rows",
        )

    def test_error_fixture_trace_accepts_both_boolean_behavioral_states(self):
        queue_rows = [
            {"row_id": "q-false", "source": "L-test"},
            {"row_id": "q-true", "source": "L-test"},
        ]
        shared = {
            "selected_unit_links": ["u-test"],
            "outcome": "runner_loaded_fixture_only",
            "owning_runner": "tools/run_sarf_evals.py",
            "owning_skill_bank": "sarf/evals/tranche-001-error-fixtures-a.jsonl",
        }
        trace_rows = [
            {
                **shared,
                "source_queue_row_id": "q-false",
                "behaviorally_decided": False,
            },
            {
                **shared,
                "source_queue_row_id": "q-true",
                "behaviorally_decided": True,
            },
        ]

        result = closure._error_fixture_dimension(
            "u-test", ["L-test"], queue_rows, trace_rows
        )

        self.assertTrue(result["satisfied"])
        self.assertEqual(result["traced"], 2)
        self.assertEqual(result["missing_queue_row_ids"], [])

    def test_error_fixture_trace_rejects_missing_behavioral_state(self):
        result = closure._error_fixture_dimension(
            "u-test",
            ["L-test"],
            [{"row_id": "q-missing", "source": "L-test"}],
            [{
                "source_queue_row_id": "q-missing",
                "selected_unit_links": ["u-test"],
                "outcome": "runner_loaded_fixture_only",
                "owning_runner": "tools/run_sarf_evals.py",
                "owning_skill_bank": "sarf/evals/tranche-001-error-fixtures-a.jsonl",
            }],
        )

        self.assertFalse(result["satisfied"])
        self.assertEqual(result["missing_queue_row_ids"], ["q-missing"])

    def test_behavioral_coverage_is_a_separate_fail_closed_dimension(self):
        queue_rows = [
            {"row_id": "q-undecided", "source": "L-test"},
            {"row_id": "q-decided", "source": "L-test"},
        ]
        shared = {
            "selected_unit_links": ["u-test"],
            "outcome": "runner_loaded_fixture_only",
            "owning_runner": "tools/run_sarf_evals.py",
            "owning_skill_bank": "sarf/evals/tranche-001-error-fixtures-a.jsonl",
        }
        trace_rows = [
            {
                **shared,
                "source_queue_row_id": "q-undecided",
                "behaviorally_decided": False,
            },
            {
                **shared,
                "source_queue_row_id": "q-decided",
                "behaviorally_decided": True,
            },
        ]

        result = closure._behavioral_coverage_dimension(
            "u-test", ["L-test"], queue_rows, trace_rows
        )

        self.assertFalse(result["satisfied"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["decided"], 1)
        self.assertEqual(result["missing_queue_row_ids"], ["q-undecided"])

    def test_behavioral_coverage_is_required_for_unit_closure(self):
        dimensions = [
            dimension("machine_execution", True),
            dimension("runtime_misconceptions", True),
            dimension("error_fixtures", True),
            dimension("behavioral_coverage", False),
            dimension("consumer_bindings", True),
            dimension("occurrence_grounding", True),
        ]

        result = closure.close_from_dimensions(dimensions)

        self.assertFalse(result["fully_operationalized"])
        self.assertEqual(result["incomplete_dimensions"], ["behavioral_coverage"])

    def test_live_tranche_001_reopens_fixture_only_units_for_grading(self):
        report = closure.build()
        by_id = {row["unit_id"]: row for row in report["units"]}

        closed = {
            unit_id
            for unit_id, row in by_id.items()
            if row["fully_operationalized"]
        }
        self.assertEqual(closed, set())
        for row in by_id.values():
            behavioral = row["dimensions"]["behavioral_coverage"]
            self.assertEqual(behavioral["decided"], 0)
            self.assertGreater(behavioral["total"], 0)
            self.assertIn("behavioral_coverage", row["incomplete_dimensions"])
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

        self.assertEqual(len(closed), 0)
        self.assertEqual(meta["units_fully_operationalized"], 0)
        self.assertEqual(meta["units_partially_operationalized"], 8)
        self.assertEqual(
            meta["units_closed_with_parked_occurrence_grounding"], 0
        )
        self.assertEqual(meta["units_closed_with_vacuous_dimensions"], 0)
        self.assertEqual(meta["lessons_fully_operationalized"], 0)
        lesson_truth = closure.lesson_closure_truth(rows)
        self.assertEqual(lesson_truth["fully_operationalized_lesson_ids"], [])

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
        self.assertEqual(tranche["closure"]["units_fully_operationalized"], 0)
        self.assertEqual(tranche["closure"]["units_still_partial"], 8)
        self.assertEqual(
            burndown["current_tranche"]["units_fully_operationalized"], 0
        )
        self.assertNotIn("baseline", burndown)
        self.assertNotIn("plan", burndown)
        self.assertEqual(
            burndown["current_state"]["lessons_by_disposition"],
            {
                "not_applicable_with_reason": 1,
                "open": 172,
                "partially_operationalized_real_consumer": 53,
            },
        )
        self.assertEqual(
            burndown["current_state"]["lessons_with_real_consumer_partial_evidence"],
            53,
        )
        self.assertEqual(
            burndown["current_state"]["units_by_disposition"],
            {
                "blocked": 0,
                "candidate_or_open": 118,
                "closed": 0,
                "real_consumer_partial": 48,
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
            [],
        )
        self.assertEqual(burndown["forecast"]["future_tranches_total"], 23)
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

    def test_absorption_builder_reopens_fixture_only_lessons(self):
        dispositions, _ = build_unit_dispositions.build()
        ledger, _, _, _, readiness = build_curriculum_absorption.build(
            build_curriculum_absorption.load(),
            unit_dispositions=dispositions,
        )
        by_lesson = {row["lesson_id"]: row for row in ledger}

        self.assertEqual(readiness["lessons_fully_operationalized"], 0)
        self.assertEqual(readiness["lessons_partially_operationalized"], 53)
        self.assertFalse(
            by_lesson["L1.M1.01"]["consumer_operationalization"][
                "fully_operationalized"
            ]
        )
        self.assertFalse(
            by_lesson["L1.M1.01"]["runtime_tutor_evidence"][
                "mapped_unit_closure_reached"
            ]
        )
        self.assertEqual(
            by_lesson["L1.M1.01"]["runtime_tutor_evidence"][
                "mapped_unit_closure_basis"
            ],
            "mapped_units_incomplete",
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
        self.assertEqual(len(closed_lessons), 0)

        mutated = copy.deepcopy(dispositions)
        closed_row = mutated[0]
        closed_row["fully_operationalized"] = True
        closed_row["fully_operationalized_basis"] = (
            "all_required_dimensions_satisfied:sha256:invalid"
        )
        errors = []
        validate_curriculum_l1l6.derive_operationalization_closure(
            mutated, lesson_units, errors
        )
        self.assertTrue(
            any("declared closure True != independent False" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
