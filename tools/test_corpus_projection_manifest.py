#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first tests for the corpus occurrence/appearance/projection manifest builder."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import build_corpus_projection_manifest as m  # noqa: E402


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def _entry(entry_id, section, senses=1, source_keys=None):
    return {
        "id": entry_id,
        "section": section,
        "headword": "x",
        "root": "",
        "source_keys": source_keys or [],
        "senses": [{"n": i + 1, "ar": "x", "gloss": "x"} for i in range(senses)],
    }


def _universe_row(appearance_id, entry_id, entry_type, canonical_loc, displayed_surface,
                   selected=False, card_ref="1:1", source_key="v001", word_class=None,
                   match_basis="exact", crosswalk="resolved", card_index=0, usage_index=0,
                   sense_index=1, blockers=None):
    row = {
        "appearance_id": appearance_id,
        "entry_id": entry_id,
        "entry_type": entry_type,
        "source_key": source_key,
        "card_ref": card_ref,
        "card_index": card_index,
        "card_token_count": 1,
        "usage_index": usage_index,
        "sense_index": sense_index,
        "tranche": "T-00",
        "tranche_kind": "VN",
        "display_local_loc": "u0.x0.w0",
        "displayed_fragment_hash": "abc123",
        "displayed_surface": displayed_surface,
        "selected": selected,
        "match_basis": match_basis,
        "source_card_backlink": f"qamus:{entry_id}#field=usage[0].examples[0]",
    }
    if word_class:
        row["word_class"] = word_class
    else:
        row["canonical_loc"] = canonical_loc
        row["crosswalk"] = crosswalk
        row["wbw_present"] = True
        if blockers:
            row["blockers"] = blockers
    return row


class _FixtureCase(unittest.TestCase):
    """Base class that builds a small, self-contained fixture set on disk."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.entries_path = os.path.join(self.tmp.name, "entries.jsonl")
        self.universe_path = os.path.join(self.tmp.name, "universe.jsonl")
        self.occ_path = os.path.join(self.tmp.name, "universe.occurrences.jsonl")
        self.appearance_index_path = os.path.join(self.tmp.name, "occurrence-appearances.jsonl")
        self.particle_matrix_path = os.path.join(self.tmp.name, "particle-occurrence-matrix.jsonl")

    def _write_all(self, entries, universe_rows, occ_rows=None, appearance_rows=None,
                    particle_rows=None):
        _write_jsonl(self.entries_path, entries)
        _write_jsonl(self.universe_path, universe_rows)
        _write_jsonl(self.occ_path, occ_rows or [])
        _write_jsonl(self.appearance_index_path, appearance_rows or [])
        _write_jsonl(self.particle_matrix_path, particle_rows or [])

    def _build(self):
        return m.build_manifest(
            self.entries_path, self.universe_path, self.occ_path,
            self.appearance_index_path, self.particle_matrix_path,
        )


class MissingEntryTests(_FixtureCase):
    def test_unresolved_entry_id_is_reported_not_silently_dropped(self):
        self._write_all(
            entries=[],
            universe_rows=[_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")],
        )
        rows, stats, _ctx = self._build()
        self.assertEqual(len(rows), 1)
        binding = rows[0]["dispositions"]["exact_binding"]
        self.assertEqual(binding["status"], "unresolved")
        self.assertIn("not found", binding["reason"])

    def test_class_trust_violation_when_section_disagrees_with_entry_type(self):
        self._write_all(
            entries=[_entry("e1", "noun")],
            universe_rows=[_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")],
        )
        rows, _stats, _ctx = self._build()
        binding = rows[0]["dispositions"]["exact_binding"]
        self.assertEqual(binding["status"], "class_trust_violation")

    def test_duplicate_entry_id_in_entries_jsonl_raises(self):
        _write_jsonl(self.entries_path, [_entry("e1", "verb"), _entry("e1", "noun")])
        with self.assertRaises(ValueError):
            m.load_entries(self.entries_path)


class OmittedTokenTests(_FixtureCase):
    def test_every_universe_row_produces_exactly_one_manifest_row(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [
            _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ"),
            _universe_row("e1:u0:x0:w1", "e1", "v", None, "ۚ", word_class="pause_mark"),
            _universe_row("e1:u0:x0:w2", "e1", "v", "1:1:3", "إِنِّى"),
        ]
        self._write_all(entries, universe_rows)
        rows, stats, _ctx = self._build()
        self.assertEqual(len(rows), 3)
        self.assertEqual(stats["total_rows"], 3)

    def test_missing_appearance_id_raises(self):
        entries = [_entry("e1", "verb")]
        bad_row = _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")
        del bad_row["appearance_id"]
        self._write_all(entries, [bad_row])
        with self.assertRaises(ValueError):
            self._build()


class DuplicateAppearanceTests(_FixtureCase):
    def test_duplicate_appearance_id_raises(self):
        entries = [_entry("e1", "verb")]
        row = _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")
        self._write_all(entries, [row, dict(row)])
        with self.assertRaises(ValueError):
            self._build()


class SelectedContextConfusionTests(_FixtureCase):
    def test_same_surface_two_entries_never_merge_identity(self):
        entries = [_entry("e1", "verb"), _entry("e2", "verb")]
        universe_rows = [
            _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=True),
            _universe_row("e2:u0:x0:w0", "e2", "v", "1:1:1", "قَالَ", selected=False),
        ]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        self.assertEqual(len(rows), 2)
        by_id = {r["appearance_id"]: r for r in rows}
        self.assertTrue(by_id["e1:u0:x0:w0"]["selected"])
        self.assertFalse(by_id["e2:u0:x0:w0"]["selected"])
        self.assertNotEqual(by_id["e1:u0:x0:w0"]["entry_id"], by_id["e2:u0:x0:w0"]["entry_id"])

    def test_two_distinct_entries_selecting_same_loc_is_a_page_local_fork(self):
        entries = [_entry("e1", "verb"), _entry("e2", "verb")]
        universe_rows = [
            _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=True),
            _universe_row("e2:u0:x0:w0", "e2", "v", "1:1:1", "قَالَ", selected=True),
        ]
        self._write_all(entries, universe_rows)
        rows, stats, _ctx = self._build()
        for row in rows:
            self.assertTrue(row["page_local_fork"]["is_fork"])
            self.assertEqual(row["page_local_fork"]["conflicting_entry_ids"], ["e1", "e2"])
            self.assertEqual(row["dispositions"]["next_action"], "adjudicate_page_local_fork")
        self.assertEqual(stats["page_local_fork:selected_multi_entry_locs"], 1)


class NormalizedFalseIdentityTests(unittest.TestCase):
    def test_short_token_equal_to_suffix_is_not_falsely_stripped(self):
        result = m.analyze_letter_ownership("ات")
        self.assertIsNone(result["plural"]["suffix"])

    def test_article_letters_inside_stem_are_not_a_false_prefix(self):
        # 'رجال' contains "ال" but not as a leading definite-article prefix.
        result = m.analyze_letter_ownership("رجال")
        self.assertFalse(result["article"]["present"])


class ArticleSwallowedByStemTests(unittest.TestCase):
    def test_article_is_separately_measurable_from_stem(self):
        result = m.analyze_letter_ownership("السماوات")
        self.assertTrue(result["article"]["present"])
        self.assertIsNone(result["article"]["leading_conjunction"])
        self.assertEqual(result["article"]["stem_after_article"], "سماوات")

    def test_leading_conjunction_is_kept_distinct_from_the_article(self):
        result = m.analyze_letter_ownership("والأنثى")
        self.assertTrue(result["article"]["present"])
        self.assertEqual(result["article"]["leading_conjunction"], "و")
        self.assertEqual(result["article"]["stem_after_article"], "أنثى")

    def test_no_article_prefix_is_reported_explicitly_not_omitted(self):
        result = m.analyze_letter_ownership("خلق")
        self.assertIn("article", result)
        self.assertFalse(result["article"]["present"])
        self.assertIsNone(result["article"]["stem_after_article"])


class PluralSwallowedByRootTests(unittest.TestCase):
    def test_plural_suffix_is_separately_measurable_from_stem(self):
        result = m.analyze_letter_ownership("السماوات")
        self.assertEqual(result["plural"]["suffix"], "ات")
        self.assertEqual(result["plural"]["stem_before_suffix"], "السماو")

    def test_singular_definite_noun_reports_no_plural_suffix(self):
        result = m.analyze_letter_ownership("الذكر")
        self.assertIsNone(result["plural"]["suffix"])


class HoverWithoutFactsTests(_FixtureCase):
    def test_hover_without_any_fact_source_reports_not_available_with_reason(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        hover = rows[0]["dispositions"]["hover"]
        self.assertEqual(hover["status"], "not_available")
        self.assertIsNone(hover["fact_id"])
        self.assertTrue(hover["reason"])


class ColourHoverMismatchTests(unittest.TestCase):
    def test_colour_and_hover_always_cite_the_same_fact_identity(self):
        row = _universe_row("e1:u0:x0:w0", "e1", "p", "1:4:1", "مَا", source_key="p099")
        attachments = [("self", {
            "matrix_id": "p099:1:4:1", "certified": "none",
            "function_candidates": ["homograph"],
        })]
        colour, hover = m.compute_colour_and_hover(row, attachments, None)
        self.assertEqual(colour["fact_id"], hover["fact_id"])
        self.assertEqual(colour["status"], hover["status"])
        self.assertEqual(colour["fact_id"], "p099:1:4:1")

    def test_manifest_wide_colour_hover_identity_invariant_holds(self):
        rows = [
            {"dispositions": {"colour": {"fact_id": "a", "status": "candidate_available_uncertified"},
                               "hover": {"fact_id": "a", "status": "candidate_available_uncertified"}}},
            {"dispositions": {"colour": {"fact_id": None, "status": "not_available"},
                               "hover": {"fact_id": None, "status": "not_available"}}},
        ]
        report = m.verify_colour_hover_identity(rows)
        self.assertEqual(report["violations"], 0)
        self.assertEqual(report["checked_rows"], 2)


class PageLocalForkTests(_FixtureCase):
    def test_no_fork_when_only_one_entry_selects_the_occurrence(self):
        entries = [_entry("e1", "verb"), _entry("e2", "verb")]
        universe_rows = [
            _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=True),
            _universe_row("e2:u0:x0:w0", "e2", "v", "1:1:2", "إِنِّى", selected=True),
        ]
        self._write_all(entries, universe_rows)
        rows, stats, _ctx = self._build()
        self.assertFalse(any(r["page_local_fork"]["is_fork"] for r in rows))
        self.assertEqual(stats.get("page_local_fork:selected_multi_entry_locs", 0), 0)


class FullCorpusCanaryTests(unittest.TestCase):
    """Full-repository regression: the real 2,092-entry corpus P099/P009 canaries."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(m.DEFAULT_ENTRIES):
            raise unittest.SkipTest("full repo authority not available")
        cls.rows, cls.stats, cls.context = m.build_manifest(
            m.DEFAULT_ENTRIES, m.DEFAULT_UNIVERSE, m.DEFAULT_UNIVERSE_OCC,
            m.DEFAULT_APPEARANCE_INDEX, m.DEFAULT_PARTICLE_MATRIX,
        )

    def test_universe_row_totals_match_repository_authority(self):
        self.assertEqual(len(self.rows), 117117)
        self.assertEqual(self.stats["word_class:word"], 109471)
        self.assertEqual(self.stats["word_class:pause_mark"], 7646)

    def test_entry_totals_match_repository_authority(self):
        self.assertEqual(self.stats["entries:total"], 2092)
        self.assertEqual(self.stats["entries:section:particle"], 100)
        self.assertEqual(self.stats["entries:section:noun"], 1045)
        self.assertEqual(self.stats["entries:section:verb"], 947)

    def test_aligned_unaligned_bucketing_matches_universe_meta(self):
        baseline = m.build_baseline(self.rows, self.stats, self.context, {}, "deadbeef")
        self.assertEqual(baseline["manifest_totals"]["aligned_word_rows"], 109018)
        self.assertEqual(baseline["manifest_totals"]["unaligned_word_rows"], 453)
        self.assertTrue(baseline["verification"]["occurrence_count_equality"])

    def test_p099_canary_shape(self):
        canary = m.compute_canary_report(self.context)
        self.assertEqual(canary["p099"]["sense_count"], 6)
        self.assertEqual(canary["p099"]["displayed_token_count"], 53)

    def test_p009_waw_fanout_keeps_candidate_separate_from_context(self):
        canary = m.compute_canary_report(self.context)
        p009 = canary["p009"]
        self.assertGreater(p009["candidate_occurrence_count"], 0)
        self.assertGreater(p009["context_appearance_total"], p009["candidate_occurrence_count"])

    def test_al_dhakar_al_untha_article_ownership_is_measured(self):
        canary = m.compute_canary_report(self.context)
        self.assertEqual(canary["al_dhakar_al_untha_article_ownership"]["status"], "measured")
        self.assertGreaterEqual(len(canary["al_dhakar_al_untha_article_ownership"]["matched_rows"]), 2)

    def test_al_samawat_plural_ownership_is_measured(self):
        canary = m.compute_canary_report(self.context)
        self.assertEqual(canary["al_samawat_plural_ownership"]["status"], "measured")
        self.assertGreaterEqual(len(canary["al_samawat_plural_ownership"]["matched_rows"]), 1)

    def test_ma_function_disambiguation_deficit_is_reported_not_fabricated(self):
        canary = m.compute_canary_report(self.context)
        deficit = canary["ma_function_disambiguation_deficit"]
        self.assertIn(deficit["status"], ("blocked", "differentiated"))
        self.assertIsInstance(deficit["distinct_function_candidate_variants"], int)

    def test_colour_hover_identity_invariant_holds_across_full_corpus(self):
        report = m.verify_colour_hover_identity(self.rows)
        self.assertEqual(report["violations"], 0)
        self.assertEqual(report["checked_rows"], 117117)

    def test_page_local_fork_population_is_real_and_bounded(self):
        self.assertGreater(self.stats["page_local_fork:selected_multi_entry_locs"], 0)
        self.assertLess(self.stats["page_local_fork:selected_multi_entry_locs"], 1000)

    def test_deterministic_rebuild_is_byte_identical(self):
        rows_again, _stats_again, _ctx_again = m.build_manifest(
            m.DEFAULT_ENTRIES, m.DEFAULT_UNIVERSE, m.DEFAULT_UNIVERSE_OCC,
            m.DEFAULT_APPEARANCE_INDEX, m.DEFAULT_PARTICLE_MATRIX,
        )
        self.assertEqual(m.sha256_rows(self.rows), m.sha256_rows(rows_again))


class SampleSelectionTests(unittest.TestCase):
    def test_sample_selection_is_deterministic_and_bounded(self):
        rows = []
        for i in range(2000):
            rows.append({
                "appearance_id": f"e{i}:u0:x0:w0",
                "source_key": "p099" if i == 5 else "v001",
                "word_class": "pause_mark" if i % 500 == 0 else "word",
                "page_local_fork": {"is_fork": i == 10},
                "dispositions": {"surface": {"status": "unaligned" if i == 20 else "certified_tier"}},
            })
        context = {"fork_locs": {}}
        sample1 = m.select_sample(rows, context, 100)
        sample2 = m.select_sample(rows, context, 100)
        self.assertEqual([r["appearance_id"] for r in sample1], [r["appearance_id"] for r in sample2])
        self.assertLessEqual(len(sample1), 2000)
        sample_ids = {r["appearance_id"] for r in sample1}
        self.assertIn("e5:u0:x0:w0", sample_ids)


if __name__ == "__main__":
    unittest.main()
