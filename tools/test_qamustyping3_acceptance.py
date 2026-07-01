"""Regression test for the qamustyping3 acceptance gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_qamustyping3_acceptance import validate_qamustyping3  # noqa: E402


class QamusTyping3AcceptanceTest(unittest.TestCase):
    def test_acceptance_gate_truthfully_closes_all_stages(self) -> None:
        result = validate_qamustyping3(ROOT)

        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(
            result["claim_boundary"]["is_full_classical_arabic_nlp_stack"],
            False,
        )
        self.assertEqual(
            set(result["stages"].keys()),
            {"P0", "P0.5", "P1", "P2", "P3", "P4"},
        )
        self.assertGreaterEqual(result["thin_slice"]["source_rows"], 17)
        self.assertGreaterEqual(result["all_qword_fixture"]["rows"], 5)
        self.assertEqual(
            result["capabilities"]["statistical_disambiguator"]["status"],
            "gated_by_corpus_eval_training",
        )
        self.assertEqual(
            result["capabilities"]["dependency_parser"]["status"],
            "rule_ranked_smoke_only",
        )
        self.assertIn("tafsir_mcp", result["external_sources"])
        self.assertIn("quran_foundation_api", result["external_sources"])
        self.assertIn("camel_tools", result["external_sources"])


if __name__ == "__main__":
    unittest.main()
