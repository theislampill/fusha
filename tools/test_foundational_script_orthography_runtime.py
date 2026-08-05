#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_foundational_script_orthography_runtime — red-first tests for the L1.M1 foundational-script-orthography
runtime practice bank (tranche-001-runtime).

Proves, in order:
  1. RED: at the batch's own start SHA, curriculum/drills/keys/foundational-script-orthography.keys.jsonl did not
     exist, and none of the seven target kc_ids existed in curriculum/kc-catalog.json.
  2. RED: at the start SHA, none of the 26 target misconception clusters had PRECISE runtime coverage. The four
     definite-article clusters (mc-0003, mc-0228, mc-0477, mc-0556) already had known, broad, indirect coverage
     under the generic kc-clitic-segmentation KC (a real fact, not a gap — that KC is not one of the seven target
     KCs and does not route to this batch's drill); the other 22 clusters had no kc-catalog coverage at all.
  3. GREEN: every one of the 26 current runtime rows resolves to exactly one of the seven target kc_ids, and its
     remediation_route is the batch's own drill.
  4. GREEN: a full-content-correct answer + its own required_reasoning CLEARS and PROMOTES an auto_safe-KC row
     (and only that row's progress state changes, not any other item's).
  5. GREEN: a wrong-reasoning answer is not content_mastered/cleared, and a forbidden answer is a true miss whose
     progress.missed[] entry records the row's own kc_id as error_reason and the row's own remediation_route.
  6. GREEN: the three nunation rows and the four definite-article rows stay two_vote_required, content_mastered,
     held_for_fact_gate, and NEVER cleared, even with a declared agreeing second_check.
  7. GREEN (adversarial): a synthetic kc_id-bearing row bound to a non-auto_safe KC but declaring
     two_vote_required=false is rejected by tools.fusha_tutor_runtime._check_kc_gate_row.
  8. GREEN: none of the 26 rows carry candidate/dr-mc-* provenance, and curriculum/assessment/*.jsonl carries no
     candidate provenance (the assessment quarantine).
  9. GREEN: every one of the 26 rows carries quran_example: null.
  10. GREEN: an ordinary `fusha_tutor_runtime.py --bank <this file> --select` run loads the bank and selects a
      first item cleanly (exit 0, a real next item).

Run: python3 tools/test_foundational_script_orthography_runtime.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_tutor_runtime as RT  # noqa: E402
from tools import validate_drill_keys as VDK  # noqa: E402

_START_SHA = "0ea77694db25ad3d95cf48370468b302f18b625c"
_KEYS_PATH = os.path.join(_REPO, "curriculum", "drills", "keys", "foundational-script-orthography.keys.jsonl")
_DRILL_PATH = os.path.join(_REPO, "curriculum", "drills", "foundational-script-orthography.md")
_CATALOG_PATH = os.path.join(_REPO, "curriculum", "kc-catalog.json")

# the exact seven target KCs and their auto_safe posture (per the tranche-001-runtime mapping).
AUTO_SAFE_KC_IDS = (
    "kc-grapheme-confusables",
    "kc-orthographic-connectivity",
    "kc-short-vowels-and-vocalization-state",
    "kc-sukun-shadda-stack",
    "kc-long-vowel-carrier-role",
)
HELD_KC_IDS = (
    "kc-nunation-written-realization",
    "kc-definite-article-assimilation",
)
ALL_TARGET_KC_IDS = AUTO_SAFE_KC_IDS + HELD_KC_IDS

# the exact 26 misconception clusters, mapped kc_id -> its ids (per the tranche-001-runtime mapping).
KC_MC_MAP = {
    "kc-grapheme-confusables": ["mc-0180", "mc-0253", "mc-0587", "mc-0757"],
    "kc-orthographic-connectivity": ["mc-0099", "mc-0439", "mc-0606", "mc-0618"],
    "kc-short-vowels-and-vocalization-state": ["mc-0233", "mc-0236", "mc-0328", "mc-0558"],
    "kc-sukun-shadda-stack": ["mc-0329", "mc-0475", "mc-0552", "mc-0642"],
    "kc-long-vowel-carrier-role": ["mc-0559", "mc-0614", "mc-0675"],
    "kc-nunation-written-realization": ["mc-0169", "mc-0557", "mc-0895"],
    "kc-definite-article-assimilation": ["mc-0003", "mc-0228", "mc-0477", "mc-0556"],
}
ALL_26_MC_IDS = sorted(mc for ids in KC_MC_MAP.values() for mc in ids)


def _git_show(path_rel, sha=_START_SHA):
    return subprocess.run(["git", "show", "%s:%s" % (sha, path_rel)], cwd=_REPO, capture_output=True)


def _load_rows():
    with open(_KEYS_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _load_catalog():
    with open(_CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class RedFirstStartStateAbsence(unittest.TestCase):
    """1/2: at the batch's own start SHA, the bank and the seven KCs did not exist. Of the 26 target
    misconception clusters, the four definite-article clusters (mc-0003, mc-0228, mc-0477, mc-0556) already had
    KNOWN, BROAD, INDIRECT coverage under the generic kc-clitic-segmentation KC (a real repository fact, not a
    gap); the other 22 clusters had NO kc-catalog coverage anywhere. Neither case is precise runtime coverage:
    the broad KC is not one of the seven target KCs and does not route to this batch's drill, and none of the
    seven target KCs or the new bank existed at all."""

    # the known, pre-existing, broad/indirect KC that already listed the four article clusters at the start SHA.
    _KNOWN_BROAD_INDIRECT_KC_ID = "kc-clitic-segmentation"

    def test_start_sha_is_a_reachable_ancestor_of_the_current_head(self):
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", _START_SHA, "HEAD"],
            cwd=_REPO,
            capture_output=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            "the red-state SHA must be carried by the published branch history so clean CI can replay it",
        )

    def test_bank_file_absent_at_start_sha(self):
        proc = _git_show("curriculum/drills/keys/foundational-script-orthography.keys.jsonl")
        self.assertNotEqual(proc.returncode, 0, "the runtime bank must NOT have existed at the start SHA")

    def test_drill_file_absent_at_start_sha(self):
        proc = _git_show("curriculum/drills/foundational-script-orthography.md")
        self.assertNotEqual(proc.returncode, 0, "the drill file must NOT have existed at the start SHA")

    def test_seven_kc_ids_absent_from_catalog_at_start_sha(self):
        catalog = json.loads(_git_show("curriculum/kc-catalog.json").stdout.decode("utf-8"))
        ids_then = {kc["kc_id"] for kc in catalog}
        self.assertFalse(ids_then & set(ALL_TARGET_KC_IDS),
                         "none of the seven target kc_ids may have existed at the start SHA")

    def test_four_article_clusters_had_only_known_broad_indirect_coverage_at_start_sha(self):
        catalog = json.loads(_git_show("curriculum/kc-catalog.json").stdout.decode("utf-8"))
        by_id = {kc["kc_id"]: kc for kc in catalog}
        broad_kc = by_id.get(self._KNOWN_BROAD_INDIRECT_KC_ID)
        self.assertIsNotNone(broad_kc, "%s must have existed at the start SHA" % self._KNOWN_BROAD_INDIRECT_KC_ID)
        article_ids = set(KC_MC_MAP["kc-definite-article-assimilation"])
        self.assertEqual(article_ids, {"mc-0003", "mc-0228", "mc-0477", "mc-0556"})
        broad_covered = set(broad_kc.get("curriculum_misconception_ids") or [])
        self.assertTrue(article_ids.issubset(broad_covered),
                        "the four article clusters must already have been listed under the known broad/indirect "
                        "%s at the start SHA, got %s" % (self._KNOWN_BROAD_INDIRECT_KC_ID, sorted(article_ids - broad_covered)))
        # the start-SHA coverage was broad/indirect, never this batch's own precise drill or KC.
        self.assertNotEqual(broad_kc.get("drill_route"), "curriculum/drills/foundational-script-orthography.md")
        self.assertNotIn(self._KNOWN_BROAD_INDIRECT_KC_ID, ALL_TARGET_KC_IDS)

    def test_other_22_clusters_lacked_any_coverage_at_start_sha(self):
        catalog = json.loads(_git_show("curriculum/kc-catalog.json").stdout.decode("utf-8"))
        covered_then = set()
        for kc in catalog:
            covered_then.update(kc.get("curriculum_misconception_ids") or [])
        article_ids = set(KC_MC_MAP["kc-definite-article-assimilation"])
        other_22 = set(ALL_26_MC_IDS) - article_ids
        self.assertEqual(len(other_22), 22)
        overlap = covered_then & other_22
        self.assertEqual(overlap, set(),
                         "the other 22 target clusters (everything but the four article clusters) must not have "
                         "had ANY kc-catalog coverage at the start SHA, got overlap: %s" % sorted(overlap))


class BankPresentAndPrecise(unittest.TestCase):
    """3: every one of the 26 rows resolves to exactly one of the seven target KCs, and every KC's
    curriculum_misconception_ids matches the exact mapping given."""

    def test_exactly_26_rows_no_id_reuse(self):
        rows = _load_rows()
        self.assertEqual(len(rows), 26)
        ids = {r["id"] for r in rows}
        self.assertEqual(len(ids), 26, "duplicate runtime ids")
        for rid in ids:
            self.assertFalse(rid.startswith("dr-mc-"), "%r reuses a candidate drill_id identity" % rid)

    def test_every_row_resolves_a_target_kc_and_its_own_remediation_route(self):
        rows = _load_rows()
        for row in rows:
            with self.subTest(id=row["id"]):
                self.assertIn(row.get("kc_id"), ALL_TARGET_KC_IDS)
                self.assertEqual(row["remediation_route"], "curriculum/drills/foundational-script-orthography.md")

    def test_kc_to_row_counts_match_the_exact_mapping(self):
        rows = _load_rows()
        by_kc = {}
        for row in rows:
            by_kc.setdefault(row["kc_id"], []).append(row["id"])
        for kc_id, mc_ids in KC_MC_MAP.items():
            with self.subTest(kc=kc_id):
                self.assertEqual(len(by_kc.get(kc_id, [])), len(mc_ids),
                                "%s: expected %d runtime rows, got %d" % (kc_id, len(mc_ids), len(by_kc.get(kc_id, []))))

    def test_catalog_curriculum_misconception_ids_match_exactly(self):
        catalog = {kc["kc_id"]: kc for kc in _load_catalog()}
        for kc_id, mc_ids in KC_MC_MAP.items():
            with self.subTest(kc=kc_id):
                self.assertIn(kc_id, catalog)
                self.assertEqual(sorted(catalog[kc_id].get("curriculum_misconception_ids") or []), sorted(mc_ids))

    def test_seven_kc_catalog_entries_gate_as_specified(self):
        catalog = {kc["kc_id"]: kc for kc in _load_catalog()}
        for kc_id in AUTO_SAFE_KC_IDS:
            self.assertEqual(catalog[kc_id]["default_gate"], "auto_safe", kc_id)
            self.assertEqual(catalog[kc_id]["drill_route"], "curriculum/drills/foundational-script-orthography.md")
        for kc_id in HELD_KC_IDS:
            self.assertEqual(catalog[kc_id]["default_gate"], "two_vote_required", kc_id)
            self.assertEqual(catalog[kc_id]["drill_route"], "curriculum/drills/foundational-script-orthography.md")

    def test_drill_keys_validator_accepts_the_file_clean(self):
        errs = VDK.validate(_KEYS_PATH)
        self.assertEqual(errs, [])


class AutoSafeRowsClearOnContentAndReasoning(unittest.TestCase):
    """4: a full-content-correct answer + the row's own required_reasoning CLEARS and PROMOTES an auto_safe-KC
    row, and touches only that item's progress state."""

    @classmethod
    def setUpClass(cls):
        cls.rows = [r for r in _load_rows() if r["kc_id"] in AUTO_SAFE_KC_IDS]

    def test_auto_safe_rows_are_not_two_vote_required(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                self.assertFalse(row["two_vote_required"])

    def test_full_correct_answer_clears_and_promotes(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertTrue(g["content_mastered"], row["id"])
                self.assertFalse(g["held_for_fact_gate"], row["id"])
                self.assertTrue(g["cleared"], row["id"])
                self.assertEqual(r["outcome"], "promote", row["id"])

    def test_clearing_one_item_touches_only_that_items_progress_state(self):
        row = self.rows[0]
        other = self.rows[1]
        payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])}
        progress = RT.new_progress()
        RT.apply_event_to_progress(progress, row, RT.step(row, None, payload, now_day=0), seq=0)
        self.assertIn(row["id"], progress["cleared_item_ids"])
        self.assertNotIn(other["id"], progress["cleared_item_ids"])
        self.assertNotIn(other["id"], progress["items"])


class WrongAnswerOrReasonRecordsExactKCAndRemediation(unittest.TestCase):
    """5: wrong reasoning fails mastery; a forbidden answer is a true miss whose progress.missed[] entry records
    the row's OWN kc_id as error_reason and the row's OWN remediation_route."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _load_rows()

    def test_right_answer_wrong_reasoning_is_not_mastered_or_cleared(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["expected_answer"], "reasoning": ["it just sounds right"]}
                r = RT.step(row, None, payload, now_day=0)
                self.assertFalse(r["grade"]["content_mastered"], row["id"])
                self.assertFalse(r["grade"]["cleared"], row["id"])

    def test_forbidden_answer_is_a_true_miss_recording_exact_kc_and_remediation(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                payload = {"answer": row["forbidden_answers"][0], "reasoning": []}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertFalse(g["cleared"], row["id"])
                self.assertFalse(g["held_for_fact_gate"], row["id"])
                progress = RT.new_progress()
                RT.apply_event_to_progress(progress, row, r, seq=0)
                missed = {m["item_id"]: m for m in progress["missed"]}
                self.assertIn(row["id"], missed, row["id"])
                self.assertEqual(missed[row["id"]]["error_reason"], row["kc_id"])
                self.assertEqual(missed[row["id"]]["remediation_route"], row["remediation_route"])


class NunationAndArticleRowsRemainHeld(unittest.TestCase):
    """6: the three nunation rows and four article rows are content_mastered but held_for_fact_gate, NEVER
    cleared, even with a declared agreeing second_check."""

    @classmethod
    def setUpClass(cls):
        cls.rows = [r for r in _load_rows() if r["kc_id"] in HELD_KC_IDS]

    def test_exactly_seven_held_rows_three_nunation_four_article(self):
        by_kc = {}
        for row in self.rows:
            by_kc.setdefault(row["kc_id"], []).append(row["id"])
        self.assertEqual(len(by_kc.get("kc-nunation-written-realization", [])), 3)
        self.assertEqual(len(by_kc.get("kc-definite-article-assimilation", [])), 4)

    def test_held_rows_are_two_vote_required(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                self.assertTrue(row["two_vote_required"])

    def test_full_correct_content_plus_declared_second_check_still_holds(self):
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


class NonAutoSafeKCWithFalseTwoVoteIsRejected(unittest.TestCase):
    """7 (adversarial): a synthetic row bound to a real non-auto_safe KC that declares two_vote_required=false
    must be rejected by the catalog-gate check."""

    def test_synthetic_wrong_gate_row_is_rejected(self):
        catalog_by_id = {kc["kc_id"]: kc for kc in _load_catalog()}
        bad_row = {
            "id": "SYN-BAD-GATE", "level": "1", "concept": "adversarial fixture",
            "prompt": "x", "quran_example": None, "expected_answer": "y",
            "accepted_variants": ["y"], "forbidden_answers": ["z"], "required_reasoning": ["r"],
            "sarf_procedure": None, "nahw_procedure": None,
            "remediation_route": "curriculum/drills/foundational-script-orthography.md",
            "two_vote_required": False,  # WRONG: kc-definite-article-assimilation is two_vote_required, not auto_safe
            "kc_id": "kc-definite-article-assimilation",
        }
        failures = RT._check_kc_gate_row(bad_row, kc_by_id=catalog_by_id)
        self.assertTrue(failures, "a non-auto_safe KC row with two_vote_required=false must be rejected")
        self.assertIn("must be two_vote_required", failures[0])

    def test_synthetic_correct_gate_auto_safe_row_is_accepted(self):
        catalog_by_id = {kc["kc_id"]: kc for kc in _load_catalog()}
        good_row = {
            "id": "SYN-GOOD-GATE", "level": "1", "concept": "adversarial fixture",
            "prompt": "x", "quran_example": None, "expected_answer": "y",
            "accepted_variants": ["y"], "forbidden_answers": ["z"], "required_reasoning": ["r"],
            "sarf_procedure": None, "nahw_procedure": None,
            "remediation_route": "curriculum/drills/foundational-script-orthography.md",
            "two_vote_required": False,
            "kc_id": "kc-grapheme-confusables",
        }
        failures = RT._check_kc_gate_row(good_row, kc_by_id=catalog_by_id)
        self.assertEqual(failures, [])

    def test_real_batch_rows_all_pass_the_catalog_gate_check(self):
        catalog_by_id = {kc["kc_id"]: kc for kc in _load_catalog()}
        for row in _load_rows():
            with self.subTest(id=row["id"]):
                self.assertEqual(RT._check_kc_gate_row(row, kc_by_id=catalog_by_id), [])


class ProvenanceBoundary(unittest.TestCase):
    """8: no candidate/dr-mc-* provenance in any runtime row, and the assessment quarantine holds."""

    _MARKERS = ("dr-mc-", "candidate_id", "candidate_drill_id", "curriculum_l1l6_id",
               "candidate_provenance", "source_misconception")

    def test_no_candidate_provenance_marker_in_runtime_rows(self):
        for row in _load_rows():
            blob = json.dumps(row, ensure_ascii=False)
            for marker in self._MARKERS:
                self.assertNotIn(marker, blob, "%s: candidate provenance marker %r leaked" % (row["id"], marker))

    def test_assessment_banks_carry_no_candidate_provenance(self):
        self.assertEqual(VDK.assessment_quarantine_violations(), [])


class QuranExampleAllNull(unittest.TestCase):
    """9: every one of the 26 rows carries quran_example: null (no occurrence claim in this batch)."""

    def test_all_26_rows_quran_example_null(self):
        for row in _load_rows():
            with self.subTest(id=row["id"]):
                self.assertIsNone(row["quran_example"])


class OrdinaryRuntimeLoadsTheBank(unittest.TestCase):
    """10: an ordinary `fusha_tutor_runtime.py --bank <this file> --select` run loads the bank cleanly."""

    def test_bank_loads_via_load_bank(self):
        rows = RT.load_bank(_KEYS_PATH)
        self.assertEqual(len(rows), 26)

    def test_cli_select_over_the_bank_exits_clean_and_names_a_real_item(self):
        argv = ["--bank", _KEYS_PATH, "--select", "--now", "0"]
        import io
        old_argv, old_out = sys.argv, sys.stdout
        try:
            sys.argv = ["fusha_tutor_runtime.py"] + argv
            sys.stdout = io.StringIO()
            rc = RT.main()
            out = sys.stdout.getvalue()
        finally:
            sys.argv, sys.stdout = old_argv, old_out
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        ids = {r["id"] for r in _load_rows()}
        self.assertIn(payload["next"], ids)
        self.assertEqual(payload["reason"], "new_item")


class F2ExactDiacriticContractGuard(unittest.TestCase):
    """F2: every row whose authored correct form and an authored forbidden form collide under the lenient
    recall normalizer (differ ONLY by a vowel/shadda diacritic) must opt into `exact_surface_forms`, and the
    exact contract must actually reject that colliding forbidden form while still accepting the gold form."""

    def test_every_diacritic_colliding_row_declares_exact_surface_forms(self):
        missing = [row["id"] for row in _load_rows()
                  if RT.diacritic_only_collision(row) and not row.get("exact_surface_forms")]
        self.assertEqual(missing, [],
                         "rows whose expected/forbidden collide under the lenient normalizer (differ only by "
                         "diacritics) but do not declare exact_surface_forms: %s" % missing)

    def test_exact_surface_forms_rows_reject_a_token_level_hostile_substitution(self):
        """R7: token-level hostile substitution -- for every row that authored a forbidden_answers TOKEN
        colliding with one of its own declared exact_surface_forms under the lenient normalizer, substitute
        that REAL authored hostile token into the REAL gold answer and assert the real grader rejects it.
        Replaces the vacuous whole-sentence membership check, which compared an entire forbidden_answers
        sentence's normalized text against an entire expected_answer/accepted_variant and so never fired."""
        for row in _load_rows():
            if not row.get("exact_surface_forms") or row.get("exact_surface_forms_mode", "all") != "all":
                continue
            for gold, hostile in RT.exact_surface_hostile_pairs(row):
                hostile_answer = row["expected_answer"].replace(gold, hostile)
                with self.subTest(id=row["id"], gold=gold, hostile=hostile):
                    self.assertNotEqual(hostile_answer, row["expected_answer"])
                    g = RT.grade(row, {"answer": hostile_answer, "reasoning": list(row["required_reasoning"])})
                    self.assertFalse(g["passed"],
                                    "%s: exact_surface_forms must reject the token-level hostile substitution "
                                    "%r -> %r" % (row["id"], gold, hostile))

    def test_conjunctive_multiform_rows_require_every_declared_surface(self):
        """R1: a row with >=2 exact_surface_forms and mode 'all' (the default) must reject an answer dropping
        one of the declared surfaces. This bank currently authors no such multi-form row, so the loop is
        expected to be a no-op today; it stays live so a future conjunctive row is covered automatically."""
        for row in _load_rows():
            forms = row.get("exact_surface_forms") or []
            if len(forms) < 2 or row.get("exact_surface_forms_mode", "all") != "all":
                continue
            partial = row["expected_answer"]
            for missing in forms[1:]:
                partial = partial.replace(missing, "")
            with self.subTest(id=row["id"]):
                self.assertNotEqual(partial, row["expected_answer"])
                g = RT.grade(row, {"answer": partial, "reasoning": list(row["required_reasoning"])})
                self.assertFalse(g["passed"], "%s: dropping a required conjunctive surface must fail "
                                              "exact_surface_forms" % row["id"])

    def test_exact_surface_forms_rows_still_accept_their_own_gold_form(self):
        for row in _load_rows():
            if not row.get("exact_surface_forms"):
                continue
            with self.subTest(id=row["id"]):
                g = RT.grade(row, {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])})
                self.assertTrue(g["passed"], "%s: exact_surface_forms must still accept the gold answer" % row["id"])


class F7DotlessFinalYaaConventionScoped(unittest.TestCase):
    """F7: the dotless-final-yāʾ-as-alif-maqṣūra default (FSO-17) is a real orthographic CONVENTION (some
    typesetting/regional conventions dot the final yāʾ in both roles), not a universal fact. It must be scoped
    to an explicit, named, closed convention rather than asserted as an unconditional default, and it must stay
    bound to its existing KC's own gate (kc-long-vowel-carrier-role is auto_safe; scoping the claim, not flipping
    the gate, is how this row documents its runtime posture without creating a KC-gate mismatch)."""

    def _row(self):
        return {r["id"]: r for r in _load_rows()}["FSO-17-alif-maqsura-not-yaa"]

    def test_fso17_names_its_governing_convention_explicitly(self):
        row = self._row()
        blob = (row["prompt"] + row["expected_answer"] + " ".join(row.get("accepted_variants") or [])).lower()
        self.assertIn("convention", blob,
                     "FSO-17 must document the runtime posture as an explicit, named convention")
        self.assertIn("uthmani", blob,
                     "FSO-17 must name the specific closed convention it assumes, not just say 'convention'")

    def test_fso17_uses_the_safe_narrowed_label_not_the_overbroad_standard_modern_print_claim(self):
        # R5: "standard modern-print" overgeneralizes -- most contemporary Arabic typesetting outside the
        # Uthmani/Egyptian-print tradition DOES distinguish dotted yaa from dotless alif maqsura. The safe,
        # independently-agreed label is "Qur'anic Uthmani / Egyptian-style print convention".
        row = self._row()
        blob = (row["prompt"] + row["expected_answer"] + " ".join(row.get("accepted_variants") or [])).lower()
        self.assertNotIn("standard modern-print", blob,
                         "FSO-17 must not claim 'standard modern-print' leaves the final yāʾ dotless -- most "
                         "modern typesetting outside Uthmani/Egyptian print distinguishes the two graphemes")
        self.assertIn("egyptian", blob,
                     "FSO-17 must name the safe narrowed label (Qur'anic Uthmani / Egyptian-style print "
                     "convention)")

    def test_fso17_rejects_a_universal_every_convention_overclaim(self):
        row = self._row()
        g = RT.grade(row, {"answer": "any yāʾ-shaped grapheme at the end of a word is always a long ī, in "
                                     "every Arabic typesetting convention",
                          "reasoning": list(row["required_reasoning"])})
        self.assertFalse(g["content_mastered"],
                         "FSO-17 must reject the claim that the a-spelling default holds in every convention")

    def test_fso17_stays_consistent_with_its_own_auto_safe_kc_gate(self):
        row = self._row()
        self.assertEqual(row["kc_id"], "kc-long-vowel-carrier-role")
        self.assertFalse(row["two_vote_required"],
                         "FSO-17's KC (kc-long-vowel-carrier-role) is auto_safe; scope the claim to a named "
                         "convention instead of creating a KC-gate mismatch by flipping two_vote_required alone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
