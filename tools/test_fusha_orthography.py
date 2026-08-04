#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first hostile tests for tools/fusha_orthography.py plus the two integration fixes it
motivated in tools/fusha_text_check.py (canonical ٱ article recognition) and
tools/fusha_pattern_engine.py (false نا subject-pronoun split on a tanwīn support alif).

Occurrence controls (exact surface behaviour only; no linguistic certification):
quran:2:8:1 وَمِنَ; quran:2:108:11 وَمَن; quran:2:34:5 لِـَٔادَمَ; quran:3:8:12 رَحْمَةً;
quran:6:77:3 ٱلْقَمَرَ; quran:6:78:3 ٱلشَّمْسَ; quran:13:31:3 قُرْءَانًا; quran:53:45:4 ٱلذَّكَرَ;
quran:53:45:5 وَٱلْأُنثَىٰ.
"""
from __future__ import annotations

import os
import sys
import unittest

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_orthography as O  # noqa: E402
from tools import fusha_text_check as TC  # noqa: E402
from tools import fusha_pattern_engine as PE  # noqa: E402
from tools import fusha_standalone_parse as SP  # noqa: E402
from tools.fusha_clitic_splitter import split_clitics  # noqa: E402


class GraphemeClusterTests(unittest.TestCase):
    def test_clusters_reconstruct_exactly(self):
        for surface in ("ٱلشَّمْسَ", "ٱلْقَمَرَ", "وَٱلْأُنثَىٰ", "قُرْءَانًا", "رَحْمَةً", "ٱلذَّكَرَ"):
            clusters = O.grapheme_clusters(surface)
            self.assertEqual("".join(c["surface"] for c in clusters), surface)
            for c in clusters:
                self.assertEqual(surface[c["start"]:c["end"]], c["surface"])

    def test_combining_marks_never_become_a_base_letter(self):
        clusters = O.grapheme_clusters("بَ")
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["base"], "ب")
        self.assertNotIn(clusters[0]["base"], O._COMBINING)

    def test_shadda_bearing_cluster_stays_one_cluster(self):
        clusters = O.grapheme_clusters("شَّ")
        self.assertEqual(len(clusters), 1)
        self.assertIn(O.SHADDA, clusters[0]["marks"])

    def test_combining_marks_never_hold_primary_ownership(self):
        # a mark-only span must never appear as its own cluster with a mark as `base`.
        for surface in ("ٱلشَّمْسَ", "قُرْءَانًا", "رَحْمَةً"):
            for c in O.grapheme_clusters(surface):
                self.assertNotIn(c["base"], O._COMBINING)


class WrittenBaseSurfaceTests(unittest.TestCase):
    def test_base_surface_never_folds_alif_wasla(self):
        self.assertTrue(O.base_surface("ٱلشَّمْسَ").startswith("ٱ"))
        self.assertNotEqual(O.base_surface("ٱلشَّمْسَ")[0], "ا")

    def test_written_surface_is_untouched(self):
        self.assertEqual(O.written_surface("ٱلْقَمَرَ"), "ٱلْقَمَرَ")

    def test_hamza_seat_variants_never_promoted_by_normalization(self):
        # base_surface must keep every hamza seat distinct from every other seat and from alif.
        seats = ["أ", "إ", "ؤ", "ئ", "ء"]
        for seat in seats:
            self.assertEqual(O.base_surface(seat), seat)
        self.assertNotEqual(O.base_surface("أ"), O.base_surface("ا"))


class ConnectivityTests(unittest.TestCase):
    def test_nonjoining_visual_boundary_never_becomes_a_word_or_morpheme_split(self):
        runs = O.visual_runs("دار")
        self.assertGreaterEqual(len(runs), 2, "د/ا are right-joining and must end a visual run")
        # the word itself must remain a single, unsplit surface regardless of visual runs.
        self.assertEqual(O.base_surface("دار"), "دار")
        all_indices = [i for run in runs for i in run["cluster_indices"]]
        self.assertEqual(sorted(all_indices), list(range(len(O.grapheme_clusters("دار")))))

    def test_combining_marks_are_connectivity_transparent(self):
        self.assertEqual(O.connectivity_class(O.SHADDA), "transparent")
        self.assertEqual(O.connectivity_class("َ"), "transparent")

    def test_dual_joining_letter_does_not_end_a_run(self):
        runs = O.visual_runs("كتب")
        self.assertEqual(len(runs), 1, "all-dual-joining كتب must stay one visual run")


class ConfusableFamilyTests(unittest.TestCase):
    def test_same_skeleton_different_dot_preserves_identity(self):
        family_ids = {ch: O.confusable_family(ch)["family"] for ch in "بتثني"}
        self.assertEqual(len(set(family_ids.values())), 1, "بتثني must share one dot-skeleton family")
        # identity must remain distinct: family metadata is never letter equality.
        self.assertEqual(len({O.base_surface(ch) for ch in "بتثني"}), 5)
        for ch in "بتثني":
            self.assertIsNone(O.confusable_family(ch).get("equality"))

    def test_hamza_seats_form_their_own_family_without_equality(self):
        fam = O.confusable_family("أ")
        self.assertEqual(fam["kind"], "hamza_seat")
        self.assertIn("ء", fam["members"])
        self.assertIsNone(fam["equality"])

    def test_unrelated_letters_have_no_family(self):
        self.assertIsNone(O.confusable_family("ل"))
        self.assertIsNone(O.confusable_family("م"))


class VocalizationStateTests(unittest.TestCase):
    def test_min_mina_man_remain_distinct_by_observed_vocalization(self):
        bare = O.vocalization_state("من")["clusters"]
        mina = O.vocalization_state("مِنَ")["clusters"]
        man = O.vocalization_state("مَن")["clusters"]
        self.assertIsNone(bare[0]["observed"]["short_vowel"])
        self.assertEqual(mina[0]["observed"]["short_vowel"], "kasra")
        self.assertEqual(man[0]["observed"]["short_vowel"], "fatha")
        self.assertEqual(O.vocalization_state("من")["state"], "unvoweled")
        self.assertEqual(O.vocalization_state("مِنَ")["state"], "fully_voweled")
        self.assertEqual(O.vocalization_state("مَن")["state"], "partially_voweled")

    def test_no_contextual_function_is_ever_reported(self):
        for surface in ("من", "مِنَ", "مَن"):
            record = O.vocalization_state(surface)
            self.assertNotIn("function", record)
            for c in record["clusters"]:
                self.assertNotIn("function", c)


class ArticleAssimilationTests(unittest.TestCase):
    def test_alshams_article_and_assimilation_observed_no_form_ii_inference(self):
        obs = O.assimilation_observation("ٱلشَّمْسَ")
        self.assertIsNotNone(obs)
        self.assertEqual(obs["article_form"], "ٱ")
        self.assertEqual(obs["lam_ownership"], "article")
        self.assertTrue(obs["host_initial_is_sun_letter_class"])
        self.assertTrue(obs["host_initial_shadda_observed"])
        self.assertTrue(obs["assimilation_observed"])
        # no doubled-root / Form-II claim is present anywhere in the record.
        self.assertNotIn("root", obs)
        self.assertNotIn("verb_form", obs)

    def test_alqamar_article_and_host_no_shadda_invented(self):
        obs = O.assimilation_observation("ٱلْقَمَرَ")
        self.assertIsNotNone(obs)
        self.assertFalse(obs["host_initial_shadda_observed"])
        self.assertFalse(obs["assimilation_observed"])
        self.assertEqual(obs["lam_ownership"], "article")

    def test_aldhakar_sun_letter_assimilation_observed(self):
        obs = O.assimilation_observation("ٱلذَّكَرَ")
        self.assertTrue(obs["assimilation_observed"])

    def test_wa_alunthaa_waw_plus_article_plus_host_byte_exact(self):
        art = O.article_candidate("وَٱلْأُنثَىٰ")
        self.assertIsNotNone(art)
        self.assertEqual(art["conjunction"], "وَ")
        rebuilt = art["conjunction"] + art["article_surface"] + art["host_surface"]
        self.assertEqual(rebuilt, "وَٱلْأُنثَىٰ")

    def test_canonical_and_bare_alif_forms_both_open_an_article_candidate(self):
        self.assertIsNotNone(O.article_candidate("ٱلْقَمَرَ"))
        self.assertIsNotNone(O.article_candidate("الْقَمَرَ"))

    def test_no_article_candidate_without_a_following_lam(self):
        self.assertIsNone(O.article_candidate("أحمد"))


class TanwinSupportAlifTests(unittest.TestCase):
    def test_quranan_tanwin_support_alif_never_a_pronoun(self):
        obs = O.tanwin_observation("قُرْءَانًا")
        self.assertTrue(obs["has_tanwin"])
        self.assertTrue(obs["has_support_alif"])
        self.assertEqual(obs["tanwin_mark"], "fathatan")

    def test_rahmatan_tanwin_on_ta_marbuta_no_support_alif_no_case_inference(self):
        obs = O.tanwin_observation("رَحْمَةً")
        self.assertTrue(obs["has_tanwin"])
        self.assertFalse(obs["has_support_alif"])
        self.assertNotIn("case", obs)

    def test_article_plus_tanwin_is_an_explicit_conflict_not_a_silent_resolution(self):
        conflict = O.article_tanwin_conflict("الكتابً")
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["status"], "abstain")
        self.assertEqual(conflict["conflict"], "article_and_tanwin")

    def test_no_conflict_when_only_one_condition_holds(self):
        self.assertIsNone(O.article_tanwin_conflict("قُرْءَانًا"))   # tanwin, no article
        self.assertIsNone(O.article_tanwin_conflict("ٱلْقَمَرَ"))     # article, no tanwin


class CarrierOrRadicalTests(unittest.TestCase):
    def test_insufficient_input_stays_unresolved(self):
        obs = O.carrier_or_radical("نور", 1)
        self.assertEqual(obs["status"], "unresolved")

    def test_written_shadda_settles_it_as_radical(self):
        obs = O.carrier_or_radical("وّ", 0)
        self.assertEqual(obs["status"], "radical")

    def test_non_carrier_letter_is_unresolved_not_radical(self):
        obs = O.carrier_or_radical("كتب", 0)
        self.assertEqual(obs["status"], "unresolved")
        self.assertEqual(obs["reason"], "not_a_carrier_letter_class")


class ArticleIntegrationInTextCheckTests(unittest.TestCase):
    """The checker's own segmentation lattice (tools.fusha_text_check.segment_candidates) must
    recognize the canonical ٱ article form, not only the bare ا form."""

    def _has_article_segment(self, surface):
        for cand in TC.segment_candidates(surface):
            if any(s["role"] == "definite_article" for s in cand["segments"]):
                return True
        return False

    def test_alshams_segments_article_plus_host(self):
        self.assertTrue(self._has_article_segment("ٱلشَّمْسَ"))

    def test_alqamar_segments_article_plus_host(self):
        self.assertTrue(self._has_article_segment("ٱلْقَمَرَ"))

    def test_aldhakar_segments_article_plus_host(self):
        self.assertTrue(self._has_article_segment("ٱلذَّكَرَ"))

    def test_wa_alunthaa_segments_article_plus_host_after_waw(self):
        self.assertTrue(self._has_article_segment("وَٱلْأُنثَىٰ"))

    def test_checker_flags_possible_definite_article_for_canonical_alif(self):
        rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "ٱلشَّمْسَ"})
        classes = {d["issue_class"] for d in rec["diagnostics"]}
        self.assertIn("possible_definite_article", classes)

    def test_segments_still_concatenate_to_the_surface_exactly(self):
        for surface in ("ٱلشَّمْسَ", "ٱلْقَمَرَ", "ٱلذَّكَرَ", "وَٱلْأُنثَىٰ"):
            for cand in TC.segment_candidates(surface):
                concat = "".join(s["surface"] for s in cand["segments"])
                self.assertEqual(concat, surface)


class TanwinIntegrationInPatternEngineTests(unittest.TestCase):
    """قُرْءَانًا must never be split as a verb stem + نا subject pronoun; a genuine verb stem
    ending in نا (with compatible verb evidence, and NOT a tanwīn support alif) must still split."""

    def _roles_for(self, surface):
        cands = split_clitics(surface)
        morph = PE.build_morphology(surface, cands, db="smoke")
        top = morph[0]
        seg_ref = top["segment_candidate_ref"]
        preview = PE.preview_segments(surface, cands[seg_ref], top)
        return {p["role"] for p in preview}

    def test_quranan_never_produces_a_subject_pronoun(self):
        roles = self._roles_for("قُرْءَانًا")
        self.assertNotIn("subject_pronoun", roles)

    def test_genuine_verb_plus_naa_still_splits(self):
        # أهلكنا: PINNED_FORMS Form-IV verb اهلك/أهلك + نا (compatible verb evidence) still splits
        # off from the verb stem, but the surface is fully UNVOWELED -- no written vocalization
        # decides subject vs. object here, so the clitic's function is honestly undetermined
        # rather than guessed from POS alone (Finding F6).
        roles = self._roles_for("أهلكنا")
        self.assertIn("verb_stem", roles)
        self.assertIn("clitic_undetermined", roles)
        self.assertNotIn("subject_pronoun", roles)
        self.assertNotIn("object_pronoun", roles)

    def test_ends_tanwin_alef_stem_is_excluded_directly(self):
        from tools import normalize_ar as N
        morph_verb = {"pos": "verb", "gloss_hint": None}
        parts = PE._verb_parts("قُرْءَانًا", morph_verb)
        self.assertFalse(any(p["role"] == "subject_pronoun" for p in parts),
                          "a tanwin-support-alif stem must never be split as stem+نا even if pos=verb")
        self.assertTrue(N.ends_tanwin_alef("قُرْءَانًا"))


class F1CombiningMarkInventoryTests(unittest.TestCase):
    """F1: U+0653 (maddah above) and U+0656..U+065F must be transparent combining marks, never a
    base cluster, and connectivity_class must fail closed (never dual_joining by default) for a
    character outside the closed Arabic letter inventory."""

    def test_madda_above_never_becomes_a_base_cluster(self):
        clusters = O.grapheme_clusters("جَآءَ")
        bases = [c["base"] for c in clusters]
        self.assertNotIn("ٓ", bases)
        self.assertEqual("".join(c["surface"] for c in clusters), "جَآءَ")

    def test_madda_above_is_transparent_and_kept_off_base_surface(self):
        self.assertEqual(O.connectivity_class("ٓ"), "transparent")
        self.assertNotIn("ٓ", O.base_surface("جَآءَ"))

    def test_extended_combining_range_all_transparent_and_never_a_base(self):
        for cp in range(0x0656, 0x0660):
            ch = chr(cp)
            self.assertEqual(O.connectivity_class(ch), "transparent", hex(cp))
            clusters = O.grapheme_clusters("ب" + ch)
            self.assertEqual(len(clusters), 1, hex(cp))
            self.assertEqual(clusters[0]["base"], "ب", hex(cp))

    def test_lilmalaikah_fully_voweled_not_partial(self):
        # the dagger-alif + maddah-above sequence on ل before ئِ must not fall out of the mark
        # inventory and silently degrade the token to partially_voweled.
        state = O.vocalization_state("لِلْمَلَٰٓئِكَةِ")["state"]
        self.assertEqual(state, "fully_voweled")

    def test_unknown_character_fails_closed_not_dual_joining(self):
        self.assertEqual(O.connectivity_class("a"), "unknown")
        self.assertEqual(O.connectivity_class("5"), "unknown")
        self.assertNotEqual(O.connectivity_class("a"), "dual_joining")

    def test_known_dual_joining_letters_still_classify(self):
        for ch in "بتثجحخسشصضطظعغفقكلمنهيئ":
            self.assertEqual(O.connectivity_class(ch), "dual_joining", ch)


class F2TanwinBeforeAlifMaqsuraTests(unittest.TestCase):
    """F2: a physically written fatḥatān immediately before a bare alif maqṣūra (هُدًى، فَتًى،
    مُصَلًّى) must be observed as tanwīn WITHOUT claiming a support alif -- ى is the direct
    spelling of the mark, not a separate support letter like قُرْءَانًا's ا."""

    def test_huda_fatan_musallan_observe_tanwin_without_support_alif(self):
        for surface in ("هُدًى", "فَتًى", "مُصَلًّى"):
            obs = O.tanwin_observation(surface)
            self.assertTrue(obs["has_tanwin"], surface)
            self.assertEqual(obs["tanwin_mark"], "fathatan", surface)
            self.assertFalse(obs["has_support_alif"], surface)
            self.assertIsNone(obs["support_alif_cluster_index"], surface)

    def test_article_plus_alif_maqsura_tanwin_still_abstains(self):
        conflict = O.article_tanwin_conflict("الهُدًى")
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["status"], "abstain")
        self.assertEqual(conflict["conflict"], "article_and_tanwin")

    def test_support_alif_case_is_unaffected(self):
        obs = O.tanwin_observation("قُرْءَانًا")
        self.assertTrue(obs["has_tanwin"])
        self.assertTrue(obs["has_support_alif"])


class F3ArticleCandidateShapeAmbiguityTests(unittest.TestCase):
    """F3: و/ف + BARE ا + ل opens the identical shape as a radical-initial فَاعِل stem
    (فَالِقُ، وَالِد، وَالٍ); shape alone must never assert an article there. A bare "ال" or a
    conjunction+article with nothing left for a host is never a genuine article+host token."""

    def test_radical_initial_faliq_walid_wali_fail_closed(self):
        for surface in ("فَالِقُ", "وَالِد", "وَالٍ"):
            self.assertIsNone(O.article_candidate(surface), surface)

    def test_bare_article_with_no_host_fails_closed(self):
        self.assertIsNone(O.article_candidate("ال"))

    def test_conjunction_article_with_no_host_fails_closed(self):
        self.assertIsNone(O.article_candidate("وَٱلْ"))

    def test_genuine_canonical_conjunction_article_canaries_still_open(self):
        for surface, conj in (("وَٱلْأُنثَىٰ", "وَ"), ("فَٱلْقَمَرَ", "فَ")):
            art = O.article_candidate(surface)
            self.assertIsNotNone(art, surface)
            self.assertEqual(art["conjunction"], conj, surface)
            self.assertEqual(art["article_form"], "ٱ", surface)

    def test_bare_alif_article_with_no_leading_conjunction_still_opens(self):
        self.assertIsNotNone(O.article_candidate("الْقَمَرَ"))
        self.assertIsNotNone(O.article_candidate("ٱلْقَمَرَ"))


class F4LexicalizedRelativeContractionTests(unittest.TestCase):
    """F4: the written لِ + ال contraction (لِلَّذِي، لِلَّتِي، لِلَّذِينَ) must never emit a
    definite_article split or a peeled-stem gloss -- these are lexicalized relative/function
    words, not article + noun-stem, regardless of whole-token lexicon-row availability. Genuine
    contracted-article cases like لِلَّهِ stay conservative (no article split either, unaffected)."""

    def _qg_roles_and_gloss(self, surface):
        rec = SP.parse_text(surface, db="full")
        tok = rec["tokens"][0]
        roles = {s["role"] for s in tok["qg_segments"]}
        gloss = (tok.get("hover_preview") or {}).get("token_contribution_gloss")
        return roles, gloss

    def test_lilladhi_lillati_lilladhina_never_split_the_article(self):
        for surface in ("لِلَّذِى", "لِلَّتِي", "لِلَّذِينَ"):
            roles, _ = self._qg_roles_and_gloss(surface)
            self.assertNotIn("definite_article", roles, surface)

    def test_lilladhi_never_leaks_the_unrelated_dhu_gloss(self):
        _, gloss = self._qg_roles_and_gloss("لِلَّذِى")
        self.assertIsNotNone(gloss)
        self.assertNotIn("possess", gloss.lower())

    def test_lillahi_stays_conservative_no_article_split(self):
        roles, _ = self._qg_roles_and_gloss("لِلَّهِ")
        self.assertNotIn("definite_article", roles)

    def test_hazard_helper_matches_the_canonical_and_contracted_spelling(self):
        contracted = {"segments": [{"role": "prefix_preposition", "surface": "لِ"},
                                    {"role": "definite_article", "surface": "لَّ"},
                                    {"role": "stem", "surface": "ذِى"}]}
        canonical = {"segments": [{"role": "definite_article", "surface": "ٱلَّ"},
                                   {"role": "stem", "surface": "ذِي"}]}
        self.assertTrue(SP._lexicalized_relative_hazard(contracted))
        self.assertTrue(SP._lexicalized_relative_hazard(canonical))

    def test_genuine_article_canaries_are_not_flagged_as_hazards(self):
        genuine = {"segments": [{"role": "definite_article", "surface": "ٱلْ"},
                                 {"role": "stem", "surface": "قَمَرَ"}]}
        self.assertFalse(SP._lexicalized_relative_hazard(genuine))


class F6NaaSubjectObjectDiscriminationTests(unittest.TestCase):
    """F6: enclitic نا must never be relabeled subject_pronoun ("we") solely because POS is verb.
    A written fatḥa on the stem's own final letter (خَلَقَنَا 'He created us') is the SAME bare
    letters as a written sukūن (خَلَقْنَا 'we created') with the OPPOSITE function; the two must
    never collapse to an identical asserted role."""

    def _roles_for(self, surface):
        cands = split_clitics(surface)
        morph = PE.build_morphology(surface, cands, db="largelexicon")
        top = morph[0]
        seg_ref = top["segment_candidate_ref"]
        preview = PE.preview_segments(surface, cands[seg_ref], top)
        return {p["role"]: p for p in preview}

    def test_fatha_before_naa_is_object_not_subject(self):
        for surface in ("خَلَقَنَا", "رَزَقَنَا"):
            roles = self._roles_for(surface)
            self.assertIn("object_pronoun", roles, surface)
            self.assertNotIn("subject_pronoun", roles, surface)

    def test_sukun_before_naa_stays_subject(self):
        roles = self._roles_for("خَلَقْنَا")
        self.assertIn("subject_pronoun", roles)
        self.assertNotIn("object_pronoun", roles)

    def test_object_and_subject_pair_never_produce_identical_asserted_function(self):
        object_roles = self._roles_for("خَلَقَنَا")
        subject_roles = self._roles_for("خَلَقْنَا")
        object_naa = object_roles.get("object_pronoun") or object_roles.get("subject_pronoun")
        subject_naa = subject_roles.get("object_pronoun") or subject_roles.get("subject_pronoun")
        self.assertNotEqual(
            (set(object_roles) & {"object_pronoun", "subject_pronoun"}),
            (set(subject_roles) & {"object_pronoun", "subject_pronoun"}),
        )

    def test_naa_role_helper_is_decisive_only_on_written_vocalization(self):
        self.assertEqual(PE._naa_role("خَلَقَ"), "object")
        self.assertEqual(PE._naa_role("خَلَقْ"), "subject")
        self.assertEqual(PE._naa_role("خلق"), "undetermined")


if __name__ == "__main__":
    unittest.main()
