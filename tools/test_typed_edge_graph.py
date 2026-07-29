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


class CitationFormDisplayTests(unittest.TestCase):
    """Red-first fixtures for the citation_form_display_edge extension (§1/§2)."""

    CORPUS = [
        {"loc": "2:187:10", "surface": "ٱلْخَيْطُ"},
        {"loc": "2:187:14", "surface": "قُلْتُمْ"},
        {"loc": "7:40:17", "surface": "ٱلْجَمَلُ"},
        {"loc": "7:40:21", "surface": "ٱلْجَمَلُ"},
    ]
    ENTRIES = [
        {
            "id": "entry-qala",
            "headword": "قَالَ",
            "usage": [{"forms": ["قَالَ"], "examples": [{"ref": "2:187"}], "sense": 1}],
        },
        {
            "id": "entry-khayt",
            "headword": "خَيْط",
            "usage": [{"forms": ["الْخَيْطُ"], "examples": [{"ref": "2:187"}], "sense": 1}],
        },
    ]

    @staticmethod
    def ledger_row(entry_id, surface, card_ref, **extra):
        row = {
            "entry_id": entry_id,
            "selected_surface": surface,
            "source_card_refs": [card_ref],
            "source_card_ref": card_ref,
            "sense_index": 1,
            "usage_index": 1,
            "form_index": 1,
            "missing_edges": ["display_local_to_canonical_crosswalk_missing"],
            "display_local_address": {"entry_example_index": 1},
        }
        row.update(extra)
        return row

    def build(self, rows):
        from tools.build_typed_edge_crosswalk import build_citation_display

        return build_citation_display(self.ENTRIES, rows, self.CORPUS)

    def test_citation_form_gets_display_edge_never_a_canonical_loc(self):
        # قَالَ rendered under a card whose āyah contains قُلْتُمْ: NOT a token of
        # the cited āyah, but a corpus... rather a citation form. It must be
        # re-typed as citation_form_display_edge, never given a canonical loc.
        rows = [self.ledger_row("entry-qala", "قَالَ", "2:187")]
        result = self.build(rows)
        self.assertEqual(len(result["queue"]), 0)
        self.assertEqual(len(result["edges"]), 1)
        item = result["edges"][0]
        self.assertEqual(item["edge_type"], "citation_form_display_edge")
        self.assertEqual(item["to_node_id"], "entry:entry-qala")
        self.assertEqual(item["display_basis"], "never_a_corpus_token")
        self.assertEqual(item["status"], "deterministic_exact")
        self.assertIn("no_canonical_loc_guard", item["guards"])
        self.assertNotIn("attach_locs", item.get("details", {}))

    def test_witness_elsewhere_recorded_as_evidence_only(self):
        # الْخَيْطُ cited under 7:40 (whose tokens are ٱلْجَمَلُ...): the surface IS
        # a Qurʾān token at 2:187:10 — witness evidence only, no attachment.
        rows = [self.ledger_row("entry-khayt", "الْخَيْطُ", "7:40")]
        result = self.build(rows)
        self.assertEqual(len(result["edges"]), 1)
        item = result["edges"][0]
        self.assertEqual(item["display_basis"], "corpus_witness_elsewhere")
        witness = [ev for ev in item["evidence"] if ev["address"].startswith("quran:")]
        self.assertTrue(witness)
        self.assertTrue(all(ev["method"] == "surface_match_strict_witness_only" for ev in witness))

    def test_attachable_row_routes_to_queue_a_not_edge(self):
        rows = [self.ledger_row("entry-khayt", "الْخَيْطُ", "2:187")]
        result = self.build(rows)
        self.assertEqual(len(result["edges"]), 0)
        self.assertEqual(len(result["queue"]), 1)
        item = result["queue"][0]
        self.assertEqual(item["attach_locs"], ["2:187:10"])
        self.assertEqual(item["status"], "candidate")

    def test_multi_position_attach_is_two_vote_ambiguous(self):
        rows = [self.ledger_row("entry-khayt", "ٱلْجَمَلُ", "7:40")]
        result = self.build(rows)
        self.assertEqual(len(result["queue"]), 1)
        item = result["queue"][0]
        self.assertEqual(item["status"], "ambiguous")
        self.assertEqual(item["review_route"], "two_vote_disambiguation")
        self.assertEqual(item["attach_locs"], ["7:40:17", "7:40:21"])

    def test_no_canonical_loc_guard_blocks_loc_bearing_rows_and_streams(self):
        from tools.build_typed_edge_crosswalk import citation_guard_violations

        # A row still carrying a canonical loc claim may not be re-typed.
        rows = [self.ledger_row("entry-qala", "قَالَ", "2:187", occurrence_id="2:187:14")]
        result = self.build(rows)
        self.assertEqual(len(result["edges"]), 0)
        self.assertEqual(result["metrics"]["no_canonical_loc_guard_blocked"], 1)

        # Red: a doctored citation edge carrying an attach loc must be caught.
        clean = self.build([self.ledger_row("entry-qala", "قَالَ", "2:187")])["edges"]
        doctored = [dict(clean[0], details={**clean[0]["details"], "attach_locs": ["2:187:14"]})]
        self.assertTrue(citation_guard_violations(doctored))
        # Red: a co-emitted canonical_occurrence_edge for the same node must be caught.
        from tools.build_typed_edge_crosswalk import make_edge

        co = make_edge(
            "canonical_occurrence_edge",
            clean[0]["from_node_id"],
            "occurrence:2:187:14",
            "deterministic_exact",
        )
        self.assertTrue(citation_guard_violations(clean + [co]))
        self.assertEqual(citation_guard_violations(clean), [])


if __name__ == "__main__":
    unittest.main()
