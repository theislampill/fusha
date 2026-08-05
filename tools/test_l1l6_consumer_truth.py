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
TRANCHE_001B_BINDING_IDS = {
    "l1l6-tranche-001b-foundational-script-runtime",
    "l1l6-tranche-001b-weak-root-voice-runtime",
    "l1l6-tranche-001b-derivation-template-runtime",
    "l1l6-tranche-001b-ma-context-runtime",
}
TRANCHE_001B_LESSONS = {
    "L1.M1.01", "L1.M1.02", "L1.M1.03", "L1.M1.04", "L1.M1.05",
    "L1.M1.06", "L1.M1.07", "L1.M5.04", "L1.M5.05", "L1.M5.07",
    "L2.M1.02", "L2.M1.04", "L2.M4.02", "L2.M5.02", "L2.M5.03",
    "L3.M4.04", "L3.M4.08", "L4.M1.01", "L4.M1.02", "L4.M1.03",
    "L4.M1.04", "L4.M1.05", "L4.M1.06", "L4.M1.07", "L4.M2.04",
    "L4.M3.07", "L4.M4.04", "L4.M5.10", "L5.M1.06", "L5.M4.01",
    "L6.M3.01", "L6.M3.07", "L6.M4.06", "L6.M6.04",
}
TRANCHE_001B_UNITS = {
    "cu-definite-article-assimilation", "cu-grapheme-inventory-and-confusables",
    "cu-nunation-support-orthography", "cu-orthographic-connectivity-classes",
    "cu-short-vowel-diacritics-and-vocalization-state",
    "u-n01", "u-n02", "u-n03", "u-n04", "u-n06", "u-n07", "u-n08",
    "u-n09", "u-n10", "u-n11", "u-n12", "u-s01", "u-s02", "u-s03",
    "u-s04", "u-s05", "u-s06", "u-s07", "u-s09",
}


def _jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ConsumerTruthTests(unittest.TestCase):
    def test_tranche_slice_sarf_binding_is_real_and_candidate_only(self):
        bindings = absorption.load_consumer_bindings()
        rows = [
            row for row in bindings
            if row.get("consumer_train") == "tranche_001a"
        ]

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["consumer_plane"], "sarf_analytical")
        self.assertEqual(row["binding_status"], "explicit")
        self.assertEqual(row["certification_posture"], "candidate_analysis_only")
        self.assertFalse(row["public_projection_eligible"])

        errors = []
        validator.check_consumer_operationalization_bindings(
            validator.load_context(), errors
        )
        self.assertEqual(errors, [])

    def test_tranche_001b_runtime_bindings_are_exact_and_candidate_only(self):
        rows = [
            row for row in absorption.load_consumer_bindings()
            if row.get("consumer_train") == "tranche_001b"
        ]

        self.assertEqual({row["binding_id"] for row in rows}, TRANCHE_001B_BINDING_IDS)
        self.assertEqual(sum(len(row["runtime_item_ids"]) for row in rows), 128)
        self.assertEqual(len({rid for row in rows for rid in row["runtime_item_ids"]}), 128)
        for row in rows:
            self.assertEqual(row["consumer_plane"], "tutor_runtime")
            self.assertEqual(row["binding_status"], "explicit")
            self.assertEqual(row["certification_posture"], "instructional_runtime_only")
            self.assertTrue(row["candidate_status_preserved"])
            self.assertFalse(row["public_projection_eligible"])

        errors = []
        validator.check_consumer_operationalization_bindings(
            validator.load_context(), errors
        )
        self.assertEqual(errors, [])

    def test_explicit_runtime_bindings_do_not_promote_candidate_drills(self):
        ctx = absorption.load()
        runtime = absorption.ordinary_tutor_runtime_truth(ctx)
        _ledger, _sections, _completeness, _queues, readiness = absorption.build(ctx)

        self.assertEqual(
            set(runtime["explicit_lesson_ids"]),
            TRAIN_C_LESSONS | TRANCHE_001B_LESSONS,
        )
        self.assertEqual(
            set(runtime["explicit_unit_ids"]),
            TRAIN_C_UNITS | TRANCHE_001B_UNITS,
        )
        self.assertEqual(len(runtime["bound_runtime_item_ids"]), 155)
        self.assertEqual(runtime["bound_runtime_item_count"], 155)
        self.assertEqual(runtime["candidate_drill_specs_promoted"], 0)
        self.assertEqual(readiness["lessons_mapped_to_tutor_drills"], 39)
        self.assertEqual(readiness["lessons_fully_operationalized"], 4)
        self.assertEqual(
            readiness["lessons_fully_operationalized_basis"],
            "all_mapped_canonical_units_fully_operationalized",
        )
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
        self.assertEqual(meta["explicit_runtime_unit_bindings"], 30)
        self.assertEqual(meta["lessons_fully_operationalized"], 4)

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
        self.assertEqual(readiness["lessons_mapped_to_tutor_drills"], 39)
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
        self.assertEqual(runtime["explicit_canonical_unit_bindings"], 30)
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
        self.assertEqual(meta["explicit_runtime_unit_bindings"], 30)
        closed = {
            "cu-definite-article-assimilation",
            "cu-grapheme-inventory-and-confusables",
            "cu-nunation-support-orthography",
            "cu-orthographic-connectivity-classes",
            "cu-short-vowel-diacritics-and-vocalization-state",
        }
        for row in rows:
            self.assertNotIn("candidate_runtime_behavioral_mapping", row["states"])
            self.assertNotIn("runtime_behavioral_evidence", row["states"])
            self.assertEqual(
                row["fully_operationalized"], row["unit_id"] in closed
            )
            if row["unit_id"] in closed:
                self.assertTrue(
                    row["fully_operationalized_basis"].startswith(
                        "all_required_dimensions_satisfied:sha256:"
                    )
                )
            else:
                self.assertFalse(row["fully_operationalized"])

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
