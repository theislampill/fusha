#!/usr/bin/env python3
"""Tests for the exact-diacritic function-word homograph pre-pass."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import funcword_homograph_prepass as prepass


QUEUE = ROOT / "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.jsonl"
LOC_SURFACE = ROOT / "qamus/indexes/quran-loc-surface/index.jsonl"
RULES = ROOT / "nahw/rules/funcword-homograph-prepass-rules.json"
CALIBRATION = ROOT / ".inputs/funcword-review-cal.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class ExactDiacriticFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = prepass.load_rules(RULES)
        cls.queue_by_loc = {
            row["target"]["canonical_location"]: row for row in read_jsonl(QUEUE)
        }
        cls.surface_by_loc = {
            row["loc"]: row["surface"] for row in read_jsonl(LOC_SURFACE)
        }

    def apply_at(self, location: str) -> dict:
        row = self.queue_by_loc[location]
        return prepass.apply_prepass_row(
            row, self.surface_by_loc[location], self.rules
        )

    def test_man_fatha_family_uses_real_calibration_location(self) -> None:
        result = self.apply_at("2:62:8")
        self.assertEqual("مَنْ", result["target"]["surface"])
        self.assertEqual("man_fatha_not_min", result["prepass_rule"])
        self.assertEqual("preposition", result["particle_class_before"])
        self.assertEqual("man-family", result["particle_class_after"])

    def test_in_light_family_uses_real_calibration_location(self) -> None:
        result = self.apply_at("2:24:1")
        self.assertEqual("فَإِن", result["target"]["surface"])
        self.assertEqual("in_light_not_inna", result["prepass_rule"])
        self.assertEqual("in-light-family", result["particle_class_after"])

    def test_an_light_family_uses_real_calibration_location(self) -> None:
        result = self.apply_at("3:193:7")
        self.assertEqual("أَنْ", result["target"]["surface"])
        self.assertEqual("an_light_not_anna", result["prepass_rule"])
        self.assertEqual("an-masdariyya", result["particle_class_after"])

    def test_out_of_table_surface_abstains_without_changing_class(self) -> None:
        result = self.apply_at("2:18:5")
        self.assertIsNone(result["prepass_rule"])
        self.assertEqual("negation", result["particle_class_before"])
        self.assertEqual("negation", result["particle_class_after"])
        self.assertEqual("negation", result["particle_class"])

    def test_normalization_collision_does_not_match_exact_surface_rule(self) -> None:
        row = copy.deepcopy(self.queue_by_loc["2:62:8"])
        result = prepass.apply_prepass_row(row, "مِنْ", self.rules)
        self.assertIsNone(result["prepass_rule"])
        self.assertEqual("preposition", result["particle_class"])

    def test_rule_loader_rejects_nonliteral_patterns(self) -> None:
        payload = json.loads(RULES.read_text(encoding="utf-8"))
        payload["rules"][0]["exact_surfaces"].append(".*مَن")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rules.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "literal"):
                prepass.load_rules(path)


class ArtifactContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CALIBRATION.is_file():
            raise unittest.SkipTest("owner calibration input is not present")
        cls.queue_rows = read_jsonl(QUEUE)
        cls.loc_rows = read_jsonl(LOC_SURFACE)
        cls.calibration_rows = read_jsonl(CALIBRATION)
        cls.rules = prepass.load_rules(RULES)
        cls.v2_rows, cls.report = prepass.build_outputs(
            cls.queue_rows, cls.loc_rows, cls.rules, cls.calibration_rows
        )

    def test_v1_queue_is_not_mutated(self) -> None:
        before = QUEUE.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            prepass.write_outputs(
                self.v2_rows,
                self.report,
                Path(temporary) / "queue.jsonl",
                Path(temporary) / "report.json",
            )
        self.assertEqual(before, QUEUE.read_bytes())

    def test_calibration_cites_all_31_homograph_corrections(self) -> None:
        calibration = self.report["calibration_agreement"]
        self.assertEqual(31, calibration["diacritic_decidable_rows"])
        self.assertGreaterEqual(calibration["homograph_corrections_reproduced"], 28)
        self.assertEqual(31, len(calibration["citations"]))
        self.assertEqual([], calibration["shortfalls"])

    def test_all_lillahi_rows_route_to_divine_name_entry(self) -> None:
        routed = [
            row for row in self.v2_rows
            if row.get("boundary_route") == "divine_name_entry"
        ]
        self.assertEqual(11, len(routed))
        self.assertTrue(
            all(row.get("boundary_note") == "lillahi_fused_divine_name" for row in routed)
        )

    def test_every_row_records_before_after_and_exact_loc_surface(self) -> None:
        surface_by_loc = {row["loc"]: row["surface"] for row in self.loc_rows}
        self.assertEqual(1043, len(self.v2_rows))
        for row in self.v2_rows:
            location = row["target"]["canonical_location"]
            self.assertEqual(surface_by_loc[location], row["target"]["surface"])
            self.assertIn("prepass_rule", row)
            self.assertEqual(row["particle_class"], row["particle_class_after"])

    def test_v2_changes_only_class_and_audit_fields(self) -> None:
        v1_by_loc = {
            row["target"]["canonical_location"]: row for row in self.queue_rows
        }
        for actual_row in self.v2_rows:
            location = actual_row["target"]["canonical_location"]
            expected = copy.deepcopy(v1_by_loc[location])
            actual = copy.deepcopy(actual_row)
            rule_id = actual.pop("prepass_rule")
            before = actual.pop("particle_class_before")
            after = actual.pop("particle_class_after")
            actual.pop("boundary_route", None)
            actual["schema"] = expected["schema"]
            self.assertEqual(expected["particle_class"], before)
            if rule_id is None:
                self.assertEqual(before, after)
            else:
                expected["particle_class"] = after
            self.assertEqual(expected, actual, location)

    def test_serialization_is_byte_identical_across_two_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            paths = []
            for suffix in ("a", "b"):
                queue = base / f"queue-{suffix}.jsonl"
                report = base / f"report-{suffix}.json"
                prepass.write_outputs(self.v2_rows, self.report, queue, report)
                paths.append((queue.read_bytes(), report.read_bytes()))
        self.assertEqual(paths[0], paths[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
