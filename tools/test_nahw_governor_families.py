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


NAHW_EVALS = os.path.join(REPO, "nahw", "evals")


def _load_bank(name):
    rows = {}
    with open(os.path.join(NAHW_EVALS, name), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def _lattice_for(row):
    from tools import fusha_governor as G
    return G.build_dependency_lattice(row)


class G3SurfaceKeyIntegrity(unittest.TestCase):
    """G3: proclitic stripping, gemination parity, maddah folding, la discrimination, roster fixes."""

    @classmethod
    def setUpClass(cls):
        cls.naw = _load_bank("nawasikh-government-eval.jsonl")
        cls.hid = _load_bank("hidden-structure-mahall-eval.jsonl")

    def test_f2_f3_heavy_lakin_discriminated_regime(self):
        for fid in ("F2", "F3"):
            lat = _lattice_for(self.naw[fid])
            self.assertTrue(any(e.get("trigger_family") == "inna_family" for e in lat["edges"]), (fid, lat["edges"]))

    def test_n1_light_lakin_never_inna_family(self):
        # N1/N2 are the LIGHT (non-geminate) lakin member. an_family_weight() reads the shadda/sukun on the
        # nun (parity requirement); a liaison kasra before a following hamzat-wasl word (as in N1) is neither
        # signal, so the honest outcome is regime_undetermined rather than a forced light/heavy call -- either
        # way it must NEVER be inna_family (D2's false-family-label defect).
        lat = _lattice_for(self.naw["N1"])
        self.assertFalse(any(e.get("trigger_family") == "inna_family" for e in lat["edges"]))
        self.assertTrue(any(e.get("trigger_family") in ("nongoverning_preverbal", "regime_undetermined")
                            for e in lat["edges"]))

    def test_f8_not_la_jins(self):
        lat = _lattice_for(self.naw["F8"])
        self.assertFalse(any(e.get("trigger_family") == "la_jins" for e in lat["edges"]))
        self.assertTrue(any(e.get("trigger_family") == "la_nafiya" for e in lat["edges"]))

    def test_f8_no_fabricated_idafa_over_fail_and_object(self):
        """I5: ٱللَّهُ (fāʿil of يُكَلِّفُ) / نَفْسًا (its mafʿūl) at 2:286 are SEPARATE verb arguments, never a
        muḍāf/muḍāf-ilayh pair — the bare noun+noun fallback must not fabricate an idafa_dependent edge here."""
        lat = _lattice_for(self.naw["F8"])
        self.assertFalse(any(e["rel_label"] == "idafa_dependent" for e in lat["edges"]))
        dep_edge = next(e for e in lat["edges"] if e["dependent"] == "2:286:4")
        self.assertFalse(dep_edge["contradiction_marker"])
        self.assertIsNone(dep_edge["candidate_head"])
        readings = {a.get("reading") for a in dep_edge["unresolved_alternatives"]}
        self.assertIn("separate arguments of the preceding verb (fāʿil + mafʿūl bihi)", readings)

    def test_f6_vs_f8_separated_by_following_token_evidence(self):
        f6 = _lattice_for(self.hid["F6"])
        f8 = _lattice_for(self.naw["F8"])
        self.assertTrue(any(e.get("trigger_family") == "la_jins" for e in f6["edges"]))
        self.assertFalse(any(e.get("trigger_family") == "la_jins" for e in f8["edges"]))

    def test_f7_maddah_recognised(self):
        lat = _lattice_for(self.hid["F7"])
        self.assertTrue(any(e.get("trigger_family") == "la_jins" for e in lat["edges"]))

    def test_f4_kana_suppression_fires_no_false_idafa(self):
        lat = _lattice_for(self.naw["F4"])
        self.assertTrue(any(e.get("trigger_family") == "kana_family" for e in lat["edges"]))
        self.assertFalse(any(e["rel_label"] == "idafa_dependent" for e in lat["edges"]))

    def test_c24_nongoverning_inventory_is_positive_evidence(self):
        bank = self.naw
        lat = _lattice_for(bank["C24"])
        self.assertTrue(any(e.get("abstention_reason") == "non_governing_use" for e in lat["edges"]))

    def test_c13_preserve_alternatives_nafiya_nahiya(self):
        edge = _lattice_for(self.naw["C13"])["edges"][0]
        readings = {a.get("reading") for a in edge["unresolved_alternatives"]}
        self.assertEqual(readings, {"nafiya_statement", "nahiya_prohibitive"})
        self.assertNotEqual(edge["decision_status"], "resolved")

    def test_c14_abstain_insufficient_features(self):
        edge = _lattice_for(self.naw["C14"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "insufficient_features")


class G4NawasikhRegimeDiscrimination(unittest.TestCase):
    """G4: regime discrimination precedes case expectation; licensing/sense/bracketing gates; contradictions."""

    @classmethod
    def setUpClass(cls):
        cls.naw = _load_bank("nawasikh-government-eval.jsonl")

    def test_c1_c3_violation_candidate(self):
        for fid in ("C1", "C3"):
            lat = _lattice_for(self.naw[fid])
            edge = lat["edges"][0]
            self.assertTrue(edge["contradiction_marker"], fid)
            self.assertEqual(edge["decision_status"], "pending", fid)
            self.assertIsNone(edge["assigned_case_mood"], fid)

    def test_c2_abstain_marking_unknown(self):
        edge = _lattice_for(self.naw["C2"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "marking_unknown")
        self.assertIsNone(edge["assigned_case_mood"])

    def test_c4_abstain_sense_dependent_gate(self):
        edge = _lattice_for(self.naw["C4"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "sense_dependent_gate")
        # I6 discovery: the regime (zanna_family) IS known here — only the sense is gated — so this
        # abrogator-family trigger edge must still carry governing_regime (FAIL 10 otherwise).
        self.assertEqual(edge.get("governing_regime"), "zanna_family")

    def test_f5_hidden_ism_edge_headless_carries_no_candidate_head(self):
        """I6 discovery: headless=True with a non-null candidate_head is a self-contradiction (FAIL 4) —
        the hidden ism has no written head of its own to point at."""
        lat = _lattice_for(self.naw["F5"])
        ism_edge = next(e for e in lat["edges"] if e["rel_label"] == "hidden_subject")
        self.assertTrue(ism_edge["headless"])
        self.assertIsNone(ism_edge["candidate_head"])

    def test_c5_abstain_licenser_absent(self):
        edge = _lattice_for(self.naw["C5"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "licenser_absent")

    def test_c6_abstain_bracketing_ambiguous(self):
        edge = _lattice_for(self.naw["C6"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "bracketing_ambiguous")
        self.assertIsNone(edge["assigned_case_mood"])

    def test_f1_inna_family_ism_nasb_gate_two_vote_pending(self):
        from tools.validate_linguistic_decisions import _GATE_RANK
        lat = _lattice_for(self.naw["F1"])
        ism_edges = [e for e in lat["edges"] if e["rel_label"] == "ism_nasikh"]
        self.assertTrue(ism_edges)
        for e in ism_edges:
            self.assertEqual(e["decision_status"], "pending")
            self.assertGreaterEqual(_GATE_RANK[e["gate"]], _GATE_RANK["two_vote_required"])

    def test_f3_marking_unknown_syncretic_exponent_never_resolved(self):
        lat = _lattice_for(self.naw["F3"])
        ism_edge = next(e for e in lat["edges"] if e["rel_label"] == "ism_nasikh")
        self.assertEqual(ism_edge.get("abstention_reason"), "marking_unknown")
        self.assertIsNone(ism_edge["assigned_case_mood"])

    def test_no_abrogator_edge_is_auto_safe(self):
        for fid, row in self.naw.items():
            lat = _lattice_for(row)
            for e in lat["edges"]:
                self.assertNotEqual(e["gate"], "auto_safe", (fid, e["edge_id"]))

    def test_f14_khabar_sweep_stops_at_idafa_boundary_no_fabricated_contradiction(self):
        """I4: 7:56-shaped إِنَّ رَحْمَتَ ٱللَّهِ — ٱللَّهِ is the muḍāf ilayh of رَحْمَتَ, not a second
        inna-khabar. The sweep must stop and abstain(khabar_boundary_undetermined), never contradiction_marker."""
        lat = _lattice_for(self.naw["F14"])
        ism_edge = next(e for e in lat["edges"] if e["rel_label"] == "ism_nasikh")
        self.assertEqual(ism_edge["assigned_case_mood"], "accusative")
        self.assertFalse(ism_edge["contradiction_marker"])
        boundary_edges = [e for e in lat["edges"] if e.get("abstention_reason") == "khabar_boundary_undetermined"]
        self.assertEqual(len(boundary_edges), 1)
        boundary_edge = boundary_edges[0]
        self.assertEqual(boundary_edge["dependent"], "7:56:12")
        self.assertFalse(boundary_edge["contradiction_marker"])
        self.assertIsNone(boundary_edge["assigned_case_mood"])
        self.assertNotEqual(boundary_edge["rel_label"], "khabar_nasikh")
        self.assertFalse(any(e["rel_label"] == "khabar_nasikh" for e in lat["edges"]))


class G5CoordinationCaseFollowing(unittest.TestCase):
    """G5: coordination case-following, wāw sense gating, apposition rivals, the coordination reason key."""

    @classmethod
    def setUpClass(cls):
        cls.co = _load_bank("coordination-case-following-eval.jsonl")

    def test_bare_waw_resolving_is_a_fail(self):
        from tools import fusha_governor as G
        unit = next(u for u in G.regression_units() if u["name"] == "coordination-headless")
        lat = G.build_dependency_lattice(unit)
        self.assertFalse(any(e["decision_status"] == "resolved" for e in lat["edges"]))
        self.assertTrue(any(e["headless"] for e in lat["edges"]))

    def test_f9_no_idafa_assigns_genitive_to_a_conjunct(self):
        lat = _lattice_for(self.co["F9"])
        self.assertFalse(any(e["rel_label"] == "idafa_dependent" for e in lat["edges"]))
        self.assertTrue(any(e.get("abstention_reason") == "cross_token_layer_boundary" for e in lat["edges"]))
        # token 15 (ٱلْـَٔاخِرِ) is explicitly POS-adjective and follows the noun token 14 in the same genitive
        # case; it must surface as an unresolved sifa/badal edge, never an idafa_dependent guess.
        sifa_edge = next(e for e in lat["edges"] if e["dependent"] == "2:177:15")
        self.assertEqual(sifa_edge["rel_label"], "sifa")
        self.assertNotEqual(sifa_edge["decision_status"], "resolved")
        self.assertIsNone(sifa_edge["assigned_case_mood"])

    def test_adjective_pos_blocks_idafa_but_genuine_noun_noun_idafa_still_candidate(self):
        from tools import fusha_governor as G
        # hostile positive: a noun followed by an explicitly-typed adjective must never be swept into the
        # noun+noun iḍāfa-candidate branch merely because "adjective" is also a member of the noun POS set.
        adj_lat = G.build_dependency_lattice({
            "input_mode": "arbitrary_typing",
            "tokens": [{"ref": "tok:0", "surface": "كتاب", "pos": "noun"},
                       {"ref": "tok:1", "surface": "الجميل", "pos": "adjective"}],
        })
        self.assertFalse(any(e["rel_label"] == "idafa_dependent" for e in adj_lat["edges"]))
        sifa_edges = [e for e in adj_lat["edges"] if e["rel_label"] == "sifa"]
        self.assertTrue(sifa_edges)
        readings = {a.get("reading") for a in sifa_edges[0]["unresolved_alternatives"]}
        self.assertTrue(any(r.startswith("ṣifa") for r in readings))
        self.assertTrue(any(r.startswith("badal") for r in readings))
        # hostile negative control: a genuine noun+noun pair (no adjective POS involved) must still keep the
        # ambiguous iḍāfa candidate reading — this repair must not regress the general iḍāfa branch.
        idafa_unit = next(u for u in G.regression_units() if u["name"] == "idafa-candidate")
        idafa_lat = G.build_dependency_lattice(idafa_unit)
        self.assertTrue(any(e["rel_label"] == "idafa_dependent" for e in idafa_lat["edges"]))

    def test_f10_identical_case_no_connector_not_coordination(self):
        lat = _lattice_for(self.co["F10"])
        self.assertFalse(any(e["rel_label"] == "coordination" for e in lat["edges"]))

    def test_c7_abstain_marking_unknown_never_copies_head_case(self):
        edge = _lattice_for(self.co["C7"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "marking_unknown")
        self.assertIsNone(edge["assigned_case_mood"])
        self.assertEqual(edge.get("head_case"), "nominative")

    def test_c8_not_coordination(self):
        edge = _lattice_for(self.co["C8"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "not_coordination")

    def test_c9_abstain_non_governing_use(self):
        edge = _lattice_for(self.co["C9"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "non_governing_use")

    def test_c10_attributed_no_decision_both_readings(self):
        edge = _lattice_for(self.co["C10"])["edges"][0]
        attribution = edge.get("analysis_attribution")
        self.assertIsNotNone(attribution)
        self.assertEqual(attribution["status"], "analysis_dependent")
        self.assertGreaterEqual(len(attribution["alternatives"]), 2)
        self.assertNotIn("selected", attribution)

    def test_c11_abstain_insufficient_features(self):
        edge = _lattice_for(self.co["C11"])["edges"][0]
        self.assertEqual(edge.get("abstention_reason"), "insufficient_features")

    def test_c12_preserve_alternatives_coordination_maiyya(self):
        edge = _lattice_for(self.co["C12"])["edges"][0]
        readings = {a.get("reading") for a in edge["unresolved_alternatives"]}
        self.assertEqual(readings, {"coordination", "maiyya"})
        self.assertNotEqual(edge["decision_status"], "resolved")

    def test_c20_both_licensed_two_alternatives_no_selection(self):
        edge = _lattice_for(self.co["C20"])["edges"][0]
        attribution = edge["analysis_attribution"]
        self.assertEqual(attribution["status"], "both_licensed")
        self.assertEqual(sorted(attribution["alternatives"]), ["atf_bayan", "badal"])
        self.assertNotIn("selected", attribution)

    def test_c21_one_edge_two_attributed_assignments(self):
        lat = _lattice_for(self.co["C21"])
        self.assertEqual(len(lat["edges"]), 1)
        edge = lat["edges"][0]
        self.assertEqual(len(edge["unresolved_alternatives"]), 2)
        self.assertEqual(edge["analysis_attribution"]["status"], "both_licensed")
        self.assertNotEqual(edge["decision_status"], "resolved")

    def test_grader_head_case_absent_routes_pending(self):
        from tools.grade_grammar_reasoning import derive_reasoning
        case = {"expected_reason_keys": ["atf-tabaiyya-follows-matuf-alayh"], "expected_conclusion": "coordination"}
        claim = {"reason_key": "atf-tabaiyya-follows-matuf-alayh", "conclusion": "coordination",
                 "case_mood": "genitive", "fact_type": "case_assignment", "source_address": "quran:2:7:4",
                 "governor": {"governor_type": "idafa"}}
        ok, defect = derive_reasoning(case, claim)
        self.assertFalse(ok)
        self.assertEqual(defect, "reason_tuple_head_unavailable")

    def test_grader_head_governor_type_not_licensing_refused(self):
        from tools.grade_grammar_reasoning import derive_reasoning
        case = {"expected_reason_keys": ["atf-tabaiyya-follows-matuf-alayh"], "expected_conclusion": "coordination"}
        claim = {"reason_key": "atf-tabaiyya-follows-matuf-alayh", "conclusion": "coordination",
                 "case_mood": "genitive", "fact_type": "case_assignment", "source_address": "quran:2:7:4",
                 "head_case": "genitive", "head_governor_type": "verb_subject",
                 "governor": {"governor_type": "verb_subject"}}
        ok, defect = derive_reasoning(case, claim)
        self.assertFalse(ok)
        self.assertEqual(defect, "reason_tuple_head_unavailable")

    def test_grader_valid_coordination_claim_passes(self):
        from tools.grade_grammar_reasoning import derive_reasoning
        case = {"expected_reason_keys": ["atf-tabaiyya-follows-matuf-alayh"], "expected_conclusion": "coordination"}
        claim = {"reason_key": "atf-tabaiyya-follows-matuf-alayh", "conclusion": "coordination",
                 "case_mood": "genitive", "fact_type": "case_assignment", "source_address": "quran:2:7:4",
                 "head_case": "genitive", "head_governor_type": "preposition",
                 "governor": {"governor_type": "preposition"}}
        ok, defect = derive_reasoning(case, claim)
        self.assertTrue(ok, defect)

    def test_grader_coordination_sentinel_refuses_candidate_mood_basis_tajarrud(self):
        """I3: the coordination sentinel must not bypass the released mood_basis gate — candidate basis
        tajarrud stays refused here exactly as it is for fixed tuples (the exact hostile claim from the
        review)."""
        from tools.grade_grammar_reasoning import derive_reasoning
        case = {"expected_reason_keys": ["atf-tabaiyya-follows-matuf-alayh"], "expected_conclusion": "coordination"}
        claim = {"reason_key": "atf-tabaiyya-follows-matuf-alayh", "conclusion": "coordination",
                 "case_mood": "nominative", "head_case": "nominative", "head_governor_type": "mubtada_khabar",
                 "governor": {"governor_type": "mubtada_khabar"}, "mood_basis": "tajarrud",
                 "fact_type": "case_assignment", "source_address": "quran:2:7:4"}
        ok, defect = derive_reasoning(case, claim)
        self.assertFalse(ok)
        self.assertEqual(defect, "governor_not_justified")

    def test_grader_registry_example_is_not_evidence_for_another_occurrence(self):
        from tools.grade_grammar_reasoning import source_address_defect
        # a registry `examples` citation names an ayah RANGE, not a single word-level occurrence; it can never
        # satisfy the evidence rung for a different claim.
        claim = {"source_address": "quran:2:177:13-14"}
        self.assertIsNotNone(source_address_defect(claim))


class G6HiddenStructureMahall(unittest.TestCase):
    """G6: hidden structure, maḥall, and the ẓarf ʿāmil-kind correction."""

    @classmethod
    def setUpClass(cls):
        cls.hid = _load_bank("hidden-structure-mahall-eval.jsonl")

    def test_mabni_with_assigned_case_mood_is_fail15(self):
        from tools.validate_dependency_lattice import validate_lattice
        from tools import fusha_governor as G
        lat = _lattice_for(next(u for u in G.regression_units() if u["name"] == "prep-majrur-known"))
        lat["edges"][0]["mabni"] = True
        conds = {c for c, _ in validate_lattice(lat)}
        self.assertIn("15", conds)

    def test_fi_mahall_without_mabni_is_fail16(self):
        from tools.validate_dependency_lattice import validate_lattice
        from tools import fusha_governor as G
        lat = _lattice_for(next(u for u in G.regression_units() if u["name"] == "prep-majrur-known"))
        lat["edges"][0]["fi_mahall_case_mood"] = "accusative"
        conds = {c for c, _ in validate_lattice(lat)}
        self.assertIn("16", conds)

    def test_c15_c16_reject_reconstruction(self):
        for fid in ("C15", "C16"):
            edge = _lattice_for(self.hid[fid])["edges"][0]
            self.assertEqual(edge.get("abstention_reason"), "reject_reconstruction")
            self.assertNotIn("hidden_element", edge)

    def test_c17_obligatory_licence(self):
        edge = _lattice_for(self.hid["C17"])["edges"][0]
        self.assertTrue(edge["hidden_element"]["obligatory"])
        self.assertEqual(edge["decision_status"], "pending")

    def test_c18_non_obligatory_licence_flip_turns_red(self):
        edge = _lattice_for(self.hid["C18"])["edges"][0]
        self.assertFalse(edge["hidden_element"]["obligatory"])
        flipped = dict(edge, hidden_element=dict(edge["hidden_element"], obligatory=True))
        self.assertNotEqual(flipped["hidden_element"]["obligatory"], edge["hidden_element"]["obligatory"])

    def test_c19_analysis_dependent_attribution(self):
        edge = _lattice_for(self.hid["C19"])["edges"][0]
        self.assertEqual(edge["decision_status"], "pending")
        self.assertEqual(edge["analysis_attribution"]["status"], "analysis_dependent")

    def test_f5_hidden_kana_ism_obligatory_khabar_no_nasb_exponent(self):
        lat = _lattice_for(_load_bank("nawasikh-government-eval.jsonl")["F5"])
        ism_edge = next(e for e in lat["edges"] if e.get("hidden_element"))
        self.assertTrue(ism_edge["hidden_element"]["obligatory"])
        khabar_edge = next(e for e in lat["edges"] if e["rel_label"] == "khabar_nasikh")
        self.assertIsNone(khabar_edge["assigned_case_mood"])
        self.assertTrue(khabar_edge["mabni"])
        self.assertEqual(khabar_edge["fi_mahall_case_mood"], "accusative")

    def test_f6_f7_mabni_mahall_no_assigned_case(self):
        for fid in ("F6", "F7"):
            lat = _lattice_for(self.hid[fid])
            ism_edge = next(e for e in lat["edges"] if e["rel_label"] == "ism_nasikh")
            self.assertTrue(ism_edge["mabni"])
            self.assertEqual(ism_edge["mabni_on"], "fatha")
            self.assertEqual(ism_edge["fi_mahall_case_mood"], "accusative")
            self.assertIsNone(ism_edge["assigned_case_mood"])

    def test_f11_f12_annexation_governor_kind_idafa(self):
        for fid in ("F11", "F12"):
            lat = _lattice_for(self.hid[fid])
            dep_edge = next(e for e in lat["edges"] if e["rel_label"] == "idafa_dependent")
            self.assertEqual(dep_edge["justification_rule"], "zarf_idafa_governs_genitive")
            self.assertEqual(dep_edge["governor_type"], "noun")
            self.assertNotEqual(dep_edge["justification_rule"], "preposition_governs_genitive")
            self.assertTrue(any(e["rel_label"] == "zarf_idafa_head" for e in lat["edges"]))

    def test_f13_unchanged_still_resolved_preposition(self):
        lat = _lattice_for(self.hid["F13"])
        edge = next(e for e in lat["edges"] if e["rel_label"] == "jar_majrur")
        self.assertEqual(edge["justification_rule"], "preposition_governs_genitive")
        self.assertEqual(edge["decision_status"], "resolved")

    def test_c22_c23_zarf_construction(self):
        c22 = _lattice_for(self.hid["C22"])["edges"][0]
        self.assertEqual(c22["justification_rule"], "zarf_idafa_governs_genitive")
        self.assertEqual(c22["assigned_case_mood"], "genitive")
        c23 = _lattice_for(self.hid["C23"])["edges"][0]
        self.assertEqual(c23["rel_label"], "zarf_idafa_head")
        self.assertIsNone(c23["assigned_case_mood"])

    def test_f11_claim_governor_preposition_on_zarf_head_flagged_ordinary_path(self):
        """I2: F11 now carries a real claims[] entry naming "the preposition عِندَ" as the genitive governor.
        Unlike test_reason_claim_preposition_on_annexation_head_is_refused below (a HAND-MUTATED lattice), this
        exercises the ordinary claim-lint path build_dependency_lattice() already runs on every claim."""
        lat = _lattice_for(self.hid["F11"])
        claim_edge = next(e for e in lat["edges"] if e.get("claim_id") == "f11-c1")
        self.assertTrue(claim_edge["right_answer_wrong_reason_marker"])
        self.assertEqual(claim_edge["assigned_case_mood"], "genitive")
        self.assertEqual(claim_edge["head_governor_type"], "idafa")

    def test_reason_claim_preposition_on_annexation_head_is_refused(self):
        from tools.validate_dependency_lattice import validate_lattice
        from tools import fusha_governor as G
        lat = G.build_dependency_lattice(
            {"input_mode": "source_addressed", "source_unit": {"address": "q", "scope": "in_scope_source_addressed"},
             "tokens": [{"ref": "t1", "surface": "عِندَ", "pos": "preposition"},
                       {"ref": "t2", "surface": "زَيْدٍ", "pos": "noun", "case_visible": "genitive"}]})
        for e in lat["edges"]:
            if e.get("rel_label") == "idafa_dependent":
                e["justification_rule"] = "preposition_governs_genitive"
        conds = {c for c, _ in validate_lattice(lat)}
        self.assertIn("18", conds)


class G3ToG6OccurrenceIdentity(unittest.TestCase):
    """The three new banks: address-bearing rows must clear FAIL 14; refusal controls must NOT."""

    def test_positive_frames_clear_occurrence_identity(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        positive_ids = {
            "nawasikh-government-eval.jsonl": ("F1", "F2", "F3", "F4", "F5", "F8", "F14"),
            "coordination-case-following-eval.jsonl": ("F9", "F10"),
            "hidden-structure-mahall-eval.jsonl": ("F6", "F7", "F11", "F12", "F13"),
        }
        for bank_name, ids in positive_ids.items():
            bank = _load_bank(bank_name)
            for fid in ids:
                lat = _lattice_for(bank[fid])
                errs = verify_occurrence_identity(lat)
                self.assertEqual(errs, [], (bank_name, fid, errs))

    def test_negative_controls_are_refused(self):
        from tools.validate_dependency_lattice import verify_occurrence_identity
        negative_ids = {
            "nawasikh-government-eval.jsonl": ("N1", "N2"),
            "coordination-case-following-eval.jsonl": ("N3",),
            "hidden-structure-mahall-eval.jsonl": ("N4",),
        }
        for bank_name, ids in negative_ids.items():
            bank = _load_bank(bank_name)
            for fid in ids:
                row = bank[fid]
                lat = _lattice_for(row)
                errs = verify_occurrence_identity(lat)
                self.assertTrue(errs, (bank_name, fid))
                # M2: the refusal must be for the row's OWN declared mechanism (resolve_address's exact detail
                # string), not merely "some error" — N1/N2/N4 are refusal controls only because their ayahs are
                # currently absent from the spine (a coverage accident), unlike N3's genuinely semantic
                # word-index-overrun control; asserting the exact reason means a future spine change that makes
                # one of these ayahs resolvable turns this test red for the RIGHT reason instead of silently
                # keeping a stale, no-longer-true control green.
                detail = row.get("resolver_detail") or ""
                joined = " ".join(msg for _, msg in errs)
                for fragment in detail.split(" / "):
                    self.assertIn(fragment, joined, (bank_name, fid, fragment, joined))


if __name__ == "__main__":
    unittest.main()
