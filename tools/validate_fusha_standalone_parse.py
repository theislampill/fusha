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
        if qg and "".join(seg.get("surface", "") for seg in qg) != surf:
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
            headline = ((tok.get("hover_preview") or {}).get("token_contribution_gloss") or "").lower()
            if "pronoun" not in headline and not any(word in headline for word in ("you", "them", "him", "her", "it", "us", "me")):
                errors.append("%s: hover headline hides attached pronoun contribution" % surf)
        if any(seg.get("class") == "qg-preposition" for seg in qg):
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
