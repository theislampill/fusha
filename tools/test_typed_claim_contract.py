#!/usr/bin/env python3
"""Red-first tests for the F-A governed typed-claim contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools import typed_claim_contract as tcc


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "qamus" / "examples" / "fa-contract"


def read_jsonl(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TypedClaimBoundaryTests(unittest.TestCase):
    def test_prose_only_projection_is_rejected_as_not_a_typed_fact(self) -> None:
        row = read_jsonl("prose-only.invalid.jsonl")[0]
        errors = tcc.validate_contract_record(row)
        self.assertTrue(
            any(tcc.PROSE_ONLY_ERROR in error for error in errors),
            errors,
        )

    def test_governed_candidate_without_claim_binding_is_rejected(self) -> None:
        row = read_jsonl("tranche1-canary.valid.jsonl")[0]
        row["projection"]["claim"] = None
        errors = tcc.validate_contract_record(row)
        self.assertTrue(
            any(tcc.PROSE_ONLY_ERROR in error for error in errors),
            errors,
        )

    def test_tranche1_canary_has_governed_fact_backing(self) -> None:
        row = read_jsonl("tranche1-canary.valid.jsonl")[0]
        self.assertEqual([], tcc.validate_contract_record(row))

    def test_alias_normalization_is_recursive_and_does_not_mutate_input(self) -> None:
        fixture = read_jsonl("alias-normalization.jsonl")[0]
        source = fixture["input"]
        normalized = tcc.normalize_aliases(source)
        self.assertEqual(fixture["expected"], normalized)
        self.assertEqual("qg-negative", source["segments"][0]["qg_class"])
        self.assertEqual([], tcc.assert_no_deprecated_aliases(normalized))

    def test_generated_output_rejects_deprecated_alias(self) -> None:
        errors = tcc.assert_no_deprecated_aliases({"qg_class": "qg-negative"})
        self.assertTrue(any("qg-negative" in error for error in errors), errors)

    def test_legacy_valid_record_is_internal_only(self) -> None:
        row = json.loads((FIXTURES / "legacy-valid.jsonl").read_text(encoding="utf-8"))
        self.assertEqual([], tcc.validate_legacy_record(row))
        bad = copy.deepcopy(row)
        bad["learner_visible"] = True
        errors = tcc.validate_legacy_record(bad)
        self.assertTrue(any("learner_visible" in error for error in errors), errors)

    def test_unresolved_statuses_have_plain_english_statements(self) -> None:
        mapping = tcc.load_unresolved_language_map()
        expected = {"unresolved", "source_gap", "producer_pending", "syntax_pending", "blocked"}
        self.assertEqual(expected, set(mapping))
        for status in expected:
            statement = tcc.learner_statement_for(status)
            self.assertTrue(statement)
            self.assertNotIn("qg-", statement)
            self.assertNotIn("fact_id", statement)
            self.assertNotIn("projector", statement)

    def test_public_unresolved_projection_requires_a_mapped_status(self) -> None:
        row = read_jsonl("tranche1-canary.valid.jsonl")[0]
        row["projection"]["status"] = "source_gap"
        row["projection"]["claim"] = None
        row["projection"]["unresolved_status"] = "source_gap"
        row["projection"]["learner_visible"] = True
        row["projection"]["learner_statement"] = tcc.learner_statement_for("source_gap")
        row["facts"][0]["unresolved_blockers"] = [
            {"blocker_id": "missing-certification", "reason": "Candidate evidence is not certification."}
        ]
        self.assertEqual([], tcc.validate_contract_record(row))

        row["projection"]["unresolved_status"] = "unknown_status"
        errors = tcc.validate_contract_record(row)
        self.assertTrue(any("unresolved language mapping" in error for error in errors), errors)

    def test_malformed_contract_shapes_fail_closed_without_exceptions(self) -> None:
        samples = [
            {"schema": "qamus.typed_claim_contract.v1", "facts": "bad"},
            {"schema": "qamus.typed_claim_contract.v1", "facts": ["bad"]},
            {"schema": "qamus.typed_claim_contract.v1", "canonical_occurrence": "bad", "facts": []},
            {"schema": "qamus.typed_claim_contract.v1", "facts": [], "projection": "bad"},
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                errors = tcc.validate_contract_record(sample)
                self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
