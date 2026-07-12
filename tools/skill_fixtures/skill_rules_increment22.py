#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic discriminators for the INCREMENT-22 skill fixtures (candidate sarf@2.2 / nahw@2.2).

Consolidation layer of the QAMUS-RICH-NORM-001 cycle (2026-07-12): the rich-hover normative-defect
ANDON (detector gaps G1-G7), the norm@1 normalization contract (clauses N-ROOT / N-LANG / N-SEG /
N-PED / N-CONS), the global lexeme join + entry-root-inheritance lattice, and the C4/C5/W13 wave
refinements. Companion to skill_rules.py + skill_rules_richseg.py + skill_rules_increment21.py, kept
SEPARATE so it does not collide with the released @2 / candidate @2.1 fixtures; it merges alongside
them at the @2.2 release.

Each candidate @2.2 rule is encoded as a PAIR:
  - a CORRECTED rule (the candidate sarf@2.2 / nahw@2.2 behaviour), and
  - the SUPERSEDED rule it replaces (the exact pre-fix behaviour that produced the ANDON defect —
    a C1-C5 detector blind spot, an un-gated norm clause, or a lattice mis-join).

RED-FIRST contract (asserted by test_skill_fixtures_increment22.py):
  GREEN     : corrected_rule(case) == correct_label
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label

NON-CONSTANT-DISCRIMINATOR contract (the SEND-BACK guard, now a harness gate): every CORRECTED
discriminator must branch on its input — across a rule's fixtures it MUST return >=2 distinct labels.
A corrected rule that returns a constant is rejected even if the constant happens to match.

These are OBSERVED normalization / morphosyntactic rules with source-addressed Qurʾānic + contract
evidence; not theological claims. Stdlib only, no network, no MCP, no live services. Deterministic.
"""

# --- shared vocabularies ------------------------------------------------------------------------
# norm@1 N-LANG-01 forbidden internal meta/process substrings (rendered-field blocklist).
_META_MARKERS = (
    "no unsupported public source label", "no unsupported root", "no public root asserted",
    "visible piece accounted", "accounted for", "retained and accounted",
    "preserved where relevant", "exposes the visible", "not separately asserted",
    "root not certified", "function only no root", "no unsupported public source",
)
# closed typed-rootless-rationale vocabulary (N-ROOT-02).
_TYPED_ROOTLESS = {"function-word", "proper-name", "jamid-contested", "pending"}
# U+0670 ARABIC LETTER SUPERSCRIPT ALEF (dagger-alef) → plain alif for the wbw match key (W13).
_DAGGER_ALEF = "ٰ"


# ================================================================================================
# SARF @2.2 — norm@1 clauses, ANDON detector gaps, lexeme-join, C4/C5/W13 refinements
# ================================================================================================

# --- S1. N-ROOT-01: a content segment MUST NOT decline its root with hedge prose (G1/G2) ---------
def _root_hedge_ban_corrected(case):
    """A row carrying a content segment (verb/noun/adjective/proper-noun/qg-segment) that asserts no
    root and hedges ('no public root asserted', 'function only no root') is nonconforming — even when
    it is multi-segment (فَحَقَّ = FA+TOK) or a clean single stem (خَلَقَ), the shapes C2's single-
    segment / verb-stem gates skip."""
    if case.get("is_content_segment") and not case.get("root_asserted") and case.get("hedge_present"):
        return "flag_root_hedge_violation"
    return "conform"


def _root_hedge_ban_superseded(case):
    """Pre-fix: C2 only fired on a single-segment derived whole-token, so the multi-segment / clean-
    stem hedge shapes escaped every gate."""
    return "conform"


# --- S2. N-ROOT-02: a genuinely rootless row MUST carry an explicit typed rationale --------------
def _typed_rootless_rationale_corrected(case):
    """A rootless content row MUST carry a typed rationale from the closed vocabulary
    (function-word / proper-name / jamid-contested / pending) in a dedicated field — never silent,
    never hedge prose standing in for the typed value."""
    if case.get("root_asserted"):
        return "na_has_root"
    if case.get("typed_rationale") in _TYPED_ROOTLESS:
        return "conform_typed_rationale"
    return "flag_untyped_rootless"


def _typed_rootless_rationale_superseded(case):
    """Pre-fix: no typed-rationale field existed; a rootless row was accepted silently."""
    return "accept_silent_rootless"


# --- S3. N-LANG-01: no internal meta-/process-language or leaked label notation in rendered fields
def _field_meta_ban_corrected(case):
    """No rendered field may carry validator/process meta-language (superset of C4's three phrases)
    or leaked uppercase segment-label notation (FA:فَ, TOK:حَقَّ, ADJ:حَقِيقٌ) inside
    learner_explanation."""
    if case.get("has_meta_marker") or case.get("has_label_notation"):
        return "flag_meta_language"
    return "conform_english_field"


def _field_meta_ban_superseded(case):
    """Pre-fix: C4 matched only 'as context requires' / 'not separately asserted' / 'exposes the
    visible'; the meta-markers and the label-notation leak escaped."""
    return "conform_english_field"


# --- S4. N-LANG-02: learner-facing fields MUST be English, not an Arabic-prose dump --------------
def _english_led_corrected(case):
    """learner_explanation MUST be substantive English; an Arabic running-prose dump is flagged.
    Short quoted Arabic forms inside an English sentence stay clean."""
    aw = case.get("arabic_words", 0)
    lw = case.get("latin_words", 0)
    ar = case.get("arabic_ratio", 0.0)
    if aw >= 6 or (aw >= 4 and ar >= 0.6) or (lw < 3 and aw >= 3):
        return "flag_arabic_dump"
    return "conform_english_led"


def _english_led_superseded(case):
    """Pre-fix: no class inspected learner-text language balance; an iʿrāb Arabic dump passed."""
    return "conform_english_led"


# --- S5. N-PED-01: every segment MUST carry a non-empty gloss_contribution -----------------------
def _gloss_present_corrected(case):
    """Every segment MUST carry a non-empty gloss_contribution; a blank gloss is nonconforming."""
    if case.get("any_segment_blank_gloss"):
        return "flag_missing_gloss"
    return "conform_all_glossed"


def _gloss_present_superseded(case):
    """Pre-fix: the schema permitted an empty gloss_contribution."""
    return "conform_all_glossed"


# --- S6. N-CONS-01: same-surface rows MUST cohere on root (the حَقَّتْ / فَحَقَّ drift) ----------
def _same_surface_coherence_corrected(case):
    """Within a diacritic-folded bare-surface group where >=1 content row asserts a root, any content
    row that hedges/omits the root is nonconforming (39:71:30 حَقَّتْ asserts ح ق ق while sibling
    38:14:6 فَحَقَّ declines it)."""
    if case.get("sibling_asserts_root") and case.get("this_row_hedges"):
        return "flag_incoherent_sibling"
    if case.get("sibling_asserts_root") and case.get("this_asserts_root"):
        return "coherent"
    return "na"


def _same_surface_coherence_superseded(case):
    """Pre-fix: no cross-row same-surface check existed."""
    return "no_cross_row_check"


# --- S7. N-CONS-02 / lexeme join: entry-root inheritance is a certification-EVIDENCE tier (tier-0)
def _entry_root_inherit_corrected(case):
    """A rootless content row whose (dagger-alef-normalized) surface matches a Qamus entry's headword
    or usage[].forms inherits that entry's root as a CANDIDATE (16:3:1 خَلَقَ is a headword; 7:54:23
    مُسَخَّرَٰتٍ matches v198 usage.forms). Never certified from pattern — attested source only; stays
    candidate until the 2-vote."""
    if case.get("surface_matches_entry_form") and case.get("attested_source"):
        return "inherit_candidate_root"
    return "authoring_first"


def _entry_root_inherit_superseded(case):
    """Pre-fix (G7): no gate cross-referenced a rootless row against the entry that owns the surface;
    a dictionary headword was served rootless."""
    return "served_rootless_no_inheritance"


# --- S8. lexeme-join correction: a bare entry_id is example-context ONLY, never a root (tier-A) ---
def _entry_id_context_only_corrected(case):
    """A row's carrier entry_id is an example-context link, NOT a root assertion (فَوْقَكُمُ carries
    the أخذ entry's id). The carrier certifies a root ONLY when the surface is actually a form of that
    entry; a bare id never asserts a root."""
    if case.get("carrier_entry_id_present") and case.get("surface_is_form_of_entry"):
        return "carrier_usable_tierA"
    if case.get("carrier_entry_id_present"):
        return "context_only_no_root"
    return "na"


def _entry_id_context_only_superseded(case):
    """Pre-fix: a bare carrier entry_id was read as asserting that entry's root."""
    return "assert_root_from_entry_id"


# --- S9. lexeme-join conflict: a rooted-row-vs-entry root disagreement is NEVER auto-resolved -----
def _root_entry_conflict_corrected(case):
    """When a row's asserted root disagrees with the root of the entry that attests the same surface
    (464 rows / 804 edges in the join), route to 2-vote/review and NEVER auto-resolve; an agreeing
    pair is confirmed."""
    ra = case.get("row_root")
    re = case.get("entry_root")
    if ra and re and ra != re:
        return "route_two_vote_never_auto"
    if ra and re and ra == re:
        return "confirm_coherent"
    return "na"


def _root_entry_conflict_superseded(case):
    """Pre-fix: a row/entry root disagreement was silently reconciled to one root."""
    return "auto_resolve_pick_one"


# --- S10. G4: a root asserted in the Arabic idiom مادة (كلم) MUST be recognized, not read rootless
def _madda_prose_root_corrected(case):
    """A root carried in the Arabic lexicographic idiom مادة (كلم) / مادّة is an ASSERTED root; the
    detector's `root <radicals>` regex missed the مادة idiom and read the row as rootless (39:71:31
    كَلِمَةُ carries مادة (كلم))."""
    if case.get("madda_prose_present"):
        return "root_asserted_from_madda"
    if case.get("root_field_present"):
        return "root_asserted"
    return "rootless"


def _madda_prose_root_superseded(case):
    """Pre-fix: only `root <radicals>` was recognized; the مادة idiom read as rootless."""
    return "rootless"


# --- S11. G6 / O-2: a sound plural ـات/ـين (+tanwīn) swallow is a suffix defect (C5 pronoun-only) -
def _sound_plural_swallow_corrected(case):
    """C5's enclitic vocabulary is pronoun-only; a sound feminine/masculine plural ـات/ـين (+tanwīn)
    fused into a single blob (7:54:23 مُسَخَّرَٰتٍ) is a suffix-swallow that must be flagged and split
    (STEM + PL-F/PL), independent of the root check. GUARD: a trailing ت that is a ROOT RADICAL routes
    to 2-vote, not a split (sarf-root-radical-not-clitic)."""
    if case.get("ends_sound_plural") and case.get("single_blob"):
        if case.get("trailing_ta_is_radical"):
            return "guard_two_vote_radical_ta"
        return "flag_plural_swallow"
    if case.get("ends_sound_plural") and not case.get("single_blob"):
        return "conform_pl_segment"
    return "na"


def _sound_plural_swallow_superseded(case):
    """Pre-fix: C5 only knew enclitic pronouns; ـات/ـين + tanwīn were outside its vocabulary."""
    return "no_flag_pl_pronoun_only"


# --- S12. C5/W1-A: the مُ- derivational pattern is stem-internal for colour but NAMED in morphline -
def _mu_pattern_taught_corrected(case):
    """The مُ- derivational pattern (مُفَعَّل / تَفَعَّل) is stem-internal for COLOUR (never peeled as a
    separate coloured segment), but when the entry attests the form it MUST be NAMED in the morphline
    (مُسَخَّر → 'Form II passive participle, wazn mufaʿʿal'); if unattested it is held, not fabricated."""
    if case.get("mu_pattern") and case.get("entry_attests_form"):
        return "name_pattern_stem_internal"
    if case.get("mu_pattern"):
        return "hold_not_attested"
    return "na"


def _mu_pattern_taught_superseded(case):
    """Pre-fix: the مُ- was either peeled as its own segment or left silent (never named)."""
    return "peel_or_silent_mu"


# --- S13. C4 + measured-effect telemetry: the learner sentence is a template of ASSERTED slots -----
def _honest_template_corrected(case):
    """The learner sentence renders from a template whose slots emit ONLY facts the morphline actually
    asserts; if any slot fact is abstained the honest-generic variant renders (generalizes the
    completeness-claim rule; 100%-agreement telemetry on the ONH/W13 waves confirms the honest form)."""
    if case.get("all_slot_facts_asserted"):
        return "render_full_template"
    return "render_honest_generic"


def _honest_template_superseded(case):
    """Pre-fix: the full template (with unasserted slots) rendered unconditionally."""
    return "render_full_template"


# --- S14. C5/W1-A: loc-range claims need EXTERNAL authority — local indexes are circular ----------
def _loc_external_authority_corrected(case):
    """A loc-range / address claim MUST be prevalidated against an EXTERNAL authority (corpus/wbw
    oracle), because a local index validating itself is circular — the 17:1:22 catch proved a local
    index confirmed an address the external authority rejected. Local-only confirmation cannot
    prevalidate."""
    if case.get("external_authority_confirms"):
        return "emit_prevalidated"
    if case.get("only_local_index"):
        return "cannot_prevalidate_local_circular"
    return "na"


def _loc_external_authority_superseded(case):
    """Pre-fix: a local index self-confirmed the address and the row was emitted."""
    return "emit_from_local_index"


# --- S15. W13: the demonstrative dagger-alef (U+0670) MUST be normalized before matching ----------
def _dagger_alef_normalize_corrected(case):
    """The demonstrative ذٰلِك / كَذٰلِك (and forms like مُسَخَّرَٰت) carries a superscript/dagger alef
    (U+0670) that the match engine missed twice; normalize dagger-alef → plain alif before the wbw /
    entry-form match. A form that already matches without a dagger-alef is untouched."""
    if case.get("has_dagger_alef"):
        return "match_after_normalization" if case.get("normalized_matches") else "no_match"
    return "match_plain" if case.get("normalized_matches") else "no_match"


def _dagger_alef_normalize_superseded(case):
    """Pre-fix: the raw dagger-alef surface was matched literally and missed the entry/wbw form."""
    return "engine_miss_no_match"


# ================================================================================================
# NAHW @2.2 — norm@1 rendered-field discipline for the grammatical notes
# ================================================================================================

# --- N1. N-LANG-03: nahw_note MAY use Arabic grammatical terms but MUST lead with English ---------
def _note_leads_english_corrected(case):
    """A sarf_note / nahw_note may cite Arabic grammatical terms but MUST lead with English; a note
    that opens as an Arabic-prose dump is flagged."""
    if case.get("note_leads_arabic_dump"):
        return "flag_note_not_english_led"
    return "conform_english_led_note"


def _note_leads_english_superseded(case):
    """Pre-fix: no gate inspected note-language ordering."""
    return "conform_english_led_note"


# --- N2. N-LANG-01/02: the nahw_note MUST NOT be the raw analyzer Arabic iʿrāb string, verbatim -----
def _irab_not_verbatim_corrected(case):
    """The nahw_note MUST NOT be the raw upstream-analyzer Arabic iʿrāb string pasted verbatim into the
    learner field (39:71:31 كَلِمَةُ carried 'فاعل مرفوع وعلامة رفعه الضمة وهو مضاف'); render an English
    iʿrāb ('subject, nominative; first term of an iḍāfa')."""
    if case.get("nahw_note_is_verbatim_source_arabic"):
        return "flag_verbatim_irab"
    return "conform_english_irab"


def _irab_not_verbatim_superseded(case):
    """Pre-fix: the verbatim raw-analyzer Arabic iʿrāb string was accepted into the rendered field."""
    return "conform_english_irab"


# --- N3. N-PED-02: a knowable mood note MUST commit, never hedge 'as context requires' -----------
def _mood_note_commit_corrected(case):
    """When mood is knowable at the exact address the nahw_note MUST commit it; it MUST NOT hedge
    'as (the) context requires'. When genuinely unknowable it states a named ambiguity."""
    if case.get("mood_knowable") and case.get("note_hedges_as_context"):
        return "flag_uncommitted_mood_note"
    if case.get("mood_knowable"):
        return "commit_mood_note"
    return "named_ambiguity"


def _mood_note_commit_superseded(case):
    """Pre-fix: the 'as context requires' hedge was accepted even when mood was knowable."""
    return "hedge_as_context_accepted"


# ------------------------------------------------------------------------------------------------
CORRECTED = {
    "root_hedge_ban": _root_hedge_ban_corrected,
    "typed_rootless_rationale": _typed_rootless_rationale_corrected,
    "field_meta_ban": _field_meta_ban_corrected,
    "english_led": _english_led_corrected,
    "gloss_present": _gloss_present_corrected,
    "same_surface_coherence": _same_surface_coherence_corrected,
    "entry_root_inherit": _entry_root_inherit_corrected,
    "entry_id_context_only": _entry_id_context_only_corrected,
    "root_entry_conflict": _root_entry_conflict_corrected,
    "madda_prose_root": _madda_prose_root_corrected,
    "sound_plural_swallow": _sound_plural_swallow_corrected,
    "mu_pattern_taught": _mu_pattern_taught_corrected,
    "honest_template": _honest_template_corrected,
    "loc_external_authority": _loc_external_authority_corrected,
    "dagger_alef_normalize": _dagger_alef_normalize_corrected,
    "note_leads_english": _note_leads_english_corrected,
    "irab_not_verbatim": _irab_not_verbatim_corrected,
    "mood_note_commit": _mood_note_commit_corrected,
}

SUPERSEDED = {
    "root_hedge_ban": _root_hedge_ban_superseded,
    "typed_rootless_rationale": _typed_rootless_rationale_superseded,
    "field_meta_ban": _field_meta_ban_superseded,
    "english_led": _english_led_superseded,
    "gloss_present": _gloss_present_superseded,
    "same_surface_coherence": _same_surface_coherence_superseded,
    "entry_root_inherit": _entry_root_inherit_superseded,
    "entry_id_context_only": _entry_id_context_only_superseded,
    "root_entry_conflict": _root_entry_conflict_superseded,
    "madda_prose_root": _madda_prose_root_superseded,
    "sound_plural_swallow": _sound_plural_swallow_superseded,
    "mu_pattern_taught": _mu_pattern_taught_superseded,
    "honest_template": _honest_template_superseded,
    "loc_external_authority": _loc_external_authority_superseded,
    "dagger_alef_normalize": _dagger_alef_normalize_superseded,
    "note_leads_english": _note_leads_english_superseded,
    "irab_not_verbatim": _irab_not_verbatim_superseded,
    "mood_note_commit": _mood_note_commit_superseded,
}
