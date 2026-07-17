"""RED-first and contract tests for the FAM4 finite-verb producer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import fam4_finite_verb_producer as producer


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "qamus" / "examples" / "fam4-finite-verbs"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class Fam4FiniteVerbProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = _jsonl(FIXTURES / "entry-fixtures.jsonl")
        cls.fixtures = _jsonl(FIXTURES / "producer-fixtures.jsonl")
        cls.registry = producer.load_affix_registry(FIXTURES / "verb-affix-registry.jsonl")

    def record(self, fixture_id: str) -> dict:
        item = next(item for item in self.fixtures if item["fixture_id"] == fixture_id)
        return producer.produce_record(item["row"], entries=self.entries, affix_registry=self.registry)

    def test_positive_fixture_matrix(self) -> None:
        positives = [item for item in self.fixtures if item["expected_status"] == "candidate"]
        self.assertGreaterEqual(len(positives), 6)
        for item in positives:
            record = self.record(item["fixture_id"])
            self.assertEqual(record["projection"]["status"], "candidate", item["fixture_id"])
            self.assertEqual(producer.validate_finite_verb_record(record), [], item["fixture_id"])
            fact = next(fact for fact in record["facts"] if fact["fact_type"] == "finite_verb_evidence")
            self.assertEqual(fact["fact_value"]["pattern_id"], item["expected_pattern"])
            self.assertTrue(fact["fact_value"]["reconstruction_proof"]["passed"])

    def test_required_adversarial_routes(self) -> None:
        required = {
            "label-only-tense-no-affix": "fam4.label_only_affix_evidence_missing",
            "weak-hidden-radical": "fam4.weak_root_pattern_unresolved",
            "derived-form-owner-gated": "fam4.owner_gated",
            "subject-object-suffix-boundary": "fam4.subject_object_suffix_ambiguity",
            "nonverb-swept-into-family": "fam4.surface_not_finite_verb",
        }
        for fixture_id, blocker in required.items():
            record = self.record(fixture_id)
            self.assertNotEqual(record["projection"]["status"], "candidate", fixture_id)
            self.assertIsNone(record["projection"]["claim"], fixture_id)
            blockers = {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers", [])
            }
            self.assertIn(blocker, blockers, fixture_id)
            self.assertEqual(producer.validate_finite_verb_record(record), [], fixture_id)

    def test_subject_and_object_roles_do_not_collapse(self) -> None:
        subject = self.record("positive-past-1cp-subject")
        object_record = self.record("positive-object-suffix")
        subject_fact = next(fact for fact in subject["facts"] if fact["fact_type"] == "finite_verb_evidence")
        object_fact = next(fact for fact in object_record["facts"] if fact["fact_type"] == "finite_verb_evidence")
        self.assertEqual(subject_fact["fact_value"]["affixes"][-1]["role"], "subject_marker")
        self.assertEqual(object_fact["fact_value"]["affixes"][-1]["role"], "object_suffix")
        self.assertEqual(object_fact["fact_value"]["affixes"][-1]["class"], "qg-object-pronoun")

    def test_n_lang_labels_and_candidate_gate(self) -> None:
        record = self.record("positive-past-1cp-subject")
        payload = record["projection"]["public_payload"]
        self.assertEqual(payload["authorization_state"], "pre_apply_not_authorized")
        self.assertFalse(payload["public_materialization_allowed"])
        self.assertFalse(payload["live_mutation_allowed"])
        learner = payload["learner_copy"]
        self.assertTrue(learner["n_lang_clean"])
        self.assertIn("Ṣarf — how this piece forms the word", learner["sarf"])
        self.assertIn("Naḥw — what this piece does here", learner["nahw"])

    def test_form_v_marker_is_owner_gated(self) -> None:
        marker = next(item for item in self.registry if item["pattern_id"] == "derived.form_v_vi.prefix_t")
        self.assertFalse(marker["supported"])
        self.assertEqual(marker["marker_class"], "derivative_prefix_form_v")
        self.assertEqual(marker["owner_gate"], "derived_verbs")


if __name__ == "__main__":
    unittest.main()
