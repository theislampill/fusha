#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate per-token morphosyntax metadata.

This gate protects the layer that explains how a written Quran token is composed:
segments, sarf/nahw tags, dependency roles, and the public-hover boundary. It is
offline and repo-local. It does not read or mutate live Qamus data.

Usage:
  python tools/validate_morphosyntax_token_metadata.py qamus/examples/morphosyntax_token.sample.jsonl
  python tools/validate_morphosyntax_token_metadata.py --self-test
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "qamus", "schemas", "morphosyntax-token.schema.json")

sys.path.insert(0, ROOT)
from tools.validate_linguistic_decisions import validate_schema  # noqa: E402

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK_RE = re.compile(
    r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
    r"tanzil|tafsir|mcp|informed_by)\b",
    re.I,
)

FUNCTION_BEARING_SEGMENTS = {
    "prefix_conjunction",
    "prefix_preposition",
    "prefix_oath",
    "prefix_comitative_waw",
    "prefix_resumption_fa",
    "prefix_coordination_fa",
    "prefix_result_fa",
    "prefix_supplemental_fa",
    "prefix_cause_fa",
    "prefix_interrogative_hamza",
    "prefix_equalization_hamza",
    "prefix_particle",
    "prefix_purpose_lam",
    "prefix_imperative_lam",
    "vocative_particle",
    "vocative_support",
    "attention_particle",
    "preventive_ma",
    "definite_article",
    "subject_pronoun",
    "object_pronoun",
    "possessive_pronoun",
    "relative_pronoun",
}

PRONOUN_SEGMENTS = {"subject_pronoun", "object_pronoun", "possessive_pronoun"}


def _load_schema():
    return json.load(io.open(SCHEMA_PATH, encoding="utf-8"))


def _read_jsonl(path):
    for line_no, line in enumerate(io.open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            yield line_no, json.loads(line)
        except Exception as exc:
            yield line_no, {"__json_error__": str(exc)}


def _bad_public_text(value):
    if isinstance(value, str) and LEAK_RE.search(value):
        return True
    if isinstance(value, list):
        return any(_bad_public_text(v) for v in value)
    return False


def _validate_invariants(record, seen):
    errors = []
    loc = record.get("loc") or "<missing loc>"

    if "__json_error__" in record:
        return ["bad JSON (%s)" % record["__json_error__"]]
    if loc in seen:
        errors.append("%s: duplicate loc" % loc)
    seen.add(loc)
    if not LOC_RE.match(str(loc)):
        errors.append("%s: bad loc" % loc)

    public_boundary = record.get("public_boundary") or {}
    if public_boundary.get("public_gloss_src") != "qamus":
        errors.append("%s: public_gloss_src must be qamus" % loc)
    if public_boundary.get("public_gloss_kind") != "authored":
        errors.append("%s: public_gloss_kind must be authored" % loc)
    if public_boundary.get("public_gloss_lang") != "en":
        errors.append("%s: public_gloss_lang must be en" % loc)
    if public_boundary.get("external_source_names_public") is not False:
        errors.append("%s: external_source_names_public must be false" % loc)

    hover_contract = record.get("hover_contract") or {}
    for key in ("must_surface", "must_not_surface", "reason"):
        if _bad_public_text(hover_contract.get(key)):
            errors.append("%s: hover_contract.%s leaks an internal source label" % (loc, key))

    must_surface = hover_contract.get("must_surface") or []
    segments = record.get("segments") or []
    if segments and not isinstance(segments, list):
        errors.append("%s: segments must be an array" % loc)
        return errors

    has_visible_article = any(
        isinstance(segment, dict)
        and segment.get("role") == "definite_article"
        and (segment.get("gloss_contribution") or "").strip().lower() == "the"
        for segment in segments
    )

    for index, segment in enumerate(segments):
        role = segment.get("role") if isinstance(segment, dict) else None
        contribution = (segment.get("gloss_contribution") or "").strip() if isinstance(segment, dict) else ""
        if role in FUNCTION_BEARING_SEGMENTS:
            if not contribution:
                errors.append("%s: segment[%d] %s needs gloss_contribution" % (loc, index, role))
            if not must_surface:
                errors.append("%s: function-bearing segment needs hover_contract.must_surface" % loc)
        if has_visible_article and role == "stem" and contribution.lower().startswith("the "):
            errors.append("%s: stem gloss duplicates definite_article contribution" % loc)
        if role in PRONOUN_SEGMENTS:
            if segment.get("person") in (None, "null"):
                errors.append("%s: segment[%d] %s needs person" % (loc, index, role))
            if segment.get("number") in (None, "null"):
                errors.append("%s: segment[%d] %s needs number" % (loc, index, role))

    return errors


def validate_file(path):
    schema = _load_schema()
    seen = set()
    n = 0
    errors = []
    for line_no, record in _read_jsonl(path):
        n += 1
        if "__json_error__" not in record:
            for err in validate_schema(record, schema):
                errors.append("line %d: SCHEMA %s" % (line_no, err))
        for err in _validate_invariants(record, seen):
            errors.append("line %d: INVARIANT %s" % (line_no, err))
    return n, errors


def _sample_records():
    return [
        {
            "loc": "22:68:2",
            "surface": "جَادَلُوكَ",
            "lemma": "جَادَلَ",
            "root": "ج د ل",
            "pos": "verb",
            "morphology": {
                "verb_form": "III",
                "voice": "active",
                "aspect": "perfect",
                "person": "3",
                "number": "plural",
                "gender": "masculine",
            },
            "segments": [
                {"role": "stem", "surface": "جَادَلُوا", "gloss_contribution": "they argued/disputed"},
                {
                    "role": "object_pronoun",
                    "surface": "كَ",
                    "gloss_contribution": "with you",
                    "person": "2",
                    "number": "singular",
                    "gender": "masculine",
                    "case": "accusative",
                },
            ],
            "syntax": {"role": "verb", "dependency": "object", "linked_locs": []},
            "hover_contract": {
                "must_surface": ["they", "you"],
                "must_not_surface": ["to argue"],
                "reason": "The object suffix must not vanish into a bare infinitive gloss.",
            },
            "evidence": {
                "labels": ["qamus:morphosyntax-contract:sample"],
                "gate": "two_vote_required",
                "reasoning": "Form III verb plus attached object pronoun.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "16:16:2",
            "surface": "وَبِٱلنَّجْمِ",
            "lemma": "نَجْم",
            "root": "ن ج م",
            "pos": "noun",
            "morphology": {"case": "genitive", "state": "definite", "number": "singular", "gender": "masculine"},
            "segments": [
                {"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
                {"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "by/through"},
                {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
                {"role": "stem", "surface": "نَّجْمِ", "gloss_contribution": "star"},
            ],
            "syntax": {
                "role": "majrur_host",
                "dependency": "jar_majrur",
                "phrase_type": "PP",
                "attachment_target_kind": "verb",
                "linked_locs": [],
            },
            "hover_contract": {
                "must_surface": ["and", "by", "star"],
                "must_not_surface": ["star only"],
                "reason": "The bāʾ relation and prefixed wāw must not be hidden behind a host-only hover.",
            },
            "evidence": {
                "labels": ["qamus:morphosyntax-contract:sample"],
                "gate": "two_vote_required",
                "reasoning": "Attached conjunction plus bāʾ creates a jar-majrur phrase.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "97:1:1",
            "surface": "إِنَّا",
            "lemma": "إِنَّ",
            "root": None,
            "pos": "accusative_particle",
            "segments": [
                {"role": "prefix_particle", "surface": "إِنَّ", "gloss_contribution": "indeed"},
                {
                    "role": "subject_pronoun",
                    "surface": "نَا",
                    "gloss_contribution": "We",
                    "person": "1",
                    "number": "plural",
                    "gender": "common",
                    "case": "accusative",
                },
            ],
            "syntax": {"role": "ism_inna", "dependency": "ism_inna", "linked_locs": []},
            "hover_contract": {
                "must_surface": ["indeed", "We"],
                "must_not_surface": ["indeed only"],
                "reason": "The attached pronoun must be visible with the particle contribution.",
            },
            "evidence": {
                "labels": ["qamus:morphosyntax-contract:sample"],
                "gate": "two_vote_required",
                "reasoning": "Accusative particle plus attached first-person plural pronoun.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "22:18:12",
            "surface": "ٱلْأَرْضِ",
            "lemma": "أَرْض",
            "root": "أ ر ض",
            "pos": "noun",
            "morphology": {"case": "genitive", "state": "definite", "number": "singular", "gender": "feminine"},
            "segments": [
                {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
                {"role": "stem", "surface": "أَرْضِ", "gloss_contribution": "earth, land"},
            ],
            "syntax": {"role": "majrur_host", "dependency": "jar_majrur", "linked_locs": []},
            "hover_contract": {
                "must_surface": ["the", "earth"],
                "must_not_surface": ["earth only"],
                "reason": "The definite article is part of the visible token and must not disappear.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:22:18:12:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "Definite genitive noun inside a prepositional phrase.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "22:18:13",
            "surface": "وَٱلشَّمْسُ",
            "lemma": "شَمْس",
            "root": "ش م س",
            "pos": "noun",
            "morphology": {"case": "nominative", "state": "definite", "number": "singular", "gender": "feminine"},
            "segments": [
                {"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
                {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
                {"role": "stem", "surface": "شَّمْسُ", "gloss_contribution": "sun"},
            ],
            "syntax": {"role": "coordinated", "dependency": "coordination", "linked_locs": ["22:18:12"]},
            "hover_contract": {
                "must_surface": ["and", "the", "sun"],
                "must_not_surface": ["sun only", "and + sun"],
                "reason": "The prefixed wāw and definite article must both remain visible.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:22:18:13:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "Coordinating wāw plus definite nominative noun.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "22:18:14",
            "surface": "وَٱلْقَمَرُ",
            "lemma": "قَمَر",
            "root": "ق م ر",
            "pos": "noun",
            "morphology": {"case": "nominative", "state": "definite", "number": "singular", "gender": "masculine"},
            "segments": [
                {"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
                {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
                {"role": "stem", "surface": "قَمَرُ", "gloss_contribution": "moon"},
            ],
            "syntax": {"role": "coordinated", "dependency": "coordination", "linked_locs": ["22:18:13"]},
            "hover_contract": {
                "must_surface": ["and", "the", "moon"],
                "must_not_surface": ["moon only"],
                "reason": "The prefixed wāw and definite article must both remain visible.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:22:18:14:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "Coordinating wāw plus definite nominative noun.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "2:13:12",
            "surface": "ٱلسُّفَهَاءُ",
            "lemma": "سَفِيه",
            "root": "س ف ه",
            "pos": "noun",
            "morphology": {
                "case": "nominative",
                "state": "definite",
                "number": "plural",
                "gender": "masculine",
                "rationality": "rational",
            },
            "segments": [
                {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
                {"role": "stem", "surface": "سُّفَهَاءُ", "gloss_contribution": "foolish ones"},
            ],
            "syntax": {"role": "subject", "dependency": "subject", "linked_locs": []},
            "hover_contract": {
                "must_surface": ["the", "foolish ones"],
                "must_not_surface": ["the + the foolish ones"],
                "reason": "The article is a separate segment; the stem gloss must not repeat it.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:2:13:12:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "Definite broken plural functioning as a subject.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "2:21:1",
            "surface": "يَا",
            "lemma": "يَا",
            "root": None,
            "pos": "vocative_particle",
            "segments": [{"role": "vocative_particle", "surface": "يَا", "gloss_contribution": "O"}],
            "syntax": {"role": "vocative", "dependency": "vocative", "linked_locs": ["2:21:2"]},
            "hover_contract": {
                "must_surface": ["O"],
                "must_not_surface": ["O you (who)"],
                "reason": "The standalone vocative particle contributes O; it should not swallow ayyuha.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:2:21:1:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "Vocative particle separated from the following addressee bridge in Qamus tokenization.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "2:21:2",
            "surface": "أَيُّهَا",
            "lemma": "أَيّ",
            "root": None,
            "pos": "particle",
            "segments": [
                {"role": "vocative_support", "surface": "أَيُّ", "gloss_contribution": "you who"},
                {"role": "attention_particle", "surface": "هَا", "gloss_contribution": "attention marker"},
            ],
            "syntax": {"role": "vocative_addressee", "dependency": "vocative_addressee", "linked_locs": ["2:21:1"]},
            "hover_contract": {
                "must_surface": ["you"],
                "must_not_surface": ["O you (who)"],
                "reason": "Ayyuha carries the addressee bridge and attention particle; ya carries O.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:2:21:1:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "MCP analyzes ya/ayyuha together; Qamus split tokens must preserve each piece separately.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
        {
            "loc": "26:139:2",
            "surface": "فَأَهْلَكْنَاهُمْ",
            "lemma": "أَهْلَكَ",
            "root": "ه ل ك",
            "pos": "verb",
            "morphology": {
                "verb_form": "IV",
                "voice": "active",
                "aspect": "perfect",
                "person": "1",
                "number": "plural",
                "gender": "common",
            },
            "segments": [
                {"role": "prefix_coordination_fa", "surface": "فَ", "gloss_contribution": "so/then"},
                {"role": "stem", "surface": "أَهْلَكْ", "gloss_contribution": "destroyed"},
                {
                    "role": "subject_pronoun",
                    "surface": "نَا",
                    "gloss_contribution": "We",
                    "person": "1",
                    "number": "plural",
                    "gender": "common",
                    "case": "nominative",
                },
                {
                    "role": "object_pronoun",
                    "surface": "هُمْ",
                    "gloss_contribution": "them",
                    "person": "3",
                    "number": "plural",
                    "gender": "masculine",
                    "case": "accusative",
                },
            ],
            "syntax": {"role": "verb", "dependency": "object", "linked_locs": []},
            "hover_contract": {
                "must_surface": ["We", "them"],
                "must_not_surface": ["stem recognized", "suffix/pronoun pending", "destroyed only"],
                "reason": "The subject and object pronouns must be visible before this can leave pending.",
            },
            "evidence": {
                "labels": ["tafsir-center:analyze_word:26:139:2:irab_sarf"],
                "gate": "two_vote_required",
                "reasoning": "Form IV perfect verb with first-person plural subject and third-person plural object suffix.",
            },
            "public_boundary": {
                "public_gloss_src": "qamus",
                "public_gloss_kind": "authored",
                "public_gloss_lang": "en",
                "external_source_names_public": False,
            },
        },
    ]


def _write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _self_test():
    with tempfile.TemporaryDirectory() as td:
        good = os.path.join(td, "good.jsonl")
        _write_jsonl(good, _sample_records())
        n, errors = validate_file(good)
        assert n == 10 and not errors, errors

        missing_lang = _sample_records()
        del missing_lang[0]["public_boundary"]["public_gloss_lang"]
        bad_lang = os.path.join(td, "missing-lang.jsonl")
        _write_jsonl(bad_lang, missing_lang)
        _, errors = validate_file(bad_lang)
        assert any("public_gloss_lang" in e for e in errors), errors

        lost_suffix = _sample_records()
        lost_suffix[0]["segments"][1]["gloss_contribution"] = None
        bad_suffix = os.path.join(td, "lost-suffix.jsonl")
        _write_jsonl(bad_suffix, lost_suffix)
        _, errors = validate_file(bad_suffix)
        assert any("object_pronoun needs gloss_contribution" in e for e in errors), errors

        no_must_surface = _sample_records()
        no_must_surface[1]["hover_contract"]["must_surface"] = []
        bad_contract = os.path.join(td, "no-contract.jsonl")
        _write_jsonl(bad_contract, no_must_surface)
        _, errors = validate_file(bad_contract)
        assert any("function-bearing segment needs hover_contract.must_surface" in e for e in errors), errors

        leak = _sample_records()
        leak[2]["hover_contract"]["reason"] = "copied from qac"
        bad_leak = os.path.join(td, "leak.jsonl")
        _write_jsonl(bad_leak, leak)
        _, errors = validate_file(bad_leak)
        assert any("leaks an internal source label" in e for e in errors), errors

        duplicate_article = _sample_records()
        duplicate_article[6]["segments"][1]["gloss_contribution"] = "the foolish ones"
        bad_article = os.path.join(td, "duplicate-article.jsonl")
        _write_jsonl(bad_article, duplicate_article)
        _, errors = validate_file(bad_article)
        assert any("stem gloss duplicates definite_article contribution" in e for e in errors), errors

    print("validate_morphosyntax_token_metadata self-test OK")


def main():
    parser = argparse.ArgumentParser(description="Validate morphosyntax token metadata JSONL.")
    parser.add_argument("metadata", nargs="?", help="path to morphosyntax metadata JSONL")
    parser.add_argument("--self-test", action="store_true", help="run inline self-test and exit")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        return
    if not args.metadata:
        parser.error("metadata JSONL path required, or pass --self-test")

    n, errors = validate_file(args.metadata)
    print("checked %d morphosyntax token record(s)" % n)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  - " + err)
        if len(errors) > 80:
            print("  ... %d more" % (len(errors) - 80))
        sys.exit(1)
    print("PASS — schema + public boundary + composition invariants OK")


if __name__ == "__main__":
    main()
