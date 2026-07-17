#!/usr/bin/env python3
"""Red-first contract tests for the FC1 naḥw dependency producer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.typed_claim_contract import validate_contract_record
from tools.fc_nahw_producer import (
    build_dependency_fact,
    build_unresolved_record,
    surface_is_preserved,
    validate_dependency_fact,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "fc1-nahw" / "producer-fixtures.jsonl"


def _fixtures() -> list[dict]:
    return [json.loads(line) for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


class Fc1NahwProducerTests(unittest.TestCase):
    def test_positive_fixtures_build_fa_dependency_facts(self) -> None:
        positives = [fixture for fixture in _fixtures() if fixture["expect"] == "accept"]
        self.assertGreaterEqual(len(positives), 5)
        for fixture in positives:
            with self.subTest(fixture=fixture["id"]):
                fact = build_dependency_fact(
                    fixture["input"],
                    source_record_id=f"fixture:{fixture['id']}",
                )
                self.assertEqual(validate_dependency_fact(fact), [])
                self.assertEqual(fact["fact_type"], "nahw_dependency")
                self.assertIn("governor", fact["fact_value"])
                self.assertIn("governed_occurrence", fact["fact_value"])
                self.assertIn("relationship_evidence", fact["fact_value"])
                self.assertIn("case_or_mood", fact["fact_value"])
                self.assertIn("ending", fact["fact_value"])
                self.assertIn("source", fact)
                self.assertIn("certification", fact)

    def test_estimated_ending_is_explicitly_flagged(self) -> None:
        fixture = next(item for item in _fixtures() if item["id"] == "positive-estimated-ending")
        fact = build_dependency_fact(fixture["input"], source_record_id="fixture:estimated")
        ending = fact["fact_value"]["ending"]
        self.assertEqual(ending["status"], "estimated")
        self.assertTrue(ending["reason"])
        self.assertNotEqual(fact["certification"]["status"], "certified")

    def test_adversarial_fixtures_fail_closed(self) -> None:
        rejects = [fixture for fixture in _fixtures() if fixture["expect"] == "reject"]
        self.assertGreaterEqual(len(rejects), 5)
        for fixture in rejects:
            with self.subTest(fixture=fixture["id"]):
                try:
                    fact = build_dependency_fact(
                        fixture["input"],
                        source_record_id=f"fixture:{fixture['id']}",
                    )
                except ValueError:
                    continue
                self.assertTrue(validate_dependency_fact(fact))

    def test_missing_governor_becomes_typed_unresolved_record(self) -> None:
        fixture = next(item for item in _fixtures() if item["id"] == "adversarial-missing-governor")
        record = build_unresolved_record(
            fixture["input"],
            blocker="exact governor occurrence is missing",
            source_record_id="fixture:missing-governor",
        )
        self.assertEqual(record["projection"]["status"], "syntax_pending")
        self.assertIsNone(record["projection"]["claim"])
        self.assertTrue(record["projection"]["learner_visible"])
        self.assertEqual(validate_contract_record(record), [])

    def test_surface_preservation_is_exact(self) -> None:
        self.assertTrue(surface_is_preserved("مِنَ", "مِنَ"))
        self.assertFalse(surface_is_preserved("مِنَ", "مَنَ"))


if __name__ == "__main__":
    unittest.main()
