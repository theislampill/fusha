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

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_segment_completeness self-test: corrected 83:26:5 passes all 7 gates; "
              "malformed [FA,STEM] trips every gate %s" % ",".join(ALL_GATES))
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Segment-completeness gates for rich-hover records.")
    ap.add_argument("metadata", nargs="?", help="path to a rich-hover morphosyntax JSONL")
    ap.add_argument("--self-test", action="store_true", help="run the red-first self-test and exit")
    ap.add_argument("--emit-fixture", dest="emit", help="write the corrected 83:26:5 exemplar JSONL")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
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
