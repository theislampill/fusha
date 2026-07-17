"""Red-first tests for the FAM3 number-word formation producer."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "qamus" / "examples" / "fam3-numbers"


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class FAM3NumberProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tools import fam3_number_producer

        cls.producer = fam3_number_producer
        cls.entries = _load_jsonl(FIXTURES / "entry-fixtures.jsonl")
        cls.fixtures = _load_jsonl(FIXTURES / "producer-fixtures.jsonl")
        cls.patterns = cls.producer.load_pattern_registry(FIXTURES / "pattern-registry.jsonl")

    def _fixture(self, fixture_id: str) -> dict:
        return next(item for item in self.fixtures if item["fixture_id"] == fixture_id)

    def test_positive_fixture_set_covers_six_number_shapes(self) -> None:
        positives = [item for item in self.fixtures if item["expected_status"] == "candidate"]
        self.assertGreaterEqual(len(positives), 6)
        expected = {
            "bare_cardinal",
            "gender_polarity_cardinal",
            "ordinals",
            "compound_11_19",
            "tens",
            "other_number_form",
        }
        self.assertTrue(expected <= {item["expected_sub_shape"] for item in positives})

    def test_positive_records_have_typed_reconstructible_number_facts(self) -> None:
        for fixture in self.fixtures:
            if fixture["expected_status"] != "candidate":
                continue
            record = self.producer.produce_record(
                fixture["row"], entries=self.entries, pattern_registry=self.patterns
            )
            self.assertEqual("projection_input", record["record_type"], fixture["fixture_id"])
            self.assertEqual([], self.producer.validate_number_record(record), fixture["fixture_id"])
            formation = [fact for fact in record["facts"] if fact["fact_type"] == "formation_evidence"]
            base = [fact for fact in record["facts"] if fact["fact_type"] == "entry_base_attestation"]
            self.assertEqual(1, len(formation), fixture["fixture_id"])
            self.assertEqual(1, len(base), fixture["fixture_id"])
            self.assertEqual(fixture["expected_sub_shape"], formation[0]["fact_value"]["sub_shape"])
            self.assertTrue(formation[0]["fact_value"]["reconstruction_proof"]["passed"])
            self.assertFalse(record["projection"]["materialization_target"]["live_mutation_allowed"])

    def test_adversarial_fixture_set_contains_required_routes(self) -> None:
        negatives = [item for item in self.fixtures if item["expected_status"] != "candidate"]
        self.assertGreaterEqual(len(negatives), 6)
        ids = {item["fixture_id"] for item in negatives}
        self.assertIn("label-only-ordinal", ids)
        self.assertIn("wrong-gender-seven", ids)
        self.assertIn("homograph-seven-number-lion", ids)
        self.assertIn("context-only-entry", ids)

    def test_adversarial_records_are_typed_unresolved_and_claimless(self) -> None:
        for fixture in self.fixtures:
            if fixture["expected_status"] == "candidate":
                continue
            record = self.producer.produce_record(
                fixture["row"], entries=self.entries, pattern_registry=self.patterns
            )
            self.assertEqual("unresolved_projection", record["record_type"], fixture["fixture_id"])
            blockers = {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers", [])
            }
            self.assertIn(fixture["expected_blocker"], blockers, fixture["fixture_id"])
            self.assertIsNone(record["projection"]["claim"], fixture["fixture_id"])
            self.assertFalse(
                any(fact["fact_type"] == "formation_evidence" for fact in record["facts"]),
                fixture["fixture_id"],
            )
            self.assertEqual([], self.producer.validate_number_record(record), fixture["fixture_id"])

    def test_wrong_gender_form_never_certifies(self) -> None:
        fixture = self._fixture("wrong-gender-seven")
        record = self.producer.produce_record(
            fixture["row"], entries=self.entries, pattern_registry=self.patterns
        )
        blockers = {
            blocker["blocker_id"]
            for fact in record["facts"]
            for blocker in fact.get("unresolved_blockers", [])
        }
        self.assertIn("gender_polarity_mismatch", blockers)

    def test_homograph_number_noun_is_quarantined(self) -> None:
        fixture = self._fixture("homograph-seven-number-lion")
        record = self.producer.produce_record(
            fixture["row"], entries=self.entries, pattern_registry=self.patterns
        )
        self.assertEqual("blocked", record["projection"]["status"])
        self.assertFalse(any(fact["fact_type"] == "formation_evidence" for fact in record["facts"]))

    def test_label_only_ordinal_cannot_create_a_base(self) -> None:
        fixture = self._fixture("label-only-ordinal")
        record = self.producer.produce_record(
            fixture["row"], entries=self.entries, pattern_registry=self.patterns
        )
        self.assertIn(
            "entry_lookup_missing",
            {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers", [])
            },
        )
        self.assertFalse(any(fact["fact_type"] == "formation_evidence" for fact in record["facts"]))

    def test_orthography_near_miss_is_not_repaired(self) -> None:
        fixture = self._fixture("hamza-seat-near-miss")
        record = self.producer.produce_record(
            fixture["row"], entries=self.entries, pattern_registry=self.patterns
        )
        self.assertIn(
            "orthography_mismatch",
            {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers", [])
            },
        )

    def test_exact_entry_variant_uses_registered_number_rule(self) -> None:
        fixture = self._fixture("thousands-plural-entry-variant")
        record = self.producer.produce_record(
            fixture["row"], entries=self.entries, pattern_registry=self.patterns
        )
        self.assertEqual("candidate", record["projection"]["status"])
        formation = next(fact for fact in record["facts"] if fact["fact_type"] == "formation_evidence")
        self.assertEqual("cardinal.base_to_number_form", formation["fact_value"]["pattern_id"])

    def test_number_learner_payload_has_family_namespace_and_shape_copy(self) -> None:
        fixture = self._fixture("tens-fourty")
        record = self.producer.produce_record(
            fixture["row"], entries=self.entries, pattern_registry=self.patterns
        )
        learner_copy = record["projection"]["public_payload"]["learner_copy"]
        self.assertTrue(learner_copy["payload_id"].startswith("fd.fam3.payload:"))
        self.assertIn("tens form", learner_copy["nahw"])

    def test_fixture_boundary_validator_is_clean(self) -> None:
        from tools import validate_fam3_numbers

        self.assertEqual([], validate_fam3_numbers.validate_fixture_boundary(FIXTURES))

    def test_report_builder_emits_full_calibration_sections(self) -> None:
        from tempfile import TemporaryDirectory
        from tools import build_fam3_report

        with TemporaryDirectory() as directory:
            output = Path(directory) / "FAM3-REPORT.md"
            build_fam3_report.build_report(FIXTURES / "generated", output)
            report = output.read_text(encoding="utf-8")
        self.assertIn("Precision + abstention by sub-shape", report)
        self.assertIn("Per-row outcome table", report)
        self.assertIn("Exact nonclaims", report)
        self.assertIn("Compounding Impact", report)
        self.assertEqual(57, report.count("| quran:"))

    def test_quranic_number_spelling_is_classified_before_abstention(self) -> None:
        self.assertEqual("tens", self.producer.classify_sub_shape({"surface": "ثَمَٰنِينَ"}))
        self.assertEqual("tens", self.producer.classify_sub_shape({"surface": "ثَلَٰثُونَ"}))
        self.assertEqual("other_number_form", self.producer.classify_sub_shape({"surface": "ٱثْنَيْنِ"}))


if __name__ == "__main__":
    unittest.main()
