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
WHITESPACE_RE = re.compile(r"\s")

FUNCTION_BEARING_SEGMENTS = {
    "verb_prefix",
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
    "particle",
    "preposition",
    "conjunction_particle",
    "negative_particle",
    "exceptive_particle",
    "conditional_particle",
    "subordinating_particle",
    "interrogative_particle",
    "time_adverb",
    "resumption_particle",
    "result_particle",
    "accusative_particle",
    "relative_particle",
    "purpose_particle",
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

DISPLAY_CLASS_BY_ROLE = {
    "stem": "qg-verb",  # nominal stems are permitted to override via pos-aware renderers; validator checks scrubbed role only.
    "verb_prefix": "qg-verb",
    "prefix_conjunction": "qg-particle",
    "prefix_preposition": "qg-preposition",
    "prefix_oath": "qg-oath",
    "prefix_comitative_waw": "qg-comitative",
    "prefix_resumption_fa": "qg-particle",
    "prefix_coordination_fa": "qg-particle",
    "prefix_result_fa": "qg-result",
    "prefix_supplemental_fa": "qg-particle",
    "prefix_cause_fa": "qg-result",
    "prefix_interrogative_hamza": "qg-particle",
    "prefix_equalization_hamza": "qg-particle",
    "prefix_particle": "qg-particle",
    "prefix_purpose_lam": "qg-particle",
    "prefix_imperative_lam": "qg-particle",
    "particle": "qg-particle",
    "preposition": "qg-preposition",
    "conjunction_particle": "qg-particle",
    "negative_particle": "qg-negative",
    "exceptive_particle": "qg-exception",
    "conditional_particle": "qg-particle",
    "subordinating_particle": "qg-particle",
    "interrogative_particle": "qg-particle",
    "time_adverb": "qg-particle",
    "resumption_particle": "qg-particle",
    "result_particle": "qg-result",
    "accusative_particle": "qg-particle",
    "relative_particle": "qg-relative",
    "purpose_particle": "qg-particle",
    "vocative_particle": "qg-vocative",
    "vocative_support": "qg-vocative",
    "attention_particle": "qg-particle",
    "preventive_ma": "qg-particle",
    "definite_article": "qg-article",
    "subject_pronoun": "qg-pronoun",
    "object_pronoun": "qg-pronoun",
    "possessive_pronoun": "qg-pronoun",
    "relative_pronoun": "qg-relative",
    "case_ending": "qg-case",
    "other": "qg-unknown",
}

DISPLAY_LABEL_BY_ROLE = {
    "stem": "STEM",
    "verb_prefix": "PFX",
    "prefix_conjunction": "CONJ",
    "prefix_preposition": "P",
    "prefix_oath": "OATH",
    "prefix_comitative_waw": "COM",
    "prefix_resumption_fa": "REM",
    "prefix_coordination_fa": "CONJ",
    "prefix_result_fa": "RES",
    "prefix_supplemental_fa": "SUP",
    "prefix_cause_fa": "CAUS",
    "prefix_interrogative_hamza": "INTG",
    "prefix_equalization_hamza": "EQL",
    "prefix_particle": "PART",
    "prefix_purpose_lam": "PURP",
    "prefix_imperative_lam": "IMPV",
    "particle": "PART",
    "preposition": "P",
    "conjunction_particle": "CONJ",
    "negative_particle": "NEG",
    "exceptive_particle": "EXP",
    "conditional_particle": "COND",
    "subordinating_particle": "SUB",
    "interrogative_particle": "INTG",
    "time_adverb": "T",
    "resumption_particle": "REM",
    "result_particle": "RES",
    "accusative_particle": "ACC",
    "relative_particle": "REL",
    "purpose_particle": "PURP",
    "vocative_particle": "VOC",
    "vocative_support": "VOC",
    "attention_particle": "ATTN",
    "preventive_ma": "KAFF",
    "definite_article": "ART",
    "subject_pronoun": "PRON",
    "object_pronoun": "PRON",
    "possessive_pronoun": "PRON",
    "relative_pronoun": "REL",
    "case_ending": "CASE",
    "other": "UNK",
}


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


def _has_whitespace(value):
    return isinstance(value, str) and WHITESPACE_RE.search(value)


def _display_class_for(role, pos=None):
    if role == "stem" and pos in {"noun", "adjective", "participle", "masdar", "number"}:
        return "qg-noun"
    if role == "stem" and pos == "proper_noun":
        return "qg-proper-noun"
    return DISPLAY_CLASS_BY_ROLE.get(role, "qg-unknown")


def _display_for(record):
    """Build the canonical scrubbed display rows for sample fixtures."""
    pos = record.get("pos")
    rows = []
    for index, segment in enumerate(record.get("segments") or []):
        role = segment.get("role")
        rows.append({
            "segment_index": index,
            "role": role,
            "class": _display_class_for(role, pos),
            "label": DISPLAY_LABEL_BY_ROLE.get(role, "UNK"),
        })
    return {"palette": "qamus-grammar-v1", "segments": rows}


def _sarf_pos_for(pos):
    if pos == "verb":
        return "fiʿl"
    if pos in {
        "particle",
        "preposition",
        "conjunction",
        "subordinating_conjunction",
        "relative",
        "interrogative_particle",
        "equalization_particle",
        "negative_particle",
        "accusative_particle",
        "preventive_particle",
        "emphatic_particle",
        "resumption_particle",
        "result_particle",
        "supplemental_particle",
        "cause_particle",
        "vocative_particle",
        "prohibitive_particle",
        "exceptive_particle",
        "purpose_particle",
        "comitative_particle",
        "initial_letters",
    }:
        return "ḥarf"
    if pos == "unknown":
        return "unknown"
    return "ism"


def _rich_sarf_for(record):
    pos = record.get("pos")
    morphology = record.get("morphology") or {}
    is_verb = pos == "verb"
    is_nominal = _sarf_pos_for(pos) == "ism"
    return {
        "pos": _sarf_pos_for(pos),
        "root": record.get("root"),
        "pattern": None,
        "verb_form": morphology.get("verb_form") if is_verb else "not_applicable",
        "voice": morphology.get("voice") if is_verb else "not_applicable",
        "tense_aspect": morphology.get("aspect") if is_verb else "not_applicable",
        "mood": morphology.get("mood") or ("unknown" if is_verb else "not_applicable"),
        "person": morphology.get("person") if is_verb else "not_applicable",
        "number": morphology.get("number") or ("unknown" if is_verb else "not_applicable"),
        "gender": morphology.get("gender") or ("unknown" if is_verb else "not_applicable"),
        "noun_number": morphology.get("number") if is_nominal else "not_applicable",
        "definiteness": morphology.get("state") if is_nominal else "not_applicable",
        "case": morphology.get("case") if is_nominal else "not_applicable",
        "derivative_type": "proper_noun" if pos == "proper_noun" else ("common_noun" if is_nominal else "not_applicable"),
    }


def _rich_nahw_for(record, function, role=None, summary=None):
    syntax = record.get("syntax") or {}
    return {
        "function": function,
        "iʿrab_role": role or syntax.get("role"),
        "governor": syntax.get("governor"),
        "governed_by": syntax.get("head"),
        "pp_attachment": syntax.get("attachment_target_kind"),
        "idafa_relation": "idafa" if syntax.get("dependency") in {"idafa_head", "idafa_dependent"} else None,
        "pronoun_referent": None,
        "clause_relation": syntax.get("clause_kind"),
        "reasoning_summary": summary or "The parse record preserves the token contribution before hover wording is certified.",
    }


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
    wbw_loc = record.get("wbw_loc")
    if wbw_loc != "wbw:%s" % loc:
        errors.append("%s: wbw_loc must equal wbw:%s" % (loc, loc))

    surface = record.get("surface")
    if not isinstance(surface, str) or not surface:
        errors.append("%s: surface must be a nonempty string" % loc)
    elif _has_whitespace(surface):
        errors.append("%s: surface must be whitespace-free so the written token stays atomic" % loc)

    if record.get("src") != "qamus":
        errors.append("%s: src must be qamus" % loc)
    if record.get("kind") != "authored":
        errors.append("%s: kind must be authored" % loc)
    if record.get("lang") != "en":
        errors.append("%s: lang must be en" % loc)
    for key in ("gloss", "learner_explanation", "blocker"):
        if _bad_public_text(record.get(key)):
            errors.append("%s: %s leaks an internal source label" % (loc, key))

    decision_state = record.get("decision_state")
    blocker = record.get("blocker")
    if decision_state in {"pending", "blocked"} and not blocker:
        errors.append("%s: %s records need an exact blocker reason" % (loc, decision_state))
    if decision_state in {"rich_candidate", "rich_certified", "token_only_override"} and blocker:
        errors.append("%s: non-blocked records must not carry blocker text" % loc)

    public_boundary = record.get("public_boundary") or {}
    if public_boundary.get("public_gloss_src") != "qamus":
        errors.append("%s: public_gloss_src must be qamus" % loc)
    if public_boundary.get("public_gloss_kind") != "authored":
        errors.append("%s: public_gloss_kind must be authored" % loc)
    if public_boundary.get("public_gloss_lang") != "en":
        errors.append("%s: public_gloss_lang must be en" % loc)
    if public_boundary.get("external_source_names_public") is not False:
        errors.append("%s: external_source_names_public must be false" % loc)
    if public_boundary.get("public_gloss_src") != record.get("src"):
        errors.append("%s: public_boundary src must match top-level src" % loc)
    if public_boundary.get("public_gloss_kind") != record.get("kind"):
        errors.append("%s: public_boundary kind must match top-level kind" % loc)
    if public_boundary.get("public_gloss_lang") != record.get("lang"):
        errors.append("%s: public_boundary lang must match top-level lang" % loc)

    nahw = record.get("nahw") or {}
    if _bad_public_text(nahw.get("reasoning_summary")):
        errors.append("%s: nahw.reasoning_summary leaks an internal source label" % loc)

    hover_contract = record.get("hover_contract") or {}
    for key in ("must_surface", "must_not_surface", "reason"):
        if _bad_public_text(hover_contract.get(key)):
            errors.append("%s: hover_contract.%s leaks an internal source label" % (loc, key))

    parse_key = record.get("parse_key") or {}
    key_text = parse_key.get("key") or ""
    if not isinstance(key_text, str) or not key_text.strip():
        errors.append("%s: parse_key.key is required" % loc)
    elif not key_text.isascii():
        errors.append("%s: parse_key.key must be compact ASCII" % loc)
    if _bad_public_text(parse_key.get("key")) or _bad_public_text(parse_key.get("summary")):
        errors.append("%s: parse_key leaks an internal source label" % loc)
    for index, component in enumerate(parse_key.get("components") or []):
        if _bad_public_text(component.get("label")) or _bad_public_text(component.get("value")) or _bad_public_text(component.get("note")):
            errors.append("%s: parse_key.components[%d] leaks an internal source label" % (loc, index))

    evidence = record.get("evidence") or {}
    if decision_state == "rich_certified" and evidence.get("gate") == "never_auto_resolve":
        errors.append("%s: never_auto_resolve evidence cannot be rich_certified" % loc)

    must_surface = hover_contract.get("must_surface") or []
    segments = record.get("segments") or []
    if segments and not isinstance(segments, list):
        errors.append("%s: segments must be an array" % loc)
        return errors

    display = record.get("display") or {}
    if display.get("palette") != "qamus-grammar-v1":
        errors.append("%s: display.palette must be qamus-grammar-v1" % loc)
    display_segments = display.get("segments") or []
    if segments and len(display_segments) != len(segments):
        errors.append("%s: display.segments must align 1:1 with segments" % loc)
    for index, display_segment in enumerate(display_segments):
        if _bad_public_text(display_segment.get("role")) or _bad_public_text(display_segment.get("class")) or _bad_public_text(display_segment.get("label")):
            errors.append("%s: display.segments[%d] leaks an internal source label" % (loc, index))
        if index < len(segments):
            role = segments[index].get("role") if isinstance(segments[index], dict) else None
            expected_class = _display_class_for(role, record.get("pos"))
            if display_segment.get("segment_index") != index:
                errors.append("%s: display.segments[%d].segment_index must be %d" % (loc, index, index))
            if display_segment.get("role") != role:
                errors.append("%s: display.segments[%d].role must match segment role %s" % (loc, index, role))
            if display_segment.get("class") != expected_class:
                errors.append("%s: display.segments[%d].class must be %s for role %s" % (loc, index, expected_class, role))
            expected_label = DISPLAY_LABEL_BY_ROLE.get(role, "UNK")
            if display_segment.get("label") != expected_label:
                errors.append("%s: display.segments[%d].label must be %s for role %s" % (loc, index, expected_label, role))

    has_visible_article = any(
        isinstance(segment, dict)
        and segment.get("role") == "definite_article"
        and (segment.get("gloss_contribution") or "").strip().lower() == "the"
        for segment in segments
    )

    for index, segment in enumerate(segments):
        role = segment.get("role") if isinstance(segment, dict) else None
        contribution = (segment.get("gloss_contribution") or "").strip() if isinstance(segment, dict) else ""
        segment_surface = segment.get("surface") if isinstance(segment, dict) else None
        if not isinstance(segment_surface, str) or not segment_surface:
            errors.append("%s: segment[%d].surface must be a nonempty string" % (loc, index))
        elif _has_whitespace(segment_surface):
            errors.append("%s: segment[%d].surface must be whitespace-free; breakdown cannot encode visual gaps" % (loc, index))
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
    rows = [
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
    specs = [
        {
            "key": "V:III:PERF:ACT:3MP+OBJ.2MS",
            "summary": "Form III perfect verb with plural subject and second-person masculine singular object suffix.",
            "components": [
                {"label": "V", "value": "Form III perfect active"},
                {"label": "SUBJ", "value": "3rd masculine plural"},
                {"label": "OBJ", "value": "2nd masculine singular"},
            ],
        },
        {
            "key": "CONJ+P:BI+ART+N:GEN:DEF",
            "summary": "Conjunction plus bā preposition, definite genitive noun, and PP attachment.",
            "components": [
                {"label": "CONJ", "value": "and"},
                {"label": "P", "value": "by/through"},
                {"label": "N", "value": "definite genitive noun"},
            ],
        },
        {
            "key": "ACC_PART:INNA+PRON.1P",
            "summary": "Accusative particle with attached first-person plural pronoun.",
            "components": [
                {"label": "ACC", "value": "inna particle"},
                {"label": "PRON", "value": "1st person plural"},
            ],
        },
        {
            "key": "ART+N:GEN:DEF",
            "summary": "Definite genitive noun inside a jar-majrur phrase.",
            "components": [
                {"label": "ART", "value": "the"},
                {"label": "N", "value": "genitive definite noun"},
            ],
        },
        {
            "key": "CONJ+ART+N:NOM:DEF",
            "summary": "Coordinating waw plus definite nominative noun.",
            "components": [
                {"label": "CONJ", "value": "and"},
                {"label": "ART", "value": "the"},
                {"label": "N", "value": "nominative definite noun"},
            ],
        },
        {
            "key": "CONJ+ART+N:NOM:DEF",
            "summary": "Coordinating waw plus definite nominative noun.",
            "components": [
                {"label": "CONJ", "value": "and"},
                {"label": "ART", "value": "the"},
                {"label": "N", "value": "nominative definite noun"},
            ],
        },
        {
            "key": "ART+N:NOM:DEF:PL",
            "summary": "Definite nominative plural noun functioning as subject.",
            "components": [
                {"label": "ART", "value": "the"},
                {"label": "N", "value": "nominative definite plural noun"},
            ],
        },
        {
            "key": "VOC_PART",
            "summary": "Standalone vocative particle linked to its addressee.",
            "components": [
                {"label": "VOC", "value": "O"},
            ],
        },
        {
            "key": "VOC_SUPPORT+ATTN",
            "summary": "Vocative support plus attention particle; yā carries the separate O.",
            "components": [
                {"label": "VOC", "value": "you who"},
                {"label": "ATTN", "value": "attention marker"},
            ],
        },
        {
            "key": "FA+V:IV:PERF:ACT:1P+OBJ.3MP",
            "summary": "Fā prefix plus Form IV perfect verb with first-person plural subject and third-person plural object suffix.",
            "components": [
                {"label": "FA", "value": "so/then"},
                {"label": "V", "value": "Form IV perfect active"},
                {"label": "SUBJ", "value": "1st person plural"},
                {"label": "OBJ", "value": "3rd masculine plural"},
            ],
        },
    ]
    glosses = [
        "they argued with you",
        "and by the star",
        "indeed We",
        "the earth, land",
        "and + the sun",
        "and + the moon",
        "the foolish ones",
        "O",
        "you who",
        "so We destroyed them",
    ]
    learner_explanations = [
        "The verb stem contributes the action, and the attached kāf contributes the masculine singular object you.",
        "The written token carries conjunction, bā preposition, article, and host noun contributions.",
        "The particle contributes emphasis, and the attached pronoun contributes We.",
        "The article contributes the, while the host noun contributes earth or land.",
        "The wāw contributes and, the article contributes the, and the host noun contributes sun.",
        "The wāw contributes and, the article contributes the, and the host noun contributes moon.",
        "The article contributes the once; the host noun contributes foolish ones without repeating the article.",
        "The split vocative particle contributes O and points to the following addressee.",
        "This token carries the vocative support expression; the preceding yā carries O.",
        "The fā prefix links the clause, the Form IV verb stem contributes destroyed, and the suffix pronouns contribute We and them.",
    ]
    nahw_functions = [
        "finite_verb_with_object_suffix",
        "conjunction_plus_prepositional_phrase",
        "accusative_particle_with_attached_pronoun",
        "definite_genitive_nominal",
        "coordination",
        "coordination",
        "definite_nominal_subject",
        "vocative_particle",
        "vocative_support",
        "finite_verb_with_subject_and_object_suffixes",
    ]
    nahw_summaries = [
        "The object suffix must be preserved in the hover, not hidden as metadata.",
        "The bā relation and the host noun are both visible grammar contributions.",
        "The inna construction requires the attached pronoun to remain visible.",
        "The genitive nominal remains definite because of the article and its syntactic environment.",
        "The coordinating wāw and article are separate visible contributions before the noun.",
        "The coordinating wāw and article are separate visible contributions before the noun.",
        "The article is a separate contribution; duplicating it in the host gloss is a defect.",
        "The vocative particle should not swallow the following addressee support token.",
        "The addressee support token should not duplicate the separate yā contribution.",
        "The verb carries explicit subject and object pronoun segments that must surface before certification.",
    ]
    for row, spec, gloss, learner, function, summary in zip(rows, specs, glosses, learner_explanations, nahw_functions, nahw_summaries):
        row["wbw_loc"] = "wbw:%s" % row["loc"]
        row["key"] = row["surface"]
        row["gloss"] = gloss
        row["src"] = "qamus"
        row["kind"] = "authored"
        row["lang"] = "en"
        row["decision_state"] = "rich_candidate"
        row["sarf"] = _rich_sarf_for(row)
        row["nahw"] = _rich_nahw_for(row, function, summary=summary)
        row["learner_explanation"] = learner
        row["blocker"] = None
        row["parse_key"] = spec
        row["display"] = _display_for(row)
    return rows


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
        del missing_lang[0]["lang"]
        bad_lang = os.path.join(td, "missing-lang.jsonl")
        _write_jsonl(bad_lang, missing_lang)
        _, errors = validate_file(bad_lang)
        assert any("missing required key 'lang'" in e or "lang must be en" in e for e in errors), errors

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

        parse_leak = _sample_records()
        parse_leak[0]["parse_key"]["summary"] = "QAC says verb"
        bad_parse_leak = os.path.join(td, "parse-leak.jsonl")
        _write_jsonl(bad_parse_leak, parse_leak)
        _, errors = validate_file(bad_parse_leak)
        assert any("parse_key leaks an internal source label" in e for e in errors), errors

        bad_display = _sample_records()
        bad_display[0]["display"]["segments"][1]["class"] = "qg-noun"
        bad_display_file = os.path.join(td, "bad-display.jsonl")
        _write_jsonl(bad_display_file, bad_display)
        _, errors = validate_file(bad_display_file)
        assert any("display.segments[1].class must be qg-pronoun" in e for e in errors), errors

        duplicate_article = _sample_records()
        duplicate_article[6]["segments"][1]["gloss_contribution"] = "the foolish ones"
        bad_article = os.path.join(td, "duplicate-article.jsonl")
        _write_jsonl(bad_article, duplicate_article)
        _, errors = validate_file(bad_article)
        assert any("stem gloss duplicates definite_article contribution" in e for e in errors), errors

        spaced_surface = _sample_records()
        spaced_surface[4]["surface"] = "وَ ٱلشَّمْسُ"
        bad_surface = os.path.join(td, "spaced-surface.jsonl")
        _write_jsonl(bad_surface, spaced_surface)
        _, errors = validate_file(bad_surface)
        assert any("surface must be whitespace-free" in e for e in errors), errors

        spaced_segment = _sample_records()
        spaced_segment[4]["segments"][0]["surface"] = "وَ "
        bad_segment = os.path.join(td, "spaced-segment.jsonl")
        _write_jsonl(bad_segment, spaced_segment)
        _, errors = validate_file(bad_segment)
        assert any("segment[0].surface must be whitespace-free" in e for e in errors), errors

        blocked_without_reason = _sample_records()
        blocked_without_reason[0]["decision_state"] = "blocked"
        bad_blocked = os.path.join(td, "blocked-without-reason.jsonl")
        _write_jsonl(bad_blocked, blocked_without_reason)
        _, errors = validate_file(bad_blocked)
        assert any("blocked records need an exact blocker reason" in e for e in errors), errors

        mismatch_wbw = _sample_records()
        mismatch_wbw[0]["wbw_loc"] = "wbw:1:1:1"
        bad_wbw = os.path.join(td, "mismatch-wbw.jsonl")
        _write_jsonl(bad_wbw, mismatch_wbw)
        _, errors = validate_file(bad_wbw)
        assert any("wbw_loc must equal" in e for e in errors), errors

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
