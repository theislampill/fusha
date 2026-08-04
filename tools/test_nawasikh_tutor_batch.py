#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_nawasikh_tutor_batch — red-first tests for the Train B/C L2.M2 nawāsikh runtime-practice batch.

Proves, in order:
  1. The exact 25-row L2.M2 candidate manifest (dr-mc-0114 .. dr-mc-0747, across L2.M2.01-06) exists unchanged
     in curriculum/l1l6/drills-candidates/drill-candidates.jsonl, still `status: candidate_not_runtime_integrated`
     — this batch never claims those rows were promoted.
  2. curriculum/drills/keys/nawasikh-governor-families.keys.jsonl carries exactly 25 NEWLY authored runtime rows
     whose ids never reuse a dr-mc-* identity, each with quran_example:null and two_vote_required:true.
  3. Every runtime row round-trips through the ordinary tutor grader (tools.fusha_tutor_runtime): a full-content
     correct answer is content_mastered=True, held_for_fact_gate=True, cleared=False, outcome='hold' — and never
     enters progress.missed. A right answer with WRONG reasoning fails (not content_mastered, not cleared). A
     genuinely wrong answer is a true miss and routes to local remediation.
  4. Candidate provenance (drill_id / dr-mc-*/mc-* ids / curriculum_l1l6_id) is absent from every runtime row and
     from every assessment bank (the quarantine tools.validate_drill_keys already enforces, re-asserted here for
     this batch specifically).
  5. The existing 14 kc_id-bearing runtime key rows (across the four pre-existing keyed drills) and the seven
     KCs they are bound to are BYTE-IDENTICAL to the batch's start SHA — this batch adds a new file; it does not
     touch any pre-existing key row or KC.

Run: python3 tools/test_nawasikh_tutor_batch.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_tutor_runtime as RT  # noqa: E402
from tools import validate_drill_keys as VDK  # noqa: E402

_START_SHA = "4d2346fa8cf942283cf40ab1ebb9e343dc461e07"
_CANDIDATE_PATH = os.path.join(_REPO, "curriculum", "l1l6", "drills-candidates", "drill-candidates.jsonl")
_KEYS_PATH = os.path.join(_REPO, "curriculum", "drills", "keys", "nawasikh-governor-families.keys.jsonl")

# the exact 25 source candidate ids, grouped by lesson exactly as specified.
LESSON_CANDIDATE_IDS = {
    "L2.M2.01": ["dr-mc-0114", "dr-mc-0420", "dr-mc-0454", "dr-mc-0678", "dr-mc-0834"],
    "L2.M2.02": ["dr-mc-0191", "dr-mc-0421", "dr-mc-0784", "dr-mc-0829"],
    "L2.M2.03": ["dr-mc-0333", "dr-mc-0409", "dr-mc-0460", "dr-mc-0535"],
    "L2.M2.04": ["dr-mc-0410", "dr-mc-0461", "dr-mc-0858", "dr-mc-0871"],
    "L2.M2.05": ["dr-mc-0032", "dr-mc-0270", "dr-mc-0450", "dr-mc-0751"],
    "L2.M2.06": ["dr-mc-0018", "dr-mc-0043", "dr-mc-0694", "dr-mc-0747"],
}
ALL_CANDIDATE_IDS = [i for ids in LESSON_CANDIDATE_IDS.values() for i in ids]

# the four pre-existing keyed drills carrying kc_id rows (Train C) — the "14 runtime key rows / seven KCs"
# this batch must leave byte-identical (verified against the batch's own start SHA below).
_PRE_EXISTING_KEYED_DRILLS = ("hover-composition-and-routing", "parse-key-and-color-layer",
                              "quranic-function-words", "root-pattern-practice")


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


class CandidateManifestUnchanged(unittest.TestCase):
    """The 25 source candidate rows exist, are unchanged in status, and were never claimed as promoted."""

    def test_exact_25_row_manifest_present_across_six_lessons(self):
        rows = _load_candidate_rows()
        self.assertEqual(len(ALL_CANDIDATE_IDS), 25)
        self.assertEqual(set(rows), set(ALL_CANDIDATE_IDS), "the candidate manifest must match exactly")
        self.assertEqual(len(LESSON_CANDIDATE_IDS), 6, "six lessons L2.M2.01..06")

    def test_candidate_rows_still_candidate_not_runtime_integrated(self):
        rows = _load_candidate_rows()
        for drill_id, row in rows.items():
            self.assertEqual(row.get("status"), "candidate_not_runtime_integrated",
                            "%s must never be marked promoted by this batch" % drill_id)

    def test_direct_unit_links_present_across_the_batch(self):
        required_units = {"u-n01", "u-n02", "u-n03", "u-n04", "u-n07", "u-n10", "u-s06", "u-s09"}
        rows = _load_candidate_rows()
        seen = set()
        for row in rows.values():
            seen.update(row.get("unit_links") or [])
        self.assertTrue(required_units.issubset(seen), "missing unit links: %s" % (required_units - seen))


class RuntimeBatchManifest(unittest.TestCase):
    """The 25 newly authored runtime rows: correct count, no dr-mc-* id reuse, quran_example null, two-vote."""

    def test_exactly_25_runtime_rows_no_id_reuse(self):
        rows = _load_runtime_rows()
        self.assertEqual(len(rows), 25)
        ids = {r["id"] for r in rows}
        self.assertEqual(len(ids), 25, "duplicate runtime ids")
        for rid in ids:
            self.assertFalse(rid.startswith("dr-mc-"), "%r reuses a candidate drill_id identity" % rid)

    def test_every_row_quran_example_null_and_two_vote_required(self):
        for row in _load_runtime_rows():
            self.assertIsNone(row["quran_example"], "%s: quran_example must be null (no occurrence claim)" % row["id"])
            self.assertTrue(row["two_vote_required"], "%s: must be two_vote_required" % row["id"])

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

    def test_drill_keys_validator_accepts_the_file_clean(self):
        errs = VDK.validate(_KEYS_PATH)
        self.assertEqual(errs, [])


class RuntimeGraderRoundTrip(unittest.TestCase):
    """Every one of the 25 rows round-trips through tools.fusha_tutor_runtime.grade()/step()."""

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

    def test_right_answer_wrong_reasoning_fails(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                # substitute plausible-but-empty reasoning: the row's own required_reasoning is withheld.
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

    def test_a_forbidden_answer_is_a_true_miss_routed_to_local_remediation(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["forbidden_answers"][0], "reasoning": []}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertFalse(g["cleared"], row["id"])
                self.assertFalse(g["held_for_fact_gate"], "%s: a forbidden answer is a real miss, not a fact hold" % row["id"])
                progress = RT.new_progress()
                RT.apply_event_to_progress(progress, row, r, seq=0)
                missed = {m["item_id"]: m for m in progress["missed"]}
                self.assertIn(row["id"], missed, row["id"])
                self.assertEqual(missed[row["id"]]["remediation_route"], row["remediation_route"])


def _case_swap(text):
    """Generate a hostile REVERSE-DIRECTION rewrite: swap every occurrence of 'nominative' <-> 'accusative'
    in place, leaving every other word (ism/khabar/agent/complements/etc.) exactly where it was. This is
    mechanically the exact case swap a direction-sensitive row teaches against (kana/inna mirror-image,
    ism-vs-khabar, agent-vs-complement) -- same bag of words, same order of every non-case-word token, only
    the case LABELS at each slot are reversed."""
    placeholder = "\x00NOMINATIVE\x00"
    swapped = re.sub(r"nominative", placeholder, text, flags=re.I)
    swapped = re.sub(r"accusative", "nominative", swapped, flags=re.I)
    return swapped.replace(placeholder, "accusative")


class DirectionSensitiveCaseSwapIsRejected(unittest.TestCase):
    """RED-first (Opus finding 1): a direction-sensitive row must never mastery-clear the exact case-swapped
    rewrite of its own expected_answer -- swapping nominative<->accusative in place is the precise mirror-image
    mistake the row exists to catch (kana/inna ism-khabar mirror, single-slot kana/inna correction, qalb-verb
    split-vs-both, agent-vs-complement). `ordered_slots` is the row-authored marker of "this row's answer
    matching is direction-sensitive"; every row that carries it must reject its own case-swapped rewrite."""

    def test_ordered_slots_rows_reject_their_own_case_swapped_rewrite(self):
        direction_sensitive = [row for row in _load_runtime_rows() if row.get("ordered_slots")]
        # sanity: this is not a vacuous test -- the batch actually authored ordered_slots-bearing rows.
        self.assertGreaterEqual(len(direction_sensitive), 8,
                                "expected several direction-sensitive (ordered_slots-bearing) rows in the batch")
        for row in direction_sensitive:
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
        # the fix must not weaken token/reason grading: every authored expected_answer/accepted_variant for a
        # direction-sensitive row must still round-trip to content_mastered=True.
        direction_sensitive = [row for row in _load_runtime_rows() if row.get("ordered_slots")]
        for row in direction_sensitive:
            forms = [row["expected_answer"]] + list(row.get("accepted_variants") or [])
            for form in forms:
                with self.subTest(id=row["id"], form=form[:40]):
                    payload = {"answer": form, "reasoning": list(row["required_reasoning"])}
                    r = RT.step(row, None, payload, now_day=0)
                    self.assertTrue(r["grade"]["content_mastered"],
                                    "%s: authored correct form must still be mastered: %r" % (row["id"], form))


class ProvenanceBoundary(unittest.TestCase):
    """Candidate provenance never enters the runtime-visible artifacts or any assessment bank."""

    _MARKERS = ("dr-mc-", "misconception_id", "candidate_id", "candidate_drill_id", "curriculum_l1l6_id",
               "candidate_provenance", "source_misconception")

    def test_no_candidate_provenance_field_or_id_in_runtime_rows(self):
        for row in _load_runtime_rows():
            for marker in self._MARKERS:
                self.assertNotIn(marker, json.dumps(row, ensure_ascii=False),
                                "%s: candidate provenance marker %r leaked" % (row["id"], marker))

    def test_assessment_banks_carry_no_candidate_provenance(self):
        errs = VDK.assessment_quarantine_violations()
        self.assertEqual(errs, [])


class ExistingRuntimeKeyRowsUnchanged(unittest.TestCase):
    """The 14 pre-existing kc_id-bearing rows (across the four keyed drills) and their seven KCs are
    byte-identical to the batch's start SHA — verified by content, not by row-count alone."""

    def test_pre_existing_keyed_drill_files_are_byte_identical_to_start_sha(self):
        for name in _PRE_EXISTING_KEYED_DRILLS:
            rel = "curriculum/drills/keys/%s.keys.jsonl" % name
            original = _git_show(rel)
            with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
                current = fh.read()
            self.assertEqual(original, current, "%s must be byte-identical to the start SHA" % rel)

    def test_exactly_14_rows_bound_to_exactly_seven_kcs_at_start_sha_and_now(self):
        n_rows, kc_ids = 0, set()
        for name in _PRE_EXISTING_KEYED_DRILLS:
            rows = _load_jsonl_text(_git_show("curriculum/drills/keys/%s.keys.jsonl" % name))
            for r in rows:
                if r.get("kc_id"):
                    n_rows += 1
                    kc_ids.add(r["kc_id"])
        self.assertEqual(n_rows, 14)
        self.assertEqual(len(kc_ids), 7)

    def test_those_seven_kcs_are_unchanged_in_the_catalog(self):
        original_catalog = {k["kc_id"]: k for k in json.loads(_git_show("curriculum/kc-catalog.json"))}
        with open(os.path.join(_REPO, "curriculum", "kc-catalog.json"), encoding="utf-8") as fh:
            current_catalog = {k["kc_id"]: k for k in json.load(fh)}
        seven = set()
        for name in _PRE_EXISTING_KEYED_DRILLS:
            for r in _load_jsonl_text(_git_show("curriculum/drills/keys/%s.keys.jsonl" % name)):
                if r.get("kc_id"):
                    seven.add(r["kc_id"])
        self.assertEqual(len(seven), 7)
        for kc_id in seven:
            self.assertEqual(original_catalog[kc_id], current_catalog[kc_id],
                            "%s must be unchanged from the start SHA" % kc_id)

    def test_original_20_kc_catalog_entries_are_all_still_present_unchanged(self):
        original = json.loads(_git_show("curriculum/kc-catalog.json"))
        with open(os.path.join(_REPO, "curriculum", "kc-catalog.json"), encoding="utf-8") as fh:
            current_catalog = {k["kc_id"]: k for k in json.load(fh)}
        self.assertEqual(len(original), 20)
        for kc in original:
            self.assertEqual(current_catalog.get(kc["kc_id"]), kc,
                            "%s must be unchanged from the start SHA" % kc["kc_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
