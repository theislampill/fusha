#!/usr/bin/env python3
"""Focused contract tests for the PREDV3 measurement CLI."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.measure_fb1_predicate_v3 import annotate_readmitted_records  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class PredicateV3MeasurementTests(unittest.TestCase):
    def test_cli_self_test_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "measure_fb1_predicate_v3.py"), "--self-test"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("FB1 PREDICATE V3 MEASUREMENT SELF-TEST PASS", result.stdout)

    def test_readmitted_hand_checks_are_persisted_on_selected_records(self):
        records = [{"loc": "2:1:1"}, {"loc": "2:1:2"}]
        selected = annotate_readmitted_records(
            records,
            ["2:1:2"],
            {"2:1:2": {"manual_family_match": True, "manual_reason": "attached"}},
            seed=20260718,
            sample_size=12,
        )
        self.assertEqual(["2:1:2"], [row["loc"] for row in selected])
        self.assertTrue(records[1]["hand_checked_re_admission"])
        self.assertTrue(records[1]["manual_family_match"])
        self.assertFalse(records[0]["hand_checked_re_admission"])


if __name__ == "__main__":
    unittest.main()
