#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic discriminators for the INCREMENT-21 skill fixtures (candidate sarf@2.1 / nahw@2.1).

Consolidation layer of the 2026-07-12 calibration cycle (C2, C4, C5, W13-round2, DR-1/2/6,
MEASURED-EFFECT). Companion to skill_rules.py + skill_rules_richseg.py, kept SEPARATE so it does not
collide with the released @2 fixtures; merges alongside them at the @2.1 release.

Each candidate @2.1 rule is encoded as a PAIR:
  - a CORRECTED rule (the candidate sarf@2.1 / nahw@2.1 behaviour), and
  - the SUPERSEDED rule it replaces (the exact pre-fix behaviour that produced the calibration defect).

RED-FIRST contract (asserted by test_skill_fixtures_increment21.py):
  GREEN     : corrected_rule(case) == correct_label
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label

NON-CONSTANT-DISCRIMINATOR contract (the SEND-BACK guard): every CORRECTED discriminator must
branch on its input — across a rule's fixtures it MUST return >=2 distinct labels (a positive case
maps to correct_label, a boundary/control case maps to something else). A corrected rule that
returns a constant is rejected by the harness even if the constant happens to match.

These are OBSERVED morphosyntactic rules with source-addressed Qurʾānic evidence; not theological
claims. Stdlib only, no network, no MCP, no live services. Deterministic.
"""

# --- shared vocabularies ------------------------------------------------------------------------
_MUDARI_PREFIXES = {"ي", "ت", "ن", "أ", "ا"}
# overt clitic morphemes that legitimately own their own segment
_OVERT_CLITICS = {"ـتُ", "ـتَ", "ـتِ", "ـتم", "ـتن", "نا", "وا", "ألف الاثنين", "نون النسوة", "ي", "ك", "ه", "ها", "هم", "هن", "هما", "كم"}
_FORM_V_VI_PATTERNS = {"تفعّل", "تفعل", "تفاعل", "تَفَعَّل", "تَفَاعَل"}
# fused preposition+pronoun closed-class surfaces (W13-2)
_FUSED_PREP_PRONOUN = {"فيها", "فيه", "فيهم", "عليكم", "عليك", "عليه", "عليها", "منه", "منها", "منهم", "لهم", "له", "لها", "بها", "بهم"}
_VALID_PRONOUN_IRAB = {"fail", "naib_fail", "maful_bihi", "mudaf_ilayh"}


# ================================================================================================
# SARF @2.1
# ================================================================================================

# --- S1. surface pattern (wazn) NEVER certifies a root (C2 / DR-2 two-tier) ----------------------
def _pattern_cert_corrected(case):
    """است/مست/ت-initial surface shapes may be Form VIII of a weak/hamza root (استوى→سوي,
    مستمعون→سمع, تتخذوا→أخذ ibdāl). Root is CERTIFIED only from an explicit مادة in a certified
    source; pattern inference alone yields a candidate_root, never a certification."""
    if case.get("certified_madda"):
        return "root_certified"
    if case.get("root_from") == "surface_pattern":
        return "candidate_root_uncertified"
    return "candidate_root_uncertified"


def _pattern_cert_superseded(case):
    """Pre-fix: the surface wazn was read as certifying a root (است→Form X root by stripping است)."""
    return "root_certified"


# --- S2. weak lafīf/nāqiṣ/ajwaf whole-token verb whose radicals are absent from the surface (C2/DR-2)
def _weak_whole_token_corrected(case):
    """A whole-token verb whose CERTIFIED root is weak (lafīf/nāqiṣ/ajwaf) and whose weak radicals
    are absent from the contiguous surface (يتوفى → و ف ي) must be FLAGGED as an incompleteness
    defect; the ت-prefix nominal allow-lists miss it."""
    if case.get("is_whole_token_verb") and case.get("root_is_weak") and not case.get("weak_radicals_visible"):
        return "flag_weak_whole_token"
    return "no_flag"


def _weak_whole_token_superseded(case):
    """Pre-fix: whole-token weak verbs outside the ت-prefix nominal templates silently passed."""
    return "no_flag"


# --- S3. cross-source root conflict is never majority-voted (C2) ---------------------------------
# Arabic root radical -> canonical single-char latin, so MCP Arabic (وفي) and QAC romanization
# (w f y) normalize to the SAME key (wfy) and w/y orthography never false-alarms a conflict.
_ROOT_TRANSLIT = {
    "ء": "'", "أ": "'", "إ": "'", "آ": "'", "ا": "'", "ى": "'",
    "ب": "b", "ت": "t", "ث": "c", "ج": "j", "ح": "H", "خ": "x", "د": "d", "ذ": "C",
    "ر": "r", "ز": "z", "س": "s", "ش": "$", "ص": "S", "ض": "D", "ط": "T", "ظ": "Z",
    "ع": "E", "غ": "g", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "ة": "p",
}


def _norm_root(r):
    """Normalize a root to a canonical latin key so MCP Arabic and QAC w/y romanization compare
    equal (وفي == 'w f y' == wfy) and orthography never false-alarms a cross-source conflict."""
    if not r:
        return r
    return "".join(_ROOT_TRANSLIT.get(ch, ch) for ch in r if not ch.isspace())


def _root_conflict_corrected(case):
    """When two certified sources give roots that DIFFER after orthography normalization
    (MCP ألك vs QAC ملك for ملائكة), neither certifies alone: record both, route 2-vote, never
    majority-vote. When they AGREE post-normalization (MCP وفي vs QAC w f y) → certify."""
    a = _norm_root(case.get("root_source_a"))
    b = _norm_root(case.get("root_source_b"))
    if a and b:
        return "certify_agreed_root" if a == b else "conflict_two_vote_no_majority"
    return "single_source_candidate"


def _root_conflict_superseded(case):
    """Pre-fix: the two source roots were reconciled by majority/first-source, certifying one."""
    return "certify_agreed_root"


# --- S4. jāmid vs mushtaqq routing (C2 subclassing) ---------------------------------------------
def _jamid_routing_corrected(case):
    """C2a مشتق (root certified, derived) → wave-eligible after review. C2b جامد / etymology-contested
    (ملكوت فَعَلُوت, مثاني, مسكين-debate) → auto-route 2-vote and the gloss may ship root-silent; the
    detector must NOT assert 'derived' for a jāmid token."""
    if case.get("is_jamid"):
        return "route_two_vote_root_silent"
    if case.get("is_derived") and case.get("root_certified"):
        return "wave_eligible_after_review"
    return "route_two_vote_root_silent"


def _jamid_routing_superseded(case):
    """Pre-fix: every C2 token was messaged as 'derived whole-token' and treated as wave-eligible."""
    return "wave_eligible_after_review"


# --- S5. loc↔surface address cross-check, fail-closed (C2 + C5 + MEASURED-EFFECT) ----------------
def _loc_integrity_corrected(case):
    """Before emitting/deploying a row, resolve canonical_location→surface against the corpus/wbw
    tokenization. An IMPOSSIBLE address (word index > the āyah's word count, e.g. 4:91:103 in a
    32-word āyah) fails closed as impossible; a MISMATCH (25:33:2→8, 61:4:3→11, 17:92:2→9, 2:91:3→w23)
    fails closed and reroutes to the addressing lane."""
    ayah_len = case.get("ayah_word_count")
    stated = case.get("stated_word_index")
    resolved = case.get("resolved_word_index")
    if ayah_len is not None and stated is not None and stated > ayah_len:
        return "fail_closed_impossible_address"
    if stated != resolved:
        return "fail_closed_reroute_addressing"
    return "loc_ok_emit"


def _loc_integrity_superseded(case):
    """Pre-fix: the row was emitted at its stated loc without a surface cross-check."""
    return "loc_ok_emit"


# --- S6. hamza-initial verb disambiguation; the lazy '1s or Form IV' disjunction is BANNED (C4) --
def _hamza_initial_corrected(case):
    """أ-initial verb tokens must be resolved among {1s imperfect, Form IV perfect, Form IV
    imperative, interrogative particle + verb} BEFORE any person/aspect tag. The disjunction
    '1st person singular or Form IV' is a BLOCKED output — commit (diacritics/MCP) or abstain."""
    if case.get("emits_1s_or_formIV_disjunction"):
        return "blocked_disjunction"
    r = case.get("resolved_reading")
    if r in {"1s_imperfect", "formIV_perfect", "formIV_imperative", "interrogative_particle_plus_verb"}:
        return "committed:" + r
    return "abstain_hamza_unresolved"


def _hamza_initial_superseded(case):
    """Pre-fix: hamza-initial tokens emitted the lazy '1st person singular or Form IV' disjunction."""
    return "emit_1s_or_formIV_disjunction"


# --- S7. imperative ⇒ 2nd person (HARD invariant, validator-grade) (C4) --------------------------
def _imperative_person_corrected(case):
    """HARD invariant: if aspect == imperative the subject person is 2nd (2ms/2fs/2mp/2fp) and a
    'they'/3rd-person SUBJ gloss is forbidden. A genuine 3rd-person form is NOT imperative."""
    if case.get("aspect") == "imperative":
        p = case.get("person", "")
        return "ok_second_person" if p.startswith("2") else "violation_imperative_non_second"
    return "not_imperative_na"


def _imperative_person_superseded(case):
    """Pre-fix: no imperative-person invariant ran; a 3rd-person tag on an imperative passed silently."""
    return "accepted_no_violation"


# --- S8. passive vocalism ⇒ commit voice (C4) ----------------------------------------------------
def _passive_vocalism_corrected(case):
    """ُ-ِ perfect / ُ-َ imperfect vocalism ⇒ commit voice=passive. 'active/passive as context
    requires' is legal ONLY for an undiacritized or qirāʾāt-split address."""
    if case.get("vocalism") in {"u_i_perfect", "u_a_imperfect"}:
        return "commit_passive"
    if case.get("vocalism") in {"a_a_perfect", "a_u_imperfect"}:
        return "commit_active"
    if case.get("qiraat_split") or case.get("undiacritized"):
        return "abstain_named_ambiguity"
    return "commit_active"


def _passive_vocalism_superseded(case):
    """Pre-fix: voice was hedged 'active/passive as context requires' even on vocalized surfaces."""
    return "hedge_active_or_passive"


# --- S9. completeness-claim template ban (C4) ----------------------------------------------------
def _completeness_claim_corrected(case):
    """The learner_explanation 'exposes … the person/number/mood facts' may render ONLY when the
    morphline actually asserts person AND mood; otherwise emit the honest-generic variant."""
    if case.get("morphline_asserts_person") and case.get("morphline_asserts_mood"):
        return "render_completeness_claim"
    return "render_honest_generic"


def _completeness_claim_superseded(case):
    """Pre-fix: the completeness claim rendered unconditionally (523/523 C4 rows carried it)."""
    return "render_completeness_claim"


# --- S10. segment↔morphline↔learner person consistency (C4) --------------------------------------
def _person_consistency_corrected(case):
    """PFX-segment person == morphline person == SUBJ-segment person == learner-text person. Any
    disagreement (17:12:16 PFX says 2nd, SUBJ says 3mp) is a hard violation."""
    persons = [p for p in (case.get("pfx_person"), case.get("morphline_person"),
                           case.get("subj_person"), case.get("learner_person")) if p]
    return "consistent" if len(set(persons)) <= 1 else "violation_person_mismatch"


def _person_consistency_superseded(case):
    """Pre-fix: no cross-field person consistency check ran; a self-contradicting row passed."""
    return "no_check_passed_consistent"


# --- S11. Form V/VI ت is a wazn augment, not a proclitic (DR-1) ----------------------------------
def _form_v_vi_ta_corrected(case):
    """The ت of Form V (تفعّل) / Form VI (تفاعل) is a زائد wazn augment (Shadhā al-ʿArf) — it is
    stem-internal and is NEVER peeled as a proclitic."""
    if case.get("wazn") in _FORM_V_VI_PATTERNS and case.get("leading_ta"):
        return "ta_is_wazn_keep_in_stem"
    if case.get("leading_ta") and case.get("prefix_is_inflectional"):
        return "ta_is_inflectional_prefix_segment"
    return "na"


def _form_v_vi_ta_superseded(case):
    """Pre-fix: any leading ت was peeled as a proclitic/inflectional prefix, splitting the wazn."""
    return "peel_ta_as_proclitic"


# --- S12. a root-radical that is suffix-shaped is never a clitic (C5) ----------------------------
def _root_radical_corrected(case):
    """A suffix-shaped surface letter (ك/ي/ه/ا/و) that is a ROOT RADICAL — final (تملك ك of ملك,
    تهدي ي of هدي, تأتي ي of أتي) or initial (وعد و of وعد, not a conjunction) — is NEVER a clitic."""
    if case.get("candidate_clitic_letter") and case.get("candidate_clitic_letter") in (case.get("root_radicals") or []):
        return "radical_not_clitic"
    if case.get("candidate_clitic_letter"):
        return "genuine_clitic"
    return "na"


def _root_radical_superseded(case):
    """Pre-fix: any suffix-shaped final/initial letter was peeled as a clitic."""
    return "peel_as_clitic"


# --- S13. zero-marker / mustatir agreement carries no visible suffix segment (C5) ----------------
def _zero_agreement_corrected(case):
    """A mustatir / zero-marker subject (3ms perfect, 2ms imperative) requires NO suffix segment;
    only an OVERT clitic does. Do not demand a segment the morphology does not realize."""
    if case.get("subject_realization") == "mustatir":
        return "no_segment_expected"
    if case.get("overt_clitic"):
        return "segment_required"
    return "no_segment_expected"


def _zero_agreement_superseded(case):
    """Pre-fix: the detector demanded a subject segment for every agreement mention."""
    return "segment_required"


# --- S14. morphline keyword match must not fire on a negated mention (C5) ------------------------
def _negated_mention_corrected(case):
    """Keyword matching (e.g. 'pronoun/ضمير') must parse the negation window: a NEGATED mention
    ('not an attached pronoun', الكبرى) must NOT trip the detector."""
    if case.get("keyword_present") and case.get("keyword_negated"):
        return "suppress_negated_mention"
    if case.get("keyword_present"):
        return "fire_detector"
    return "na"


def _negated_mention_superseded(case):
    """Pre-fix: the detector fired on any keyword occurrence, including its own disclaimer."""
    return "fire_detector"


# --- S15. epenthetic ishbāʿ waw is not a segment (C5) --------------------------------------------
def _ishbaa_waw_corrected(case):
    """In ـتُمُو + pronoun (آتيتموهن, أورثتموها) the و is حرف إشباع (epenthetic): it stays with the
    تم subject segment and is never its own segment nor a root radical."""
    if case.get("context") == "tumu_plus_pronoun" and case.get("letter") == "و":
        return "ishbaa_stays_with_tum"
    if case.get("context") == "waw_al_jamaa" and case.get("letter") == "و":
        return "waw_jamaa_own_segment"
    return "na"


def _ishbaa_waw_superseded(case):
    """Pre-fix: the ishbāʿ waw was split off as its own segment / mistaken for a radical."""
    return "split_ishbaa_as_segment"


# --- S16. jamʿ/dual-marked pronoun is ONE segment carrying its jamʿ letters (C5) -----------------
def _jam_marker_corrected(case):
    """The canonical split is ONE pronoun segment carrying its jamʿ/ʿimād/dual letters
    (هُمْ، هُنَّ، هُمَا، كُمُ) with a sarf note decomposing them; never a bare هـ segment that orphans
    the mīm/nūn."""
    if case.get("pronoun_cluster") and case.get("keeps_jam_letters"):
        return "one_pronoun_segment_with_jam"
    if case.get("pronoun_cluster"):
        return "orphaned_jam_letter"
    return "na"


def _jam_marker_superseded(case):
    """Pre-fix: a bare هـ segment was emitted, orphaning the جمع mīm/nūn."""
    return "orphaned_jam_letter"


# --- S17. within-root HALT: a POS reading that only one candidate root supports is an ownership arm (W13)
def _pos_arm_corrected(case):
    """When a surface resolves to TWO candidate roots (قُل → ق ل ل / ق و ل), a POS reading that only
    ONE candidate root supports is a valid ownership arm: the imperative 'say' exists only for قول,
    so قُل rebinds to ق و ل. Absent such an arm, HALT."""
    supporting = case.get("roots_supporting_pos") or []
    if case.get("candidate_roots") and len(supporting) == 1:
        return "rebind_pos_arm:" + supporting[0]
    if case.get("candidate_roots"):
        return "halt_no_deciding_arm"
    return "na"


def _pos_arm_superseded(case):
    """Pre-fix: the within-root HALT certified a root with no POS/surface arm (or halted with one)."""
    return "halt_no_deciding_arm"


# --- S18. content token with root named but no forms arm → HOLD, never a fabricated rebind (W13) -
def _content_hold_corrected(case):
    """A content token whose root morphology NAMES (ربك → ر ب ب, الشياطين → ش ط ن) but whose surface
    is documented by NO entry's usage[].forms → HOLD (review_required). Absence of an ownership arm
    is INVENTORY, not proof; never fabricate a rebind edge."""
    if case.get("root_named") and not case.get("forms_arm_present"):
        return "hold_review_required"
    if case.get("root_named") and case.get("forms_arm_present"):
        return "rebind_supported"
    return "na"


def _content_hold_superseded(case):
    """Pre-fix: a content token was rebinded on morphology alone (round-1 rebinded rabb-type)."""
    return "rebind_on_morphology_alone"


# --- S19. coarse-tier verb+subject is ONE valid unit; the object pronoun always splits (C1) ------
def _coarse_tier_verb_corrected(case):
    """C1 refuted: MCP treats a finite verb + its subject/agreement morphology as ONE sarf unit
    ({يُنْفِقُونَ}) — matching the live coarse tier. A committed whole-token verb with root+form+person
    is VALID, not a stem_swallow. The OBJECT pronoun is always its own segment; a rootless whole-token
    is still a defect."""
    if not case.get("root_committed"):
        return "rootless_defect"
    if case.get("object_pronoun_fused"):
        return "object_must_split"
    return "valid_coarse_verb_subject_unit"


def _coarse_tier_verb_superseded(case):
    """Pre-fix C1 theory: any agreement prefix inside the verb segment was flagged as a swallow."""
    return "flag_prefix_swallow"


# ================================================================================================
# NAHW @2.1
# ================================================================================================

# --- N1. mood from a visible governor, not 'not separately asserted' (C4) ------------------------
def _mood_governor_corrected(case):
    """Mood is decidable from a visible governor (لِ/أَنْ/لَمْ/لَا الناهية/شرط) + the final vowel:
    commit the mood or state an explicit named ambiguity — never 'mood context not separately
    asserted' when a governor is visible."""
    g = case.get("governor")
    mood = {"an": "subjunctive", "lam_taleel": "subjunctive", "lam": "jussive",
            "la_nahiya": "jussive", "shart": "jussive"}.get(g)
    if mood:
        return "commit:" + mood
    if case.get("indicative_default"):
        return "commit:indicative"
    return "named_ambiguity"


def _mood_governor_superseded(case):
    """Pre-fix: mood was hedged 'not separately asserted' even with a visible governor."""
    return "mood_not_separately_asserted"


# --- N2. lām-prefix typology: each lām type is its own segment with its own consequence (DR-1/DR-6)
def _lam_typology_corrected(case):
    """The lām prefix has distinct types, each its OWN segment: لام الأمر (jussive governor),
    لام التعليل/كي (subjunctive via أن مضمرة), لام الجر (jarr), لام الابتداء/التوكيد (emphasis, no
    mood effect). Type must be resolved before glossing."""
    return {"lam_al_amr": "governor_jussive",
            "lam_taleel": "governor_subjunctive_an_mudmara",
            "lam_jarr": "jarr_particle",
            "lam_ibtida": "emphasis_no_mood"}.get(case.get("lam_type"), "na")


def _lam_typology_superseded(case):
    """Pre-fix: any prefixed lām was folded into the verb/handled as a single undifferentiated lām."""
    return "lam_undifferentiated_folded"


# --- N3. jazm applies only to the muḍāriʿ (HARD invariant) (DR-6) --------------------------------
def _jazm_only_mudari_corrected(case):
    """Mood (and jazm/naṣb specifically) is a category of the muḍāriʿ ONLY. A perfect (mabnī) or an
    imperative is never 'majzūm/manṣūb' — asserting a mood on a non-imperfect is a hard violation."""
    if case.get("aspect") == "imperfect":
        return "mood_applicable"
    if case.get("asserted_mood"):
        return "violation_mood_on_non_mudari"
    return "mood_na_correct"


def _jazm_only_mudari_superseded(case):
    """Pre-fix: a mood label (jussive/subjunctive) on a perfect/imperative passed unflagged."""
    return "mood_allowed_on_non_mudari"


# --- N4. مَا / مَن function is per-occurrence; never propagated across occurrences (DR-6) ----------
def _ma_man_occurrence_corrected(case):
    """مَا/مَن function (nāfiya/mawṣūla/istifhāmiyya/…) is resolved PER OCCURRENCE. The SAME surface
    can carry DIFFERENT functions in the SAME āyah (5:116 relative مَا @33 AND nāfiya مَا); never
    carry one occurrence's reading to another."""
    if case.get("propagated_from_other_occurrence"):
        return "violation_propagated_reading"
    if case.get("occurrence_function"):
        return "function_per_occurrence:" + case["occurrence_function"]
    return "na"


def _ma_man_occurrence_superseded(case):
    """Pre-fix: the first/lexicon reading of مَا was carried to every occurrence, unflagged."""
    return "propagated_reading_accepted"


# --- N5. لا الناهية is a jussive-forcing governor owning the following verb (DR-6) ----------------
def _la_nahiya_corrected(case):
    """لا الناهية is a jussive-forcing governor that OWNS the following verb (verb → majzūm) — it is
    distinct from لا النافية, and the verb after it is a CONTENT verb keeping its root."""
    if case.get("particle") == "la_nahiya":
        return "governor_forces_jussive_verb_is_content"
    if case.get("particle") == "la_nafiya":
        return "negation_particle_no_jussium"
    return "na"


def _la_nahiya_superseded(case):
    """Pre-fix: لا الناهية was merged with the verb / not treated as a jussive governor."""
    return "la_folded_no_governor"


# --- N6. هاء التنبيه in a vocative compound is not a pronoun (C5) ---------------------------------
def _ha_tanbih_corrected(case):
    """ها in the vocative compounds يا+أيها / أيتها is حرف تنبيه (attention particle) — its own
    vocative element, NEVER an attached pronoun clitic."""
    if case.get("surface_family") == "ya_ayyuha" and case.get("segment") == "ها":
        return "ha_tanbih_particle"
    if case.get("segment") == "ها":
        return "ha_pronoun_clitic"
    return "na"


def _ha_tanbih_superseded(case):
    """Pre-fix: the ها of يأيها was flagged as a swallowed attached pronoun."""
    return "ha_pronoun_clitic"


# --- N7. fused preposition+pronoun surfaces belong to the closed-class function-word floor (W13) --
def _fused_prep_corrected(case):
    """Fused jarr+pronoun surfaces (فِيهَا, عَلَيْكُم, مِنْهُ) are closed-class function words on the
    affirm/function-word floor; the deterministic closed-class set must include the fused-preposition
    inventory so they are affirmed, not parked in review."""
    if case.get("surface") in _FUSED_PREP_PRONOUN:
        return "affirm_function_floor"
    if case.get("is_content_token"):
        return "not_function_floor"
    return "na"


def _fused_prep_superseded(case):
    """Pre-fix: the enclitic peel missed the و-final preposition contraction, parking these in review."""
    return "parked_review"


# --- N8. lām jawāb al-qasam + nūn al-tawkīd: finite energic marfūʿ, never an infinitive gloss (C1)
def _lam_qasam_corrected(case):
    """لام جواب القسم + نون التوكيد welds to a FINITE energic verb that stays مرفوع (فَلَيُبَتِّكُنَّ →
    'they will surely cut off'), never a dictionary infinitive ('to slit'). It is distinguished from
    لام الأمر (which gives majzūm) by mood: marfūʿ+energic vs jussive."""
    if case.get("lam_type") == "lam_qasam":
        return "finite_energic_marfu_no_infinitive"
    if case.get("lam_type") == "lam_al_amr":
        return "jussive_amr"
    return "na"


def _lam_qasam_superseded(case):
    """Pre-fix: the qasam-welded verb leaked a dictionary infinitive and/or was mislabeled لام الأمر."""
    return "infinitive_leak_labeled_amr"


# ------------------------------------------------------------------------------------------------
CORRECTED = {
    "coarse_tier_verb": _coarse_tier_verb_corrected,
    "lam_qasam": _lam_qasam_corrected,
    "pattern_cert": _pattern_cert_corrected,
    "weak_whole_token": _weak_whole_token_corrected,
    "root_conflict": _root_conflict_corrected,
    "jamid_routing": _jamid_routing_corrected,
    "loc_integrity": _loc_integrity_corrected,
    "hamza_initial": _hamza_initial_corrected,
    "imperative_person": _imperative_person_corrected,
    "passive_vocalism": _passive_vocalism_corrected,
    "completeness_claim": _completeness_claim_corrected,
    "person_consistency": _person_consistency_corrected,
    "form_v_vi_ta": _form_v_vi_ta_corrected,
    "root_radical": _root_radical_corrected,
    "zero_agreement": _zero_agreement_corrected,
    "negated_mention": _negated_mention_corrected,
    "ishbaa_waw": _ishbaa_waw_corrected,
    "jam_marker": _jam_marker_corrected,
    "pos_arm": _pos_arm_corrected,
    "content_hold": _content_hold_corrected,
    "mood_governor": _mood_governor_corrected,
    "lam_typology": _lam_typology_corrected,
    "jazm_only_mudari": _jazm_only_mudari_corrected,
    "ma_man_occurrence": _ma_man_occurrence_corrected,
    "la_nahiya": _la_nahiya_corrected,
    "ha_tanbih": _ha_tanbih_corrected,
    "fused_prep": _fused_prep_corrected,
}

SUPERSEDED = {
    "coarse_tier_verb": _coarse_tier_verb_superseded,
    "lam_qasam": _lam_qasam_superseded,
    "pattern_cert": _pattern_cert_superseded,
    "weak_whole_token": _weak_whole_token_superseded,
    "root_conflict": _root_conflict_superseded,
    "jamid_routing": _jamid_routing_superseded,
    "loc_integrity": _loc_integrity_superseded,
    "hamza_initial": _hamza_initial_superseded,
    "imperative_person": _imperative_person_superseded,
    "passive_vocalism": _passive_vocalism_superseded,
    "completeness_claim": _completeness_claim_superseded,
    "person_consistency": _person_consistency_superseded,
    "form_v_vi_ta": _form_v_vi_ta_superseded,
    "root_radical": _root_radical_superseded,
    "zero_agreement": _zero_agreement_superseded,
    "negated_mention": _negated_mention_superseded,
    "ishbaa_waw": _ishbaa_waw_superseded,
    "jam_marker": _jam_marker_superseded,
    "pos_arm": _pos_arm_superseded,
    "content_hold": _content_hold_superseded,
    "mood_governor": _mood_governor_superseded,
    "lam_typology": _lam_typology_superseded,
    "jazm_only_mudari": _jazm_only_mudari_superseded,
    "ma_man_occurrence": _ma_man_occurrence_superseded,
    "la_nahiya": _la_nahiya_superseded,
    "ha_tanbih": _ha_tanbih_superseded,
    "fused_prep": _fused_prep_superseded,
}
