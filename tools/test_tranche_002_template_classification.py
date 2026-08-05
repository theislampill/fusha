#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused red-first tests for the T2 template-classification batch (ten preserved units).

Every unit here is CANDIDATE machinery only: it never certifies an occurrence, infers a
lexeme/sense/meaning/translation, or becomes public-projection eligible. These tests prove the
real directory-discovered tools/curriculum_unit_consumer.py loads each new pack and its fixtures,
that the four new dispatcher extensions (R4/GEM template slots, the gemination-licensing gate,
the diminutive base-lexeme/affix gate, and the passive-voice written-vocalization disambiguator)
are genuinely PACK-DRIVEN (a pack mutation flips the decision), and that hostile/near-collision
input never survives as a default candidate.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import curriculum_unit_consumer as cu  # noqa: E402
import build_curriculum_canonical as canonical_builder  # noqa: E402

INC_BASE = ROOT / "curriculum" / "l1l6" / "increments"

NEW_TEMPLATE_INCREMENTS = (
    "inc-diminutive-template-family",
    "inc-five-verb-inflection-class",
    "inc-quadriliteral-templates",
    "inc-gemination-licensing",
)
NEW_DISCRIMINATOR_INCREMENTS = (
    "inc-suffix-abstract-noun",
    "inc-nongoverning-preverbal-inventory",
    "inc-nun-raf-vs-nun-niswa",
    "inc-initial-hamza-class",
    "inc-lexical-feminine-registry",
)
ALL_NEW_INCREMENTS = NEW_TEMPLATE_INCREMENTS + NEW_DISCRIMINATOR_INCREMENTS


def _deep_copy(obj):
    return json.loads(json.dumps(obj))


class NewIncrementsDiscoveredAndGreenTests(unittest.TestCase):
    """Every new increment is directory-discovered (not a hard-coded list) and every one of its
    committed fixtures matches through the real consumer."""

    def test_all_nine_new_increments_are_discovered(self):
        discovered = cu.discover_increments()
        for inc in ALL_NEW_INCREMENTS:
            self.assertIn(inc, discovered, "%s must be directory-discovered" % inc)

    def test_every_new_increment_is_green(self):
        for inc in ALL_NEW_INCREMENTS:
            rec = cu.run(inc)
            self.assertEqual(rec["mismatches"], 0,
                             "%s has mismatches: %r" % (inc, [r for r in rec["results"] if not r["match"]]))
            self.assertGreaterEqual(rec["fixtures"], 6, "%s needs meaningful fixture coverage" % inc)

    def test_every_new_increment_declares_a_registered_non_hidden_capability(self):
        for inc in ALL_NEW_INCREMENTS:
            unit, _ = cu.load(inc)
            cap = unit.get("capability")
            self.assertIn(cap, ("template_classification", "discriminator_table"))
            self.assertNotEqual(cap, "licensing_table",
                                "the hidden-structure ontology must never be reused for "
                                "unrelated morphological licensing: %s" % inc)

    def test_every_new_fixture_is_candidate_status(self):
        for inc in ALL_NEW_INCREMENTS:
            _, fixtures = cu.load(inc)
            for fx in fixtures:
                self.assertEqual(fx["status"], "candidate", "%s/%s" % (inc, fx["fixture_id"]))

    def test_every_new_increment_has_positive_adversarial_and_abstention_fixtures(self):
        for inc in ALL_NEW_INCREMENTS:
            _, fixtures = cu.load(inc)
            classes = {fx["class"] for fx in fixtures}
            self.assertIn("positive", classes, inc)
            self.assertIn("adversarial", classes, inc)
            has_abstention = any(
                fx["class"] == "abstention" or fx["expected"].get("decision") == "abstain"
                for fx in fixtures
            )
            self.assertTrue(has_abstention, "%s needs at least one abstention fixture" % inc)

    def test_voice_melody_v2_pack_exists_and_is_green_and_v1_still_abstains_conservatively(self):
        rec2 = cu.run("inc-voice-melody-templates", "unit-v2.json")
        self.assertEqual(rec2["mismatches"], 0)
        pack2, _ = cu.load("inc-voice-melody-templates", "unit-v2.json")
        self.assertEqual(
            pack2["unit_refs"],
            ["cu-passive-voice-vocalization", "cu-voice-melody-templates"],
            "a superseding voice pack must preserve both canonical contributions",
        )
        rec1 = cu.run("inc-voice-melody-templates", "unit-v1.json")
        # v1 is not WRONG about anything: it keeps abstaining ambiguous_template on every one of
        # the six newly-resolvable rows (it has no `vocalization_disambiguation` flag at all), so
        # the "mismatch" here is purely v1 being less capable than v2, never a false candidate --
        # the same recorded-defect pattern inc-derivatives already pins for its own older packs.
        newly_resolvable = {"voc-pos-01", "voc-pos-02", "voc-pos-03",
                            "voc-pos-04", "voc-pos-05", "voc-pos-06"}
        bad = {r["fixture_id"] for r in rec1["results"] if not r["match"]}
        self.assertEqual(bad, newly_resolvable)
        for r in rec1["results"]:
            if r["fixture_id"] in newly_resolvable:
                self.assertEqual(r["actual"], {"decision": "abstain", "reason": "ambiguous_template"})

    def test_canonical_backlinks_preserve_both_voice_units(self):
        units, _, _, _ = canonical_builder.build(canonical_builder.load())
        by_id = {row["unit_id"]: row for row in units}
        for unit_id in ("cu-passive-voice-vocalization", "cu-voice-melody-templates"):
            self.assertIn(
                "inc-voice-melody-templates",
                by_id[unit_id]["machine_increments"],
                "%s lost its machine-pack backlink" % unit_id,
            )

    def test_t2a_real_consumer_binding_covers_every_pack_backed_unit(self):
        rows = [
            json.loads(line)
            for line in (ROOT / "curriculum" / "l1l6" / "links" /
                          "consumer-operationalization-bindings.jsonl").read_text(
                              encoding="utf-8").splitlines()
            if line.strip()
        ]
        binding = next(
            row for row in rows
            if row["binding_id"] ==
            "l1l6-tranche-002a-template-classification-analysis"
        )
        expected_units = {
            "cu-diminutive-template-family",
            "cu-five-verb-inflection-class",
            "cu-gemination-licensing",
            "cu-initial-hamza-class",
            "cu-lexical-feminine-registry",
            "cu-nongoverning-preverbal-inventory",
            "cu-nun-raf-vs-nun-niswa",
            "cu-passive-voice-vocalization",
            "cu-quadriliteral-templates",
            "cu-suffix-abstract-noun",
            "cu-voice-melody-templates",
        }
        self.assertEqual(set(binding["unit_ids"]), expected_units)
        self.assertEqual(binding["consumer_plane"], "sarf_analytical")
        self.assertFalse(binding["public_projection_eligible"])
        self.assertTrue(binding["candidate_status_preserved"])

    def test_consumer_self_test_still_passes(self):
        self.assertEqual(cu.self_test(), 0)


SEVEN_PART_CONTRACT_FILES = ("reference.md", "procedure.md", "staged-explanation.md",
                             "hover-fields.json", "guards.json")


class SevenPartPackContractTests(unittest.TestCase):
    """Every directory-discovered committed pack (a unit-vN.json + fixtures.jsonl already present) must
    also carry its reference/procedure/staged-explanation/hover-fields/guards quintet -- the complete
    seven-part contract (unit, fixtures, reference, procedure, staged explanation, hover fields, guards).
    Before this batch authored the five support files for each of the nine T2 packs,
    tools/validate_curriculum_l1l6.py independently reported exactly 45 missing-file failures across
    these same nine increments; this test reproduces that same completeness requirement directly against
    the real directory-discovered pack set (never a hard-coded increment list)."""

    def test_every_discovered_increment_has_the_complete_seven_part_contract(self):
        discovered = cu.discover_increments()
        missing_by_inc = {}
        for inc in sorted(discovered):
            inc_dir = INC_BASE / inc
            missing = [name for name in SEVEN_PART_CONTRACT_FILES if not (inc_dir / name).is_file()]
            if missing:
                missing_by_inc[inc] = missing
        self.assertEqual(missing_by_inc, {},
                         "every committed pack (unit + fixtures) needs its full seven-part contract "
                         "(unit, fixtures, reference.md, procedure.md, staged-explanation.md, "
                         "hover-fields.json, guards.json): %r" % missing_by_inc)

    def test_the_nine_t2_increments_specifically_carry_every_support_file(self):
        for inc in ALL_NEW_INCREMENTS:
            inc_dir = INC_BASE / inc
            for name in SEVEN_PART_CONTRACT_FILES:
                self.assertTrue((inc_dir / name).is_file(), "%s/%s must exist" % (inc, name))


class QuadriliteralTemplateR4Tests(unittest.TestCase):
    """cu-quadriliteral-templates (L5.M4.06): a fourth radical is licensed exactly like the
    first three, and a genuinely ambiguous unvocalised active/passive participle abstains."""

    def setUp(self):
        self.unit, self.fixtures = cu.load("inc-quadriliteral-templates")

    def test_match_template_licenses_a_fourth_radical(self):
        used = cu._match_template(["R1", "R2", "R3", "R4"], list("دحرج"), list("دحرج"), {})
        self.assertEqual(used, [])

    def test_four_radical_perfect_resolves(self):
        rec = cu.analyze_derivative(
            {"letters": list("دحرج"), "surface": "دحرج",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("دحرج")}},
            self.unit)
        self.assertEqual(rec["decision"], "candidate_pending")
        self.assertEqual(rec["template"], "fa3lala_perfect_active")

    def test_active_passive_participle_collision_abstains(self):
        rec = cu.analyze_derivative(
            {"letters": list("مدحرج"), "surface": "مدحرج",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("دحرج")}},
            self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "ambiguous_template"})

    def test_three_radical_root_never_borrows_the_fourth_slot(self):
        rec = cu.analyze_derivative(
            {"letters": list("دحر"), "surface": "دحر",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("دحر")}},
            self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "no_template"})

    def test_pack_mutation_flips_decision(self):
        fx = next(f for f in self.fixtures if f["fixture_id"] == "quad-pos-01")
        unit_m = _deep_copy(self.unit)
        unit_m["templates"] = [t for t in unit_m["templates"] if t["id"] != "fa3lala_perfect_active"]
        rec = cu.analyze_derivative(fx["input"], unit_m)
        self.assertNotEqual(rec, cu.analyze_derivative(fx["input"], self.unit))
        self.assertEqual(rec["decision"], "abstain")


class GeminationLicensingTests(unittest.TestCase):
    """cu-gemination-licensing (L5.M4.02): an exact declared environment is required; unresolved
    shadda source, jussive variants and cross-boundary mergers all abstain."""

    def setUp(self):
        self.unit, self.fixtures = cu.load("inc-gemination-licensing")

    def _base(self, **overrides):
        ev = {"basis": "qamus_entry_ladder", "radicals": list("درس"),
              "gemination_position": "R2", "gemination_radical": "ر",
              "gemination_evidence": {"shadda_source": "written_shadda",
                                      "mood": "indicative", "boundary": "word_internal"}}
        ev.update(overrides.pop("root_evidence_overrides", {}))
        inp = {"letters": list("درس"), "surface": "درس", "root_evidence": ev}
        inp.update(overrides)
        return inp

    def test_licensed_gemination_resolves(self):
        rec = cu.analyze_derivative(self._base(), self.unit)
        self.assertEqual(rec["decision"], "candidate_pending")
        self.assertEqual(rec["template"], "fa33ala_perfect_active")

    def test_unbound_declaration_abstains(self):
        inp = self._base(root_evidence_overrides={"gemination_position": "R1"})
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec["decision"], "abstain")
        self.assertEqual(rec["reason"], "gemination_declaration_unbound")

    def test_unresolved_shadda_source_abstains(self):
        ev = {"basis": "qamus_entry_ladder", "radicals": list("درس"),
              "gemination_position": "R2", "gemination_radical": "ر",
              "gemination_evidence": {"shadda_source": "assumed",
                                      "mood": "indicative", "boundary": "word_internal"}}
        rec = cu.analyze_derivative({"letters": list("درس"), "surface": "درس", "root_evidence": ev},
                                    self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "shadda_source_unresolved",
                               "unbound_slot": "R2", "template": "fa33ala_perfect_active"})

    def test_jussive_variant_abstains(self):
        ev = {"basis": "qamus_entry_ladder", "radicals": list("درس"),
              "gemination_position": "R2", "gemination_radical": "ر",
              "gemination_evidence": {"shadda_source": "written_shadda",
                                      "mood": "jussive", "boundary": "word_internal"}}
        rec = cu.analyze_derivative({"letters": list("درس"), "surface": "درس", "root_evidence": ev},
                                    self.unit)
        self.assertEqual(rec["reason"], "jussive_variant_unlicensed")

    def test_cross_boundary_merger_abstains(self):
        ev = {"basis": "qamus_entry_ladder", "radicals": list("درس"),
              "gemination_position": "R2", "gemination_radical": "ر",
              "gemination_evidence": {"shadda_source": "written_shadda",
                                      "mood": "indicative", "boundary": "clitic_boundary"}}
        rec = cu.analyze_derivative({"letters": list("درس"), "surface": "درس", "root_evidence": ev},
                                    self.unit)
        self.assertEqual(rec["reason"], "cross_boundary_merger_unlicensed")

    def test_unlicensed_radical_at_licensed_slot_abstains(self):
        # ب is a real radical position but the pack licenses no gemination realization for it
        ev = {"basis": "qamus_entry_ladder", "radicals": list("كبر"),
              "gemination_position": "R2", "gemination_radical": "ب",
              "gemination_evidence": {"shadda_source": "written_shadda",
                                      "mood": "indicative", "boundary": "word_internal"}}
        rec = cu.analyze_derivative({"letters": list("كبر"), "surface": "كبر", "root_evidence": ev},
                                    self.unit)
        self.assertEqual(rec["reason"], "gemination_realization_unlicensed")

    def test_undoubled_evidence_never_borrows_the_gem_slot(self):
        ev = {"basis": "qamus_entry_ladder", "radicals": list("دفس")}
        rec = cu.analyze_derivative({"letters": list("درس"), "surface": "درس", "root_evidence": ev},
                                    self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "no_template"})

    def test_pack_mutation_revokes_a_licensed_realization(self):
        fx = next(f for f in self.fixtures if f["fixture_id"] == "gem-pos-01")
        unit_m = _deep_copy(self.unit)
        unit_m["gemination_realizations"]["by_template"]["fa33ala_perfect_active"]["R2"]["ر"]["licensed"] = False
        rec = cu.analyze_derivative(fx["input"], unit_m)
        self.assertEqual(rec, {"decision": "abstain", "reason": "gemination_realization_unlicensed",
                               "unlicensed_slot": "R2", "weak_radical": "ر",
                               "template": "fa33ala_perfect_active",
                               "note": "the pack licenses no gemination realization for this exact "
                                       "slot/radical combination in this template"})

    def test_gemination_and_quadriliteral_stay_distinct_packs(self):
        gem_unit, _ = cu.load("inc-gemination-licensing")
        quad_unit, _ = cu.load("inc-quadriliteral-templates")
        gem_shapes = {t["id"]: t["shape"] for t in gem_unit["templates"]}
        quad_shapes = {t["id"]: t["shape"] for t in quad_unit["templates"]}
        self.assertTrue(any("GEM" in s for s in gem_shapes.values()))
        self.assertFalse(any("GEM" in s for s in quad_shapes.values()))
        self.assertTrue(any("R4" in s for s in quad_shapes.values()))
        self.assertFalse(any("R4" in s for s in gem_shapes.values()))


class DiminutiveTemplateFamilyTests(unittest.TestCase):
    """cu-diminutive-template-family (L6.M5.01): shape alone never certifies identity or
    meaning -- base-lexeme, affix and (for weak roots) restoration evidence are all required."""

    def setUp(self):
        self.unit, self.fixtures = cu.load("inc-diminutive-template-family")

    def _sound(self, **overrides):
        inp = {"letters": list("رجيل"), "surface": "رجيل",
               "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("رجل")},
               "base_lexeme_evidence": {"basis": "qamus_entry_ladder", "attested": True},
               "diminutive_affix_evidence": {"marker": "ي", "licensed": True}}
        inp.update(overrides)
        return inp

    def test_sound_root_diminutive_resolves(self):
        rec = cu.analyze_derivative(self._sound(), self.unit)
        self.assertEqual(rec["decision"], "candidate_pending")
        self.assertEqual(rec["template"], "fu3ayl")

    def test_shape_alone_without_base_lexeme_evidence_abstains(self):
        inp = self._sound(base_lexeme_evidence=None)
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "base_lexeme_evidence_required"})

    def test_unattested_base_lexeme_evidence_abstains(self):
        inp = self._sound(base_lexeme_evidence={"basis": "qamus_entry_ladder", "attested": False})
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec["reason"], "base_lexeme_evidence_required")

    def test_missing_affix_evidence_abstains(self):
        inp = self._sound(diminutive_affix_evidence=None)
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "diminutive_affix_evidence_required"})

    def test_unlicensed_affix_evidence_abstains(self):
        inp = self._sound(diminutive_affix_evidence={"marker": "ي", "licensed": False})
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec["reason"], "diminutive_affix_evidence_required")

    def test_weak_root_requires_restoration_evidence(self):
        inp = {"letters": list("بويب"), "surface": "بويب",
               "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("بوب")},
               "base_lexeme_evidence": {"basis": "qamus_entry_ladder", "attested": True},
               "diminutive_affix_evidence": {"marker": "ي", "licensed": True}}
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec["decision"], "abstain")
        self.assertEqual(rec["reason"], "weak_declaration_unbound")

    def test_hostile_nonword_shape_never_matches(self):
        inp = self._sound()
        inp["letters"] = list("رجيلز")
        inp["surface"] = "رجيلز"
        rec = cu.analyze_derivative(inp, self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "no_template"})

    def test_pack_mutation_removing_base_lexeme_requirement_changes_decision(self):
        fx = next(f for f in self.fixtures
                  if f["fixture_id"] == "dim-abs-01")
        unit_m = _deep_copy(self.unit)
        unit_m["require_base_lexeme_evidence"] = False
        rec_pack = cu.analyze_derivative(fx["input"], self.unit)
        rec_mut = cu.analyze_derivative(fx["input"], unit_m)
        self.assertNotEqual(rec_pack.get("decision"), rec_mut.get("decision"))


class FiveVerbInflectionClassTests(unittest.TestCase):
    """cu-five-verb-inflection-class (L2.M1.01): surface classification only -- never mood or
    governor, and occurrence use stays dependent on an authoritative Naḥw envelope."""

    def setUp(self):
        self.unit, self.fixtures = cu.load("inc-five-verb-inflection-class")

    def test_five_distinct_classes_declared(self):
        classes = {t["class"] for t in self.unit["templates"]}
        self.assertEqual(len(classes), 5)

    def test_second_masc_plural_resolves(self):
        rec = cu.analyze_derivative(
            {"letters": list("تكتبون"), "surface": "تكتبون",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("كتب")}},
            self.unit)
        self.assertEqual(rec["decision"], "candidate_pending")
        self.assertNotIn("mood", rec)
        self.assertNotIn("governor", rec)
        self.assertNotIn("case", rec)

    def test_declared_mood_input_is_never_echoed(self):
        rec = cu.analyze_derivative(
            {"letters": list("تكتبون"), "surface": "تكتبون", "declared_mood": "jussive",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("كتب")}},
            self.unit)
        self.assertNotIn("mood", rec)
        self.assertEqual(rec["decision"], "candidate_pending")

    def test_hostile_extra_letter_abstains(self):
        rec = cu.analyze_derivative(
            {"letters": list("تكتبونز"), "surface": "تكتبونز",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("كتب")}},
            self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "no_template"})


class PassiveVoiceVocalizationTests(unittest.TestCase):
    """cu-passive-voice-vocalization (L6.M3.01, L6.M5.08): a genuinely WRITTEN vocalization
    resolves the letter-identical form-I/form-II perfect collision; unvocalised sound stems keep
    abstaining exactly as unit-v1.json already did."""

    def setUp(self):
        self.unit, self.fixtures = cu.load("inc-voice-melody-templates", "unit-v2.json")

    def _row(self, surface, written_vocalization):
        return {"letters": list("كتب"), "surface": surface,
                "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("كتب")},
                "written_vocalization": written_vocalization}

    def test_form_i_perfect_active_resolves_from_written_marks(self):
        rec = cu.analyze_derivative(
            self._row("كَتَبَ", {"R1": "fatha", "R2": "fatha", "gem_R2": False}), self.unit)
        self.assertEqual(rec["decision"], "candidate_pending")
        self.assertEqual(rec["template"], "f1_perfect_active")
        self.assertEqual(rec["class"], "active")

    def test_form_i_perfect_passive_resolves_from_written_marks(self):
        rec = cu.analyze_derivative(
            self._row("كُتِبَ", {"R1": "damma", "R2": "kasra", "gem_R2": False}), self.unit)
        self.assertEqual(rec["template"], "f1_perfect_passive")
        self.assertEqual(rec["class"], "passive")

    def test_form_ii_perfect_active_resolves_from_shadda_plus_marks(self):
        rec = cu.analyze_derivative(
            self._row("كَتَّبَ", {"R1": "fatha", "R2": "fatha", "gem_R2": True}), self.unit)
        self.assertEqual(rec["template"], "f2_perfect_active")

    def test_form_ii_perfect_passive_resolves_from_shadda_plus_marks(self):
        rec = cu.analyze_derivative(
            self._row("كُتِّبَ", {"R1": "damma", "R2": "kasra", "gem_R2": True}), self.unit)
        self.assertEqual(rec["template"], "f2_perfect_passive")

    def test_unvocalised_sound_stem_still_abstains(self):
        rec = cu.analyze_derivative(
            {"letters": list("كتب"), "surface": "كتب",
             "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("كتب")}},
            self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "ambiguous_template"})

    def test_declared_marks_not_actually_written_never_resolve(self):
        # written_vocalization is asserted, but the surface itself carries no marks at all
        rec = cu.analyze_derivative(
            self._row("كتب", {"R1": "fatha", "R2": "fatha", "gem_R2": False}), self.unit)
        self.assertEqual(rec, {"decision": "abstain", "reason": "ambiguous_template"})

    def test_contradictory_written_marks_abstain_distinctly(self):
        # a sukun on R2 matches none of the four declared voice/form rows
        rec = cu.analyze_derivative(
            self._row("كَتْبَ", {"R1": "fatha", "R2": "fatha", "gem_R2": False}), self.unit)
        self.assertEqual(rec["decision"], "abstain")

    def test_pack_mutation_removing_vowel_pattern_restores_ambiguity(self):
        unit_m = _deep_copy(self.unit)
        for t in unit_m["templates"]:
            t.pop("vowel_pattern", None)
        rec = cu.analyze_derivative(
            self._row("كَتَبَ", {"R1": "fatha", "R2": "fatha", "gem_R2": False}), unit_m)
        self.assertEqual(rec, {"decision": "abstain", "reason": "ambiguous_template"})

    def test_deputy_agent_promotion_never_emitted(self):
        rec = cu.analyze_derivative(
            self._row("كُتِبَ", {"R1": "damma", "R2": "kasra", "gem_R2": False}), self.unit)
        for key in ("naib_fail", "deputy_agent", "case", "agreement"):
            self.assertNotIn(key, rec)


class DiscriminatorRegistryPacksTests(unittest.TestCase):
    """The five closed-registry units (suffix-abstract-noun, nongoverning-preverbal-inventory,
    nun-raf-vs-nun-niswa, initial-hamza-class, lexical-feminine-registry) reuse the EXISTING
    discriminator_table capability declaratively -- zero consumer code was needed for them."""

    def test_suffix_abstract_noun_distinguishes_nisba_from_abstract(self):
        unit, _ = cu.load("inc-suffix-abstract-noun")
        nisba = cu.analyze_discriminator_table(
            {"features": {"shadda_on_yaa_evidence": "written_shadda",
                          "final_letter": "none_word_final_yaa"}}, unit)
        abstract = cu.analyze_discriminator_table(
            {"features": {"shadda_on_yaa_evidence": "written_shadda",
                          "final_letter": "taa_marbuta"}}, unit)
        self.assertEqual(nisba["function"], "nisba_relational_yaa")
        self.assertEqual(abstract["function"], "abstract_noun_yaa")

    def test_suffix_abstract_noun_unmarked_shadda_abstains(self):
        unit, _ = cu.load("inc-suffix-abstract-noun")
        rec = cu.analyze_discriminator_table(
            {"features": {"shadda_on_yaa_evidence": "unmarked", "final_letter": "taa_marbuta"}},
            unit)
        self.assertEqual(rec["decision"], "abstain")

    def test_nongoverning_preverbal_inventory_never_emits_governor_effects(self):
        unit, _ = cu.load("inc-nongoverning-preverbal-inventory")
        rec = cu.analyze_discriminator_table(
            {"features": {"particle": "قد", "verb_tense": "perfect"}}, unit)
        self.assertEqual(rec["decision"], "candidate_pending")
        for key in ("mood", "governor", "case"):
            self.assertNotIn(key, rec)

    def test_nongoverning_preverbal_inventory_rejects_a_governing_particle(self):
        unit, _ = cu.load("inc-nongoverning-preverbal-inventory")
        rec = cu.analyze_discriminator_table({"features": {"particle": "لن", "verb_tense": "imperfect"}},
                                             unit)
        self.assertEqual(rec["decision"], "abstain")

    def test_nun_raf_vs_nun_niswa_distinguishes_the_two_nuns(self):
        unit, _ = cu.load("inc-nun-raf-vs-nun-niswa")
        rafa = cu.analyze_discriminator_table(
            {"features": {"preceding_letter_class": "long_vowel_glide",
                          "pos": "verb_imperfect_five_verb_form"}}, unit)
        niswa = cu.analyze_discriminator_table(
            {"features": {"preceding_letter_class": "consonant_stem_final",
                          "pos": "verb_imperfect_feminine_plural"}}, unit)
        self.assertEqual(rafa["function"], "nun_al_rafa")
        self.assertEqual(niswa["function"], "nun_al_niswa")

    def test_nun_raf_vs_nun_niswa_unknown_preceding_letter_abstains(self):
        unit, _ = cu.load("inc-nun-raf-vs-nun-niswa")
        rec = cu.analyze_discriminator_table(
            {"features": {"preceding_letter_class": "unknown", "pos": "verb_imperfect_five_verb_form"}},
            unit)
        self.assertEqual(rec["decision"], "abstain")

    def test_initial_hamza_class_requires_exact_written_vocalization(self):
        unit, _ = cu.load("inc-initial-hamza-class")
        qat = cu.analyze_discriminator_table(
            {"features": {"initial_seat": "hamza_qat_alif", "vocalization_evidence": "written_mark"}},
            unit)
        wasl = cu.analyze_discriminator_table(
            {"features": {"initial_seat": "hamza_wasl_seated", "vocalization_evidence": "written_mark"}},
            unit)
        unmarked = cu.analyze_discriminator_table(
            {"features": {"initial_seat": "hamza_qat_alif", "vocalization_evidence": "unmarked"}},
            unit)
        self.assertEqual(qat["function"], "hamzat_qat")
        self.assertEqual(wasl["function"], "hamzat_wasl")
        self.assertEqual(unmarked["decision"], "abstain")

    def test_lexical_feminine_registry_is_closed_and_never_infers_from_shape(self):
        unit, _ = cu.load("inc-lexical-feminine-registry")
        registered = cu.analyze_discriminator_table({"features": {"lexeme_surface": "أرض"}}, unit)
        self.assertEqual(registered["function"], "lexically_feminine_noun")
        # قمر is masculine and NOT in the closed registry -- shape gives no vote here
        unregistered = cu.analyze_discriminator_table({"features": {"lexeme_surface": "قمر"}}, unit)
        self.assertEqual(unregistered["decision"], "abstain")
        # a regular taa-marbuta feminine is a DIFFERENT (morphological) mechanism, out of this
        # closed lexical registry's scope -- it must abstain here too, never be inferred from shape
        shape_only = cu.analyze_discriminator_table({"features": {"lexeme_surface": "مدرسة"}}, unit)
        self.assertEqual(shape_only["decision"], "abstain")

    def test_registry_pack_mutation_revokes_a_registered_lexeme(self):
        unit, _ = cu.load("inc-lexical-feminine-registry")
        unit_m = _deep_copy(unit)
        for fn in unit_m["functions"]:
            if fn["id"] == "lexically_feminine_noun":
                fn["discriminators"]["lexeme_surface"] = [
                    w for w in fn["discriminators"]["lexeme_surface"] if w != "أرض"]
        rec = cu.analyze_discriminator_table({"features": {"lexeme_surface": "أرض"}}, unit_m)
        self.assertEqual(rec["decision"], "abstain")


class EvalBankStructuralTests(unittest.TestCase):
    def test_template_classification_train_1_bank_registered_in_contract(self):
        contract = json.loads((ROOT / "sarf" / "eval-runner-contract.json").read_text(encoding="utf-8"))
        bank = next((b for b in contract["banks"]
                    if b["path"] == "sarf/evals/template-classification-train-1-eval.jsonl"), None)
        self.assertIsNotNone(bank, "the new bank must be registered in the contract")
        self.assertEqual(bank["disposition"], "implemented_and_consumed")
        self.assertEqual(bank["behavioral_consumer"], "tools/curriculum_unit_consumer.py:analyze_derivative")

    def test_bank_file_is_valid_jsonl_and_covers_all_ten_units(self):
        path = ROOT / "sarf" / "evals" / "template-classification-train-1-eval.jsonl"
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        increments = {r["increment"] for r in rows}
        self.assertTrue(ALL_NEW_INCREMENTS_SET <= increments | {"inc-voice-melody-templates"})


ALL_NEW_INCREMENTS_SET = set(ALL_NEW_INCREMENTS)

_TC1_BANK = "sarf/evals/template-classification-train-1-eval.jsonl"


def _rse_ctx():
    import tools.run_sarf_evals as rse
    return rse.Consumers.real()


def _rse_spec():
    import tools.run_sarf_evals as rse
    return rse.bank_spec(rse.load_contract(str(ROOT)), _TC1_BANK)


def _rse_rows():
    import tools.run_sarf_evals as rse
    return rse.load_bank(str(ROOT), _rse_spec())


def _rse_run(ctx=None):
    import tools.run_sarf_evals as rse
    return rse.run_adapter(_rse_spec(), _rse_rows(), ctx or _rse_ctx(), str(ROOT))


class EvalBankBehavioralAdapterTests(unittest.TestCase):
    """The template-classification-train-1-eval.jsonl bank is genuinely decided by the real
    tools/curriculum_unit_consumer.py:analyze_derivative / :analyze_discriminator_table -- never a
    structural echo of the bank's own expected_decision field."""

    def test_all_twenty_rows_are_decided_by_the_real_consumers_and_go_green(self):
        failures, metrics = _rse_run()
        self.assertEqual(failures, [], "template-classification-train-1 bank failed: %s" % failures[:5])
        self.assertEqual(metrics["decided_rows"], 20)
        self.assertEqual(metrics["consumer_calls"]["tools/curriculum_unit_consumer.py:analyze_derivative"], 10)
        self.assertEqual(metrics["consumer_calls"]["tools/curriculum_unit_consumer.py:analyze_discriminator_table"],
                         10)

    def test_a_stubbed_injected_consumer_turns_the_bank_red(self):
        """MUTATION (a): rebind the INJECTED ctx slot to a constant-return stub -- the bank must go RED."""
        ctx = _rse_ctx()
        ctx.derivative_decide = lambda inp, unit: {"decision": "candidate_pending",
                                                   "authority": "none_fixture_harness",
                                                   "class": "diminutive_noun", "template": "fu3ayl"}
        failures, _m = _rse_run(ctx)
        self.assertTrue(failures, "a stubbed analyze_derivative must fail the bank")

    def test_a_stubbed_injected_discriminator_consumer_turns_the_bank_red(self):
        ctx = _rse_ctx()
        ctx.discriminator_decide = lambda inp, unit: {"decision": "candidate_pending",
                                                       "function": "nisba_relational_yaa"}
        failures, _m = _rse_run(ctx)
        self.assertTrue(failures, "a stubbed analyze_discriminator_table must fail the bank")

    def test_external_derivative_module_is_genuinely_invoked(self):
        """MUTATION (b): rebind the EXTERNAL tools.curriculum_unit_consumer MODULE ATTRIBUTE run_sarf_evals.py
        itself imports (`import tools.curriculum_unit_consumer` -- a DISTINCT sys.modules entry from this
        file's own bare `import curriculum_unit_consumer as cu`) -- proves run_sarf_evals.py genuinely calls
        the external module, never a local echo of the bank's own expected_decision."""
        import tools.curriculum_unit_consumer as tcu
        import tools.run_sarf_evals as rse
        original = tcu.analyze_derivative
        tcu.analyze_derivative = lambda inp, unit: {"decision": "candidate_pending",
                                                    "authority": "none_fixture_harness",
                                                    "class": "diminutive_noun", "template": "fu3ayl"}
        try:
            failures, _m = _rse_run(rse.Consumers.real())
        finally:
            tcu.analyze_derivative = original
        self.assertTrue(failures, "a stubbed EXTERNAL analyze_derivative must fail the bank")

    def test_external_discriminator_module_is_genuinely_invoked(self):
        import tools.curriculum_unit_consumer as tcu
        import tools.run_sarf_evals as rse
        original = tcu.analyze_discriminator_table
        tcu.analyze_discriminator_table = lambda inp, unit: {"decision": "candidate_pending",
                                                             "function": "nisba_relational_yaa"}
        try:
            failures, _m = _rse_run(rse.Consumers.real())
        finally:
            tcu.analyze_discriminator_table = original
        self.assertTrue(failures, "a stubbed EXTERNAL analyze_discriminator_table must fail the bank")

    def test_an_eval_fixtures_own_expected_answer_cannot_certify_a_fact_by_itself(self):
        """A row's expected_decision must be independently REPRODUCED by the real consumer -- flipping the
        bank's own expected_decision (never touching the consumer) must also fail, proving the assertion is a
        genuine comparison and not a tautology."""
        rows = copy.deepcopy(_rse_rows())
        row = next(r for r in rows if r["id"] == "tc1-dim-01")
        row["expected_decision"] = "abstain"
        import tools.run_sarf_evals as rse
        failures, _m = rse.run_adapter(_rse_spec(), rows, _rse_ctx(), str(ROOT))
        self.assertTrue(any(f.startswith("tc1-dim-01 ") for f in failures), failures[:5])

    def test_pack_mutation_removing_a_bound_template_flips_the_bound_row(self):
        """The bound fixture's decision genuinely depends on the PACK content: dropping fu3ayl from
        inc-diminutive-template-family's in-memory pack must flip tc1-dim-01 away from candidate_pending."""
        import tools.run_sarf_evals as rse
        original = rse._tc1_pack

        def _dropped(increment, root=str(ROOT)):
            unit, fixtures = original(increment, root)
            if increment == "inc-diminutive-template-family":
                unit = _deep_copy(unit)
                unit["templates"] = [t for t in unit["templates"] if t["id"] != "fu3ayl"]
            return unit, fixtures
        rse._tc1_pack = _dropped
        try:
            failures, _m = _rse_run()
        finally:
            rse._tc1_pack = original
        self.assertTrue(any(f.startswith("tc1-dim-01 ") for f in failures), failures[:5])


if __name__ == "__main__":
    unittest.main()
