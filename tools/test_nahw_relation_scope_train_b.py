#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first test module for TRAIN-B relation licensing, scope, hidden government, rival preservation.

Twelve candidate units (bound-fa-function-discrimination, fa-function-and-mood-licensing,
preposition-sense-discriminators, verb-particle-selection-licensing, clitic-pronoun-role-discriminator,
hal-licensing-conditions, ishtighal-fronted-noun-case, ighra-tahdhir-licensing, tanazu-governor-selection,
badal-typology-discriminator, badal-vs-atf-bayan, la-negative-vs-prohibitive-discriminator) — candidates only;
none of this certifies an occurrence or absorbs a whole lesson.

This module is deliberately split into:
  TB1 - fa function discrimination (NEW: tools.fusha_nahw_particle_rules.fa_context_frame())
  TB2 - la negative-vs-prohibitive discrimination (regression over existing tools.fusha_governor)
  TB3 - attachment/governor safety (F11/F13 regression + NEW hostile dual-syncretic positive)
  TB4 - rival/school-attribution preservation (regression over existing C7-C21 fixtures)
  TB5 - non-regression controls (ma occurrence-binding, NGF drill keys)
  TB6 - cross-cutting mandatory safety (wrong-reason fails, no surface-alone selection, two-vote ceiling)
"""
import json
import os
import sys
import unicodedata
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from tools import fusha_nahw_particle_rules as PR  # noqa: E402
from tools import fusha_governor as G  # noqa: E402
from tools.fusha_check import resolve_address  # noqa: E402

NAHW_EVALS = os.path.join(REPO, "nahw", "evals")
SURFACE_INDEX_PATH = os.path.join(REPO, "qamus", "indexes", "quran-loc-surface", "index.jsonl")


def _jsonl(name):
    rows = {}
    with open(os.path.join(NAHW_EVALS, name), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def _load_surface_index():
    """quran_loc:word -> committed authoritative surface, from the repo's own word-index."""
    idx = {}
    with open(SURFACE_INDEX_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            idx[row["loc"]] = row["surface"]
    return idx


def _lattice_for(row):
    return G.build_dependency_lattice(row)


# ---------------------------------------------------------------------------
# TB1 - fa function discrimination (cu-bound-fa-function-discrimination, cu-fa-function-and-mood-licensing)
# ---------------------------------------------------------------------------
class TB1FaFunctionDiscrimination(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bank = _jsonl("fa-function-occurrence-eval.jsonl")
        cls.surface_index = _load_surface_index()

    def _assert_row_surface_matches_index(self, rid, row):
        """The row's surface must be NFC-exact-equal to the committed index at its own quran_loc:word — never
        merely equal to itself (self-consistency is not authority)."""
        loc = "%s:%d" % (row["quran_loc"], row["word"])
        indexed = self.surface_index.get(loc)
        self.assertIsNotNone(
            indexed, "%s: %s not present in qamus/indexes/quran-loc-surface/index.jsonl" % (rid, loc))
        self.assertEqual(
            unicodedata.normalize("NFC", indexed), unicodedata.normalize("NFC", row["surface"]),
            "%s: surface %r does not match the committed index surface %r at %s" % (rid, row["surface"], indexed, loc))

    def _evidence_for(self, row):
        return PR.mint_fixture_observation(
            row["frame"], source_address=row["source_address"], quran_loc=row["quran_loc"],
            word=row["word"], surface=row["surface"], target_kind="token", target_value="fa_function_frame")

    def test_fa_occ_001_2_37_1_ordinary_sequence_stays_pending_atfiyya_not_excluded(self):
        """narrative_perfect_no_mood_question cannot exclude a plain listing ʿāṭifa reading, so this frame
        must fail closed as pending rather than silently selecting istinafiyya (MERGE BLOCKER 1)."""
        row = self.bank["fa-occ-001"]
        r = PR.fa_context_frame(row["surface"], evidence=self._evidence_for(row), at=row["source_address"])
        self.assertEqual(r["decision"], "pending")
        self.assertEqual(r.get("evidence_defect"), "fa_function_unresolved")
        self.assertIsNone(r["mood_licensing"])
        rivals = {a["role"] for a in r["unresolved_alternatives"]
                  if a["defeater"] != "not_examined_by_this_axis"}
        self.assertEqual(rivals, {"istinafiyya", "sababiyya", "rabita"})
        for a in r["unresolved_alternatives"]:
            if a["defeater"] != "not_examined_by_this_axis":
                self.assertFalse(a["selected"])

    def test_fa_occ_002_17_22_7_causative_result_subjunctive(self):
        row = self.bank["fa-occ-002"]
        r = PR.fa_context_frame(row["surface"], evidence=self._evidence_for(row), at=row["source_address"])
        self.assertEqual(r["decision"], "candidate")
        self.assertEqual(r["function_candidate"], "sababiyya")
        ml = r["mood_licensing"]
        self.assertEqual(ml["licensed_mood"], "subjunctive")
        # fa itself is the CONTEXT for sababiyya, never the stated governor (the implied an is).
        self.assertFalse(ml["fa_governs_mood"])
        self.assertEqual(ml["governor"], "implied_an_after_fa_sababiyya")

    def test_fa_occ_003_80_4_3_refused_spine_absent_not_fabricated(self):
        """80:4 is genuinely absent from the repository's own address spine (a coverage accident, matching
        the established N1/N2/N4 refusal-control pattern) — evidence must never be minted for an out-of-scope
        address; 17:22:7 (fa-occ-002) already proves the sababiyya frame is discriminated correctly in-scope."""
        row = self.bank["fa-occ-003"]
        self.assertEqual(resolve_address(row["source_address"]).get("scope"), "out_of_scope")
        # mint_fixture_observation builds a well-formed ARTIFACT; it does not itself validate scope. The real
        # refusal is inside typed_observation's own coordinate check, exercised via fa_context_frame() below.
        ev = PR.mint_fixture_observation(
            row["frame"], source_address=row["source_address"], quran_loc=row["quran_loc"],
            word=row["word"], surface=row["surface"], target_kind="token", target_value="fa_function_frame")
        r = PR.fa_context_frame(row["surface"], evidence=ev, at=row["source_address"])
        self.assertEqual(r["decision"], "pending")
        # the caller's own `at` coordinate is checked before the evidence artifact -- an out-of-scope address
        # is refused at the very first gate, so no evidence is ever reached for this occurrence at all.
        self.assertEqual(r.get("evidence_defect"), "caller_occurrence_invalid")

    def test_fa_occ_004_2_283_14_fa_is_not_the_mood_governor(self):
        row = self.bank["fa-occ-004"]
        r = PR.fa_context_frame(row["surface"], evidence=self._evidence_for(row), at=row["source_address"])
        self.assertEqual(r["decision"], "candidate")
        self.assertEqual(r["function_candidate"], "rabita")
        ml = r["mood_licensing"]
        self.assertFalse(ml["fa_governs_mood"])
        self.assertEqual(ml["governor"], "lam_al_amr")
        self.assertEqual(ml["licensed_mood"], "jussive")
        self.assertNotEqual(ml["governor"], "fa")

    def test_fa_occ_005_7_39_4_fa_and_ma_stay_pending_atfiyya_not_excluded(self):
        """linked_to_separate_particle_component cannot exclude a plain listing ʿāṭifa reading either, so this
        frame must also fail closed as pending (MERGE BLOCKER 1) — the linked particle's own function is still
        decided independently, at the same address, regardless of fa's own pending state."""
        row = self.bank["fa-occ-005"]
        r = PR.fa_context_frame(row["surface"], evidence=self._evidence_for(row), at=row["source_address"])
        self.assertEqual(r["decision"], "pending")
        self.assertEqual(r.get("evidence_defect"), "fa_function_unresolved")
        rivals = {a["role"] for a in r["unresolved_alternatives"]
                  if a["defeater"] != "not_examined_by_this_axis"}
        self.assertEqual(rivals, {"istinafiyya", "sababiyya", "rabita"})
        # the linked negation particle's OWN function is decided independently, at the SAME address, via a
        # completely separate consumer — proving the two decisions are genuinely not fused into one call, even
        # while fa's own function candidate stays pending.
        neg = PR.negation_effect("مَا", context={"following_token_mood": "indicative"},
                                 at="quran:7:39:4", rules=PR.load_negation_rules(),
                                 particle_rules=PR.load_particle_rules())
        self.assertIsNotNone(neg)

    def test_fa_occ_006_ambiguous_frame_preserves_both_rivals(self):
        row = self.bank["fa-occ-006"]
        r = PR.fa_context_frame(row["surface"], evidence=self._evidence_for(row), at=row["source_address"])
        self.assertEqual(r["decision"], "pending")
        self.assertEqual(r.get("evidence_defect"), "fa_function_unresolved")
        rivals = {a["role"] for a in r["unresolved_alternatives"]
                  if a["defeater"] != "not_examined_by_this_axis"}
        self.assertEqual(rivals, {"istinafiyya", "sababiyya", "rabita"})
        for a in r["unresolved_alternatives"]:
            if a["defeater"] != "not_examined_by_this_axis":
                self.assertFalse(a["selected"])

    def test_fa_occ_007_conclusion_label_as_frame_is_off_vocabulary(self):
        row = self.bank["fa-occ-007"]
        ev = PR.mint_fixture_observation(
            row["frame"], source_address=row["source_address"], quran_loc="17:22", word=7,
            surface="فَتَقْعُدَ", target_kind="token", target_value="fa_function_frame")
        r = PR.fa_context_frame("فَتَقْعُدَ", evidence=ev, at="quran:17:22:7")
        self.assertEqual(r["decision"], "pending")
        self.assertEqual(r.get("evidence_defect"), "observation_off_vocabulary")

    def test_fa_surface_alone_never_selects_a_function(self):
        """Mandatory safety: fa's bare presence (no typed evidence) must abstain, never guess istinafiyya
        (the most frequent reading) by default."""
        r = PR.fa_context_frame("فَ", evidence=None, at=None)
        self.assertEqual(r["decision"], "pending")
        self.assertNotIn("function_candidate", r)

    def test_fa_bank_ids_are_unique_and_addresses_resolve_or_are_honest_refusal_controls(self):
        seen = set()
        for rid, row in self.bank.items():
            self.assertNotIn(rid, seen)
            seen.add(rid)
            scope = resolve_address(row["source_address"]).get("scope")
            # a refusal control is identified by the real consumer's own decision vocabulary
            # (pending/caller_occurrence_invalid) — "refused" is not a value fa_context_frame() ever emits.
            if row.get("expected_defect") == "caller_occurrence_invalid":
                self.assertEqual(scope, "out_of_scope", rid)
            else:
                self.assertEqual(scope, "in_scope_source_addressed", rid)

    def test_fa_exact_indexed_surface_bound_at_source_address(self):
        """MERGE BLOCKER 4: every bank row's surface is the exact indexed token at source_address (proclitic
        fused onto its host word), never the bare morpheme فَ that no real corpus word-index equals, and never
        a surface that merely equals itself — it must be NFC-exact-equal to the repository's own committed
        qamus/indexes/quran-loc-surface/index.jsonl at that row's quran_loc:word (authority, not
        self-consistency)."""
        from tools.normalize_ar import bare as _bare
        for rid, row in self.bank.items():
            self.assertNotEqual(row["surface"], "فَ", "%s: surface must be the exact indexed token" % rid)
            self.assertGreater(len(_bare(row["surface"])), 1,
                               "%s: surface must be a full word, not the isolated fa" % rid)
            ev = self._evidence_for(row)
            self.assertEqual(ev["occurrence"]["surface"], row["surface"], rid)
            self._assert_row_surface_matches_index(rid, row)

    def test_fa_stale_surface_from_another_address_is_rejected(self):
        """Hostile control: proves the index-authority check above actually checks the committed index rather
        than the bank's own self-equality. Substitutes a real, multi-character indexed surface from a
        DIFFERENT address/word (fa-occ-002's 17:22:7 token) onto a copy of fa-occ-001's row (2:37:1) and
        proves the surface-matches-index assertion fails on that stale value."""
        rid = "fa-occ-001"
        row = dict(self.bank[rid])
        own_loc = "%s:%d" % (row["quran_loc"], row["word"])
        stale_loc = "17:22:7"
        stale_surface = self.surface_index[stale_loc]
        self.assertNotEqual(own_loc, stale_loc)
        self.assertNotEqual(stale_surface, self.surface_index[own_loc],
                            "the substituted surface must genuinely differ from the row's own indexed surface")
        row["surface"] = stale_surface
        with self.assertRaises(AssertionError):
            self._assert_row_surface_matches_index(rid, row)


# ---------------------------------------------------------------------------
# TB2 - la negative vs prohibitive (cu-la-negative-vs-prohibitive-discriminator)
# ---------------------------------------------------------------------------
class TB2LaNegativeVsProhibitive(unittest.TestCase):

    def test_2_2_3_la_of_genus_not_2_2_2(self):
        """CORRECTION: the task packet's canary cites quran:2:2:2, but 2:2:2 is ٱلْكِتَٰبُ ('the Book') --
        لَا النافية للجنس is word 3 (verified via qamus/indexes/quran-loc-surface/index.jsonl, the repository's
        own internal word-index authority). The pre-existing nahw/evals/particle-function-eval.jsonl
        row PF-011 carries the SAME off-by-one (loc:"2:2:2"), so this is an inherited data-quality defect, not
        one introduced here; PF-011 is left untouched (a broadly shared bank) and this test uses the correct
        occurrence 2:2:3 instead of miscoding new evidence at the wrong address."""
        self.assertEqual(resolve_address("quran:2:2:3").get("scope"), "in_scope_source_addressed")
        unit = {
            "input_mode": "source_addressed",
            "source_unit": {"address": "quran:2:2", "scope": "in_scope_source_addressed"},
            "tokens": [
                {"ref": "2:2:3", "surface": "لَا", "pos": "particle"},
                {"ref": "2:2:4", "surface": "رَيْبَ", "pos": "noun", "definiteness": "indefinite",
                 "exponent": "fatha_no_tanwin"},
            ],
        }
        lat = _lattice_for(unit)
        ism_edge = next(e for e in lat["edges"] if e["rel_label"] == "ism_nasikh")
        self.assertEqual(ism_edge["trigger_family"], "la_jins")
        self.assertTrue(ism_edge["mabni"])
        self.assertEqual(ism_edge["mabni_on"], "fatha")
        self.assertEqual(ism_edge["fi_mahall_case_mood"], "accusative")
        self.assertIsNone(ism_edge["assigned_case_mood"])

    def test_4_43_4_prohibitive_plus_jussive(self):
        self.assertEqual(resolve_address("quran:4:43:4").get("scope"), "in_scope_source_addressed")
        unit = {
            "input_mode": "source_addressed",
            "source_unit": {"address": "quran:4:43", "scope": "in_scope_source_addressed"},
            "tokens": [
                {"ref": "4:43:4", "surface": "لَا", "pos": "particle"},
                {"ref": "4:43:5", "surface": "تَقْرَبُوا۟", "pos": "verb", "mood_visible": "jussive"},
            ],
        }
        lat = _lattice_for(unit)
        verb_edge = next(e for e in lat["edges"] if e["dependent"] == "4:43:5")
        self.assertEqual(verb_edge["trigger_family"], "la_nahiya")
        self.assertEqual(verb_edge["assigned_case_mood"], "jussive")
        self.assertEqual(verb_edge["justification_rule"], "operating_particle_governs_mood")

    def test_la_without_following_token_evidence_abstains(self):
        """Mandatory safety: la's surface alone (no POS/mood on the following token) never selects a family."""
        unit = {"input_mode": "arbitrary_typing",
                "tokens": [{"ref": "t1", "surface": "لَا", "pos": "particle"},
                          {"ref": "t2", "surface": "X"}]}
        lat = _lattice_for(unit)
        self.assertEqual(lat["edges"], [])

    def test_gp_wr_002_wrong_reasoning_trap_stays_two_vote_and_non_auto(self):
        """Regression: the la-jins right-visible-ending/wrong-reasoning trap (mabni fatha called muʿrab manṣūb)
        stays at or above two_vote_required and is never auto_safe."""
        from tools import fusha_nahw_gate_rules as GATE
        rows = [json.loads(l) for l in
                open(os.path.join(NAHW_EVALS, "grammar-wrong-reasoning-cases.jsonl"), encoding="utf-8")
                if l.strip()]
        row = next(r for r in rows if r["id"] == "GP-WR-002")
        self.assertEqual(row["topic"], "la_nafiyah_lil_jins")
        self.assertGreaterEqual(GATE.gate_rank(row["required_gate"]), GATE.gate_rank("two_vote_required"))
        self.assertNotEqual(row["hover_safety"], "auto_safe")
        self.assertTrue(row["wrong_reasoning_trap"])
        self.assertNotEqual(str(row["expected_reasoning"]), str(row["wrong_reasoning_trap"]))

    def test_gp_wr_002_correct_conclusion_wrong_reason_fails_via_grader(self):
        """Mandatory safety, exercised through the real grader: a correct visible ending (fatḥa) reached via
        the WRONG reasoning path (muʿrab manṣūb instead of mabni fatḥ) must fail, never pass on the strength
        of the right-looking ending alone."""
        from tools.grade_grammar_reasoning import grade
        row = json.loads(next(l for l in
                              open(os.path.join(NAHW_EVALS, "grammar-wrong-reasoning-cases.jsonl"),
                                   encoding="utf-8") if json.loads(l)["id"] == "GP-WR-002"))
        r = grade(row, {"final_ok": True, "reasoning_ok": False, "evidence_cited": True,
                        "source_address": "quran:demo", "two_vote_done": True})
        self.assertFalse(r["pass"])


# ---------------------------------------------------------------------------
# TB3 - attachment/governor safety (cu-preposition-sense-discriminators and the shared governor plane)
# ---------------------------------------------------------------------------
class TB3AttachmentGovernorSafety(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.hid = _jsonl("hidden-structure-mahall-eval.jsonl")

    def test_2_80_10_11_reject_invented_preposition(self):
        """F11 regression: عِندَ (2:80:10) is a ẓarf/iḍāfa-annexation NOUN, never a genuine ḥarf jarr; a claim
        that invents 'the preposition عِندَ' as the governor is right-answer/wrong-reason, flagged and pending."""
        lat = _lattice_for(self.hid["F11"])
        claim_edge = next(e for e in lat["edges"] if e.get("claim_id") == "f11-c1")
        self.assertTrue(claim_edge["right_answer_wrong_reason_marker"])
        self.assertEqual(claim_edge["justification_rule"], "governor_not_justified")
        self.assertEqual(claim_edge["head_governor_type"], "idafa")
        self.assertEqual(claim_edge["decision_status"], "pending")

    def test_2_7_3_4_control_genuine_preposition_resolved(self):
        """F13 regression control: عَلَىٰ is a genuine ḥarf jarr and must stay resolved, unaffected by the
        ẓarf/iḍāfa correction."""
        lat = _lattice_for(self.hid["F13"])
        edge = next(e for e in lat["edges"] if e["rel_label"] == "jar_majrur")
        self.assertEqual(edge["justification_rule"], "preposition_governs_genitive")
        self.assertEqual(edge["decision_status"], "resolved")

    def test_2_284_1_control_occurrence_resolves_normally(self):
        self.assertIsNone(resolve_address("quran:2:284:1").get("scope") == "out_of_scope" or None)
        self.assertEqual(resolve_address("quran:2:284:1").get("scope"), "in_scope_source_addressed")

    def test_2_97_14_15_syncretic_dual_does_not_rescue_wrong_head_claim(self):
        """NEW hostile positive: بَيْنَ (2:97:14) is a genuine ẓarf/iḍāfa head (like عِندَ) governing the dual
        يَدَيْهِ (2:97:15), whose oblique ending is nasb/jarr-SYNCRETIC (case_visible unmarked). A claim that
        mislabels the governor as a plain ḥarf jarr ('the preposition بين') must be refused exactly like F11 --
        the dependent's syncretic marking must never be read as confirmation that rescues the wrong governor
        kind, even though the CASE VALUE (genitive) it names happens to be right."""
        self.assertEqual(resolve_address("quran:2:97:14").get("scope"), "in_scope_source_addressed")
        self.assertEqual(resolve_address("quran:2:97:15").get("scope"), "in_scope_source_addressed")
        unit = {
            "input_mode": "source_addressed",
            "source_unit": {"address": "quran:2:97", "scope": "in_scope_source_addressed"},
            "tokens": [
                {"ref": "2:97:14", "surface": "بَيْنَ"},
                {"ref": "2:97:15", "surface": "يَدَيْهِ", "pos": "noun", "exponent_syncretic": True},
            ],
            "claims": [{"claim_id": "t97-c1", "target": "2:97:15", "claim_type": "case_mood",
                       "claimed_value": "genitive", "claimed_governor": "the preposition بين",
                       "claimed_reasoning": "genitive because governed by the preposition بين"}],
        }
        lat = _lattice_for(unit)
        # the CORRECT construction edge still reads the syncretic exponent as construction-categorical support
        # (medium confidence), never as a confirmed marking -- the ẓarf correction is not "rescued" upward either.
        idafa_edge = next(e for e in lat["edges"] if e["rel_label"] == "idafa_dependent")
        self.assertEqual(idafa_edge["justification_rule"], "zarf_idafa_governs_genitive")
        self.assertEqual(idafa_edge["justification_confidence"], "medium")
        # the WRONG-governor-kind CLAIM is refused independent of the dependent's own marking.
        claim_edge = next(e for e in lat["edges"] if e.get("claim_id") == "t97-c1")
        self.assertTrue(claim_edge["right_answer_wrong_reason_marker"])
        self.assertEqual(claim_edge["justification_rule"], "governor_not_justified")
        self.assertEqual(claim_edge["head_governor_type"], "idafa")
        self.assertNotEqual(claim_edge["decision_status"], "resolved")

    def test_attachment_unresolved_without_exact_head_evidence(self):
        """Mandatory safety: a bare noun+noun pair with no case evidence stays an unresolved PP-attachment /
        iḍāfa candidate, never a forced resolution."""
        unit = {"input_mode": "arbitrary_typing",
                "tokens": [{"ref": "t1", "surface": "كتاب", "pos": "noun"},
                          {"ref": "t2", "surface": "معلم", "pos": "noun"}]}
        lat = _lattice_for(unit)
        idafa_edges = [e for e in lat["edges"] if e["rel_label"] == "idafa_dependent"]
        self.assertTrue(idafa_edges)
        self.assertNotEqual(idafa_edges[0]["decision_status"], "resolved")
        self.assertIsNone(idafa_edges[0]["assigned_case_mood"])


# ---------------------------------------------------------------------------
# TB4 - rival / school-attribution preservation (cu-badal-typology-discriminator, cu-badal-vs-atf-bayan,
# cu-tanazu-governor-selection, and the shared coordination/hidden-structure planes)
# ---------------------------------------------------------------------------
class TB4RivalPreservation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.hid = _jsonl("hidden-structure-mahall-eval.jsonl")
        cls.co = _jsonl("coordination-case-following-eval.jsonl")

    def test_c15_c16_hidden_structure_reject_reconstruction_preserved(self):
        for fid in ("C15", "C16"):
            edge = _lattice_for(self.hid[fid])["edges"][0]
            self.assertEqual(edge.get("abstention_reason"), "reject_reconstruction")
            self.assertNotIn("hidden_element", edge)

    def test_c17_c18_hidden_structure_licensing_preserved(self):
        c17 = _lattice_for(self.hid["C17"])["edges"][0]
        self.assertTrue(c17["hidden_element"]["obligatory"])
        self.assertEqual(c17["decision_status"], "pending")
        c18 = _lattice_for(self.hid["C18"])["edges"][0]
        self.assertFalse(c18["hidden_element"]["obligatory"])

    def test_c19_hidden_structure_analysis_dependent_preserved(self):
        edge = _lattice_for(self.hid["C19"])["edges"][0]
        self.assertEqual(edge["decision_status"], "pending")
        self.assertEqual(edge["analysis_attribution"]["status"], "analysis_dependent")

    def test_c20_badal_vs_atf_bayan_both_licensed_preserved(self):
        edge = _lattice_for(self.co["C20"])["edges"][0]
        attribution = edge["analysis_attribution"]
        self.assertEqual(attribution["status"], "both_licensed")
        self.assertEqual(sorted(attribution["alternatives"]), ["atf_bayan", "badal"])
        self.assertNotIn("selected", attribution)

    def test_c21_tanazu_school_attributed_alternatives_preserved(self):
        lat = _lattice_for(self.co["C21"])
        self.assertEqual(len(lat["edges"]), 1)
        edge = lat["edges"][0]
        self.assertEqual(len(edge["unresolved_alternatives"]), 2)
        self.assertEqual(edge["analysis_attribution"]["status"], "both_licensed")
        self.assertNotEqual(edge["decision_status"], "resolved")

    def test_c7_c12_coordination_no_invented_governor_preserved(self):
        c7 = _lattice_for(self.co["C7"])["edges"][0]
        self.assertEqual(c7.get("abstention_reason"), "marking_unknown")
        self.assertIsNone(c7["assigned_case_mood"])
        c8 = _lattice_for(self.co["C8"])["edges"][0]
        self.assertEqual(c8.get("abstention_reason"), "not_coordination")
        c9 = _lattice_for(self.co["C9"])["edges"][0]
        self.assertEqual(c9.get("abstention_reason"), "non_governing_use")
        c10 = _lattice_for(self.co["C10"])["edges"][0]
        self.assertEqual(c10["analysis_attribution"]["status"], "analysis_dependent")
        c11 = _lattice_for(self.co["C11"])["edges"][0]
        self.assertEqual(c11.get("abstention_reason"), "insufficient_features")
        c12 = _lattice_for(self.co["C12"])["edges"][0]
        readings = {a.get("reading") for a in c12["unresolved_alternatives"]}
        self.assertEqual(readings, {"coordination", "maiyya"})
        self.assertNotEqual(c12["decision_status"], "resolved")

    def test_bare_waw_never_auto_resolves_no_invented_governor(self):
        unit = next(u for u in G.regression_units() if u["name"] == "coordination-headless")
        lat = _lattice_for(unit)
        self.assertFalse(any(e["decision_status"] == "resolved" for e in lat["edges"]))
        self.assertTrue(any(e["headless"] for e in lat["edges"]))


# ---------------------------------------------------------------------------
# TB5 - non-regression controls
# ---------------------------------------------------------------------------
class TB5NonRegression(unittest.TestCase):

    def test_93_3_1_and_2_284_10_stay_different_ma_occurrence_analyses(self):
        rel_ev = PR.mint_fixture_observation("object_of_verb_then_prep", source_address="quran:2:284:10",
                                             quran_loc="2:284", word=10, surface="مَا", target_kind="token",
                                             target_value="maa_relative_vs_negation")
        neg_ev = PR.mint_fixture_observation("not_object_before_verb", source_address="quran:93:3:1",
                                             quran_loc="93:3", word=1, surface="مَا", target_kind="token",
                                             target_value="maa_relative_vs_negation")
        r_rel = PR.maa_context_frame("مَا", evidence=rel_ev, at="quran:2:284:10")
        r_neg = PR.maa_context_frame("مَا", evidence=neg_ev, at="quran:93:3:1")
        self.assertEqual(r_rel["function_candidate"], "relative")
        self.assertEqual(r_neg["function_candidate"], "negation")
        self.assertNotEqual(r_rel["function_candidate"], r_neg["function_candidate"])
        # evidence for one occurrence is refused when replayed at the other's address (no cross-occurrence reuse).
        r_cross = PR.maa_context_frame("مَا", evidence=rel_ev, at="quran:93:3:1")
        self.assertEqual(r_cross["decision"], "pending")
        self.assertEqual(r_cross.get("evidence_defect"), "occurrence_not_current")

    def test_ngf_02_04_07_remain_reason_sensitive(self):
        keys_path = os.path.join(REPO, "curriculum", "drills", "keys", "nawasikh-governor-families.keys.jsonl")
        rows = {json.loads(l)["id"]: json.loads(l) for l in open(keys_path, encoding="utf-8") if l.strip()}
        for rid in ("NGF-02-kana-predicate-left-nominative", "NGF-04-laysa-not-verb-negator",
                   "NGF-07-continuative-two-token-governor"):
            row = rows[rid]
            self.assertTrue(row["two_vote_required"])
            self.assertTrue(row["required_reasoning"])
            self.assertTrue(row["forbidden_answers"])


# ---------------------------------------------------------------------------
# TB6 - cross-cutting mandatory safety
# ---------------------------------------------------------------------------
class TB6MandatorySafety(unittest.TestCase):

    def test_two_votes_yield_only_candidate_agreed_pending_certification(self):
        from tools.grade_grammar_reasoning import grade_two_vote, mint_fixture_vote
        KJ = "lam-jarr-fused-majrur-kasra"
        case = {"id": "TB", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
               "expected_reason_keys": [KJ]}

        def v(index, **kw):
            base = dict(reason_key=KJ, conclusion="genitive", case_mood="genitive",
                       relation="preposition_governs_genitive", fact_type="case_assignment",
                       worklist_id="worklist-%s" % ("a" if index == 0 else "b"))
            base.update(kw)
            return mint_fixture_vote(index, **base)

        r = grade_two_vote(case, v(0), v(1))
        self.assertTrue(r["pass"])
        self.assertFalse(r["certified"])
        self.assertEqual(r["route"], "candidate_agreed_pending_certification")

    def test_missing_pos_abstains_not_guesses(self):
        unit = {"input_mode": "source_addressed",
                "source_unit": {"address": "quran:2:2", "scope": "in_scope_source_addressed"},
                "tokens": [{"ref": "2:2:3", "surface": "لَا"}, {"ref": "2:2:4", "surface": "رَيْبَ"}]}
        lat = _lattice_for(unit)
        self.assertEqual(lat["edges"], [])

    def test_hidden_operators_use_closed_positive_inventory(self):
        self.assertEqual(G.HIDDEN_ELEMENT_LICENSING_INVENTORY,
                         {"kana_family_hidden_ism", "inna_family_hidden_ism", "imperative_verb",
                          "relative_clause_object_gap", "vocative_ya_noun"})

    def test_no_abrogator_or_la_edge_is_ever_auto_safe(self):
        for name, bank in (("hidden-structure-mahall-eval.jsonl", _jsonl("hidden-structure-mahall-eval.jsonl")),
                           ("coordination-case-following-eval.jsonl",
                            _jsonl("coordination-case-following-eval.jsonl"))):
            for fid, row in bank.items():
                lat = _lattice_for(row)
                for e in lat["edges"]:
                    self.assertNotEqual(e["gate"] if "gate" in e else e.get("gate"), "auto_safe", (name, fid))


if __name__ == "__main__":
    unittest.main()
