#!/usr/bin/env python3
"""Focused tests for the tranche-001 owner-facing candidate snapshot."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_tranche_candidate_snapshot as snapshot


class TrancheCandidateSnapshotTests(unittest.TestCase):
    def test_snapshot_is_honest_and_candidate_only(self):
        report = snapshot.build()
        by_id = {row["probe_id"]: row for row in report["probes"]}

        self.assertEqual(len(by_id), 5)
        self.assertFalse(report["public_projection_eligible"])
        self.assertEqual(by_id["mulk-final-kaf"]["status"], "regression_detected")
        self.assertEqual(
            by_id["relative-alladhina"]["after"]["roles"], ["stem"]
        )
        self.assertNotIn(
            "subject_pronoun", by_id["quranan-tanwin"]["after"]["roles"]
        )
        self.assertEqual(
            by_id["ma-rivals"]["after"]["rivals"],
            ["negation", "relative"],
        )
        self.assertTrue(by_id["geminate-jussive-rivals"]["after"]["held"])


if __name__ == "__main__":
    unittest.main()
