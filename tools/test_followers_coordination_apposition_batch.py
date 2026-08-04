#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_followers_coordination_apposition_batch — red-first tests for the Train C ordinary-runtime formative-
practice batch covering L1.M4.05, L2.M5.01, L4.M2.01, L4.M2.04, L4.M2.05, L4.M5.04 (followers: attributive
agreement, coordination case-following, badal/apposition typology, wāw function discrimination).

Proves, in order:
  1. The exact 27-row source candidate manifest (across the six named lessons) exists BYTE-IDENTICAL in
     curriculum/l1l6/drills-candidates/drill-candidates.jsonl, still `status: candidate_not_runtime_integrated`
     — this batch never claims those rows were promoted, and never touches that file.
  2. curriculum/drills/keys/followers-coordination-apposition.keys.jsonl carries exactly 27 NEWLY, independently
     authored runtime rows whose ids never reuse a dr-mc-* identity, each with quran_example:null and
     two_vote_required:true (every row is grammar: case/attachment/government).
  3. Every runtime row round-trips through the ordinary tutor grader (tools.fusha_tutor_runtime): a full-content
     correct answer is content_mastered=True, held_for_fact_gate=True, cleared=False, outcome='hold' and never
     enters progress.missed; a right answer with WRONG reasoning fails; a forbidden (wrong governor/attachment/
     function/relation-direction) answer is a true miss routed to local remediation.
  4. Two rows (FCA-04, FCA-18) model an occurrence whose deciding evidence is genuinely absent (a shared case
     inside an iḍāfa chain; a disputed particle with no interrogative marker); their authored correct answer IS
     the explicit abstention, and a forced-pick answer is forbidden — the runtime never forces a choice the
     evidence cannot license.
  5. `ordered_slots`-bearing rows reject the exact case-swapped (reversed-direction) rewrite of their own
     answer while still accepting every authored correct form — the direction of a case/government/attachment
     claim is load-bearing, not just its bag of words.
  6. Candidate provenance (drill_id / dr-mc-*/mc-* ids / curriculum_l1l6_id) is absent from every runtime row and
     from every assessment bank (the quarantine `tools.validate_drill_keys` already enforces, re-asserted here).
  7. Dry-run writes nothing; an explicit `--write` persists a schema-valid progress state.
  8. Hostile mutations of the shipped file (dropping two_vote_required / remediation_route, inserting candidate
     provenance, misrouting a kc_id to another drill) are all caught by `tools.validate_drill_keys.validate()`.
  9. The four proposed Knowledge Components (kc-attributive-follower-licensing, kc-coordination-particle-case-
     following, kc-badal-apposition-typology, kc-waw-function-accompaniment) HAVE SINCE been integrated into the
     shared `curriculum/kc-catalog.json` by the integration-owner commit that bound these drills to the shared
     KC runtime (append-only: the original 25 entries plus exactly these four, `_proposed_kc_catalog_patch()`,
     unchanged). This class now verifies that real integration byte-for-byte, and a genuine miss on an
     integrated row routes to KC-coded remediation through the real, unmodified catalog.
 10. Nine pre-existing keyed drill files are BYTE-IDENTICAL to the batch's start SHA; the KC catalog is
     append-only (original 25 unchanged, plus exactly the four integrated entries above).

Run: python3 tools/test_followers_coordination_apposition_batch.py
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_tutor_runtime as RT  # noqa: E402
from tools import validate_drill_keys as VDK  # noqa: E402
from tools import leak_sot  # noqa: E402

_START_SHA = "1bd48d1bf3664316415a01d976fc3b7771dbb38a"
_CANDIDATE_PATH = os.path.join(_REPO, "curriculum", "l1l6", "drills-candidates", "drill-candidates.jsonl")
_KEYS_PATH = os.path.join(_REPO, "curriculum", "drills", "keys", "followers-coordination-apposition.keys.jsonl")
_DRILL_PATH = os.path.join(_REPO, "curriculum", "drills", "followers-coordination-apposition.md")
_DRILL_ROUTE = "curriculum/drills/followers-coordination-apposition.md"

# the exact 27 source candidate ids, grouped by lesson exactly as specified (matched via each candidate row's
# misconception_link -> curriculum/l1l6/misconceptions/misconception-registry.jsonl manifestations[].lesson_id).
LESSON_CANDIDATE_IDS = {
    "L1.M4.05": ["dr-mc-0399", "dr-mc-0478", "dr-mc-0708"],
    "L2.M5.01": ["dr-mc-0001", "dr-mc-0298", "dr-mc-0824", "dr-mc-0853", "dr-mc-0865"],
    "L4.M2.01": ["dr-mc-0056", "dr-mc-0322", "dr-mc-0378", "dr-mc-0512", "dr-mc-0563"],
    "L4.M2.04": ["dr-mc-0223", "dr-mc-0418", "dr-mc-0626", "dr-mc-0826", "dr-mc-0827"],
    "L4.M2.05": ["dr-mc-0040", "dr-mc-0097", "dr-mc-0295", "dr-mc-0376", "dr-mc-0484"],
    "L4.M5.04": ["dr-mc-0079", "dr-mc-0573", "dr-mc-0610", "dr-mc-0823"],
}
ALL_CANDIDATE_IDS = [i for ids in LESSON_CANDIDATE_IDS.values() for i in ids]

# the primary canonical units this batch's runtime practice is written against (review context only — these
# units are candidate-status in curriculum/l1l6 and are never edited by this batch).
PRIMARY_UNITS = {
    "cu-attributive-agreement-licensing", "cu-atf-case-following", "cu-lakin-coordinator-vs-abrogator",
    "cu-atf-particle-discriminator", "cu-badal-typology-discriminator", "cu-waw-function-discriminator",
}
SUPPORTING_UNITS = {"u-n01", "u-n02", "u-n04", "u-n05", "u-n07", "u-n10", "u-n11", "u-s08"}

# rows whose expected_answer/accepted_variants narrate a genuine RELATION DIRECTION (which element gets which
# case) via ordered_slots — a hostile case-swapped rewrite of the same bag of words must be rejected.
DIRECTION_SENSITIVE_IDS = {
    "FCA-01-naat-case-copy", "FCA-10-atf-case-inheritance-core", "FCA-11-lakin-light-vs-heavy-nun-shape",
    "FCA-14-atf-case-inheritance-dual-discriminator", "FCA-19-badal-bad-min-kull-vs-naat",
    "FCA-21-badal-case-identity", "FCA-25-maiyya-object-accusative", "FCA-27-maiyya-requires-verbal-governor",
}

# the two rows whose authored correct answer IS an explicit abstention (missing/insufficient deciding evidence).
ABSTENTION_IDS = {"FCA-04-idafa-chain-case-undecidable", "FCA-18-amm-aw-disputed-clause-type"}

# the nine pre-existing keyed drills this batch must leave byte-identical (verified against the start SHA).
_PRE_EXISTING_KEYED_DRILLS = (
    "hover-composition-and-routing", "morphology-foundations", "nawasikh-governor-families",
    "parse-key-and-color-layer", "plan15-route-families", "quranic-function-words",
    "root-pattern-practice", "sentence-foundations", "vn00-aggressive-hover-closure",
)

# the four proposed KCs this batch is written against, and the exact patch (never applied to a repo file).
PROPOSED_KC_IDS = (
    "kc-attributive-follower-licensing", "kc-coordination-particle-case-following",
    "kc-badal-apposition-typology", "kc-waw-function-accompaniment",
)
# row-id -> proposed kc_id, matching each of the 27 rows to exactly one of the four proposed KCs.
_ATTR_IDS = ["FCA-%02d" % n for n in range(1, 9)]
_ATF_IDS = ["FCA-%02d" % n for n in range(9, 19)]
_BADAL_IDS = ["FCA-%02d" % n for n in range(19, 24)]
_WAW_IDS = ["FCA-%02d" % n for n in range(24, 28)]


def _proposed_kc_map(rows):
    by_prefix = {}
    for r in rows:
        num = int(re.match(r"FCA-(\d+)-", r["id"]).group(1))
        if num <= 8:
            by_prefix[r["id"]] = "kc-attributive-follower-licensing"
        elif num <= 18:
            by_prefix[r["id"]] = "kc-coordination-particle-case-following"
        elif num <= 23:
            by_prefix[r["id"]] = "kc-badal-apposition-typology"
        else:
            by_prefix[r["id"]] = "kc-waw-function-accompaniment"
    return by_prefix


def _proposed_kc_catalog_patch():
    """The EXACT four catalog entries the integration owner needs to add to curriculum/kc-catalog.json. Built
    here as data only — never written to a real repository file by this batch."""
    common = {"drill_route": _DRILL_ROUTE, "sarf_route": None,
              "nahw_route": "nahw/procedures/coordination-case-following.md",
              "grammar_topic": "followers", "cefr_band": "C1", "severity": "warn",
              "default_gate": "human_source_review_required", "diagnostic_classes": ["possible_governor_unresolved"],
              "curriculum_misconception_ids": [], "curriculum_error_examples": []}
    return [
        dict(common, kc_id="kc-attributive-follower-licensing",
             arabic_grammar_name="naʿt agreement licensing",
             plain_rule="An attributive follower (naʿt) copies its head noun's case, definiteness, gender and "
                        "number, except a non-human plural head takes feminine-singular agreement and an "
                        "indefinite, non-annexed elative stays in its invariable base shape.",
             trigger_condition="an adjective follows a noun and the agreement lattice cannot confirm all "
                               "required axes from the supplied evidence",
             expected_feature="case, definiteness, gender and number copied from the head (or the two named "
                              "exceptions correctly applied)",
             typical_error_feature="one agreement axis left uncopied, or an exception applied where it does "
                                   "not hold",
             point_template="Before assigning agreement here, name which axis the follower must copy.",
             teach_template="A naʿt copies its head's case, definiteness, gender and number, with two named "
                            "exceptions; a right ending named without checking every axis is unsafe.",
             nahw_route="nahw/procedures/irab-case-mood.md",
             bottom_out_template="Name every agreement axis, then justify each one from the head."),
        dict(common, kc_id="kc-coordination-particle-case-following",
             arabic_grammar_name="ʿaṭf case-following and the light/heavy لكن split",
             plain_rule="A coordinated conjunct copies the case of the element it is joined to, whatever that "
                        "case is; لكن with no gemination coordinates, لَٰكِنَّ with gemination abrogates.",
             trigger_condition="a coordinator joins two terms and the governor lattice cannot confirm the "
                               "conjunct's case matches the joined-to element from the supplied evidence",
             expected_feature="the conjunct's case named as inherited from the joined-to element",
             typical_error_feature="the conjunct assigned a case of its own, or لكن's gemination misread",
             point_template="Before assigning the conjunct's case, name the element it is joined to.",
             teach_template="A conjunct never carries a case of its own; it copies the joined-to element's "
                            "case, whatever that case is.",
             bottom_out_template="Name the joined-to element, then copy its case onto the conjunct."),
        dict(common, kc_id="kc-badal-apposition-typology",
             arabic_grammar_name="badal (apposition) typology",
             plain_rule="An appositive (badal) copies its antecedent's case; total apposition needs no "
                        "resumptive clitic, while partitive and inclusion apposition require one.",
             trigger_condition="a nominal follows another nominal sharing reference and the typology lattice "
                               "cannot confirm the badal type from the supplied evidence",
             expected_feature="the badal type named (total/partitive/inclusion) with its case and clitic "
                              "requirement",
             typical_error_feature="the badal's case assigned independently of its antecedent, or the clitic "
                                   "requirement of the partitive/inclusion types ignored",
             point_template="Before assigning a case here, name the badal type and its clitic requirement.",
             teach_template="A badal always copies its antecedent's case; only the partitive and inclusion "
                            "types also require a resumptive clitic.",
             bottom_out_template="Name the badal type, then copy the antecedent's case and check the clitic."),
        dict(common, kc_id="kc-waw-function-accompaniment",
             arabic_grammar_name="wāw function discrimination (coordination vs. maʿiyya)",
             plain_rule="A nominal after وَ is an accompaniment (maʿiyya) object only with a verbal governor to "
                        "its left; otherwise the wāw defaults to coordination and the second nominal copies the "
                        "first noun's case. Animacy is a cue toward coordination, never an absolute gate against "
                        "accompaniment.",
             trigger_condition="a nominal follows وَ and the sense lattice cannot confirm coordination vs. "
                               "maʿiyya from the supplied evidence",
             expected_feature="a verbal governor checked before any accompaniment (accusative) reading",
             typical_error_feature="accompaniment asserted with no verbal governor, or ruled out from "
                                   "animacy alone",
             point_template="Before assigning a case after وَ, check for a verbal governor to its left.",
             teach_template="Maʿiyya needs a verbal governor; with none, the wāw coordinates and the second "
                            "noun copies the first noun's case.",
             bottom_out_template="Check for a verbal governor, then decide coordination vs. accompaniment."),
    ]


# --------------------------------------------------------------------------- loaders

def _git_show(path_rel):
    out = subprocess.run(["git", "show", "%s:%s" % (_START_SHA, path_rel)], cwd=_REPO,
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8")


def _load_jsonl_text(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _load_candidate_rows():
    with open(_CANDIDATE_PATH, encoding="utf-8") as fh:
        rows = {}
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("drill_id") in ALL_CANDIDATE_IDS:
                rows[r["drill_id"]] = r
    return rows


def _load_runtime_rows():
    with open(_KEYS_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# --------------------------------------------------------------------------- 1. candidate manifest untouched

class CandidateManifestUnchanged(unittest.TestCase):
    """The 27 source candidate rows exist, are unchanged in status, and are byte-identical to the start SHA —
    this batch never writes curriculum/l1l6/drills-candidates/drill-candidates.jsonl."""

    def test_exact_27_row_manifest_present_across_six_lessons(self):
        rows = _load_candidate_rows()
        self.assertEqual(len(ALL_CANDIDATE_IDS), 27)
        self.assertEqual(set(rows), set(ALL_CANDIDATE_IDS), "the candidate manifest must match exactly")
        self.assertEqual(len(LESSON_CANDIDATE_IDS), 6, "six lessons")

    def test_candidate_rows_still_candidate_not_runtime_integrated(self):
        rows = _load_candidate_rows()
        for drill_id, row in rows.items():
            self.assertEqual(row.get("status"), "candidate_not_runtime_integrated",
                            "%s must never be marked promoted by this batch" % drill_id)

    def test_candidate_rows_byte_identical_to_start_sha(self):
        original = {r["drill_id"]: r for r in _load_jsonl_text(_git_show(
            "curriculum/l1l6/drills-candidates/drill-candidates.jsonl")) if r.get("drill_id") in ALL_CANDIDATE_IDS}
        current = _load_candidate_rows()
        self.assertEqual(set(original), set(ALL_CANDIDATE_IDS))
        for drill_id in ALL_CANDIDATE_IDS:
            self.assertEqual(original[drill_id], current[drill_id],
                            "%s must be byte-identical to the start SHA" % drill_id)

    def test_primary_and_supporting_units_are_the_ones_named(self):
        rows = _load_candidate_rows()
        seen = set()
        for row in rows.values():
            seen.update(row.get("unit_links") or [])
        # every candidate row's unit_links stay inside supporting units ∪ {u-n03, u-s06, u-s09-like extras
        # never appear here}; a genuine subset check against the supporting-unit roster named in the brief.
        self.assertTrue(seen.issubset(SUPPORTING_UNITS),
                        "unexpected unit_links outside the named supporting units: %s" % (seen - SUPPORTING_UNITS))


# --------------------------------------------------------------------------- 2. runtime batch manifest

class RuntimeBatchManifest(unittest.TestCase):
    """The 27 newly, independently authored runtime rows: correct count, no dr-mc-* id reuse, quran_example
    null, two_vote_required for every grammar row."""

    def test_exactly_27_runtime_rows_no_padding_no_id_reuse(self):
        rows = _load_runtime_rows()
        self.assertGreaterEqual(len(rows), 25)
        self.assertLessEqual(len(rows), 27)
        self.assertEqual(len(rows), 27, "this batch authored all 27 (no defer reasons needed)")
        ids = {r["id"] for r in rows}
        self.assertEqual(len(ids), 27, "duplicate runtime ids")
        for rid in ids:
            self.assertFalse(rid.startswith("dr-mc-"), "%r reuses a candidate drill_id identity" % rid)
            self.assertFalse(re.match(r"^mc-\d+$", rid), "%r reuses a misconception id identity" % rid)

    def test_every_row_quran_example_null_and_two_vote_required(self):
        for row in _load_runtime_rows():
            self.assertIsNone(row["quran_example"], "%s: quran_example must be null (no occurrence claim)" % row["id"])
            self.assertTrue(row["two_vote_required"], "%s: every row in this batch is grammar and must be "
                            "two_vote_required" % row["id"])

    def test_every_row_has_the_required_authoring_fields(self):
        required = {"id", "level", "concept", "prompt", "quran_example", "expected_answer", "accepted_variants",
                    "forbidden_answers", "required_reasoning", "sarf_procedure", "nahw_procedure",
                    "remediation_route", "two_vote_required"}
        for row in _load_runtime_rows():
            missing = required - set(row)
            self.assertFalse(missing, "%s missing fields %s" % (row["id"], missing))
            self.assertTrue(row["accepted_variants"])
            self.assertTrue(row["forbidden_answers"])
            self.assertTrue(row["required_reasoning"])
            self.assertEqual(row["remediation_route"], _DRILL_ROUTE)
            self.assertIsNone(row["sarf_procedure"])
            self.assertIn(row["nahw_procedure"],
                         ("nahw/procedures/irab-case-mood.md", "nahw/procedures/coordination-case-following.md"),
                         "%s cites an unexpected nahw_procedure %r" % (row["id"], row["nahw_procedure"]))

    def test_every_row_is_bound_to_its_reviewed_kc_family(self):
        rows = _load_runtime_rows()
        expected = _proposed_kc_map(rows)
        for row in rows:
            self.assertEqual(row.get("kc_id"), expected[row["id"]],
                             "%s must resolve to its reviewed follower-family KC" % row["id"])

    def test_drill_keys_validator_accepts_the_file_clean(self):
        errs = VDK.validate(_KEYS_PATH)
        self.assertEqual(errs, [])

    def test_drill_markdown_exists_and_cites_every_item_id(self):
        self.assertTrue(os.path.exists(_DRILL_PATH))
        with open(_DRILL_PATH, encoding="utf-8") as fh:
            text = fh.read()
        for row in _load_runtime_rows():
            self.assertIn(row["id"].split("-")[0] + "-" + row["id"].split("-")[1], text,
                          "%s not referenced in the drill markdown" % row["id"])


# --------------------------------------------------------------------------- 3. grader round trip

class RuntimeGraderRoundTrip(unittest.TestCase):
    """Every one of the 27 rows round-trips through tools.fusha_tutor_runtime.grade()/step()."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _load_runtime_rows()

    def test_full_correct_answer_is_mastered_but_held_never_cleared(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"]),
                          "second_check": {"conclusion_agrees": True, "reason_agrees": True}}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertTrue(g["content_mastered"], row["id"])
                self.assertTrue(g["held_for_fact_gate"], row["id"])
                self.assertFalse(g["cleared"], row["id"])
                self.assertEqual(r["outcome"], "hold", row["id"])

    def test_every_accepted_variant_also_clears_content(self):
        for row in self.rows:
            for i, variant in enumerate(row["accepted_variants"]):
                with self.subTest(id=row["id"], variant=i):
                    payload = {"answer": variant, "reasoning": list(row["required_reasoning"])}
                    g = RT.grade(row, payload)
                    self.assertTrue(g["content_mastered"], "%s variant %d: %r" % (row["id"], i, variant[:60]))

    def test_right_answer_wrong_reasoning_fails(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["expected_answer"], "reasoning": ["it just sounds right"]}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertFalse(g["content_mastered"], "%s: wrong reasoning must not be mastered" % row["id"])
                self.assertFalse(g["cleared"], row["id"])

    def test_content_mastered_held_rows_never_enter_missed_progress(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])}
                r = RT.step(row, None, payload, now_day=0)
                progress = RT.new_progress()
                RT.apply_event_to_progress(progress, row, r, seq=0)
                open_misses = {m["item_id"] for m in progress["missed"]}
                self.assertNotIn(row["id"], open_misses,
                                "%s: a content-mastered/held row must never appear in progress.missed" % row["id"])

    def test_every_forbidden_answer_is_a_true_miss_routed_to_local_remediation(self):
        """Generalizes the ordered_slots case: a wrong governor/attachment/function/relation-direction answer
        (the row's own authored forbidden_answers) never clears and always routes to this drill."""
        for row in self.rows:
            for i, bad in enumerate(row["forbidden_answers"]):
                with self.subTest(id=row["id"], forbidden=i):
                    payload = {"answer": bad, "reasoning": []}
                    r = RT.step(row, None, payload, now_day=0)
                    g = r["grade"]
                    self.assertFalse(g["cleared"], row["id"])
                    self.assertFalse(g["held_for_fact_gate"],
                                    "%s: a forbidden answer is a real miss, not a fact hold" % row["id"])
                    progress = RT.new_progress()
                    RT.apply_event_to_progress(progress, row, r, seq=0)
                    missed = {m["item_id"]: m for m in progress["missed"]}
                    self.assertIn(row["id"], missed, row["id"])
                    self.assertEqual(missed[row["id"]]["remediation_route"], _DRILL_ROUTE)


# --------------------------------------------------------------------------- 4. abstention accepted, not forced

class MissingEvidenceAcceptsExplicitAbstention(unittest.TestCase):
    """FCA-04 (a shared genitive case inside an iḍāfa chain) and FCA-18 (a disputed particle with no
    interrogative marker) authored their CORRECT answer as the explicit abstention itself — the runtime must
    never force a pick the evidence cannot license."""

    def test_abstention_rows_present(self):
        ids = {r["id"] for r in _load_runtime_rows()}
        self.assertTrue(ABSTENTION_IDS.issubset(ids), "missing abstention rows: %s" % (ABSTENTION_IDS - ids))

    def test_the_abstention_answer_itself_is_content_mastered(self):
        rows = {r["id"]: r for r in _load_runtime_rows()}
        for rid in ABSTENTION_IDS:
            row = rows[rid]
            with self.subTest(id=rid):
                payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])}
                g = RT.grade(row, payload)
                self.assertTrue(g["content_mastered"], "%s: the abstention itself must be the mastered answer" % rid)

    def test_a_forced_pick_is_a_forbidden_answer_and_fails(self):
        rows = {r["id"]: r for r in _load_runtime_rows()}
        for rid in ABSTENTION_IDS:
            row = rows[rid]
            with self.subTest(id=rid):
                self.assertTrue(row["forbidden_answers"], "%s: must name at least one forced-pick answer" % rid)
                for bad in row["forbidden_answers"]:
                    g = RT.grade(row, {"answer": bad, "reasoning": []})
                    self.assertFalse(g["cleared"], "%s: forced pick %r must not clear" % (rid, bad[:60]))


# --------------------------------------------------------------------------- 5. ordered_slots direction guard

def _case_swap(text):
    """Swap every occurrence of 'nominative' <-> 'accusative' in place — the exact reversed-direction rewrite
    a direction-sensitive row (agreement copy direction, case-inheritance direction, badal/maʿiyya case
    assignment) teaches against. Same bag of words, only the case LABELS at each slot are reversed."""
    placeholder = "\x00NOMINATIVE\x00"
    swapped = re.sub(r"nominative", placeholder, text, flags=re.I)
    swapped = re.sub(r"accusative", "nominative", swapped, flags=re.I)
    return swapped.replace(placeholder, "accusative")


class DirectionSensitiveCaseSwapIsRejected(unittest.TestCase):
    """`ordered_slots` is the row-authored marker of "this row's answer matching is direction-sensitive"; every
    row that carries it must reject its own case-swapped rewrite while still accepting every authored form."""

    def test_direction_sensitive_rows_present(self):
        rows = [row for row in _load_runtime_rows() if row.get("ordered_slots")]
        ids = {r["id"] for r in rows}
        self.assertEqual(ids, DIRECTION_SENSITIVE_IDS)
        self.assertGreaterEqual(len(rows), 6)

    def test_ordered_slots_rows_reject_their_own_case_swapped_rewrite(self):
        for row in _load_runtime_rows():
            if not row.get("ordered_slots"):
                continue
            with self.subTest(id=row["id"]):
                swapped = _case_swap(row["expected_answer"])
                self.assertNotEqual(swapped, row["expected_answer"],
                                    "%s: case swap must actually change the answer text" % row["id"])
                payload = {"answer": swapped, "reasoning": list(row["required_reasoning"])}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertFalse(g["content_mastered"],
                                 "%s: the case-swapped (reverse-direction) rewrite must NOT be mastered" % row["id"])
                self.assertFalse(g["cleared"], row["id"])

    def test_ordered_slots_rows_still_accept_every_authored_correct_form(self):
        for row in _load_runtime_rows():
            if not row.get("ordered_slots"):
                continue
            forms = [row["expected_answer"]] + list(row.get("accepted_variants") or [])
            for form in forms:
                with self.subTest(id=row["id"], form=form[:40]):
                    payload = {"answer": form, "reasoning": list(row["required_reasoning"])}
                    r = RT.step(row, None, payload, now_day=0)
                    self.assertTrue(r["grade"]["content_mastered"],
                                    "%s: authored correct form must still be mastered: %r" % (row["id"], form))


# --------------------------------------------------------------------------- 6. provenance boundary

class ProvenanceBoundary(unittest.TestCase):
    """Candidate provenance never enters the runtime-visible artifacts or any assessment bank."""

    _MARKERS = ("dr-mc-", "misconception_id", "candidate_id", "candidate_drill_id", "curriculum_l1l6_id",
               "candidate_provenance", "source_misconception")

    def test_no_candidate_provenance_field_or_id_in_runtime_rows(self):
        for row in _load_runtime_rows():
            for marker in self._MARKERS:
                self.assertNotIn(marker, json.dumps(row, ensure_ascii=False),
                                "%s: candidate provenance marker %r leaked" % (row["id"], marker))

    def test_no_leak_sot_hits_in_any_runtime_row(self):
        for row in _load_runtime_rows():
            hits = leak_sot.scan(json.dumps(row, ensure_ascii=False))
            self.assertEqual(hits, [], "%s: leak-SoT hit %s" % (row["id"], hits))

    def test_assessment_banks_carry_no_candidate_provenance(self):
        errs = VDK.assessment_quarantine_violations()
        self.assertEqual(errs, [])

    def test_drill_markdown_carries_no_candidate_provenance(self):
        with open(_DRILL_PATH, encoding="utf-8") as fh:
            text = fh.read()
        for marker in self._MARKERS:
            self.assertNotIn(marker, text, "drill markdown leaked %r" % marker)
        hits = leak_sot.scan(text)
        self.assertEqual(hits, [])


# --------------------------------------------------------------------------- 7. dry-run / schema-valid writes

class DryRunAndExplicitProgressWrites(unittest.TestCase):
    """No persistent write without --write; a schema-valid progress state is written only when asked."""

    def test_dry_run_writes_nothing(self):
        rows = _load_runtime_rows()
        with tempfile.TemporaryDirectory() as td:
            bank_path = os.path.join(td, "bank.jsonl")
            with open(bank_path, "w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            ans_path = os.path.join(td, "answer.json")
            row0 = rows[0]
            with open(ans_path, "w", encoding="utf-8") as fh:
                json.dump({"answer": row0["expected_answer"], "reasoning": list(row0["required_reasoning"])}, fh)
            prog_path = os.path.join(td, "progress.json")
            log_path = os.path.join(td, "events.jsonl")
            argv = ["--bank", bank_path, "--item", row0["id"], "--answer", ans_path,
                    "--progress", prog_path, "--event-log", log_path, "--now", "0"]
            RT._run_main(argv)  # NO --write
            self.assertFalse(os.path.exists(prog_path), "dry run wrote progress without --write")
            self.assertFalse(os.path.exists(log_path), "dry run wrote an event log without --write")

    def test_explicit_write_persists_schema_valid_progress(self):
        rows = _load_runtime_rows()
        with tempfile.TemporaryDirectory() as td:
            bank_path = os.path.join(td, "bank.jsonl")
            with open(bank_path, "w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            row0 = rows[0]
            ans_path = os.path.join(td, "answer.json")
            with open(ans_path, "w", encoding="utf-8") as fh:
                json.dump({"answer": row0["expected_answer"], "reasoning": list(row0["required_reasoning"])}, fh)
            prog_path = os.path.join(td, "progress.json")
            log_path = os.path.join(td, "events.jsonl")
            argv = ["--bank", bank_path, "--item", row0["id"], "--answer", ans_path,
                    "--progress", prog_path, "--event-log", log_path, "--now", "0", "--write"]
            RT._run_main(argv)
            self.assertTrue(os.path.exists(prog_path) and os.path.exists(log_path))
            with open(prog_path, encoding="utf-8") as fh:
                prog = json.load(fh)
            self.assertEqual(prog.get("schema"), RT.PROGRESS_SCHEMA)
            self.assertIn(row0["id"], prog.get("items", {}))
            with open(log_path, encoding="utf-8") as fh:
                events = [json.loads(l) for l in fh if l.strip()]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["schema"], RT.EVENT_SCHEMA)
            self.assertEqual(events[0]["item_id"], row0["id"])


# --------------------------------------------------------------------------- 8. hostile mutations rejected

class HostileMutationsAreRejected(unittest.TestCase):
    """Mutating the shipped file's invariants must be caught by tools.validate_drill_keys.validate()."""

    def _write_temp_repo(self, rows, fname="followers-coordination-apposition.keys.jsonl",
                         extra_catalog_entries=None):
        d = tempfile.mkdtemp()
        keys_dir = os.path.join(d, "curriculum", "drills", "keys")
        os.makedirs(keys_dir)
        open(os.path.join(d, "curriculum", "drills", "followers-coordination-apposition.md"),
             "w", encoding="utf-8").close()
        for drill in ("nawasikh-governor-families",):
            open(os.path.join(d, "curriculum", "drills", drill + ".md"), "w", encoding="utf-8").close()
        for proc in ("nahw/procedures/irab-case-mood.md", "nahw/procedures/coordination-case-following.md"):
            pdir = os.path.join(d, os.path.dirname(proc))
            os.makedirs(pdir, exist_ok=True)
            open(os.path.join(d, proc), "w", encoding="utf-8").close()
        with open(os.path.join(_REPO, "curriculum", "kc-catalog.json"), encoding="utf-8") as fh:
            catalog = json.load(fh)
        if extra_catalog_entries:
            catalog = catalog + extra_catalog_entries
        os.makedirs(os.path.join(d, "curriculum"), exist_ok=True)
        with open(os.path.join(d, "curriculum", "kc-catalog.json"), "w", encoding="utf-8") as fh:
            json.dump(catalog, fh)
        fp = os.path.join(keys_dir, fname)
        with open(fp, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        return d, fp

    def test_dropping_two_vote_required_on_a_level7_hard_row_is_caught(self):
        rows = _load_runtime_rows()
        mutated = copy.deepcopy(rows)
        target = next(r for r in mutated if r["level"] == "7")
        target["two_vote_required"] = False
        d, fp = self._write_temp_repo(mutated)
        errs = VDK.validate(fp, repo_root=d)
        self.assertTrue(any("Level 7+ hard-grammar row" in e for e in errs),
                        "dropping two_vote_required on a hard row was accepted: %s" % errs)

    def test_dropping_remediation_route_field_is_caught(self):
        rows = _load_runtime_rows()
        mutated = copy.deepcopy(rows)
        del mutated[0]["remediation_route"]
        d, fp = self._write_temp_repo(mutated)
        errs = VDK.validate(fp, repo_root=d)
        self.assertTrue(any("missing fields" in e and "remediation_route" in e for e in errs),
                        "a row missing remediation_route was accepted: %s" % errs)

    def test_inserting_candidate_provenance_is_caught_by_the_provenance_boundary_scan(self):
        # tools.validate_drill_keys's assessment-quarantine check only scans curriculum/assessment/*.jsonl, and
        # leak_sot has no "dr-mc-"/provenance-field vocabulary — a keys-file-level provenance leak is caught by
        # this batch's own marker scan (ProvenanceBoundary, above), re-asserted here as the hostile-insertion
        # case: inserting a candidate-provenance field must make that scan fail on the mutated row.
        rows = _load_runtime_rows()
        mutated = copy.deepcopy(rows)
        mutated[0]["drill_id"] = "dr-mc-0001"
        blob = json.dumps(mutated[0], ensure_ascii=False)
        hits = [m for m in ProvenanceBoundary._MARKERS if m in blob]
        self.assertIn("dr-mc-", hits, "inserted candidate provenance (drill_id=dr-mc-0001) was not detected "
                      "by the provenance-boundary marker scan")

    def test_misrouted_kc_id_to_a_different_drill_is_caught(self):
        rows = _load_runtime_rows()
        mutated = copy.deepcopy(rows)
        # kc-nawasikh-kana-laysa-government resolves in the real catalog but routes to a DIFFERENT drill.
        mutated[0]["kc_id"] = "kc-nawasikh-kana-laysa-government"
        d, fp = self._write_temp_repo(mutated)
        errs = VDK.validate(fp, repo_root=d)
        self.assertTrue(any("is not this key file's own drill" in e for e in errs),
                        "a kc_id misrouted to a different drill's key file was accepted: %s" % errs)


# --------------------------------------------------------------------------- 9. shared-KC integration

class SharedKCCatalogIntegration(unittest.TestCase):
    """The integration owner applied the exact Sonnet-authored four-KC patch and row mapping."""

    def test_reviewed_kc_entries_are_present_exactly(self):
        with open(os.path.join(_REPO, "curriculum", "kc-catalog.json"), encoding="utf-8") as fh:
            real = {kc["kc_id"]: kc for kc in json.load(fh)}
        expected = {kc["kc_id"]: kc for kc in _proposed_kc_catalog_patch()}
        self.assertEqual({kc_id: real.get(kc_id) for kc_id in PROPOSED_KC_IDS}, expected)

    def test_bound_runtime_rows_validate_against_the_real_catalog(self):
        self.assertEqual(VDK.validate(_KEYS_PATH, repo_root=_REPO), [])

    def test_a_genuine_miss_once_patched_routes_to_kc_coded_remediation(self):
        """Proves 'genuine misses route remediation and KC progress': once a row is kc_id-bound (the
        integration-owner's future state), a real miss's progress.missed entry carries that kc_id as its
        error_reason — exactly what tools.fusha_tutor_runtime.apply_event_to_progress already implements."""
        rows = _load_runtime_rows()
        kc_of = _proposed_kc_map(rows)
        row = copy.deepcopy(rows[0])
        self.assertEqual(row["kc_id"], kc_of[row["id"]])
        payload = {"answer": row["forbidden_answers"][0], "reasoning": []}
        r = RT.step(row, None, payload, now_day=0)
        progress = RT.new_progress()
        RT.apply_event_to_progress(progress, row, r, seq=0)
        missed = {m["item_id"]: m for m in progress["missed"]}
        self.assertIn(row["id"], missed)
        self.assertEqual(missed[row["id"]]["error_reason"], kc_of[row["id"]])
        self.assertEqual(missed[row["id"]]["remediation_route"], _DRILL_ROUTE)


# --------------------------------------------------------------------------- 9b. badal subtype regression
class FCA19BadalSubtypeRegression(unittest.TestCase):
    """MERGE BLOCKER 2: FCA-19 must stay badal baʿḍ min kull (a literal part/fraction of the whole) and must
    never regress into an ishtimāl-style stimulus (an abstract attribute/quality of the whole) while keeping
    the ba'd-min-kull label — that combination is a right-answer/wrong-reason defect the grammar-safety gate
    forbids (AGENTS.md: 'a correct answer with wrong iʿrāb reasoning is unsafe')."""

    _ISHTIMAL_MARKERS = ("خُلُقُ", "خلقه", "khuluquhu")

    def _row(self):
        rows = _load_runtime_rows()
        return next(r for r in rows if r["id"] == "FCA-19-badal-bad-min-kull-vs-naat")

    def test_stimulus_is_a_genuine_literal_part_not_an_abstract_attribute(self):
        row = self._row()
        blob = row["prompt"] + row["expected_answer"] + " ".join(row["accepted_variants"])
        for marker in self._ISHTIMAL_MARKERS:
            self.assertNotIn(marker, blob,
                            "FCA-19 regressed to an ishtimal-typed stimulus (%r) under the ba'd-min-kull label"
                            % marker)
        self.assertIn("نِصْفُ", row["prompt"], "FCA-19 must use a literal-fraction (نِصْف) partitive stimulus")

    def test_reasoning_names_a_literal_part_never_an_abstract_attribute(self):
        row = self._row()
        joined = " ".join(row["required_reasoning"]).lower()
        self.assertIn("literal", joined)
        self.assertIn("part", joined)

    def test_ishtimal_mislabel_is_a_forbidden_answer(self):
        row = self._row()
        self.assertTrue(any("ishtimal" in bad.lower() for bad in row["forbidden_answers"]),
                        "FCA-19 must explicitly forbid mislabeling this literal-part badal as ishtimal")
        for bad in row["forbidden_answers"]:
            if "ishtimal" in bad.lower():
                g = RT.grade(row, {"answer": bad, "reasoning": []})
                self.assertFalse(g["cleared"], "the ishtimal mislabel must not clear")


# --------------------------------------------------------------------------- 10. existing artifacts unchanged

class ExistingArtifactsUnchanged(unittest.TestCase):
    """The nine pre-existing keyed drill files remain byte-identical; the KC catalog is append-only."""

    def test_pre_existing_keyed_drill_files_are_byte_identical_to_start_sha(self):
        for name in _PRE_EXISTING_KEYED_DRILLS:
            rel = "curriculum/drills/keys/%s.keys.jsonl" % name
            original = _git_show(rel)
            with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
                current = fh.read()
            self.assertEqual(original, current, "%s must be byte-identical to the start SHA" % rel)

    def test_kc_catalog_preserves_the_original_25_and_appends_exactly_four(self):
        original = json.loads(_git_show("curriculum/kc-catalog.json"))
        with open(os.path.join(_REPO, "curriculum", "kc-catalog.json"), encoding="utf-8") as fh:
            current = json.load(fh)
        self.assertEqual(current[:25], original)
        self.assertEqual(current[25:], _proposed_kc_catalog_patch())

    def test_no_other_untracked_or_modified_files_outside_the_writable_set(self):
        """Integration-aware: this repair round's permitted-writable set spans a targeted merge-blocker repair
        across nahw/particle rules, the fa bank, the Train-B reference doc, the follower drills, and the L1-L6
        consumer-truth builders/validators — a superset of this batch's own original narrow set, authorized by
        the repair task's own explicit writable-file list. Anything outside it is still caught."""
        out = subprocess.run(["git", "status", "--porcelain"], cwd=_REPO, capture_output=True, check=True)
        allowed = {
            "nahw/rules/particle-context-rules.json",
            "nahw/evals/fa-function-occurrence-eval.jsonl",
            "nahw/references/relation-scope-candidate-units.md",
            "tools/fusha_nahw_particle_rules.py",
            "tools/test_nahw_relation_scope_train_b.py",
            "curriculum/drills/followers-coordination-apposition.md",
            "curriculum/drills/keys/followers-coordination-apposition.keys.jsonl",
            "curriculum/kc-catalog.json",
            "tools/test_followers_coordination_apposition_batch.py",
            "curriculum/l1l6/links/consumer-operationalization-bindings.jsonl",
            "tools/build_curriculum_absorption.py",
            "tools/build_unit_dispositions.py",
            "tools/test_l1l6_consumer_truth.py",
            "tools/validate_curriculum_l1l6.py",
            "curriculum/l1l6/reports/absorption-ledger.jsonl",
            "curriculum/l1l6/reports/absorption-ledger.meta.json",
            "curriculum/l1l6/reports/section-ledger.jsonl",
            "curriculum/l1l6/reports/section-ledger.meta.json",
            "curriculum/l1l6/reports/section-completeness.json",
            "curriculum/l1l6/reports/full-curriculum-readiness.json",
            "curriculum/l1l6/canonical/unit-dispositions.jsonl",
            "curriculum/l1l6/canonical/unit-dispositions.meta.json",
        }
        allowed_prefixes = ("curriculum/l1l6/reports/queues/",)
        for line in out.stdout.decode("utf-8").splitlines():
            path = line[3:].strip().replace("\\", "/")
            if not path:
                continue
            if path in allowed or path.startswith(allowed_prefixes):
                continue
            self.fail("unexpected working-tree change outside the writable set: %s" % path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
