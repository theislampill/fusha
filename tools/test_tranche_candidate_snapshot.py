#!/usr/bin/env python3
"""Focused tests for the tranche-001 owner-facing candidate snapshot."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_tranche_candidate_snapshot as snapshot
import fusha_pattern_engine


class TrancheCandidateSnapshotTests(unittest.TestCase):
    def test_snapshot_is_honest_and_candidate_only(self):
        report = snapshot.build()
        by_id = {row["probe_id"]: row for row in report["probes"]}

        self.assertEqual(len(by_id), 5)
        self.assertFalse(report["public_projection_eligible"])
        self.assertEqual(report["analysis_database"], "largelexicon")
        self.assertEqual(
            report["analysis_database_source"],
            "fusha/lexicon/largelexicon/lemma-source.full.jsonl",
        )
        self.assertEqual(
            by_id["mulk-final-kaf"]["status"], "analysis_gap_detected"
        )
        self.assertEqual(
            by_id["mulk-final-kaf"]["after"]["analysis_database"],
            "largelexicon",
        )
        self.assertEqual(by_id["mulk-final-kaf"]["after"]["roles"], [])
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

    def test_unknown_lexicon_database_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported lexicon database"):
            fusha_pattern_engine._load_lexicon(db="full")

    def test_missing_lexicon_sources_fail_closed_without_fallback(self):
        with self.assertRaisesRegex(FileNotFoundError, "required seed lexicon"):
            fusha_pattern_engine._load_lexicon(path="missing-seed.jsonl")
        with mock.patch.object(
            fusha_pattern_engine,
            "LARGELEXICON_FULL_PATH",
            "missing-largelexicon-full.jsonl",
        ):
            with self.assertRaisesRegex(
                FileNotFoundError, "required largelexicon full source"
            ):
                fusha_pattern_engine._load_lexicon(db="largelexicon")


if __name__ == "__main__":
    unittest.main()
