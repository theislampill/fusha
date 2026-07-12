#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "build_rm36_residual_closure.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_rm36_residual_closure", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ResidualClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()
        cls.index_rows = [
            {"loc": "3:152:2", "surface": "صَدَقَكُمُ"},
            {"loc": "2:4:8", "surface": "مِن"},
            {"loc": "2:214:2", "surface": "حَسِبْتُمْ"},
            {"loc": "2:214:30", "surface": "قَرِيبٌ"},
            {"loc": "98:1:1", "surface": "بِسْمِ"},
            {"loc": "98:1:5", "surface": "لَمْ"},
            {"loc": "27:42:2", "surface": "جَآءَتْ"},
            {"loc": "27:42:8", "surface": "عَرْشُهَا"},
        ]
        cls.index_by_loc, cls.index_by_ayah = cls.mod.index_rows(cls.index_rows)

    def row(self, **overrides):
        row = {
            "canonical_quran_loc": "3:152:2",
            "classification": "nf_t10_1_dependent",
            "quran_ref": "3:152",
            "row_id": "row-exact",
            "visible_surface": "صَدَقَكُمُ",
        }
        row.update(overrides)
        return row

    def test_exact_loc_surface_closes_verified(self):
        result = self.mod.classify_row(
            self.row(), self.index_by_loc, self.index_by_ayah, set(), set(), "packet#row-exact"
        )
        self.assertEqual(result["terminal_class"], "closed_verified")
        self.assertIsNone(result["exception"])
        self.assertEqual(result["evidence"]["indexed_location_surface"], "صَدَقَكُمُ")

    def test_pr53_row_uses_correction_terminal_class(self):
        result = self.mod.classify_row(
            self.row(row_id="row-pr53"),
            self.index_by_loc,
            self.index_by_ayah,
            set(),
            {"row-pr53"},
            "packet#row-pr53",
        )
        self.assertEqual(result["terminal_class"], "closed_by_correction")
        self.assertEqual(result["correction"]["pull_request"], 53)

    def test_lane_a2_row_stays_demoted(self):
        result = self.mod.classify_row(
            self.row(row_id="row-demoted"),
            self.index_by_loc,
            self.index_by_ayah,
            {"row-demoted"},
            set(),
            "packet#row-demoted",
        )
        self.assertEqual(result["terminal_class"], "demoted")
        self.assertEqual(result["demotion"]["wave"], "rm36-demotion-01")

    def test_surface_drift_exception_carries_exact_pair(self):
        result = self.mod.classify_row(
            self.row(
                canonical_quran_loc="2:4:8",
                classification="normalization_correction",
                quran_ref="2:4",
                row_id="row-drift",
                visible_surface="مِنْ",
            ),
            self.index_by_loc,
            self.index_by_ayah,
            set(),
            set(),
            "packet#row-drift",
        )
        self.assertEqual(result["terminal_class"], "exception")
        self.assertEqual(result["exception"]["cause"], "vowel_preserving_surface_drift")
        self.assertEqual(
            result["exception"]["exact_pair"],
            {"indexed": "مِن", "visible": "مِنْ"},
        )

    def test_fragment_relative_index_is_owner_gated(self):
        result = self.mod.classify_row(
            self.row(
                canonical_quran_loc="2:214:2",
                quran_ref="2:214",
                row_id="row-fragment",
                visible_surface="قريب",
            ),
            self.index_by_loc,
            self.index_by_ayah,
            set(),
            set(),
            "qamus/indexes/largelexicon/qword-crosswalk/p051-p060.jsonl#row-fragment",
        )
        self.assertEqual(result["exception"]["cause"], "example_fragment_relative_index_artifact")
        self.assertTrue(result["exception"]["owner_gated_data_fix"])
        self.assertIn("p051-p060.jsonl", result["exception"]["packet_ref"])

    def test_98_1_uses_documented_wbw_slice_exception(self):
        result = self.mod.classify_row(
            self.row(
                canonical_quran_loc="98:1:1",
                quran_ref="98:1",
                row_id="row-98",
                visible_surface="لَمْ",
            ),
            self.index_by_loc,
            self.index_by_ayah,
            set(),
            set(),
            "packet#row-98",
        )
        self.assertEqual(result["exception"]["cause"], "wbw_slice_reference_artifact")
        self.assertEqual(result["exception"]["wbw_slice_reference"], "98:1")

    def test_permanent_candidate_becomes_concrete_owner_gate(self):
        result = self.mod.classify_row(
            self.row(
                canonical_quran_loc="27:42:2",
                classification="permanent_exception_candidate",
                quran_ref="27:42",
                row_id="row-owner",
                visible_surface="عرشك",
            ),
            self.index_by_loc,
            self.index_by_ayah,
            set(),
            set(),
            "packet#row-owner",
        )
        self.assertEqual(result["exception"]["cause"], "owner_gated_source_card_surface_fix")
        self.assertEqual(result["exception"]["exact_pair"]["visible"], "عرشك")
        self.assertEqual(result["exception"]["exact_pair"]["indexed"], "جَآءَتْ")

    def test_serialization_and_hashing_are_deterministic(self):
        payload = {"z": 1, "a": ["مِنْ", "مِن"]}
        first = self.mod.pretty_json_bytes(payload)
        second = self.mod.pretty_json_bytes(payload)
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        self.assertEqual(
            self.mod.sha256_bytes(first), hashlib.sha256(first).hexdigest()
        )
        self.assertEqual(json.loads(first.decode("utf-8")), payload)

    def test_terminal_counts_include_zero_valued_classes(self):
        self.assertEqual(
            self.mod.complete_terminal_counts(Counter({"closed_verified": 36, "demoted": 37, "exception": 406})),
            {
                "closed_by_correction": 0,
                "closed_verified": 36,
                "demoted": 37,
                "exception": 406,
            },
        )

    def test_proposed_regression_hunk_is_scoped_but_not_applied(self):
        hunk = self.mod.proposed_regression_hunk_bytes().decode("utf-8")
        self.assertIn("diff --git a/tools/check_regressions.py b/tools/check_regressions.py", hunk)
        self.assertIn("build_rm36_residual_closure.py", hunk)
        self.assertIn('"--check"', hunk)
        self.assertTrue(hunk.endswith("\n"))
        checked = subprocess.run(
            ["git", "apply", "--check", "-"],
            cwd=self.mod.REPO_ROOT,
            input=self.mod.proposed_regression_hunk_bytes(),
            capture_output=True,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr.decode("utf-8", errors="replace"))

    def test_patch_bytes_are_not_line_ending_normalized_by_git(self):
        paths = [
            str(self.mod.HUNK_PATH.relative_to(self.mod.REPO_ROOT)),
            str(self.mod.ATTRIBUTES_PATH.relative_to(self.mod.REPO_ROOT)),
        ]
        checked = subprocess.run(
            ["git", "check-attr", "text", "--", *paths],
            cwd=self.mod.REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout.count("text: unset"), 2, checked.stdout)


if __name__ == "__main__":
    unittest.main()
