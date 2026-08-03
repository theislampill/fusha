#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first / guard tests for the corpus occurrence/appearance/projection
manifest builder, per the Train D component-1 bounded repair packet
(fusha.train_d.component_repair_packet.v1). Test names follow the packet's
``red_first_tests`` ids/names (T1-T20) where a single test can carry the
full assertion; supplementary corpus-count checks use descriptive names.
"""

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
                   match_basis=None, crosswalk="resolved", card_index=0, usage_index=0,
                   sense_index=1, blockers=None):
    if match_basis is None:
        match_basis = "not_a_word" if word_class == "pause_mark" else "exact"
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


# ---------------------------------------------------------------------------
# R1 / B1 -- orthographic_shape_recall (T1-T4)
# ---------------------------------------------------------------------------

class OrthographicShapeRecallPacketTests(unittest.TestCase):
    def test_letter_ownership_never_claims_measured(self):
        words = ["الذين", "كالذين", "مسكين", "مدين", "فرعون", "يكون", "حين",
                  "الله", "ال", "abc", "", "ۚ"]
        for w in words:
            with self.subTest(w=w):
                self.assertNotEqual(m.analyze_letter_ownership(w)["status"], "measured")

    def test_kaf_ba_lam_proclitic_does_not_hide_the_article(self):
        self.assertNotEqual(m.analyze_letter_ownership("كالذين")["article"]["present"], False)
        self.assertNotEqual(m.analyze_letter_ownership("بالله")["article"]["present"], False)

    def test_article_and_suffix_never_claim_the_same_letters(self):
        for w in ["الذين", "الخاسرون", "الخائضين"]:
            r = m.analyze_letter_ownership(w)
            with self.subTest(w=w):
                self.assertFalse(
                    bool(r["article"]["present"]) and r["plural"]["suffix"] is not None
                    and (r["plural"]["stem_before_suffix"] or "").startswith("ال")
                )

    def test_singular_and_proper_noun_get_no_plural_suffix_claim(self):
        words = ["مسكين", "مدين", "فرعون", "هارون", "قارون", "حين", "دين", "ذات"]
        for w in words:
            r = m.analyze_letter_ownership(w)
            with self.subTest(w=w):
                self.assertTrue(
                    r["plural"]["suffix"] is None
                    or (r["status"] == "shape_recall_only" and r["not_a_morpheme_ownership_claim"] is True)
                )


class NormalizedFalseIdentityTests(unittest.TestCase):
    def test_short_token_equal_to_suffix_is_not_falsely_stripped(self):
        result = m.analyze_letter_ownership("ات")
        self.assertIsNone(result["plural"]["suffix"])

    def test_article_letters_inside_stem_are_not_a_false_prefix(self):
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
        self.assertEqual(result["plural"]["stem_before_suffix"], "سماو")

    def test_singular_definite_noun_reports_no_plural_suffix(self):
        result = m.analyze_letter_ownership("الذكر")
        self.assertIsNone(result["plural"]["suffix"])


# ---------------------------------------------------------------------------
# R2 / B2 -- card_owner_binding vs token_lexeme_binding (T5)
# ---------------------------------------------------------------------------

class CardOwnerBindingTests(_FixtureCase):
    def test_unresolved_entry_id_is_reported_not_silently_dropped(self):
        self._write_all(
            entries=[],
            universe_rows=[_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")],
        )
        rows, _stats, _ctx = self._build()
        self.assertEqual(len(rows), 1)
        binding = rows[0]["dispositions"]["card_owner_binding"]
        self.assertEqual(binding["status"], "owner_entry_unresolved")
        self.assertIn("not found", binding["reason"])

    def test_class_trust_violation_when_section_disagrees_with_entry_type(self):
        self._write_all(
            entries=[_entry("e1", "noun")],
            universe_rows=[_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")],
        )
        rows, _stats, _ctx = self._build()
        binding = rows[0]["dispositions"]["card_owner_binding"]
        self.assertEqual(binding["status"], "owner_class_trust_violation")

    def test_duplicate_entry_id_in_entries_jsonl_raises(self):
        _write_jsonl(self.entries_path, [_entry("e1", "verb"), _entry("e1", "noun")])
        with self.assertRaises(ValueError):
            m.load_entries(self.entries_path)


class TokenLexemeBindingTests(_FixtureCase):
    def test_context_token_lexeme_is_not_determined(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=False)]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        self.assertEqual(rows[0]["dispositions"]["token_lexeme_binding"]["status"],
                          "token_lexeme_not_determined")

    def test_selected_token_is_bound(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=True)]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        self.assertEqual(rows[0]["dispositions"]["token_lexeme_binding"]["status"],
                          "bound_selected_token")


# ---------------------------------------------------------------------------
# R3 / B2, M2 -- sarf never branches on the card-owner's section (T6)
# ---------------------------------------------------------------------------

class SarfCardOwnerTests(_FixtureCase):
    def test_sarf_does_not_branch_on_card_owner_section(self):
        entries = [_entry("e1", "noun")]
        universe_rows = [_universe_row(
            "e1:u0:x0:w0", "e1", "v", "1:1:1", "كَانُوا", selected=True)]
        self._write_all(entries, universe_rows)
        rows, stats, _ctx = self._build()
        sarf = rows[0]["dispositions"]["sarf"]
        self.assertNotEqual(sarf["status"], "not_applicable_non_verb_class")
        self.assertEqual(sarf["status"], "authority_not_joined_in_closed_inputs")
        self.assertEqual(stats.get("sarf:not_applicable_non_verb_class", 0), 0)

    def test_context_token_class_is_not_determined(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [_universe_row(
            "e1:u0:x0:w0", "e1", "v", "1:1:1", "كَانُوا", selected=False)]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        self.assertEqual(rows[0]["dispositions"]["sarf"]["status"], "token_class_not_determined")


# ---------------------------------------------------------------------------
# R4/R5/R6 / B3, B4 -- colour, hover, particle candidates, identity invariant
# (T7, T9)
# ---------------------------------------------------------------------------

class ColourHoverPacketTests(_FixtureCase):
    def test_particle_candidate_never_becomes_a_colour_or_hover_fact_id(self):
        entries = [_entry("e1", "particle")]
        universe_rows = [_universe_row(
            "e1:u0:x0:w0", "e1", "p", "1:4:1", "مَا", selected=True, source_key="p099")]
        particle_rows = [{
            "particle_source_key": "p099", "canonical_loc": "1:4:1",
            "matrix_id": "p099:1:4:1", "certified": "none",
            "function_candidates": ["homograph"], "appearance_ids": [],
        }]
        self._write_all(entries, universe_rows, particle_rows=particle_rows)
        rows, _stats, _ctx = self._build()
        row = rows[0]
        self.assertTrue(row["particle_function_candidate_refs"])
        colour = row["dispositions"]["colour"]
        hover = row["dispositions"]["hover"]
        self.assertEqual(colour["status"], "not_available")
        self.assertIsNone(colour["fact_id"])
        self.assertEqual(hover["status"], "not_available")
        self.assertIsNone(hover["fact_id"])

    def test_hover_without_any_fact_source_reports_not_available_with_reason(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        hover = rows[0]["dispositions"]["hover"]
        self.assertEqual(hover["status"], "not_available")
        self.assertIsNone(hover["fact_id"])
        self.assertTrue(hover["reason"])


class ColourHoverIdentityInvariantTests(unittest.TestCase):
    def test_colour_hover_invariant_reports_what_it_actually_compared(self):
        rows = [
            {"dispositions": {"colour": {"fact_id": "a", "status": "x"},
                               "hover": {"fact_id": "a", "status": "x"}},
             "particle_function_candidate_refs": []},
            {"dispositions": {"colour": {"fact_id": None, "status": "not_available"},
                               "hover": {"fact_id": None, "status": "not_available"}},
             "particle_function_candidate_refs": []},
            {"dispositions": {"colour": {"fact_id": None, "status": "not_available"},
                               "hover": {"fact_id": None, "status": "not_available"}},
             "particle_function_candidate_refs": [{"matrix_id": "p1"}]},
        ]
        report = m.verify_colour_hover_identity(rows)
        self.assertEqual(report["both_present_compared"], 1)
        self.assertEqual(report["both_absent_not_compared"], 1)
        self.assertEqual(report["candidate_only_not_compared"], 1)
        self.assertEqual(report["violations"], 0)
        # equality of two null fact_ids must not be counted as "checked"
        self.assertNotIn("checked_rows", report)


# ---------------------------------------------------------------------------
# R7 / B5 -- surface alignment tiers, never "certified" (T10, T11)
# ---------------------------------------------------------------------------

class SurfaceAlignmentTierTests(unittest.TestCase):
    def test_no_plane_uses_the_word_certified_for_string_alignment(self):
        for tier_status in m.ALIGNMENT_MATCH_TIER_STATUS.values():
            self.assertNotIn("certified", tier_status)


# ---------------------------------------------------------------------------
# R8 / B6 -- payload never asserts live state (T12)
# ---------------------------------------------------------------------------

class PayloadLiveStateTests(_FixtureCase):
    def test_payload_status_never_says_live(self):
        entries = [_entry("e1", "verb")]
        universe_rows = [_universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ")]
        self._write_all(entries, universe_rows)
        rows, _stats, _ctx = self._build()
        payload = rows[0]["dispositions"]["payload"]
        self.assertNotIn("live", payload["status"])
        live_state = rows[0]["dispositions"]["live_state"]
        self.assertEqual(live_state["status"], "not_measured")


# ---------------------------------------------------------------------------
# R9 / B7 -- nahw vs particle_function_candidates_at_loc (T13)
# ---------------------------------------------------------------------------

class NahwParticleCandidateSeparationTests(_FixtureCase):
    def test_nahw_plane_is_not_populated_from_particle_function_candidates(self):
        entries = [_entry("e1", "particle")]
        universe_rows = [_universe_row(
            "e1:u0:x0:w0", "e1", "p", "1:4:1", "مَا", selected=True, source_key="p099")]
        particle_rows = [{
            "particle_source_key": "p099", "canonical_loc": "1:4:1",
            "matrix_id": "p099:1:4:1", "certified": "none",
            "function_candidates": ["homograph"], "appearance_ids": [],
        }]
        self._write_all(entries, universe_rows, particle_rows=particle_rows)
        rows, _stats, _ctx = self._build()
        row = rows[0]
        self.assertEqual(row["dispositions"]["nahw"]["status"],
                          "occurrence_bound_nahw_not_joined_in_closed_inputs")
        self.assertEqual(
            row["dispositions"]["particle_function_candidates_at_loc"]["status"],
            "candidate_only_partial_function_evidence",
        )


# ---------------------------------------------------------------------------
# R19 / M3 -- no code path can emit "certified" from particle-matrix data (T19)
# ---------------------------------------------------------------------------

class NoUnreachableCertifiedBranchTests(unittest.TestCase):
    def test_no_unreachable_certified_branch(self):
        row = {"word_class": "word"}
        matrix_row = {
            "matrix_id": "pXXX:1:1:1",
            "certified": "yes_should_never_matter",
            "function_candidates": ["definite article al-"],
        }
        attachments = [("self", matrix_row)]
        refs = m.compute_particle_candidate_refs(attachments)
        disp = m.compute_particle_function_candidates_at_loc(row, attachments, refs)
        self.assertNotEqual(disp["status"], "certified")
        self.assertEqual(disp["status"], "candidate_only_partial_function_evidence")


# ---------------------------------------------------------------------------
# R10 / B8 -- multi-entry transclusion fanout is not a fork (T14)
# ---------------------------------------------------------------------------

class MultiEntryTransclusionFanoutTests(_FixtureCase):
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

    def test_multi_entry_transclusion_is_not_called_a_fork(self):
        entries = [_entry("e1", "verb"), _entry("e2", "verb")]
        universe_rows = [
            _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=True),
            _universe_row("e2:u0:x0:w0", "e2", "v", "1:1:1", "قَالَ", selected=True),
        ]
        self._write_all(entries, universe_rows)
        rows, stats, _ctx = self._build()
        for row in rows:
            fanout = row["multi_entry_transclusion_fanout"]
            self.assertTrue(fanout["is_transclusion_fanout"])
            self.assertEqual(fanout["fork_status"], "no_divergent_projection_identity_in_closed_inputs")
            self.assertEqual(sorted(fanout["conflicting_entry_ids"]), ["e1", "e2"])
            # the fanout must not preempt/mask the other applicable pending actions
            self.assertIn("author_rich_colour_hover_batch", row["dispositions"]["pending_actions"])
        self.assertEqual(stats["multi_entry_transclusion_fanout:selected_multi_entry_locs"], 1)

    def test_no_fanout_when_only_one_entry_selects_the_occurrence(self):
        entries = [_entry("e1", "verb"), _entry("e2", "verb")]
        universe_rows = [
            _universe_row("e1:u0:x0:w0", "e1", "v", "1:1:1", "قَالَ", selected=True),
            _universe_row("e2:u0:x0:w0", "e2", "v", "1:1:2", "إِنِّى", selected=True),
        ]
        self._write_all(entries, universe_rows)
        rows, stats, _ctx = self._build()
        self.assertFalse(any(r["multi_entry_transclusion_fanout"]["is_transclusion_fanout"] for r in rows))
        self.assertEqual(stats.get("multi_entry_transclusion_fanout:selected_multi_entry_locs", 0), 0)


# ---------------------------------------------------------------------------
# Structural fixture-level omission / duplication guards (unrelated to any
# single R-item, kept as regression coverage)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Full-corpus regression: the real 2,092-entry / 117,117-row corpus.
# ---------------------------------------------------------------------------

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

    def test_al_dhakar_al_untha_article_shape_recall_is_explicitly_non_ownership(self):
        canary = m.compute_canary_report(self.context)
        self.assertEqual(
            canary["al_dhakar_al_untha_article_shape_recall"]["status"],
            "shape_recall_signal_present",
        )
        self.assertGreaterEqual(
            len(canary["al_dhakar_al_untha_article_shape_recall"]["matched_rows"]), 2
        )

    def test_al_samawat_plural_shape_recall_is_explicitly_non_ownership(self):
        canary = m.compute_canary_report(self.context)
        self.assertEqual(
            canary["al_samawat_plural_shape_recall"]["status"],
            "shape_recall_signal_present",
        )
        self.assertGreaterEqual(
            len(canary["al_samawat_plural_shape_recall"]["matched_rows"]), 1
        )

    def test_canary_shape_recall_never_republishes_measured_ownership(self):
        canary = m.compute_canary_report(self.context)
        self.assertFalse(
            any(
                key.endswith("_ownership") and value.get("status") == "measured"
                for key, value in canary.items()
                if isinstance(value, dict)
            )
        )

    def test_ma_function_disambiguation_deficit_is_reported_not_fabricated(self):
        canary = m.compute_canary_report(self.context)
        deficit = canary["ma_function_disambiguation_deficit"]
        self.assertIn(deficit["status"], ("blocked", "differentiated"))
        self.assertIsInstance(deficit["distinct_function_candidate_variants"], int)

    def test_colour_hover_identity_invariant_holds_across_full_corpus(self):
        report = m.verify_colour_hover_identity(self.rows)
        self.assertEqual(report["violations"], 0)
        self.assertEqual(
            report["both_present_compared"] + report["both_absent_not_compared"]
            + report["candidate_only_not_compared"],
            117117,
        )

    def test_multi_entry_transclusion_fanout_population_is_real_and_bounded(self):
        self.assertGreater(self.stats["multi_entry_transclusion_fanout:selected_multi_entry_locs"], 0)
        self.assertLess(self.stats["multi_entry_transclusion_fanout:selected_multi_entry_locs"], 1000)

    def test_deterministic_rebuild_is_byte_identical(self):
        rows_again, _stats_again, _ctx_again = m.build_manifest(
            m.DEFAULT_ENTRIES, m.DEFAULT_UNIVERSE, m.DEFAULT_UNIVERSE_OCC,
            m.DEFAULT_APPEARANCE_INDEX, m.DEFAULT_PARTICLE_MATRIX,
        )
        self.assertEqual(m.sha256_rows(self.rows), m.sha256_rows(rows_again))


class FullCorpusRepairPacketTests(unittest.TestCase):
    """Corpus-wide assertions for the repair packet's red_first_tests that
    require the real committed authorities (T5/T8/T10/T11/T12/T13/T15/T16/
    T17/T18/T20)."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(m.DEFAULT_ENTRIES):
            raise unittest.SkipTest("full repo authority not available")
        cls.rows, cls.stats, cls.context = m.build_manifest(
            m.DEFAULT_ENTRIES, m.DEFAULT_UNIVERSE, m.DEFAULT_UNIVERSE_OCC,
            m.DEFAULT_APPEARANCE_INDEX, m.DEFAULT_PARTICLE_MATRIX,
        )
        cls.by_appearance_id = {r["appearance_id"]: r for r in cls.rows}

    def test_context_token_lexeme_is_not_determined(self):
        self.assertEqual(self.stats.get("token_lexeme_binding:token_lexeme_not_determined", 0), 105062)
        self.assertEqual(self.stats.get("token_lexeme_binding:bound_selected_token", 0), 4409)

    def test_false_positive_particle_candidate_does_not_project(self):
        row = self.by_appearance_id.get("00107b99a50e:u0:x0:w3")
        self.assertIsNotNone(row, "canary appearance not found in the full manifest")
        self.assertEqual(row["canonical_loc"], "9:69:4")
        refs = row["particle_function_candidate_refs"]
        self.assertTrue(any(str(ref.get("matrix_id", "")).startswith("p006") for ref in refs))
        self.assertEqual(row["dispositions"]["colour"]["status"], "not_available")
        self.assertIsNone(row["dispositions"]["colour"]["fact_id"])

    def test_no_plane_uses_the_word_certified_for_string_alignment(self):
        self.assertEqual(self.stats.get("surface:alignment_tier_exact", 0), 95416)
        self.assertEqual(self.stats.get("surface:alignment_tier_strict", 0), 12795)
        self.assertEqual(self.stats.get("surface:alignment_tier_strict_word_unique", 0), 630)
        surface_statuses = {k.split(":", 1)[1] for k in self.stats if k.startswith("surface:")}
        for status in surface_statuses:
            self.assertNotIn("certified", status)

    def test_divergent_bare_surface_at_same_loc_is_reported(self):
        self.assertEqual(
            self.stats.get("surface_conflict:locs:divergent_bare_surface_at_same_loc", 0), 11)
        rows_at_loc = [r for r in self.rows if r["canonical_loc"] == "2:198:12"]
        self.assertTrue(rows_at_loc)
        self.assertTrue(any(
            r["dispositions"]["surface_conflict"]["status"] == "divergent_bare_surface_at_same_loc"
            for r in rows_at_loc
        ))

    def test_payload_never_asserts_live_state(self):
        payload_statuses = {k.split(":", 1)[1] for k in self.stats if k.startswith("payload:")}
        for status in payload_statuses:
            self.assertNotIn("live", status)
        self.assertEqual(self.stats.get("live_state:not_measured", 0), 117117)

    def test_nahw_plane_is_not_populated_from_particle_function_candidates(self):
        self.assertEqual(
            self.stats.get("nahw:occurrence_bound_nahw_not_joined_in_closed_inputs", 0), 109471)
        self.assertEqual(self.stats.get("nahw:not_applicable", 0), 7646)
        for row in self.rows:
            if row["word_class"] != "word":
                continue
            self.assertEqual(
                row["dispositions"]["nahw"]["status"],
                "occurrence_bound_nahw_not_joined_in_closed_inputs",
            )

    def test_every_word_row_carries_every_required_ontology_plane(self):
        required_planes = [
            "surface", "orthographic_shape_recall", "morpheme_ownership", "sarf", "nahw",
            "particle_function_candidates_at_loc", "token_lexeme_binding", "contextual_meaning",
            "translation", "colour", "hover", "appearance_identity", "reverse_trace",
            "certification", "revocation_dependency", "payload", "live_state",
        ]
        for row in self.rows:
            if row["word_class"] != "word":
                continue
            dispositions = row["dispositions"]
            for plane in required_planes:
                self.assertIn(plane, dispositions)
                self.assertTrue(dispositions[plane].get("status"))

    def test_pause_marks_stay_out_of_word_denominators(self):
        self.assertEqual(len(self.rows), 117117)
        self.assertEqual(self.stats["word_class:word"], 109471)
        self.assertEqual(self.stats["word_class:pause_mark"], 7646)
        planes = [
            "card_owner_binding", "token_lexeme_binding", "surface", "surface_conflict",
            "orthographic_shape_recall", "morpheme_ownership", "sarf", "nahw",
            "particle_function_candidates_at_loc", "contextual_meaning", "translation",
            "colour", "hover", "cross_plane_conflict", "appearance_identity", "certification",
            "revocation_dependency", "payload",
        ]
        for row in self.rows:
            if row["word_class"] != "pause_mark":
                continue
            for plane in planes:
                self.assertEqual(
                    row["dispositions"][plane]["status"], "not_applicable",
                    f"{plane} not not_applicable for pause row {row['appearance_id']}",
                )

    def test_full_colour_hover_backlog_is_reported_not_masked(self):
        count = sum(
            1 for r in self.rows
            if "author_rich_colour_hover_batch" in r["dispositions"]["pending_actions"]
        )
        self.assertEqual(count, 109471)
        self.assertEqual(self.stats.get("pending_actions:author_rich_colour_hover_batch", 0), 109471)

    def test_cross_plane_article_disagreement_is_reported(self):
        self.assertEqual(
            self.stats.get("cross_plane_conflict:article_shape_vs_candidate_disagreement", 0), 2453)
        rows_at_loc = [r for r in self.rows if r["canonical_loc"] == "28:8:2"]
        self.assertTrue(rows_at_loc)
        self.assertTrue(any(
            r["dispositions"]["cross_plane_conflict"]["status"] == "article_shape_vs_candidate_disagreement"
            for r in rows_at_loc
        ))

    def test_sarf_never_emits_removed_status_corpus_wide(self):
        self.assertEqual(self.stats.get("sarf:not_applicable_non_verb_class", 0), 0)

    def test_no_certified_status_particle_plane_corpus_wide(self):
        statuses = {
            k.split(":", 1)[1] for k in self.stats
            if k.startswith("particle_function_candidates_at_loc:")
        }
        self.assertNotIn("certified", statuses)

    def test_determinism_and_counts_preserved(self):
        self.assertEqual(self.stats["entries:total"], 2092)
        self.assertEqual(self.stats["entries:section:particle"], 100)
        self.assertEqual(self.stats["entries:section:noun"], 1045)
        self.assertEqual(self.stats["entries:section:verb"], 947)
        self.assertEqual(len(self.rows), 117117)
        rows_again, _stats_again, _ctx_again = m.build_manifest(
            m.DEFAULT_ENTRIES, m.DEFAULT_UNIVERSE, m.DEFAULT_UNIVERSE_OCC,
            m.DEFAULT_APPEARANCE_INDEX, m.DEFAULT_PARTICLE_MATRIX,
        )
        self.assertEqual(m.sha256_rows(self.rows), m.sha256_rows(rows_again))
        baseline = m.build_baseline(self.rows, self.stats, self.context, {}, m.sha256_rows(self.rows))
        self.assertTrue(baseline["verification"]["entries_set_equality"])
        self.assertTrue(baseline["verification"]["universe_row_count_equality"])
        self.assertTrue(baseline["verification"]["occurrence_count_equality"])
        sample_rows = m.select_sample(self.rows, self.context, m.SAMPLE_SIZE_DEFAULT)
        self.assertLessEqual(len(sample_rows), m.SAMPLE_SIZE_DEFAULT)
        self.assertGreater(len(sample_rows), 0)


# ---------------------------------------------------------------------------
# Deterministic, bounded sample selection (unrelated to a single R-item;
# guard coverage for the existing sample/baseline contract).
# ---------------------------------------------------------------------------

class SampleSelectionTests(unittest.TestCase):
    def test_sample_selection_is_deterministic_and_bounded(self):
        rows = []
        for i in range(2000):
            rows.append({
                "appearance_id": f"e{i}:u0:x0:w0",
                "source_key": "p099" if i == 5 else "v001",
                "word_class": "pause_mark" if i % 500 == 0 else "word",
                "multi_entry_transclusion_fanout": {"is_transclusion_fanout": i == 10},
                "dispositions": {"surface": {"status": "unaligned" if i == 20 else "alignment_tier_exact"}},
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
