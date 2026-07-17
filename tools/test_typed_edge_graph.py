#!/usr/bin/env python3
"""Red-first fixtures for the typed-edge and crosswalk contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from tools.build_typed_edge_crosswalk import build_graph
from tools.analyze_typed_edge_closure import (
    DEBT_FAMILIES,
    GRAPH_BLOCKERS,
    classify_debt_rows,
    reclassify_source_gaps,
)
from tools.validate_typed_edge_graph import CHECK_NAMES, validate_graph


FIXTURES = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "edges"


def read_fixture(name):
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_fixture(*, include_orphan=False):
    entries = read_fixture("entries.fixture.jsonl")
    ledger = read_fixture("ledger.fixture.jsonl")
    whitelist = read_fixture("whitelist.fixture.jsonl")
    appearances = read_fixture("appearances.fixture.jsonl")
    facts = read_fixture("facts.fixture.jsonl")
    if not include_orphan:
        facts = [fact for fact in facts if fact["fact_id"] != "fact-orphan"]
    return build_graph(
        entries=entries,
        ledger_rows=ledger,
        whitelist_rows=whitelist,
        appearance_rows=appearances,
        fact_rows=facts,
    ), (entries, ledger, whitelist, appearances, facts)


def edge(bundle, edge_type, *, from_node_id=None, to_node_id=None):
    for item in bundle["edges"]:
        if item["edge_type"] != edge_type:
            continue
        if from_node_id is not None and item["from_node_id"] != from_node_id:
            continue
        if to_node_id is not None and item["to_node_id"] != to_node_id:
            continue
        return item
    raise AssertionError(f"edge not found: {edge_type}, {from_node_id}, {to_node_id}")


class TypedEdgeGraphTests(unittest.TestCase):
    def test_fixture_passes_all_named_checks(self):
        bundle, inputs = build_fixture()
        report = validate_graph(bundle, *inputs)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(CHECK_NAMES, [check["name"] for check in report["checks"]])

    def test_page_context_promotion_is_red_first(self):
        bundle, inputs = build_fixture()
        page_edge = edge(bundle, "page_context_entry_edge", to_node_id="entry:entry-page")
        page_edge["edge_type"] = "lexeme_entry_edge"
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("page-context" in error for error in report["errors"]))

    def test_selected_word_card_backlink_is_red_first(self):
        bundle, inputs = build_fixture()
        bundle["edges"] = [
            item for item in bundle["edges"] if item["edge_type"] != "source_card_edge"
        ]
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("card backlink" in error for error in report["errors"]))

    def test_certified_reverse_index_is_red_first(self):
        bundle, inputs = build_fixture()
        for record in bundle["reverse"]:
            record["occurrence_ids"] = []
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("reverse entry" in error for error in report["errors"]))

    def test_form_evidence_is_red_first(self):
        bundle, inputs = build_fixture()
        form_edge = edge(bundle, "form_entry_edge", to_node_id="entry:entry-book")
        form_edge["evidence"] = []
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("form edge" in error for error in report["errors"]))

    def test_sense_identity_is_red_first(self):
        bundle, inputs = build_fixture()
        sense_edge = edge(bundle, "sense_entry_edge", to_node_id="entry:entry-book")
        sense_edge["details"].pop("sense_id", None)
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("sense edge" in error for error in report["errors"]))

    def test_duplicate_surface_abstention_is_red_first(self):
        bundle, inputs = build_fixture()
        duplicate = edge(bundle, "lexeme_entry_edge", to_node_id="entry:entry-eye-a")
        duplicate["status"] = "deterministic_exact"
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("duplicate" in error for error in report["errors"]))

    def test_display_local_exact_mapping_is_red_first(self):
        bundle, inputs = build_fixture()
        display_edge = edge(
            bundle,
            "display_local_to_canonical_crosswalk_edge",
            to_node_id="occurrence:1:1:1",
        )
        display_edge["details"]["exact_surface"] = False
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("display-local" in error for error in report["errors"]))

    def test_repeated_appearance_propagation_is_red_first(self):
        bundle, inputs = build_fixture()
        bundle["edges"] = [
            item
            for item in bundle["edges"]
            if not (
                item["edge_type"] == "rendered_appearance_edge"
                and item["from_node_id"] == "occurrence:1:1:1"
                and item["to_node_id"] == "appearance:1:1:1:2"
            )
        ]
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("appearance" in error for error in report["errors"]))

    def test_orphaned_fact_is_red_first(self):
        bundle, inputs = build_fixture(include_orphan=True)
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("orphan" in error for error in report["errors"]))

    def test_exact_reconstruction_is_red_first(self):
        bundle, inputs = build_fixture()
        reconstruction = edge(
            bundle,
            "display_local_to_canonical_crosswalk_edge",
            to_node_id="occurrence:1:1:1",
        )
        reconstruction["details"]["reconstruction_exact"] = False
        report = validate_graph(bundle, *inputs)
        self.assertFalse(report["ok"])
        self.assertTrue(any("reconstruction" in error for error in report["errors"]))

    def test_root_agreement_does_not_create_lexeme_edge(self):
        bundle, inputs = build_fixture()
        root_only = [
            item
            for item in bundle["edges"]
            if item["edge_type"] == "root_family_edge"
            and item["to_node_id"] == "entry:entry-root"
        ]
        self.assertTrue(root_only)
        self.assertFalse(
            any(
                item["edge_type"] == "lexeme_entry_edge"
                and item["to_node_id"] == "entry:entry-root"
                for item in bundle["edges"]
            )
        )

    def test_debt_classifier_uses_owner_vocabulary(self):
        bundle, inputs = build_fixture()
        entries, ledger, whitelist, appearances, _ = inputs
        rows = [dict(ledger[0], crosswalk_flag=False, missing_edges=["display_local_to_canonical_crosswalk_missing"])]
        summary, records = classify_debt_rows(rows, entries, bundle, whitelist, appearances)
        self.assertEqual(sum(summary.values()), 1)
        self.assertEqual(set(summary), set(DEBT_FAMILIES))
        self.assertEqual(records[0]["repair_family"], "deterministic entry/form match")

    def test_source_gap_reclassification_names_exact_graph_blocker(self):
        bundle, inputs = build_fixture()
        entries, ledger, whitelist, appearances, _ = inputs
        producer = {
            "canonical_occurrence": {
                "occurrence_id": "quran:1:1:1",
                "quran_loc": "1:1:1",
                "surface": "كِتَابٌ",
                "entry_id": "entry-book",
            },
            "facts": [{
                "fact_id": "fact-repair",
                "certification": {"status": "certified"},
                "fact_value": {
                    "entry_id": "entry-book",
                    "source_fields": ["entry:entry-book:usage[0].forms[0]"],
                },
                "source_address": {"address": "fixture:repair", "source_kind": "fixture"},
            }],
            "projection": {"status": "source_gap", "projection_id": "projection-repair"},
        }
        delta = reclassify_source_gaps(
            [producer], bundle, entries, ledger, whitelist, appearances
        )
        self.assertEqual(len(delta), 1)
        self.assertIn(delta[0]["blocker_class"], GRAPH_BLOCKERS)
        self.assertEqual(delta[0]["status"], "candidate")


if __name__ == "__main__":
    unittest.main()
