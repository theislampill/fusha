#!/usr/bin/env python3
"""Red-first contract tests for the PROOF-V real verb proof."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import proofv_shared_compiler as compiler  # noqa: E402
from tools import proofv_verb_producer as producer  # noqa: E402
from tools import fact_projectors  # noqa: E402


FIXTURES = ROOT / "qamus" / "examples" / "proof-verb" / "producer-fixtures.jsonl"


def _fixtures() -> list[dict]:
    return [json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()]


class ProofVProducerTests(unittest.TestCase):
    def test_registered_projector_is_candidate_only(self) -> None:
        fixture = _fixtures()[0]
        contract = fact_projectors.REGISTRY.contract(fact_projectors.PROOFV_VERB_PROJECTOR_ID)
        result = fact_projectors.REGISTRY.run(
            fact_projectors.PROOFV_VERB_PROJECTOR_ID,
            source_row=fixture["row"],
            nearest=fixture["nearest"],
        )
        self.assertEqual("qamus.projector_record.v1", contract["schema"])
        self.assertEqual("candidate", result["status"])
        self.assertEqual("proofv_verb_evidence", result["candidate"]["fact_type"])
        self.assertFalse(result["materialization_allowed"])

    def test_target_has_one_primary_class_per_written_base_letter(self) -> None:
        fixture = _fixtures()[0]
        proof = producer.build_verb_facts(fixture["row"], nearest=fixture["nearest"])
        self.assertEqual("candidate_with_source_gaps", proof["status"])
        self.assertEqual("فَٱتَّبِعْنِىٓ", proof["canonical_occurrence"]["surface"])
        ownership = proof["sarf"]["letter_ownership"]
        self.assertEqual(list(range(7)), [item["base_letter_index"] for item in ownership])
        self.assertEqual(7, len({item["base_letter_index"] for item in ownership}))
        self.assertEqual("qg-result-fa", ownership[0]["display_class"])
        self.assertEqual("hamzat_al_wasl", ownership[1]["owner_class"])
        self.assertEqual("qg-root-radical", ownership[2]["display_class"])
        self.assertEqual(["root_radical_1", "derivative_infix"], ownership[2]["shared_roles"])
        self.assertEqual("qg-protective-nun", ownership[5]["display_class"])
        self.assertEqual("sarf.protective_nun", ownership[5]["typed_kind"])
        self.assertNotIn("particle", ownership[5]["display_class"])
        self.assertEqual("qg-object-pronoun", ownership[6]["display_class"])

    def test_treatment_c_and_source_gap_are_explicit(self) -> None:
        fixture = _fixtures()[0]
        proof = producer.build_verb_facts(fixture["row"], nearest=fixture["nearest"])
        self.assertEqual("VIII", proof["sarf"]["form"])
        self.assertEqual("imperative", proof["sarf"]["mood"])
        self.assertEqual("2", proof["sarf"]["person"])
        self.assertEqual("active", proof["sarf"]["voice"])
        gemination = proof["sarf"]["gemination"]
        self.assertEqual("C_shared_written_letter", gemination["treatment"])
        self.assertIn(gemination["idgham_classification"], {
            "A_clean_split",
            "B_shared_letter_clean_split",
            "C_fused_boundary",
            "D_ambiguous_boundary",
        })
        self.assertFalse(gemination["split_authorized"])
        self.assertTrue(any(fact["fact_type"] == "nahw_dependency" and fact["fact_value"].get("status") == "unresolved" for fact in proof["facts"]))
        self.assertTrue(proof["uncertainty"]["source_gap"])

    def test_adversarial_rows_abstain_without_laundering_claims(self) -> None:
        for fixture in _fixtures()[1:]:
            proof = producer.build_verb_facts(fixture["row"], nearest=fixture.get("nearest"))
            self.assertEqual(fixture["expected_status"], proof["status"], fixture["fixture_id"])
            self.assertTrue(proof["uncertainty"]["routes"], fixture["fixture_id"])
            self.assertFalse(proof["materialization_allowed"], fixture["fixture_id"])


class ProofVCompilerTests(unittest.TestCase):
    def test_shared_compiler_requires_canonical_letter_fact(self) -> None:
        fixture = _fixtures()[0]
        facts = producer.build_verb_facts(fixture["row"], nearest=fixture["nearest"])
        without_canonical_fact = dict(facts)
        without_canonical_fact["facts"] = [
            fact for fact in facts["facts"] if fact["fact_type"] != "proofv_letter_ownership"
        ]
        with self.assertRaises(ValueError):
            compiler.compile_payload(without_canonical_fact, appearances=[])

    def test_shared_payload_has_at_rest_both_views_hover_and_readback(self) -> None:
        fixture = _fixtures()[0]
        facts = producer.build_verb_facts(fixture["row"], nearest=fixture["nearest"])
        payload = compiler.compile_payload(facts, appearances=[{"appearance_index": 1, "surface_kind": "reader"}])
        self.assertEqual("فَٱتَّبِعْنِىٓ", payload["at_rest"]["surface"])
        self.assertTrue(payload["at_rest"]["exact_reconstruction"]["passed"])
        self.assertEqual(payload["payload_id"], payload["compact"]["payload_id"])
        self.assertEqual(payload["payload_id"], payload["expanded"]["payload_id"])
        self.assertTrue(payload["hover"]["text"].startswith("PENDING"))
        self.assertEqual("candidate_with_source_gaps", payload["candidate_status"])
        self.assertTrue(payload["readback"]["same_payload_identity"])
        self.assertTrue(payload["per_appearance"])
        self.assertIn("Ṣarf — how this piece forms the word", payload["expanded"]["sarf"]["label"])
        self.assertIn("Naḥw — what this piece does here", payload["expanded"]["nahw"]["label"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
