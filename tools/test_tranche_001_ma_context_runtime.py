#!/usr/bin/env python3
"""Red-first tests for tranche-001 T1 coherent ordinary-tutor coverage of the CONTEXTUAL مَا family.

Pins the exact 49 misconception ids named by this batch, grouped into 14 coherent same-surface-مَا
diagnostics (masdariyya-vs-relative substitution, hijaziyya/tamimiyya nullifiers, the أَمَّا kaffa+fāʾ-
al-jawāb frame, exclamatory-vs-interrogative case, the negated-possession lām+subjunctive frame, the
لَمَّا jazm-vs-temporal rival pair, the ما زال kāna-sister family, the idiomatic ما دام frame, plain ما
النافية with no mood government, the interrogative مَا alif-elision after a preposition, the relative/
masdariyya مَا retained-alif preposition government, the مَا-vs-مَن rational-referent split, the إنّما
kaffa restriction-scope frame, and لَمَّا's own tense-selection requirement) — every one of them a
distinct occurrence-bound resolution of the SAME written مَا, per the round's linguistic contract. It
verifies the 49 ids against the COMMITTED public evidence they must reverse-trace to:
curriculum/l1l6/drills-candidates/drill-candidates.jsonl (per-misconception drill candidate spec, never
trusted without independent re-verification) and curriculum/l1l6/misconceptions/misconception-registry.jsonl
(per-misconception disposition/violated-capability record).

The batch must then produce three NEW, currently-absent artifacts:
  * curriculum/drills/keys/tranche-001-ma-context-runtime.keys.jsonl — exactly 49 ORIGINAL ordinary
    fusha_tutor_runtime rows (never copied from the candidate specs), one primary row per misconception id
    (T1MC-01..T1MC-49), every row two_vote_required, occurrence-neutral (quran_example: null) and
    public-ineligible, covering every one of the 49 target ids and no id outside that set.
  * curriculum/drills/tranche-001-ma-context-runtime.md — the lesson/remediation surface every row's
    remediation_route must point at.
  * a coherent family of 14 NEW KCs appended to the combined KC catalog (via
    curriculum/kc-catalog.d/tranche-001-ma-context.jsonl, an append-safe shard), with non-overlapping
    curriculum_misconception_ids coverage that exactly partitions the 49 target ids, each gated
    non-auto_safe (so every row stays two-vote held, never auto-cleared).

This file is RED by construction: none of the three artifacts exist yet, so every test below either fails on
a missing path or (for the source-truth class) exercises only what is ALREADY committed. Runtime behaviour is
checked through the REAL tools/fusha_tutor_runtime.py and tools/validate_drill_keys.py interfaces (never a
reimplementation of that grading/validation logic).
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tools/ itself, so "import fusha_tutor_runtime" works
import kc_catalog

DRILL_CANDIDATES = _REPO / "curriculum" / "l1l6" / "drills-candidates" / "drill-candidates.jsonl"
MISCONCEPTIONS = _REPO / "curriculum" / "l1l6" / "misconceptions" / "misconception-registry.jsonl"
NEW_BANK = _REPO / "curriculum" / "drills" / "keys" / "tranche-001-ma-context-runtime.keys.jsonl"
NEW_BANK_NAME = "tranche-001-ma-context-runtime.keys.jsonl"
NEW_BANK_REL = "curriculum/drills/keys/tranche-001-ma-context-runtime.keys.jsonl"
NEW_LESSON = _REPO / "curriculum" / "drills" / "tranche-001-ma-context-runtime.md"
NEW_LESSON_REL = "curriculum/drills/tranche-001-ma-context-runtime.md"
NEW_SHARD = _REPO / "curriculum" / "kc-catalog.d" / "tranche-001-ma-context.jsonl"
REMEDIATION_INDEX = _REPO / "curriculum" / "drills" / "dogfood-error-remediation-index.md"
MISSED_ERROR_LOG_TEMPLATE = _REPO / "curriculum" / "progress" / "missed-error-log.template.md"

# ---------------------------------------------------------------------------
# the 14 KC families: kc_id -> ordered list of misconception ids (ascending numeric within family). Family order
# below is also the ROW_PLAN order (T1MC-01.. assigned family-by-family, ascending numeric within a family).
# ---------------------------------------------------------------------------
KC_MASDARIYYA = "kc-t1-ma-context-masdariyya-verbal-noun-substitution"
KC_HIJAZIYYA = "kc-t1-ma-context-hijaziyya-tamimiyya-nullifiers"
KC_AMMA_KAFFA = "kc-t1-ma-context-amma-kaffa-jawab-fa"
KC_EXCLAM_INTERROG = "kc-t1-ma-context-exclamatory-interrogative-case"
KC_POSSESSION_LAM = "kc-t1-ma-context-negated-possession-lam-subjunctive"
KC_LAMMA_RIVAL = "kc-t1-ma-context-lamma-jazm-vs-temporal-rival"
KC_MA_ZALA = "kc-t1-ma-context-ma-zala-kana-sister-government"
KC_MA_DAMA = "kc-t1-ma-context-ma-dama-temporal-not-negation"
KC_NAFIYA_NO_MOOD = "kc-t1-ma-context-ma-nafiya-no-mood-government"
KC_ALIF_ELISION = "kc-t1-ma-context-istifham-alif-elision-preposition"
KC_RELATIVE_MAJRUR = "kc-t1-ma-context-relative-preposition-majrur-government"
KC_MA_VS_MAN = "kc-t1-ma-context-ma-vs-man-rational-referent"
KC_INNAMA_KAFFA = "kc-t1-ma-context-innama-kaffa-restriction-scope"
KC_LAMMA_TENSE = "kc-t1-ma-context-lamma-jazm-requires-mudari"

FAMILIES = {
    KC_MASDARIYYA: ["mc-0142", "mc-0310", "mc-0463", "mc-0469", "mc-0882"],
    KC_HIJAZIYYA: ["mc-0223", "mc-0418", "mc-0626", "mc-0826", "mc-0827"],
    KC_AMMA_KAFFA: ["mc-0258", "mc-0411", "mc-0486", "mc-0777", "mc-0874"],
    KC_EXCLAM_INTERROG: ["mc-0252", "mc-0562", "mc-0567", "mc-0800"],
    KC_POSSESSION_LAM: ["mc-0257", "mc-0435", "mc-0436", "mc-0904"],
    KC_LAMMA_RIVAL: ["mc-0367", "mc-0660", "mc-0850", "mc-0861"],
    KC_MA_ZALA: ["mc-0412", "mc-0413", "mc-0462", "mc-0828"],
    KC_MA_DAMA: ["mc-0006", "mc-0591", "mc-0763"],
    KC_NAFIYA_NO_MOOD: ["mc-0198", "mc-0579", "mc-0851"],
    KC_ALIF_ELISION: ["mc-0363", "mc-0659", "mc-0685"],
    KC_RELATIVE_MAJRUR: ["mc-0401", "mc-0516", "mc-0687"],
    KC_MA_VS_MAN: ["mc-0527", "mc-0565", "mc-0847"],
    KC_INNAMA_KAFFA: ["mc-0470", "mc-0831"],
    KC_LAMMA_TENSE: ["mc-0264"],
}
FAMILY_ORDER = list(FAMILIES)  # dict preserves insertion order (py3.7+)
NEW_KC_IDS = list(FAMILY_ORDER)

TARGET_IDS = sorted((mc for ids in FAMILIES.values() for mc in ids), key=lambda s: int(s.split("-")[1]))

# exact capability_link / related_units / manifested-lesson contract, re-verified against the committed
# candidate + registry files below (never trusted from this table alone).
CAPS_UNITS_LESSONS = {
    'mc-0142': (frozenset(['discriminator_table', 'inc-derivatives', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-s02', 'u-s03', 'u-s05']), frozenset(['L3.M4.08'])),
    'mc-0310': (frozenset(['discriminator_table', 'inc-derivatives', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-s02', 'u-s03', 'u-s05']), frozenset(['L3.M4.08'])),
    'mc-0463': (frozenset(['discriminator_table', 'inc-derivatives', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-s02', 'u-s03', 'u-s05']), frozenset(['L3.M4.08'])),
    'mc-0469': (frozenset(['discriminator_table', 'inc-derivatives', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-s02', 'u-s03', 'u-s05']), frozenset(['L3.M4.08'])),
    'mc-0882': (frozenset(['discriminator_table', 'inc-derivatives', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-s02', 'u-s03', 'u-s05']), frozenset(['L3.M4.08'])),
    'mc-0223': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-n11']), frozenset(['L4.M2.04'])),
    'mc-0418': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-n11']), frozenset(['L4.M2.04'])),
    'mc-0626': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-n11']), frozenset(['L4.M2.04'])),
    'mc-0826': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-n11']), frozenset(['L4.M2.04'])),
    'mc-0827': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n07', 'u-n11']), frozenset(['L4.M2.04'])),
    'mc-0258': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'inc-pedagogy', 'licensing_table']), frozenset(['u-n01', 'u-n06', 'u-n07', 'u-n08', 'u-n12']), frozenset(['L3.M4.04'])),
    'mc-0411': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'inc-pedagogy', 'licensing_table']), frozenset(['u-n01', 'u-n06', 'u-n07', 'u-n08', 'u-n12']), frozenset(['L3.M4.04'])),
    'mc-0486': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'inc-pedagogy', 'licensing_table']), frozenset(['u-n01', 'u-n06', 'u-n07', 'u-n08', 'u-n12']), frozenset(['L3.M4.04'])),
    'mc-0777': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'inc-pedagogy', 'licensing_table']), frozenset(['u-n01', 'u-n06', 'u-n07', 'u-n08', 'u-n12']), frozenset(['L3.M4.04'])),
    'mc-0874': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'inc-pedagogy', 'licensing_table']), frozenset(['u-n01', 'u-n06', 'u-n07', 'u-n08', 'u-n12']), frozenset(['L3.M4.04'])),
    'mc-0252': (frozenset(['inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n04', 'u-n07']), frozenset(['L4.M5.10'])),
    'mc-0562': (frozenset(['inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n04', 'u-n07']), frozenset(['L4.M5.10'])),
    'mc-0567': (frozenset(['inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n04', 'u-n07']), frozenset(['L4.M5.10'])),
    'mc-0800': (frozenset(['inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n04', 'u-n07']), frozenset(['L4.M5.10'])),
    'mc-0257': (frozenset(['inc-ma', 'inc-negation', 'inc-ownership']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s09']), frozenset(['L4.M3.07'])),
    'mc-0435': (frozenset(['inc-ma', 'inc-negation', 'inc-ownership']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s09']), frozenset(['L4.M3.07'])),
    'mc-0436': (frozenset(['inc-ma', 'inc-negation', 'inc-ownership']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s09']), frozenset(['L4.M3.07'])),
    'mc-0904': (frozenset(['inc-ma', 'inc-negation', 'inc-ownership']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s09']), frozenset(['L4.M3.07'])),
    'mc-0367': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s06']), frozenset(['L2.M1.04'])),
    'mc-0660': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s06']), frozenset(['L2.M1.04'])),
    'mc-0850': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s06']), frozenset(['L2.M1.04'])),
    'mc-0861': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-s06']), frozenset(['L2.M1.04'])),
    'mc-0412': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L2.M5.02'])),
    'mc-0413': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L2.M5.02'])),
    'mc-0462': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L2.M5.02'])),
    'mc-0828': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L2.M5.02'])),
    'mc-0006': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L6.M4.06'])),
    'mc-0591': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L6.M4.06'])),
    'mc-0763': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07']), frozenset(['L6.M4.06'])),
    'mc-0198': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n03', 'u-n07']), frozenset(['L1.M5.07'])),
    'mc-0579': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n03', 'u-n07']), frozenset(['L1.M5.07'])),
    'mc-0851': (frozenset(['discriminator_table', 'inc-ma', 'inc-negation']), frozenset(['u-n01', 'u-n03', 'u-n07']), frozenset(['L1.M5.07'])),
    'mc-0363': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-n08']), frozenset(['L2.M1.02'])),
    'mc-0659': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-n08']), frozenset(['L2.M1.02'])),
    'mc-0685': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-n08']), frozenset(['L2.M1.02'])),
    'mc-0401': (frozenset(['inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-n10']), frozenset(['L1.M5.04'])),
    'mc-0516': (frozenset(['inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-n10']), frozenset(['L1.M5.04'])),
    'mc-0687': (frozenset(['inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n03', 'u-n07', 'u-n10']), frozenset(['L1.M5.04'])),
    'mc-0527': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n07', 'u-n09', 'u-n10']), frozenset(['L1.M5.05'])),
    'mc-0565': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n07', 'u-n09', 'u-n10']), frozenset(['L1.M5.05'])),
    'mc-0847': (frozenset(['inc-hidden', 'inc-ma', 'inc-negation', 'licensing_table']), frozenset(['u-n01', 'u-n07', 'u-n09', 'u-n10']), frozenset(['L1.M5.05'])),
    'mc-0470': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n03', 'u-n07']), frozenset(['L5.M1.06'])),
    'mc-0831': (frozenset(['inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n03', 'u-n07']), frozenset(['L5.M1.06'])),
    'mc-0264': (frozenset(['discriminator_table', 'inc-ma', 'inc-nawasikh', 'inc-negation']), frozenset(['u-n01', 'u-n02', 'u-n07', 'u-s06', 'u-s07']), frozenset(['L2.M5.02', 'L2.M5.03'])),
}

# the pinned row plan: T1MC-01..T1MC-49, family-by-family (FAMILY_ORDER), ascending-numeric within a family.
ROW_PLAN = [mc for fam in FAMILY_ORDER for mc in FAMILIES[fam]]
ROW_ID_BY_MC = {mc_id: "T1MC-%02d" % (i + 1) for i, mc_id in enumerate(ROW_PLAN)}
NEW_ROW_IDS = ["T1MC-%02d" % n for n in range(1, 50)]
KC_BY_MC = {mc_id: kc_id for kc_id, ids in FAMILIES.items() for mc_id in ids}

REQUIRED_ROW_FIELDS = (
    "id", "level", "concept", "prompt", "expected_answer", "accepted_variants", "forbidden_answers",
    "required_reasoning", "explanation", "kc_id", "sarf_procedure", "nahw_procedure",
    "remediation_route", "two_vote_required",
    "curriculum_misconception_ids", "quran_example", "public_eligible", "occurrence_status",
)
CANONICAL_KEY_SCHEMA_FIELDS = ("id", "level", "concept", "prompt", "quran_example", "expected_answer",
                               "accepted_variants", "forbidden_answers", "required_reasoning",
                               "sarf_procedure", "nahw_procedure", "remediation_route", "two_vote_required")
PROCEDURE_FIELDS = ("sarf_procedure", "nahw_procedure")

FORBIDDEN_SUBSTRINGS = (
    "curriculum/assessment", "eval/fusha-bench", "fusha-bench-v1", "benchmark",
    "candidate_not_runtime_integrated", "curriculum.l1l6_drill_candidate", "drills-candidates/drill-candidates",
    "qamus_certified", '"certified": true', "public_release", "closes_unit", "closes_lesson",
    "unit_closure", "lesson_closure", "mastery achieved", "fact certified", "http://", "https://",
    "c:" + "\\\\", "c:" + "/users", "/" + "users/", "placement-test",
)

EXPECTED_OCCURRENCE_STATUS = "no_committed_occurrence_evidence"


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _drills_by_misconception():
    return {r["misconception_link"]: r for r in _jsonl(DRILL_CANDIDATES)}


def _misconceptions_by_id():
    return {r["misconception_id"]: r for r in _jsonl(MISCONCEPTIONS)}


def _blob(row):
    return json.dumps(row, ensure_ascii=False)


def _assert_no_forbidden(testcase, blob, label):
    low = blob.lower()
    for bad in FORBIDDEN_SUBSTRINGS:
        testcase.assertNotIn(bad.lower(), low, "%s: forbidden substring %r" % (label, bad))


class TargetSetSourceTruthTests(unittest.TestCase):
    """The 49-id target set / 14-family plan is re-verified against the COMMITTED candidate + registry files,
    never trusted from the hardcoded tables above alone."""

    def test_target_set_has_exactly_49_unique_ids_in_14_disjoint_families(self):
        self.assertEqual(len(TARGET_IDS), 49)
        self.assertEqual(len(set(TARGET_IDS)), 49)
        self.assertEqual(len(FAMILIES), 14)
        seen = set()
        for fam_ids in FAMILIES.values():
            overlap = seen & set(fam_ids)
            self.assertEqual(overlap, set(), "families overlap on %s" % sorted(overlap))
            seen |= set(fam_ids)
        self.assertEqual(seen, set(TARGET_IDS))
        self.assertEqual(len(ROW_ID_BY_MC), 49)
        self.assertEqual(set(ROW_ID_BY_MC.values()), set(NEW_ROW_IDS))
        self.assertEqual(set(CAPS_UNITS_LESSONS), set(TARGET_IDS))

    def test_every_target_id_resolves_in_the_committed_drill_candidates_file_with_its_exact_capability_group(self):
        drills = _drills_by_misconception()
        for mc_id in TARGET_IDS:
            row = drills.get(mc_id)
            self.assertIsNotNone(row, "%s missing from drill-candidates.jsonl" % mc_id)
            self.assertEqual(row["drill_id"], "dr-" + mc_id)
            exp_caps, exp_units, _ = CAPS_UNITS_LESSONS[mc_id]
            self.assertEqual(frozenset(row["capability_link"]), exp_caps,
                              "%s: committed capability_link %r does not match expected %r"
                              % (mc_id, row["capability_link"], sorted(exp_caps)))
            self.assertEqual(frozenset(row["unit_links"]), exp_units,
                              "%s: committed unit_links %r does not match expected %r"
                              % (mc_id, row["unit_links"], sorted(exp_units)))
            self.assertEqual(row["status"], "candidate_not_runtime_integrated")

    def test_every_target_id_resolves_in_the_committed_misconception_registry(self):
        registry = _misconceptions_by_id()
        for mc_id in TARGET_IDS:
            row = registry.get(mc_id)
            self.assertIsNotNone(row, "%s missing from misconception-registry.jsonl" % mc_id)
            self.assertEqual(row["disposition"], "candidate_fixture")
            exp_caps, exp_units, exp_lessons = CAPS_UNITS_LESSONS[mc_id]
            self.assertEqual(frozenset(row["violated_capabilities"]), exp_caps,
                              "%s: registry violated_capabilities %r does not match expected %r"
                              % (mc_id, row["violated_capabilities"], sorted(exp_caps)))
            self.assertEqual(frozenset(row["related_units"]), exp_units)
            manifest_lessons = frozenset(m["lesson_id"] for m in row["manifestations"])
            self.assertEqual(manifest_lessons, exp_lessons,
                              "%s: registry manifestations %r does not match expected lessons %r"
                              % (mc_id, sorted(manifest_lessons), sorted(exp_lessons)))
            self.assertIn("u-n01", row["related_units"], "%s must carry u-n01" % mc_id)

    def test_contributing_lesson_set_matches_the_round_instructions(self):
        expected_lessons = {"L1.M5.04", "L1.M5.05", "L1.M5.07", "L2.M1.02", "L2.M1.04", "L2.M5.02", "L2.M5.03",
                            "L3.M4.04", "L3.M4.08", "L4.M2.04", "L4.M3.07", "L4.M5.10", "L5.M1.06", "L6.M4.06"}
        seen_lessons = set()
        for _caps, _units, lessons in CAPS_UNITS_LESSONS.values():
            seen_lessons |= lessons
        self.assertEqual(seen_lessons, expected_lessons)


class NewKcPlanTests(unittest.TestCase):
    """This worker's own KC plan is well-formed (self-check; does not depend on future files)."""

    def test_a_coherent_kc_family_is_chosen(self):
        self.assertEqual(len(NEW_KC_IDS), 14)
        self.assertEqual(len(NEW_KC_IDS), len(set(NEW_KC_IDS)))
        for kc_id in NEW_KC_IDS:
            self.assertRegex(kc_id, r"^kc-t1-ma-context-[a-z0-9-]+$")

    def test_family_sizes_sum_to_49_and_none_is_empty(self):
        sizes = [len(ids) for ids in FAMILIES.values()]
        self.assertEqual(sum(sizes), 49)
        self.assertTrue(all(n >= 1 for n in sizes))


class FutureKcCatalogTests(unittest.TestCase):
    """The combined KC catalog (legacy + curriculum/kc-catalog.d/*.jsonl shards) must gain this batch's 14 KCs
    with non-overlapping coverage of TARGET_IDS, routed to the new markdown remediation surface."""

    def _catalog_by_id(self):
        return kc_catalog.load_kc_catalog_by_id(_REPO)

    def test_shard_file_exists(self):
        self.assertTrue(NEW_SHARD.exists(), "%s does not exist yet" % NEW_SHARD)

    def test_every_new_kc_id_is_present_in_the_catalog(self):
        by_id = self._catalog_by_id()
        missing = [kc_id for kc_id in NEW_KC_IDS if kc_id not in by_id]
        self.assertEqual(missing, [], "not yet defined in the combined KC catalog: %s" % missing)

    def test_every_new_kc_has_the_required_fields_and_a_non_auto_safe_gate_and_routes_to_the_new_lesson(self):
        by_id = self._catalog_by_id()
        required_fields = ("kc_id", "arabic_grammar_name", "plain_rule", "trigger_condition", "expected_feature",
                            "typical_error_feature", "default_gate", "grammar_topic",
                            "curriculum_misconception_ids", "drill_route")
        for kc_id in NEW_KC_IDS:
            kc = by_id[kc_id]
            for field in required_fields:
                self.assertIn(field, kc, "%s missing field %r" % (kc_id, field))
            self.assertNotEqual(kc["default_gate"], "auto_safe",
                                 "%s must stay non-auto_safe so its rows stay two_vote_required" % kc_id)
            self.assertIsInstance(kc["curriculum_misconception_ids"], list)
            self.assertEqual(kc["drill_route"], NEW_LESSON_REL,
                              "%s must route to the new markdown remediation surface" % kc_id)

    def test_new_kc_coverage_exactly_and_disjointly_partitions_the_49_target_ids(self):
        by_id = self._catalog_by_id()
        seen = set()
        union = set()
        for kc_id in NEW_KC_IDS:
            ids = set(by_id[kc_id]["curriculum_misconception_ids"])
            overlap = ids & seen
            self.assertEqual(overlap, set(), "%s overlaps another new KC on %s" % (kc_id, sorted(overlap)))
            outside = ids - set(TARGET_IDS)
            self.assertEqual(outside, set(), "%s covers ids outside the 49-id target set: %s"
                              % (kc_id, sorted(outside)))
            seen |= ids
            union |= ids
        self.assertEqual(union, set(TARGET_IDS), "new-KC coverage does not exactly equal the 49 target ids")

    def test_new_kc_family_membership_matches_the_pinned_family_plan(self):
        by_id = self._catalog_by_id()
        for kc_id, expected_ids in FAMILIES.items():
            self.assertEqual(set(by_id[kc_id]["curriculum_misconception_ids"]), set(expected_ids),
                              "%s coverage does not match the pinned family membership" % kc_id)

    def test_new_kc_text_fields_carry_no_forbidden_vocabulary(self):
        by_id = self._catalog_by_id()
        for kc_id in NEW_KC_IDS:
            _assert_no_forbidden(self, _blob(by_id[kc_id]), kc_id)

    def test_mc_0006_and_mc_0142_are_not_relabelled_into_a_pre_existing_central_kc(self):
        """Per the round's route-locality constraint: mc-0006 and mc-0142 already sit in central KCs whose
        drill_route is NOT this batch's lesson surface, so this batch must define its OWN narrowly-scoped
        route-local KC for each rather than silently reusing (or duplicating the intent of) the central one."""
        by_id = self._catalog_by_id()
        self.assertIn("mc-0006", by_id[KC_MA_DAMA]["curriculum_misconception_ids"])
        self.assertIn("mc-0142", by_id[KC_MASDARIYYA]["curriculum_misconception_ids"])
        # the pre-existing central KCs (if still present) must keep routing elsewhere, never to this lesson.
        central = by_id.get("kc-case-mood-context")
        if central is not None:
            self.assertNotEqual(central.get("drill_route"), NEW_LESSON_REL)
        central2 = by_id.get("kc-unvoweled-homograph")
        if central2 is not None:
            self.assertNotEqual(central2.get("drill_route"), NEW_LESSON_REL)


class FutureBankStructureTests(unittest.TestCase):
    """curriculum/drills/keys/tranche-001-ma-context-runtime.keys.jsonl must exist with exactly 49 original rows
    (T1MC-01..T1MC-49), one primary row per misconception id. RED until authored."""

    def _rows(self):
        return _jsonl(NEW_BANK)

    def test_bank_file_exists_with_exactly_49_unique_rows_with_the_pinned_ids(self):
        self.assertTrue(NEW_BANK.exists(), "%s does not exist yet" % NEW_BANK_REL)
        rows = self._rows()
        self.assertEqual(len(rows), 49)
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate row ids in the new bank")
        self.assertEqual(sorted(ids), sorted(NEW_ROW_IDS))

    def test_every_row_carries_the_three_canonical_key_schema_fields(self):
        for row in self._rows():
            for field in CANONICAL_KEY_SCHEMA_FIELDS:
                self.assertIn(field, row, "%s missing canonical key-schema field %r" % (row.get("id"), field))
            self.assertIsInstance(row["concept"], str)
            self.assertTrue(row["concept"].strip(), "%s: concept must be a non-empty string" % row["id"])
            self.assertTrue(
                row["sarf_procedure"] is not None or row["nahw_procedure"] is not None,
                "%s: at least one of sarf_procedure/nahw_procedure must be non-null" % row["id"])

    def test_every_non_null_procedure_path_exists_on_disk(self):
        for row in self._rows():
            for field in PROCEDURE_FIELDS:
                path = row[field]
                if path is None:
                    continue
                self.assertTrue((_REPO / path).exists(),
                                 "%s: %s cites missing path %r" % (row["id"], field, path))

    def test_every_row_carries_the_required_fields_and_is_two_vote_occurrence_neutral_and_public_ineligible(self):
        for row in self._rows():
            for field in REQUIRED_ROW_FIELDS:
                self.assertIn(field, row, "%s missing field %r" % (row.get("id"), field))
            self.assertIs(row["two_vote_required"], True, "%s must be two_vote_required" % row["id"])
            self.assertIsNone(row["quran_example"], "%s: occurrence-neutral rows use quran_example: null" % row["id"])
            self.assertIs(row["public_eligible"], False, "%s must be public-ineligible" % row["id"])
            self.assertEqual(row["occurrence_status"], EXPECTED_OCCURRENCE_STATUS)
            self.assertEqual(row["remediation_route"], NEW_LESSON_REL,
                              "%s must remediate to the new lesson surface" % row["id"])
            self.assertIn(row["kc_id"], NEW_KC_IDS, "%s uses a KC outside this batch's new KCs" % row["id"])
            self.assertGreaterEqual(len(row["curriculum_misconception_ids"]), 1)
            self.assertGreaterEqual(len(row.get("accepted_variants") or []), 1)
            self.assertGreaterEqual(len(row.get("forbidden_answers") or []), 1,
                                     "%s needs at least one forbidden (wrong-reasoning) answer" % row["id"])
            self.assertGreaterEqual(len(row.get("required_reasoning") or []), 1)

    def test_bank_coverage_exactly_equals_the_49_target_ids_with_no_unrelated_id_laundered_in(self):
        rows = self._rows()
        covered = set()
        for row in rows:
            covered |= set(row["curriculum_misconception_ids"])
        self.assertEqual(covered, set(TARGET_IDS),
                          "bank coverage != target set; missing=%s extra=%s"
                          % (sorted(set(TARGET_IDS) - covered), sorted(covered - set(TARGET_IDS))))

    def test_every_row_is_a_single_id_primary_row_no_id_appears_twice(self):
        rows = self._rows()
        seen = []
        for row in rows:
            ids = row["curriculum_misconception_ids"]
            self.assertEqual(len(ids), 1, "%s: a primary row must carry exactly one misconception id" % row["id"])
            seen.append(ids[0])
        self.assertEqual(sorted(seen), TARGET_IDS)

    def test_bank_row_ids_match_the_pinned_row_plan(self):
        rows = self._rows()
        by_mc = {row["curriculum_misconception_ids"][0]: row["id"] for row in rows}
        self.assertEqual(by_mc, ROW_ID_BY_MC)

    def test_bank_row_family_membership_matches_the_pinned_family_plan(self):
        rows = self._rows()
        by_mc = {row["curriculum_misconception_ids"][0]: row for row in rows}
        for mc_id, kc_id in KC_BY_MC.items():
            self.assertEqual(by_mc[mc_id]["kc_id"], kc_id,
                              "%s: row for %s must use kc_id %s per the pinned family plan"
                              % (by_mc[mc_id]["id"], mc_id, kc_id))

    def test_every_new_kc_is_exercised_by_at_least_one_row_and_no_stray_kc_is_used(self):
        rows = self._rows()
        counts = {}
        for row in rows:
            counts[row["kc_id"]] = counts.get(row["kc_id"], 0) + 1
        self.assertEqual(set(counts), set(NEW_KC_IDS), "row KC usage does not match the new KC set exactly")

    def test_no_row_carries_forbidden_vocabulary_or_a_candidate_schema_leak(self):
        for row in self._rows():
            _assert_no_forbidden(self, _blob(row), row.get("id"))
            self.assertNotIn("prompt_specification", row)
            self.assertNotIn("expected_rubric", row)
            self.assertNotIn("capability_link", row)
            self.assertNotIn("answer_leakage_posture", row)
            self.assertNotIn("adapter_requirement", row)

    def test_rows_are_clean_room_never_copying_the_candidate_specs_prose_verbatim(self):
        drills = _drills_by_misconception()
        for row in self._rows():
            mc_id = row["curriculum_misconception_ids"][0]
            cand = drills[mc_id]
            self.assertNotIn(cand["expected_rubric"], row["expected_answer"],
                              "%s: expected_answer launders the candidate's expected_rubric verbatim" % row["id"])
            self.assertNotIn(cand["prompt_specification"], row["prompt"],
                              "%s: prompt launders the candidate's prompt_specification verbatim" % row["id"])
            self.assertNotEqual(row["expected_answer"].strip(), cand["expected_rubric"].strip(),
                                "%s: expected_answer is a verbatim copy of the candidate expected_rubric" % row["id"])

    def test_bank_and_catalog_kc_assignments_are_mutually_consistent(self):
        catalog_by_id = kc_catalog.load_kc_catalog_by_id(_REPO)
        for row in self._rows():
            kc = catalog_by_id.get(row["kc_id"])
            self.assertIsNotNone(kc, "%s: kc_id %r not in combined KC catalog" % (row["id"], row["kc_id"]))
            allowed = set(kc["curriculum_misconception_ids"])
            got = set(row["curriculum_misconception_ids"])
            self.assertTrue(got.issubset(allowed),
                             "%s: misconception ids %s not all listed under its own KC %s"
                             % (row["id"], sorted(got - allowed), row["kc_id"]))

    def test_no_row_leaks_its_own_expected_answer_phrase_into_the_prompt(self):
        for row in self._rows():
            self.assertNotIn(row["expected_answer"].strip(), row["prompt"],
                              "%s: expected_answer text leaks verbatim into the prompt" % row["id"])
            for variant in row["accepted_variants"]:
                self.assertNotIn(variant.strip(), row["prompt"],
                                  "%s: an accepted_variant leaks verbatim into the prompt" % row["id"])


class DrillKeysValidatorRealInterfaceTests(unittest.TestCase):
    """Runs the REAL tools/validate_drill_keys.validate() against this bank (never a reimplementation of its
    schema/leak/cited-path/hard-grammar checks)."""

    def test_validate_drill_keys_accepts_this_bank_with_zero_errors(self):
        import validate_drill_keys as vdk
        errors = vdk.validate(str(NEW_BANK))
        self.assertEqual(errors, [], "validate_drill_keys.validate() rejected the bank: %s" % errors)

    def test_validate_drill_keys_recognizes_at_least_one_two_vote_hard_grammar_row(self):
        import validate_drill_keys as vdk
        rows = _jsonl(NEW_BANK)
        hard_rows = 0
        two_vote_hard_rows = 0
        for row in rows:
            blob = json.dumps(row, ensure_ascii=False).lower()
            is_hard = any(term.lower() in blob for term in vdk.HARD_TERMS)
            if is_hard:
                hard_rows += 1
                if row.get("two_vote_required"):
                    two_vote_hard_rows += 1
        self.assertGreater(hard_rows, 0, "validate_drill_keys would report 'expected at least one hard-grammar row'")
        self.assertGreater(two_vote_hard_rows, 0,
                           "validate_drill_keys would report 'expected at least one two_vote_required hard-grammar "
                           "row'")


class FutureLessonSurfaceTests(unittest.TestCase):
    """curriculum/drills/tranche-001-ma-context-runtime.md must exist and honestly disclaim assessment/
    certification status, without claiming whole-unit or whole-lesson closure. RED until authored."""

    def test_lesson_file_exists(self):
        self.assertTrue(NEW_LESSON.exists(), "%s does not exist yet" % NEW_LESSON_REL)

    def test_lesson_mentions_every_new_kc_and_carries_no_forbidden_vocabulary(self):
        text = NEW_LESSON.read_text(encoding="utf-8")
        for kc_id in NEW_KC_IDS:
            self.assertIn(kc_id, text, "lesson never mentions %s" % kc_id)
        _assert_no_forbidden(self, text, "lesson")

    def test_lesson_carries_an_explicit_non_assessment_non_certification_disclaimer(self):
        low = NEW_LESSON.read_text(encoding="utf-8").lower()
        assessment_disclaimed = ("never assessment" in low or "not assessment" in low
                                  or "never usable as independent assessment" in low)
        certification_disclaimed = ("never certification" in low or "not certification" in low
                                     or "not certified" in low or "no certification" in low
                                     or "never assessment or certification" in low)
        self.assertTrue(assessment_disclaimed, "lesson must disclaim assessment use")
        self.assertTrue(certification_disclaimed, "lesson must disclaim certification/closure claims")

    def test_lesson_does_not_claim_whole_unit_or_whole_lesson_closure(self):
        low = NEW_LESSON.read_text(encoding="utf-8").lower()
        for bad in ("closes this lesson", "closes this unit", "completes the lesson", "completes the unit",
                    "unit is now closed", "lesson is now closed"):
            self.assertNotIn(bad, low, "lesson must not claim whole-unit/whole-lesson closure")

    def test_lesson_does_not_claim_a_unit_is_fully_operationalized_or_tranche_closed(self):
        low = NEW_LESSON.read_text(encoding="utf-8").lower()
        for bad in ("unit fully operationalized", "fully operationalized", "unit is complete",
                    "tranche closure", "tranche is closed", "closes the tranche", "runtime integration of "
                    "all", "learner mastery", "certifies"):
            self.assertNotIn(bad, low, "lesson must not claim unit/tranche closure or fact certification")


class RuntimeBehaviourTests(unittest.TestCase):
    """Ordinary fusha_tutor_runtime bank loading, correct-answer-plus-wrong-reason hold, wrong-answer
    remediation, and two-vote hold behaviour, all through the REAL tools/fusha_tutor_runtime.py interfaces
    (never a reimplementation). RED until the bank + KC catalog entries exist."""

    def test_bank_loads_through_the_real_runtime_loader(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        self.assertEqual(len(rows), 49)

    def test_every_row_passes_the_real_catalog_gate_check(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        kc_by_id = ftr._load_kc_catalog_by_id()
        for row in rows:
            failures = ftr._check_kc_gate_row(row, kc_by_id)
            self.assertEqual(failures, [], "%s failed the real catalog-gate check: %s" % (row["id"], failures))

    def test_correct_answer_and_correct_reasoning_is_held_for_the_two_vote_fact_gate_not_cleared(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertTrue(result["grade"]["passed"])
        self.assertTrue(result["grade"]["reasoning_passed"])
        self.assertTrue(result["grade"]["held_for_fact_gate"])
        self.assertFalse(result["grade"]["cleared"])
        self.assertEqual(result["outcome"], "hold")
        self.assertIsNone(result["event"]["remediation_route"])

    def test_correct_answer_with_missing_required_reasoning_is_rejected_and_routed_to_remediation(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": row["expected_answer"], "reasoning": []}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertFalse(result["grade"]["reasoning_passed"])
        self.assertFalse(result["grade"]["content_mastered"])
        self.assertEqual(result["outcome"], "hold")
        self.assertEqual(result["event"]["remediation_route"], row["remediation_route"])

    def test_correct_answer_with_wrong_reasoning_is_rejected_and_routed_to_remediation(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": row["expected_answer"], "reasoning": ["this reasoning names nothing the row requires"]}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertFalse(result["grade"]["reasoning_passed"])
        self.assertFalse(result["grade"]["content_mastered"])
        self.assertEqual(result["outcome"], "hold")
        self.assertEqual(result["event"]["remediation_route"], row["remediation_route"])

    def test_wrong_answer_is_rejected_and_routed_to_remediation(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": "this is not the expected answer at all", "reasoning": list(row["required_reasoning"])}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertFalse(result["grade"]["passed"])
        self.assertEqual(result["outcome"], "lapse")
        self.assertEqual(result["event"]["remediation_route"], row["remediation_route"])

    def test_a_self_declared_agreeing_second_vote_never_clears_a_row(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"]),
                   "second_check": {"conclusion_agrees": True, "reason_agrees": True}}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertTrue(result["grade"]["content_mastered"])
        self.assertEqual(result["grade"]["two_vote_status"], "pending")
        self.assertIs(result["grade"]["second_check_declared"], True)
        self.assertFalse(result["grade"]["cleared"])
        self.assertEqual(result["outcome"], "hold")

    def test_every_row_labelled_with_missing_reasoning_is_rejected(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            payload = {"answer": row["expected_answer"], "reasoning": []}
            result = ftr.step(row, None, payload, now_day=0)
            self.assertFalse(result["grade"]["reasoning_passed"],
                              "%s: missing-reasoning answer unexpectedly passed reasoning" % row["id"])
            self.assertFalse(result["grade"]["content_mastered"],
                              "%s: missing-reasoning answer unexpectedly counted as mastered" % row["id"])

    def test_every_row_rejects_at_least_one_forbidden_answer_via_the_real_grader(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            forbidden = row["forbidden_answers"][0]
            payload = {"answer": forbidden, "reasoning": list(row["required_reasoning"])}
            g = ftr.grade(row, payload)
            self.assertTrue(g["forbidden_hit"], "%s: forbidden answer %r not detected by the real grader"
                             % (row["id"], forbidden))

    def test_select_next_can_reach_a_new_item_from_this_bank(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        progress = ftr.new_progress()
        item_id, reason = ftr.select_next(rows, progress, 0)
        self.assertEqual(item_id, rows[0]["id"])
        self.assertEqual(reason, "new_item")

    def test_at_least_one_hostile_forbidden_answer_per_kc_family_is_caught_by_the_real_grader(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        by_kc = {}
        for row in rows:
            by_kc.setdefault(row["kc_id"], []).append(row)
        self.assertEqual(set(by_kc), set(NEW_KC_IDS))
        for kc_id, kc_rows in by_kc.items():
            hit_any = False
            for row in kc_rows:
                forbidden = row["forbidden_answers"][0]
                g = ftr.grade(row, {"answer": forbidden, "reasoning": list(row["required_reasoning"])})
                if g["forbidden_hit"] and not g["cleared"]:
                    hit_any = True
            self.assertTrue(hit_any, "%s: no hostile forbidden-answer case caught by the real grader" % kc_id)


class NegativeMutationSurgicalTests(unittest.TestCase):
    """Surgical negative-mutation checks: each test takes a real, in-memory row/catalog copy, applies exactly one
    deliberate defect, and asserts the defect is caught by a REAL interface (tools/validate_drill_keys.validate,
    tools/fusha_tutor_runtime.grade/step/_check_kc_gate_row) wherever one exists for that defect class, or by the
    same structural assertion already exercised (in the positive direction) elsewhere in this file. RED until the
    three artifacts exist (every test here loads the real bank/catalog first)."""

    def _rows(self):
        return _jsonl(NEW_BANK)

    def _validate_mutated_bank(self, rows):
        with tempfile.TemporaryDirectory() as td:
            temp_path = Path(td) / NEW_BANK_NAME
            _write_jsonl(temp_path, rows)
            import validate_drill_keys as vdk
            return vdk.validate(str(temp_path), repo_root=str(_REPO))

    def test_a_row_retargeted_off_the_49_id_set_breaks_exact_coverage(self):
        rows = self._rows()
        mutated = copy.deepcopy(rows)
        mutated[0]["curriculum_misconception_ids"] = ["mc-9999"]
        covered = {mc_id for row in mutated for mc_id in row["curriculum_misconception_ids"]}
        missing = set(TARGET_IDS) - covered
        self.assertNotEqual(missing, set(), "retargeting a row off the target set must surface a missing id")
        self.assertIn(rows[0]["curriculum_misconception_ids"][0], missing)

    def test_public_eligible_true_violates_the_batch_public_ineligibility_contract(self):
        rows = self._rows()
        mutated = copy.deepcopy(rows[0])
        mutated["public_eligible"] = True
        with self.assertRaises(AssertionError):
            self.assertIs(mutated["public_eligible"], False)

    def test_a_non_null_quran_example_violates_the_batch_occurrence_neutral_contract(self):
        rows = self._rows()
        mutated = copy.deepcopy(rows[0])
        mutated["quran_example"] = "quran:2:255:1"
        with self.assertRaises(AssertionError):
            self.assertIsNone(mutated["quran_example"])

    def test_two_vote_required_false_is_caught_by_the_real_catalog_gate_check(self):
        import fusha_tutor_runtime as ftr
        rows = self._rows()
        mutated = copy.deepcopy(rows[0])
        mutated["two_vote_required"] = False
        kc_by_id = ftr._load_kc_catalog_by_id()
        failures = ftr._check_kc_gate_row(mutated, kc_by_id)
        self.assertNotEqual(failures, [], "a non-auto_safe KC row with two_vote_required=False must fail the "
                                          "real catalog-gate check")

    def test_correct_answer_with_wrong_reason_fails_the_real_grader(self):
        import fusha_tutor_runtime as ftr
        row = self._rows()[0]
        g = ftr.grade(row, {"answer": row["expected_answer"],
                             "reasoning": ["an unrelated statement that names none of the required reasoning"]})
        self.assertFalse(g["reasoning_passed"])
        self.assertFalse(g["content_mastered"])

    def test_a_self_declared_second_vote_cannot_clear_a_two_vote_row_via_the_real_grader(self):
        import fusha_tutor_runtime as ftr
        row = self._rows()[0]
        g = ftr.grade(row, {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"]),
                             "second_check": {"conclusion_agrees": True, "reason_agrees": True}})
        self.assertEqual(g["two_vote_status"], "pending")
        self.assertFalse(g["cleared"])

    def test_an_expected_answer_phrase_injected_into_the_prompt_is_caught(self):
        rows = self._rows()
        mutated = copy.deepcopy(rows[0])
        mutated["prompt"] = mutated["prompt"] + " " + mutated["expected_answer"]
        with self.assertRaises(AssertionError):
            self.assertNotIn(mutated["expected_answer"].strip(), mutated["prompt"])

    def test_an_unresolvable_kc_id_is_caught_by_the_real_validator(self):
        rows = self._rows()
        mutated = copy.deepcopy(rows)
        mutated[0]["kc_id"] = "kc-does-not-exist-in-any-catalog"
        errors = self._validate_mutated_bank(mutated)
        self.assertTrue(any("does not resolve" in e for e in errors),
                         "an unresolvable kc_id must be flagged by validate_drill_keys.validate(): %s" % errors)

    def test_an_unresolvable_remediation_route_is_caught_by_the_real_validator(self):
        rows = self._rows()
        mutated = copy.deepcopy(rows)
        mutated[0]["remediation_route"] = "curriculum/drills/this-route-does-not-exist.md"
        errors = self._validate_mutated_bank(mutated)
        self.assertTrue(any("cites missing path" in e for e in errors),
                         "an unresolvable remediation_route must be flagged by validate_drill_keys.validate(): %s"
                         % errors)


class SourceCustodyAndLeakageBoundaryTests(unittest.TestCase):
    """The three new artifacts must never read/cite the eval or placement-test surfaces this round excludes, and
    must never leak candidate-only schema fields into runtime-visible rows."""

    def test_no_new_artifact_references_the_excluded_eval_or_placement_surfaces(self):
        for path in (NEW_BANK, NEW_LESSON, NEW_SHARD):
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            low = text.lower()
            self.assertNotIn("eval/fusha-bench-v1", low)
            self.assertNotIn("fusha-bench", low)
            self.assertNotIn("placement-test.sample", low)

    def test_no_new_artifact_leaks_via_the_shared_leak_sot_scanner(self):
        import leak_sot
        for path in (NEW_BANK, NEW_SHARD):
            if not path.exists():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                hits = leak_sot.scan(line)
                self.assertEqual(hits, [], "%s:%d leaks: %s" % (path, lineno, hits))

    def test_assessment_quarantine_is_unaffected_by_this_batch(self):
        import validate_drill_keys as vdk
        errs = vdk.assessment_quarantine_violations()
        self.assertEqual(errs, [], "real assessment banks fail the quarantine after this batch: %s" % errs[:3])


def _jsonl_shard(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


class F6InterrogativeVsRelativeAlifProseUnambiguous(unittest.TestCase):
    """F6: the interrogative alif-elided closed inventory (لِمَ، عَمَّ، مِمَّ، فِيمَ، بِمَ) vs the relative/
    masdariyya retained-alif inventory (لِمَا، عَمَّا، مِمَّا، فِيمَا، بِمَا) must be spelled out in ARABIC
    SCRIPT in the KC prose, never left as bare Latin transliteration ('lima, amma, mimma, fima, bima') that is
    textually indistinguishable from the UNRELATED topic particle أَمَّا (also transliterated 'amma')."""

    def _kc(self, kc_id):
        return {row["kc_id"]: row for row in _jsonl_shard(NEW_SHARD)}[kc_id]

    def test_istifham_alif_elision_kc_uses_arabic_script_for_its_closed_inventory(self):
        kc = self._kc("kc-t1-ma-context-istifham-alif-elision-preposition")
        for form in ("لِمَ", "عَمَّ", "مِمَّ", "فِيمَ", "بِمَ"):
            self.assertIn(form, kc["plain_rule"],
                         "istifham-alif-elision KC must spell its closed inventory in Arabic script: %s" % form)
        self.assertNotIn("lima, amma, mimma, fima, bima", kc["plain_rule"],
                         "the closed inventory must not be left as bare ambiguous Latin transliteration")

    def test_istifham_kc_explicitly_disambiguates_amma_from_the_unrelated_topic_particle(self):
        kc = self._kc("kc-t1-ma-context-istifham-alif-elision-preposition")
        self.assertIn("أَمَّا", kc["plain_rule"],
                     "the KC must explicitly name and distinguish the unrelated topic particle أَمَّا from "
                     "the interrogative عَمَّ, since both transliterate identically as 'amma'")

    def test_relative_masdariyya_kc_uses_arabic_script_for_its_retained_alif_inventory(self):
        kc = self._kc("kc-t1-ma-context-relative-preposition-majrur-government")
        for form in ("بِمَا", "مِمَّا", "فِيمَا"):
            self.assertIn(form, kc["plain_rule"],
                         "relative/masdariyya KC must spell its retained-alif inventory in Arabic script: %s" % form)


class F11ProseIntegrityBoundedAssertion(unittest.TestCase):
    """F11: no committed T1b file may contain a digit-corrupted Arabic transliteration token (e.g. 'a1n' for
    'in'/'إِنْ') or a mixed-script token that directly fuses a Latin letter with an Arabic letter with no
    separator (e.g. 'command-lام'). R6: scoped to this batch's own writable T1b artifacts PLUS the shared
    remediation index and missed-error-log template this same repair round may also edit (the F11 residue was
    exactly a token that survived in the remediation index outside the original three-file scan)."""

    # a lowercase LETTER-DIGIT-LETTER(S) run at a word boundary — the exact 'a1n' (for 'in'/'إِنْ')
    # corruption shape. Deliberately narrow: repo IDs like T1MC-11, kc-t1-..., l1l6 never match (uppercase, or
    # the digit sits next to a hyphen/another digit rather than being letter-digit-letter with no separator).
    _DIGIT_IN_LATIN_WORD = __import__("re").compile(r"\b[a-z][0-9][a-z]+\b")
    _MIXED_SCRIPT_TOKEN = __import__("re").compile(r"[A-Za-z][؀-ۿ]|[؀-ۿ][A-Za-z]")

    def _scan_paths(self):
        return [NEW_BANK, NEW_LESSON, NEW_SHARD, REMEDIATION_INDEX, MISSED_ERROR_LOG_TEMPLATE]

    def test_no_digit_corrupted_transliteration_token(self):
        for path in self._scan_paths():
            text = path.read_text(encoding="utf-8")
            hits = self._DIGIT_IN_LATIN_WORD.findall(text)
            self.assertEqual(hits, [], "%s: digit-corrupted transliteration token(s): %s" % (path, hits))

    def test_no_mixed_script_fused_token(self):
        for path in self._scan_paths():
            text = path.read_text(encoding="utf-8")
            hits = self._MIXED_SCRIPT_TOKEN.findall(text)
            self.assertEqual(hits, [], "%s: mixed-script fused token(s): %s" % (path, hits))


class F9HijaziyyaZarfJarrMajrurExceptionQualified(unittest.TestCase):
    """F9: the hijaziyya cancellation-by-predicate-fronting AND cancellation-by-complement-fronting rules must
    both be qualified with the licensed zarf/jarr-majrur exception (fronting a shibh al-jumla khabar, OR a
    shibh al-jumla complement of an otherwise-ordinary khabar, does NOT cancel ma's government), in the KC
    prose and in BOTH T1MC-07's (khabar-fronting) and T1MC-08's (complement-fronting) own row reasoning — and
    add no occurrence certification (quran_example stays null on either row)."""

    def _kc(self):
        return {row["kc_id"]: row for row in _jsonl_shard(NEW_SHARD)}["kc-t1-ma-context-hijaziyya-tamimiyya-nullifiers"]

    def _row(self, item_id="T1MC-07"):
        import fusha_tutor_runtime as ftr
        return {r["id"]: r for r in ftr.load_bank(str(NEW_BANK))}[item_id]

    def test_kc_plain_rule_names_the_zarf_jarr_majrur_exception(self):
        kc = self._kc()
        blob = kc["plain_rule"].lower()
        self.assertIn("ẓarf", blob)
        self.assertIn("majrūr", blob)
        self.assertIn("does not cancel", blob)

    def test_kc_plain_rule_scopes_the_exception_to_both_the_khabar_and_complement_triggers(self):
        # R3: the licensed exception must cover BOTH the predicate(khabar)-fronting trigger and the
        # complement-fronting trigger, not only the one F9's original repair touched.
        kc = self._kc()
        blob = kc["plain_rule"].lower()
        self.assertIn("complement", blob)
        self.assertIn("maʿmūl", blob)
        self.assertIn("both the predicate-fronting trigger and the complement-fronting trigger", blob)

    def test_row_reasoning_names_the_exception_and_stays_occurrence_neutral(self):
        for item_id in ("T1MC-07", "T1MC-08"):
            with self.subTest(id=item_id):
                row = self._row(item_id)
                self.assertIsNone(row["quran_example"], "F9 qualification must add no occurrence certification")
                blob = " ".join(row["required_reasoning"]).lower()
                self.assertIn("zarf", blob)
                self.assertIn("licensed exception", blob)

    def test_row_rejects_the_overgeneralized_every_predicate_cancels_claim(self):
        import fusha_tutor_runtime as ftr
        row = self._row("T1MC-07")
        g = ftr.grade(row, {"answer": "Fronting any predicate at all, including a zarf or jarr-majrur, always "
                                     "cancels ma's government the same way an ordinary predicate does.",
                          "reasoning": []})
        self.assertFalse(g["content_mastered"])

    def test_t1mc08_rejects_the_overgeneralized_every_complement_cancels_claim(self):
        # R3: the mirror forbidden answer on T1MC-08 itself, proven through the real grader (not just present
        # in forbidden_answers text) -- this is the exact counterexample the Opus targeted re-review named.
        import fusha_tutor_runtime as ftr
        row = self._row("T1MC-08")
        g = ftr.grade(row, {"answer": "Fronting any complement at all, including a zarf or jarr-majrur, always "
                                     "cancels ma's government over the predicate the same way an ordinary "
                                     "complement does.",
                          "reasoning": []})
        self.assertFalse(g["content_mastered"])

    def test_t1mc08_still_clears_content_on_its_own_gold_answer(self):
        import fusha_tutor_runtime as ftr
        row = self._row("T1MC-08")
        g = ftr.grade(row, {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])})
        self.assertTrue(g["content_mastered"])


class F2ExactDiacriticContractGuard(unittest.TestCase):
    """F2: every row whose authored correct form and an authored forbidden form collide under the lenient
    recall normalizer (differ ONLY by a vowel/shadda/case-ending diacritic) must opt into `exact_surface_forms`,
    and the exact contract must actually reject that colliding forbidden form while still accepting the gold
    form."""

    def test_every_diacritic_colliding_row_declares_exact_surface_forms(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        missing = [row["id"] for row in rows
                  if ftr.diacritic_only_collision(row) and not row.get("exact_surface_forms")]
        self.assertEqual(missing, [],
                         "rows whose expected/forbidden collide under the lenient normalizer (differ only by "
                         "diacritics) but do not declare exact_surface_forms: %s" % missing)

    def test_exact_surface_forms_rows_reject_a_token_level_hostile_substitution(self):
        """R7: token-level hostile substitution -- for every row that authored a forbidden_answers TOKEN
        colliding with one of its own declared exact_surface_forms under the lenient normalizer, substitute
        that REAL authored hostile token into the REAL gold answer and assert the real grader rejects it.
        Replaces the vacuous whole-sentence membership check, which compared an entire forbidden_answers
        sentence's normalized text against an entire expected_answer/accepted_variant and so never fired."""
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            if not row.get("exact_surface_forms") or row.get("exact_surface_forms_mode", "all") != "all":
                continue
            for gold, hostile in ftr.exact_surface_hostile_pairs(row):
                hostile_answer = row["expected_answer"].replace(gold, hostile)
                with self.subTest(id=row["id"], gold=gold, hostile=hostile):
                    self.assertNotEqual(hostile_answer, row["expected_answer"])
                    g = ftr.grade(row, {"answer": hostile_answer, "reasoning": list(row["required_reasoning"])})
                    self.assertFalse(g["passed"],
                                    "%s: exact_surface_forms must reject the token-level hostile substitution "
                                    "%r -> %r" % (row["id"], gold, hostile))

    def test_exact_surface_forms_rows_still_accept_their_own_gold_form(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            if not row.get("exact_surface_forms"):
                continue
            with self.subTest(id=row["id"]):
                g = ftr.grade(row, {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])})
                self.assertTrue(g["passed"], "%s: exact_surface_forms must still accept the gold answer" % row["id"])

    def test_conjunctive_multiform_rows_require_every_declared_surface(self):
        """R1: a row with >=2 exact_surface_forms and mode 'all' (the default) must reject an answer dropping
        one of the declared surfaces. This bank currently authors no such multi-form row, so the loop is
        expected to be a no-op today; it stays live so a future conjunctive row is covered automatically."""
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            forms = row.get("exact_surface_forms") or []
            if len(forms) < 2 or row.get("exact_surface_forms_mode", "all") != "all":
                continue
            partial = row["expected_answer"]
            for missing in forms[1:]:
                partial = partial.replace(missing, "")
            with self.subTest(id=row["id"]):
                self.assertNotEqual(partial, row["expected_answer"])
                g = ftr.grade(row, {"answer": partial, "reasoning": list(row["required_reasoning"])})
                self.assertFalse(g["passed"], "%s: dropping a required conjunctive surface must fail "
                                              "exact_surface_forms" % row["id"])


if __name__ == "__main__":
    unittest.main()
