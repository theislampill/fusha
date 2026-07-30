"""Red-first acceptance tests for the real PROOF-N noun chain."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import proofn_noun_sufaha as proofn
from tools.validate_proofn_noun_sufaha import validate_proof


ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = ROOT / "qamus" / "examples" / "proof-noun-sufaha"


def load_committed_proof() -> dict:
    return proofn.load_proof_artifacts(PROOF_DIR)


class ProofNNounSufahaTests(unittest.TestCase):
    def test_json_writer_pins_lf_newline_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "nested" / "review.json"
            with mock.patch.object(Path, "write_text", autospec=True) as write_text:
                proofn._write_json(output, {})
            write_text.assert_called_once_with(
                output,
                "{}\n",
                encoding="utf-8",
                newline="\n",
            )

    def test_json_writer_emits_lf_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "nested" / "review.json"
            proofn._write_json(output, {"surface": "سُفَهَاء", "status": "candidate"})
            self.assertEqual(
                (
                    '{\n'
                    '  "status": "candidate",\n'
                    '  "surface": "سُفَهَاء"\n'
                    '}\n'
                ).encode("utf-8"),
                output.read_bytes(),
            )

    def test_committed_proof_passes(self) -> None:
        proof = load_committed_proof()
        self.assertEqual([], validate_proof(proof))

    def test_real_identity_split_and_sense_card_example_chain(self) -> None:
        proof = load_committed_proof()
        identity = proof["manifest"]["identity"]
        self.assertEqual("1ffcc554ec44", identity["lexical_entry_id"])
        self.assertEqual("c59a0161fac8", identity["page_context_entry_id"])
        self.assertEqual("2:13:12", identity["canonical_location"])
        self.assertEqual("sense:1ffcc554ec44:s1", identity["sense_node_id"])
        self.assertEqual("2:13", identity["card_ref"])
        self.assertEqual("سُفَهَاء", identity["documented_plural_form"])

    def test_certified_packet_and_required_morphology_are_bound(self) -> None:
        proof = load_committed_proof()
        contract = proof["contract"]
        self.assertEqual(11, len(contract["facts"]))
        self.assertTrue(all(fact["certification"]["status"] == "certified" for fact in contract["facts"]))
        comparison = proof["payload"]["comparison"]
        self.assertEqual("سَفِيه", comparison["singular"]["surface"])
        self.assertEqual("سُفَهَاء", comparison["plural"]["surface"])
        self.assertEqual("س ف ه", comparison["root"])
        self.assertEqual("فَعِيل", comparison["singular"]["pattern"])
        self.assertEqual("فُعَلَاء", comparison["plural"]["pattern"])
        self.assertEqual("ي", comparison["removed"])
        self.assertEqual(["ا", "ء"], comparison["introduced"])

    def test_graph_contains_full_candidate_repair_chain_and_both_edges(self) -> None:
        proof = load_committed_proof()
        edges = proof["edges"]
        edge_types = {edge["edge_type"] for edge in edges}
        for edge_type in (
            "page_context_entry_edge",
            "source_card_edge",
            "selected_example_edge",
            "display_local_to_canonical_crosswalk_edge",
            "projection_input_edge",
            "certified_fact_attachment_edge",
            "form_entry_edge",
            "lexeme_entry_edge",
            "sense_entry_edge",
            "root_family_edge",
        ):
            self.assertIn(edge_type, edge_types)
        page = [edge for edge in edges if edge["edge_type"] == "page_context_entry_edge"]
        lexeme = [edge for edge in edges if edge["edge_type"] == "lexeme_entry_edge"]
        self.assertEqual({"entry:c59a0161fac8"}, {edge["to_node_id"] for edge in page})
        self.assertEqual({"entry:1ffcc554ec44"}, {edge["to_node_id"] for edge in lexeme})
        self.assertTrue(all(edge["status"] in {"candidate", "deterministic_exact"} for edge in edges))
        self.assertTrue(all(edge.get("evidence") for edge in edges))

    def test_at_rest_compact_expanded_hover_and_appearance_parity(self) -> None:
        proof = load_committed_proof()
        payload = proof["payload"]
        self.assertEqual("السُّفَهَاءُ", "".join(span["surface"] for span in payload["at_rest_spans"]))
        self.assertEqual([(0, 2), (2, 11), (11, 12)], [(span["start"], span["end"]) for span in payload["at_rest_spans"]])
        self.assertEqual(payload["compact_view"]["payload_id"], payload["expanded_view"]["payload_id"])
        self.assertEqual(payload["compact_view"]["payload_id"], payload["rich_hover"]["payload_id"])
        self.assertIn("Ṣarf — how this piece forms the word", payload["expanded_view"]["sarf"])
        self.assertIn("Naḥw — what this piece does here", payload["expanded_view"]["nahw"])
        self.assertEqual(2, len(payload["appearance_parity"]["appearances"]))
        self.assertTrue(all(item["same_payload_id"] for item in payload["appearance_parity"]["appearances"]))

    def test_boundary_and_unresolved_tension_are_explicit(self) -> None:
        proof = load_committed_proof()
        self.assertEqual("pre_apply_not_authorized", proof["payload"]["authorization_state"])
        self.assertFalse(proof["payload"]["live_mutation_allowed"])
        self.assertEqual("declared_not_measured", proof["payload"]["readback_target"]["status"])
        self.assertEqual("unresolved", proof["contract"]["tension_records"][0]["status"])

    def test_red_missing_lexeme_edge(self) -> None:
        proof = load_committed_proof()
        proof["edges"] = [edge for edge in proof["edges"] if edge["edge_type"] != "lexeme_entry_edge"]
        self.assertTrue(any("lexeme" in error for error in validate_proof(proof)))

    def test_red_page_context_promotion(self) -> None:
        proof = load_committed_proof()
        mutated = copy.deepcopy(proof)
        for edge in mutated["edges"]:
            if edge["edge_type"] == "page_context_entry_edge":
                edge["edge_type"] = "lexeme_entry_edge"
        self.assertTrue(any("page-context" in error for error in validate_proof(mutated)))

    def test_red_missing_appearance_parity(self) -> None:
        proof = load_committed_proof()
        mutated = copy.deepcopy(proof)
        mutated["edges"] = [
            edge for edge in mutated["edges"]
            if not (edge["edge_type"] == "rendered_appearance_edge" and edge["to_node_id"].endswith(":2"))
        ]
        self.assertTrue(any("appearance" in error for error in validate_proof(mutated)))

    def test_red_case_span_and_n_lang_boundary(self) -> None:
        proof = load_committed_proof()
        mutated = copy.deepcopy(proof)
        mutated["payload"]["at_rest_spans"][-1]["start"] = 10
        mutated["payload"]["rich_hover"]["learner_explanation"] += " MCP"
        mutated["payload"]["authorization_state"] = "live"
        errors = validate_proof(mutated)
        self.assertTrue(any("span" in error for error in errors))
        self.assertTrue(any("N-LANG" in error for error in errors))
        self.assertTrue(any("authorization" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
