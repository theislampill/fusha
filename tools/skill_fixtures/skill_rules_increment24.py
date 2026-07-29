#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic discriminators for the INCREMENT-24 skill fixtures (candidate sarf@2.4 / nahw@2.4).

P00-vertical-slice pilot dogfood (2026-07-29): the first complete source-grounded particle family
(p007 jarr clitic لِـ on noun hosts, 12 occurrences end-to-end) plus the two-vote canary run and the
particle-denominator calibration, distilled into 9 candidate @2.4 rules — 5 sarf + 4 nahw.
Companion to skill_rules.py + skill_rules_richseg.py + skill_rules_increment21/22/23.py, kept
SEPARATE so it does not collide with the released @2 / candidate @2.1–@2.3 fixtures; it merges
alongside them at the @2.4 release.

Each candidate @2.4 rule is encoded as a PAIR:
  - a CORRECTED rule (the candidate sarf@2.4 / nahw@2.4 behaviour), and
  - the SUPERSEDED rule it replaces (the exact pre-pilot behaviour that produced the measured
    defect — a blanket لِ prefix strip over lexical-lām/pronoun/verb hosts, a per-page article
    carve fork, a byte-compare false boundary fork on NFC-equivalent mark orders, a governor-null
    iʿrāb claim the validator rejects, a notation-variant false disagreement, or the tajarrud
    canary false-FAIL).

RED-FIRST contract (asserted by test_skill_fixtures_increment24.py):
  GREEN     : corrected_rule(case) == correct_label
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label

NON-CONSTANT-DISCRIMINATOR contract: every CORRECTED discriminator must branch on its input —
across a rule's fixtures it MUST return >=2 distinct labels.

These are OBSERVED segmentation / normalization / morphosyntactic rules with source-addressed
Qurʾānic + pilot-packet evidence; not theological claims. Stdlib only, no network, no MCP,
no live services. Deterministic.
"""
import unicodedata


# ================================================================================================
# SARF @2.4 — لِ clitic/host segmentation, fused-token letter ownership, NFC span parity
# ================================================================================================

# --- S1. strict لِ+kasra prefix routes by HOST, never by surface shape alone ---------------------
def _li_clitic_carve_corrected(case):
    """A لِ+kasra prefix candidate is a jarr-clitic carve ONLY over a nominal host. A lexical
    initial lām (root radical, لِبَاسٌ ل ب س) rejects the carve; a pronoun host (لِى) is a genuine
    jarr particle but OUTSIDE the noun-host family; a muḍāriʿ host routes to the lām-taʿlīl rival
    (nahw decides the type). Calibration S7 measured the blanket stripper at 16.7% precision."""
    if case.get("lexical_lam_root_initial"):
        return "reject_carve_lexical_initial_lam"
    host = case.get("host_pos", "")
    if host == "pronoun":
        return "route_pronoun_host_outside_noun_family"
    if host.startswith("verb"):
        return "route_lam_talil_rival"
    return "carve_jarr_clitic_noun_host"


def _li_clitic_carve_superseded(case):
    """Pre-pilot: the discovery prefix-stripper claimed EVERY لِ+kasra token as a jarr-clitic carve
    on a noun host (surface shape only — no مادة check, no host-POS check, no pronoun check)."""
    return "carve_jarr_clitic_noun_host"


# --- S2. a candidate clitic lām that is the HOST'S initial root radical rejects the carve --------
def _lexical_lam_guard_corrected(case):
    """If the surface-initial lām is the host's initial root radical (مادة starts with ل and the
    per-occurrence iʿrāb shows no jarr clause — لِبَاسٌ wazn فِعَال مادة ل ب س), the carve is a
    false split. A lexical-lām-initial host UNDER a real jarr lām is confirmed only by the
    per-occurrence iʿrāb attesting the jarr clause (لِّلَّذِينَ)."""
    if case.get("madda_initial") == "ل":
        if case.get("irab_attests_jarr_clause"):
            return "carve_confirmed_by_irab"
        return "reject_carve_root_radical_lam"
    return "carve_allowed_lam_not_radical"


def _lexical_lam_guard_superseded(case):
    """Pre-pilot: shape-only matching allowed the carve whenever the surface began لِ + kasra."""
    return "carve_allowed_shape_only"


# --- S3. pronoun hosts are a distinct family: jarr particle + ضمير, both rootless ----------------
def _pronoun_host_guard_corrected(case):
    """لِ + pronoun (لِى) is a genuine jarr preposition but its host is a mabnī pronoun: both
    pieces are rootless (حرف + ضمير) and the row belongs to the pronoun-host family — never to the
    noun-host family and never to a noun-host projection template. A noun host whose muḍāf-ilayh
    is a pronoun (لِقَوْمِهِۦ) is still a NOUN host (the pronoun sits inside the host phrase)."""
    if case.get("host_class") == "pronoun":
        return "jarr_pronoun_host_family_rootless"
    return "jarr_noun_host_family"


def _pronoun_host_guard_superseded(case):
    """Pre-pilot: the family classifier lumped every لِ carve into the noun-host lane."""
    return "jarr_noun_host_family"


# --- S4. fused لِ + article: exact base-letter ownership, one canonical carve per surface --------
def _fused_lil_carve_corrected(case):
    """The carve of a لِ + ال host is decided by the WRITTEN form, once per occurrence surface:
    when the article's alif is elided and the writing fuses with the Name (لِلَّهِ rasm), the
    clitic owns exactly its own lām+kasra and the fused writing of the Name owns the rest
    (لِ ∣ لَّهِ); when the assimilated article's lām is written (لِلنَّاسِ), it gets its own span
    (لِ ∣ ل ∣ نَّاسِ); a bare noun host carves two spans (لِ ∣ غَيْرِ). Every span concatenates
    byte-exact; each base letter carries its own trailing combining marks."""
    art = case.get("article_written", "none")
    if art == "elided_into_name_fusion":
        return "carve_clitic_lam_plus_fused_name"
    if art == "assimilated_visible":
        return "carve_clitic_article_host_three_spans"
    return "carve_clitic_host_two_spans"


def _fused_lil_carve_superseded(case):
    """Pre-pilot (live behaviour): the article was folded into the host on some pages and carved
    separately on others — the SAME surface للناس carved two different ways at its two occurrences
    (the per-surface fork the projection contract §1.1/§2.3 exists to kill)."""
    return "fold_article_into_host_per_page"


# --- S5. NFC-normalize both sides before any span/boundary parity comparison ---------------------
def _nfc_span_parity_corrected(case):
    """Combining-mark codepoint ORDER (vowel-before-shadda vs shadda-before-vowel) is not a carve
    fork: NFC-normalize BOTH sides before span comparison (public bytes are never mutated — this is
    a comparison key only). A difference that survives NFC is a true carve fork."""
    a = unicodedata.normalize("NFC", case.get("side_a", ""))
    b = unicodedata.normalize("NFC", case.get("side_b", ""))
    if a == b:
        return "boundary_equivalent_after_nfc"
    return "true_carve_fork"


def _nfc_span_parity_superseded(case):
    """Pre-pilot: raw byte equality — NFC-equivalent mark orders reported as boundary forks
    (hit 12:31:24, 24:35:44, 24:31:23 in the matrix↔live comparison)."""
    if case.get("side_a", "") == case.get("side_b", ""):
        return "boundary_equivalent_after_nfc"
    return "boundary_fork_reported"


# ================================================================================================
# NAHW @2.4 — preposition government, khabar-muqaddam notation, tajarrud mood basis, lām typing
# ================================================================================================

# --- N6. an iʿrāb jarr claim names the preposition itself as governor — never null ---------------
def _jarr_governor_corrected(case):
    """Case is a consequence of a stated governor. For a majrūr the governor is the PREPOSITION
    ITSELF (relation preposition-governs-majrur) — including when the jarr-majrūr phrase is a
    fronted predicate: attachment (mutaʿalliq/khabar plane) is a separate field and never a reason
    to null the governor. A null-governor jarr claim is repaired, not emitted."""
    gov = case.get("governor")
    if gov == "preposition_itself":
        return "accept_preposition_governor"
    if gov is None:
        return "repair_set_preposition_governor"
    return "accept_stated_governor"


def _jarr_governor_superseded(case):
    """Pre-pilot: fronted-predicate rows were emitted with governor:null (the attachment was
    mistaken for the government), which the iʿrāb validator rightly rejects."""
    if case.get("governor") is None:
        return "emit_null_governor_case_claim"
    return "accept_stated_governor"


# --- N7. khabar muqaddam: two standard notations are ONE analysis under one reason key -----------
_KHABAR_MUQADDAM_NOTATIONS = {"khabar_muqaddam", "mutaalliq_elided_fronted_khabar"}


def _khabar_muqaddam_notation_corrected(case):
    """For a jarr-majrūr (shibh al-jumla) fronted predicate, 'khabar muqaddam' and 'mutaʿalliq to
    an elided fronted khabar' are the two standard notations of ONE analysis: they share one
    reason key (khabar-muqaddam-shibh-jumla) and never count as reviewer disagreement. A genuinely
    different attachment (ṣifa, ḥāl, verb-attachment) IS a real disagreement."""
    a = case.get("notation_a")
    b = case.get("notation_b")
    if a == b:
        return "one_analysis_shared_reason_key"
    if a in _KHABAR_MUQADDAM_NOTATIONS and b in _KHABAR_MUQADDAM_NOTATIONS:
        return "one_analysis_shared_reason_key"
    return "genuine_attachment_disagreement"


def _khabar_muqaddam_notation_superseded(case):
    """Pre-pilot: whitespace-compacted exact-string comparison — the two notations of one analysis
    were recorded as a textual disagreement (canary 3; slice rows 9:120:3 / 4:11:5)."""
    if case.get("notation_a") == case.get("notation_b"):
        return "one_analysis_shared_reason_key"
    return "textual_disagreement_recorded"


# --- N8. rafʿ by tajarrud satisfies the governor requirement for verb mood -----------------------
def _tajarrud_mood_corrected(case):
    """A muḍāriʿ marfūʿ by tajarrud (absence of any nāṣib/jāzim) carries mood_basis=tajarrud and
    needs NO overt governor: the 'case value + visible sign ⇒ governor required' rule is a NOMINAL
    iʿrāb rule. Nominal case claims still require their governor."""
    if case.get("claim_kind") == "verb_mood":
        if case.get("mood_basis") == "tajarrud":
            return "accept_mood_basis_tajarrud"
        if case.get("governor"):
            return "accept_governed_mood"
        return "reject_unbased_mood_claim"
    if case.get("governor"):
        return "accept_governed_case"
    return "reject_missing_governor"


def _tajarrud_mood_superseded(case):
    """Pre-pilot (the canary-1 contract bug): any case/mood claim with a visible sign and no named
    governor was rejected — mislabelling default-mood verbs both reviewers got right."""
    if case.get("governor"):
        return "accept_governed_case"
    return "reject_missing_governor"


# --- N9. token-initial لِ types by HOST POS: jarr / taʿlīl / amr ---------------------------------
def _lam_function_by_host_corrected(case):
    """A token-initial لِ is typed by its host's POS+mood before any gloss or government claim:
    nominal host ⇒ لام الجر (governs jarr); muḍāriʿ manṣūb (بأن مضمرة) ⇒ لام التعليل (subjunctive,
    NOT jarr); muḍāriʿ majzūm ⇒ لام الأمر (jussive). A jarr claim over a verb host is never valid."""
    host = case.get("host_pos", "")
    if host == "noun":
        return "lam_jarr_governs_majrur"
    if host == "verb_mudari_mansub":
        return "lam_talil_an_mudmara_subjunctive"
    if host == "verb_mudari_majzum":
        return "lam_amr_jussive"
    return "route_lam_type_review"


def _lam_function_by_host_superseded(case):
    """Pre-pilot: the p007 lattice's blanket function candidate read every لِ as the jarr lām."""
    return "lam_jarr_governs_majrur"


# ------------------------------------------------------------------------------------------------
CORRECTED = {
    "li_clitic_carve": _li_clitic_carve_corrected,
    "lexical_lam_guard": _lexical_lam_guard_corrected,
    "pronoun_host_guard": _pronoun_host_guard_corrected,
    "fused_lil_carve": _fused_lil_carve_corrected,
    "nfc_span_parity": _nfc_span_parity_corrected,
    "jarr_governor": _jarr_governor_corrected,
    "khabar_muqaddam_notation": _khabar_muqaddam_notation_corrected,
    "tajarrud_mood": _tajarrud_mood_corrected,
    "lam_function_by_host": _lam_function_by_host_corrected,
}

SUPERSEDED = {
    "li_clitic_carve": _li_clitic_carve_superseded,
    "lexical_lam_guard": _lexical_lam_guard_superseded,
    "pronoun_host_guard": _pronoun_host_guard_superseded,
    "fused_lil_carve": _fused_lil_carve_superseded,
    "nfc_span_parity": _nfc_span_parity_superseded,
    "jarr_governor": _jarr_governor_superseded,
    "khabar_muqaddam_notation": _khabar_muqaddam_notation_superseded,
    "tajarrud_mood": _tajarrud_mood_superseded,
    "lam_function_by_host": _lam_function_by_host_superseded,
}
