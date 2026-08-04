#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_weak_root_voice_runtime — RED-FIRST tests for the tranche-001 L4.M1 weak-root/voice ordinary-runtime
formative-practice batch covering L4.M1.01-07 (assimilated, defective, geminate, hamzated, doubly weak,
passive-voice-melody, deputy-agent).

This batch has NO source candidate-drill manifest (curriculum/l1l6/drills-candidates/drill-candidates.jsonl
carries zero L4.M1 rows): it is authored directly from the committed misconception registry
(curriculum/l1l6/misconceptions/misconception-registry.jsonl), the canonical-unit inputs named in the task
brief, and the existing accepted Sarf/Nahw procedures. There is therefore no "candidate manifest unchanged"
class here (unlike the nawasikh/followers Train B/C batches) — the deterministic manifest below IS the
authoring source, pinned directly against the real registry file.

Proves, in order:
  1. The exact 31-unique-id misconception manifest (mc-0278 contributes to two lessons, L4.M1.02 and L4.M1.05,
     but is bound to exactly ONE runtime row / ONE KC — reused, not duplicated) is pinned against the REAL
     curriculum/l1l6/misconceptions/misconception-registry.jsonl content (lesson_id + pattern text), not a mock.
  2. curriculum/drills/keys/weak-root-voice-runtime.keys.jsonl carries exactly 31 NEWLY authored runtime rows,
     one per unique misconception id (a bijection between rows and the 31-id manifest), each two_vote_required
     and quran_example:null (fresh constructed Arabic paradigm practice, no invented occurrence claim).
  3. Every runtime row round-trips through the REAL ordinary tutor grader (tools.fusha_tutor_runtime, imported
     and called directly — never mocked): a full-content-correct answer is content_mastered=True,
     held_for_fact_gate=True, cleared=False, outcome='hold', and never enters progress.missed; a right answer
     with WRONG reasoning fails; every authored accepted_variant also clears content; a forbidden (wrong
     weak-rule/voice/governor/deputy-agent reason) answer is a true miss routed to this drill's own
     remediation_route.
  4. Every hard-grammar (here: every) row is two_vote_required and STAYS held even with an explicit, self-
     declared agreeing second_check — a learner declaration never substitutes for the external two-vote fact
     gate (ROUND-11 invariant re-asserted here for this batch's own rows).
  5. The nine voice/deputy-agent rows (L4.M1.06 melody + L4.M1.07 deputy-agent function) carry `ordered_slots`
     and reject the hostile nominative<->accusative / active<->passive relation-reversal of their own answer,
     while still accepting every authored correct form — voice and deputy-agent-function are direction-
     sensitive planes, not bags of words.
  6. Seven new precise KCs (one per lesson family, never one blanket "weak verbs" KC) are integrated append-
     only into curriculum/kc-catalog.json with a non-auto_safe default_gate; every row's kc_id resolves through
     the REAL catalog and REAL fusha_tutor_runtime gate-check (tools.fusha_tutor_runtime._check_kc_gate_row),
     and every row resolves to this drill as its remediation_route.
  7. No row enters curriculum/assessment/*.jsonl (the real quarantine check, tools.validate_drill_keys), and no
     row's answer text overlaps a FUSHA-BENCH quarantined placement probe (the real tools.fusha_bench functions
     answer_exposures / ensure_no_quarantine_overlap, run against the real eval/fusha-bench-v1 quarantine).
  8. No candidate-provenance or public-projection-promotion marker appears in any row or KC entry; a dry run
     writes nothing, and the REAL runtime CLI/selector (tools.fusha_tutor_runtime.main via --select) round-
     trips over the real bank file without exception.
  9. The eleven pre-existing keyed drill files and the pre-existing prefix of curriculum/kc-catalog.json remain
     byte-identical to the batch's start SHA; no file outside the six exclusive-writable paths changes.

RED (this round): none of the writable-set files exist yet (the bank, the drill markdown, the seven new KC
catalog entries), so this suite is expected to fail/error end-to-end. It must NOT be run yet — the orchestrator
runs it and records the red result before implementation.

Run: python3 tools/test_weak_root_voice_runtime.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_tutor_runtime as RT  # noqa: E402
from tools import validate_drill_keys as VDK  # noqa: E402
from tools import fusha_bench as FB  # noqa: E402
from tools import leak_sot  # noqa: E402

_START_SHA = "647390b619e444c69960b32cb46b8a29e03027cd"
_MISCONCEPTION_REGISTRY = os.path.join(_REPO, "curriculum", "l1l6", "misconceptions",
                                       "misconception-registry.jsonl")
_KEYS_PATH = os.path.join(_REPO, "curriculum", "drills", "keys", "weak-root-voice-runtime.keys.jsonl")
_DRILL_PATH = os.path.join(_REPO, "curriculum", "drills", "weak-root-voice-runtime.md")
_DRILL_ROUTE = "curriculum/drills/weak-root-voice-runtime.md"
_KC_CATALOG_PATH = os.path.join(_REPO, "curriculum", "kc-catalog.json")

# --------------------------------------------------------------------------- the deterministic manifest
# Exact lesson -> misconception-id manifest from the task brief (31 unique ids; mc-0278 is shared by two
# lessons and must resolve to exactly ONE runtime row / ONE kc_id — never duplicated as two KCs).
LESSON_ORDER = ["L4.M1.01", "L4.M1.02", "L4.M1.03", "L4.M1.04", "L4.M1.05", "L4.M1.06", "L4.M1.07"]

LESSON_MC_IDS = {
    "L4.M1.01": ["mc-0119", "mc-0129", "mc-0242", "mc-0592"],
    "L4.M1.02": ["mc-0234", "mc-0278", "mc-0353", "mc-0891"],
    "L4.M1.03": ["mc-0076", "mc-0225", "mc-0355", "mc-0674", "mc-0899"],
    "L4.M1.04": ["mc-0145", "mc-0356", "mc-0653", "mc-0709", "mc-0859"],
    "L4.M1.05": ["mc-0173", "mc-0278", "mc-0354", "mc-0654", "mc-0898"],
    "L4.M1.06": ["mc-0031", "mc-0251", "mc-0348", "mc-0398", "mc-0422"],
    "L4.M1.07": ["mc-0176", "mc-0250", "mc-0423", "mc-0806"],
}
SHARED_MC_ID = "mc-0278"
SHARED_MC_LESSONS = ("L4.M1.02", "L4.M1.05")

ALL_MC_OCCURRENCES = [mc for lesson in LESSON_ORDER for mc in LESSON_MC_IDS[lesson]]
ALL_UNIQUE_MC_IDS = sorted(set(ALL_MC_OCCURRENCES))

# canonical-unit inputs named in the task brief (documentation/pinning only; these units are never edited here).
LESSON_CANONICAL_UNITS = {
    "L4.M1.01": ["u-s01", "u-s02", "u-s06", "u-s07"],
    "L4.M1.02": ["u-n01", "u-s06", "u-s07", "u-s09"],
    "L4.M1.03": ["cu-geminate-jussive-variants", "u-s06", "u-s07", "u-s09"],
    "L4.M1.04": ["cu-hamza-carrier-licensing", "u-s01", "u-s06", "u-s07"],
    "L4.M1.05": ["cu-weak-rule-composition", "u-s06", "u-s07"],
    "L4.M1.06": ["cu-voice-melody-templates", "u-n01", "u-s02", "u-s07"],
    "L4.M1.07": ["cu-agent-vs-deputy-discrimination", "u-n01", "u-n03", "u-n08", "u-n09", "u-n10"],
}

# one precise KC per lesson family (never one blanket "weak verbs" KC).
LESSON_KC_ID = {
    "L4.M1.01": "kc-assimilated-verb-radical-scope",
    "L4.M1.02": "kc-defective-verb-suffix-and-jussive-shift",
    "L4.M1.03": "kc-geminate-verb-merger-licensing",
    "L4.M1.04": "kc-hamzated-verb-carrier-and-imperfect",
    "L4.M1.05": "kc-doubly-weak-verb-subtype-composition",
    "L4.M1.06": "kc-passive-voice-melody-and-argument-promotion",
    "L4.M1.07": "kc-deputy-agent-function-discrimination",
}
NEW_KC_IDS = tuple(LESSON_KC_ID[l] for l in LESSON_ORDER)

LESSON_SARF_ROUTE = {
    "L4.M1.01": "sarf/procedures/weak-root.md", "L4.M1.02": "sarf/procedures/weak-root.md",
    "L4.M1.03": "sarf/procedures/doubled-root.md", "L4.M1.04": "sarf/procedures/hamza-root.md",
    "L4.M1.05": "sarf/procedures/weak-root.md", "L4.M1.06": "sarf/procedures/verb-form.md",
    "L4.M1.07": "sarf/procedures/verb-form.md",
}
LESSON_NAHW_ROUTE = {
    "L4.M1.01": None, "L4.M1.02": None, "L4.M1.03": None, "L4.M1.04": None, "L4.M1.05": None,
    "L4.M1.06": "nahw/procedures/irab-case-mood.md", "L4.M1.07": "nahw/procedures/irab-case-mood.md",
}
# the two lessons whose rows assert a direction-sensitive plane (voice melody / deputy-agent case) and must
# therefore carry `ordered_slots` and reject a hostile nominative<->accusative / active<->passive swap.
DIRECTION_SENSITIVE_LESSONS = ("L4.M1.06", "L4.M1.07")

# exact registry anchors: (lesson_id, pattern) pinned against the REAL committed misconception registry —
# a real-content regression guard, not a mock. Collected by direct inspection of
# curriculum/l1l6/misconceptions/misconception-registry.jsonl at the batch's start SHA.
MISCONCEPTION_ANCHORS = {
    "mc-0119": ("L4.M1.01", "building a long imperative with a prosthetic hamza"),
    "mc-0129": ("L4.M1.01", "carrying the first-position weak consonant into the Form I imperfect"),
    "mc-0242": ("L4.M1.01", "extending deletion to the derived forms"),
    "mc-0592": ("L4.M1.01", "reading a retained weak consonant after the prefix as if the verb were still Form I"),
    "mc-0234": ("L4.M1.02", "exchanging the two subtype vowels in the imperfect"),
    "mc-0278": ("L4.M1.02", "forming the masculine plural past without the final-radical shift"),
    "mc-0353": ("L4.M1.02", "keeping the final weak consonant under a jussive operator"),
    "mc-0891": ("L4.M1.02", "writing a suffixed past cell with the long alif of the bare past"),
    "mc-0076": ("L4.M1.03", "assuming one imperfect middle vowel for the whole class"),
    "mc-0225": ("L4.M1.03", "dropping the gemination mark in the imperfect"),
    "mc-0355": ("L4.M1.03", "keeping the geminate before a consonant-initial suffix"),
    "mc-0674": ("L4.M1.03", "separating the radicals in a cell that should merge"),
    "mc-0899": ("L4.M1.03", "writing the indicative shape after a jussive operator"),
    "mc-0145": ("L4.M1.04", "choosing the wrong carrier for the hamza"),
    "mc-0356": ("L4.M1.04", "keeping the hamza in the three stored imperatives"),
    "mc-0653": ("L4.M1.04", "restoring a hamza into the imperfect of the irregular member"),
    "mc-0709": ("L4.M1.04", "treating a hamza-bearing root as a weak root"),
    "mc-0859": ("L4.M1.04", "using the singular carrier in the plural cells of a final-hamza verb"),
    "mc-0173": ("L4.M1.05", "conflating the two subtypes' imperfect shapes"),
    "mc-0354": ("L4.M1.05", "keeping the final weak radical under a jussive operator"),
    "mc-0654": ("L4.M1.05", "restoring the first weak radical into the imperfect of the separated subtype"),
    "mc-0898": ("L4.M1.05", "writing the indefinite active participle with a visible final radical"),
    "mc-0031": ("L4.M1.06", "applying the ordinary melody to a medial-weak stem"),
    "mc-0251": ("L4.M1.06", "failing to agree the passive verb with the promoted argument"),
    "mc-0348": ("L4.M1.06", "keeping the active prefix vowel in the imperfect passive"),
    "mc-0398": ("L4.M1.06", "leaving the active vowel melody in place while treating the sentence as passive"),
    "mc-0422": ("L4.M1.06", "leaving the promoted argument in the accusative"),
    "mc-0176": ("L4.M1.07", "confusing a following prepositional phrase with the deputy agent"),
    "mc-0250": ("L4.M1.07", "failing to agree the passive verb with its deputy agent"),
    "mc-0423": ("L4.M1.07", "leaving the promoted element in the accusative"),
    "mc-0806": ("L4.M1.07", "using an active verb melody with a nominative patient"),
}


def _home_lesson_of(mc_id):
    """First-occurrence-wins home lesson (L4.M1.02 for the shared mc-0278) — the lesson whose KC actually
    owns the single runtime row for this misconception id."""
    for lesson in LESSON_ORDER:
        if mc_id in LESSON_MC_IDS[lesson]:
            return lesson
    return None


# forbidden marker KEYS (checked as dict keys, not JSON substrings, so the legitimate
# `curriculum_misconception_ids` field — which already ships safely in curriculum/kc-catalog.json — is never
# confused with a banned candidate-pipeline provenance field like the singular `misconception_id`).
FORBIDDEN_ROW_KEYS = frozenset({
    "misconception_id", "candidate_id", "candidate_drill_id", "curriculum_l1l6_id",
    "candidate_provenance", "source_misconception", "drill_id", "status",
    "public_export_allowed", "certified", "promoted_to_assessment",
})


def _expected_new_kc_entries():
    """The exact seven new KC catalog entries this batch integrates (append-only) into
    curriculum/kc-catalog.json — one precise KC per lesson family, never one blanket "weak verbs" KC."""
    common = {"drill_route": _DRILL_ROUTE, "severity": "warn", "default_gate": "human_source_review_required",
              "cefr_band": "C1"}

    def entry(lesson, kc_id, name, plain_rule, trigger, expected, typical, point, teach, bottom_out,
              diag_class, topic, example):
        return dict(common, kc_id=kc_id, arabic_grammar_name=name, plain_rule=plain_rule,
                    trigger_condition=trigger, expected_feature=expected, typical_error_feature=typical,
                    point_template=point, teach_template=teach, bottom_out_template=bottom_out,
                    grammar_topic=topic, diagnostic_classes=[diag_class],
                    sarf_route=LESSON_SARF_ROUTE[lesson], nahw_route=LESSON_NAHW_ROUTE[lesson],
                    curriculum_misconception_ids=list(LESSON_MC_IDS[lesson]),
                    curriculum_error_examples=[{"kind": "error_pattern", "en": example}])

    return [
        entry("L4.M1.01", "kc-assimilated-verb-radical-scope",
              "assimilated (mithāl) verb — Form I imperfect first-radical deletion",
              "In Form I only, an assimilated verb whose first radical is wāw deletes that radical in the "
              "imperfect when the stem vowel is /i/ or /u/; the derived-form/imperative rebuilding this "
              "deletion licenses is scoped to that same Form I imperfect cell — it is never extended to Forms "
              "II-X, to the corresponding imperative of a stem that already opens on a voweled consonant, or "
              "read back as if a derived form's retained first radical meant the verb was still Form I.",
              "a Form I assimilated verb's imperfect, imperative, or a derived-form (II-X) cell built on the "
              "same root is being formed and the deletion rule's Form-I-only scope has not been checked",
              "the imperfect first-radical deletion applied only to the Form I imperfect cell it is licensed "
              "for, with derived forms and the imperative correctly excluded or re-derived from their own "
              "template",
              "the deletion extended to a derived (II-X) form, a prosthetic hamza added to an imperative stem "
              "that already opens on a voweled consonant, or a derived form's retained first radical misread "
              "as evidence the verb is still Form I",
              "Before you touch the first radical, check which form (I or derived) and which cell "
              "(imperfect/imperative) you are actually building.",
              "First-radical wāw-deletion is a Form I imperfect fact only; the imperative built from a "
              "deleted stem needs no prosthetic hamza, derived forms (II-X) keep the first radical because "
              "they never delete it, and a retained first radical after a derived-form prefix is not a sign "
              "the verb reverted to Form I.",
              "Name the form and the cell, then state whether first-radical deletion applies there.",
              "assimilated_verb_deletion_scope_error", "weak_root_morphology",
              "A learner treats the Form I imperfect deletion rule as if it applied to a Form II-X verb "
              "sharing the same root, wrongly dropping the first radical from a derived form that never "
              "deletes it."),
        entry("L4.M1.02", "kc-defective-verb-suffix-and-jussive-shift",
              "defective (nāqiṣ) verb — subtype vowel, jussive deletion, and suffix-triggered shift",
              "A defective verb's imperfect middle/final vowel is a lexically stored subtype fact, never "
              "interchangeable between subtypes; its jussive/imperative is formed by deleting the final weak "
              "radical outright rather than adding sukūn to it; and a consonant-initial suffix on the past "
              "stem (e.g. the masculine plural wāw) forces the weak final radical to shift/reappear rather "
              "than leaving the bare past's long vowel in place.",
              "a defective verb's imperfect subtype vowel, its jussive/imperative form, or a suffixed past "
              "cell is being produced and the subtype-specific vowel, the deletion rule, or the "
              "suffix-triggered shift has not been checked against this verb's own lexical entry",
              "the subtype's own stored vowel used (never swapped for the other subtype's), the final weak "
              "radical deleted (not merely marked with sukūn) under a jussive/imperative operator, and the "
              "suffix-triggered shift applied before a consonant-initial suffix",
              "the two subtype vowels exchanged, the final weak consonant kept visible under a jussive "
              "operator, or a suffixed past cell written with the bare past's long alif instead of the "
              "shifted consonant the suffix licenses",
              "Before you write this cell, check the verb's own subtype vowel and whether a jussive operator "
              "or a consonant-initial suffix is acting on it.",
              "Nāqiṣ subtype vowels are stored per verb, not interchangeable; the jussive/imperative is "
              "exponed by deleting the final radical outright; and a consonant-initial suffix forces the "
              "underlying weak radical back, so the bare past's long vowel is not available in that cell.",
              "Name the subtype vowel, then state what the jussive/imperative or the suffix does to the "
              "final radical.",
              "defective_verb_subtype_or_shift_error", "weak_root_morphology",
              "A learner writes the masculine plural past of a defective verb with the bare past's final "
              "long vowel instead of the consonant the suffix forces back, producing a non-existent "
              "past-tense cell."),
        entry("L4.M1.03", "kc-geminate-verb-merger-licensing",
              "geminate (muḍaʿʿaf) verb — merger/separation licensing and the jussive shapes",
              "A geminate verb's imperfect vowel is a lexically stored fact, not predictable from the class; "
              "its gemination realizes two root consonants and is never dropped as if optional; the two "
              "identical radicals merge only where the following element is NOT a bare consonant-initial "
              "suffix, and separate only where a consonant-initial suffix follows — reversing this licensing "
              "stacks or drops a radical; and merged-with-fatḥa and separated-with-sukūn are two SECURELY "
              "licensed jussive shapes of a geminate verb — this pair is taught as securely licensed "
              "examples, not as a claim that they exhaust the complete classical geminate-jussive inventory; "
              "whether a further merged-vowel shape (kasra-merged or ḍamma-merged, by itbāʿ) is also a "
              "licensed jussive alternative, or is simply the bare indicative, is a disputed, open "
              "scholar-review question this KC does not settle.",
              "a geminate verb's imperfect vowel, its merger/separation, or its jussive shape is being "
              "produced and the per-verb vowel or the suffix-conditioned merger licensing has not been "
              "checked",
              "the verb's own stored imperfect vowel used, merger applied only where no consonant-initial "
              "suffix follows and separation only where one does, and the jussive limited to its securely "
              "licensed shapes",
              "one uniform imperfect vowel assumed for the whole class, the gemination mark dropped as if "
              "decorative, merger and separation licensing reversed against the following suffix, or the "
              "jussive operator's effect ignored altogether as if the geminate verb's shape never changes "
              "from the indicative",
              "Before you write this cell, check the verb's own stored vowel and what actually follows the "
              "second radical.",
              "The geminate imperfect vowel is stored per verb; gemination realizes two radicals and is "
              "never optional; a consonant-initial suffix forces separation and blocks merger; and "
              "merged-with-fatḥa and separated-with-sukūn are two securely licensed jussive shapes — "
              "without this being a claim that no other merged-vowel shape (kasra- or ḍamma-merged, by "
              "itbāʿ) is ever licensed; that wider question is disputed and awaits scholar review, not "
              "settled here either way.",
              "State the stored vowel, then justify merger or separation from what follows, then name the "
              "licensed jussive shape.",
              "geminate_verb_merger_or_jussive_error", "weak_root_morphology",
              "A learner keeps a geminate verb's two identical radicals merged even though a consonant-"
              "initial suffix follows, stacking a doubled consonant against a vowelless one."),
        entry("L4.M1.04", "kc-hamzated-verb-carrier-and-imperfect",
              "hamzated (mahmūz) verb — carrier selection and stored irregular cells",
              "A hamzated verb's hamza carrier is selected by the vowels in its immediate environment, never "
              "a free spelling choice, and that carrier is re-evaluated after every affixation; a small "
              "closed set of hamzated verbs additionally have stored irregular imperatives (formed without "
              "the hamza) and, for one member, a stored irregular imperfect with no hamza at all — lexical "
              "facts to check, not outputs of the regular carrier rule; and a hamza radical is a separate "
              "class from the weak (wāw/yāʾ) radicals, so weak-root rules never transfer to it.",
              "a hamzated verb's carrier, its imperative, its imperfect, or its root classification is being "
              "decided and the vowel-environment carrier rule, the small stored-irregular list, or the "
              "hamza-vs-weak-root distinction has not been checked",
              "the carrier chosen from the immediate vowel environment and re-checked after affixation, the "
              "stored irregular imperatives (and the one stored irregular imperfect) used as lexical facts "
              "rather than derived, and a hamza radical never treated as a weak radical",
              "the wrong carrier chosen or kept unchanged after a plural suffix, a regular hamza restored "
              "into a cell that is lexically hamza-less, or a hamza-bearing root run through a weak-root rule",
              "Before you write the hamza, check the vowels immediately around it and whether this cell is "
              "one of the small stored-irregular ones.",
              "The hamza carrier is decided by its immediate vowel environment and must be re-checked after "
              "every affixation; a short stored list of hamzated verbs has irregular imperatives (and one an "
              "irregular imperfect) with no hamza at all; and a hamza radical is a separate class from the "
              "weak radicals, so weak-root rules do not transfer to it.",
              "Name the carrier from its vowel environment (or the stored irregular form), then confirm the "
              "root's class is hamza, not weak.",
              "hamzated_verb_carrier_or_classification_error", "weak_root_morphology",
              "A learner restores a regular hamza into the imperfect of one of the few hamzated verbs that "
              "are lexically stored without a hamza there at all."),
        entry("L4.M1.05", "kc-doubly-weak-verb-subtype-composition",
              "doubly weak (lafīf) verb — subtype composition",
              "A lafīf verb's subtype (maqrūn/mafrūq — which two positions carry the weak radicals) is "
              "assigned from the positions of its weak radicals before conjugating, and the two subtypes' "
              "imperfect stems differ in shape AND length; the separated (mafrūq) subtype deletes its first "
              "weak radical in the imperfect exactly as a plain first-weak (assimilated) verb does, so "
              "restoring it produces a non-word; a lafīf verb's jussive still deletes its final weak radical, "
              "exactly as an ordinary defective verb's does; and in the indefinite, its active participle's "
              "final radical gives way to tanwīn — writing that radical as a visible consonant there is a "
              "spelling error, not a variant.",
              "a lafīf verb's subtype, its imperfect stem, its jussive, or its indefinite active-participle "
              "spelling is being produced and the subtype has not been fixed from the weak-radical positions "
              "first",
              "the subtype assigned from radical position before conjugating, the correct (subtype-specific) "
              "imperfect stem produced, the final weak radical deleted under the jussive, and the indefinite "
              "participle spelled with tanwīn in place of the final radical",
              "the two subtypes' imperfect shapes conflated, the mafrūq subtype's first weak radical wrongly "
              "restored into the imperfect, the final weak radical kept visible under a jussive operator, or "
              "the indefinite active participle written with a visible final radical instead of tanwīn",
              "Before you conjugate a lafīf verb, fix its subtype from the positions of its two weak "
              "radicals.",
              "Lafīf subtype is decided by radical position first; maqrūn and mafrūq imperfects differ in "
              "shape and length; the mafrūq subtype deletes its first radical in the imperfect exactly like a "
              "plain assimilated verb; the jussive still deletes the final radical exactly like a plain "
              "defective verb; and the indefinite active participle spells tanwīn where the final radical "
              "would be, never the radical itself.",
              "Name the subtype, then justify the imperfect stem, the jussive, or the indefinite spelling "
              "from it.",
              "doubly_weak_verb_subtype_error", "weak_root_morphology",
              "A learner conjugates a lafīf verb's imperfect without first checking whether its two weak "
              "radicals are in the maqrūn or mafrūq positions, producing the wrong stem shape and length."),
        entry("L4.M1.06", "kc-passive-voice-melody-and-argument-promotion",
              "passive voice melody (bināʾ lil-majhūl) and promoted-argument case/agreement, in weak-root "
              "stems",
              "Voice is carried entirely by the vowel melody (the prefix vowel together with the vowel "
              "before the final radical, or — for a medial-weak stem — its own distinct passive melody), "
              "never by argument marking alone; a medial-weak (hollow) stem takes its own passive melody and "
              "rejects the sound-stem melody; once an argument is promoted to fill the missing agent slot, it "
              "takes the case a subject takes (nominative, never left accusative) and controls agreement "
              "exactly as an agent would, including the feminine-singular pattern for a non-human plural; and "
              "an active melody left in place states an active proposition however the arguments are marked.",
              "a passive clause's verb melody, or the case/agreement of its promoted argument, is being "
              "produced for a weak-root (specifically medial-weak/hollow) stem and the melody or the "
              "promotion consequence has not been checked",
              "the correct passive melody used for the stem's own class (including the hollow stem's own "
              "passive melody), the promoted argument marked nominative, and agreement controlled by the "
              "promoted argument",
              "the ordinary (sound-stem) passive melody applied to a medial-weak stem, the active prefix "
              "vowel kept in the imperfect passive, an active melody paired with passive-looking argument "
              "marking, the promoted argument left accusative, or the passive verb left unagreed with its "
              "promoted argument",
              "Before you assign case or agreement here, check the verb's own melody first — voice is "
              "decided there.",
              "Voice is exponed by the vowel melody, not by argument marking; a hollow (medial-weak) stem has "
              "its own passive melody, never the sound-stem one; once promoted, the argument takes the "
              "subject's case (nominative) and controls agreement exactly as an agent would; and an active "
              "melody always states an active proposition, regardless of how the arguments happen to be "
              "marked.",
              "Name the melody first, then justify the promoted argument's case and agreement from it.",
              "passive_melody_or_promotion_error", "verb_voice",
              "A learner applies the ordinary sound-stem passive melody to a medial-weak (hollow) verb "
              "instead of that stem's own distinct passive melody."),
        entry("L4.M1.07", "kc-deputy-agent-function-discrimination",
              "deputy agent (nāʾib al-fāʿil) function discrimination",
              "The deputy agent is identified by case and position — the nominative element occupying the "
              "subject position of a passive verb — never by translating into a language whose passive uses "
              "a by-phrase; a following prepositional phrase is a separate constituent in the genitive and is "
              "never itself the deputy agent; the deputy agent controls agreement exactly as an agent does, "
              "including the feminine-singular pattern for a non-human plural; once promoted, an element "
              "takes the case a subject takes (nominative), never the accusative case it had in the active "
              "sentence; and the verb's melody must itself be set to passive.",
              "a passive clause's subject-position element, or the agreement/case it carries, is being "
              "identified and a following prepositional phrase, an unagreed verb, a leftover accusative case, "
              "or the verb's own melody has not been checked",
              "the deputy agent identified by case and position (not by a by-phrase translation), a "
              "following PP correctly excluded as a separate genitive constituent, agreement and nominative "
              "case correctly assigned to the deputy agent, and the verb's melody confirmed passive",
              "a following prepositional phrase mistaken for the deputy agent, the passive verb left "
              "unagreed with its actual deputy agent, the promoted element left in the accusative case it "
              "had in the active sentence, or an active verb melody used with a nominative patient",
              "Before you name the deputy agent, check case and position first, then confirm the verb's own "
              "melody is passive.",
              "The deputy agent is the nominative element in the passive subject position, found from case "
              "and position, never from a by-phrase translation; a following PP is a separate genitive "
              "constituent, not the deputy agent; it controls agreement like any agent; it takes nominative "
              "case, never the accusative it had actively; and the verb's melody itself must be passive for "
              "any of this to cohere.",
              "Name the deputy agent by case and position, confirm the verb's melody is passive, then "
              "justify its case and agreement.",
              "deputy_agent_function_error", "deputy_agent",
              "A learner names the object of a following prepositional phrase as the deputy agent instead of "
              "the nominative element actually occupying the passive subject position."),
    ]


_PRE_EXISTING_KEYED_DRILLS = (
    "followers-coordination-apposition", "hover-composition-and-routing",
    "morphology-foundations", "nawasikh-governor-families", "parse-key-and-color-layer",
    "plan15-route-families", "quranic-function-words", "root-pattern-practice", "sentence-foundations",
    "vn00-aggressive-hover-closure",
)
# NOTE (T1b bounded repair round): foundational-script-orthography was removed from the above byte-identical
# set. It was pre-existing at THIS batch's own start SHA, but the T1b review-repair round (F2/F7) is explicitly
# authorized to edit curriculum/drills/keys/foundational-script-orthography.keys.jsonl and its .md, so it can no
# longer be asserted byte-identical here without contradicting that authorized repair.

# The T1b bounded review-repair round's exclusive writable allowlist (superset of this batch's own six files) —
# every file any of F1-F11 may touch, repo-wide, so this cross-cutting guard reflects the repair's real scope
# rather than only this one batch's original authoring footprint.
_WRITABLE_SET = {
    "curriculum/drills/keys/foundational-script-orthography.keys.jsonl",
    "curriculum/drills/keys/weak-root-voice-runtime.keys.jsonl",
    "curriculum/drills/keys/tranche-001-derivation-template-runtime.keys.jsonl",
    "curriculum/drills/keys/tranche-001-ma-context-runtime.keys.jsonl",
    "curriculum/drills/foundational-script-orthography.md",
    "curriculum/drills/weak-root-voice-runtime.md",
    "curriculum/drills/tranche-001-derivation-template-runtime.md",
    "curriculum/drills/tranche-001-ma-context-runtime.md",
    "curriculum/kc-catalog.json",
    "curriculum/kc-catalog.d/tranche-001-derivation-template.jsonl",
    "curriculum/kc-catalog.d/tranche-001-ma-context.jsonl",
    "curriculum/drills/dogfood-error-remediation-index.md",
    "curriculum/progress/missed-error-log.template.md",
    "tools/fusha_tutor_runtime.py",
    "tools/kc_catalog.py",
    "tools/validate_drill_keys.py",
    "tools/validate_tutor_runtime.py",
    "tools/test_foundational_script_orthography_runtime.py",
    "tools/test_weak_root_voice_runtime.py",
    "tools/test_tranche_001_derivation_template_runtime.py",
    "tools/test_tranche_001_ma_context_runtime.py",
    "tools/test_kc_catalog_shards.py",
    "eval/fusha-bench-v1/data-manifest.json",
    "eval/fusha-bench-v1/tutor-quarantine.json",
    "tools/fusha_bench.py",
    "tools/test_fusha_bench.py",
    "tools/check_regressions.py",
    "docs/review-rubrics/drills-kc.md",
    "dist/claude-ai/knowledge-manifest.md",
}


# --------------------------------------------------------------------------- loaders

def _git_show(path_rel):
    out = subprocess.run(["git", "show", "%s:%s" % (_START_SHA, path_rel)], cwd=_REPO,
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8")


def _load_jsonl_text(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _load_jsonl_file(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _load_runtime_rows():
    return _load_jsonl_file(_KEYS_PATH)


def _load_kc_catalog():
    with open(_KC_CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _rows_by_mc_id():
    rows = _load_runtime_rows()
    by_mc = {}
    for row in rows:
        mcs = row.get("curriculum_misconception_ids") or []
        assert len(mcs) == 1, "%s: expected exactly one traceable misconception id, got %r" % (row["id"], mcs)
        by_mc[mcs[0]] = row
    return by_mc


def _hostile_voice_case_swap(text):
    """Reverse-direction rewrite for the voice/deputy-agent planes: nominative<->accusative AND
    active<->passive, in place, leaving every other word untouched. The exact mirror-image mistake these
    rows exist to catch (promoted-argument case, melody direction)."""
    ph1, ph2 = "\x00NOM\x00", "\x00ACT\x00"
    t = re.sub(r"nominative", ph1, text, flags=re.I)
    t = re.sub(r"accusative", "nominative", t, flags=re.I)
    t = t.replace(ph1, "accusative")
    t = re.sub(r"\bactive\b", ph2, t, flags=re.I)
    t = re.sub(r"\bpassive\b", "active", t, flags=re.I)
    t = t.replace(ph2, "passive")
    return t


# --------------------------------------------------------------------------- 1. manifest pinned to the real registry

class MisconceptionManifestPinnedToRegistry(unittest.TestCase):
    """The deterministic 31-id manifest is authored FROM, and stays pinned to, the real committed registry."""

    def test_manifest_shape(self):
        self.assertEqual(len(LESSON_ORDER), 7)
        self.assertEqual(len(ALL_MC_OCCURRENCES), 32, "32 lesson-occurrences (mc-0278 counted twice)")
        self.assertEqual(len(ALL_UNIQUE_MC_IDS), 31, "31 unique misconception ids")
        self.assertEqual(set(MISCONCEPTION_ANCHORS), set(ALL_UNIQUE_MC_IDS))

    def test_shared_id_contributes_to_exactly_two_lessons_not_more(self):
        lessons_with_shared = [l for l in LESSON_ORDER if SHARED_MC_ID in LESSON_MC_IDS[l]]
        self.assertEqual(tuple(lessons_with_shared), SHARED_MC_LESSONS)
        self.assertEqual(_home_lesson_of(SHARED_MC_ID), "L4.M1.02")

    def test_every_anchor_matches_the_real_registry_file_content(self):
        registry = {}
        with open(_MISCONCEPTION_REGISTRY, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                registry[row["misconception_id"]] = row
        for mc_id, (lesson, pattern) in MISCONCEPTION_ANCHORS.items():
            with self.subTest(mc_id=mc_id):
                self.assertIn(mc_id, registry, "%s missing from the real misconception registry" % mc_id)
                row = registry[mc_id]
                self.assertEqual(row["pattern"], pattern)
                manifestation_lessons = {m["lesson_id"] for m in row["manifestations"]}
                self.assertIn(lesson, manifestation_lessons,
                             "%s: registry manifestations %s do not include %s" %
                             (mc_id, manifestation_lessons, lesson))

    def test_registry_confirms_mc_0278_is_genuinely_shared_not_a_manifest_typo(self):
        registry = {}
        with open(_MISCONCEPTION_REGISTRY, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("misconception_id") == SHARED_MC_ID:
                    registry = row
                    break
        manifestation_lessons = {m["lesson_id"] for m in registry["manifestations"]}
        self.assertEqual(manifestation_lessons, set(SHARED_MC_LESSONS))


# --------------------------------------------------------------------------- 2. runtime batch manifest

class RuntimeBatchManifest(unittest.TestCase):
    """Exactly 31 newly authored runtime rows: one per unique misconception id, no duplication, no drift."""

    def test_exactly_31_runtime_rows_bijective_with_the_31_id_manifest(self):
        rows = _load_runtime_rows()
        self.assertEqual(len(rows), 31)
        ids = [r["id"] for r in rows]
        self.assertEqual(len(set(ids)), 31, "duplicate runtime row ids")
        for rid in ids:
            self.assertFalse(rid.startswith("dr-mc-"), "%r reuses a candidate drill_id identity" % rid)
            self.assertFalse(re.match(r"^mc-\d+$", rid), "%r reuses a misconception id identity" % rid)
        mc_counts = Counter(mc for row in rows for mc in (row.get("curriculum_misconception_ids") or []))
        self.assertEqual(mc_counts, {mc: 1 for mc in ALL_UNIQUE_MC_IDS},
                         "every unique misconception id must trace to EXACTLY one row: no silent drop, no "
                         "duplicate mapping, no unrelated/foreign id")

    def test_every_row_has_the_required_authoring_fields(self):
        required = {"id", "level", "concept", "prompt", "quran_example", "expected_answer", "accepted_variants",
                    "forbidden_answers", "required_reasoning", "sarf_procedure", "nahw_procedure",
                    "remediation_route", "two_vote_required", "explanation", "kc_id",
                    "curriculum_misconception_ids"}
        for row in _load_runtime_rows():
            missing = required - set(row)
            self.assertFalse(missing, "%s missing fields %s" % (row["id"], missing))
            self.assertTrue(row["accepted_variants"])
            self.assertTrue(row["forbidden_answers"])
            self.assertTrue(row["required_reasoning"])
            self.assertTrue(row["explanation"].strip())
            self.assertEqual(row["remediation_route"], _DRILL_ROUTE)

    def test_every_row_quran_example_null_and_two_vote_required(self):
        for row in _load_runtime_rows():
            self.assertIsNone(row["quran_example"],
                             "%s: fresh constructed-Arabic practice must carry quran_example: null (no "
                             "invented occurrence claim)" % row["id"])
            self.assertTrue(row["two_vote_required"], "%s: every row asserts a weak-rule/voice/governor/"
                            "deputy-agent fact and must be two_vote_required" % row["id"])

    def test_every_row_binds_to_its_own_lessons_precise_kc_and_procedures(self):
        by_mc = _rows_by_mc_id()
        for mc_id in ALL_UNIQUE_MC_IDS:
            lesson = _home_lesson_of(mc_id)
            row = by_mc[mc_id]
            with self.subTest(mc_id=mc_id, lesson=lesson):
                self.assertEqual(row["kc_id"], LESSON_KC_ID[lesson])
                self.assertEqual(row["sarf_procedure"], LESSON_SARF_ROUTE[lesson])
                self.assertEqual(row["nahw_procedure"], LESSON_NAHW_ROUTE[lesson])

    def test_mc_0278_bound_to_exactly_one_kc_reused_not_duplicated(self):
        by_mc = _rows_by_mc_id()
        row = by_mc[SHARED_MC_ID]
        self.assertEqual(row["kc_id"], LESSON_KC_ID["L4.M1.02"])
        all_kc_ids_used = {r["kc_id"] for r in _load_runtime_rows()}
        # the shared id's row uses exactly one of the seven precise KCs -- never a bespoke eighth KC.
        self.assertLessEqual(all_kc_ids_used, set(NEW_KC_IDS))

    def test_row_content_traces_meaningfully_to_its_own_misconception_pattern(self):
        """A soft but real content-linkage guard: a bound row's own authored text must cover a meaningful share
        of its misconception's significant vocabulary (paraphrase allowed; a copy-paste stand-in row is not)."""
        by_mc = _rows_by_mc_id()
        for mc_id, (_lesson, pattern) in MISCONCEPTION_ANCHORS.items():
            row = by_mc[mc_id]
            blob = " ".join([row["concept"], row["explanation"], row["expected_answer"],
                             " ".join(row["required_reasoning"])])
            toks = RT._sig_tokens(pattern)
            self.assertTrue(toks, "pattern produced no significant tokens: %r" % pattern)
            hit = sum(1 for t in toks if t in RT._norm(blob))
            coverage = hit / len(toks)
            self.assertGreaterEqual(coverage, 0.3,
                                    "%s: row content covers only %.0f%% of its misconception's own "
                                    "vocabulary (%r)" % (mc_id, coverage * 100, pattern))

    def test_no_forbidden_provenance_or_promotion_keys_on_any_row(self):
        for row in _load_runtime_rows():
            hit = FORBIDDEN_ROW_KEYS & set(row)
            self.assertFalse(hit, "%s: forbidden key(s) present: %s" % (row["id"], sorted(hit)))
            self.assertNotIn("dr-mc-", json.dumps(row, ensure_ascii=False))

    def test_no_leak_sot_hits_in_any_runtime_row(self):
        for row in _load_runtime_rows():
            hits = leak_sot.scan(json.dumps(row, ensure_ascii=False))
            self.assertEqual(hits, [], "%s: leak-SoT hit %s" % (row["id"], hits))

    def test_drill_keys_validator_accepts_the_file_clean(self):
        errs = VDK.validate(_KEYS_PATH)
        self.assertEqual(errs, [])

    def test_drill_markdown_exists_and_documents_every_lesson_and_kc(self):
        self.assertTrue(os.path.exists(_DRILL_PATH))
        with open(_DRILL_PATH, encoding="utf-8") as fh:
            text = fh.read()
        for lesson in LESSON_ORDER:
            self.assertIn(lesson, text, "%s not documented in the drill markdown" % lesson)
        for kc_id in NEW_KC_IDS:
            self.assertIn(kc_id, text, "%s not documented in the drill markdown" % kc_id)
        hits = leak_sot.scan(text)
        self.assertEqual(hits, [])
        self.assertNotIn("dr-mc-", text)


# --------------------------------------------------------------------------- 3. grader round trip (real runtime)

class RuntimeGraderRoundTrip(unittest.TestCase):
    """Every one of the 31 rows round-trips through the REAL tools.fusha_tutor_runtime.grade()/step()."""

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
                    g = RT.grade(row, {"answer": variant, "reasoning": list(row["required_reasoning"])})
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
        for row in self.rows:
            for i, bad in enumerate(row["forbidden_answers"]):
                with self.subTest(id=row["id"], forbidden=i):
                    payload = {"answer": bad, "reasoning": []}
                    r = RT.step(row, None, payload, now_day=0)
                    g = r["grade"]
                    self.assertFalse(g["cleared"], row["id"])
                    self.assertFalse(g["held_for_fact_gate"],
                                    "%s: a forbidden (wrong weak-rule/voice/governor/deputy-agent reason) "
                                    "answer is a real miss, not a fact hold" % row["id"])
                    progress = RT.new_progress()
                    RT.apply_event_to_progress(progress, row, r, seq=0)
                    missed = {m["item_id"]: m for m in progress["missed"]}
                    self.assertIn(row["id"], missed, row["id"])
                    self.assertEqual(missed[row["id"]]["remediation_route"], _DRILL_ROUTE)
                    self.assertEqual(missed[row["id"]]["error_reason"], row["kc_id"])


# --------------------------------------------------------------------------- 4. hard-grammar two-vote held

class HardGrammarTwoVoteAlwaysHeld(unittest.TestCase):
    """Every row is two_vote_required and STAYS held even with a self-declared agreeing second_check — a
    learner declaration never clears the external two-vote fact gate (ROUND-11 invariant)."""

    def test_declared_agreement_never_clears_any_row(self):
        for row in _load_runtime_rows():
            with self.subTest(id=row["id"]):
                self.assertTrue(row["two_vote_required"])
                payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"]),
                          "second_check": {"conclusion_agrees": True, "reason_agrees": True}}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertEqual(g["two_vote_status"], "pending")
                self.assertFalse(g["cleared"])
                self.assertTrue(g["held_for_fact_gate"])
                self.assertEqual(r["outcome"], "hold")
                self.assertIs(g["second_check_declared"], True)

    def test_catalog_gate_rule_agrees_via_the_real_runtime_helper(self):
        """Reuses tools.fusha_tutor_runtime._check_kc_gate_row directly (the same function the runtime's own
        --self-test uses) rather than re-implementing the gate logic in this test."""
        kc_by_id = {kc["kc_id"]: kc for kc in _load_kc_catalog()}
        failures = []
        for row in _load_runtime_rows():
            failures.extend(RT._check_kc_gate_row(row, kc_by_id))
        self.assertEqual(failures, [])


# --------------------------------------------------------------------------- 4b. F1: geminate jussive inventory
class GeminateJussiveInventoryNoContradiction(unittest.TestCase):
    """F1: WRV-12 and WRV-13 must never teach a licensed geminate-verb form as forbidden. WRV-13 asserts BOTH
    the merged-with-fatha (لَمْ يَمُدَّ) and separated-with-sukun (لَمْ يَمْدُدْ) jussive shapes are licensed;
    WRV-12 must therefore never forbid the separated jussive shape, and must instead test the genuinely
    distinct obligatory-merger environment (a vowel immediately follows the second radical)."""

    def _row(self, item_id):
        return {r["id"]: r for r in _load_runtime_rows()}[item_id]

    def test_wrv13_licenses_both_geminate_jussive_shapes(self):
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        for licensed in ("لَمْ يَمُدَّ", "لَمْ يَمْدُدْ"):
            self.assertIn(licensed, row["expected_answer"],
                         "WRV-13 must name both licensed jussive shapes: %r" % licensed)

    def test_wrv12_never_forbids_wrv13s_licensed_separated_jussive_shape(self):
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        forbidden_blob = " ".join(row12["forbidden_answers"])
        self.assertNotIn("لَمْ يَمْدُدْ", forbidden_blob,
                        "WRV-12 must never forbid WRV-13's own licensed separated jussive shape (لَمْ يَمْدُدْ)")

    def test_wrv12_targets_the_obligatory_merger_vowel_following_cell_not_the_jussive_cell(self):
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        # WRV-12 must no longer overlap WRV-13's own jussive-after-lam cell (the actual site of the
        # contradiction); it now targets a cell where a vowel follows the second radical (merger obligatory).
        self.assertNotIn("لَمْ", row12["expected_answer"])
        self.assertIn("يَمُدُّونَ", row12["expected_answer"])

    def test_wrv12_hostile_separated_form_in_the_vowel_following_cell_is_rejected(self):
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        payload = {"answer": "يَمْدُدُونَ — the radicals separate here.",
                  "reasoning": list(row12["required_reasoning"])}
        g = RT.grade(row12, payload)
        self.assertFalse(g["content_mastered"], "a separated form must not clear in an obligatory-merger cell")

    def test_wrv13_teaches_no_exhaustive_only_or_exactly_claim(self):
        # R2: the Opus targeted re-review and the independent Sonnet linguistic vote DISAGREE on whether the
        # merged geminate-jussive inventory is limited to exactly these two shapes (a further kasra/damma-by-
        # itbaa merged variant is contested). WRV-13 and its KC must teach the merged-fatha/separated-sukun
        # pair as SECURELY licensed examples without asserting they exhaust the classical inventory.
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        kc = {kc["kc_id"]: kc for kc in _load_kc_catalog()}["kc-geminate-verb-merger-licensing"]
        exhaustive_phrases = ("exactly two", "only two licensed", "only two shapes",
                              "the two licensed jussive shapes")
        for label, blob in (
            ("WRV-13 prompt", row["prompt"]),
            ("WRV-13 concept", row["concept"]),
            ("WRV-13 expected_answer", row["expected_answer"]),
            ("WRV-13 accepted_variants", " ".join(row["accepted_variants"])),
            ("WRV-13 forbidden_answers", " ".join(row["forbidden_answers"])),
            ("WRV-13 required_reasoning", " ".join(row["required_reasoning"])),
            ("WRV-13 explanation", row["explanation"]),
            ("kc-geminate-verb-merger-licensing plain_rule", kc["plain_rule"]),
            ("kc-geminate-verb-merger-licensing typical_error_feature", kc["typical_error_feature"]),
            ("kc-geminate-verb-merger-licensing teach_template", kc["teach_template"]),
        ):
            low = blob.lower()
            for phrase in exhaustive_phrases:
                self.assertNotIn(phrase, low, "%s must not assert an exhaustive inventory claim (%r)"
                                 % (label, phrase))

    def test_wrv13_and_kc_no_longer_hard_settle_the_disputed_vowel_question(self):
        # R3: "not a jussive option at all" (and its ḍamma-specific framing) was the exact language that hard-
        # settled the disputed ḍamma-merged question in the Sonnet vote's favor while claiming the disagreement
        # was preserved. A bounded repair that genuinely preserves the disagreement must not use it anywhere.
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        kc = {kc["kc_id"]: kc for kc in _load_kc_catalog()}["kc-geminate-verb-merger-licensing"]
        banned_phrases = ("not a jussive option at all", "not a jussive shape at all",
                          "simply the indicative, not a jussive")
        for label, blob in (
            ("WRV-13 prompt", row["prompt"]),
            ("WRV-13 concept", row["concept"]),
            ("WRV-13 expected_answer", row["expected_answer"]),
            ("WRV-13 accepted_variants", " ".join(row["accepted_variants"])),
            ("WRV-13 forbidden_answers", " ".join(row["forbidden_answers"])),
            ("WRV-13 required_reasoning", " ".join(row["required_reasoning"])),
            ("WRV-13 explanation", row["explanation"]),
            ("kc-geminate-verb-merger-licensing plain_rule", kc["plain_rule"]),
            ("kc-geminate-verb-merger-licensing typical_error_feature", kc["typical_error_feature"]),
            ("kc-geminate-verb-merger-licensing teach_template", kc["teach_template"]),
        ):
            low = blob.lower()
            for phrase in banned_phrases:
                self.assertNotIn(phrase, low, "%s must not hard-settle the disputed vowel question (%r)"
                                 % (label, phrase))

    def test_wrv13_prompt_does_not_presuppose_the_disputed_form_is_an_error(self):
        # R3: asking a learner to "correct" a specific disputed surface presupposes it is wrong, which is
        # itself picking a side of the unresolved disagreement -- even without a matching forbidden_answers
        # entry. The prompt must ask for the safe intersection, never stage a disputed form as a mistake.
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        prompt_low = row["prompt"].lower()
        for phrase in ("correct this", "a learner writes", "correct a learner"):
            self.assertNotIn(phrase, prompt_low,
                             "WRV-13's prompt must not frame a disputed surface as something to correct: %r"
                             % phrase)
        self.assertNotIn("يَمُدُّ", row["prompt"],
                         "WRV-13's prompt must not single out the disputed ḍamma-merged surface at all")

    def test_wrv13_does_not_hard_reject_the_disputed_kasra_merged_variant(self):
        # R2: the disputed variant (Opus: possibly licensed by itbaa; Sonnet: not licensed) must be neither
        # accepted nor hard-rejected by this bounded repair -- it must stay an open scholar-review question, so
        # a learner mentioning it must not trigger forbidden_hit.
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        disputed_kasra_merged = "لَمْ يَمُدِّ"
        blob = " ".join(row["forbidden_answers"]).lower()
        self.assertNotIn(disputed_kasra_merged, blob,
                         "the disputed kasra-merged variant must not appear as a forbidden (hard-rejected) form")
        g = RT.grade(row, {"answer": "some describe a disputed kasra-merged form %s as licensed by itbaa"
                                     % disputed_kasra_merged,
                          "reasoning": list(row["required_reasoning"])})
        self.assertFalse(g["forbidden_hit"], "mentioning the disputed variant must not be graded a forbidden hit")

    def test_wrv13_does_not_hard_reject_the_disputed_damma_merged_variant(self):
        # R3: the ḍamma-merged variant (لَمْ يَمُدُّ) is EQUALLY disputed -- an Opus 5 review and an independent
        # Sonnet 5 vote disagree on whether it is a further itbaa-licensed jussive shape or simply the bare
        # indicative -- so it must be neither accepted nor hard-rejected either, the exact residual this test
        # closes (the prior repair kept a hard-reject of this specific surface while claiming the disagreement
        # was preserved).
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        disputed_damma_merged = "لَمْ يَمُدُّ"
        blob = " ".join(row["forbidden_answers"]).lower()
        self.assertNotIn(disputed_damma_merged, blob,
                         "the disputed ḍamma-merged variant must not appear as a forbidden (hard-rejected) form")
        g = RT.grade(row, {"answer": "some describe a disputed ḍamma-merged form %s as licensed by itbaa"
                                     % disputed_damma_merged,
                          "reasoning": list(row["required_reasoning"])})
        self.assertFalse(g["forbidden_hit"], "mentioning the disputed variant must not be graded a forbidden hit")

    def test_wrv13_still_rejects_the_uncontested_no_change_misconception(self):
        # both reviews agree a geminate verb's jussive is NEVER identical to the indicative in every cell (the
        # separated-sukun shape alone disproves "no change") -- that genuinely uncontested misconception, unlike
        # any specific disputed vowel realization, must still be rejected.
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        g = RT.grade(row, {"answer": "the jussive of a geminate verb always keeps the indicative's ending "
                                     "unchanged.",
                          "reasoning": list(row["required_reasoning"])})
        self.assertFalse(g["content_mastered"])

    def test_wrv13_unresolved_wider_question_variant_is_content_mastered_but_held(self):
        # required repair #4: an accepted variant names the wider kasra/damma question as unresolved while
        # still supplying a secure example; the REAL grader must content-master it (right answer + right
        # reasoning, no forbidden hit) yet still HOLD it for the mandatory two-vote fact gate -- content mastery
        # is not fact certification.
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        variant = next((v for v in row["accepted_variants"] if "unresolved" in v.lower()), None)
        self.assertIsNotNone(variant, "expected an accepted variant naming the wider question unresolved")
        g = RT.grade(row, {"answer": variant, "reasoning": list(row["required_reasoning"])})
        self.assertTrue(g["content_mastered"], "the unresolved-question variant must be content-mastered: %s" % g)
        self.assertTrue(g["held_for_fact_gate"], "it must still be HELD pending the two-vote fact gate: %s" % g)
        self.assertFalse(g["cleared"], "content mastery must never auto-clear a two_vote_required row: %s" % g)

    def test_wrv13_records_the_honest_scholar_review_blocker(self):
        row = self._row("WRV-13-mudaaf-jussive-licensed-shapes")
        self.assertIn("scholar review", row["explanation"].lower())

    def test_wrv12_correct_merged_form_still_clears_content(self):
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        payload = {"answer": row12["expected_answer"], "reasoning": list(row12["required_reasoning"])}
        g = RT.grade(row12, payload)
        self.assertTrue(g["content_mastered"])


# --------------------------------------------------------------------------- 4b2. Sonnet repair: two surviving
# semantic mirrors of the WRV-13 adjudication (Train C remediation-index row + WRV-12's own exhaustive claim)
class SonnetMirrorAdjudicationRepairGuard(unittest.TestCase):
    """Two surviving semantic mirrors of the disputed WRV-13 kasra/damma-merged jussive adjudication, found by
    Opus targeted re-review after the prior Sonnet repair:
    (1) the Train C emittable remediation-index row for kc-geminate-verb-merger-licensing said an indicative
        ḍamma-marked form is "mistaken for a jussive" — delivering the disputed Sonnet-side adjudication as
        learner-facing remediation text, contradicting WRV-13's own unresolved posture.
    (2) WRV-12's own concept/explanation asserted the jussive/imperative cell has its "own two licensed
        shapes" — an exhaustive-inventory claim one row above WRV-13's explicit disclaimer that the pair does
        not exhaust the classical inventory.
    Both must keep teaching the secure merger/separation distinction with concrete examples while explicitly
    routing the wider merged-vowel inventory question to unresolved scholar review — never accepting,
    hard-rejecting, or silently settling the disputed reading. These checks scan for the underlying MEANING
    (a closed set of paraphrases), not one exact phrase, so a superficial reword cannot silently reintroduce
    either defect."""

    # paraphrases of "this disputed form is settled as indicative-only / not a jussive" — the exact defect in
    # the Train C row and the exact class of language WRV-13 itself already had to be repaired to drop.
    _HARD_SETTLE_PHRASES = (
        "mistaken for a jussive", "form mistaken for", "is simply indicative, not a jussive",
        "damma-marked form is invalid", "damma-marked form is indicative only",
        "damma-marked form is indicative-only", "not a jussive option at all", "not a jussive shape at all",
        "simply the indicative, not a jussive", "is not a licensed jussive", "is not licensed as a jussive",
    )
    # paraphrases of "this pair is the complete/only licensed inventory for that cell".
    _EXHAUSTIVE_PHRASES = (
        "exactly two", "only two licensed", "only two shapes", "the two licensed jussive shapes",
        "own two licensed shapes", "has its own two licensed shapes", "exactly two licensed shapes",
        "the only two licensed shapes",
    )

    def _row(self, item_id):
        return {r["id"]: r for r in _load_runtime_rows()}[item_id]

    def _remediation_index_text(self):
        with open(os.path.join(_REPO, "curriculum", "drills", "dogfood-error-remediation-index.md"),
                  encoding="utf-8") as fh:
            return fh.read()

    def _kc_geminate_remediation_row_line(self):
        for line in self._remediation_index_text().splitlines():
            if line.startswith("| `kc-geminate-verb-merger-licensing`"):
                return line
        self.fail("kc-geminate-verb-merger-licensing row missing from the Train C remediation index")
        return ""

    def _all_scanned_blobs(self, row12):
        remediation_line = self._kc_geminate_remediation_row_line()
        return [
            ("WRV-12 concept", row12["concept"]),
            ("WRV-12 explanation", row12["explanation"]),
            ("WRV-12 expected_answer", row12["expected_answer"]),
            ("WRV-12 accepted_variants", " ".join(row12["accepted_variants"])),
            ("Train C kc-geminate-verb-merger-licensing remediation-index row", remediation_line),
        ]

    def test_remediation_index_row_does_not_deliver_the_disputed_adjudication_as_settled(self):
        line = self._kc_geminate_remediation_row_line()
        low = line.lower()
        for phrase in self._HARD_SETTLE_PHRASES:
            self.assertNotIn(phrase, low,
                             "Train C kc-geminate-verb-merger-licensing row must not hard-settle the disputed "
                             "kasra/damma-merged jussive question as learner-facing remediation text (%r)"
                             % phrase)

    def test_remediation_index_row_routes_the_wider_inventory_to_scholar_review(self):
        line = self._kc_geminate_remediation_row_line()
        low = line.lower()
        self.assertTrue(
            ("scholar review" in low or "scholar-review" in low) and
            ("unresolved" in low or "disputed" in low or "open question" in low),
            "Train C kc-geminate-verb-merger-licensing row must explicitly route the wider merged-vowel "
            "inventory question to unresolved scholar review: %r" % line)

    def test_remediation_index_row_still_teaches_the_secure_merger_separation_distinction(self):
        line = self._kc_geminate_remediation_row_line()
        low = line.lower()
        self.assertIn("merger", low)
        self.assertIn("separat", low)

    def test_wrv12_does_not_assert_the_jussive_cells_licensed_pair_is_exhaustive(self):
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        for label, blob in self._all_scanned_blobs(row12)[:-1]:
            low = blob.lower()
            for phrase in self._EXHAUSTIVE_PHRASES:
                self.assertNotIn(phrase, low, "%s must not assert an exhaustive jussive-shape-count claim "
                                              "(%r)" % (label, phrase))

    def test_wrv12_still_distinguishes_merger_and_separation_with_secure_examples(self):
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        self.assertIn("يَمُدُّونَ", row12["expected_answer"])
        self.assertIn("suffix", (row12["concept"] + row12["explanation"]).lower())

    def test_wrv12_still_preserves_its_own_suffix_triggered_licensing_target(self):
        # the repair must not lose WRV-12's actual point: merger is obligatory once a vowel follows the second
        # radical (the plural-indicative suffix cell), and a separated answer there must still fail.
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        g = RT.grade(row12, {"answer": "يَمْدُدُونَ — the radicals separate here.",
                             "reasoning": list(row12["required_reasoning"])})
        self.assertFalse(g["content_mastered"])

    def test_no_scanned_source_hard_settles_or_exhaustively_claims_the_disputed_question(self):
        """Cross-check across every surviving surface named by the finding: neither WRV-12's own fields nor
        the Train C remediation-index row may recur EITHER defect, matched by meaning-level paraphrase rather
        than the one exact phrase each was originally reported with."""
        row12 = self._row("WRV-12-mudaaf-merger-default-no-trigger")
        for label, blob in self._all_scanned_blobs(row12):
            low = blob.lower()
            for phrase in self._HARD_SETTLE_PHRASES + self._EXHAUSTIVE_PHRASES:
                self.assertNotIn(phrase, low, "%s must not recur %r" % (label, phrase))


# --------------------------------------------------------------------------- 4c. F8: WRV-18 dual hamza spellings
class WRV18DualHamzaCarrierSpellingsAccepted(unittest.TestCase):
    """F8: WRV-18 must accept BOTH licensed hamza-carrier spellings for the plural cell (bare hamza يَقْرَءُونَ
    and wāw-carrier يَقْرَؤُونَ) while still rejecting the copied-singular-alif-carrier misconception."""

    def _row(self):
        return {r["id"]: r for r in _load_runtime_rows()}["WRV-18-mahmuz-carrier-recheck-after-suffix"]

    def test_both_licensed_spellings_clear_content(self):
        row = self._row()
        base = row["expected_answer"]
        # each answer keeps ONLY one of the two licensed spellings (drop the other's parenthetical mention),
        # proving either spelling alone — not just the two stated together — clears content.
        only_bare = base.replace(" or يَقْرَؤُونَ (wāw carrier)", "")
        only_waw = base.replace("يَقْرَءُونَ (bare hamza) or ", "")
        for form, answer in (("يَقْرَءُونَ", only_bare), ("يَقْرَؤُونَ", only_waw)):
            with self.subTest(form=form):
                self.assertIn(form, answer)
                g = RT.grade(row, {"answer": answer, "reasoning": list(row["required_reasoning"])})
                self.assertTrue(g["content_mastered"], "must accept the licensed spelling %r alone" % form)

    def test_copied_singular_alif_carrier_is_still_rejected(self):
        row = self._row()
        g = RT.grade(row, {"answer": "يَقْرَأُونَ — the singular's alif carrier is copied unchanged into the "
                                    "plural cell.",
                          "reasoning": list(row["required_reasoning"])})
        self.assertFalse(g["content_mastered"])


# --------------------------------------------------------------------------- 5. voice/deputy-agent direction guard

class VoiceAndDeputyAgentDirectionGuard(unittest.TestCase):
    """The nine L4.M1.06/07 rows reject the hostile nominative<->accusative / active<->passive swap of their
    own answer while still accepting every authored correct form."""

    def _direction_sensitive_rows(self):
        by_mc = _rows_by_mc_id()
        rows = [by_mc[mc] for lesson in DIRECTION_SENSITIVE_LESSONS for mc in LESSON_MC_IDS[lesson]]
        # dedupe defensively (no lesson here shares mc-0278, but keep the guard honest either way)
        seen, out = set(), []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)
        return out

    def test_nine_direction_sensitive_rows_present_and_carry_ordered_slots(self):
        rows = self._direction_sensitive_rows()
        self.assertEqual(len(rows), 9)
        for row in rows:
            with self.subTest(id=row["id"]):
                self.assertTrue(row.get("ordered_slots"), "%s must carry ordered_slots" % row["id"])

    def test_hostile_voice_case_swap_is_rejected(self):
        for row in self._direction_sensitive_rows():
            with self.subTest(id=row["id"]):
                swapped = _hostile_voice_case_swap(row["expected_answer"])
                self.assertNotEqual(swapped, row["expected_answer"],
                                    "%s: the hostile swap must actually change the answer text" % row["id"])
                payload = {"answer": swapped, "reasoning": list(row["required_reasoning"])}
                r = RT.step(row, None, payload, now_day=0)
                g = r["grade"]
                self.assertFalse(g["content_mastered"],
                                 "%s: the reverse-direction (voice/case-swapped) rewrite must NOT be mastered"
                                 % row["id"])
                self.assertFalse(g["cleared"], row["id"])

    def test_every_authored_correct_form_still_clears(self):
        for row in self._direction_sensitive_rows():
            forms = [row["expected_answer"]] + list(row.get("accepted_variants") or [])
            for form in forms:
                with self.subTest(id=row["id"], form=form[:40]):
                    payload = {"answer": form, "reasoning": list(row["required_reasoning"])}
                    r = RT.step(row, None, payload, now_day=0)
                    self.assertTrue(r["grade"]["content_mastered"],
                                    "%s: authored correct form must still be mastered: %r" % (row["id"], form))


# --------------------------------------------------------------------------- 5b. F2: exact/diacritic contract
class F2ExactDiacriticContractGuard(unittest.TestCase):
    """F2: every row whose authored correct form and an authored forbidden form collide under the lenient
    recall normalizer (differ ONLY by a vowel/shadda diacritic) must opt into `exact_surface_forms`, and the
    exact contract must actually reject that colliding forbidden form while still accepting the gold form."""

    def test_every_diacritic_colliding_row_declares_exact_surface_forms(self):
        missing = [row["id"] for row in _load_runtime_rows()
                  if RT.diacritic_only_collision(row) and not row.get("exact_surface_forms")]
        self.assertEqual(missing, [],
                         "rows whose expected/forbidden collide under the lenient normalizer (differ only by "
                         "diacritics) but do not declare exact_surface_forms: %s" % missing)

    def test_exact_surface_forms_rows_reject_a_token_level_hostile_substitution(self):
        """R7: token-level hostile substitution replaces the vacuous whole-sentence membership check (which
        compared an entire forbidden_answers sentence's normalized text against an entire expected_answer/
        accepted_variant and so never fired, since authored forbidden prose always differs in wording). For
        every row that authored a forbidden_answers TOKEN colliding with one of its own declared
        exact_surface_forms under the lenient normalizer, substitute that REAL authored hostile token into the
        REAL gold answer and assert the real grader rejects it."""
        exercised = 0
        for row in _load_runtime_rows():
            if not row.get("exact_surface_forms"):
                continue
            if row.get("exact_surface_forms_mode", "all") != "all":
                # mode 'any': corrupting ONE declared alternative while a SIBLING alternative stays present in
                # the same expected_answer text correctly still passes (any() semantics) -- that is exactly
                # WRV-13/WRV-18's own point, tested separately by test_alternative_multiform_rows_accept_...;
                # a single-token substitution here is not a real hostile case for those rows.
                continue
            for gold, hostile in RT.exact_surface_hostile_pairs(row):
                exercised += 1
                hostile_answer = row["expected_answer"].replace(gold, hostile)
                with self.subTest(id=row["id"], gold=gold, hostile=hostile):
                    self.assertNotEqual(hostile_answer, row["expected_answer"],
                                        "%s: the substitution must actually change the answer text" % row["id"])
                    g = RT.grade(row, {"answer": hostile_answer, "reasoning": list(row["required_reasoning"])})
                    self.assertFalse(g["passed"],
                                    "%s: exact_surface_forms must reject the token-level hostile substitution "
                                    "%r -> %r" % (row["id"], gold, hostile))
        self.assertGreater(exercised, 0, "no row exercised a real token-level hostile pair -- the guard is vacuous")

    def test_exact_surface_forms_rows_still_accept_their_own_gold_form(self):
        for row in _load_runtime_rows():
            if not row.get("exact_surface_forms"):
                continue
            with self.subTest(id=row["id"]):
                g = RT.grade(row, {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])})
                self.assertTrue(g["passed"], "%s: exact_surface_forms must still accept the gold answer" % row["id"])

    def test_conjunctive_multiform_rows_require_every_declared_surface(self):
        """R1: a row with >=2 exact_surface_forms and mode 'all' (the default) must reject an answer that drops
        one of the declared surfaces -- even though the ordinary lenient content-coverage match alone would
        still accept it. This is the exact defect the geminate/hamzated/defective contrastive rows exist to
        test: a learner who supplies only ONE half of a two-cell contrast has not demonstrated the row's fact."""
        exercised = 0
        for row in _load_runtime_rows():
            forms = row.get("exact_surface_forms") or []
            if len(forms) < 2 or row.get("exact_surface_forms_mode", "all") != "all":
                continue
            exercised += 1
            partial = row["expected_answer"]
            for missing in forms[1:]:
                partial = partial.replace(missing, "")
            with self.subTest(id=row["id"]):
                self.assertNotEqual(partial, row["expected_answer"],
                                    "%s: the drop must actually change the answer text" % row["id"])
                g = RT.grade(row, {"answer": partial, "reasoning": list(row["required_reasoning"])})
                self.assertFalse(g["passed"], "%s: dropping a required conjunctive surface must fail "
                                              "exact_surface_forms" % row["id"])
                full = RT.grade(row, {"answer": row["expected_answer"],
                                      "reasoning": list(row["required_reasoning"])})
                self.assertTrue(full["passed"], "%s: the full gold answer must still pass" % row["id"])
        self.assertGreaterEqual(exercised, 4,
                                "expected at least the 4 conjunctive contrastive rows (WRV-05/09/14/19)")

    def test_alternative_multiform_rows_accept_either_licensed_surface(self):
        """R1: a row with mode 'any' must accept an answer supplying just ONE of its declared alternatives
        (WRV-13's two licensed jussive shapes; WRV-18's two licensed plural hamza-carrier spellings)."""
        exercised = 0
        for row in _load_runtime_rows():
            forms = row.get("exact_surface_forms") or []
            if row.get("exact_surface_forms_mode") != "any" or len(forms) < 2:
                continue
            exercised += 1
            partial = row["expected_answer"]
            for missing in forms[1:]:
                partial = partial.replace(missing, "")
            with self.subTest(id=row["id"]):
                self.assertNotEqual(partial, row["expected_answer"],
                                    "%s: the drop must actually change the answer text" % row["id"])
                g = RT.grade(row, {"answer": partial, "reasoning": list(row["required_reasoning"])})
                self.assertTrue(g["passed"], "%s: mode 'any' must accept an answer with just one licensed "
                                             "surface" % row["id"])
        self.assertGreaterEqual(exercised, 2, "expected at least WRV-13 and WRV-18")


# --------------------------------------------------------------------------- 6. KC catalog resolution

class KCCatalogResolutionAndRemediation(unittest.TestCase):
    """The seven new precise KCs are integrated append-only, non-auto_safe, and every row resolves through
    the real catalog to this drill's own remediation_route."""

    def test_seven_new_kcs_present_exactly_as_specified(self):
        current = {kc["kc_id"]: kc for kc in _load_kc_catalog()}
        expected = {kc["kc_id"]: kc for kc in _expected_new_kc_entries()}
        self.assertEqual(set(expected), set(NEW_KC_IDS))
        self.assertEqual({kc_id: current.get(kc_id) for kc_id in NEW_KC_IDS}, expected)

    def test_every_new_kc_has_a_non_auto_safe_gate_and_owns_this_drill(self):
        current = {kc["kc_id"]: kc for kc in _load_kc_catalog()}
        for kc_id in NEW_KC_IDS:
            with self.subTest(kc_id=kc_id):
                kc = current[kc_id]
                self.assertNotEqual(kc["default_gate"], "auto_safe",
                                   "%s must not be auto_safe: every row here asserts a weak-rule/voice/"
                                   "governor/deputy-agent fact" % kc_id)
                self.assertEqual(kc["drill_route"], _DRILL_ROUTE)

    def test_kc_catalog_is_append_only_original_prefix_unchanged_plus_exactly_seven(self):
        original = json.loads(_git_show("curriculum/kc-catalog.json"))
        current = _load_kc_catalog()
        self.assertEqual(current[:len(original)], original)
        self.assertEqual(current[len(original):], _expected_new_kc_entries())

    def test_every_row_kc_id_resolves_and_locality_matches_this_key_file(self):
        errs = VDK.validate(_KEYS_PATH)
        self.assertEqual(errs, [])
        current = {kc["kc_id"]: kc for kc in _load_kc_catalog()}
        for row in _load_runtime_rows():
            with self.subTest(id=row["id"]):
                kc = current.get(row["kc_id"])
                self.assertIsNotNone(kc, "%s: kc_id %r does not resolve" % (row["id"], row["kc_id"]))
                self.assertEqual(kc["drill_route"], _DRILL_ROUTE)


# --------------------------------------------------------------------------- 7. assessment + FUSHA-BENCH quarantine

class AssessmentAndBenchmarkQuarantine(unittest.TestCase):
    """No row enters curriculum/assessment/*.jsonl; no row's answer text overlaps a FUSHA-BENCH quarantined
    placement probe (exercised via the REAL tools.fusha_bench functions, not a mock)."""

    def test_assessment_banks_carry_no_candidate_provenance(self):
        errs = VDK.assessment_quarantine_violations()
        self.assertEqual(errs, [])

    def test_no_runtime_row_id_appears_in_any_assessment_bank(self):
        import glob
        ids = {r["id"] for r in _load_runtime_rows()}
        for path in glob.glob(os.path.join(_REPO, "curriculum", "assessment", "*.jsonl")):
            for row in _load_jsonl_file(path):
                self.assertNotIn(row.get("id"), ids, "%s: batch row id reused in assessment bank" % path)

    def test_no_answer_text_overlap_with_the_real_quarantined_placement_probes(self):
        with open(os.path.join(_REPO, "eval", "fusha-bench-v1", "tutor-quarantine.json"), encoding="utf-8") as fh:
            quarantine = json.load(fh)
        probe_path = os.path.join(_REPO, "curriculum", "assessment", "placement-test.sample.jsonl")
        probe_rows = FB.read_jsonl(probe_path)
        probe_ids = set(quarantine["probe_ids"])
        self.assertEqual({r["id"] for r in probe_rows}, probe_ids)
        rows = _load_runtime_rows()
        row_ids = {r["id"] for r in rows}
        FB.ensure_no_quarantine_overlap(probe_ids, {"weak-root-voice-runtime": row_ids})
        exposures = FB.answer_exposures(probe_rows, {"weak-root-voice-runtime": rows})
        self.assertEqual(exposures, [], "quarantined placement-probe answer text reused in this batch")


# --------------------------------------------------------------------------- 8. provenance / public-projection / CLI

class ProvenanceAndPublicProjectionBoundary(unittest.TestCase):
    """No candidate/certified/public-projection promotion marker anywhere; dry run writes nothing; the REAL
    CLI/selector round-trips over the real bank file."""

    def test_no_promotion_marker_on_any_kc_or_row(self):
        for kc in _expected_new_kc_entries():
            hit = FORBIDDEN_ROW_KEYS & set(kc)
            self.assertFalse(hit, "%s: forbidden key(s) present: %s" % (kc["kc_id"], sorted(hit)))
        for row in _load_runtime_rows():
            hit = FORBIDDEN_ROW_KEYS & set(row)
            self.assertFalse(hit, "%s: forbidden key(s) present: %s" % (row["id"], sorted(hit)))

    def test_dry_run_writes_nothing_against_the_real_bank(self):
        rows = _load_runtime_rows()
        row0 = rows[0]
        with tempfile.TemporaryDirectory() as td:
            ans_path = os.path.join(td, "answer.json")
            with open(ans_path, "w", encoding="utf-8") as fh:
                json.dump({"answer": row0["expected_answer"], "reasoning": list(row0["required_reasoning"])}, fh)
            prog_path = os.path.join(td, "progress.json")
            log_path = os.path.join(td, "events.jsonl")
            argv = ["--bank", _KEYS_PATH, "--item", row0["id"], "--answer", ans_path,
                    "--progress", prog_path, "--event-log", log_path, "--now", "0"]
            RT._run_main(argv)  # NO --write
            self.assertFalse(os.path.exists(prog_path))
            self.assertFalse(os.path.exists(log_path))
            RT._run_main(argv + ["--write"])
            self.assertTrue(os.path.exists(prog_path) and os.path.exists(log_path))

    def test_real_selector_picks_the_first_new_item_on_an_empty_progress(self):
        bank = RT.load_bank(_KEYS_PATH)
        item_id, reason = RT.select_next(bank, RT.new_progress(), 0)
        self.assertEqual(reason, "new_item")
        self.assertEqual(item_id, bank[0]["id"])

    def test_real_cli_select_over_the_real_bank_does_not_raise(self):
        rc = RT._run_main(["--bank", _KEYS_PATH, "--select"])
        self.assertEqual(rc, 0)


# --------------------------------------------------------------------------- 9. existing artifacts unchanged

class ExistingArtifactsUnchanged(unittest.TestCase):
    """The eleven pre-existing keyed drill files and the pre-existing kc-catalog prefix remain byte-identical;
    nothing outside the six exclusive-writable paths changes."""

    def test_pre_existing_keyed_drill_files_are_byte_identical_to_start_sha(self):
        for name in _PRE_EXISTING_KEYED_DRILLS:
            rel = "curriculum/drills/keys/%s.keys.jsonl" % name
            original = _git_show(rel)
            with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
                current = fh.read()
            self.assertEqual(original, current, "%s must be byte-identical to the start SHA" % rel)

    def test_no_other_working_tree_changes_outside_the_writable_set(self):
        out = subprocess.run(["git", "status", "--porcelain"], cwd=_REPO, capture_output=True, check=True)
        for line in out.stdout.decode("utf-8").splitlines():
            path = line[3:].strip().replace("\\", "/")
            if not path:
                continue
            self.assertIn(path, _WRITABLE_SET, "unexpected working-tree change outside the writable set: %s" % path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
