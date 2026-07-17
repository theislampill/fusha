"""Red-first tests for the FAM2 lexical formation producer."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools import fam2_lexical_producer


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "qamus" / "examples" / "fam2-lexical"


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class FAM2LexicalProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = _load_jsonl(FIXTURES / "entry-fixtures.jsonl")
        cls.fixtures = _load_jsonl(FIXTURES / "producer-fixtures.jsonl")

    def test_positive_fixture_set_covers_all_bounded_subshapes(self) -> None:
        positives = [fixture for fixture in self.fixtures if fixture["expected_status"] == "candidate"]
        expected = {
            "broken_plural",
            "sound_masculine_plural",
            "sound_feminine_plural",
            "dual",
            "nisba_adjective",
            "elative",
        }
        self.assertTrue(expected <= {fixture["expected_sub_shape"] for fixture in positives})
        self.assertGreaterEqual(len(positives), 6)

    def test_positive_records_are_typed_and_reconstructible(self) -> None:
        for fixture in self.fixtures:
            if fixture["expected_status"] != "candidate":
                continue
            record = fam2_lexical_producer.produce_record(fixture["row"], entries=self.entries)
            self.assertEqual("projection_input", record["record_type"], fixture["fixture_id"])
            self.assertEqual([], fam2_lexical_producer.validate_formation_record(record), fixture["fixture_id"])
            facts = [fact for fact in record["facts"] if fact["fact_type"] == "formation_evidence"]
            self.assertTrue(facts, fixture["fixture_id"])
            fact_value = facts[0]["fact_value"]
            self.assertEqual(fixture["expected_sub_shape"], fact_value["sub_shape"])
            self.assertTrue(fact_value["reconstruction_proof"]["passed"], fixture["fixture_id"])
            self.assertFalse(record["projection"]["materialization_target"]["live_mutation_allowed"])

    def test_adversarial_fixture_set_contains_required_routes(self) -> None:
        negatives = [fixture for fixture in self.fixtures if fixture["expected_status"] != "candidate"]
        self.assertGreaterEqual(len(negatives), 6)
        ids = {fixture["fixture_id"] for fixture in negatives}
        self.assertIn("sufaha-label-only-canary", ids)
        self.assertIn("sound-plural-not-broken", {fixture["fixture_id"] for fixture in self.fixtures})
        self.assertIn("missing-singular-ababil", ids)
        self.assertIn("noun-adjective-homograph", ids)

    def test_adversarial_records_are_typed_unresolved_and_never_projected(self) -> None:
        for fixture in self.fixtures:
            if fixture["expected_status"] == "candidate":
                continue
            record = fam2_lexical_producer.produce_record(fixture["row"], entries=self.entries)
            self.assertEqual("unresolved_projection", record["record_type"], fixture["fixture_id"])
            self.assertEqual(fixture["expected_blocker"], record["projection"]["status"], fixture["fixture_id"])
            self.assertIsNone(record["projection"]["claim"], fixture["fixture_id"])
            self.assertEqual([], fam2_lexical_producer.validate_formation_record(record), fixture["fixture_id"])

    def test_sound_plural_resembling_broken_pattern_is_not_broken(self) -> None:
        fixture = next(item for item in self.fixtures if item["fixture_id"] == "sound-plural-not-broken")
        record = fam2_lexical_producer.produce_record(fixture["row"], entries=self.entries)
        value = next(fact["fact_value"] for fact in record["facts"] if fact["fact_type"] == "formation_evidence")
        self.assertEqual("sound_masculine_plural", value["sub_shape"])
        self.assertNotEqual("broken_plural", value["sub_shape"])

    def test_sufaha_canary_label_without_entry_singular_abstains(self) -> None:
        fixture = next(item for item in self.fixtures if item["fixture_id"] == "sufaha-label-only-canary")
        record = fam2_lexical_producer.produce_record(fixture["row"], entries=self.entries)
        self.assertEqual("entry_lookup_missing", record["projection"]["status"])
        self.assertFalse(any(fact["fact_type"] == "formation_evidence" for fact in record["facts"]))

    def test_pattern_matcher_rejects_orthography_variants(self) -> None:
        self.assertIsNone(
            fam2_lexical_producer.match_registered_pattern(
                "حِزْب", "اَلْأَحْزَاب", "broken.fi3l_to_af3aal", self.fixtures
            )
        )


if __name__ == "__main__":
    unittest.main()
