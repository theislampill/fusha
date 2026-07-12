#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Segment-completeness gates for rich-hover morphosyntax records (QAMUS-RICH-SEG-001).

The existing morphosyntax validator proves a segmentation is INTERNALLY CONSISTENT
(segments concatenate to the surface, align 1:1 with display rows, use allowed classes,
function segments carry a gloss). It does NOT prove the segmentation is COMPLETE. A
producer can declare `[فَ, لْيَتَنَافَسِ as STEM]` and stay internally consistent while the
STEM swallows the imperative lām لْ (a governor) and the imperfect prefix يَ (inflection).

This module adds seven completeness gates that reject internally-consistent but
pedagogically incomplete rows. Every gate FAILS CLOSED (a match is an error) and each is
red-first proven by `--self-test` against a malformed [FA, STEM] fixture for 83:26:5.

Gates:
  A governor_to_segment      — an analysis asserting imperative_lam government must show a
                               visible prefix_imperative_lam segment.
  B finite_imperfect         — an imperfect verb must account for its agreement prefix
                               (a verb_prefix segment) or carry an exact reviewable exception.
  C feature_to_display       — a parse-key/prose claim of a visible prefix/suffix/article/
                               pronoun/dual-plural/derivative must appear in segments[] or be
                               explicitly renderer-blocked.
  D stem_swallow             — a stem may not BEGIN with a known clitic/governor that the exact
                               analysis identifies separately (imperative/purpose lām, an
                               unambiguous imperfect prefix, resumption/conjunction fā/waw, the
                               definite article, a prefixed preposition).
  E exact_occurrence         — an exact source-addressed record may not fall back to generic
                               "as context requires" / "not separately asserted" bundles when
                               exact aspect/voice/mood/person/number/form are available.
  F explanation_truth        — prose claiming the hover "exposes the visible prefix/stem/suffix
                               pieces" is checked against the actually displayed roles.
  G definition_example_parity— flag a sense line that highlights derivational morphology while
                               the paired occurrence flattens functionally more important grammar.

Deterministic, stdlib-only, offline, repo-local. Reads no live Qamus data.

Usage:
  python tools/validate_segment_completeness.py --self-test
  python tools/validate_segment_completeness.py qamus/examples/rich_seg_83_26_5.sample.jsonl
  python tools/validate_segment_completeness.py --emit-fixture qamus/examples/rich_seg_83_26_5.sample.jsonl
"""
import argparse
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Exact 83:26:5 surface, built by concatenation so the surface can never drift.
# فَ (resumption) + لْ (imperative lām) + يَ (imperfect 3ms prefix) + تَنَافَسِ (Form VI stem)
# Built from explicit codepoints so the fully-vocalized surface can never drift on hand-edit.
FA_SEG = "فَ"                                        # فَ
LAM_SEG = "لْ"                                       # لْ  (lām + sukūn)
YA_SEG = "يَ"                                        # يَ
STEM_SEG = "تَنَافَسِ"  # تَنَافَسِ (Form VI stem)
SURFACE_83_26_5 = FA_SEG + LAM_SEG + YA_SEG + STEM_SEG         # فَلْيَتَنَافَسِ
STEM_SWALLOW = LAM_SEG + YA_SEG + STEM_SEG                     # لْيَتَنَافَسِ  (the swallowing STEM)
ROOT_NFS = "ن ف س"                             # ن ف س
WAZN_VI = "يتفاعل"              # يتفاعل (bare wazn label)

# Arabic diacritic strip, for clitic detection on stem surfaces.
_DIAC = re.compile(r"[ً-ْٰـۖ-ۭ]")
def _bare(s):
    return _DIAC.sub("", s or "").replace("ٱ", "ا")

# Unambiguous imperfect agreement prefixes (bare). تـ is deliberately EXCLUDED: it collides
# with the Form V/VI derivational tāʾ (تَفَعَّل / تَفَاعَل), so flagging a تـ-initial stem would
# false-positive on a correctly separated Form VI stem such as تَنَافَس. يـ/نـ/أـ do not begin
# any derivational verb pattern, so they are safe to flag as swallowed inflection.
_IMPERFECT_PREFIX_BARE = ("ي", "ن", "أ", "إ", "ا")  # ي ن أ إ ا(hamza-carrier)

_FALLBACK_MARKERS = (
    "as context requires",
    "not separately asserted",
    "context not separately asserted",
    "perfect/imperative active/passive",
    "indicative/subjunctive/jussive",
    "mood context",
)

_SUFFIX_ROLES = {
    "object_pronoun", "possessive_pronoun", "subject_pronoun", "case_ending",
    "dual_suffix", "plural_suffix",
}


# ---------------------------------------------------------------------------
def _segments(rec):
    return rec.get("segments") or []

def _roles(rec):
    return [s.get("role") for s in _segments(rec) if isinstance(s, dict)]

def _sarf(rec):
    return rec.get("sarf") or {}

def _nahw(rec):
    return rec.get("nahw") or {}

def _parse_key(rec):
    return rec.get("parse_key") or {}

def _renderer_blocked(rec):
    return rec.get("decision_state") in {"blocked", "renderer_requirement"} or bool(rec.get("blocker"))


def gate_a_governor_to_segment(rec):
    """A: analysis asserting imperative_lam government must show a prefix_imperative_lam segment."""
    errs = []
    nahw = _nahw(rec)
    pk = _parse_key(rec)
    summary = (pk.get("summary") or "").lower()
    key = (pk.get("key") or "")
    indicates = (
        nahw.get("governed_by") == "imperative_lam"
        or (nahw.get("governor") or "") == LAM_SEG
        or "imperative_lam" in str(nahw.get("function") or "")
        or "IMPV" in key
        or "imperative lam" in summary
        or "imperative lām" in summary
        or "prefix_imperative_lam" in _roles(rec)
    )
    if indicates and "prefix_imperative_lam" not in _roles(rec):
        errs.append(("GATE-A", "governor_to_segment: analysis asserts imperative-lām government "
                              "but no visible prefix_imperative_lam segment is present"))
    return errs


def gate_b_finite_imperfect(rec):
    """B: an imperfect verb must account for its agreement prefix (verb_prefix) or a stated exception."""
    errs = []
    sarf = _sarf(rec)
    is_imperfect = (sarf.get("pos") == "fiʿl" or rec.get("pos") == "verb") and sarf.get("tense_aspect") == "imperfect"
    if not is_imperfect:
        return errs
    if "verb_prefix" in _roles(rec):
        return errs
    if rec.get("imperfect_prefix_exception"):  # exact, reviewable exception hook
        return errs
    errs.append(("GATE-B", "finite_imperfect: imperfect verb has no verb_prefix segment for its "
                          "agreement prefix and no exact reviewable exception"))
    return errs


def gate_c_feature_to_display(rec):
    """C: a claimed visible affix must be represented in segments[] or be renderer-blocked."""
    errs = []
    if _renderer_blocked(rec):
        return errs
    pk = _parse_key(rec)
    text = " ".join([
        (pk.get("key") or ""),
        (pk.get("summary") or ""),
        (rec.get("learner_explanation") or ""),
    ] + [str(c.get("label", "")) + " " + str(c.get("value", "")) for c in (pk.get("components") or [])]).lower()
    roles = set(_roles(rec))
    has_suffix = bool(roles & _SUFFIX_ROLES)
    checks = [
        ("suffix", has_suffix, "suffix"),
        ("article", "definite_article" in roles, "definite article"),
        ("pronoun", bool(roles & {"object_pronoun", "possessive_pronoun", "subject_pronoun"}), "pronoun"),
        ("dual", "dual_suffix" in roles, "dual ending"),
        ("derivative", "derivative_prefix" in roles or "verb_prefix" in roles, "derivative/inflection prefix"),
    ]
    for needle, present, human in checks:
        if needle in text and not present:
            errs.append(("GATE-C", "feature_to_display: prose/parse-key claims a visible %s "
                                  "but no matching segment is present" % human))
    # An imperfect verb whose prose claims a "prefix" must show a verb_prefix segment.
    if "prefix" in text and rec.get("pos") == "verb" and _sarf(rec).get("tense_aspect") == "imperfect" \
            and "verb_prefix" not in roles:
        errs.append(("GATE-C", "feature_to_display: prose claims a visible verb prefix but no "
                              "verb_prefix segment is present"))
    return errs


def gate_d_stem_swallow(rec):
    """D: a stem may not BEGIN with a known clitic/governor the exact analysis identifies separately."""
    errs = []
    pos = rec.get("pos")
    for seg in _segments(rec):
        if not isinstance(seg, dict) or seg.get("role") != "stem":
            continue
        surf = seg.get("surface") or ""
        bare = _bare(surf)
        # 1. imperative/purpose lām welded to the front of a verb stem (raw diacritic check: لْ / لِ).
        if pos == "verb" and (surf.startswith(LAM_SEG) or surf.startswith("لِ")):
            errs.append(("GATE-D", "stem_swallow: verb stem %r begins with a lām governor "
                                  "(imperative/purpose lām) that must be a separate segment" % surf))
            continue
        # 2. unambiguous imperfect agreement prefix welded to the stem front (ي/ن/أ), when the row is imperfect.
        if pos == "verb" and _sarf(rec).get("tense_aspect") == "imperfect" \
                and bare[:1] in _IMPERFECT_PREFIX_BARE:
            errs.append(("GATE-D", "stem_swallow: imperfect verb stem %r begins with an agreement "
                                  "prefix that must be a separate verb_prefix segment" % surf))
            continue
        # 3. resumption/conjunction fā or waw welded to a stem front.
        if surf.startswith(FA_SEG) or surf.startswith("وَ"):
            errs.append(("GATE-D", "stem_swallow: stem %r begins with a resumption/conjunction "
                                  "particle that must be a separate segment" % surf))
            continue
        # 4. definite article welded to a nominal stem front.
        if bare.startswith("ال"):
            errs.append(("GATE-D", "stem_swallow: stem %r begins with the definite article ٱل "
                                  "that must be a separate segment" % surf))
    return errs


def gate_e_exact_occurrence(rec):
    """E: exact source-addressed records may not fall back to generic bundles when exact facts exist."""
    errs = []
    # exact-address record?
    if not re.match(r"^\d{1,3}:\d{1,3}:\d{1,3}$", str(rec.get("loc") or "")):
        return errs
    pk = _parse_key(rec)
    haystacks = [pk.get("summary") or "", rec.get("learner_explanation") or "",
                 _sarf(rec).get("verb_form") or "", _sarf(rec).get("voice") or "",
                 _sarf(rec).get("mood") or ""]
    blob = " ".join(str(h) for h in haystacks).lower()
    for marker in _FALLBACK_MARKERS:
        if marker in blob:
            errs.append(("GATE-E", "exact_occurrence: exact-address record uses the generic fallback "
                                  "%r instead of the available exact grammar" % marker))
            break
    # a finite imperfect verb whose exact mood is unasserted is itself a fallback leak.
    sarf = _sarf(rec)
    if rec.get("pos") == "verb" and sarf.get("tense_aspect") == "imperfect" \
            and sarf.get("mood") in (None, "", "unknown", "null", "not_applicable"):
        errs.append(("GATE-E", "exact_occurrence: imperfect verb leaves mood unasserted at an exact "
                              "address where indicative/subjunctive/jussive is determinable"))
    return errs


def gate_f_explanation_truth(rec):
    """F: 'exposes the visible prefix/stem/suffix pieces' prose must match displayed roles."""
    errs = []
    lower = (rec.get("learner_explanation") or "").lower()
    if not (("expose" in lower or "exposes" in lower) and ("prefix" in lower or "suffix" in lower)):
        return errs
    roles = set(_roles(rec))
    if "suffix" in lower and not (roles & _SUFFIX_ROLES):
        errs.append(("GATE-F", "explanation_truth: explanation claims it exposes a visible suffix "
                              "but no suffix/pronoun/case segment is displayed"))
    if "prefix" in lower and rec.get("pos") == "verb" and _sarf(rec).get("tense_aspect") == "imperfect" \
            and "verb_prefix" not in roles:
        errs.append(("GATE-F", "explanation_truth: explanation claims it exposes the visible verb "
                              "prefix but no verb_prefix segment is displayed"))
    return errs


def gate_g_definition_example_parity(rec, companion=None):
    """G: sense highlights derivational morphology while the occurrence flattens more important grammar."""
    errs = []
    if not companion:
        return errs
    sense_exposes = bool(companion.get("exposes_derivation")) or any(
        isinstance(s, dict) and s.get("role") in {"derivative_prefix", "verb_prefix"}
        for s in (companion.get("segments") or [])
    )
    # occurrence flattens if it is a finite/derived verb but shows a single stem swallowing
    # inflection/government (no verb_prefix and no imperative_lam breakout) though the surface carries them.
    occ_roles = set(_roles(rec))
    occ_flattens = (
        rec.get("pos") == "verb"
        and "verb_prefix" not in occ_roles
        and "prefix_imperative_lam" not in occ_roles
        and any(isinstance(s, dict) and s.get("role") == "stem"
                and (s.get("surface") or "").startswith((LAM_SEG, "لِ"))
                for s in _segments(rec))
    )
    if sense_exposes and occ_flattens:
        errs.append(("GATE-G", "definition_example_parity: the sense line highlights derivational "
                              "morphology, but this occurrence flattens the imperative lām / imperfect "
                              "prefix into an undifferentiated stem"))
    return errs


ALL_GATES = ["GATE-A", "GATE-B", "GATE-C", "GATE-D", "GATE-E", "GATE-F", "GATE-G"]


def run_gates(rec, companion=None):
    """Run every gate. Returns a list of (code, message). Empty == complete."""
    out = []
    out += gate_a_governor_to_segment(rec)
    out += gate_b_finite_imperfect(rec)
    out += gate_c_feature_to_display(rec)
    out += gate_d_stem_swallow(rec)
    out += gate_e_exact_occurrence(rec)
    out += gate_f_explanation_truth(rec)
    out += gate_g_definition_example_parity(rec, companion=companion)
    return out


# ---------------------------------------------------------------------------
# Canonical records (single source of truth; reused by the red fixture test).
def build_correct_record():
    """The corrected, complete 83:26:5 exemplar (candidate; Fable + owner verify scripture)."""
    return {
        "loc": "83:26:5",
        "wbw_loc": "wbw:83:26:5",
        "surface": SURFACE_83_26_5,
        "key": SURFACE_83_26_5,
        "gloss": "so let him compete",
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "decision_state": "rich_candidate",
        "lemma": "تَنَافَسَ",  # تَنَافَسَ
        "root": ROOT_NFS,
        "pos": "verb",
        "sarf": {
            "pos": "fiʿl",
            "root": ROOT_NFS,
            "pattern": WAZN_VI,
            "verb_form": "VI",
            "voice": "active",
            "tense_aspect": "imperfect",
            "mood": "jussive",
            "person": "3",
            "number": "singular",
            "gender": "masculine",
            "noun_number": "not_applicable",
            "definiteness": "not_applicable",
            "case": "not_applicable",
            "derivative_type": "not_applicable",
        },
        "nahw": {
            "function": "fa_plus_imperative_lam_jussive_verb",
            "iʿrab_role": "jussive_verb_governed_by_imperative_lam",
            "governor": LAM_SEG,
            "governed_by": "imperative_lam",
            "pp_attachment": None,
            "idafa_relation": None,
            "pronoun_referent": None,
            "clause_relation": "imperative_clause",
            "reasoning_summary": ("The fāʾ links the clause, the imperative lām commands and drives the "
                                  "imperfect verb into the jussive, and the يـ marks the third masculine "
                                  "singular subject; the Form VI stem gives the reciprocal compete/strive."),
        },
        "morphology": {
            "verb_form": "VI",
            "voice": "active",
            "aspect": "imperfect",
            "mood": "jussive",
            "person": "3",
            "number": "singular",
            "gender": "masculine",
        },
        "segments": [
            {"role": "prefix_resumption_fa", "surface": FA_SEG, "gloss_contribution": "so/then"},
            {"role": "prefix_imperative_lam", "surface": LAM_SEG, "gloss_contribution": "let"},
            {"role": "verb_prefix", "surface": YA_SEG, "gloss_contribution": "imperfect third-person marker",
             "person": "3", "number": "singular", "gender": "masculine"},
            {"role": "stem", "surface": STEM_SEG, "gloss_contribution": "compete/strive"},
        ],
        "parse_key": {
            "key": "REM+IMPV+V:VI:IMPF:ACT:JUSS:3MS",
            "summary": ("Resumption fāʾ, then imperative lām governing a jussive Form VI imperfect active "
                        "verb, third masculine singular."),
            "components": [
                {"label": "REM", "value": "so/then", "note": None},
                {"label": "IMPV", "value": "let (imperative lām)", "note": "governs the jussive"},
                {"label": "PFX", "value": "imperfect 3ms marker", "note": None},
                {"label": "V", "value": "Form VI imperfect active jussive", "note": "reciprocal compete/strive"},
            ],
        },
        "display": {
            "palette": "qamus-grammar-v1",
            "segments": [
                {"segment_index": 0, "role": "prefix_resumption_fa", "class": "qg-result-fa", "label": "REM"},
                {"segment_index": 1, "role": "prefix_imperative_lam", "class": "qg-lam", "label": "IMPV"},
                {"segment_index": 2, "role": "verb_prefix", "class": "qg-verb-prefix", "label": "PFX"},
                {"segment_index": 3, "role": "stem", "class": "qg-verb-stem", "label": "STEM"},
            ],
        },
        "syntax": {
            "role": "jussive_verb",
            "governor": None,
            "head": None,
            "dependency": "imperative_lam",
            "phrase_type": "VS",
            "linked_locs": [],
        },
        "hover_contract": {
            "must_surface": ["so/then", "let", "compete/strive"],
            "must_not_surface": ["to compete as a bare infinitive", "one undifferentiated stem",
                                 "as context requires"],
            "reason": ("The resumption fāʾ, the imperative lām, and the imperfect prefix are visible "
                       "pieces and must not be swallowed by the stem."),
        },
        "learner_explanation": ("The fāʾ contributes so/then, the imperative lām contributes let and forces "
                                "the jussive, the يـ marks the third masculine singular subject, and the "
                                "Form VI stem contributes compete or strive with one another."),
        "blocker": None,
        "evidence": {
            "labels": ["tafsir-center:analyze_word:83:26:5:irab_sarf"],
            "gate": "two_vote_required",
            "reasoning": ("Form VI imperfect verb driven into the jussive by the imperative lām; resumption "
                          "fāʾ; third masculine singular though the explicit subject noun is plural."),
        },
        "public_boundary": {
            "public_gloss_src": "qamus",
            "public_gloss_kind": "authored",
            "public_gloss_lang": "en",
            "external_source_names_public": False,
        },
    }


def build_malformed_record():
    """The current public-equivalent [FA, STEM] payload that swallows لْ + يَ (the collapse)."""
    return {
        "loc": "83:26:5",
        "wbw_loc": "wbw:83:26:5",
        "surface": SURFACE_83_26_5,
        "key": SURFACE_83_26_5,
        "gloss": "strive",
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "decision_state": "rich_candidate",
        "root": ROOT_NFS,
        "pos": "verb",
        "sarf": {
            "pos": "fiʿl",
            "root": ROOT_NFS,
            "pattern": None,
            "verb_form": None,
            "voice": None,
            "tense_aspect": "imperfect",
            "mood": "unknown",
            "person": "3",
            "number": "singular",
            "gender": "masculine",
            "noun_number": "not_applicable",
            "definiteness": "not_applicable",
            "case": "not_applicable",
            "derivative_type": "not_applicable",
        },
        "nahw": {
            "function": "finite_verb",
            "iʿrab_role": "verbal_clause_role",
            "governor": LAM_SEG,
            "governed_by": "imperative_lam",
            "pp_attachment": None,
            "idafa_relation": None,
            "pronoun_referent": None,
            "clause_relation": None,
            "reasoning_summary": "Finite verb from root ن ف س; mood context not separately asserted.",
        },
        "segments": [
            {"role": "prefix_resumption_fa", "surface": FA_SEG, "gloss_contribution": "so/then"},
            {"role": "stem", "surface": STEM_SWALLOW, "gloss_contribution": "strive"},
        ],
        "parse_key": {
            "key": "REM+STEM",
            "summary": ("root ن ف س · finite verb form · perfect/imperative active/passive as context "
                        "requires · indicative/subjunctive/jussive mood context not separately asserted"),
            "components": [
                {"label": "REM", "value": "so/then", "note": None},
                {"label": "STEM", "value": "strive", "note": None},
            ],
        },
        "display": {
            "palette": "qamus-grammar-v1",
            "segments": [
                {"segment_index": 0, "role": "prefix_resumption_fa", "class": "qg-result-fa", "label": "REM"},
                {"segment_index": 1, "role": "stem", "class": "qg-verb-stem", "label": "STEM"},
            ],
        },
        "learner_explanation": ("The hover exposes the visible prefix, stem, and suffix pieces of the "
                                "token."),
        "blocker": None,
        "evidence": {
            "labels": ["tafsir-center:analyze_word:83:26:5:irab_sarf"],
            "gate": "two_vote_required",
            "reasoning": "Legacy flatten: fāʾ plus one undifferentiated stem.",
        },
        "public_boundary": {
            "public_gloss_src": "qamus",
            "public_gloss_kind": "authored",
            "public_gloss_lang": "en",
            "external_source_names_public": False,
        },
    }


def build_sense_companion():
    """Sense-one تَنَفَّسَ (Form V) that visibly teaches the derivational تَـ — parity partner for gate G."""
    return {
        "loc": "sense:nfs:1",
        "surface": "تَنَفَّسَ",  # تَنَفَّسَ
        "pos": "verb",
        "exposes_derivation": True,
        "segments": [
            {"role": "derivative_prefix", "surface": "تَ", "gloss_contribution": "reflexive tā (Form V)"},
            {"role": "stem", "surface": "نَفَّسَ", "gloss_contribution": "breathe"},
        ],
    }


# ===========================================================================
# LIVE RICH-HOVER WHITELIST ROW GATES  (defect classes C1..C5)
#
# Gates A..G above operate on the AUTHORING record shape (segments carry a
# `role`, plus `sarf`/`nahw`/`parse_key` blocks). The DEPLOYED rich-hover
# whitelist uses a leaner RUNTIME row shape: each segment carries a display
# `class` (qg-*), a `label`, a `role`, a `surface` and a `sarf_note`; the row
# carries a `morphline`, a `token_contribution_gloss` and a
# `learner_explanation`. The five defect classes catalogued by the segment-
# completeness audit are defined over THAT runtime shape, so they are
# implemented here as a second, self-contained classifier `classify_live_row`.
# Both shapes share this one module, so a single --self-test proves the whole
# gate red-first. Runtime rows have no `sarf`/`parse_key`, so gates A..G stay
# inert on them, and authoring records have no `morphline`, so C1..C5 stay
# inert on those -- the two layers never cross-fire.
#
# Every class FAILS CLOSED (a match is a rejection). Deterministic, stdlib-only,
# offline; reads no live Qamus data (the whitelist path is a CLI argument).
#
#   C1 stem_swallow      a verb STEM surface begins with an imperfect agreement
#                        prefix (unambiguous ي/ن, or the ambiguous ت/أ/إ only on
#                        an undifferentiated whole-token plural swallow) or a
#                        proclitic (ل/ف/و/ب/ك/س) that is NOT a root radical and is
#                        NOT already carried by a preceding prefix-sibling segment.
#   C2 whole_token_root  a single whole-token nominal/derived segment (است/مست/
#                        مـ/تـ, >=5 letters) whose root is left UNASSERTED and which
#                        is not a clean derivational participle/adjective (its
#                        leading mīm/tāʾ is inseparable pattern morphology, not a
#                        folded clitic -> no separable affix -> not a swallow).
#   C3 misclassified_fn  a function segment (qg-negation / qg-particle /
#                        qg-ma-particle) whose surface is actually a finite verb
#                        (imperfect prefix + real second radical, or a plural
#                        و-ا / و-ن ending) with a real lexical root.
#   C4 fallback_leak     morphline/learner prose falls back to a generic bundle
#                        ("as context requires" / "not separately asserted" /
#                        "exposes the visible ...").
#   C5 suffix_swallow    the morphline asserts an attached +OBJ/+POSS/+SUBJ
#                        pronoun (or the surface ends in an enclitic pronoun the
#                        gloss renders) yet no pronoun/suffix segment exists.
#
# Tightening (proven by the two negative fixtures in --self-test):
#   * C1 preceding-prefix-sibling check + the ambiguous ت/أ/إ carve-out let the
#     correctly-split 102:3:3 تَعْلَمُونَ (STEM+SUBJ) PASS while 2:91:3 تقتلون
#     (whole-token) and 83:26:5 فَلْيَتَنَافَسِ (welded lām) are REJECTED.
#   * C2 clitic-presence / clean-participle guard + transliterated-root
#     recognition let 4:144:17 مُّبِينًا (Form IV participle, zero clitics) PASS
#     while 9:107:3 مَسْجِدًا (root uncertified) is REJECTED.
# ===========================================================================

# Diacritics to strip for leading-letter / enclitic detection on runtime rows.
_LIVE_DIAC = set()
for _c in list(range(0x064B, 0x0659)) + [0x0670, 0x0640] + list(range(0x06D6, 0x06EE)):
    _LIVE_DIAC.add(chr(_c))

def _live_bare(s):
    """Strip Qurʾanic diacritics/annotation marks and fold alif-wasla for detection."""
    return "".join(ch for ch in (s or "") if ch not in _LIVE_DIAC).replace("ٱ", "ا")

_HARAKAT_ONLY = set(chr(c) for c in range(0x064B, 0x0653))
def _deharaka(s):
    return "".join(ch for ch in (s or "") if ch not in _HARAKAT_ONLY)

_VERB_STEM_CLASSES = {"qg-verb-stem"}
_PREFIX_CLASSES = {"qg-verb-prefix", "qg-conjunction", "qg-lam", "qg-result-fa",
                   "qg-preposition", "qg-future-particle", "qg-derivative-prefix",
                   "qg-emphasis", "qg-particle"}
_PRON_SUFFIX_CLASSES = {"qg-object-pronoun", "qg-subject-pronoun", "qg-possessive-pronoun",
                        "qg-pronoun", "qg-plural-suffix", "qg-dual-suffix",
                        "qg-referential-pronoun"}
_FUNC_ONLY_CLASSES = {"qg-negation", "qg-particle", "qg-ma-particle"}

_IMPF_UNAMBIG = set("ين")       # yāʾ (3rd) and nūn (1st pl) never begin a bare stem
_IMPF_AMBIG = set("تأإاآ")      # tāʾ/hamza/alif collide with Form II..X and imperative augments
_PROCLITIC = set("لفوبكس")      # lām, fāʾ, wāw, bāʾ, kāf, sīn
_BAD_SECOND = set("اٰوي")       # a weak/long second letter is not a finite-verb signature
_PLURAL_VERB_SUFFIX = ("ون", "وا", "ين")
_IMPF_STRICT = set("يتن")

_FALLBACK_PHRASES = ("as context requires", "not separately asserted", "exposes the visible")

_ENCLITIC = ["هما", "كما", "هم", "هن", "كم", "كن", "ها", "هو", "نا", "ه", "ك", "ي"]
_OBJ_POSS_HINTS = ("+obj", "+poss", "attached object", "attached possessive",
                   "object pronoun", "possessive pronoun", "attached pronoun")
_GLOSS_PRON = (" him", " them", " us", " your", " his", " its", " her", "you")
_PERF_SUBJ_SUFFIX = ("نا", "تم", "تن", "وا", "تما")
_VOC_DEM_MARKERS = ("vocative", "demonstrative", "deictic", "addressee", "addressed")
_PARTICLE_STOPLIST = {"افلا", "انما", "اينما", "اولا", "الا", "اما", "اءنك", "اءن", "اذا", "اذ"}

_SUBJ_OBJ_MARKER = re.compile(r"\d[mf][spd]\s+(?:subject|object)")
_ROOT_ARABIC_RE = re.compile(r"root\s+([؀-ۿ\s]+?)(?:·|\||\-| - |$)")
_ROOT_LATIN_RE = re.compile(r"root\s+[a-z](?:[\s\-][a-z]){1,}")
_ROOT_UNCERT = ("root not certified", "root not asserted", "no lexical root",
                "not certified in frozen", "root uncertified")


def _live_segments(rec):
    return rec.get("segments") or []

def _live_root_radicals(morphline):
    """Extract Arabic root radicals asserted as 'root ن ف س ...' -> ['ن','ف','س']; else None."""
    mm = _ROOT_ARABIC_RE.search(morphline or "")
    if mm:
        rad = [x for x in mm.group(1).split() if x]
        if rad:
            return rad
    return None

def _live_root_asserted(morphline):
    """True if the morphline asserts a root (Arabic radicals OR a transliterated b-y-n form)."""
    low = (morphline or "").lower()
    if any(u in low for u in _ROOT_UNCERT):
        return False
    if _live_root_radicals(morphline or ""):
        return True
    if _ROOT_LATIN_RE.search(low):
        return True
    return False

def _is_verb_stem(s):
    if not isinstance(s, dict):
        return False
    if s.get("class") in _VERB_STEM_CLASSES:
        return True
    if s.get("role") == "verb_stem":
        return True
    if s.get("label") in ("STEM", "V") and "verb" in (s.get("role") or "").lower():
        return True
    return False

def _is_vocative_ya(raw):
    d = _deharaka(raw)
    return bool(d) and d[0] == "ي" and len(d) > 1 and d[1] in ("ٰ", "ا")


def _c1_stem_swallow(rec):
    errs = []
    segs = _live_segments(rec)
    m = rec.get("morphline") or ""
    for i, s in enumerate(segs):
        if not _is_verb_stem(s):
            continue
        surf = s.get("surface") or ""
        bare = _live_bare(surf)
        if not bare:
            continue
        note = s.get("sarf_note") or ""
        is_impf = ("imperfect" in (m + " " + note).lower() or "مضارع" in m or "مضارع" in note)
        rad = _live_root_radicals(m)
        first = bare[0]
        prev = segs[i - 1] if i > 0 else None
        prev_prefix = isinstance(prev, dict) and prev.get("class") in _PREFIX_CLASSES
        # preceding-prefix-sibling check: a split-out prefix carries the swallowed clitic ONLY
        # when its own surface actually ends with that leading letter (this is stricter than a
        # bare "any preceding prefix" test, so a lām welded behind an unrelated fāʾ is caught).
        prev_covers = prev_prefix and _live_bare(prev.get("surface")).endswith(first)
        # C1a: unambiguous imperfect agreement prefix (yāʾ/nūn) folded into an imperfect stem
        # with no split prefix sibling. Gated on `is_impf` so a yāʾ/nūn first radical never fires.
        if is_impf and first in _IMPF_UNAMBIG and not prev_prefix and (rad is None or rad[0] != first):
            errs.append(("C1", "stem_swallow: imperfect verb stem %r folds its agreement prefix %r into the STEM" % (surf, first)))
            continue
        # C1b: a proclitic (imperative/purpose lām, resumption fāʾ/wāw, bi/ka/sa) welded to the
        # stem front with NO split prefix sibling, root-aware (leading clitic is not a radical).
        # The sīn+tāʾ carve-out keeps the Form VIII/X است-/ـْتَ infix (e.g. نَسْتَعِينُ) from being
        # misread as a future-particle sīn.
        if (first in _PROCLITIC and not prev_prefix and rad is not None and first not in rad
                and not (first == "س" and bare[1:2] == "ت")):
            errs.append(("C1", "stem_swallow: verb stem %r begins with proclitic %r folded into the STEM" % (surf, first)))
            continue
        # C1c: an imperative/purpose/emphatic lām welded to the stem front BEHIND an unrelated
        # prefix (fāʾ/wāw) that does not carry it — the 83:26:5 فَ+لْيَ… shape a bare preceding-
        # prefix test would miss. Restricted to the lām (the documented governor) so Form VIII/X
        # sīn/tāʾ infixes behind an agreement prefix never trip it.
        if first == "ل" and prev_prefix and not prev_covers and rad is not None and "ل" not in rad:
            errs.append(("C1", "stem_swallow: verb stem %r welds an imperative/purpose lām behind an "
                              "unrelated prefix instead of splitting it out" % surf))
            continue
        # C1d: ambiguous tāʾ/hamza/alif prefix — a defect ONLY on an undifferentiated whole-token
        # plural swallow, so a correctly split STEM+SUBJ imperfect (102:3:3) passes.
        if first in _IMPF_AMBIG and is_impf and rad and rad[0] != first:
            ends_plural = any(bare.endswith(sfx) for sfx in _PLURAL_VERB_SUFFIX)
            has_subject_seg = any(
                isinstance(sg, dict) and (sg.get("class") in _PRON_SUFFIX_CLASSES
                                          or "subject" in (sg.get("role") or "").lower())
                for sg in segs)
            whole = len(segs) == 1 or bare == _live_bare(rec.get("surface"))
            if ends_plural and not has_subject_seg and whole:
                errs.append(("C1", "stem_swallow: whole-token imperfect verb %r folds its agreement "
                                  "prefix and plural subject ending into one undifferentiated STEM" % surf))
    return errs


_C2_WHOLE_LABELS = {"TOK", "TOKEN", "SEG", "N"}
_C2_WHOLE_ROLES = {"whole_token", "token", "token_host", "noun_stem"}
_C2_WHOLE_CLASSES = {"qg-segment", "qg-noun", "qg-noun-stem", "qg-adjective"}

def _c2_whole_token_root(rec):
    errs = []
    segs = _live_segments(rec)
    if len(segs) != 1:
        return errs
    s = segs[0]
    if not isinstance(s, dict):
        return errs
    cls = s.get("class"); role = (s.get("role") or "").lower(); lab = s.get("label") or ""
    note = (s.get("sarf_note") or "").lower()
    m = rec.get("morphline") or ""
    bare = _live_bare(s.get("surface"))
    if not bare or len(bare) < 5:
        return errs
    wholeish = (lab in _C2_WHOLE_LABELS or role in _C2_WHOLE_ROLES or cls in _C2_WHOLE_CLASSES)
    if not wholeish:
        return errs
    # clitic-presence / clean-participle guard: a derivational participle or adjective has NO
    # separable affix (its leading mīm/tāʾ is inseparable pattern morphology) -> not a swallow.
    if (cls == "qg-adjective" or "participle" in m.lower() or "participle" in note
            or "adjective" in m.lower()):
        return errs
    if (cls == "qg-proper-noun" or "proper" in role or "proper name" in note
            or "divine name" in note):
        return errs
    # only a genuinely UNASSERTED root is a defect (Arabic OR transliterated root counts as asserted).
    if _live_root_asserted(m):
        return errs
    derived = False
    if bare.startswith("است") or bare.startswith("مست"):
        derived = True
    elif bare[0] == "م" and not bare.startswith(("من", "ما", "مه")):
        derived = True
    elif bare[0] == "ت":
        derived = True
    if derived:
        errs.append(("C2", "whole_token_root: single derived whole-token %r leaves its root unasserted "
                          "(no separable segment, no certified root)" % (s.get("surface"))))
    return errs


def _c3_misclassified_function(rec):
    errs = []
    segs = _live_segments(rec)
    m = rec.get("morphline") or ""
    learner = rec.get("learner_explanation") or ""
    low_all = (m + " " + learner).lower()
    raw_surface = rec.get("surface") or ""
    for s in segs:
        if not isinstance(s, dict):
            continue
        cls = s.get("class"); note = (s.get("sarf_note") or "").lower()
        func = cls in _FUNC_ONLY_CLASSES or "function only no root" in note
        if not func:
            continue
        if _is_vocative_ya(raw_surface) or any(v in low_all for v in _VOC_DEM_MARKERS):
            continue
        bare = _live_bare(s.get("surface"))
        if not bare or bare in _PARTICLE_STOPLIST:
            continue
        impf_verb = (bare[0] in _IMPF_STRICT and len(bare) >= 5 and bare[1] not in _BAD_SECOND)
        perf_verb = (bare.endswith("وا") or bare.endswith("ون")) and len(bare) >= 5
        if impf_verb or perf_verb:
            errs.append(("C3", "misclassified_function: %s segment %r is actually a finite verb form" % (cls, s.get("surface"))))
    return errs


def _c4_fallback_leak(rec):
    m = rec.get("morphline") or ""
    learner = rec.get("learner_explanation") or ""
    blob = (m + " " + learner).lower()
    for ph in _FALLBACK_PHRASES:
        if ph in blob:
            return [("C4", "fallback_leak: morphline/learner text uses the generic fallback %r" % ph)]
    return []


def _c5_suffix_swallow(rec):
    segs = _live_segments(rec)
    m = rec.get("morphline") or ""
    learner = rec.get("learner_explanation") or ""
    gloss = rec.get("token_contribution_gloss") or ""
    low_all = (m + " " + learner).lower()
    has_pron_seg = any(isinstance(sg, dict) and sg.get("class") in _PRON_SUFFIX_CLASSES for sg in segs)
    if has_pron_seg:
        return []
    if any(v in low_all for v in _VOC_DEM_MARKERS):
        return []
    surf = _live_bare(rec.get("surface"))
    end_enc = None
    for enc in _ENCLITIC:
        if surf.endswith(enc) and len(surf) >= len(enc) + 2:
            end_enc = enc
            break
    mlow = m.lower()
    obj_poss = any(h in mlow for h in _OBJ_POSS_HINTS) or bool(_SUBJ_OBJ_MARKER.search(mlow))
    perf_subj = ("perfect" in mlow and "+subj" in mlow
                 and any(surf.endswith(x) for x in _PERF_SUBJ_SUFFIX))
    gloss_pron = end_enc is not None and any(w in gloss.lower() for w in _GLOSS_PRON)
    if obj_poss or perf_subj or gloss_pron:
        tag = end_enc or ("+SUBJ" if perf_subj else "(morphline)")
        return [("C5", "suffix_swallow: attached pronoun/subject %r asserted but no pronoun/suffix "
                      "segment is present" % tag)]
    return []


LIVE_CLASSES = ["C1", "C2", "C3", "C4", "C5"]
_LIVE_CLASS_FNS = [_c1_stem_swallow, _c2_whole_token_root, _c3_misclassified_function,
                   _c4_fallback_leak, _c5_suffix_swallow]

def classify_live_row(rec):
    """Run every live-row completeness class. Returns a list of (code, message). Empty == clean."""
    out = []
    for fn in _LIVE_CLASS_FNS:
        out += fn(rec)
    return out


# ---------------------------------------------------------------------------
def _read_jsonl(path):
    for line_no, line in enumerate(io.open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        yield line_no, json.loads(line)


def validate_file(path):
    n = 0
    errors = []
    for line_no, rec in _read_jsonl(path):
        n += 1
        for code, msg in run_gates(rec):
            errors.append("line %d: %s %s" % (line_no, code, msg))
    return n, errors


def emit_fixture(path):
    rec = build_correct_record()
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    print("wrote corrected 83:26:5 exemplar -> %s" % path)
    return 0


# ---------------------------------------------------------------------------
# Live-row fixtures: the 9 confirmed positives (each must be REJECTED by its
# class) + the 2 known false alarms (each must PASS). Each positive carries a
# `defective` shape (the actual live row) and a `corrected` shape (the complete
# segmentation) so --self-test proves the class red-first and green-after.
def _live_fixtures():
    return [
        # ---- C1 stem_swallow ----
        {"loc": "83:26:5", "expect": "C1",
         "defective": {
             "loc": "83:26:5", "surface": "فَلْيَتَنَافَسِ", "token_contribution_gloss": "strive",
             "morphline": "root ن ف س · finite verb form · imperfect active · finite",
             "learner_explanation": "finite verb from root ن ف س",
             "segments": [
                 {"class": "qg-result-fa", "label": "FA", "role": "prefix_result_fa", "surface": "فَ", "sarf_note": "function proclitic; no lexical root"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "لْيَتَنَافَسِ", "sarf_note": "finite verb stem from root ن ف س"}]},
         "corrected": {
             "loc": "83:26:5", "surface": "فَلْيَتَنَافَسِ", "token_contribution_gloss": "so let him compete",
             "morphline": "root ن ف س · Form VI imperfect active · jussive · 3ms · governed by imperative lām",
             "learner_explanation": "the fāʾ, imperative lām, and imperfect prefix are visible before the stem",
             "segments": [
                 {"class": "qg-result-fa", "label": "FA", "role": "prefix_result_fa", "surface": "فَ", "sarf_note": "resumption fāʾ"},
                 {"class": "qg-lam", "label": "IMPV", "role": "prefix_imperative_lam", "surface": "لْ", "sarf_note": "imperative lām governor"},
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "يَ", "sarf_note": "imperfect 3ms prefix; root ن ف س"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "تَنَافَسِ", "sarf_note": "Form VI stem from root ن ف س"}]}},
        {"loc": "2:91:3", "expect": "C1",
         "defective": {
             "loc": "2:91:3", "surface": "تقتلون", "token_contribution_gloss": "you kill",
             "morphline": "root ق ت ل · imperfect active verb 2mp · base قَتَلَ",
             "learner_explanation": "the verb you all kill",
             "segments": [{"class": "qg-verb-stem", "label": "V", "role": "verb_stem", "surface": "تقتلون", "sarf_note": "imperfect active 2mp from root ق ت ل; base قَتَلَ"}]},
         "corrected": {
             "loc": "2:91:3", "surface": "تقتلون", "token_contribution_gloss": "you all kill",
             "morphline": "root ق ت ل · imperfect active · 2mp",
             "learner_explanation": "prefix, stem, and plural subject are all visible",
             "segments": [
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "تَ", "sarf_note": "2nd person imperfect prefix; root ق ت ل"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "قْتُلُ", "sarf_note": "imperfect stem from root ق ت ل"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_2mp", "surface": "ونَ", "sarf_note": "masculine plural subject marker"}]}},
        # ---- C2 whole_token_root ----
        {"loc": "9:107:3", "expect": "C2",
         "defective": {
             "loc": "9:107:3", "surface": "مَسْجِدًۭا", "token_contribution_gloss": "Mosque",
             "morphline": "noun/proper-name token · root not certified in frozen row",
             "learner_explanation": "contributes 'Mosque' in this example.",
             "segments": [{"class": "qg-noun-stem", "label": "N", "role": "noun_stem", "surface": "مَسْجِدًۭا", "sarf_note": "noun/proper-name token · root not certified in frozen row"}]},
         "corrected": {
             "loc": "9:107:3", "surface": "مَسْجِدًۭا", "token_contribution_gloss": "a mosque",
             "morphline": "root س ج د · noun of place (مَفْعِل) · accusative indefinite",
             "learner_explanation": "place of prostration from root س ج د",
             "segments": [{"class": "qg-noun-stem", "label": "N", "role": "noun_stem", "surface": "مَسْجِدًۭا", "sarf_note": "noun of place from root س ج د"}]}},
        # ---- C3 misclassified_function ----
        {"loc": "24:4:13", "expect": "C3",
         "defective": {
             "loc": "24:4:13", "surface": "تَقْبَلُوا۟", "token_contribution_gloss": "do not accept",
             "morphline": "function only no root · NEG",
             "learner_explanation": "This word contributes 'do not accept'.",
             "segments": [{"class": "qg-negation", "label": "NEG", "role": "negation", "surface": "تَقْبَلُوا۟", "sarf_note": ""}]},
         "corrected": {
             "loc": "24:4:13", "surface": "تَقْبَلُوا۟", "token_contribution_gloss": "you accept",
             "morphline": "root ق ب ل · imperfect active · 2mp (jussive after negation)",
             "learner_explanation": "prefix, stem, and plural subject are visible",
             "segments": [
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "تَ", "sarf_note": "2nd person imperfect prefix; root ق ب ل"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "قْبَلُ", "sarf_note": "imperfect stem from root ق ب ل"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_2mp", "surface": "وا۟", "sarf_note": "masculine plural subject marker"}]}},
        {"loc": "40:72:4", "expect": "C3",
         "defective": {
             "loc": "40:72:4", "surface": "يُسْجَرُونَ", "token_contribution_gloss": "to set on fire",
             "morphline": "function particle; no lexical root",
             "learner_explanation": "This token contributes 'to set on fire'.",
             "segments": [{"class": "qg-particle", "label": "P", "role": "particle_or_preposition", "surface": "يُسْجَرُونَ", "sarf_note": "function particle; no lexical root"}]},
         "corrected": {
             "loc": "40:72:4", "surface": "يُسْجَرُونَ", "token_contribution_gloss": "they are set ablaze",
             "morphline": "root س ج ر · imperfect passive · 3mp",
             "learner_explanation": "prefix, stem, and plural subject are visible",
             "segments": [
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "يُ", "sarf_note": "3rd person imperfect passive prefix; root س ج ر"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "سْجَرُ", "sarf_note": "imperfect passive stem from root س ج ر"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_3mp", "surface": "ونَ", "sarf_note": "masculine plural subject marker"}]}},
        # ---- C4 fallback_leak ----
        {"loc": "6:84:20", "expect": "C4",
         "defective": {
             "loc": "6:84:20", "surface": "نَجْزِى", "token_contribution_gloss": "We reward",
             "morphline": "root ج ز ي · finite verb form · imperfect active/passive as context requires · 1st person plural · indicative/subjunctive/jussive mood context not separately asserted",
             "learner_explanation": "the hover exposes the visible prefix/stem/suffix pieces and the person/number/mood facts",
             "segments": [
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "نَ", "sarf_note": "1st person plural imperfect prefix; root ج ز ي"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "جْزِى", "sarf_note": "finite verb stem from root ج ز ي"}]},
         "corrected": {
             "loc": "6:84:20", "surface": "نَجْزِى", "token_contribution_gloss": "We reward",
             "morphline": "root ج ز ي · imperfect active · 1cp · indicative",
             "learner_explanation": "the نَ marks the first person plural subject; the stem gives reward",
             "segments": [
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "نَ", "sarf_note": "1st person plural imperfect prefix; root ج ز ي"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "جْزِى", "sarf_note": "imperfect stem from root ج ز ي"}]}},
        {"loc": "2:40:3", "expect": "C4",
         "defective": {
             "loc": "2:40:3", "surface": "ٱذْكُرُوا۟", "token_contribution_gloss": "remember",
             "morphline": "root ذ ك ر · finite verb form · perfect/imperative active/passive as context requires · 3mp · indicative/subjunctive/jussive mood context not separately asserted",
             "learner_explanation": "the hover exposes the visible prefix/stem/suffix pieces and the person/number/mood facts",
             "segments": [
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "ٱذْكُرُ", "sarf_note": "finite verb stem from root ذ ك ر"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_3mp", "surface": "وا۟", "sarf_note": "visible 3mp subject ending"}]},
         "corrected": {
             "loc": "2:40:3", "surface": "ٱذْكُرُوا۟", "token_contribution_gloss": "remember",
             "morphline": "root ذ ك ر · imperative active · 2mp",
             "learner_explanation": "the imperative stem gives remember and the plural ending marks you all",
             "segments": [
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "ٱذْكُرُ", "sarf_note": "imperative stem from root ذ ك ر"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_2mp", "surface": "وا۟", "sarf_note": "visible 2mp subject ending"}]}},
        # ---- C5 suffix_swallow ----
        {"loc": "7:43:33", "expect": "C5",
         "defective": {
             "loc": "7:43:33", "surface": "أُورِثْتُمُوهَا", "token_contribution_gloss": "you inherited it",
             "morphline": "root و ر ث · passive verb + 2mp subject + 3fs object",
             "learner_explanation": "the ending marks you all and it",
             "segments": [{"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "أُورِثْتُمُوهَا", "sarf_note": "passive finite verb from root و ر ث with subject/object"}]},
         "corrected": {
             "loc": "7:43:33", "surface": "أُورِثْتُمُوهَا", "token_contribution_gloss": "you all inherited it",
             "morphline": "root و ر ث · passive perfect · 2mp subject · 3fs object",
             "learner_explanation": "the subject ending marks you all and the object pronoun marks it",
             "segments": [
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "أُورِثْتُ", "sarf_note": "passive perfect stem from root و ر ث"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_2mp", "surface": "تُمُو", "sarf_note": "2mp subject connector"},
                 {"class": "qg-object-pronoun", "label": "OBJ", "role": "object_pronoun_3fs", "surface": "هَا", "sarf_note": "3fs attached object pronoun"}]}},
        {"loc": "2:235:17", "expect": "C5",
         "defective": {
             "loc": "2:235:17", "surface": "سَتَذْكُرُونَهُنَّ", "token_contribution_gloss": "will mention them",
             "morphline": "noun/proper-name token · root not certified in frozen row",
             "learner_explanation": "contributes 'will mention them' in this example.",
             "segments": [{"class": "qg-noun-stem", "label": "N", "role": "noun_stem", "surface": "سَتَذْكُرُونَهُنَّ", "sarf_note": "noun/proper-name token · root not certified in frozen row"}]},
         "corrected": {
             "loc": "2:235:17", "surface": "سَتَذْكُرُونَهُنَّ", "token_contribution_gloss": "you will mention them",
             "morphline": "root ذ ك ر · imperfect active · 2mp · future سَـ · 3fp object",
             "learner_explanation": "the future sīn, the prefix, the plural subject, and the object pronoun are all visible",
             "segments": [
                 {"class": "qg-future-particle", "label": "FUT", "role": "future_particle", "surface": "سَ", "sarf_note": "future particle sīn"},
                 {"class": "qg-verb-prefix", "label": "PFX", "role": "verb_prefix", "surface": "تَ", "sarf_note": "2nd person imperfect prefix; root ذ ك ر"},
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "ذْكُرُ", "sarf_note": "imperfect stem from root ذ ك ر"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_suffix_2mp", "surface": "ونَ", "sarf_note": "masculine plural subject marker"},
                 {"class": "qg-object-pronoun", "label": "OBJ", "role": "object_pronoun_3fp", "surface": "هُنَّ", "sarf_note": "3fp attached object pronoun"}]}},
        # ---- negatives: known false alarms; each MUST pass (no class fires) ----
        {"loc": "102:3:3", "expect": None, "negative": True,
         "row": {
             "loc": "102:3:3", "surface": "تَعْلَمُونَ", "token_contribution_gloss": "you know",
             "morphline": "root ع ل م · Form I imperfect active · +SUBJ 2mp · future supplied by سَوْفَ",
             "learner_explanation": "تَعْلَمُ is the verb stem, ونَ marks the plural subject, and سَوْفَ supplies the future",
             "segments": [
                 {"class": "qg-verb-stem", "label": "STEM", "role": "verb_stem", "surface": "تَعْلَمُ", "sarf_note": "sarf: Form I imperfect stem from ع ل م"},
                 {"class": "qg-subject-pronoun", "label": "SUBJ", "role": "subject_marker_2mp", "surface": "ونَ", "sarf_note": "sarf: masculine plural subject marker"}]}},
        {"loc": "4:144:17", "expect": None, "negative": True,
         "row": {
             "loc": "4:144:17", "surface": "مُّبِينًا", "token_contribution_gloss": "clear",
             "morphline": "adjective/active participle · root b-y-n",
             "learner_explanation": "The Arabic adjective describes the authority as clear or manifest.",
             "segments": [{"class": "qg-adjective", "label": "TOK", "role": "whole_token", "surface": "مُّبِينًا", "sarf_note": "sarf: adjective/active participle · root b-y-n"}]}},
    ]


def _self_test_live():
    """Red-first proof for the live-row classes C1..C5 against the 9 positives + 2 negatives."""
    failures = []
    fired_classes = set()
    for fx in _live_fixtures():
        loc = fx["loc"]
        if fx.get("negative"):
            hits = classify_live_row(fx["row"])
            if hits:
                failures.append("negative %s must PASS all live classes but fired %s"
                                % (loc, [c for c, _ in hits]))
            continue
        want = fx["expect"]
        red = {c for c, _ in classify_live_row(fx["defective"])}
        if want not in red:
            failures.append("positive %s defective row must be REJECTED by %s but fired only %s"
                            % (loc, want, sorted(red)))
        else:
            fired_classes.add(want)
        green = {c for c, _ in classify_live_row(fx["corrected"])}
        if want in green:
            failures.append("positive %s corrected row must PASS %s but it still fired" % (loc, want))
    for cls in LIVE_CLASSES:
        if cls not in fired_classes:
            failures.append("no fixture exercised class %s red-first" % cls)
    return failures


def scan_whitelist(path):
    """Read-only classifier scan over a live rich-hover whitelist JSONL. Returns per-class counts."""
    counts = {c: 0 for c in LIVE_CLASSES}
    distinct = set()
    rows = 0
    for _line_no, rec in _read_jsonl(path):
        rows += 1
        hit_classes = {c for c, _ in classify_live_row(rec)}
        for c in hit_classes:
            counts[c] += 1
        if hit_classes:
            distinct.add(rec.get("loc"))
    return {"rows": rows, "counts": counts,
            "total_class_hits": sum(counts.values()),
            "distinct_rows_flagged": len(distinct)}


def _self_test():
    failures = []

    correct = build_correct_record()
    sense = build_sense_companion()
    # 1. GREEN: the corrected record must pass ALL gates (even with the parity companion).
    green = run_gates(correct, companion=sense)
    if green:
        failures.append("corrected record must pass all gates, got: %s" % green)

    # 2. RED: the malformed [FA, STEM] record must trip the relevant gates.
    malformed = build_malformed_record()
    red = run_gates(malformed, companion=sense)
    fired = {code for code, _ in red}
    # Every gate is relevant to this malform and must fire (fail-closed proof).
    for code in ALL_GATES:
        if code not in fired:
            failures.append("malformed [FA,STEM] fixture must trip %s but it did not fire" % code)

    # 3. Surface integrity of the exemplar (guards the hand-built Arabic constants).
    if "".join(s["surface"] for s in correct["segments"]) != SURFACE_83_26_5:
        failures.append("corrected segments do not concatenate to the surface")
    if "".join(s["surface"] for s in malformed["segments"]) != SURFACE_83_26_5:
        failures.append("malformed segments do not concatenate to the surface")

    # 4. LIVE-ROW classes C1..C5: red-first on the 9 positives, green on the 2 false alarms.
    failures += _self_test_live()

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_segment_completeness self-test: corrected 83:26:5 passes all 7 gates; "
              "malformed [FA,STEM] trips every gate %s; live-row classes %s each reject their "
              "confirmed positive and pass the corrected shape; 102:3:3 and 4:144:17 pass clean"
              % (",".join(ALL_GATES), ",".join(LIVE_CLASSES)))
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Segment-completeness gates for rich-hover records.")
    ap.add_argument("metadata", nargs="?", help="path to a rich-hover morphosyntax JSONL")
    ap.add_argument("--self-test", action="store_true", help="run the red-first self-test and exit")
    ap.add_argument("--emit-fixture", dest="emit", help="write the corrected 83:26:5 exemplar JSONL")
    ap.add_argument("--scan-whitelist", dest="scan",
                    help="read-only C1..C5 classifier scan over a live rich-hover whitelist JSONL")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.scan:
        rep = scan_whitelist(a.scan)
        print("scanned %d rich-hover whitelist row(s) for completeness defects" % rep["rows"])
        for c in LIVE_CLASSES:
            print("  %s  count=%d" % (c, rep["counts"][c]))
        print("total_class_hits=%d  distinct_rows_flagged=%d"
              % (rep["total_class_hits"], rep["distinct_rows_flagged"]))
        print(json.dumps(rep, ensure_ascii=False, sort_keys=True))
        return 0
    if a.emit:
        return emit_fixture(a.emit)
    if not a.metadata:
        ap.error("metadata JSONL path required, or pass --self-test / --emit-fixture")
    n, errors = validate_file(a.metadata)
    print("checked %d rich-hover record(s) for segment completeness" % n)
    if errors:
        print("FAIL:")
        for e in errors[:80]:
            print("  - " + e)
        return 1
    print("PASS - segment-completeness gates OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
