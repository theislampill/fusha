#!/usr/bin/env python3
"""Red-first tests for the Repair1 graph-repair families."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.build_occurrence_appearance_index import build_index
from tools.build_typed_edge_crosswalk import build_graph
from tools.validate_typed_edge_graph import validate_graph


FIXTURES = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "repair1"
EDGE_FIXTURES = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "edges"


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class Repair1GraphFamilyTests(unittest.TestCase):
    def test_guarded_match_emits_exact_edges_and_reclassifies_mismatch(self):
        from tools.build_repair1_graph_families import build_deterministic_repairs

        entries = read_jsonl(EDGE_FIXTURES / "entries.fixture.jsonl")[:1]
        rows = read_jsonl(FIXTURES / "deterministic-debt.fixture.jsonl")
        result = build_deterministic_repairs(rows, entries, [])

        self.assertEqual(result["metrics"]["input_rows"], 3)
        self.assertEqual(result["metrics"]["deterministic_rows"], 1)
        self.assertEqual(result["metrics"]["reclassified_rows"], 2)
        self.assertEqual(
            {edge["edge_type"] for edge in result["edges"]},
            {"form_entry_edge", "lexeme_entry_edge"},
        )
        self.assertTrue(all(edge["status"] == "deterministic_exact" for edge in result["edges"]))
        self.assertTrue(all(record["status"] == "reclassified" for record in result["reclassifications"]))
        self.assertTrue(all(record["reason_code"] for record in result["reclassifications"]))

    def test_source_key_aliases_reciprocate_for_all_six_rows(self):
        from tools.build_repair1_graph_families import resolve_source_key_alias

        fixture = read_jsonl(FIXTURES / "source-key-resolver.fixture.jsonl")
        entries = [{"id": f"entry-{row['entry_id']}", "source_keys": [row["source_key"]]} for row in fixture]
        by_id = {entry["id"]: entry for entry in entries}
        by_source = {(row["source_key"][0], int(row["source_key"][1:])): f"entry-{row['entry_id']}" for row in fixture}
        for row in fixture:
            self.assertEqual(resolve_source_key_alias(row["entry_id"], by_id, by_source), f"entry-{row['entry_id']}")

    def test_duplicate_resolution_is_candidate_not_exact_and_divine_name_stays_silent(self):
        from tools.build_repair1_graph_families import build_duplicate_crosswalk_packets

        rows = read_jsonl(FIXTURES / "duplicate-crosswalk.fixture.jsonl")
        entries = [
            {"id": "entry-context", "headword": "عَيْنٌ", "section": "noun", "senses": [{"ar": "عَيْنٌ"}], "usage": [{"sense": 1, "forms": ["عَيْنٌ"], "examples": [{"ref": "3:1"}]}]},
            {"id": "entry-collision", "headword": "عَيْنٌ", "section": "noun", "senses": [{"ar": "عَيْنٌ"}], "usage": [{"sense": 1, "forms": ["عَيْنٌ"], "examples": [{"ref": "3:2"}]}]},
            {"id": "entry-divine", "headword": "اللَّهُ", "section": "noun", "tags": ["noun", "the_unseen"], "senses": [{"ar": "اللَّهُ"}], "usage": [{"sense": 1, "forms": ["اللَّهُ"], "examples": [{"ref": "6:3"}]}]},
        ]
        whitelist = [
            {"loc": "3:1:1", "surface": "عَيْنٌ"},
            {"loc": "3:2:1", "surface": "عَيْنٌ"},
            {"loc": "3:2:2", "surface": "عَيْنٌ"},
            {"loc": "6:3:2", "surface": "اللَّهُ"},
        ]
        packets = build_duplicate_crosswalk_packets(rows, entries, whitelist, [])
        packets_by_entry = {packet["entry_id"]: packet for packet in packets}

        self.assertEqual(len(packets), 3)
        self.assertEqual(packets_by_entry["entry-context"]["resolution"], "resolved")
        self.assertEqual(packets_by_entry["entry-context"]["status"], "candidate")
        self.assertTrue(packets_by_entry["entry-context"]["proposed_edge_set"])
        self.assertNotEqual(packets_by_entry["entry-context"]["status"], "deterministic_exact")
        self.assertEqual(packets_by_entry["entry-collision"]["resolution"], "still_ambiguous")
        self.assertEqual(packets_by_entry["entry-collision"]["route"], "owner_or_scholar_required")
        self.assertTrue(packets_by_entry["entry-collision"]["required_evidence"])
        self.assertEqual(packets_by_entry["entry-divine"]["policy_family"], "divine-name policy")
        self.assertEqual(packets_by_entry["entry-divine"]["root_projection"], "root-silent")
        self.assertFalse(packets_by_entry["entry-divine"]["proposed_edge_set"])

    def test_deterministic_overlay_preserves_ten_graph_checks(self):
        from tools.build_repair1_graph_families import merge_repair_edges

        entries = read_jsonl(EDGE_FIXTURES / "entries.fixture.jsonl")
        ledger = read_jsonl(EDGE_FIXTURES / "ledger.fixture.jsonl")
        whitelist = read_jsonl(EDGE_FIXTURES / "whitelist.fixture.jsonl")
        appearances = read_jsonl(EDGE_FIXTURES / "appearances.fixture.jsonl")
        facts = [row for row in read_jsonl(EDGE_FIXTURES / "facts.fixture.jsonl") if row["fact_id"] != "fact-orphan"]
        bundle = build_graph(entries=entries, ledger_rows=ledger, whitelist_rows=whitelist, appearance_rows=appearances, fact_rows=facts)
        repaired = merge_repair_edges(bundle["edges"], [])
        report = validate_graph({**bundle, "edges": repaired}, entries, ledger, whitelist, appearances, facts)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(len(report["checks"]), 10)


if __name__ == "__main__":
    unittest.main()
