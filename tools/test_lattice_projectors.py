#!/usr/bin/env python3
"""Tests for the transclusion-lattice projectors (T12).

Beyond the embedded ``self-test``, these assert the registry contract, the
data-driven guard/predicate dispatch, and the read-only projection behaviour on
in-memory fixtures. No production identifiers; no whitelist mutation.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import lattice_projectors as L  # noqa: E402


def wl(loc, surface, segments, morphline):
    return {"loc": loc, "surface": surface, "segments": segments, "morphline": morphline}


IMPF = [
    {"segment_index": 0, "role": "verb_prefix", "label": "PFX", "surface": "يَ"},
    {"segment_index": 1, "role": "verb_stem", "label": "STEM", "surface": "فْعَلُ"},
]


class RegistryTests(unittest.TestCase):
    def test_registry_loads_and_validates_against_projector_schema(self):
        reg = L.load_registry()
        ids = [e["projector_id"] for e in reg["registered"]]
        self.assertEqual(
            ids,
            [
                "sarf.c1_impf_segmentation.v1",
                "sarf.c5_enclitic_segmentation.v1",
                "sarf.meta_form56_ta_negative.v1",
                "sarf.root_inherit_transclusion.v1",
                "sarf.note_normalize.v1",
                "sarf.suffix_fempl_segmentation.v1",
            ],
        )
        for e in reg["registered"]:
            self.assertIn(e["class_predicate"], L.NAMED_PREDICATES)
            for g in e["guards"]:
                self.assertIn(g, L.NAMED_GUARDS)
            self.assertEqual([], L._validate_registry_entry(e["registry_entry"]))

    def test_cli_self_test_passes(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "lattice_projectors.py"), "self-test"],
            cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=False,
        )
        self.assertEqual(0, r.returncode, r.stderr + r.stdout)
        self.assertTrue(json.loads(r.stdout)["ok"])


class ClassPredicateTests(unittest.TestCase):
    def test_c1_requires_imperfect_prefix_and_stem(self):
        self.assertTrue(L.pred_c1_impf(wl("1:1:1", "يَفْعَلُ", IMPF, "root f C l · Form I imperfect active")))
        self.assertFalse(L.pred_c1_impf(wl("1:1:1", "فَعَلَ", IMPF, "root f C l · Form I perfect active")))

    def test_c5_requires_host_plus_enclitic(self):
        row = wl("1:1:1", "كِتَابُهُ", [
            {"segment_index": 0, "role": "noun_stem", "label": "N", "surface": "كِتَابُ"},
            {"segment_index": 1, "role": "possessive_pronoun", "label": "POSS", "surface": "هُ"},
        ], "noun + possessive")
        self.assertTrue(L.pred_c5_enclitic(row))
        # a leading independent pronoun is not an enclitic carve
        self.assertFalse(L.pred_c5_enclitic(wl("1:1:1", "هُوَ", [
            {"segment_index": 0, "role": "independent_pronoun_3ms", "label": "PRON", "surface": "هُوَ"}
        ], "pronoun")))


class NegativeMetaTests(unittest.TestCase):
    def test_form_viii_prefix_is_not_flagged(self):
        # Form VIII imperfect: leading taa' is a legitimate person prefix; the exact
        # form token must not collide with the 'Form VI' substring.
        row = wl("2:63:15", "تَتَّقُونَ", [
            {"segment_index": 0, "role": "verb_prefix", "label": "PFX", "surface": "تَ"},
            {"segment_index": 1, "role": "verb_stem", "label": "STEM", "surface": "تَّقُ"},
            {"segment_index": 2, "role": "subject_pronoun", "label": "SUBJ", "surface": "ونَ"},
        ], "root w q y · Form VIII imperfect active · +SUBJ 2mp")
        self.assertFalse(L.splits_derivational_ta(L.analysis_of(row)))

    def test_form_v_imperfect_prefix_is_not_flagged(self):
        # Form V imperfect: prefix taa' precedes a stem that KEEPS the derivational taa'.
        row = wl("1:1:1", "تَتَبَيَّنُ", [
            {"segment_index": 0, "role": "verb_prefix", "label": "PFX", "surface": "تَ"},
            {"segment_index": 1, "role": "verb_stem", "label": "STEM", "surface": "تَبَيَّنُ"},
        ], "root b y n · Form V imperfect active")
        self.assertFalse(L.splits_derivational_ta(L.analysis_of(row)))

    def test_form_v_perfect_peeled_augment_is_flagged(self):
        row = wl("2:259:58", "تَبَيَّنَ", [
            {"segment_index": 0, "role": "verb_prefix", "label": "PFX", "surface": "تَ"},
            {"segment_index": 1, "role": "verb_stem", "label": "STEM", "surface": "بَيَّنَ"},
        ], "root b y n · Form V perfect active · 3ms")
        self.assertTrue(L.splits_derivational_ta(L.analysis_of(row)))

    def test_plural_suffix_taa_is_not_flagged(self):
        row = wl("4:25:33", "مُتَّخِذَٰتِ", [
            {"segment_index": 0, "role": "derivative_prefix", "label": "DER", "surface": "مُ"},
            {"segment_index": 1, "role": "participle_stem", "label": "PTCP", "surface": "تَّخِذَٰ"},
            {"segment_index": 2, "role": "plural_suffix", "label": "PL", "surface": "تِ"},
        ], "root a kh dh · Form VIII active participle feminine plural")
        self.assertFalse(L.splits_derivational_ta(L.analysis_of(row)))


class ProjectionTests(unittest.TestCase):
    def test_reachable_excludes_covered_and_routes_homographs(self):
        surface = "يَفْعَلُ"
        src = wl("2:2:2", surface, IMPF, "root f C l · Form I imperfect active")
        corpus = [("2:2:2", surface), ("5:5:5", surface)]
        homs = L.build_homograph_surfaces([src])
        c1 = L.load_registry()["registered"][0]
        recs, instr = L.run_positive_projector(c1, [src], {"2:2:2"}, corpus, homs)
        self.assertEqual(1, instr["reachable_uncovered_rows"])
        self.assertEqual(1, instr["auto_candidates"])
        self.assertEqual("candidate", recs[0]["projection_state"])
        self.assertEqual("5:5:5", recs[0]["target_loc"])
        # candidate carries lineage + gate, never a certified/materialized state
        self.assertEqual("two_vote_required", recs[0]["gate_tier"])
        self.assertTrue(recs[0]["created_from"].startswith("projector:"))


class RootInheritanceTests(unittest.TestCase):
    def _idx(self):
        entries = [
            {"id": "e1", "root": "ك ف ر", "headword": "كَفَرَ", "category": "Verbs with Derivatives",
             "usage": [{"forms": ["الْكَافِرِينَ", "كَافِرٌ"]}]},
            {"id": "e2", "root": "س خ ر", "headword": "سَخَّرَ", "category": "Verbs with Derivatives",
             "usage": [{"forms": ["مُسَخَّرَات", "مُسَخَّر"]}]},
        ]
        return L.build_entry_index(entries)

    def test_dagger_alef_matches_full_alif_but_hamza_preserved(self):
        self.assertEqual(L.match_key("مُسَخَّرَٰتٍۭ"), L.match_key("مُسَخَّرَات"))
        self.assertNotEqual(L.match_key("أمن"), L.match_key("امن"))

    def test_rootless_lexhead_inherits_and_is_candidate(self):
        form_root, eid_root = self._idx()
        row = {"loc": "36:70:4", "surface": "الْكَافِرِينَ", "morphline": "no public root asserted",
               "segments": [{"segment_index": 0, "surface": "الْ", "label": "ART", "role": "definite_article"},
                            {"segment_index": 1, "surface": "كَافِرِ", "label": "STEM", "role": "participle_stem"},
                            {"segment_index": 2, "surface": "ينَ", "label": "PL", "role": "masculine_plural_suffix"}]}
        proj = {e["projector_id"]: e for e in L.load_registry()["registered"]}["sarf.root_inherit_transclusion.v1"]
        recs, instr, worked = L.run_root_inherit(proj, [row], form_root, eid_root, {}, {})
        self.assertEqual("ك ف ر", recs[0]["inherited"]["root"])
        self.assertEqual("candidate", recs[0]["certification_state"])
        self.assertIsNone(recs[0]["guard"])

    def test_carrier_entry_id_alone_does_not_assert_root(self):
        # entry_id points at an example-context entry whose forms do NOT include the surface:
        # it must NOT drive inheritance (DR-2), so the row falls through to authoring.
        form_root, eid_root = self._idx()
        row = {"loc": "2:63:5", "surface": "فَوْقَكُمُ", "morphline": "no public root asserted",
               "entry_id": "e1",  # كفر example page, but فوقكم is not a كفر form
               "segments": [{"segment_index": 0, "surface": "فَوْقَ", "label": "TOK", "role": "token"}]}
        proj = {e["projector_id"]: e for e in L.load_registry()["registered"]}["sarf.root_inherit_transclusion.v1"]
        recs, instr, worked = L.run_root_inherit(proj, [row], form_root, eid_root, {}, {})
        self.assertEqual([], recs)
        self.assertEqual(1, instr["authoring_no_attested_source"])


class SuffixFemplTests(unittest.TestCase):
    def test_projects_stem_plus_plural(self):
        form_root, _ = L.build_entry_index([
            {"id": "e2", "root": "س خ ر", "headword": "سَخَّرَ", "category": "Verbs with Derivatives",
             "usage": [{"forms": ["مُسَخَّر", "مُسَخَّرَات"]}]}])
        row = {"loc": "7:54:23", "surface": "مُسَخَّرَٰتٍۭ", "morphline": "no public root asserted",
               "segments": [{"segment_index": 0, "surface": "مُسَخَّرَٰتٍۭ", "label": "TOK", "role": "token"}]}
        proj = {e["projector_id"]: e for e in L.load_registry()["registered"]}["sarf.suffix_fempl_segmentation.v1"]
        recs, instr = L.run_suffix_fempl(proj, [row], form_root, {}, {})
        self.assertEqual(1, len(recs))
        self.assertEqual("feminine_plural_suffix", recs[0]["proposed_segments"][1]["role"])
        self.assertEqual("س خ ر", recs[0]["inherited_root"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
