#!/usr/bin/env python3
"""Focused tests for the deterministic L1-L6 tranche selector."""

from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import select_tranche as selector


def lesson(lesson_id: str) -> dict:
    return {"lesson_id": lesson_id}


def mapping(lesson_id: str, *units: str) -> dict:
    return {"lesson_id": lesson_id, "units": list(units)}


def unit(
    unit_id: str,
    *,
    closed: bool = False,
    basis: str = "not_yet_computed",
    blockers: list[dict] | None = None,
    strongest_state: str = "candidate_pack_harnessed",
) -> dict:
    return {
        "unit_id": unit_id,
        "axis": "sarf",
        "capability_interface": "discriminator_table",
        "machine_execution_appropriate": True,
        "tutor_projection_appropriate": True,
        "occurrence_grounding_appropriate": False,
        "misconception_cluster_count": 0,
        "fully_operationalized": closed,
        "fully_operationalized_basis": basis,
        "strongest_state": strongest_state,
        "blockers": blockers or [],
        "real_consumer_bindings": [],
    }


def fixture_inputs() -> selector.Inputs:
    return selector.Inputs(
        lessons=[lesson("L1")],
        lesson_unit_map=[mapping("L1", "u1")],
        unit_dispositions=[unit("u1")],
        canonical_units=[{
            "unit_id": "u1",
            "axis": "sarf",
            "capability_family": "discriminator_table",
            "contributing_lessons": {"L1": "proposer"},
        }],
        absorption_rows=[{
            "lesson_id": "L1",
            "absorption_state": "unitized",
            "consumer_operationalization": {
                "status": "not_operationalized",
                "real_binding_ids": [],
            },
        }],
        consumer_bindings=[],
        error_fixture_rows=[{"source": "L1"}],
        readiness={"lessons_fully_operationalized": 0},
        bench_report={"axes": {}},
        source_hashes={"fixture": "sha256:test"},
    )


class SelectorTests(unittest.TestCase):
    def test_already_closed_units_count_at_time_zero(self):
        plan = selector.plan_tranches(
            [lesson("L1"), lesson("L2")],
            [mapping("L1", "u-closed"), mapping("L2", "u-open")],
            [
                unit("u-closed", closed=True, basis="all_closure_dimensions_proven"),
                unit("u-open"),
            ],
            quota=1,
        )

        self.assertEqual(plan["baseline_closed_unit_ids"], ["u-closed"])
        self.assertEqual(plan["baseline_closed_lesson_ids"], ["L1"])
        self.assertEqual(plan["tranches"][0]["unit_ids"], ["u-open"])
        self.assertEqual(plan["tranches"][0]["newly_flipped_lesson_ids"], ["L2"])

    def test_lesson_flips_only_after_all_mapped_units_close(self):
        plan = selector.plan_tranches(
            [lesson("L1"), lesson("L2")],
            [mapping("L1", "u-a", "u-b"), mapping("L2", "u-a")],
            [unit("u-a"), unit("u-b")],
            quota=1,
        )

        self.assertEqual(plan["tranches"][0]["unit_ids"], ["u-a"])
        self.assertEqual(plan["tranches"][0]["newly_flipped_lesson_ids"], ["L2"])
        self.assertEqual(plan["tranches"][1]["unit_ids"], ["u-b"])
        self.assertEqual(plan["tranches"][1]["newly_flipped_lesson_ids"], ["L1"])

    def test_blocked_unit_prevents_done_and_is_surfaced(self):
        blocker = {
            "dimension": "linguistic_review",
            "state": "scholar_review_blocked",
            "cause": "school-dependent analysis requires adjudication",
        }
        plan = selector.plan_tranches(
            [lesson("L1"), lesson("L2")],
            [mapping("L1", "u-blocked"), mapping("L2", "u-open")],
            [unit("u-blocked", blockers=[blocker]), unit("u-open")],
            quota=1,
        )

        self.assertEqual(plan["blocked_unit_ids"], ["u-blocked"])
        self.assertEqual(plan["blocked_units"][0]["blockers"], [blocker])
        self.assertEqual(plan["lesson_dispositions"]["L1"]["state"], "blocked")
        self.assertEqual(plan["tranches"][0]["newly_flipped_lesson_ids"], ["L2"])

    def test_parkable_evidence_blocker_is_retained_without_stalling_selection(self):
        blocker = {
            "dimension": "occurrence_grounding",
            "state": "evidence_blocked",
            "cause": "missing exact occurrence witness",
        }
        plan = selector.plan_tranches(
            [lesson("L1")],
            [mapping("L1", "u-parked")],
            [unit("u-parked", blockers=[blocker])],
            quota=1,
        )

        self.assertEqual(plan["blocked_unit_ids"], [])
        self.assertEqual(plan["parked_unit_ids"], ["u-parked"])
        self.assertEqual(plan["tranches"][0]["unit_ids"], ["u-parked"])
        self.assertEqual(plan["tranches"][0]["newly_flipped_lesson_ids"], ["L1"])

    def test_closed_unit_may_retain_only_a_parked_occurrence_blocker(self):
        blocker = {
            "dimension": "occurrence_grounding",
            "state": "evidence_blocked",
            "cause": "missing exact occurrence witness",
        }
        plan = selector.plan_tranches(
            [lesson("L1")],
            [mapping("L1", "u-closed-parked")],
            [unit(
                "u-closed-parked",
                closed=True,
                basis="all_non_occurrence_dimensions_proven",
                blockers=[blocker],
            )],
            quota=1,
        )

        self.assertEqual(plan["baseline_closed_unit_ids"], ["u-closed-parked"])
        self.assertEqual(plan["baseline_closed_lesson_ids"], ["L1"])
        self.assertEqual(plan["parked_unit_ids"], ["u-closed-parked"])

    def test_greedy_selection_is_stable_and_reaches_quota_when_possible(self):
        lessons = [lesson(f"L{i:02}") for i in range(1, 11)]
        mappings = [mapping(f"L{i:02}", f"u{i:02}") for i in range(1, 11)]
        units = [unit(f"u{i:02}") for i in range(1, 11)]

        plan = selector.plan_tranches(lessons, mappings, units, quota=9)

        self.assertEqual(
            plan["tranches"][0]["unit_ids"],
            [f"u{i:02}" for i in range(1, 10)],
        )
        self.assertEqual(len(plan["tranches"][0]["newly_flipped_lesson_ids"]), 9)

    def test_final_residual_below_quota_is_retained(self):
        lessons = [lesson(f"L{i}") for i in range(1, 4)]
        mappings = [mapping(f"L{i}", f"u{i}") for i in range(1, 4)]
        units = [unit(f"u{i}") for i in range(1, 4)]

        plan = selector.plan_tranches(lessons, mappings, units, quota=2)

        self.assertEqual(len(plan["tranches"]), 2)
        self.assertFalse(plan["tranches"][0]["residual"])
        self.assertTrue(plan["tranches"][1]["residual"])
        self.assertEqual(plan["tranches"][1]["unit_ids"], ["u3"])
        self.assertEqual(plan["tranches"][1]["newly_flipped_lesson_ids"], ["L3"])

    def test_candidate_only_disposition_is_not_closed(self):
        candidate = unit("u-candidate", strongest_state="candidate_pack_harnessed")
        plan = selector.plan_tranches(
            [lesson("L1")],
            [mapping("L1", "u-candidate")],
            [candidate],
            quota=1,
        )

        self.assertEqual(plan["baseline_closed_unit_ids"], [])
        self.assertEqual(plan["tranches"][0]["unit_ids"], ["u-candidate"])

    def test_no_silent_lesson_or_unit_omission(self):
        with self.assertRaisesRegex(ValueError, "missing lesson-unit map rows: L2"):
            selector.plan_tranches(
                [lesson("L1"), lesson("L2")],
                [mapping("L1", "u1")],
                [unit("u1")],
                quota=1,
            )

        with self.assertRaisesRegex(ValueError, "unknown canonical units: u-missing"):
            selector.plan_tranches(
                [lesson("L1")],
                [mapping("L1", "u-missing")],
                [unit("u1")],
                quota=1,
            )

    def test_serialization_is_byte_deterministic(self):
        inputs = fixture_inputs()

        first = selector.serialize_outputs(inputs, quota=1)
        second = selector.serialize_outputs(inputs, quota=1)

        self.assertEqual(first, second)
        for payload in first.values():
            self.assertTrue(payload.endswith(b"\n"))
            json.loads(payload.decode("utf-8"))

    def test_default_cli_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sentinel = root / "sentinel.json"
            sentinel.write_text("unchanged", encoding="utf-8")

            with mock.patch.object(
                selector, "load_inputs", return_value=fixture_inputs()
            ) as mocked_load, redirect_stdout(io.StringIO()) as stdout:
                rc = selector.main(["--root", str(root), "--quota", "1"])

            self.assertEqual(rc, 0)
            mocked_load.assert_called_once_with(root)
            self.assertIn('"mode": "read_only"', stdout.getvalue())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")
            self.assertEqual(list(root.iterdir()), [sentinel])


if __name__ == "__main__":
    unittest.main()
