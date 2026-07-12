#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic discriminators for the QAMUS-RICH-SEG-001 skill fixtures (candidate @2).

Companion to skill_rules.py, kept SEPARATE so it does not collide with the in-flight
skill-registry / skill-fixtures integration. Merges alongside skill_rules.py at release.

Each of the 9 confirmed rich-segmentation defect classes (5 ṣarf, 4 naḥw) plus the 2
over-segmentation boundary negatives is encoded here as a PAIR:
  - a CORRECTED rule (the candidate sarf@2 / nahw@2 behaviour), and
  - the SUPERSEDED rule it replaces (the exact pre-fix behaviour that produced the bug).

A fixture is "red-first" when the SUPERSEDED rule reproduces the wrong label AND that wrong
label diverges from the correct one — so a test asserting the correct label FAILS against the
superseded behaviour and PASSES against the corrected behaviour.

These are OBSERVED morphosyntactic rules with source-addressed Qurʾānic evidence; they are not
theological claims. Stdlib only, no network, no MCP, no live services. Deterministic.

Dispatch: CORRECTED[rule](case) and SUPERSEDED[rule](case) both return a short label string.
"""

# Inflectional muḍāriʿ prefixes (ʾanaytu: hamza / nūn / yāʾ / tāʾ), bare seats.
_MUDARI_PREFIXES = {"ي", "ت", "ن", "أ", "ا"}
_VALID_PRONOUN_IRAB = {"fail", "naib_fail", "maful_bihi", "mudaf_ilayh"}


# --- S1. muḍāriʿ inflectional prefix is its own segment (sarf@2) ---------------------------------------------
def _mudari_prefix_corrected(case):
    """The imperfect inflectional prefix (يـ/تـ/نـ/أـ) of a muḍāriʿ verb is its OWN segment,
    never folded into a rootless whole-token stem."""
    if (case.get("aspect") == "imperfect"
            and case.get("prefix_is_inflectional")
            and case.get("prefix") in _MUDARI_PREFIXES):
        return "prefix_is_own_segment"
    return "no_prefix_segment"


def _mudari_prefix_superseded(case):
    """Pre-fix: the inflectional prefix was folded into the stem and emitted as one rootless whole token."""
    return "prefix_folded_into_stem"


# --- S2. derived-form noun/participle/maṣdar exposes its root (sarf@2) ---------------------------------------
def _derived_root_corrected(case):
    """A derived-form nominal (Form II maṣdar تفعيل, Form X استفعال, ism makān/zamān مَفْعِل,
    broken plural) EXPOSES its triliteral root; it is never a rootless whole-token."""
    if case.get("is_derived_nominal"):
        return "root_exposed" if case.get("root") else "missing_root"
    return "na"


def _derived_root_superseded(case):
    """Pre-fix: a derived nominal was stored/emitted as a rootless whole-token surface."""
    return "rootless_whole_token"


# --- S3. attached pronoun / subject marker / dual-plural ending is its own segment (sarf@2) ------------------
def _attached_unit_corrected(case):
    """Attached pronouns (ـه/ـها/ـهم/ـك/ـكم), subject markers (ـتُ/ـتم/ـوا/ـنَ), and dual/plural
    endings are EACH their own segment, never fused into the stem."""
    units = case.get("attached_units") or []
    if units:
        return "each_unit_own_segment" if case.get("all_units_isolated") else "affix_fused_into_stem"
    return "no_affix"


def _attached_unit_superseded(case):
    """Pre-fix: subject markers + attached pronouns were absorbed into a single stem token."""
    return "affix_fused_into_stem"


# --- S4. per-occurrence voice/mood/aspect/Form is committed, never hedged (sarf@2) --------------------------
def _occurrence_form_corrected(case):
    """An exact Qurʾānic occurrence's voice/mood/aspect/Form is KNOWABLE and must be committed
    per occurrence — never hedged as 'as context requires / not separately asserted'."""
    if case.get("hedged"):
        return "hedged_uncommitted"
    fields = case.get("committed") or {}
    if all(fields.get(k) for k in ("voice", "mood", "aspect", "form")):
        return "fully_committed"
    return "partial"


def _occurrence_form_superseded(case):
    """Pre-fix: the occurrence's inflection was hedged ('as context requires / not separately asserted')."""
    return "hedged_uncommitted"


# --- S5 (boundary A). derivational mīm of a clitic-free participle is NOT a separable affix (sarf@2) ---------
def _oversegment_mim_corrected(case):
    """BOUNDARY: a Form IV / participle with zero clitics (e.g. مُّبِينًا) is a SINGLE token — the
    derivational mīm is part of the wazn, not a separable affix. Do not over-segment."""
    if case.get("clitic_count", 0) == 0 and case.get("leading_mim_is_derivational"):
        return "single_token_do_not_split"
    return "segment"


def _oversegment_mim_superseded(case):
    """Pre-fix over-segmentation: any leading mīm was stripped off as though it were an affix."""
    return "split_mim_as_affix"


# --- S5 (boundary B). a designed learner-coarse STEM+SUBJ split is complete, not a defect (sarf@2) -----------
def _coarse_split_corrected(case):
    """BOUNDARY: a deliberately learner-coarse STEM+SUBJ split (e.g. تَعْلَمُونَ → stem + ونَ) is a
    COMPLETE analysis for its tier, not a segmentation defect to be re-flagged."""
    if (case.get("designed_learner_coarse")
            and case.get("stem_present")
            and case.get("subject_marker_present")):
        return "complete_coarse_not_a_defect"
    return "incomplete"


def _coarse_split_superseded(case):
    """Pre-fix: any non-maximal (coarse) split was flagged as a segmentation defect."""
    return "flagged_as_segmentation_defect"


# --- N1. imperative lām is a jussive-forcing governor segment (nahw@2) --------------------------------------
def _imperative_lam_corrected(case):
    """The imperative lām (لام الأمر) is a governor forcing the following muḍāriʿ into the jussive
    and is its OWN segment; a resumption/result fāʾ is its own clitic."""
    if case.get("particle") == "lam_al_amr":
        return "governor_segment_forces_jussive"
    return "na"


def _imperative_lam_superseded(case):
    """Pre-fix: the lām (and fāʾ) were folded into the verb token, dropping the governor role."""
    return "lam_folded_into_verb_no_governor"


# --- N2. negation is owned by its own particle, not the verb it precedes (nahw@2) ---------------------------
def _negation_owner_corrected(case):
    """NEGATION is owned by its own particle (لا/ما/لم/لن). A verb standing after a negator is still
    a CONTENT verb carrying its root, not a function/NEG token."""
    role = case.get("token_role")
    if role == "negator":
        return "negation_particle"
    if role == "verb_after_negator":
        return "content_verb_keeps_root"
    return "na"


def _negation_owner_superseded(case):
    """Pre-fix: the negated verb itself was tagged as the negation / a function token."""
    return "verb_mislabeled_as_negation"


# --- N3. a verb-shaped triliteral-root token is content, never a bare function particle (nahw@2) ------------
def _funcword_content_corrected(case):
    """Function-vs-content routing: a verb-shaped token with a triliteral root is CONTENT, never a
    bare function particle."""
    if case.get("verb_shaped") and case.get("triliteral_root"):
        return "content_verb"
    if case.get("is_true_particle"):
        return "function_particle"
    return "na"


def _funcword_content_superseded(case):
    """Pre-fix: a verb form + root was mislabeled as a function particle."""
    return "mislabeled_as_particle"


# --- N4. the attached pronoun's iʿrāb role is stated per occurrence (nahw@2) --------------------------------
def _pronoun_irab_corrected(case):
    """The attached pronoun's iʿrāb role (fāʿil / nāʾib fāʿil / mafʿūl bihi / muḍāf ilayh) is stated
    per occurrence, not left unstated."""
    role = case.get("irab_role")
    if role in _VALID_PRONOUN_IRAB:
        return "role_stated:" + role
    return "role_unstated"


def _pronoun_irab_superseded(case):
    """Pre-fix: the attached pronoun carried no per-occurrence iʿrāb role."""
    return "role_unstated"


CORRECTED = {
    "mudari_prefix_segment": _mudari_prefix_corrected,
    "derived_form_root": _derived_root_corrected,
    "attached_unit_segment": _attached_unit_corrected,
    "occurrence_form_committed": _occurrence_form_corrected,
    "oversegment_mim": _oversegment_mim_corrected,
    "coarse_split_complete": _coarse_split_corrected,
    "imperative_lam_governor": _imperative_lam_corrected,
    "negation_owned_by_particle": _negation_owner_corrected,
    "funcword_content_routing": _funcword_content_corrected,
    "pronoun_irab_role": _pronoun_irab_corrected,
}

SUPERSEDED = {
    "mudari_prefix_segment": _mudari_prefix_superseded,
    "derived_form_root": _derived_root_superseded,
    "attached_unit_segment": _attached_unit_superseded,
    "occurrence_form_committed": _occurrence_form_superseded,
    "oversegment_mim": _oversegment_mim_superseded,
    "coarse_split_complete": _coarse_split_superseded,
    "imperative_lam_governor": _imperative_lam_superseded,
    "negation_owned_by_particle": _negation_owner_superseded,
    "funcword_content_routing": _funcword_content_superseded,
    "pronoun_irab_role": _pronoun_irab_superseded,
}
