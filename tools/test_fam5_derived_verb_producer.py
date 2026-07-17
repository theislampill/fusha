"""RED-first and contract tests for the FAM5 derived-verb producer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import fam5_derived_verb_producer as producer


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "qamus" / "examples" / "fam5-derived-verbs"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class Fam5DerivedVerbProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = _jsonl(FIXTURES / "entry-fixtures.jsonl")
        cls.fixtures = _jsonl(FIXTURES / "producer-fixtures.jsonl")
        cls.registry = producer.load_derived_form_registry(FIXTURES / "derived-form-registry.jsonl")

    def record(self, fixture_id: str) -> dict:
        item = next(item for item in self.fixtures if item["fixture_id"] == fixture_id)
        return producer.produce_record(item["row"], entries=self.entries, form_registry=self.registry)

    def test_positive_fixture_matrix(self) -> None:
        positives = [item for item in self.fixtures if item["expected_status"] == "candidate"]
        self.assertGreaterEqual(len(positives), 6)
        for item in positives:
            record = self.record(item["fixture_id"])
            self.assertEqual(record["projection"]["status"], "candidate", item["fixture_id"])
            self.assertEqual(producer.validate_derived_verb_record(record), [], item["fixture_id"])
            fact = next(fact for fact in record["facts"] if fact["fact_type"] == "derived_verb_evidence")
            self.assertEqual(fact["fact_value"]["template"]["pattern_id"], item["expected_pattern"])
            self.assertTrue(fact["fact_value"]["reconstruction_proof"]["passed"])

    def test_required_adversarial_routes(self) -> None:
        adversarial = [item for item in self.fixtures if item["expected_status"] != "candidate"]
        self.assertGreaterEqual(len(adversarial), 8)
        for item in adversarial:
            record = self.record(item["fixture_id"])
            self.assertNotEqual(record["projection"]["status"], "candidate", item["fixture_id"])
            self.assertIsNone(record["projection"]["claim"], item["fixture_id"])
            blockers = {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers", [])
            }
            self.assertIn(item["expected_blocker"], blockers, item["fixture_id"])
            self.assertEqual(producer.validate_derived_verb_record(record), [], item["fixture_id"])

    def test_surface_template_only_claim_abstains(self) -> None:
        record = self.record("surface-template-only")
        self.assertEqual(record["projection"]["status"], "source_gap")
        self.assertIsNone(record["projection"]["claim"])

    def test_form_viii_gemination_has_one_owned_written_letter(self) -> None:
        record = self.record("positive-form-viii-passive-geminate")
        value = next(fact for fact in record["facts"] if fact["fact_type"] == "derived_verb_evidence")["fact_value"]
        th_segments = [segment for segment in value["surface_segments"] if segment["surface"].startswith("ث")]
        self.assertEqual(len(th_segments), 1)
        self.assertEqual(th_segments[0]["role"], "root_radical_shared_2_3")
        self.assertEqual(value["gemination"]["treatment"], "C_shared_written_letter")
        self.assertFalse(value["gemination"]["split_authorized"])
        self.assertEqual(value["gemination"]["idgham_classification"], "B_shared_letter_clean_split")

    def test_letter_level_ownership_is_total_and_unique(self) -> None:
        for fixture_id in (
            "positive-form-ii-perfect",
            "positive-form-iv-perfect-1cs",
            "positive-form-viii-passive-geminate",
            "positive-quadriliteral",
        ):
            record = self.record(fixture_id)
            value = next(fact for fact in record["facts"] if fact["fact_type"] == "derived_verb_evidence")["fact_value"]
            ownership = value["letter_ownership"]
            self.assertEqual(len({item["base_letter_index"] for item in ownership}), len(ownership), fixture_id)
            self.assertEqual([item["base_letter_index"] for item in ownership], list(range(len(ownership))), fixture_id)
            self.assertTrue(all(item["owner_class"] for item in ownership), fixture_id)

    def test_n_lang_labels_and_candidate_gate(self) -> None:
        record = self.record("positive-form-iv-perfect-1cs")
        payload = record["projection"]["public_payload"]
        self.assertEqual(payload["authorization_state"], "pre_apply_not_authorized")
        self.assertFalse(payload["public_materialization_allowed"])
        self.assertFalse(payload["live_mutation_allowed"])
        learner = payload["learner_copy"]
        self.assertTrue(learner["n_lang_clean"])
        self.assertIn("Ṣarf — how this piece forms the word", learner["sarf"])
        self.assertIn("Naḥw — what this piece does here", learner["nahw"])

    def test_registry_uses_d3_marker_classes(self) -> None:
        by_pattern = {item["pattern_id"]: item for item in self.registry}
        self.assertEqual(by_pattern["derived.form_iv.perfect_active.1cs"]["derivational_class"], "derivative_prefix")
        self.assertEqual(by_pattern["derived.form_viii.perfect_passive.3fs"]["derivational_class"], "derivative_infix")
        self.assertEqual(by_pattern["derived.form_viii.perfect_passive.3fs"]["onset_class"], "hamzat_al_wasl")
        self.assertEqual(by_pattern["quadriliteral.perfect_active.3ms"]["marker_class"], "quadriliteral_root")

    def test_fam4_carrier_registries_are_loaded(self) -> None:
        affixes, weak = producer.load_carrier_registries()
        self.assertTrue(affixes)
        self.assertTrue(weak)
        self.assertTrue(any(item.get("owner_gate") == "derived_verbs" for item in affixes))
        self.assertTrue(any(item.get("owner_next") == "derived_verbs" for item in weak))


if __name__ == "__main__":
    unittest.main()
