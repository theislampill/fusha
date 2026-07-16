#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic discriminators for the INCREMENT-23 skill fixtures (candidate sarf@2.3 / nahw@2.3).

Window-1-measured flywheel (2026-07-16): the first live-seeding window's WAVE-RECORD adjudicator catches
plus the C2-reviewerA calibration deltas, distilled into 8 candidate @2.3 rules — 6 sarf + 2 nahw.
Companion to skill_rules.py + skill_rules_richseg.py + skill_rules_increment21.py +
skill_rules_increment22.py, kept SEPARATE so it does not collide with the released @2 / candidate
@2.1 / @2.2 fixtures; it merges alongside them at the @2.3 release.

Each candidate @2.3 rule is encoded as a PAIR:
  - a CORRECTED rule (the candidate sarf@2.3 / nahw@2.3 behaviour), and
  - the SUPERSEDED rule it replaces (the exact pre-fix behaviour that produced the Window-1 defect —
    a wrong join-inherited root, a false out-of-range hold, a surface↔gloss smear, an empty segment
    gloss, or an asymmetric-normalization no_match).

RED-FIRST contract (asserted by test_skill_fixtures_increment23.py):
  GREEN     : corrected_rule(case) == correct_label
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label

NON-CONSTANT-DISCRIMINATOR contract (the SEND-BACK guard, now a harness gate): every CORRECTED
discriminator must branch on its input — across a rule's fixtures it MUST return >=2 distinct labels.
A corrected rule that returns a constant is rejected even if the constant happens to match.

These are OBSERVED normalization / morphosyntactic rules with source-addressed Qurʾānic + wave-record
evidence; not theological claims. Stdlib only, no network, no MCP, no live services. Deterministic.
"""

# --- shared normalizers -------------------------------------------------------------------------
# Romanized-radical → Arabic map (for cross-source root agreement; w/y kept DISTINCT so سمو≠سمي).
_TRANSLIT_RADICAL = {
    "s": "س", "m": "م", "w": "و", "y": "ي", "l": "ل", "k": "ك", "q": "ق",
    "r": "ر", "n": "ن", "d": "د", "b": "ب", "t": "ت", "h": "ه", "f": "ف",
}


def _norm_root(s):
    """Fold a root token to a comparison key: strip spaces, transliterate latin radicals to Arabic.
    w/y stay distinct (سمو vs سمي remain a real conflict); only romanization is reconciled."""
    out = []
    for ch in s.replace(" ", ""):
        out.append(_TRANSLIT_RADICAL.get(ch.lower(), ch))
    return "".join(out)


# Orthographic fold for corpus-word matching: hamza-seat drop + alif/waw + ة/ه folding. Deliberately
# lossy so hamza/alif spelling variants collapse; the ambiguity guard (below) refuses distinct raw pairs.
_ORTHO_FOLD = {
    "أ": "", "إ": "", "آ": "ا", "ٱ": "", "ء": "", "ؤ": "و", "ئ": "ي",
    "ة": "ه", "ى": "ا", "و": "ا",
}


def _ortho_fold(s):
    return "".join(_ORTHO_FOLD.get(ch, ch) for ch in s)


# ================================================================================================
# SARF @2.3 — root-certification gates, per-segment gloss, orthographic matching
# ================================================================================================

# --- S1. surface/skeleton join NEVER certifies a root without a per-occurrence مادة -------------
def _surface_join_corrected(case):
    """A join-inherited root is a candidate only; it certifies iff a per-occurrence surface-matched
    مادة confirms it (a strong triliteral with no skeleton collision). Otherwise it stays
    candidate_root_uncertified (مال hollow, نُقِرُّ geminate, يده weak-final all collide)."""
    if case.get("per_occurrence_madda_present"):
        return "root_certified"
    return "candidate_root_uncertified"


def _surface_join_superseded(case):
    """Pre-fix: a same-skeleton join to an entry-form was read as certifying the entry root."""
    return "certify_join_root"


# --- S2. a closed-class function word never inherits a content root by surface join --------------
def _closed_class_corrected(case):
    """A closed-class function word carries no content مادة: a particle/negation is حرف (rootless), a
    pronoun is اسم مبني (rootless). A genuine content homograph (POS-resolved verb مَنَّ) keeps its root."""
    if not case.get("is_closed_class"):
        return "root_certified"
    if "pronoun" in case.get("surface_class", ""):
        return "rootless_ism_mabni_no_madda"
    return "rootless_harf_no_madda"


def _closed_class_superseded(case):
    """Pre-fix: the surface-join laundering assigned the function word the entry's content root."""
    return "certify_content_root"


# --- S3. two certified sources disagreeing on the SAME occurrence root are HELD, never voted -----
def _root_conflict_held_corrected(case):
    """Normalize romanization first; if the two source roots agree it certifies (false-alarm cleared).
    If they still differ and both are classical, HOLD (2-vote/owner) — never majority-vote or pick."""
    a = _norm_root(case.get("root_source_a", ""))
    b = _norm_root(case.get("root_source_b", ""))
    if a == b:
        return "certify_agreed_root"
    if case.get("classically_defensible_both"):
        return "hold_two_vote_owner_gate"
    return "single_source_candidate"


def _root_conflict_held_superseded(case):
    """Pre-fix: one side was silently chosen (or majority-voted) for the contested occurrence."""
    return "silently_choose_or_majority"


# --- S4. N-ROOT-03: prose root ⟺ structured root field (display consistency, bidirectional) ------
def _display_consistency_corrected(case):
    """A root claimed in learner prose must exist in the structured field, and a populated field must
    surface in prose — one fact rendered twice. Either-direction mismatch flags; both-present (agree)
    or both-absent conforms. Translit prose is a display artifact, never auto-promoted to the field."""
    prose = bool(case.get("morphline_translit_root"))
    field = bool(case.get("structured_root_field"))
    if prose != field:
        return "flag_display_inconsistency"
    return "conform"


def _display_consistency_superseded(case):
    """Pre-fix: prose/field divergence was not cross-checked; the row was accepted as conforming."""
    return "conform"


# --- S7. N-PED-01: every rendered segment carries a non-empty gloss_contribution ----------------
def _segment_gloss_corrected(case):
    """A segment with a non-empty gloss conforms; a role-ambiguous suffix_pronoun with an empty gloss
    stays pending (never guessed); a role-determinate closed-class suffix with an empty gloss is filled
    from the deterministic suffix table (ه/ها/هم/كم/نا/ي/ك)."""
    if case.get("gloss_contribution"):
        return "conform_has_gloss"
    if "ambiguous" in case.get("role", ""):
        return "hold_pending_role"
    return "fill_from_suffix_table"


def _segment_gloss_superseded(case):
    """Pre-fix (N-PED-01 seam leak): the seam checked rows not segments and accepted an empty gloss."""
    return "accept_empty_gloss"


# --- S8. orthographic match symmetry: normalize both sides; block an ambiguous fold --------------
def _match_symmetry_corrected(case):
    """Fold BOTH sides with the same normalizer. If the keys agree it is a match — UNLESS both raw
    words were already normalized yet still collide (distinct raw words sharing a key), which is an
    ambiguous fold and must BLOCK (لا/إلا). Disjoint keys stay no_match."""
    cand = case.get("candidate_side", "")
    corp = case.get("corpus_side", "")
    if _ortho_fold(cand) == _ortho_fold(corp):
        if case.get("candidate_normalized") and case.get("corpus_normalized") and cand != corp:
            return "block_ambiguous_fold"
        return "match_after_symmetric_normalization"
    return "no_match"


def _match_symmetry_superseded(case):
    """Pre-fix: one side normalized, the other raw → the folded/unfolded keys differed → spurious
    no_match (50 Window-1 candidates lost)."""
    return "no_match"


# ================================================================================================
# NAHW @2.3 — addressing convention + surface↔gloss binding
# ================================================================================================

# --- N5. basmala-aware loc authority: apply the +4 band on ayah-1 of basmala-carrying surahs ------
def _basmala_addr_corrected(case):
    """Surah 1/9 carry no offset (raw authority governs). On a basmala-carrying surah's ayah-1 the
    basmala occupies words 1–4, so a word-index above the raw count but within authority+4 is valid
    (certify with offset); an index within the raw count needs no offset; an index beyond authority+4
    is a genuine overflow and is held."""
    if not case.get("surah_has_basmala"):
        return "certify_no_offset"
    raw = case.get("raw_ayah_wordcount", 0)
    loc = case.get("loc_word_index", 0)
    if loc <= raw:
        return "certify_no_offset"
    if case.get("within_authority_plus4"):
        return "certify_address_basmala_offset"
    return "hold_out_of_range"


def _basmala_addr_superseded(case):
    """Pre-fix: the basmala-blind ayah_wordcount authority held every ayah-1 overflow as out-of-range."""
    return "hold_out_of_range"


# --- N6. surface↔gloss single-wordlist binding: surface & gloss share ONE index convention -------
def _surface_gloss_bind_corrected(case):
    """Surface and gloss must be resolved from one word list under one indexing convention; if their
    basmala index parity disagrees the gloss is describing a neighbouring token (binding corruption)."""
    if case.get("surface_index_basmala") == case.get("gloss_index_basmala"):
        return "publish_row"
    return "flag_binding_corruption"


def _surface_gloss_bind_superseded(case):
    """Pre-fix: each field was individually well-formed so the row published despite the index skew."""
    return "publish_row"


# ------------------------------------------------------------------------------------------------
CORRECTED = {
    "surface_join": _surface_join_corrected,
    "closed_class": _closed_class_corrected,
    "root_conflict_held": _root_conflict_held_corrected,
    "display_consistency": _display_consistency_corrected,
    "basmala_addr": _basmala_addr_corrected,
    "surface_gloss_bind": _surface_gloss_bind_corrected,
    "segment_gloss": _segment_gloss_corrected,
    "match_symmetry": _match_symmetry_corrected,
}

SUPERSEDED = {
    "surface_join": _surface_join_superseded,
    "closed_class": _closed_class_superseded,
    "root_conflict_held": _root_conflict_held_superseded,
    "display_consistency": _display_consistency_superseded,
    "basmala_addr": _basmala_addr_superseded,
    "surface_gloss_bind": _surface_gloss_bind_superseded,
    "segment_gloss": _segment_gloss_superseded,
    "match_symmetry": _match_symmetry_superseded,
}
