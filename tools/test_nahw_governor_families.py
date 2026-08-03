#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first test module for TRAIN-B-NAHW-GOVERNOR-REASON-PLANE (G1-G7).

One plane, six families over the committed governor/iʿrāb lattice: nawasikh regime discrimination,
coordination case-following, hidden structure/maḥall, negation multifunction (لا), a non-governing
inventory, and rivals/attribution — plus the reason-key licensing tuple that ties a stated governor
to the case it may license. Candidate/pending/abstention repairs only: nothing here certifies.
"""
import copy
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from tools.validate_linguistic_decisions import validate_schema  # noqa: E402

SCHEMA_PATH = os.path.join(REPO, "qamus", "schemas", "dependency-candidate-lattice.schema.json")
with open(SCHEMA_PATH, encoding="utf-8") as _fh:
    _SCHEMA = json.load(_fh)
_EDGE_SCHEMA = _SCHEMA["$defs"]["edge"]


def _base_edge(**overrides):
    edge = {
        "edge_id": "e1", "dependent": "tok:1", "candidate_head": None, "headless": True,
        "governor_type": "none", "rel_label": "coordination", "rel_label_ar": "x",
        "assigned_case_mood": None, "governor_justification": "j", "justification_rule": "coordination_no_governor",
        "justification_confidence": "medium", "evidence_class": "heuristic", "unresolved_alternatives": [],
        "contradiction_marker": False, "right_answer_wrong_reason_marker": False, "decision_status": "resolved",
        "gate": "two_vote_required", "route_to": {"lane": "nahw", "procedure": "x.md"},
    }
    edge.update(overrides)
    return edge


class G1SchemaSurface(unittest.TestCase):
    """G1: additive-only schema surface for the plane; no behaviour change."""

    def test_new_rel_label_values_accepted(self):
        for value in ("ism_nasikh", "khabar_nasikh", "matuf", "matuf_alayh", "atf_bayan", "zarf_idafa_head"):
            edge = _base_edge(rel_label=value)
            self.assertEqual(validate_schema(edge, _EDGE_SCHEMA), [], value)

    def test_new_trigger_family_values_accepted(self):
        for value in ("zanna_family", "la_nafiya", "la_nahiya", "la_jins_candidate", "conditional",
                      "atf_candidate", "nongoverning_preverbal", "regime_undetermined"):
            edge = _base_edge(trigger_family=value)
            self.assertEqual(validate_schema(edge, _EDGE_SCHEMA), [], value)

    def test_new_justification_rule_values_accepted(self):
        for value in ("nasikh_governs_ism_nasb", "nasikh_governs_khabar_raf3", "kana_governs_ism_raf3",
                      "kana_governs_khabar_nasb", "la_jins_governs_ism_mabni_fath", "zarf_idafa_governs_genitive",
                      "coordination_follows_matuf_alayh_case", "hidden_element_licensed", "mahall_positional_case",
                      "non_governing_use_abstention", "regime_undetermined_abstention"):
            edge = _base_edge(justification_rule=value)
            self.assertEqual(validate_schema(edge, _EDGE_SCHEMA), [], value)

    def test_new_optional_edge_properties_accepted(self):
        edge = _base_edge(
            governing_regime="inna_family", regime_evidence="visible fatḥa on the ism",
            hidden_element={"type": "mustatir_pronoun", "licensing_construction": "imperative_verb", "obligatory": True},
            analysis_attribution={"status": "both_licensed", "alternatives": ["badal", "atf_bayan"], "party_source_ref": None},
            head_case="nominative", head_governor_type="mubtada_khabar", frame_kind="address_bearing",
        )
        self.assertEqual(validate_schema(edge, _EDGE_SCHEMA), [])

    def test_forged_enum_value_still_rejected(self):
        edge = _base_edge(trigger_family="not_a_real_family")
        self.assertTrue(validate_schema(edge, _EDGE_SCHEMA))

    def test_forged_undeclared_property_still_rejected(self):
        edge = _base_edge()
        edge["not_a_real_property"] = True
        self.assertTrue(validate_schema(edge, _EDGE_SCHEMA))

    def test_forged_out_of_enum_governing_regime_rejected(self):
        edge = _base_edge(governing_regime="made_up_regime")
        self.assertTrue(validate_schema(edge, _EDGE_SCHEMA))

    def test_analysis_attribution_rejects_additional_property(self):
        edge = _base_edge(analysis_attribution={"status": "both_licensed", "alternatives": ["a", "b"], "selected": "a"})
        self.assertTrue(validate_schema(edge, _EDGE_SCHEMA))

    def test_required_keys_unchanged_no_addition(self):
        self.assertEqual(
            set(_EDGE_SCHEMA["required"]),
            {"edge_id", "dependent", "headless", "governor_type", "rel_label", "rel_label_ar",
             "assigned_case_mood", "governor_justification", "justification_rule", "justification_confidence",
             "evidence_class", "unresolved_alternatives", "contradiction_marker",
             "right_answer_wrong_reason_marker", "decision_status", "gate", "route_to"},
        )


class G2ValidatorConditions(unittest.TestCase):
    """G2: validator conditions 10-14 + occurrence-identity verification + attribution rules.

    F11 (quran:2:80:10-11, the flagship right-answer/wrong-reason zarf frame) is asserted against the FULLY
    assembled validator (FAIL 10 or G6's ʿāmil-kind condition, FAIL 18) in G6TrainAssembled below — at G2 time
    neither governing_regime population (G4) nor FAIL 18 (G6) exist yet, so that specific cross-group red only
    becomes meaningful once G6 has landed. This ordering is a deliberate, documented sequencing call.
    """

    def test_bad_lattices_10_through_13_fire(self):
        from tools import validate_dependency_lattice as V
        for cond, lat in V._bad_lattices():
            conds = {c for c, _ in V.validate_lattice(lat)}
            self.assertIn(cond, conds, (cond, sorted(conds)))

    def test_fail10_family_less_abrogator_edge_rejected(self):
        from tools.validate_dependency_lattice import validate_lattice
        edge = _base_edge(trigger_family="kana_family", governing_regime=None)
        lat = {
            "schema": "fusha/dependency-candidate-lattice@1", "input_mode": "arbitrary_typing",
            "source_unit": {"address": "", "scope": "arbitrary"},
            "tokens": [{"ref": "tok:1", "surface": "x"}], "edges": [edge],
            "summary": {"live_writes": 0, "n_edges": 1, "n_unresolved": 0, "by_decision": {}},
            "public_boundary": {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                                "public_gloss_lang": "en", "external_source_names_public": False},
            "source_boundary": {"heuristic_never_overrides_source": True, "quran_text_altered": False},
        }
        conds = {c for c, _ in validate_lattice(lat)}
        self.assertIn("10", conds)

    def test_fail11_attribution_rules(self):
        from tools.validate_dependency_lattice import validate_lattice
        for bad in (
            {"status": "both_licensed", "alternatives": ["only_one"]},
            {"status": "both_licensed", "alternatives": ["a", "b"], "selected": "a"},
            {"status": "school_dependent", "alternatives": ["a", "b"], "party_source_ref": None},
        ):
            edge = _base_edge(analysis_attribution=bad, decision_status="unresolved", unresolved_alternatives=[{"reading": "a"}])
            lat = {
                "schema": "fusha/dependency-candidate-lattice@1", "input_mode": "arbitrary_typing",
                "source_unit": {"address": "", "scope": "arbitrary"},
                "tokens": [{"ref": "tok:1", "surface": "x"}], "edges": [edge],
                "summary": {"live_writes": 0, "n_edges": 1, "n_unresolved": 1, "by_decision": {}},
                "public_boundary": {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                                    "public_gloss_lang": "en", "external_source_names_public": False},
                "source_boundary": {"heuristic_never_overrides_source": True, "quran_text_altered": False},
            }
            conds = {c for c, _ in validate_lattice(lat)}
            self.assertTrue(conds, bad)

    def test_fail14_n3_surface_present_but_address_refused(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        lat = {
            "input_mode": "source_addressed", "source_unit": {"address": "quran:2:110", "scope": "in_scope_source_addressed"},
            "tokens": [{"ref": "2:110:11", "surface": "عِندَ"}, {"ref": "2:110:12", "surface": "ٱللَّهِ"}],
        }
        errs = verify_occurrence_identity(lat)
        self.assertTrue(errs, "N3: word-level address refusal must still be a FAIL 14")
        self.assertFalse(any("surface does not match" in msg for _, msg in errs),
                          "N3: the surface itself DOES match the loc-surface index; only the resolver refuses")
        self.assertTrue(any(c == "14" for c, _ in errs))

    def test_fail14_n1_ayah_absent_from_spine(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        lat = {
            "input_mode": "source_addressed", "source_unit": {"address": "quran:3:198", "scope": "in_scope_source_addressed"},
            "tokens": [{"ref": "3:198:1", "surface": "لَٰكِنِ"}, {"ref": "3:198:2", "surface": "ٱلَّذِينَ"}],
        }
        errs = verify_occurrence_identity(lat)
        self.assertTrue(errs, "N1: refusal control — the address authority refuses the ayah")

    def test_fail14_n2_ayah_absent_from_spine(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        lat = {
            "input_mode": "source_addressed", "source_unit": {"address": "quran:2:12", "scope": "in_scope_source_addressed"},
            "tokens": [{"ref": "2:12:5", "surface": "وَلَٰكِن"}, {"ref": "2:12:6", "surface": "لَّا"}],
        }
        errs = verify_occurrence_identity(lat)
        self.assertTrue(errs, "N2: refusal control — the address authority refuses the ayah")

    def test_fail14_corrupted_surface_rejected(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        lat = {
            "input_mode": "source_addressed", "source_unit": {"address": "quran:2:7", "scope": "in_scope_source_addressed"},
            "tokens": [{"ref": "2:7:3", "surface": "عَلَىٰ"}, {"ref": "2:7:4", "surface": "قُلُوبِهِمْXX"}],
        }
        errs = verify_occurrence_identity(lat)
        self.assertTrue(any("surface does not match" in msg for _, msg in errs))

    def test_fail14_clean_address_bearing_lattice_passes(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        lat = {
            "input_mode": "source_addressed", "source_unit": {"address": "quran:2:7", "scope": "in_scope_source_addressed"},
            "tokens": [{"ref": "2:7:3", "surface": "عَلَىٰ"}, {"ref": "2:7:4", "surface": "قُلُوبِهِمْ"}],
        }
        self.assertEqual(verify_occurrence_identity(lat), [])


if __name__ == "__main__":
    unittest.main()
