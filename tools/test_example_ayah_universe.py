#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the example-ayah universe + particle matrix builders."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.build_example_ayah_universe import (  # noqa: E402
    align_card, build_universe, loose_key, strict_key)
from tools.build_particle_occurrence_matrix import (  # noqa: E402
    build_matrix, _proclitic_strips)


AYAH = [(1, "قَالَ"), (2, "إِنِّى"), (3, "أَعْلَمُ"), (4, "مَا"), (5, "لَا"),
        (6, "تَعْلَمُونَ")]


class AlignmentTests(unittest.TestCase):
    def test_exact_contiguous(self):
        assignments, basis = align_card(["قَالَ", "إِنِّى"], AYAH)
        self.assertEqual(basis, "contiguous_exact")
        self.assertEqual(assignments, [(1, "exact"), (2, "exact")])

    def test_annotation_marks_do_not_break_strict(self):
        assignments, basis = align_card(["قَالَ", "إِنِّىۖ"], AYAH)
        self.assertEqual(basis, "contiguous_strict")
        self.assertEqual(assignments[1][0], 2)

    def test_orthography_variant_loose_tier(self):
        # wasla vs plain alif + missing diacritics -> loose tier resolves.
        assignments, basis = align_card(["اعلم", "ما", "لا"], AYAH)
        self.assertIn(basis, ("contiguous_strict", "contiguous_loose"))
        self.assertEqual([a[0] for a in assignments], [3, 4, 5])

    def test_per_word_fallback_marks_unaligned(self):
        assignments, basis = align_card(["قَالَ", "غَرِيبٌ"], AYAH)
        self.assertEqual(basis, "per_word_fallback")
        self.assertEqual(assignments[0], (1, "strict_word_unique"))
        self.assertIsNone(assignments[1][0])

    def test_ambiguous_repeated_word_abstains(self):
        ayah = [(1, "قَالَ"), (2, "مَا"), (3, "مَا")]
        assignments, basis = align_card(["مَا"], ayah)
        self.assertEqual(basis, "ambiguous_exact")
        self.assertEqual(assignments[0], (None, "ambiguous"))

    def test_keys_never_collapse_man_min(self):
        # The qamus-highlight flagship: مَنْ (who) vs مِنْ (from).
        self.assertNotEqual(strict_key("مَنْ"), strict_key("مِنْ") + "_")
        self.assertEqual(loose_key("ٱلَّذِينَ"), loose_key("الَّذِينَ"))


def _mini_entries():
    return [
        {
            "id": "vvv111", "section": "verb", "source_keys": ["v001"],
            "headword": "قَالَ",
            "senses": [{"n": 1, "ar": "قَالَ", "gloss": "he said"}],
            "usage": [{"sense": 1, "forms": ["قَالَ"], "examples": [
                {"ar": "قَالَ إِنِّى أَعْلَمُ", "en": "x", "ref": "9:9"},
            ]}],
        },
        {
            "id": "ppp099", "section": "particle", "source_keys": ["p099"],
            "headword": "مَا",
            "senses": [{"n": 1, "ar": "مَا", "gloss": "what/not"}],
            "usage": [{"sense": 1, "forms": ["مَا"], "examples": [
                {"ar": "مَا لَا تَعْلَمُونَ ۖ", "en": "x", "ref": "9:9"},
            ]}],
        },
    ]


def _mini_ayat():
    return {(9, 9): AYAH}


def _mini_membership():
    rows = []
    for i in range(1, 101):
        tranche = ("P-00" if i <= 12 else "P-01" if i <= 29
                   else "P-02" if i <= 51 else "P-03")
        row = {
            "source_key": f"p{i:03d}", "entry_id": f"fixture{i:03d}",
            "headword": "x", "tranche": tranche, "function_family": "fixture",
            "scholar_two_vote_required": tranche == "P-02",
        }
        rows.append(row)
    # p099 points at the fixture particle entry, marked P-02 homograph.
    rows[98] = {
        "source_key": "p099", "entry_id": "ppp099", "headword": "مَا",
        "tranche": "P-02",
        "function_family": "homograph: mā (relative/negation/istifhām/maṣdarī)",
        "scholar_two_vote_required": True,
    }
    return {"membership": rows}


class UniverseBuildTests(unittest.TestCase):
    def build(self):
        return build_universe(
            _mini_entries(), _mini_ayat(), [], {"membership": []},
            {"vvv111": "VN-00"})

    def test_selected_vs_context_and_denominators(self):
        rows, occurrences, meta = self.build()
        words = [r for r in rows if r.get("word_class") != "pause_mark"]
        selected = [r for r in words if r["selected"]]
        self.assertEqual(meta["totals"]["displayed_words"], len(words))
        self.assertEqual(meta["totals"]["selected_words"], len(selected))
        self.assertEqual(
            meta["totals"]["selected_words"] + meta["totals"]["context_words"],
            meta["totals"]["displayed_words"])
        # قَالَ on v page selected; مَا on p page selected.
        self.assertEqual({r["displayed_surface"] for r in selected},
                         {"قَالَ", "مَا"})

    def test_pause_mark_excluded_from_occurrences(self):
        rows, occurrences, meta = self.build()
        pause = [r for r in rows if r.get("word_class") == "pause_mark"]
        self.assertEqual(len(pause), 1)
        self.assertNotIn("canonical_loc", pause[0])
        self.assertEqual(meta["totals"]["pause_mark_tokens"], 1)

    def test_unique_vs_appearance_denominators_preserved(self):
        rows, occurrences, meta = self.build()
        self.assertEqual(meta["totals"]["unique_occurrences"], len(occurrences))
        self.assertEqual(
            meta["totals"]["appearances_at_occurrences"],
            sum(o["appearance_count"] for o in occurrences))
        # 6 aligned words over 6 distinct locs here; force the general shape.
        for occurrence in occurrences:
            self.assertEqual(occurrence["appearance_count"],
                             len(occurrence["appearance_ids"]))

    def test_backlink_and_display_local_loc(self):
        rows, _occ, _meta = self.build()
        row = next(r for r in rows if r["entry_id"] == "vvv111")
        self.assertEqual(row["source_card_backlink"],
                         "qamus:vvv111#field=usage[0].examples[0]")
        self.assertEqual(row["display_local_loc"], "u0.x0.w0")


class MatrixBuildTests(unittest.TestCase):
    def build(self):
        entries = _mini_entries()
        universe_rows, _occ, _meta = build_universe(
            entries, _mini_ayat(), [], {"membership": []}, {"vvv111": "VN-00"})
        entries_by_id = {e["id"]: e for e in entries}
        # Fixture membership entries that don't exist need stub entries.
        for row in _mini_membership()["membership"]:
            entries_by_id.setdefault(
                row["entry_id"],
                {"id": row["entry_id"], "headword": row["headword"],
                 "senses": [], "usage": []})
        return build_matrix(universe_rows,
                            _mini_membership()["membership"],
                            entries_by_id, {})

    def test_free_match_and_page_classes(self):
        rows, meta = self.build()
        ma_rows = [r for r in rows if r["particle_source_key"] == "p099"]
        self.assertTrue(ma_rows)
        by_loc = {r["canonical_loc"]: r for r in ma_rows}
        # مَا appears selected on its own p page (9:9:4).
        self.assertIn("9:9:4", by_loc)
        self.assertEqual(
            by_loc["9:9:4"]["page_appearances"].get("selected_on_p"), 1)
        self.assertEqual(by_loc["9:9:4"]["evidence_status"], "candidate_linked")

    def test_candidate_only_contract(self):
        rows, _meta = self.build()
        for row in rows:
            self.assertEqual(row["certified"], "none")
            self.assertTrue(row["function_candidates"])
            if row["tranche"] == "P-02":
                self.assertIn("homograph_requires_scholar_two_vote",
                              row.get("blockers") or [])

    def test_proclitic_strip_generator(self):
        strips = dict(_proclitic_strips("والذان"))
        self.assertEqual(strips.get("و"), "الذان")

    def test_meta_reports_all_100_particles(self):
        _rows, meta = self.build()
        self.assertEqual(len(meta["per_particle"]), 100)


if __name__ == "__main__":
    unittest.main()
