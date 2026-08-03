#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the standalone Fusha parser MVP output.

This is the Mode C/preview gate: it checks source-clean JSON, qg class safety,
segment concatenation, clitic preservation, ambiguity preservation, and no fake
source certainty. It is intentionally stricter than a demo script because this
kernel feeds Qamus/RH-LIVE authoring later.
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402

SCHEMA = "fusha/standalone-parse@1"

PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}

ALLOWED_QG_CLASSES = {
    "qg-verb-prefix",
    "qg-verb",
    "qg-verb-stem",
    "qg-subject-pronoun",
    "qg-object-pronoun",
    "qg-possessive-pronoun",
    "qg-noun",
    "qg-noun-stem",
    "qg-adjective",
    "qg-dual-suffix",
    "qg-plural-suffix",
    "qg-derivative-prefix",
    "qg-proper-noun",
    "qg-pronoun",
    "qg-preposition",
    "qg-oath",
    "qg-comitative",
    "qg-particle",
    "qg-conjunction",
    "qg-negative",
    "qg-result",
    "qg-result-fa",
    "qg-lam",
    "qg-ma-particle",
    "qg-article",
    "qg-relative",
    "qg-vocative",
    "qg-exception",
    "qg-case",
    "qg-relation",
}

LEAK_RE = re.compile(
    r"(?:MCP|QAC|Tafsir|Quran\.com|Corpus|Tanzil|source[-_ ]?photo|/srv|C:\\|"
    r"process prose|external evidence|Ayat|i.?rab tafsir center)",
    re.I,
)

FIXTURES = [
    "إنما الأعمال بالنيات",
    "قال رسول الله",
    "من كان يؤمن بالله واليوم الآخر",
    "فسيكفيكهم",
    "بالكتاب",
    "وما",
    "لمّا",
    "إنما",
    "يستغفرون",
    "مستغفرين",
    "فأهلكناهم",
    "يسألك",
]


def _public_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"raw_input", "surface"}:
                continue
            yield from _public_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _public_strings(v)
    elif isinstance(obj, str):
        yield obj


def _segments_concat(token, key):
    for cand in token.get(key) or []:
        segs = cand.get("segments") if isinstance(cand, dict) else None
        if segs and "".join(s.get("surface", "") for s in segs) != token.get("surface"):
            return False
    return True


def _retained_segments_ordered_subset(qg, surface):
    """True when each qg segment's surface appears in `surface` in left-to-right,
    non-overlapping order (Train E I2). A stem_identity collision withholds the
    disputed stem but preserves the surrounding affix/clitic segments in place, so
    the retained pieces cannot concatenate back to the full surface -- they must
    still land at the right, non-reordered, non-overlapping positions."""
    pos = 0
    for seg in qg:
        piece = seg.get("surface", "")
        if not piece:
            continue
        idx = surface.find(piece, pos)
        if idx == -1:
            return False
        pos = idx + len(piece)
    return True


def validate_record(rec):
    errors = []
    if rec.get("schema") != SCHEMA:
        errors.append("schema must be %s" % SCHEMA)
    if rec.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append("public_boundary must be source-clean qamus/authored/en")
    sb = rec.get("source_boundary") or {}
    if sb.get("original_preserved") is not True or sb.get("external_text_copied") is not False:
        errors.append("source_boundary must preserve original and forbid copied external text")
    if rec.get("input_mode") != "arbitrary_typing":
        errors.append("standalone MVP validator expects arbitrary_typing mode")
    if rec.get("raw_input") is None or rec.get("raw_input") == "":
        errors.append("raw_input required")
    if (rec.get("summary") or {}).get("live_writes") != 0:
        errors.append("live_writes must be 0")

    for s in _public_strings(rec):
        if LEAK_RE.search(s):
            errors.append("public string leaks provenance/process text: %r" % s[:80])
            break

    for tok in rec.get("tokens") or []:
        surf = tok.get("surface") or ""
        if tok.get("loc") is not None:
            errors.append("%s: arbitrary token carries source loc" % surf)
        if tok.get("confidence_gate") in {"certified", "auto_safe", "source_certified"}:
            errors.append("%s: arbitrary token claims source certainty" % surf)
        if not _segments_concat(tok, "segment_candidates"):
            errors.append("%s: segment candidate does not concatenate" % surf)
        qg = tok.get("qg_segments") or []
        collision = tok.get("collision") or {}
        # Train E I2: a collision-withheld token is not an ordinary complete
        # segmentation. Whole-token withholding (or a non-stem_identity scope)
        # projects no segments; stem_identity withholding retains the surrounding
        # affix/clitic segments in place while withholding the disputed stem, so
        # they can only be an ordered, non-overlapping SUBSET of the surface, never
        # a full concatenation. Ordinary (non-collision) tokens keep the original,
        # unweakened complete-concatenation check.
        if collision:
            if collision.get("scope") == "stem_identity":
                if not qg:
                    errors.append("%s: stem_identity collision withholding dropped all affix/clitic coverage" % surf)
                elif not _retained_segments_ordered_subset(qg, surf):
                    errors.append("%s: stem_identity collision retained segments are not an ordered subset of the surface" % surf)
            elif qg:
                errors.append("%s: collision withholding outside stem_identity scope must project no qg_segments" % surf)
            hover_gloss = (tok.get("hover_preview") or {}).get("token_contribution_gloss")
            if hover_gloss is not None:
                errors.append("%s: collision-withheld token must not carry a public token_contribution_gloss, got %r" % (surf, hover_gloss))
        elif qg and "".join(seg.get("surface", "") for seg in qg) != surf:
            errors.append("%s: qg_segments do not concatenate" % surf)
        for seg in qg:
            if seg.get("class") not in ALLOWED_QG_CLASSES:
                errors.append("%s: unsupported qg class %r" % (surf, seg.get("class")))
        if tok.get("selected_preview") and not qg:
            errors.append("%s: selected_preview without qg_segments" % surf)
        if N.bare(surf) in {"وما", "ما", "لما", "انما"}:
            if tok.get("confidence_gate") not in {"pending_context", "ambiguous", "likely_from_internal_pattern"}:
                errors.append("%s: function particle not context-gated" % surf)
        if N.bare(surf).startswith("ب") and len(N.bare(surf)) > 2:
            if qg and not any(seg.get("class") == "qg-preposition" for seg in qg):
                errors.append("%s: bāʾ-host token lacks preposition segment" % surf)
        roles = [seg.get("role") for seg in qg]
        if any(r in roles for r in ("object_pronoun", "possessive_pronoun")):
            if not any(seg.get("class") in {"qg-object-pronoun", "qg-possessive-pronoun", "qg-pronoun"} for seg in qg):
                errors.append("%s: pronoun role lacks pronoun qg class" % surf)
            if not collision:
                headline = ((tok.get("hover_preview") or {}).get("token_contribution_gloss") or "").lower()
                if "pronoun" not in headline and not any(word in headline for word in ("you", "them", "him", "her", "it", "us", "me")):
                    errors.append("%s: hover headline hides attached pronoun contribution" % surf)
        if any(seg.get("class") == "qg-preposition" for seg in qg) and not collision:
            headline = ((tok.get("hover_preview") or {}).get("token_contribution_gloss") or "").lower()
            if not any(word in headline for word in ("by", "with", "in", "for", "to", "preposition")):
                errors.append("%s: hover headline hides attached preposition contribution" % surf)
        for cand in tok.get("morphology_candidates") or []:
            if cand.get("root") and cand.get("evidence_class") not in {"seed_lexicon", "pinned_pattern"}:
                errors.append("%s: root lacks seed/pinned evidence" % surf)
        if len(tok.get("segment_candidates") or []) > 1 and tok.get("confidence_gate") == "certified":
            errors.append("%s: ambiguous segmentation marked certified" % surf)
    return errors


def _self_test():
    from tools import fusha_standalone_parse as parser  # noqa: E402

    failures = []
    for text in FIXTURES:
        rec = parser.parse_text(text)
        errs = validate_record(rec)
        if errs:
            failures.append("%s -> %s" % (text, errs[:3]))
    joined = parser.parse_text(" ".join(FIXTURES))
    if len(joined.get("tokens") or []) < len(FIXTURES):
        failures.append("joined fixtures should emit at least one token per fixture phrase")
    for surface in ("فسيكفيكهم", "فأهلكناهم", "يسألك", "بالكتاب", "وما", "مستغفرين"):
        rec = parser.parse_text(surface)
        tok = (rec.get("tokens") or [{}])[0]
        if not tok.get("qg_segments"):
            failures.append("%s should expose qg_segments" % surface)
    # Component regressions from RH-LIVE ANDONs: future particle, imperfect prefix, subject/object pieces,
    # derivative prefix, and plural suffix must not disappear behind a host-only preview.
    role_expect = {
        "فسيكفيكهم": {"prefix_resumption_fa", "future_particle", "verb_prefix", "verb_stem", "object_pronoun"},
        "فأهلكناهم": {"prefix_resumption_fa", "verb_stem", "subject_pronoun", "object_pronoun"},
        "يسألك": {"verb_prefix", "verb_stem", "object_pronoun"},
        "مستغفرين": {"derivative_prefix", "adjective_stem", "plural_suffix"},
        "بالكتاب": {"prefix_preposition", "definite_article", "stem"},
        "وما": {"prefix_conjunction", "stem"},
    }
    for surface, expected in role_expect.items():
        rec = parser.parse_text(surface)
        tok = (rec.get("tokens") or [{}])[0]
        roles = {seg.get("role") for seg in tok.get("qg_segments") or []}
        missing = expected - roles
        if missing:
            failures.append("%s qg roles missing %s; got %s" % (surface, sorted(missing), sorted(roles)))
    segs = [{"rank": 1, "segments": [{"role": "stem", "surface": "كتاب"}]}]
    morphs = [{"rank": 1, "pos": "noun", "evidence_class": "seed_lexicon", "segment_candidate_ref": 99}]
    selected, morph = parser._selected(segs, morphs)
    gate, collision = parser._gate("كتاب", segs, morph, [], morphs)
    if selected is not None or gate != "blocked" or not collision or collision.get("kind") != "dangling_segment_ref":
        failures.append("dangling segment_candidate_ref must block instead of selecting candidate 0")

    # Train E B1 (red-first): a source_risk_flags=[requires_nahw_function] candidate
    # whose scoped competitors span >=2 trichotomy classes must NOT be masked down to
    # pending_context by the source-risk cap; the stronger skeleton collision must win,
    # keep its collision descriptor, and still strip the withheld candidate's identity.
    b1_seg_cands = [{"rank": 1, "segments": [{"role": "stem", "surface": "بعض"}]}]
    b1_morph = {
        "rank": 1,
        "pos": "noun",
        "lemma": "بَعْض",
        "root": "ب ع ض",
        "gloss_hint": "some",
        "pattern": None,
        "evidence_class": "largelexicon_full",
        "segment_candidate_ref": 0,
        "features": {"source_risk_flags": ["requires_nahw_function"]},
        "collision": {
            "competing_entry_ids": ["e1", "e2"],
            "competitors": [
                {"entry_id": "e1", "pos": "noun", "root": "ب ع ض", "lemma": "بَعْض"},
                {"entry_id": "e2", "pos": "verb", "root": "ب ع ض", "lemma": "بَعَضَ"},
            ],
        },
    }
    b1_morphs = [b1_morph]
    b1_selected, b1_selected_morph = parser._selected(b1_seg_cands, b1_morphs)
    b1_gate, b1_collision = parser._gate(
        "بعض", b1_seg_cands, b1_selected_morph, [], b1_morphs, selected_seg=b1_selected,
    )
    if b1_gate != "lexical_collision_requires_context":
        failures.append(
            "B1: a source_risk_flags=[requires_nahw_function] candidate must not mask a "
            "stronger pos_trichotomy_conflict skeleton collision; got gate=%r" % b1_gate
        )
    if not b1_collision or b1_collision.get("kind") != "pos_trichotomy_conflict":
        failures.append("B1: the winning collision descriptor (pos_trichotomy_conflict) must be preserved")
    if (b1_morph.get("features") or {}).get("gate_cap_decided_by", {}).get("filter") != "source_requires_nahw_function":
        failures.append("B1: the masked source-risk cap must still carry typed decided_by evidence")
    b1_cand = dict(b1_morph)
    b1_cand["features"] = dict(b1_morph["features"])
    parser._strip_collision_identity(b1_cand, decided_by=b1_collision.get("kind") if b1_collision else None)
    if b1_cand.get("lemma") is not None or b1_cand.get("root") is not None or b1_cand.get("pos") is not None:
        failures.append("B1: identity must be stripped once the stronger skeleton collision wins")
    if b1_cand["features"].get("identity_withheld_decided_by", {}).get("filter") != "pos_trichotomy_conflict":
        failures.append("B1: identity withholding must carry typed decided_by evidence naming the winning filter")

    # Train E I4 (red-first): _selected can promote a richer multi-segment candidate
    # over the collapsed whole-token ref _skeleton_collision used to read directly.
    # Scope must be derived from the segment candidate _selected actually returned.
    i4_seg_cands = [
        {"rank": 1, "segments": [{"role": "stem", "surface": "بالكتب"}]},
        {"rank": 2, "segments": [
            {"role": "prefix_preposition", "surface": "ب"},
            {"role": "stem", "surface": "الكتب"},
        ]},
    ]
    i4_morph = {
        "rank": 1,
        "pos": "noun",
        "evidence_class": "largelexicon_sample",
        "segment_candidate_ref": 0,
        "features": {},
        "collision": {
            "competing_entry_ids": ["e1", "e2"],
            "competitors": [
                {"entry_id": "e1", "pos": "noun", "root": "ك ت ب", "lemma": "كِتَاب"},
                {"entry_id": "e2", "pos": "verb", "root": "ك ت ب", "lemma": "كَتَبَ"},
            ],
        },
    }
    i4_morphs = [i4_morph]
    i4_selected, i4_selected_morph = parser._selected(i4_seg_cands, i4_morphs)
    if len(i4_selected.get("segments") or []) < 2:
        failures.append("I4 setup: _selected must promote the richer multi-segment candidate")
    i4_skeleton = parser._skeleton_collision("بالكتب", i4_seg_cands, i4_selected_morph, selected_seg=i4_selected)
    if not i4_skeleton or i4_skeleton.get("scope") != "stem_identity":
        failures.append(
            "I4: skeleton collision scope must come from the segment candidate _selected "
            "returned, not the collapsed morph.segment_candidate_ref; got scope=%r"
            % ((i4_skeleton or {}).get("scope"))
        )

    # Train E I2 (red-first): Mode C validate_record must be collision-aware.
    # stem_identity withholding retains an ordered, non-contiguous-with-full-surface
    # affix subset (never the ordinary full concatenation); whole-token/other-scope
    # withholding retains none; a collision token must never carry a public gloss.
    def _base_record(qg_segments, collision):
        return {
            "schema": SCHEMA,
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "source_boundary": {"original_preserved": True, "external_text_copied": False, "quran_text_altered": False},
            "input_mode": "arbitrary_typing",
            "raw_input": "بهم",
            "summary": {"live_writes": 0},
            "tokens": [{
                "surface": "بهم",
                "loc": None,
                "confidence_gate": "lexical_collision_requires_context",
                "segment_candidates": [],
                "morphology_candidates": [],
                "collision": collision,
                "qg_segments": qg_segments,
                "hover_preview": {"token_contribution_gloss": None},
            }],
        }

    stem_identity_ok = _base_record(
        [{"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition"}],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    stem_identity_ok_errs = validate_record(stem_identity_ok)
    if stem_identity_ok_errs:
        failures.append(
            "I2: a valid stem_identity collision retaining an in-order affix subset "
            "must not be flagged by validate_record: %s" % stem_identity_ok_errs
        )

    stem_identity_bad = _base_record(
        [{"role": "prefix_preposition", "surface": "زز", "class": "qg-preposition"}],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    if not validate_record(stem_identity_bad):
        failures.append("I2: a stem_identity retained segment absent from the surface must be flagged")

    stem_identity_empty = _base_record([], {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"})
    if not validate_record(stem_identity_empty):
        failures.append("I2: stem_identity collision withholding must not drop ALL affix/clitic coverage")

    whole_token_leak = _base_record(
        [{"role": "stem", "surface": "بهم", "class": "qg-noun-stem"}],
        {"kind": "unsafe_bare_match"},
    )
    if not validate_record(whole_token_leak):
        failures.append(
            "I2: a whole-token (non-stem_identity) collision must reject leftover qg_segments, "
            "even when they happen to fully concatenate the surface"
        )

    gloss_leak = _base_record(
        [{"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition"}],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    gloss_leak["tokens"][0]["hover_preview"]["token_contribution_gloss"] = "some gloss"
    if not validate_record(gloss_leak):
        failures.append("I2: a collision-withheld token carrying a public token_contribution_gloss must be flagged")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_fusha_standalone_parse self-test: fixtures parse; source-clean; qg-safe; clitics preserved")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate standalone Fusha parser JSON.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.path:
        ap.error("need path or --self-test")
    with open(args.path, encoding="utf-8") as fh:
        rec = json.load(fh)
    errs = validate_record(rec)
    for e in errs:
        print("FAIL " + e)
    print("checked 1 record, %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
