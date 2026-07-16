"""Red-first tests for the F-D evidence compiler and proof artifacts."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools import fd_compiler
from tools.typed_claim_contract import validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
FD_EXAMPLES = ROOT / "qamus" / "examples" / "fd"


def _fact_id(seed: str) -> str:
    return "sha256:" + (seed.encode("utf-8").hex() * 64)[:64]


def _source_address(address: str = "quran:2:13:12") -> dict[str, str]:
    return {"address": address, "source_kind": "quran_token"}


def _contract(*, evidence_mode: str = "direct_source_attestation") -> dict:
    fact_id = _fact_id("a")
    projection_id = "fd.test_projection.v1"
    return {
        "schema": "qamus.typed_claim_contract.v1",
        "contract_version": "1.0.0",
        "contract_id": "fd.test.contract",
        "record_type": "projection_input",
        "canonical_occurrence": {
            "occurrence_id": "quran:2:13:12",
            "quran_loc": "2:13:12",
            "wbw_loc": "wbw:2:13:12",
            "surface": "السُّفَهَاءُ",
            "surface_length": len("السُّفَهَاءُ"),
            "entry_id": "1ffcc554ec44",
            "card_id": "fd-test-card",
        },
        "facts": [
            {
                "fact_id": fact_id,
                "fact_type": "lexical_relation",
                "fact_value": {"claim": "سُفَهَاء is the plural of سَفِيه"},
                "surface_spans": [
                    {"span_id": "body", "start": 2, "end": 11, "surface": "سُّفَهَاء", "role": "lexical_body"}
                ],
                "ownership": {"primary": {"owner_id": "fd-owner", "owner_type": "compiler_fixture"}, "secondary": []},
                "source": {"source_id": "quran:2:13:12", "source_kind": "quran_token"},
                "source_address": _source_address(),
                "certification": {"status": "certified", "reason": "fixture evidence is owner-certified"},
                "evidence": {
                    "status": "certified",
                    "confidence": "high",
                    "evidence_ids": ["fixture:e1"],
                    "summary": "The relation is explicitly attested in the supplied fixture.",
                },
                "evidence_mode": evidence_mode,
                "source_evidence": {
                    "structured_source_fact": {"claim": "plural relation attested"},
                    "source_addresses": [_source_address()],
                },
                "derivation_chain": [],
                "dependencies": {"fact_ids": [], "source_addresses": [_source_address()]},
                "contradiction_records": [],
                "producer": {"id": "tests.fd_compiler", "version": "1.0.0"},
                "rule_projector": {
                    "rule_id": "fd.test.rule",
                    "projector_id": projection_id,
                    "version": "1.0.0",
                },
                "guards": [],
                "defeaters": [],
                "unresolved_blockers": [],
                "dependent_fact_ids": [],
                "dependent_projection_ids": [projection_id],
            }
        ],
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": "fd-test.json",
                "field": "components[0]",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "The lexical relation is source-addressed.",
                "language": "en",
                "fact_bindings": [
                    {"fact_id": fact_id, "fact_field": "fact_value.claim", "surface_span_ids": ["body"]}
                ],
            },
            "learner_statement": "The lexical relation is source-addressed.",
            "public_payload": {"segments": [{"surface": "السُّفَهَاءُ"}]},
        },
    }


class EvidenceContractTests(unittest.TestCase):
    def test_evidence_extension_accepts_structured_source_fact(self) -> None:
        self.assertEqual(validate_contract_record(_contract()), [])

    def test_evidence_mode_is_closed(self) -> None:
        errors = validate_contract_record(_contract(evidence_mode="invented_mode"))
        self.assertTrue(any("evidence_mode" in error for error in errors), errors)

    def test_derived_fact_requires_chain_and_dependency(self) -> None:
        row = _contract(evidence_mode="deterministic_derivation_from_certified_facts")
        row["facts"][0]["source_evidence"] = {
            "structured_source_fact": {"claim": "derived"},
            "source_addresses": [_source_address()],
        }
        errors = validate_contract_record(row)
        self.assertTrue(any("derivation_chain" in error for error in errors), errors)

    def test_tension_reference_is_attached_without_changing_certification(self) -> None:
        row = _contract()
        row["tension_records"] = [
            {
                "tension_id": "tension:jamiid-mushtaq",
                "status": "unresolved",
                "statement": "The jām id/mushtaq classification remains unresolved.",
                "fact_ids": [row["facts"][0]["fact_id"]],
                "resolution_requirement": "owner_or_scholar_adjudication",
            }
        ]
        row["facts"][0]["contradiction_records"] = [
            {
                "tension_id": "tension:jamiid-mushtaq",
                "relation": "attached_unresolved",
                "note": "The unresolved tension does not alter the certified fact.",
            }
        ]
        self.assertEqual(validate_contract_record(row), [])
        self.assertEqual(row["facts"][0]["certification"]["status"], "certified")


class SufahaCompilerTests(unittest.TestCase):
    def test_checked_in_sufaha_fixture_has_owner_modes(self) -> None:
        contract = json.loads((FD_EXAMPLES / "sufaha-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_contract_record(contract), [])
        by_type = {fact["fact_type"]: fact for fact in contract["facts"]}
        self.assertEqual(by_type["singular_plural_relation"]["evidence_mode"], "direct_source_attestation")
        self.assertEqual(by_type["root"]["evidence_mode"], "cross_source_corroboration")
        self.assertEqual(by_type["paired_y_removal"]["evidence_mode"], "paired_form_inference")
        self.assertTrue(by_type["paired_y_removal"]["derivation_chain"])
        self.assertEqual(by_type["plural_lexical_body"]["evidence_mode"], "normalized_lexical_body")
        self.assertEqual(by_type["case_ending"]["evidence_mode"], "direct_source_attestation")
        self.assertEqual(by_type["governor_relation"]["evidence_mode"], "direct_source_attestation")
        self.assertEqual(len(contract["tension_records"]), 1)
        self.assertEqual(contract["tension_records"][0]["status"], "unresolved")

    def test_normalized_payload_reconstructs_and_is_live_safe(self) -> None:
        payload = json.loads((FD_EXAMPLES / "sufaha-normalized-public-payload.json").read_text(encoding="utf-8"))
        self.assertFalse(payload["live_mutation_allowed"])
        self.assertEqual("".join(span["surface"] for span in payload["at_rest_spans"]), "السُّفَهَاءُ")
        self.assertTrue(payload["exact_reconstruction"]["passed"])
        self.assertTrue(all(component["sarf"] or component["nahw"] for component in payload["components"]))
        self.assertTrue(all("learner_text" in component for component in payload["components"]))

    def test_html_views_consume_one_payload_and_expose_proofs(self) -> None:
        html = (FD_EXAMPLES / "sufaha-card.html").read_text(encoding="utf-8")
        self.assertIn('id="fd-normalized-payload"', html)
        self.assertIn("renderCompact(payload)", html)
        self.assertIn("renderExpanded(payload)", html)
        self.assertIn("document.fonts.check", html)
        self.assertIn("window.__reconCheck", html)
        self.assertIn("live_mutation_allowed=false", html)

    def test_real_render_proof_records_font_reconstruction_and_same_payload(self) -> None:
        proof = json.loads((FD_EXAMPLES / "render-proof.json").read_text(encoding="utf-8"))
        self.assertTrue(proof["font_check"])
        self.assertTrue(proof["exact_reconstruction"])
        self.assertTrue(proof["compact_present"])
        self.assertTrue(proof["expanded_present"])
        self.assertTrue(proof["same_payload_identity"])
        self.assertFalse(proof["live_mutation_allowed"])

    def test_entry_reciprocity_and_repeated_family_fixture(self) -> None:
        proof = json.loads((FD_EXAMPLES / "sufaha-parity-fixture.json").read_text(encoding="utf-8"))
        self.assertTrue(proof["entry_reciprocity"]["occurrence_to_entry"])
        self.assertTrue(proof["entry_reciprocity"]["entry_to_occurrence"])
        self.assertTrue(proof["repeated_appearance_parity"]["same_family_payload_id"])
        self.assertFalse(proof["repeated_appearance_parity"]["page_trace_inferred"])


class CandidateMatrixTests(unittest.TestCase):
    def test_report_has_exactly_the_twelve_requested_metrics(self) -> None:
        report = json.loads((ROOT / "fd-455-report.json").read_text(encoding="utf-8"))
        expected = {
            "rows compiling successfully",
            "rows failing linguistic consistency",
            "rows missing span ownership",
            "rows missing learner-language fields",
            "rows missing entry linkage",
            "rows missing a projector",
            "rows requiring F-B morphology producers",
            "rows requiring F-C naḥw producers",
            "rows routed to source/scholar review",
            "repeated page appearances covered",
            "parity failures",
            "exact reconstruction failures",
        }
        self.assertEqual(set(report["metrics"]), expected)
        self.assertEqual(report["verified_row_count"], 455)

    def test_verdicts_are_reproducible_jsonl_and_have_primary_blockers(self) -> None:
        path = ROOT / "fd-455-verdicts.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 455)
        self.assertTrue(all(row["compile_mode"] == "candidate" for row in rows))
        self.assertTrue(all(row["primary_blocker"] for row in rows))
        self.assertTrue(all(row["live_mutation_allowed"] is False for row in rows))


if __name__ == "__main__":
    unittest.main()
