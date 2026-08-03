#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_nawasikh_diagnostic_export — red-first tests for the Train B/C L2.M2 nawāsikh diagnostic-export adapter.

Proves, in order:
  1. BEFORE this batch, no family-specific nawāsikh diagnostic reached the learner-KC path (structural proof:
     the arbitrary-text checker's IRAB_SENSITIVE_ISSUE_CLASSES/ISSUE_ROUTE vocabularies carry no nawāsikh-family
     name; the five family KCs are NEW catalog entries distinct from the generic kc-governor-justification).
  2. The bounded adapter (tools.fusha_governor.nawasikh_lattice_family /
     tools.fusha_governor.nawasikh_pending_diagnostics) classifies one lattice input per family into ITS OWN KC
     via tools.fusha_check.NAWASIKH_FAMILY_KC + tools.fusha_learner_feedback.nawasikh_family_events. Two families
     (kāna/laysa, inna-family) use a real source-addressed Qurʾānic occurrence, because the lattice's
     address-bearing sweep natively derives their regime from token POS/case_visible alone. The other three
     (continuative licensing, qalb-verb transitivity, stacked-governor scope) have NO token-level source-
     addressed representation in this lattice — their evidence (a polarity licenser, a verb sense, a clause
     bracketing) is a SUPPLIED feature the address-bearing sweep does not model from raw tokens, so they are
     exercised through the same "constructed" supplied-evidence path `nahw/evals/nawasikh-government-eval.jsonl`
     already uses for these exact three families (C4/C5/C6) — never a fabricated occurrence claim.
  3. Hostile cases abstain or avoid the wrong class (light lakin, syncretic case endings, coordinating wāw,
     literal-perception qalb-verb sense, إنما not inheriting bare إن's government, stacked-governor rivals).
  4. Every emitted class maps to exactly one KC (bijective family -> KC, no collisions, no substitute KCs).
  5. Candidate provenance (drill_id / mc-id / curriculum-l1l6 ids) is absent from every adapter/event output.
  6. Inna-family MODAL FORCE is deliberately NOT registered as an emitted class (cu-inna-modal-force is
     `capability_family: instructional_only`, "no current consumer can act on it" — fabricating one would be a
     false-consumption claim).

Run: python3 tools/test_nawasikh_diagnostic_export.py
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_governor as GOV  # noqa: E402
from tools import fusha_check as FC  # noqa: E402
from tools import fusha_learner_feedback as LF  # noqa: E402
from tools import validate_learner_feedback as VLF  # noqa: E402

_KC_CATALOG_PATH = os.path.join(_REPO, "curriculum", "kc-catalog.json")


def _constructed(features):
    return {"input_mode": "arbitrary_typing", "frame_kind": "constructed", "construction_family": "nawasikh",
            "source_unit": {"address": "", "scope": "arbitrary"}, "tokens": [{"ref": "tok:0", "surface": "x"}],
            "features": features}


# one source-addressed / evidence-bearing lattice input per family (mirrors nahw/evals/nawasikh-government-eval.jsonl)
FAMILY_FIXTURES = {
    "kana_laysa_government": {"input_mode": "source_addressed", "frame_kind": "address_bearing",
                              "source_unit": {"address": "quran:4:17", "scope": "in_scope_source_addressed"},
                              "tokens": [{"ref": "4:17:17", "surface": "وَكَانَ", "pos": "verb"},
                                        {"ref": "4:17:18", "surface": "ٱللَّهُ", "pos": "proper_noun", "case_visible": "nominative"},
                                        {"ref": "4:17:19", "surface": "عَلِيمًا", "pos": "adjective", "case_visible": "accusative"}]},
    "inna_family_government": {"input_mode": "source_addressed", "frame_kind": "address_bearing",
                               "source_unit": {"address": "quran:2:177", "scope": "in_scope_source_addressed"},
                               "tokens": [{"ref": "2:177:9", "surface": "وَلَٰكِنَّ", "pos": "particle"},
                                         {"ref": "2:177:10", "surface": "ٱلْبِرَّ", "pos": "noun", "case_visible": "accusative"}]},
    "continuative_licensing": _constructed({"polarity_licenser": "absent", "regime": "kana_family_polarity_licensed"}),
    "qalb_verb_transitivity": _constructed({"regime": "zanna_family", "sense": "judgemental",
                                            "first_object_marking": "nasb", "second_object_marking": "nasb"}),
    "stacked_governor_scope": _constructed({"abrogator_count": 2, "bracketing": "ambiguous"}),
}


class NawasikhAdapterDeepStructure(unittest.TestCase):
    """Establishes the RED condition this adapter fixes still holds for the vocabularies it must NOT touch."""

    def test_generic_arbitrary_checker_vocabulary_carries_no_nawasikh_family_name(self):
        # the pre-existing arbitrary-text checker classes named in the defect report — unchanged by this batch.
        generic = {"possible_particle_function", "possible_case_or_mood_requires_context", "possible_governor_unresolved"}
        self.assertTrue(generic.issubset(FC.IRAB_SENSITIVE_ISSUE_CLASSES))
        for family_label in GOV.NAWASIKH_DIAGNOSTIC_FAMILIES:
            self.assertNotIn(family_label, FC.ISSUE_ROUTE)
            self.assertNotIn(family_label, FC.IRAB_SENSITIVE_ISSUE_CLASSES)

    def test_five_family_kcs_are_new_and_distinct_from_the_generic_governor_kc(self):
        with open(_KC_CATALOG_PATH, encoding="utf-8") as fh:
            kcs = {k["kc_id"]: k for k in json.load(fh)}
        for family, kc_id in FC.NAWASIKH_FAMILY_KC.items():
            self.assertIn(kc_id, kcs, "family %r's KC %r missing from the catalog" % (family, kc_id))
            self.assertNotEqual(kc_id, "kc-governor-justification")
            self.assertEqual(kcs[kc_id]["drill_route"], "curriculum/drills/nawasikh-governor-families.md")

    def test_modal_force_has_no_registered_family_or_kc(self):
        self.assertNotIn("inna_modal_force", GOV.NAWASIKH_DIAGNOSTIC_FAMILIES)
        self.assertNotIn("inna_modal_force", FC.NAWASIKH_FAMILY_KC)


class NawasikhAdapterFamilyClassification(unittest.TestCase):
    """One lattice input per family (source-addressed for kāna/laysa and inna-family; supplied-evidence
    constructed for the three whose evidence has no token-level source-addressed form) -> its own KC, never
    resolved, never a substitute KC, never an invented issue_class."""

    def test_each_family_produces_a_diagnostic_routed_to_its_own_kc(self):
        for family, unit in FAMILY_FIXTURES.items():
            with self.subTest(family=family):
                diags = GOV.nawasikh_pending_diagnostics(unit)
                self.assertTrue(diags, "no diagnostic produced for %r" % family)
                self.assertTrue(any(d["family"] == family for d in diags))
                events = LF.nawasikh_family_events(unit)
                self.assertTrue(events, "no learner-feedback event produced for %r" % family)
                expected_kc = FC.NAWASIKH_FAMILY_KC[family]
                for ev in events:
                    self.assertEqual(ev["knowledge_component"], expected_kc)
                    self.assertNotEqual(ev["knowledge_component"], "kc-governor-justification")
                    self.assertIn(ev["diagnostic_class"], VLF._DIAG_CLASSES,
                                 "diagnostic_class must be the existing closed fusha-text-check value, never invented")
                    self.assertIsNone(ev["bottom_out_hint"], "never certifies a fact: bottom_out must stay withheld")
                    self.assertEqual(ev["decision_status"], "pending")
                    self.assertNotEqual(ev["when_not_to_give_answer"]["gate"], "auto_safe")
                    self.assertFalse(VLF.validate_event(ev), "adapter event must validate clean")

    def test_bijective_family_to_kc_mapping_no_collisions(self):
        kc_ids = list(FC.NAWASIKH_FAMILY_KC.values())
        self.assertEqual(len(kc_ids), len(set(kc_ids)), "two families must never share one KC")
        self.assertEqual(set(FC.NAWASIKH_FAMILY_KC), set(GOV.NAWASIKH_DIAGNOSTIC_FAMILIES))

    def test_contradiction_and_rivals_are_preserved_never_silently_corrected(self):
        # a kāna-pattern (raf3/nasb) read under an inna-family head is a CONTRADICTION candidate, not a "fix".
        contradiction_unit = _constructed({"ism_marking": "raf3", "khabar_marking": "nasb", "regime": "inna_family"})
        diags = GOV.nawasikh_pending_diagnostics(contradiction_unit)
        self.assertTrue(any(d["contradiction_marker"] for d in diags))
        self.assertTrue(all(d["decision_status"] == "pending" for d in diags))


class NawasikhAdapterHostileCases(unittest.TestCase):
    """Every hostile case named in the task spec: abstain or avoid the wrong class."""

    def test_light_lakin_is_not_classified_as_a_heavy_inna_family_governor(self):
        unit = {"input_mode": "arbitrary_typing",
                "tokens": [{"ref": "tok:0", "surface": "لَٰكِنْ", "pos": "particle"},
                          {"ref": "tok:1", "surface": "قَالَ", "pos": "verb"}]}
        diags = GOV.nawasikh_pending_diagnostics(unit)
        self.assertFalse(diags, "a light لكن must never classify into any nawāsikh family")

    def test_innama_does_not_inherit_bare_inna_government(self):
        # إنما is a distinct surface from إن and does not key into _TRIGGER_FAMILIES; no edge -> no family.
        unit = {"input_mode": "arbitrary_typing",
                "tokens": [{"ref": "tok:0", "surface": "إِنَّمَا", "pos": "particle"},
                          {"ref": "tok:1", "surface": "ٱللَّهُ", "pos": "proper_noun"}]}
        diags = GOV.nawasikh_pending_diagnostics(unit)
        self.assertFalse(diags, "إنما must not silently inherit إن's ordinary government without modeled scope evidence")

    def test_syncretic_endings_do_not_prove_a_case(self):
        unit = {"input_mode": "source_addressed", "frame_kind": "address_bearing",
                "source_unit": {"address": "quran:2:102", "scope": "in_scope_source_addressed"},
                "tokens": [{"ref": "2:102:11", "surface": "وَلَٰكِنَّ", "pos": "particle"},
                          {"ref": "2:102:12", "surface": "ٱلشَّيَٰطِينَ", "pos": "noun", "exponent_syncretic": True}]}
        diags = GOV.nawasikh_pending_diagnostics(unit)
        self.assertTrue(diags)
        for d in diags:
            self.assertIsNone(GOV.build_dependency_lattice(unit)["edges"][0].get("assigned_case_mood"))
            self.assertEqual(d["abstention_reason"], "marking_unknown")

    def test_ordinary_coordinating_waw_acquires_no_invented_governor(self):
        unit = {"input_mode": "arbitrary_typing",
                "tokens": [{"ref": "tok:0", "surface": "و", "pos": "conjunction"},
                          {"ref": "tok:1", "surface": "ٱلشَّمْسَ", "pos": "noun"}]}
        diags = GOV.nawasikh_pending_diagnostics(unit)
        self.assertFalse(diags, "coordinating وَ must never acquire a nawāsikh family/governor")

    def test_literal_perception_is_not_forced_into_two_object_cognition_analysis(self):
        unit = _constructed({"regime": "zanna_family", "sense": "literal_perception"})
        diags = GOV.nawasikh_pending_diagnostics(unit)
        self.assertTrue(diags)
        d = diags[0]
        self.assertEqual(d["family"], "qalb_verb_transitivity")
        self.assertEqual(d["abstention_reason"], "sense_dependent_gate")
        self.assertFalse(d["contradiction_marker"])

    def test_stacked_governors_preserve_abstention_never_a_forced_scope(self):
        unit = _constructed({"abrogator_count": 2, "bracketing": "ambiguous"})
        diags = GOV.nawasikh_pending_diagnostics(unit)
        self.assertTrue(diags)
        self.assertEqual(diags[0]["family"], "stacked_governor_scope")
        self.assertEqual(diags[0]["abstention_reason"], "bracketing_ambiguous")


class NawasikhAdapterProvenanceBoundary(unittest.TestCase):
    """Candidate provenance must never leak into the adapter's diagnostics or the emitted learner-feedback events."""

    _PROVENANCE_MARKERS = ("dr-mc-", "mc-0", "drill_id", "curriculum_l1l6_id", "candidate_drill_id")

    def test_no_candidate_provenance_in_adapter_diagnostics_or_events(self):
        for family, unit in FAMILY_FIXTURES.items():
            for d in GOV.nawasikh_pending_diagnostics(unit):
                blob = json.dumps(d, ensure_ascii=False)
                for marker in self._PROVENANCE_MARKERS:
                    self.assertNotIn(marker, blob, "%s leaked into a %r diagnostic" % (marker, family))
            for ev in LF.nawasikh_family_events(unit):
                blob = json.dumps(ev, ensure_ascii=False)
                for marker in self._PROVENANCE_MARKERS:
                    self.assertNotIn(marker, blob, "%s leaked into a %r learner-feedback event" % (marker, family))


if __name__ == "__main__":
    unittest.main(verbosity=2)
