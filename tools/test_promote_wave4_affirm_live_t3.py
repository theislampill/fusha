#!/usr/bin/env python3
"""Red-first tests for the wave-4 affirm-live T3 due-process writer."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools import promote_wave4_affirm_live_t3 as subject


ROOT = Path(__file__).resolve().parents[1]
PACKETS = (
    ROOT
    / "qamus"
    / "indexes"
    / "largelexicon"
    / "crosswalk-gap"
    / "two-vote"
    / "packets-wave-04.jsonl"
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class TripleGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.morphology = subject.load_morphology()
        cls.packet_by_loc = {row["canonical_location"]: row for row in read_jsonl(PACKETS)}

    def test_documented_form_lookup_does_not_treat_usage_phrase_as_token_ownership(self) -> None:
        packet = self.packet_by_loc["2:158:6"]
        result = subject.deterministic_zero_overlap(packet, self.morphology)
        self.assertTrue(result["passed"])
        self.assertEqual(result["overlaps"], [])
        self.assertNotIn("61c3bedee211", result["target_documented_entry_ids"])

    def test_explicit_root_overlap_fails_closed(self) -> None:
        packet = copy.deepcopy(self.packet_by_loc["2:128:9"])
        packet["morphology_record"]["target_self"]["root"]["value"] = "س ل م"
        result = subject.deterministic_zero_overlap(packet, self.morphology)
        self.assertFalse(result["passed"])
        self.assertIn("deterministic_zero_overlap", result["failed_gate"])
        self.assertTrue(any(item["overlap_kind"] == "root" for item in result["overlaps"]))

    def test_blank_root_noun_documented_form_overlap_fails_closed(self) -> None:
        packet = copy.deepcopy(self.packet_by_loc["2:128:9"])
        carrier = next(
            row for row in packet["candidate_carriers"]
            if not row["candidate_entry_content"]["root"]["value"]
        )
        carrier["entry_id"] = "synthetic-blank-root"
        carrier["candidate_entry_content"]["entry_source_address"] = (
            "qamus/data/current/entries.jsonl#id=synthetic-blank-root"
        )
        carrier["candidate_entry_content"]["section"]["value"] = "noun"
        carrier["candidate_entry_content"]["matching_usage_examples"] = [
            {"usage_forms": [packet["live_surface"]]}
        ]
        result = subject.deterministic_zero_overlap(packet, self.morphology)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any(item["overlap_kind"] == "blank_root_noun_documented_form" for item in result["overlaps"])
        )

    def test_gate_order_names_first_failure(self) -> None:
        packet = self.packet_by_loc["2:128:9"]
        vote_b = {"proposed_conclusion": "wrong"}
        t3 = {"verdict": subject.T3_CONCLUSION}
        result = subject.evaluate_triple_gate(packet, vote_b, t3, self.morphology)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_gate"], "gate_2_b_vote")


class EndToEndTests(unittest.TestCase):
    def test_authoritative_inputs_pass_136_and_double_run_is_identical(self) -> None:
        first = subject.build(ROOT / ".lane-inputs")
        second = subject.build(ROOT / ".lane-inputs")
        self.assertEqual(first.output_bytes(), second.output_bytes())
        self.assertEqual(first.report["counts"]["gate_pass"], 136)
        self.assertEqual(first.report["counts"]["gate_fail"], 0)
        self.assertEqual(first.report["queue_arithmetic"]["physical_rows"], [4854, 4854])
        self.assertEqual(first.report["queue_arithmetic"]["active_live_only_rows"], [4843, 4843])

    def test_gate_failure_stays_review_required_with_named_t4_packet(self) -> None:
        row = {
            "canonical_location": "2:128:9",
            "review_state": "two_vote_disagreement_tier_routing",
        }
        gate = {
            "passed": False,
            "failed_gate": "gate_3_t3_verdict",
            "gates": {"gate_3_t3_verdict": {"passed": False}},
        }
        failed = subject.mutate_queue([row], {"2:128:9": gate}, {})[0]
        self.assertEqual(failed["review_state"], "two_vote_disagreement_tier_routing")
        self.assertEqual(failed["t4_packet"]["failed_gate"], "gate_3_t3_verdict")


if __name__ == "__main__":
    unittest.main()
