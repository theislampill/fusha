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

TRAIN_B_NEW_UNITS = {
    "cu-bound-fa-function-discrimination",
    "cu-fa-function-and-mood-licensing",
}
TRAIN_B_REVERIFIED_UNITS = {
    "cu-badal-vs-atf-bayan",
    "cu-clitic-pronoun-role-discriminator",
    "cu-la-negative-vs-prohibitive-discriminator",
    "cu-preposition-sense-discriminators",
    "cu-tanazu-governor-selection",
}
TRAIN_B_PENDING_UNITS = {
    "cu-badal-typology-discriminator",
    "cu-hal-licensing-conditions",
    "cu-ighra-tahdhir-licensing",
    "cu-ishtighal-fronted-noun-case",
    "cu-verb-particle-selection-licensing",
}
TRAIN_C_LESSONS = {
    "L1.M4.05", "L2.M5.01", "L4.M2.01",
    "L4.M2.04", "L4.M2.05", "L4.M5.04",
}
TRAIN_C_UNITS = {
    "cu-attributive-agreement-licensing",
    "cu-atf-case-following",
    "cu-atf-particle-discriminator",
    "cu-badal-typology-discriminator",
    "cu-lakin-coordinator-vs-abrogator",
    "cu-waw-function-discriminator",
}


def _jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ConsumerTruthTests(unittest.TestCase):
    def test_train_c_runtime_bindings_do_not_promote_candidate_drills(self):
        ctx = absorption.load()
        runtime = absorption.ordinary_tutor_runtime_truth(ctx)
        _ledger, _sections, _completeness, _queues, readiness = absorption.build(ctx)

        self.assertEqual(set(runtime["explicit_lesson_ids"]), TRAIN_C_LESSONS)
        self.assertEqual(set(runtime["explicit_unit_ids"]), TRAIN_C_UNITS)
        self.assertEqual(len(runtime["bound_runtime_item_ids"]), 27)
        self.assertEqual(runtime["bound_runtime_item_count"], 27)
        self.assertEqual(runtime["candidate_drill_specs_promoted"], 0)
        self.assertEqual(readiness["lessons_mapped_to_tutor_drills"], 6)
        self.assertEqual(readiness["lessons_fully_operationalized"], 0)
        self.assertEqual(readiness["lessons_fully_operationalized_basis"], "not_yet_computed")
        self.assertEqual(
            readiness["candidate_drill_packets"]["runtime_integrated"], 0
        )

    def test_train_b_and_c_unit_bindings_preserve_consumer_planes(self):
        bindings = absorption.load_consumer_bindings()
        truth = absorption.consumer_operationalization_truth(bindings)
        rows, meta = dispositions.build(bindings=bindings)
        by_id = {row["unit_id"]: row for row in rows}

        self.assertEqual(
            set(truth["new_real_unit_ids_by_plane"]["nahw_analytical"]),
            TRAIN_B_NEW_UNITS,
        )
        self.assertEqual(
            set(truth["reverified_unit_ids_by_plane"]["nahw_analytical"]),
            TRAIN_B_REVERIFIED_UNITS,
        )
        self.assertEqual(
            set(truth["pending_unit_ids_by_plane"]["nahw_analytical"]),
            TRAIN_B_PENDING_UNITS,
        )
        self.assertEqual(meta["explicit_runtime_unit_bindings"], 6)
        self.assertEqual(meta["lessons_fully_operationalized"], 0)

        badal = by_id["cu-badal-typology-discriminator"]
        self.assertEqual(badal["operationalized_planes"], ["tutor_runtime"])
        self.assertEqual(badal["pending_consumer_planes"], ["nahw_analytical"])

    def test_removing_one_binding_changes_only_its_lesson_and_unit_plane(self):
        bindings = absorption.load_consumer_bindings()
        trimmed = [
            row for row in bindings
            if row["binding_id"] != "l1l6-train-c-badal-runtime"
        ]
        full_truth = absorption.consumer_operationalization_truth(bindings)
        truth = absorption.consumer_operationalization_truth(trimmed)
        rows, _meta = dispositions.build(bindings=trimmed)
        by_id = {row["unit_id"]: row for row in rows}

        self.assertNotIn("L4.M2.05", truth["real_consumer_lesson_ids"])
        self.assertIn("L4.M2.04", truth["real_consumer_lesson_ids"])
        self.assertEqual(
            set(truth["real_consumer_lesson_ids"]),
            set(full_truth["real_consumer_lesson_ids"]) - {"L4.M2.05"},
        )
        self.assertEqual(
            set(truth["real_consumer_unit_ids"]),
            set(full_truth["real_consumer_unit_ids"])
            - {"cu-badal-typology-discriminator"},
        )
        self.assertEqual(
            by_id["cu-badal-typology-discriminator"]["operationalized_planes"],
            [],
        )
        self.assertEqual(
            by_id["cu-badal-typology-discriminator"]["pending_consumer_planes"],
            ["nahw_analytical"],
        )
        self.assertEqual(
            by_id["cu-atf-particle-discriminator"]["operationalized_planes"],
            ["tutor_runtime"],
        )

    def test_readiness_separates_runtime_fixture_and_candidate_drill_evidence(self):
        ctx = absorption.load()
        expected_runtime = absorption.ordinary_tutor_runtime_truth(ctx)
        ledger, _sections, _completeness, _queues, readiness = absorption.build(ctx)

        self.assertEqual(readiness["source_lessons"], 226)
        self.assertEqual(
            readiness["lesson_denominators_by_level"], EXPECTED_LEVEL_DENOMINATORS
        )
        self.assertEqual(readiness["lessons_mapped_to_tutor_drills"], 6)
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
        self.assertEqual(runtime["explicit_canonical_unit_bindings"], 6)
        self.assertFalse(runtime["lesson_content_fully_operationalized"])
        self.assertEqual(runtime["lesson_content_fully_operationalized_basis"], "not_yet_computed")

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

        # train_d/train_e have no bindings in ANY committed link file, so asserting they are 0 alone is
        # tautological (true regardless of whether explicit_other_train_linkage reads the right manifest at
        # all). Also assert train_b/train_c against independently known, non-zero evidence -- this is the
        # genuine no-false-runtime-evidence check: it would catch both a broken reader (e.g. one that globs
        # unrelated link files with no consumer_train field and silently returns 0) and a false inflation.
        linkage = readiness["other_train_l1l6_linkage"]
        train_b_lessons = {lid for row in absorption.load_consumer_bindings()
                           if row["consumer_train"] == "train_b" and row["binding_status"] == "explicit"
                           for lid in row["lesson_ids"]}
        train_b_units = {uid for row in absorption.load_consumer_bindings()
                         if row["consumer_train"] == "train_b" and row["binding_status"] == "explicit"
                         for uid in row["unit_ids"]}
        self.assertGreater(len(train_b_lessons), 0)
        self.assertEqual(linkage["train_b"]["explicit_lesson_bindings"], len(train_b_lessons))
        self.assertEqual(linkage["train_b"]["explicit_unit_bindings"], len(train_b_units))
        self.assertEqual(linkage["train_c"]["explicit_lesson_bindings"], len(TRAIN_C_LESSONS))
        self.assertEqual(linkage["train_c"]["explicit_unit_bindings"], len(TRAIN_C_UNITS))
        for train in ("train_d", "train_e"):
            self.assertEqual(linkage[train]["explicit_lesson_bindings"], 0)
            self.assertEqual(linkage[train]["explicit_unit_bindings"], 0)

    def test_unit_dispositions_keep_consumer_evidence_out_of_candidate_states(self):
        rows, meta = dispositions.build()
        self.assertEqual(meta["explicit_runtime_unit_bindings"], 6)
        for row in rows:
            self.assertNotIn("candidate_runtime_behavioral_mapping", row["states"])
            self.assertNotIn("runtime_behavioral_evidence", row["states"])
            self.assertFalse(row["fully_operationalized"])
            self.assertEqual(row["fully_operationalized_basis"], "not_yet_computed")

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
