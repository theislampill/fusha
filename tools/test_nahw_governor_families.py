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


if __name__ == "__main__":
    unittest.main()
