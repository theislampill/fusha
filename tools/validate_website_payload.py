#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable twin of docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md.

Validates `qamus.website_projection_payload.v1` files — the renderer-facing
payload shape the separate website agent consumes. Red-first named checks:

- missing entry links (entry_link_state discipline, contract §4)
- prose leak (Arabic i'rab formulas in learner fields, contract §11)
- hash fork (projection_hash recomputation + appearance parity, contract §5)
- non-whitelist page-local metadata (closed 4-key whitelist, contract §6)
- segment-reconstruction failure (surface tiling invariant, contract §3.1)
- unresolved colour-guessing (neutral qg-unresolved only, contract §10.2)
- rootless particle without rootless_pedagogy (contract §10.1)
- provenance/certification honesty (only certified provenance certifies, §8)
- no server paths in any payload string (RM-09)

Usage:
    python tools/validate_website_payload.py PAYLOAD.json [...]
    python tools/validate_website_payload.py            # committed samples
    python tools/validate_website_payload.py --self-test

Repo style: hand-rolled named validators, no jsonschema dependency,
red-first self-test gated in tools/check_regressions.py.
"""

from __future__ import annotations

import argparse
import copy
from functools import lru_cache
import glob
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "qamus" / "examples" / "website-payloads"
P007_DIR = ROOT / "qamus" / "examples" / "p007-li-pilot"
APPEARANCE_UNIVERSE_PATH = (
    ROOT / "qamus" / "lattice" / "example-ayah-universe.jsonl"
)
OCCURRENCE_UNIVERSE_PATH = (
    ROOT / "qamus" / "lattice" / "example-ayah-universe.occurrences.jsonl"
)
P007_GEOMETRY_FACTS_PATH = (
    ROOT
    / "qamus"
    / "certification"
    / "p007-geometry-wave"
    / "typed-facts.jsonl"
)

PAYLOAD_SCHEMA = "qamus.website_projection_payload.v1"
ACCEPTED_MAJOR = 1
APPEARANCE_BINDING_VERSION = (1, 2, 0)
APPEARANCE_BINDING_STATE = (
    "candidate_requires_renderer_capability_acceptance"
)
UNRESOLVED_PRIMARY_TEXT = (
    "Analysis unresolved; candidate analyses are listed only as alternatives."
)
IGNORABLE_APPEARANCE_ANNOTATION_LETTERS = frozenset({
    "\u06e5",  # ARABIC SMALL WAW
    "\u06e6",  # ARABIC SMALL YEH
})

PAGE_KINDS = frozenset({
    "reader", "entry", "example_card", "wbw_hover", "dogfood_review",
})
PROJECTION_KINDS = frozenset({
    "particle_clitic_word", "noun_word", "verb_word",
})
RELATION_KINDS = frozenset({
    "certified_sense", "certified_entry", "candidate_entry",
    "clitic_component_of_entry",
    # Added 1.1.0 (additive within major 1, contract §9): a root-agreement
    # relation ONLY — the occurrence shares the entry's root family; never a
    # lexeme/entry-membership claim (guard: root_agreement_never_lexeme_edge).
    "root_family_of_entry",
})
ENTRY_LINK_STATES = frozenset({"linked", "none_yet"})
PROVENANCE_CLASSES = frozenset({
    "certified", "illustrative-from-live", "illustrative-constructed",
})
CERT_STATUSES = frozenset({"certified", "candidate", "unresolved"})
V12_LINK_STATES = frozenset({"candidate", "certified"})
V12_SENSE_STATES = frozenset({
    "candidate", "certified", "not_applicable", "unresolved",
})
V12_CERTIFICATION_PLANE_STATES = frozenset({"candidate", "unresolved"})
V12_CERTIFICATION_PLANE_KEYS = frozenset({
    "attachment_head", "contextual_meaning", "entry_links", "function",
    "governor", "referent", "root", "segmentation", "translation",
})
V12_ENTRY_LINK_KEYS = frozenset({
    "entry_id", "evidence_refs", "link_state", "relation_kind",
    "segment_index", "sense_id", "sense_state",
})
V12_REVERSE_ENTRY_KEYS = frozenset({
    "entry_id", "evidence_refs", "link_state", "occurrences",
    "relation_kind", "segment_index", "sense_id", "sense_state",
})
V12_REVERSE_OCCURRENCE_KEYS = frozenset({
    "loc", "occurrence_id", "page_refs", "projection_hash", "surface",
})

# Closed page-local whitelist — extending it is an owner decision recorded in
# the particle projection contract (§2.2, flag A), never a validator edit.
PERMITTED_PAGE_LOCAL_KEYS = frozenset({
    "selected_highlight", "entry_relationship", "focus", "navigation",
})

# Arabic technical i'rab formulas: private-side analysis prose, forbidden in
# the learner-facing teaching plane (contract §11). Multi-word formulas only,
# so quoted object-language Arabic stays legal.
FORBIDDEN_IRAB_PROSE = (
    "مبتدأ مرفوع",
    "خبر مرفوع",
    "فاعل مرفوع",
    "مفعول به منصوب",
    "في محل جر",
    "في محل رفع",
    "في محل نصب",
    "وعلامة رفعه",
    "وعلامة نصبه",
    "وعلامة جره",
    "مجرور وعلامة",
)

# Public payloads carry no external-source labels or private review prose.
EXTERNAL_OR_PRIVATE_SOURCE_RE = re.compile(
    r"(?i)(?:"
    r"corpus[._ -]?quran[._ -]?com|quran[._ -]?com|\bqac\b|"
    r"quranic arabic corpus|tanzil|sunnah\.com|"
    r"\breviewer-private\b|\bprivate reviewer\b|"
    r"\bsource prose\b|\bprivate source\b"
    r")"
)
V12_PRIVATE_WORKFLOW_RE = re.compile(
    r"(?i)(?:"
    r"\breviewer(?:s)?\b|\btwo[- ]vote\b|\bcandidate mode\b|"
    r"\bpacket\b|\bsource row\b|\bclassification row\b|"
    r"\brung[- ]?\d+\b|\bworkflow\b|\bprivate path\b|\bmcp\b|"
    r"\binformed_by\b"
    r")"
)
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "build_host", "hostname", "informed_by", "machine_topology",
    "private_path", "reviewer_private", "worktree",
})

# RM-09: no private filesystem path or machine topology crosses the boundary.
MACHINE_TOPOLOGY_PATTERNS = (
    # The negative lookbehind prevents URI schemes such as https:// from
    # being mistaken for a Windows drive path while still catching a drive
    # path embedded in prose.
    re.compile(r"(?i)(?<![a-z0-9+.-])[a-z]:[\\/]"),
    re.compile(
        r"(?i)(?<![a-z0-9:/\\])(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+"
    ),
    re.compile(r"(?i)(?<![a-z0-9_])~[\\/]"),
    re.compile(
        r"(?i)(?<![a-z0-9:/._-])"
        r"/(?:home|users|root|srv|etc|var/www|volumes)(?:/|\b)"
    ),
    re.compile(r"(?i)(?<![a-z0-9:/._-])/mnt/[a-z](?:/|\b)"),
    re.compile(
        r"(?<![\d.])(?:10(?:\.\d{1,3}){3}|"
        r"192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?![\d.])"
    ),
)
SERVER_PATH_RE = re.compile(
    r"(?:/var/www|/srv/|/home/[a-z]|/etc/|[A-Za-z]:\\\\|[A-Za-z]:\\)"
)

REQUIRED_ENVELOPE_KEYS = (
    "schema", "schema_version", "payload_kind", "occurrence_id",
    "artifact_id", "appearance", "projection", "projection_hash",
    "reverse_links", "provenance",
)
REQUIRED_PROJECTION_KEYS = (
    "occurrence_id", "surface", "normalization", "kind", "segments",
    "whole_word_gloss", "learner_explanation", "entry_links",
    "entry_link_state", "morpheme_spans", "root", "hover_cards",
    "unresolved", "certification", "evidence_refs",
)
REQUIRED_SEGMENT_KEYS = (
    "segment_index", "surface", "char_start", "char_end",
    "semantic_class", "renderer_class",
)
REQUIRED_MORPHEME_SPAN_KEYS = (
    "morpheme_occurrence_id", "segment_index", "char_start", "char_end",
)
REQUIRED_APPEARANCE_MAP_KEYS = frozenset({
    "appearance_char_end", "appearance_char_start",
    "canonical_char_end", "canonical_char_start",
    "morpheme_occurrence_id", "segment_index",
})


def projection_hash(projection: dict) -> str:
    """sha256 over the canonical serialization of the fact plane (§5)."""
    blob = json.dumps(projection, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _version_tuple(payload: dict) -> tuple[int, int, int] | None:
    match = re.fullmatch(
        r"(\d+)\.(\d+)\.(\d+)",
        str(payload.get("schema_version") or ""),
    )
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def appearance_binding_basis(payload: dict) -> dict:
    """Stable appearance identity, local geometry, and shared projection."""
    appearance = payload.get("appearance") or {}
    projection = payload.get("projection")
    normalization = (
        projection.get("normalization")
        if isinstance(projection, dict)
        else None
    )
    return {
        "appearance_id": appearance.get("appearance_id"),
        "artifact_id": payload.get("artifact_id"),
        "binding_state": appearance.get("binding_state"),
        "canonical_to_appearance_span_map": appearance.get(
            "canonical_to_appearance_span_map"
        ),
        "displayed_surface": appearance.get("displayed_surface"),
        "normalization": normalization,
        "occurrence_id": payload.get("occurrence_id"),
        "page_id": appearance.get("page_id"),
        "page_kind": appearance.get("page_kind"),
        "projection_hash": payload.get("projection_hash"),
    }


def appearance_binding_hash(payload: dict) -> str:
    """sha256 over the stable appearance binding, outside projection."""
    blob = json.dumps(
        appearance_binding_basis(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _letter_ownership_signature(text: str) -> str:
    """Preserve written base letters while ignoring attached mark variation."""
    if not isinstance(text, str):
        return ""
    return "".join(
        char
        for char in unicodedata.normalize("NFC", text)
        if not unicodedata.category(char).startswith("M")
        and char not in IGNORABLE_APPEARANCE_ANNOTATION_LETTERS
    )


@lru_cache(maxsize=1)
def _appearance_universe() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with APPEARANCE_UNIVERSE_PATH.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            appearance_id = row.get("appearance_id")
            if not isinstance(appearance_id, str) or not appearance_id:
                raise ValueError(
                    "appearance universe line %d lacks appearance_id"
                    % line_number
                )
            if appearance_id in rows:
                raise ValueError(
                    "appearance universe duplicates %s" % appearance_id
                )
            rows[appearance_id] = row
    return rows


@lru_cache(maxsize=1)
def _occurrence_universe() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with OCCURRENCE_UNIVERSE_PATH.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            occurrence_id = row.get("occurrence_id")
            if not isinstance(occurrence_id, str) or not occurrence_id:
                raise ValueError(
                    "occurrence universe line %d lacks occurrence_id"
                    % line_number
                )
            if occurrence_id in rows:
                raise ValueError(
                    "occurrence universe duplicates %s" % occurrence_id
                )
            rows[occurrence_id] = row
    return rows


@lru_cache(maxsize=1)
def _p007_geometry_facts() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with P007_GEOMETRY_FACTS_PATH.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            fact_id = row.get("fact_id")
            if not isinstance(fact_id, str) or not fact_id:
                raise ValueError(
                    "p007 geometry fact line %d lacks fact_id" % line_number
                )
            if fact_id in rows:
                raise ValueError(
                    "p007 geometry facts duplicate %s" % fact_id
                )
            rows[fact_id] = row
    return rows


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_strings(child)


def _all_key_paths(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            path = "%s.%s" % (prefix, key) if prefix else key
            yield path, key
            yield from _all_key_paths(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _all_key_paths(child, "%s[%d]" % (prefix, index))


def _nested_learner_strings(value, prefix):
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _nested_learner_strings(
                child,
                "%s.%s" % (prefix, key),
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _nested_learner_strings(
                child,
                "%s[%d]" % (prefix, index),
            )


def _learner_fields(projection: dict):
    """Yield (field_name, text) for every learner-facing field (§11)."""
    for key in ("whole_word_gloss", "learner_explanation",
                "rootless_pedagogy"):
        yield key, projection.get(key)
    unresolved = projection.get("unresolved")
    if isinstance(unresolved, dict):
        yield from _nested_learner_strings(unresolved, "unresolved")
    for i, seg in enumerate(projection.get("segments") or []):
        if not isinstance(seg, dict):
            continue
        for key in ("gloss", "sarf_note", "nahw_note"):
            yield "segments[%d].%s" % (i, key), seg.get(key)
    for i, card in enumerate(projection.get("hover_cards") or []):
        if not isinstance(card, dict):
            continue
        learner_card = {
            key: value
            for key, value in card.items()
            if key not in {
                "entry_link", "morpheme_occurrence_id", "segment_index",
            }
        }
        yield from _nested_learner_strings(
            learner_card,
            "hover_cards[%d]" % i,
        )


def _entry_link_signature(row: dict) -> str:
    """Canonical v1.2 forward/reverse entry-edge identity."""
    basis = {
        key: row.get(key)
        for key in V12_ENTRY_LINK_KEYS
    }
    return json.dumps(
        basis,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _entry_link_state_errors(row: dict, label: str, errors) -> None:
    relation = row.get("relation_kind")
    link_state = row.get("link_state")
    sense_id = row.get("sense_id")
    sense_state = row.get("sense_state")
    evidence_refs = row.get("evidence_refs")
    if link_state not in V12_LINK_STATES:
        errors.append(
            "reverse_entry_parity: %s link_state %r not in %s"
            % (label, link_state, sorted(V12_LINK_STATES))
        )
    if sense_state not in V12_SENSE_STATES:
        errors.append(
            "reverse_entry_parity: %s sense_state %r not in %s"
            % (label, sense_state, sorted(V12_SENSE_STATES))
        )
    if not isinstance(evidence_refs, list) or not evidence_refs \
            or not all(
                isinstance(ref, str) and ref.strip()
                for ref in evidence_refs
            ) or len(set(evidence_refs)) != len(evidence_refs):
        errors.append(
            "reverse_entry_parity: %s evidence_refs must be a non-empty "
            "unique string array" % label
        )
    if relation == "candidate_entry" and link_state != "candidate":
        errors.append(
            "reverse_entry_parity: %s candidate_entry must retain "
            "link_state candidate" % label
        )
    if relation in {"certified_entry", "certified_sense"} \
            and link_state != "certified":
        errors.append(
            "reverse_entry_parity: %s %s must retain link_state certified"
            % (label, relation)
        )
    if relation == "certified_sense":
        if not isinstance(sense_id, str) or not sense_id \
                or sense_state != "certified":
            errors.append(
                "reverse_entry_parity: %s certified_sense requires a "
                "non-empty sense_id and sense_state certified" % label
            )
    elif relation == "certified_entry":
        if sense_id is not None or sense_state != "unresolved":
            errors.append(
                "reverse_entry_parity: %s certified_entry requires null "
                "sense_id and sense_state unresolved" % label
            )
    elif relation == "candidate_entry":
        expected_sense_state = (
            "candidate"
            if isinstance(sense_id, str) and sense_id
            else "unresolved"
        )
        if sense_state != expected_sense_state:
            errors.append(
                "reverse_entry_parity: %s candidate_entry sense_state %r "
                "must be %r for sense_id %r"
                % (label, sense_state, expected_sense_state, sense_id)
            )
    elif relation == "root_family_of_entry":
        if sense_id is not None or sense_state != "not_applicable":
            errors.append(
                "reverse_entry_parity: %s root-family relation requires "
                "null sense_id and sense_state not_applicable" % label
            )


def _key_scan_views(path: str, key: str):
    """Views that expose separator-hidden private/source labels in keys."""
    yield key
    yield re.sub(r"[_-]+", " ", key)
    yield path
    yield re.sub(r"[_-]+", " ", path)


# --------------------------------------------------------------------------- #
# named checks — each appends "check_name: message" strings to errors
# --------------------------------------------------------------------------- #

def check_envelope(payload, errors):
    for key in REQUIRED_ENVELOPE_KEYS:
        if key not in payload:
            errors.append("envelope_shape: missing top-level key %r" % key)
    if payload.get("schema") != PAYLOAD_SCHEMA:
        errors.append("envelope_shape: schema is %r, expected %r"
                      % (payload.get("schema"), PAYLOAD_SCHEMA))
    if payload.get("payload_kind") != "occurrence_projection":
        errors.append("envelope_shape: payload_kind is %r, expected "
                      "'occurrence_projection'" % payload.get("payload_kind"))
    version = payload.get("schema_version")
    version_parts = _version_tuple(payload)
    if version_parts is None:
        errors.append("envelope_version: schema_version %r is not semver"
                      % version)
    elif version_parts[0] != ACCEPTED_MAJOR:
        errors.append(
            "envelope_version: schema_version %r has major %s, validator "
            "accepts major %d only (breaking changes are an owner decision, "
            "contract §9)" % (version, version_parts[0], ACCEPTED_MAJOR))
    appearance = payload.get("appearance")
    if not isinstance(appearance, dict):
        errors.append("envelope_shape: appearance must be an object")
        return
    for key in ("appearance_id", "page_id", "page_kind"):
        if not appearance.get(key):
            errors.append("envelope_shape: appearance missing %r" % key)
    if appearance.get("page_kind") not in PAGE_KINDS:
        errors.append("envelope_shape: appearance.page_kind %r not in %s"
                      % (appearance.get("page_kind"), sorted(PAGE_KINDS)))
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        errors.append("projection_shape: projection must be an object")
        return
    if projection.get("occurrence_id") != payload.get("occurrence_id"):
        errors.append(
            "envelope_shape: projection.occurrence_id %r != envelope "
            "occurrence_id %r"
            % (projection.get("occurrence_id"),
               payload.get("occurrence_id")))
    for key in REQUIRED_PROJECTION_KEYS:
        if key not in projection:
            errors.append("projection_shape: missing projection key %r"
                          % key)
    if projection.get("normalization") != "NFC":
        errors.append("projection_shape: normalization is %r, expected "
                      "'NFC'" % projection.get("normalization"))
    if projection.get("kind") not in PROJECTION_KINDS:
        errors.append("projection_shape: kind %r not in %s"
                      % (projection.get("kind"),
                         sorted(PROJECTION_KINDS)))


def check_hash_fork(payload, errors):
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    want = projection_hash(projection)
    got = payload.get("projection_hash")
    if got != want:
        errors.append(
            "hash_fork: projection_hash %s does not match the canonical "
            "serialization hash %s — the fact plane and its hash have forked "
            "(contract §5)" % (got, want))
    # appearance-parity: every listed appearance of this occurrence must
    # carry the same hash as the canonical projection.
    reverse = payload.get("reverse_links")
    if not isinstance(reverse, dict):
        errors.append("reverse_links: reverse_links must be an object")
        return
    appearances = reverse.get("occurrence_to_appearances")
    if not isinstance(appearances, list):
        errors.append(
            "reverse_links: occurrence_to_appearances must be an array"
        )
        return
    top_appearance = payload.get("appearance") or {}
    top_matches = 0
    seen_ids = set()
    for index, app in enumerate(appearances):
        if not isinstance(app, dict):
            errors.append(
                "reverse_links: occurrence_to_appearances[%d] must be an "
                "object" % index
            )
            continue
        appearance_id = app.get("appearance_id")
        if not isinstance(appearance_id, str) or not appearance_id:
            errors.append(
                "reverse_links: occurrence_to_appearances[%d] lacks "
                "appearance_id" % index
            )
        elif appearance_id in seen_ids:
            errors.append(
                "reverse_links: duplicate appearance_id %s"
                % appearance_id
            )
        else:
            seen_ids.add(appearance_id)
        listed = app.get("projection_hash")
        if listed != want:
            errors.append(
                "hash_fork: appearance %s lists projection_hash %s but the "
                "canonical occurrence hash is %s — same occurrence must "
                "carry the same projection everywhere (contract §5)"
                % (app.get("appearance_id"), listed, want))
        if appearance_id == top_appearance.get("appearance_id"):
            top_matches += 1
            for key in ("page_id", "page_kind"):
                if app.get(key) != top_appearance.get(key):
                    errors.append(
                        "reverse_links: envelope appearance %s has %s=%r "
                        "but its reverse declaration has %r"
                        % (
                            appearance_id,
                            key,
                            top_appearance.get(key),
                            app.get(key),
                        )
                    )
    if top_matches != 1:
        errors.append(
            "reverse_links: envelope appearance_id %r must occur exactly "
            "once in occurrence_to_appearances; found %d"
            % (top_appearance.get("appearance_id"), top_matches)
        )
    entry_reverse = reverse.get("entry_to_occurrences")
    if not isinstance(entry_reverse, list):
        errors.append(
            "reverse_links: entry_to_occurrences must be an array"
        )


def check_page_local_whitelist(payload, errors):
    appearance = payload.get("appearance")
    if not isinstance(appearance, dict):
        return
    page_local = appearance.get("page_local")
    if page_local is None:
        return
    if not isinstance(page_local, dict):
        errors.append("page_local_whitelist: appearance.page_local must be "
                      "an object")
        return
    extra = sorted(set(page_local) - PERMITTED_PAGE_LOCAL_KEYS)
    if extra:
        errors.append(
            "page_local_whitelist: non-whitelist page-local metadata %s — "
            "the whitelist is closed at 4 keys (contract §6, owner flag A)"
            % ", ".join(extra))
    projection = payload.get("projection")
    if isinstance(projection, dict):
        smuggled = sorted(PERMITTED_PAGE_LOCAL_KEYS & set(projection))
        if smuggled:
            errors.append(
                "page_local_whitelist: presentation keys %s smuggled into "
                "the hashed projection object (contract §6)"
                % ", ".join(smuggled))


def check_entry_links(payload, errors):
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    state = projection.get("entry_link_state")
    links = projection.get("entry_links")
    if state not in ENTRY_LINK_STATES:
        errors.append(
            "entry_links: entry_link_state %r is not one of %s — a payload "
            "must declare its entry-link state honestly (contract §4)"
            % (state, sorted(ENTRY_LINK_STATES)))
        return
    if not isinstance(links, list):
        errors.append("entry_links: entry_links must be an array")
        return
    if state == "linked" and not links:
        errors.append(
            "entry_links: entry_link_state is 'linked' but entry_links is "
            "empty — missing entry links (contract §4)")
    if state == "none_yet" and links:
        errors.append(
            "entry_links: entry_link_state is 'none_yet' but entry_links is "
            "non-empty (contract §4)")
    for i, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append("entry_links: entry_links[%d] must be an object" % i)
            continue
        if not link.get("entry_id"):
            errors.append("entry_links: entry_links[%d] missing entry_id" % i)
        if "sense_id" not in link:
            errors.append(
                "entry_links: entry_links[%d] missing sense_id key (null is "
                "legal; absence is not, contract §4)" % i)
        if link.get("relation_kind") not in RELATION_KINDS:
            errors.append(
                "entry_links: entry_links[%d] relation_kind %r not in %s"
                % (i, link.get("relation_kind"), sorted(RELATION_KINDS)))


def check_reverse_entry_parity(payload, errors):
    """Require lossless v1.2 forward/reverse candidate-edge identity."""
    version = _version_tuple(payload)
    if version is None or version < APPEARANCE_BINDING_VERSION:
        return
    projection = payload.get("projection")
    reverse = payload.get("reverse_links")
    if not isinstance(projection, dict) or not isinstance(reverse, dict):
        return
    forward = projection.get("entry_links")
    reverse_rows = reverse.get("entry_to_occurrences")
    appearances = reverse.get("occurrence_to_appearances")
    if not isinstance(forward, list) \
            or not isinstance(reverse_rows, list) \
            or not isinstance(appearances, list):
        return

    expected_page_refs = [
        row.get("page_id")
        for row in appearances
        if isinstance(row, dict)
    ]
    if any(
        not isinstance(page_id, str) or not page_id
        for page_id in expected_page_refs
    ) or len(set(expected_page_refs)) != len(expected_page_refs):
        errors.append(
            "reverse_entry_parity: reverse appearance page_ids must be "
            "non-empty and unique"
        )

    forward_signatures = []
    for index, row in enumerate(forward):
        if not isinstance(row, dict):
            continue
        if set(row) != V12_ENTRY_LINK_KEYS:
            errors.append(
                "reverse_entry_parity: entry_links[%d] keys %s do not "
                "equal the closed 1.2.0 edge shape %s"
                % (
                    index,
                    sorted(row),
                    sorted(V12_ENTRY_LINK_KEYS),
                )
            )
        _entry_link_state_errors(
            row,
            "entry_links[%d]" % index,
            errors,
        )
        forward_signatures.append(_entry_link_signature(row))
    if len(set(forward_signatures)) != len(forward_signatures):
        errors.append(
            "reverse_entry_parity: projection.entry_links contains a "
            "duplicate typed edge"
        )

    occurrence_id = payload.get("occurrence_id")
    projection_surface = projection.get("surface")
    occurrence_parts = str(occurrence_id or "").split(":")
    canonical_loc = (
        ":".join(occurrence_parts[1:])
        if len(occurrence_parts) == 4
        else None
    )
    projection_digest = payload.get("projection_hash")
    reverse_signatures = []
    for index, row in enumerate(reverse_rows):
        if not isinstance(row, dict):
            errors.append(
                "reverse_entry_parity: entry_to_occurrences[%d] must be "
                "an object" % index
            )
            continue
        if set(row) != V12_REVERSE_ENTRY_KEYS:
            errors.append(
                "reverse_entry_parity: entry_to_occurrences[%d] keys %s "
                "do not equal the closed 1.2.0 reverse edge shape %s"
                % (
                    index,
                    sorted(row),
                    sorted(V12_REVERSE_ENTRY_KEYS),
                )
            )
        _entry_link_state_errors(
            row,
            "entry_to_occurrences[%d]" % index,
            errors,
        )
        reverse_signatures.append(_entry_link_signature(row))
        occurrences = row.get("occurrences")
        if not isinstance(occurrences, list) or len(occurrences) != 1:
            errors.append(
                "reverse_entry_parity: entry_to_occurrences[%d] must "
                "contain exactly this payload's one occurrence" % index
            )
            continue
        occurrence = occurrences[0]
        if not isinstance(occurrence, dict):
            errors.append(
                "reverse_entry_parity: entry_to_occurrences[%d]."
                "occurrences[0] must be an object" % index
            )
            continue
        if set(occurrence) != V12_REVERSE_OCCURRENCE_KEYS:
            errors.append(
                "reverse_entry_parity: reverse occurrence %d keys %s do "
                "not equal the closed 1.2.0 shape %s"
                % (
                    index,
                    sorted(occurrence),
                    sorted(V12_REVERSE_OCCURRENCE_KEYS),
                )
            )
        expected_values = {
            "loc": canonical_loc,
            "occurrence_id": occurrence_id,
            "projection_hash": projection_digest,
            "surface": projection_surface,
        }
        for key, expected in expected_values.items():
            if occurrence.get(key) != expected:
                errors.append(
                    "reverse_entry_parity: reverse occurrence %d %s=%r "
                    "does not equal %r"
                    % (index, key, occurrence.get(key), expected)
                )
        page_refs = occurrence.get("page_refs")
        if not isinstance(page_refs, list) \
                or any(
                    not isinstance(page_id, str) or not page_id
                    for page_id in page_refs
                ) \
                or len(page_refs) != len(set(page_refs)) \
                or set(page_refs) != set(expected_page_refs):
            errors.append(
                "reverse_entry_parity: reverse occurrence %d page_refs "
                "must equal the unique occurrence appearance page set"
                % index
            )

    if sorted(reverse_signatures) != sorted(forward_signatures):
        errors.append(
            "reverse_entry_parity: reverse typed entry-edge set does not "
            "equal projection.entry_links; candidate state or identity "
            "would be lost"
        )
    if len(set(reverse_signatures)) != len(reverse_signatures):
        errors.append(
            "reverse_entry_parity: entry_to_occurrences contains a "
            "duplicate typed edge"
        )


def check_prose_leak(payload, errors):
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    for field, text in _learner_fields(projection):
        if not isinstance(text, str):
            continue
        for formula in FORBIDDEN_IRAB_PROSE:
            if formula in text:
                errors.append(
                    "prose_leak: learner field %r carries Arabic i'rab "
                    "formula %r — the teaching plane is learner-register "
                    "English (contract §11)" % (field, formula))


def check_segment_reconstruction(payload, errors):
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    surface = projection.get("surface")
    segments = projection.get("segments")
    if not isinstance(surface, str) or not isinstance(segments, list):
        return
    if unicodedata.normalize("NFC", surface) != surface:
        errors.append(
            "segment_reconstruction: projection.surface is not "
            "NFC-normalized (contract §3)")
    joined = ""
    cursor = 0
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            errors.append("segment_reconstruction: segments[%d] must be an "
                          "object" % i)
            return
        for key in REQUIRED_SEGMENT_KEYS:
            if key not in seg:
                errors.append("segment_reconstruction: segments[%d] missing "
                              "%r" % (i, key))
        if seg.get("segment_index") != i:
            errors.append(
                "segment_reconstruction: segments[%d] carries segment_index "
                "%r — indices must be 0-based and contiguous"
                % (i, seg.get("segment_index")))
        seg_surface = seg.get("surface")
        if not isinstance(seg_surface, str) or not seg_surface:
            errors.append("segment_reconstruction: segments[%d] has an "
                          "empty surface" % i)
            return
        start, end = seg.get("char_start"), seg.get("char_end")
        if start != cursor:
            errors.append(
                "segment_reconstruction: segments[%d] char_start %r does "
                "not tile the surface (expected %d) — spans must be "
                "contiguous (contract §3.1)" % (i, start, cursor))
        if not isinstance(end, int) or not isinstance(start, int) \
                or end - start != len(seg_surface):
            errors.append(
                "segment_reconstruction: segments[%d] span [%r,%r) does not "
                "match its surface length %d"
                % (i, start, end, len(seg_surface)))
        if isinstance(start, int) and isinstance(end, int) \
                and surface[max(start, 0):end] != seg_surface:
            errors.append(
                "segment_reconstruction: segments[%d] surface %r does not "
                "equal the sliced span %r of the word surface"
                % (i, seg_surface, surface[max(start, 0):end]))
        joined += seg_surface
        cursor += len(seg_surface)
    if joined != surface:
        errors.append(
            "segment_reconstruction: joined segment surfaces %r do not "
            "reconstruct the word surface %r — a renderer slicing by spans "
            "and a renderer joining segments would render different words "
            "(contract §3.1)" % (joined, surface))


def _valid_offset(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _splits_combining_sequence(surface: str, offset: int) -> bool:
    if offset <= 0 or offset >= len(surface):
        return False
    return bool(
        unicodedata.combining(surface[offset])
        or unicodedata.category(surface[offset]).startswith("M")
    )


def check_morpheme_spans(payload, errors):
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    surface = projection.get("surface")
    segments = projection.get("segments")
    spans = projection.get("morpheme_spans")
    if not isinstance(spans, list):
        errors.append("morpheme_spans: morpheme_spans must be an array")
        return
    if not isinstance(surface, str) or not isinstance(segments, list):
        return
    seen_ids = set()
    seen_segments = set()
    for index, row in enumerate(spans):
        if not isinstance(row, dict):
            errors.append(
                "morpheme_spans: morpheme_spans[%d] must be an object"
                % index
            )
            continue
        for key in REQUIRED_MORPHEME_SPAN_KEYS:
            if key not in row:
                errors.append(
                    "morpheme_spans: morpheme_spans[%d] missing %r"
                    % (index, key)
                )
        morpheme_id = row.get("morpheme_occurrence_id")
        if not isinstance(morpheme_id, str) or not morpheme_id:
            errors.append(
                "morpheme_spans: morpheme_spans[%d] has no non-empty "
                "morpheme_occurrence_id" % index
            )
        elif morpheme_id in seen_ids:
            errors.append(
                "morpheme_spans: duplicate morpheme_occurrence_id %s"
                % morpheme_id
            )
        else:
            seen_ids.add(morpheme_id)
        segment_index = row.get("segment_index")
        if not _valid_offset(segment_index) \
                or not 0 <= segment_index < len(segments):
            errors.append(
                "morpheme_spans: morpheme_spans[%d] segment_index %r is "
                "outside the segment array" % (index, segment_index)
            )
            continue
        if segment_index in seen_segments:
            errors.append(
                "morpheme_spans: segment %d has more than one primary "
                "morpheme ownership row" % segment_index
            )
        else:
            seen_segments.add(segment_index)
        start = row.get("char_start")
        end = row.get("char_end")
        if not _valid_offset(start) or not _valid_offset(end) \
                or not 0 <= start < end <= len(surface):
            errors.append(
                "morpheme_spans: morpheme_spans[%d] has invalid half-open "
                "span [%r,%r) for surface length %d"
                % (index, start, end, len(surface))
            )
            continue
        if _splits_combining_sequence(surface, start) \
                or _splits_combining_sequence(surface, end):
            errors.append(
                "morpheme_spans: morpheme_spans[%d] boundary splits a "
                "combining-mark sequence" % index
            )
        segment = segments[segment_index]
        if not isinstance(segment, dict):
            continue
        if (
            start != segment.get("char_start")
            or end != segment.get("char_end")
        ):
            errors.append(
                "morpheme_spans: morpheme_spans[%d] span [%d,%d) does not "
                "equal referenced segment %d span [%r,%r)"
                % (
                    index,
                    start,
                    end,
                    segment_index,
                    segment.get("char_start"),
                    segment.get("char_end"),
                )
            )


def check_appearance_binding(payload, errors):
    version = _version_tuple(payload)
    appearance = payload.get("appearance")
    if not isinstance(appearance, dict):
        return
    extension_keys = {
        "binding_state",
        "canonical_to_appearance_span_map",
        "displayed_surface",
    }
    active = (
        version is not None and version >= APPEARANCE_BINDING_VERSION
    ) or bool(extension_keys & set(appearance)) \
        or "appearance_binding_hash" in payload
    if not active:
        return
    if version is None or version < APPEARANCE_BINDING_VERSION:
        errors.append(
            "appearance_binding: appearance binding fields require "
            "schema_version 1.2.0 or later"
        )
    for key in extension_keys:
        if key not in appearance:
            errors.append(
                "appearance_binding: appearance missing %r" % key
            )
    if "appearance_binding_hash" not in payload:
        errors.append(
            "appearance_binding: missing top-level appearance_binding_hash"
        )
    if appearance.get("binding_state") != APPEARANCE_BINDING_STATE:
        errors.append(
            "appearance_binding: binding_state %r is not %r"
            % (
                appearance.get("binding_state"),
                APPEARANCE_BINDING_STATE,
            )
        )
    displayed = appearance.get("displayed_surface")
    if not isinstance(displayed, str) or not displayed:
        errors.append(
            "appearance_binding: displayed_surface must be a non-empty string"
        )
        return
    if unicodedata.normalize("NFC", displayed) != displayed:
        errors.append(
            "appearance_binding: displayed_surface must be NFC-normalized"
        )
    want_hash = appearance_binding_hash(payload)
    if payload.get("appearance_binding_hash") != want_hash:
        errors.append(
            "appearance_binding: appearance_binding_hash %r does not match "
            "the canonical binding hash %s"
            % (payload.get("appearance_binding_hash"), want_hash)
        )

    appearance_id = appearance.get("appearance_id")
    universe_row = _appearance_universe().get(appearance_id)
    if universe_row is None:
        errors.append(
            "appearance_binding: appearance_id %r is absent from "
            "qamus/lattice/example-ayah-universe.jsonl" % appearance_id
        )
    else:
        if universe_row.get("displayed_surface") != displayed:
            errors.append(
                "appearance_binding: displayed_surface %r does not equal "
                "authoritative appearance %s surface %r"
                % (
                    displayed,
                    appearance_id,
                    universe_row.get("displayed_surface"),
                )
            )
        if universe_row.get("crosswalk") != "resolved":
            errors.append(
                "appearance_binding: appearance %s crosswalk is %r, not "
                "resolved"
                % (appearance_id, universe_row.get("crosswalk"))
            )
        occurrence_id = payload.get("occurrence_id")
        parts = str(occurrence_id or "").split(":")
        canonical_loc = ":".join(parts[1:]) if len(parts) == 4 else None
        if universe_row.get("canonical_loc") != canonical_loc:
            errors.append(
                "appearance_binding: appearance %s canonical_loc %r does "
                "not bind occurrence_id %r"
                % (
                    appearance_id,
                    universe_row.get("canonical_loc"),
                    occurrence_id,
                )
            )
        expected_page_id = "entry:%s" % universe_row.get("entry_id")
        if appearance.get("page_kind") != "entry" \
                or appearance.get("page_id") != expected_page_id:
            errors.append(
                "appearance_binding: appearance %s must bind page_kind "
                "'entry' and page_id %r"
                % (appearance_id, expected_page_id)
            )
        if universe_row.get("appearance_index_entry_linked") is False:
            projection_for_links = payload.get("projection")
            links = (
                projection_for_links.get("entry_links", [])
                if isinstance(projection_for_links, dict)
                else []
            )
            entry_ids = {
                row.get("entry_id")
                for row in links
                if isinstance(row, dict)
            }
            if universe_row.get("entry_id") in entry_ids:
                errors.append(
                    "appearance_binding: context-page entry %s cannot become "
                    "occurrence entry identity"
                    % universe_row.get("entry_id")
                )

    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    segments = projection.get("segments")
    span_map = appearance.get("canonical_to_appearance_span_map")
    if not isinstance(segments, list) or not isinstance(span_map, list):
        errors.append(
            "appearance_binding: canonical_to_appearance_span_map must be "
            "an array paired with projection.segments"
        )
        return
    if len(span_map) != len(segments):
        errors.append(
            "appearance_binding: span map has %d rows for %d canonical "
            "segments" % (len(span_map), len(segments))
        )
    morphemes_by_segment = {
        row.get("segment_index"): row
        for row in projection.get("morpheme_spans") or []
        if isinstance(row, dict)
    }
    appearance_cursor = 0
    for index, row in enumerate(span_map):
        if not isinstance(row, dict):
            errors.append(
                "appearance_binding: span map row %d must be an object"
                % index
            )
            continue
        if set(row) != REQUIRED_APPEARANCE_MAP_KEYS:
            errors.append(
                "appearance_binding: span map row %d keys %s do not equal "
                "the closed 1.2.0 shape %s"
                % (
                    index,
                    sorted(row),
                    sorted(REQUIRED_APPEARANCE_MAP_KEYS),
                )
            )
        if row.get("segment_index") != index:
            errors.append(
                "appearance_binding: span map row %d carries "
                "segment_index %r" % (index, row.get("segment_index"))
            )
        if index >= len(segments) or not isinstance(segments[index], dict):
            continue
        segment = segments[index]
        canonical_start = row.get("canonical_char_start")
        canonical_end = row.get("canonical_char_end")
        if (
            canonical_start != segment.get("char_start")
            or canonical_end != segment.get("char_end")
        ):
            errors.append(
                "appearance_binding: span map row %d canonical span "
                "[%r,%r) does not equal segment span [%r,%r)"
                % (
                    index,
                    canonical_start,
                    canonical_end,
                    segment.get("char_start"),
                    segment.get("char_end"),
                )
            )
        local_start = row.get("appearance_char_start")
        local_end = row.get("appearance_char_end")
        if not _valid_offset(local_start) or not _valid_offset(local_end) \
                or not 0 <= local_start < local_end <= len(displayed):
            errors.append(
                "appearance_binding: span map row %d has invalid local span "
                "[%r,%r)" % (index, local_start, local_end)
            )
            continue
        if local_start != appearance_cursor:
            errors.append(
                "appearance_binding: span map row %d starts at %d, expected "
                "%d for gap-free local tiling"
                % (index, local_start, appearance_cursor)
            )
        if _splits_combining_sequence(displayed, local_start) \
                or _splits_combining_sequence(displayed, local_end):
            errors.append(
                "appearance_binding: span map row %d splits a combining-mark "
                "sequence" % index
            )
        appearance_cursor = local_end
        morpheme = morphemes_by_segment.get(index)
        expected_morpheme_id = (
            morpheme.get("morpheme_occurrence_id")
            if isinstance(morpheme, dict)
            else None
        )
        if row.get("morpheme_occurrence_id") != expected_morpheme_id:
            errors.append(
                "identity_parity: span map row %d morpheme identity %r does "
                "not equal the canonical segment ownership %r"
                % (
                    index,
                    row.get("morpheme_occurrence_id"),
                    expected_morpheme_id,
                )
            )
        if displayed == projection.get("surface"):
            if (
                local_start != canonical_start
                or local_end != canonical_end
                or displayed[local_start:local_end]
                != segment.get("surface")
            ):
                errors.append(
                    "appearance_binding: identical canonical and displayed "
                    "surfaces require an identity span map at row %d" % index
                )
        else:
            canonical_letters = _letter_ownership_signature(
                segment.get("surface")
            )
            appearance_letters = _letter_ownership_signature(
                displayed[local_start:local_end]
            )
            if canonical_letters != appearance_letters:
                errors.append(
                    "appearance_binding: span map row %d changes letter "
                    "ownership from canonical %r to appearance %r"
                    % (index, canonical_letters, appearance_letters)
                )
    if appearance_cursor != len(displayed):
        errors.append(
            "appearance_binding: local span map ends at %d, displayed "
            "surface length is %d" % (appearance_cursor, len(displayed))
        )

    occurrence_row = _occurrence_universe().get(payload.get("occurrence_id"))
    if occurrence_row is None:
        errors.append(
            "appearance_binding: occurrence_id %r is absent from the "
            "occurrence universe" % payload.get("occurrence_id")
        )
    else:
        expected_ids = set(occurrence_row.get("appearance_ids") or [])
        reverse_rows = (
            (payload.get("reverse_links") or {})
            .get("occurrence_to_appearances") or []
        )
        for index, row in enumerate(reverse_rows):
            if not isinstance(row, dict) or row.get("page_kind") != "entry":
                continue
            authoritative = _appearance_universe().get(
                row.get("appearance_id")
            )
            expected_page = (
                "entry:%s" % authoritative.get("entry_id")
                if isinstance(authoritative, dict)
                else None
            )
            if authoritative is None or row.get("page_id") != expected_page:
                errors.append(
                    "appearance_binding: reverse entry appearance %d does "
                    "not bind its authoritative page_id"
                    % index
                )
        actual_entry_ids = {
            row.get("appearance_id")
            for row in reverse_rows
            if isinstance(row, dict) and row.get("page_kind") == "entry"
        }
        if actual_entry_ids != expected_ids:
            errors.append(
                "appearance_binding: reverse entry appearance set %s does "
                "not equal authoritative set %s"
                % (sorted(actual_entry_ids), sorted(expected_ids))
            )
        occurrence_parts = str(payload.get("occurrence_id") or "").split(":")
        canonical_loc = (
            ":".join(occurrence_parts[1:])
            if len(occurrence_parts) == 4
            else ""
        )
        reader_id = "app:reader:%s" % canonical_loc
        allowed_ids = expected_ids | {reader_id}
        actual_ids = {
            row.get("appearance_id")
            for row in reverse_rows
            if isinstance(row, dict)
        }
        if actual_ids != allowed_ids:
            errors.append(
                "appearance_binding: reverse appearance set %s does not "
                "equal authoritative entry set plus reader %s"
                % (sorted(actual_ids), sorted(allowed_ids))
            )
        reader_rows = [
            row
            for row in reverse_rows
            if isinstance(row, dict)
            and row.get("appearance_id") == reader_id
        ]
        expected_reader_page = "reader:%s" % ":".join(
            occurrence_parts[1:3]
        )
        if len(reader_rows) != 1 or (
            reader_rows[0].get("page_kind") != "reader"
            or reader_rows[0].get("page_id") != expected_reader_page
        ):
            errors.append(
                "appearance_binding: reader reverse declaration must be "
                "exactly %s on %s" % (reader_id, expected_reader_page)
            )


def check_identity_parity(payload, errors):
    version = _version_tuple(payload)
    if version is None or version < APPEARANCE_BINDING_VERSION:
        return
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    segments = projection.get("segments")
    cards = projection.get("hover_cards")
    if not isinstance(segments, list) or not isinstance(cards, list):
        errors.append(
            "identity_parity: segments and hover_cards must be arrays"
        )
        return
    if len(cards) != len(segments):
        errors.append(
            "identity_parity: %d hover cards do not cover %d segments"
            % (len(cards), len(segments))
        )
    morphemes_by_segment = {
        row.get("segment_index"): row
        for row in projection.get("morpheme_spans") or []
        if isinstance(row, dict)
    }
    for index, segment in enumerate(segments):
        if index >= len(cards):
            break
        card = cards[index]
        if not isinstance(segment, dict) or not isinstance(card, dict):
            errors.append(
                "identity_parity: segment and hover card %d must be objects"
                % index
            )
            continue
        if card.get("segment_index") != index:
            errors.append(
                "identity_parity: hover card %d carries segment_index %r"
                % (index, card.get("segment_index"))
            )
        morpheme = morphemes_by_segment.get(index)
        expected_morpheme_id = (
            morpheme.get("morpheme_occurrence_id")
            if isinstance(morpheme, dict)
            else None
        )
        if card.get("morpheme_occurrence_id") != expected_morpheme_id:
            errors.append(
                "identity_parity: hover card %d morpheme identity %r does "
                "not equal segment ownership %r"
                % (
                    index,
                    card.get("morpheme_occurrence_id"),
                    expected_morpheme_id,
                )
            )
        if card.get("component_surface") != segment.get("surface"):
            errors.append(
                "identity_parity: hover card %d component_surface %r does "
                "not equal segment surface %r"
                % (
                    index,
                    card.get("component_surface"),
                    segment.get("surface"),
                )
            )


def check_unresolved_and_rootless(payload, errors):
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    unresolved = projection.get("unresolved")
    certification = projection.get("certification") or {}
    for i, seg in enumerate(projection.get("segments") or []):
        if not isinstance(seg, dict):
            continue
        sem = seg.get("semantic_class")
        renderer = seg.get("renderer_class")
        if sem == "unresolved" and renderer != "qg-unresolved":
            errors.append(
                "unresolved_colour: segments[%d] is unresolved but carries "
                "renderer_class %r — unresolved is never colour-guessed; the "
                "only legal class is 'qg-unresolved' (contract §10.2)"
                % (i, renderer))
        if renderer == "qg-unresolved" and sem != "unresolved":
            errors.append(
                "unresolved_colour: segments[%d] carries qg-unresolved but "
                "semantic_class %r — the neutral class is reserved for the "
                "unresolved state (contract §10.2)" % (i, sem))
    if isinstance(unresolved, dict):
        if not (unresolved.get("message") or "").strip():
            errors.append("unresolved_honesty: unresolved state without a "
                          "learner-facing message (contract §10.2)")
        if certification.get("status") != "unresolved":
            errors.append(
                "unresolved_honesty: projection.unresolved is set but "
                "certification.status is %r — an unresolved state can never "
                "certify (contract §10.2)" % certification.get("status"))
    if projection.get("kind") == "particle_clitic_word" \
            and projection.get("root") in (None, ""):
        pedagogy = projection.get("rootless_pedagogy")
        if not (isinstance(pedagogy, str) and pedagogy.strip()):
            errors.append(
                "rootless_pedagogy: rootless particle payload has no "
                "rootless_pedagogy — rootlessness is taught, never blank "
                "(contract §10.1)")


def check_candidate_public_plane(payload, errors):
    version = _version_tuple(payload)
    if version is None or version < APPEARANCE_BINDING_VERSION:
        return
    appearance = payload.get("appearance")
    projection = payload.get("projection")
    if not isinstance(appearance, dict) or not isinstance(projection, dict):
        return
    if appearance.get("binding_state") != APPEARANCE_BINDING_STATE:
        return
    certification = projection.get("certification")
    if not isinstance(certification, dict):
        errors.append(
            "candidate_public_plane: certification must be an object"
        )
        return
    plane = certification.get("plane")
    if not isinstance(plane, dict):
        errors.append(
            "candidate_public_plane: certification.plane must be an object"
        )
        return
    if set(plane) != V12_CERTIFICATION_PLANE_KEYS:
        errors.append(
            "candidate_public_plane: certification.plane keys %s do not "
            "equal the closed 1.2.0 shape %s"
            % (
                sorted(plane),
                sorted(V12_CERTIFICATION_PLANE_KEYS),
            )
        )
    for key, state in plane.items():
        if state not in V12_CERTIFICATION_PLANE_STATES:
            errors.append(
                "candidate_public_plane: certification.plane[%r]=%r is "
                "not one of %s"
                % (
                    key,
                    state,
                    sorted(V12_CERTIFICATION_PLANE_STATES),
                )
            )
    for index, row in enumerate(projection.get("entry_links") or []):
        if not isinstance(row, dict):
            continue
        if row.get("relation_kind") in {"certified_entry", "certified_sense"} \
                or row.get("link_state") == "certified" \
                or row.get("sense_state") == "certified":
            errors.append(
                "candidate_public_plane: entry_links[%d] carries a certified "
                "edge or sense while certification.plane.entry_links is %r"
                % (index, plane.get("entry_links"))
            )
    if projection.get("public_projection_eligible") is not False:
        errors.append(
            "candidate_public_plane: candidate capability handoff must set "
            "public_projection_eligible to false"
        )
    if certification.get("status") != "unresolved":
        errors.append(
            "candidate_public_plane: candidate capability handoff with "
            "unresolved facts must retain certification.status unresolved"
        )
    unresolved = projection.get("unresolved")
    if not isinstance(unresolved, dict):
        errors.append(
            "candidate_public_plane: candidate handoff requires an explicit "
            "unresolved object"
        )
    if projection.get("whole_word_gloss") != "unresolved":
        errors.append(
            "candidate_public_plane: unresolved contextual meaning or "
            "translation requires whole_word_gloss 'unresolved'"
        )
    if projection.get("learner_explanation") != UNRESOLVED_PRIMARY_TEXT:
        errors.append(
            "candidate_public_plane: learner_explanation must remain neutral"
        )
    if projection.get("root") is not None:
        errors.append(
            "candidate_public_plane: unresolved root must remain null"
        )
    for index, segment in enumerate(projection.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        expected = {
            "semantic_class": "unresolved",
            "renderer_class": "qg-unresolved",
            "gloss": "unresolved",
            "sarf_note": UNRESOLVED_PRIMARY_TEXT,
            "nahw_note": UNRESOLVED_PRIMARY_TEXT,
        }
        for key, value in expected.items():
            if segment.get(key) != value:
                errors.append(
                    "candidate_public_plane: segment %d %s=%r must be %r"
                    % (index, key, segment.get(key), value)
                )
    for index, card in enumerate(projection.get("hover_cards") or []):
        if not isinstance(card, dict):
            continue
        for key in (
            "particle_identity", "contextual_function", "governor",
            "governed_expression", "scope", "attachment", "entry_link",
        ):
            if card.get(key) is not None:
                errors.append(
                    "candidate_public_plane: hover card %d primary field %s "
                    "must be null while analysis is unresolved"
                    % (index, key)
                )
        expected = {
            "contextual_gloss": "unresolved",
            "sarf_note": UNRESOLVED_PRIMARY_TEXT,
            "nahw_note": UNRESOLVED_PRIMARY_TEXT,
            "reason": UNRESOLVED_PRIMARY_TEXT,
        }
        for key, value in expected.items():
            if card.get(key) != value:
                errors.append(
                    "candidate_public_plane: hover card %d %s=%r must be %r"
                    % (index, key, card.get(key), value)
                )
        alternatives = card.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            errors.append(
                "candidate_public_plane: hover card %d must preserve "
                "candidate analyses only under non-empty alternatives"
                % index
            )
        else:
            for alternative in alternatives:
                if not isinstance(alternative, str) \
                        or not alternative.startswith("Candidate only:"):
                    errors.append(
                        "candidate_public_plane: hover card %d alternative "
                        "%r lacks the explicit 'Candidate only:' marker"
                        % (index, alternative)
                    )


def check_geometry_evidence(payload, errors):
    version = _version_tuple(payload)
    if version is None or version < APPEARANCE_BINDING_VERSION:
        return
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        return
    refs = projection.get("evidence_refs")
    if not isinstance(refs, list):
        errors.append(
            "geometry_evidence: evidence_refs must be an array"
        )
        return
    occurrence_id = payload.get("occurrence_id")
    if occurrence_id != "quran:61:5:4":
        errors.append(
            "geometry_evidence: schema 1.2.0 pilot validator has no "
            "registered geometry resolver for occurrence %r; preserve "
            "candidate ineligibility and extend the validator with its "
            "producer before handoff" % occurrence_id
        )
        return
    required = {
        "fact:p007geo:61_5_4:geom": "attachment_geometry",
        "fact:p007geo:61_5_4:recon": "surface_reconstruction_nfc",
        "fact:p007geo:61_5_4:bound": "token_host_boundary",
    }
    missing = sorted(set(required) - set(refs))
    if missing:
        errors.append(
            "geometry_evidence: missing authoritative geometry fact ids %s"
            % missing
        )
        return
    facts = _p007_geometry_facts()
    resolved = {}
    for fact_id, fact_type in required.items():
        fact = facts.get(fact_id)
        if not isinstance(fact, dict) or fact.get("fact_type") != fact_type:
            errors.append(
                "geometry_evidence: %s does not resolve to fact_type %s"
                % (fact_id, fact_type)
            )
            continue
        if (fact.get("source_address") or {}).get("address") != occurrence_id:
            errors.append(
                "geometry_evidence: %s source address does not bind %s"
                % (fact_id, occurrence_id)
            )
        resolved[fact_type] = fact.get("fact_value") or {}
    if set(resolved) != set(required.values()):
        return
    surface = projection.get("surface")
    geometry = resolved["attachment_geometry"]
    reconstruction = resolved["surface_reconstruction_nfc"]
    boundary = resolved["token_host_boundary"]
    if (
        geometry.get("surface_nfc") != surface
        or reconstruction.get("surface_nfc") != surface
        or boundary.get("surface_nfc") != surface
    ):
        errors.append(
            "geometry_evidence: resolved fact surfaces do not equal "
            "projection.surface"
        )
    segments = projection.get("segments")
    if not isinstance(segments, list) or len(segments) != 2:
        errors.append(
            "geometry_evidence: current 61:5:4 facts support exactly the "
            "opening component and host-remainder boundary, not an inner "
            "three-segment carve"
        )
        return
    char_span = geometry.get("char_span") or {}
    boundary_index = boundary.get("boundary_char_index")
    if (
        segments[0].get("char_start") != char_span.get("start")
        or segments[0].get("char_end") != char_span.get("end")
        or segments[0].get("surface") != geometry.get("component_surface")
        or boundary_index != segments[0].get("char_end")
        or segments[1].get("char_start") != boundary_index
        or segments[1].get("char_end") != len(surface)
        or segments[1].get("surface")
        != boundary.get("host_remainder_surface")
    ):
        errors.append(
            "geometry_evidence: primary segments exceed or disagree with "
            "the resolved lam and host-remainder geometry"
        )
    morphemes = projection.get("morpheme_spans") or []
    if len(morphemes) != 1 \
            or morphemes[0].get("morpheme_occurrence_id") \
            != "mocc:p007:61:5:4":
        errors.append(
            "geometry_evidence: only the repository-backed "
            "mocc:p007:61:5:4 ownership may bind the opening span"
        )


def check_provenance(payload, errors):
    provenance = payload.get("provenance")
    projection = payload.get("projection")
    if not isinstance(provenance, dict):
        errors.append("provenance: provenance must be an object")
        return
    klass = provenance.get("provenance_class")
    if klass not in PROVENANCE_CLASSES:
        errors.append("provenance: provenance_class %r not in %s"
                      % (klass, sorted(PROVENANCE_CLASSES)))
    if isinstance(projection, dict):
        status = (projection.get("certification") or {}).get("status")
        if status not in CERT_STATUSES:
            errors.append("provenance: certification.status %r not in %s"
                          % (status, sorted(CERT_STATUSES)))
        if status == "certified" and klass != "certified":
            errors.append(
                "provenance: certification.status 'certified' under "
                "provenance_class %r — only certified provenance may claim "
                "certification (contract §8)" % klass)
        if status == "certified" and not projection.get("evidence_refs"):
            errors.append(
                "provenance: certified payload without evidence_refs — "
                "certification always cites its internal evidence ids "
                "(contract §8)")


def check_no_server_paths(payload, errors):
    blob = json.dumps(payload, ensure_ascii=False)
    hit = SERVER_PATH_RE.search(blob)
    if hit:
        errors.append(
            "server_paths: payload carries a server filesystem path %r — "
            "internal ids only ever cross the boundary (RM-09, contract §8)"
            % hit.group(0))


def check_public_boundary(payload, errors):
    version = _version_tuple(payload)
    for path, key in _all_key_paths(payload):
        if key.casefold() in FORBIDDEN_PUBLIC_KEYS:
            errors.append(
                "public_boundary: forbidden public key %r at %s"
                % (key, path)
            )
            continue
        for view in _key_scan_views(path, key):
            source_hit = EXTERNAL_OR_PRIVATE_SOURCE_RE.search(view)
            workflow_hit = (
                V12_PRIVATE_WORKFLOW_RE.search(view)
                if version is not None
                and version >= APPEARANCE_BINDING_VERSION
                else None
            )
            if source_hit or workflow_hit:
                hit = source_hit or workflow_hit
                errors.append(
                    "public_boundary: forbidden source/private key %r at "
                    "%s (matched %r)"
                    % (key, path, hit.group(0))
                )
                break
    for value in _all_strings(payload):
        source_hit = EXTERNAL_OR_PRIVATE_SOURCE_RE.search(value)
        workflow_hit = (
            V12_PRIVATE_WORKFLOW_RE.search(value)
            if version is not None
            and version >= APPEARANCE_BINDING_VERSION
            else None
        )
        if source_hit or workflow_hit:
            hit = source_hit or workflow_hit
            errors.append(
                "public_boundary: payload carries external/private-source or "
                "private-workflow "
                "label %r" % hit.group(0)
            )
    for field, text in _learner_fields(
        payload.get("projection")
        if isinstance(payload.get("projection"), dict)
        else {}
    ):
        if not isinstance(text, str):
            continue
        if version is not None and version >= APPEARANCE_BINDING_VERSION:
            hit = V12_PRIVATE_WORKFLOW_RE.search(text)
            if hit:
                errors.append(
                    "public_boundary: learner field %r carries private "
                    "workflow prose %r" % (field, hit.group(0))
                )


def check_machine_topology(payload, errors):
    candidates = list(_all_strings(payload))
    for path, key in _all_key_paths(payload):
        candidates.extend((path, key))
    for value in candidates:
        for pattern in MACHINE_TOPOLOGY_PATTERNS:
            hit = pattern.search(value)
            if hit:
                errors.append(
                    "machine_topology: payload carries private path or "
                    "machine topology %r" % hit.group(0)
                )
                break


def check_p007_authority(payload, errors):
    """Bind p007 handoff samples to the current canonical occurrence plane."""
    if not str(payload.get("artifact_id") or "").startswith("artifact:p007:"):
        return
    projections = [
        json.loads(line)
        for line in (P007_DIR / "projections.jsonl").read_text(
            encoding="utf-8").splitlines()
        if line.strip()
    ]
    occurrence_id = payload.get("occurrence_id")
    source = next((row for row in projections
                   if row.get("projection", {}).get("occurrence_id") ==
                   occurrence_id), None)
    if source is None:
        errors.append("p007_authority: occurrence is absent from canonical "
                      "p007 projections")
        return
    projection = payload.get("projection") or {}
    canonical = source["projection"]
    if payload.get("candidate_only") is not True \
            or payload.get("deliverable") is not False:
        errors.append("p007_authority: p007 handoff samples must remain "
                      "candidate_only and non-deliverable")
    if payload.get("source_projection_hash") != source.get("projection_hash"):
        errors.append("p007_authority: source projection hash is stale or "
                      "missing")
    if unicodedata.normalize("NFC", projection.get("surface") or "") != \
            unicodedata.normalize("NFC", canonical.get("surface") or ""):
        errors.append("p007_authority: written surface differs from the "
                      "canonical occurrence projection")
    canonical_segments = []
    cursor = 0
    for row in canonical.get("segments") or []:
        surface = unicodedata.normalize("NFC", row.get("surface") or "")
        canonical_segments.append({
            "surface": surface,
            "char_start": cursor,
            "char_end": cursor + len(surface),
            "semantic_class": row.get("role"),
            "renderer_class": row.get("colour_class"),
        })
        cursor += len(surface)
    projected_segments = [
        {key: row.get(key) for key in (
            "surface", "char_start", "char_end", "semantic_class",
            "renderer_class")}
        for row in projection.get("segments") or []
    ]
    if projected_segments != canonical_segments:
        errors.append("p007_authority: colour/span segments fork from the "
                      "canonical occurrence projection")
    expected_plane = canonical.get("certification_plane") or {}
    certification = projection.get("certification") or {}
    if certification.get("plane") != expected_plane:
        errors.append("p007_authority: certification plane differs from "
                      "canonical p007 posture")
    unresolved_dependencies = canonical.get("unresolved_dependencies") or []
    unresolved = projection.get("unresolved") or {}
    if unresolved_dependencies:
        if certification.get("status") != "unresolved":
            errors.append("p007_authority: unresolved canonical dependencies "
                          "were presented as settled")
        if unresolved.get("dependencies") != unresolved_dependencies:
            errors.append("p007_authority: unresolved dependency set drifted")
    facts = [
        json.loads(line)
        for line in (P007_DIR / "typed-facts.jsonl").read_text(
            encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_fact_ids = sorted(
        fact["fact_id"] for fact in facts
        if fact.get("fact_type") == "particle_rootlessness"
        or any(span.get("quran_loc") == occurrence_id
               for span in fact.get("surface_spans") or [])
    )
    expected_hover = copy.deepcopy((canonical.get("hover_cards") or [])[0])
    expected_hover["component_surface"] = unicodedata.normalize(
        "NFC", expected_hover.get("component_surface") or "")
    expected_hover.setdefault("particle_identity", {}).pop("sense", None)
    expected_hover["fact_ids"] = expected_fact_ids
    if projection.get("hover_cards") != [expected_hover]:
        errors.append("p007_authority: hover content or fact trace forked "
                      "from the canonical occurrence projection")
    for card in projection.get("hover_cards") or []:
        if "relation" in (card.get("governor") or {}):
            errors.append("p007_authority: uncompared governor relation was "
                          "rendered in public hover")
        identity = card.get("particle_identity") or {}
        if expected_plane.get("sense") != "certified" \
                and identity.get("sense") is not None:
            errors.append("p007_authority: candidate sense was rendered as "
                          "settled identity")
    if expected_plane.get("sense") != "certified":
        for link in projection.get("entry_links") or []:
            if link.get("sense_id") is not None:
                errors.append("p007_authority: candidate sense was emitted "
                              "as a website sense link")
    source_appearance_ids = {
        row.get("appearance_id") for row in source.get("appearances") or []
    }
    payload_appearance_rows = (
        (payload.get("reverse_links") or {}).get(
            "occurrence_to_appearances") or []
    )
    payload_appearance_ids = {
        row.get("appearance_id") for row in payload_appearance_rows
    }
    if len(payload_appearance_rows) != len(payload_appearance_ids):
        errors.append("p007_authority: duplicate reverse appearance id")
    if payload_appearance_ids != source_appearance_ids:
        errors.append("p007_authority: reverse appearance set is incomplete "
                      "or contains page-local inventions")
    universe = {
        row["appearance_id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "qamus" / "lattice" /
                          "example-ayah-universe.jsonl").read_text(
                              encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    reverse_rows = {
        row.get("appearance_id"): row
        for row in (payload.get("reverse_links") or {}).get(
            "occurrence_to_appearances") or []
    }
    for appearance_id in source_appearance_ids:
        expected = universe.get(appearance_id)
        actual = reverse_rows.get(appearance_id) or {}
        if expected is None or actual.get("page_id") != \
                "entry:%s" % expected.get("entry_id") \
                or actual.get("page_kind") != "entry":
            errors.append("p007_authority: appearance %s page binding "
                          "differs from the canonical appearance universe"
                          % appearance_id)
    chosen = payload.get("appearance") or {}
    chosen_id = chosen.get("appearance_id")
    chosen_source = universe.get(chosen_id)
    if chosen_id not in source_appearance_ids or chosen_source is None:
        errors.append("p007_authority: selected envelope appearance is not "
                      "an authoritative occurrence appearance")
    else:
        expected_local = {
            "selected_highlight": bool(chosen_source.get("selected")),
            "entry_relationship": (
                "entry_relation" if
                chosen_source.get("appearance_index_entry_linked") else
                "context_only"
            ),
            "focus": "example-card",
            "navigation": [],
        }
        if chosen.get("page_id") != "entry:%s" % chosen_source["entry_id"] \
                or chosen.get("page_kind") != "entry" \
                or chosen.get("page_local") != expected_local:
            errors.append("p007_authority: selected appearance page/local "
                          "binding forks from the canonical universe")
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from certify_typed_fact import TypedFactCertificationStore
        store = TypedFactCertificationStore(P007_DIR / "certification")
        trail_errors = store.validate_trail()
        status_by_id = store.status_by_id() if not trail_errors else {}
    finally:
        if str(ROOT / "tools") in sys.path:
            sys.path.remove(str(ROOT / "tools"))
    if trail_errors:
        errors.append("p007_authority: certification trail is invalid")
    fact_refs = sorted(ref for ref in projection.get("evidence_refs") or []
                       if str(ref).startswith("fact:"))
    if fact_refs != expected_fact_ids:
        errors.append("p007_authority: evidence fact set is not the exact "
                      "canonical occurrence dependency set")
    for fact_id in fact_refs:
        if status_by_id.get(fact_id) != "certified":
            errors.append("p007_authority: evidence fact %s is not currently "
                          "certified" % fact_id)
    segment_rows = projection.get("segments") or []
    clitic_fact_ids = sorted((segment_rows[0] if segment_rows else {}).get(
        "fact_ids") or [])
    hover_fact_ids = sorted((projection.get("hover_cards") or [{}])[0].get(
        "fact_ids") or [])
    if clitic_fact_ids != expected_fact_ids \
            or hover_fact_ids != clitic_fact_ids:
        errors.append("p007_authority: hover component lacks the exact "
                      "fact-id trace carried by its colour segment")


def validate_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    check_envelope(payload, errors)
    check_hash_fork(payload, errors)
    check_page_local_whitelist(payload, errors)
    check_entry_links(payload, errors)
    check_reverse_entry_parity(payload, errors)
    check_prose_leak(payload, errors)
    check_segment_reconstruction(payload, errors)
    check_morpheme_spans(payload, errors)
    check_appearance_binding(payload, errors)
    check_identity_parity(payload, errors)
    check_unresolved_and_rootless(payload, errors)
    check_candidate_public_plane(payload, errors)
    check_geometry_evidence(payload, errors)
    check_provenance(payload, errors)
    check_no_server_paths(payload, errors)
    check_p007_authority(payload, errors)
    check_public_boundary(payload, errors)
    check_machine_topology(payload, errors)
    return errors


# --------------------------------------------------------------------------- #
# red-first self-test
# --------------------------------------------------------------------------- #

def _green_payload() -> dict:
    projection = {
        "occurrence_id": "quran:2:34:5",
        "surface": "لِءَادَمَ",
        "normalization": "NFC",
        "kind": "particle_clitic_word",
        "segments": [
            {"segment_index": 0, "surface": "لِ", "char_start": 0,
             "char_end": 2, "semantic_class": "jarr_clitic_lam",
             "renderer_class": "qg-particle-jarr-clitic",
             "gloss": "for / to",
             "sarf_note": "An indeclinable tool word written joined to its host.",
             "nahw_note": "It governs the next word, pulling it into the jarr state."},
            {"segment_index": 1, "surface": "ءَادَمَ", "char_start": 2,
             "char_end": 9, "semantic_class": "proper_name_majrur",
             "renderer_class": "qg-proper-noun",
             "gloss": "Adam", "sarf_note": None, "nahw_note": None},
        ],
        "whole_word_gloss": "to Adam",
        "learner_explanation": "The little lam means 'to'; the rest is the name Adam.",
        "entry_links": [
            {"entry_id": "b10a1ee04666", "sense_id": "li-sense-2",
             "relation_kind": "clitic_component_of_entry",
             "segment_index": 0},
        ],
        "entry_link_state": "linked",
        "morpheme_spans": [
            {"morpheme_occurrence_id": "morph:2:34:5:li",
             "segment_index": 0, "char_start": 0, "char_end": 2},
        ],
        "root": None,
        "rootless_pedagogy": "This little lam is not built from a "
                             "three-letter root - it is an indeclinable tool "
                             "word (a particle).",
        "hover_cards": [
            {"component_surface": "لِ", "contextual_gloss": "to Adam",
             "particle_identity": {"headword": "لَـ / لِـ",
                                   "entry_id": "b10a1ee04666",
                                   "sense": "li-sense-2"},
             "contextual_function": "preposition (jarr)",
             "sarf_note": "Indeclinable tool word attached to its host.",
             "nahw_note": "Governs the following name in the jarr state.",
             "governor": {"loc": "quran:2:34:4", "surface": "اسجدوا",
                          "relation": "muta-alliq"},
             "governed_expression": "آدم", "scope": None,
             "attachment": {"host": "ءادم",
                            "boundary": "clitic letter | host"},
             "alternatives": [], "reason": "both reviewers agreed",
             "unresolved": None,
             "entry_link": "/qamus/entry/b10a1ee04666"},
        ],
        "unresolved": None,
        "certification": {"status": "certified",
                          "plane": {"segmentation": "certified",
                                    "function": "certified"}},
        "evidence_refs": ["two-vote-artifact:quran_2_34_5:selftest"],
    }
    return {
        "schema": PAYLOAD_SCHEMA,
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:2:34:5",
        "artifact_id": "artifact:selftest:2:34:5",
        "appearance": {
            "appearance_id": "app:selftest:reader",
            "page_id": "reader:2:34",
            "page_kind": "reader",
            "page_local": {"selected_highlight": False, "focus": None},
        },
        "projection": projection,
        "projection_hash": projection_hash(projection),
        "reverse_links": {
            "occurrence_to_appearances": [
                {"appearance_id": "app:selftest:reader",
                 "page_id": "reader:2:34", "page_kind": "reader",
                 "projection_hash": projection_hash(projection)},
                {"appearance_id": "app:selftest:entry",
                 "page_id": "entry:b10a1ee04666", "page_kind": "entry",
                 "projection_hash": projection_hash(projection)},
            ],
            "entry_to_occurrences": [
                {"entry_id": "b10a1ee04666",
                 "occurrences": [
                     {"occurrence_id": "quran:2:34:5",
                      "surface": "لِءَادَمَ", "loc": "2:34:5",
                      "page_refs": ["reader:2:34", "entry:b10a1ee04666"]},
                 ]},
            ],
        },
        "provenance": {
            "provenance_class": "certified",
            "built_by": "tools.validate_website_payload.selftest v1",
            "source_refs": ["two-vote-artifact:quran_2_34_5:selftest"],
        },
    }


def _green_v12_payload() -> dict:
    path = (
        SAMPLES_DIR
        / "multi_entry_liqawmihi_61_5_4.payload.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash_payload(payload: dict) -> None:
    projection = payload.get("projection")
    if isinstance(projection, dict):
        payload["projection_hash"] = projection_hash(projection)
        reverse = payload.get("reverse_links")
        if isinstance(reverse, dict):
            for row in reverse.get("occurrence_to_appearances") or []:
                if isinstance(row, dict):
                    row["projection_hash"] = payload["projection_hash"]
    if "appearance_binding_hash" in payload:
        payload["appearance_binding_hash"] = appearance_binding_hash(payload)


def _self_test() -> int:
    failures = []

    def expect_green(name, payload):
        errs = validate_payload(payload)
        ok = not errs
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            for err in errs:
                print("   ", err)
            failures.append(name)

    def expect_red(name, payload, needle):
        errs = validate_payload(payload)
        ok = any(needle in err for err in errs)
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            print("    expected an error containing %r, got: %s"
                  % (needle, errs))
            failures.append(name)

    expect_green("green: full contract-shaped payload passes", _green_payload())
    expect_green(
        "green: 1.2 appearance-bound candidate pilot passes",
        _green_v12_payload(),
    )

    # red 1 — missing entry links while claiming linked
    bad = _green_payload()
    bad["projection"]["entry_links"] = []
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: linked state with empty entry_links is missing entry "
               "links", bad, "entry_links")

    # red 2 — missing entry_link_state entirely
    bad = _green_payload()
    del bad["projection"]["entry_link_state"]
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: undeclared entry_link_state", bad, "entry_link_state")

    # red 3 — Arabic i'rab prose leaking into a learner field
    bad = _green_payload()
    bad["projection"]["hover_cards"][0]["nahw_note"] = \
        "اسم مجرور وعلامة جره الفتحة"
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: i'rab formula in a learner field is a prose leak",
               bad, "prose_leak")

    # red 4 — hash fork: fact plane mutated without re-hashing
    bad = _green_payload()
    bad["projection"]["whole_word_gloss"] = "for Adam"
    expect_red("red: mutated fact plane with stale hash is a hash fork",
               bad, "hash_fork")

    # red 5 — hash fork across appearances of one occurrence
    bad = _green_payload()
    bad["reverse_links"]["occurrence_to_appearances"][1][
        "projection_hash"] = "0" * 64
    expect_red("red: appearance carrying a different hash forks the "
               "occurrence", bad, "hash_fork")

    # red 6 — non-whitelist page-local metadata
    bad = _green_payload()
    bad["appearance"]["page_local"]["custom_banner"] = True
    expect_red("red: non-whitelist page-local metadata",
               bad, "page_local_whitelist")

    # red 7 — presentation key smuggled into the hashed projection
    bad = _green_payload()
    bad["projection"]["selected_highlight"] = True
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: presentation key smuggled into the projection",
               bad, "page_local_whitelist")

    # red 8 — segment reconstruction failure (dropped letter)
    bad = _green_payload()
    bad["projection"]["segments"][1]["surface"] = "ءَادَم"
    bad["projection"]["segments"][1]["char_end"] = 8
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: segments that do not reconstruct the surface",
               bad, "segment_reconstruction")

    # red 9 — non-contiguous spans
    bad = _green_payload()
    bad["projection"]["segments"][1]["char_start"] = 3
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: non-contiguous base-letter spans",
               bad, "segment_reconstruction")

    # red 10 — unresolved segment colour-guessed
    bad = _green_payload()
    bad["projection"]["segments"][0]["semantic_class"] = "unresolved"
    bad["projection"]["certification"]["status"] = "unresolved"
    bad["projection"]["unresolved"] = {
        "state": "function_unresolved",
        "message": "function not yet adjudicated; 2 candidate analyses",
        "candidate_count": 2, "candidates": ["jarr", "tawkid"]}
    bad["provenance"]["provenance_class"] = "illustrative-constructed"
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: unresolved segment keeping a semantic colour class",
               bad, "unresolved_colour")

    # red 11 — unresolved state claiming certification
    bad = _green_payload()
    bad["projection"]["unresolved"] = {
        "state": "function_unresolved",
        "message": "function not yet adjudicated; 2 candidate analyses",
        "candidate_count": 2, "candidates": ["jarr", "tawkid"]}
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: unresolved state may never certify",
               bad, "unresolved_honesty")

    # red 12 — rootless particle without rootless pedagogy
    bad = _green_payload()
    bad["projection"]["rootless_pedagogy"] = None
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: rootless particle must teach rootlessness",
               bad, "rootless_pedagogy")

    # red 13 — illustrative provenance claiming certified status
    bad = _green_payload()
    bad["provenance"]["provenance_class"] = "illustrative-from-live"
    expect_red("red: illustrative provenance may not claim certification",
               bad, "provenance")

    # red 14 — server path leaking across the boundary (RM-09)
    bad = _green_payload()
    bad["provenance"]["source_refs"].append("/var/www/qamus/live/rows.jsonl")
    expect_red("red: server filesystem path crossing the boundary",
               bad, "machine_topology")

    # red 15 — wrong schema major
    bad = _green_payload()
    bad["schema_version"] = "2.0.0"
    expect_red("red: unaccepted schema major", bad, "envelope_version")

    # red 16-18 — p007 samples may never fork from the canonical occurrence
    # projection or cite a revoked pre-claim-binding fact.
    p007 = json.loads((SAMPLES_DIR /
                       "p007_li_adam_clean.payload.json").read_text(
                           encoding="utf-8"))
    bad = copy.deepcopy(p007)
    bad["source_projection_hash"] = "0" * 64
    expect_red("red: stale p007 source projection hash", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["projection"]["hover_cards"][0]["governor"]["relation"] = \
        "muta-alliq"
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: uncompared p007 governor relation rendered", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["projection"]["evidence_refs"] = [
        "fact:p00slice:2_34_5:func" if ref.endswith(":func:v2") else ref
        for ref in bad["projection"]["evidence_refs"]
    ]
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: revoked legacy p007 fact cited", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["candidate_only"] = False
    bad["deliverable"] = True
    expect_red("red: p007 candidate payload marked deliverable", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["projection"]["hover_cards"][0]["contextual_gloss"] = \
        "invented page-local gloss"
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: p007 hover prose forked from canonical projection", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["projection"]["evidence_refs"] = [
        ref for ref in bad["projection"]["evidence_refs"]
        if not ref.endswith(":gov:v2")
    ]
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: required p007 fact omitted", bad, "p007_authority")

    bad = copy.deepcopy(p007)
    bad["projection"]["evidence_refs"][-1] = \
        "fact:p00slice:61_5_4:func:v2"
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: foreign certified p007 fact substituted", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["appearance"]["page_id"] = "entry:invented"
    expect_red("red: selected p007 appearance page fork", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["appearance"]["page_local"]["entry_relationship"] = "entry_relation"
    expect_red("red: p007 context appearance promoted to entry relation", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    bad["projection"]["hover_cards"][0]["fact_ids"] = []
    bad["projection_hash"] = projection_hash(bad["projection"])
    for app in bad["reverse_links"]["occurrence_to_appearances"]:
        app["projection_hash"] = bad["projection_hash"]
    expect_red("red: p007 hover lost its segment fact trace", bad,
               "p007_authority")

    bad = copy.deepcopy(p007)
    duplicate = copy.deepcopy(
        bad["reverse_links"]["occurrence_to_appearances"][0])
    duplicate["page_id"] = "entry:invented"
    bad["reverse_links"]["occurrence_to_appearances"].insert(0, duplicate)
    expect_red("red: duplicate p007 appearance shadows page binding", bad,
               "p007_authority")

    # red 16 — projection scalar must fail closed
    bad = _green_payload()
    bad["projection"] = "not-an-object"
    bad["projection_hash"] = "0" * 64
    expect_red(
        "red: projection scalar fails closed",
        bad,
        "projection_shape",
    )

    # red 17 — authoritative local appearance surface mismatch
    bad = _green_v12_payload()
    bad["appearance"]["appearance_id"] = "3041d6f44a27:u11:x1:w3"
    bad["appearance"]["page_id"] = "entry:3041d6f44a27"
    bad["appearance_binding_hash"] = appearance_binding_hash(bad)
    expect_red(
        "red: appearance id and displayed surface must join exactly",
        bad,
        "appearance_binding",
    )

    # red 18 — local span map missing
    bad = _green_v12_payload()
    del bad["appearance"]["canonical_to_appearance_span_map"]
    bad["appearance_binding_hash"] = appearance_binding_hash(bad)
    expect_red(
        "red: 1.2 appearance binding requires a local span map",
        bad,
        "appearance_binding",
    )

    # red 19 — malformed morpheme ownership span
    bad = _green_v12_payload()
    bad["projection"]["morpheme_spans"][0]["char_end"] = 1
    _rehash_payload(bad)
    expect_red(
        "red: morpheme ownership cannot split its segment",
        bad,
        "morpheme_spans",
    )

    # red 20 — colour and hover identities fork
    bad = _green_v12_payload()
    bad["projection"]["hover_cards"][0]["morpheme_occurrence_id"] = "wrong"
    _rehash_payload(bad)
    expect_red(
        "red: hover morpheme identity must equal visible ownership",
        bad,
        "identity_parity",
    )

    # red 21 — arbitrary geometry labels are not evidence
    bad = _green_v12_payload()
    bad["projection"]["evidence_refs"] = ["fact:fake:geom"]
    _rehash_payload(bad)
    expect_red(
        "red: primary geometry requires resolvable fact ids",
        bad,
        "geometry_evidence",
    )

    # red 22 — private external source label in a learner field
    bad = _green_v12_payload()
    bad["projection"]["hover_cards"][0][
        "unresolved"
    ] = "Quranic Arabic Corpus says this"
    _rehash_payload(bad)
    expect_red(
        "red: every learner field rejects source-private prose",
        bad,
        "public_boundary",
    )

    # red 23 — forward-slash Windows path
    bad = _green_v12_payload()
    bad["provenance"]["source_refs"].append(
        "C:" + "/Users/alice/private.json"
    )
    expect_red(
        "red: forward-slash Windows path is private topology",
        bad,
        "machine_topology",
    )

    # red 24 — missing reverse projection hash
    bad = _green_v12_payload()
    del bad["reverse_links"]["occurrence_to_appearances"][0][
        "projection_hash"
    ]
    expect_red(
        "red: every reverse appearance requires the shared hash",
        bad,
        "hash_fork",
    )

    # red 25 — forbidden topology key
    bad = _green_v12_payload()
    bad["appearance"]["build_host"] = "builder-17"
    expect_red(
        "red: machine topology keys never cross the boundary",
        bad,
        "public_boundary",
    )

    # red 26 — reverse entry relation invented without a forward typed edge
    bad = _green_v12_payload()
    phantom = json.loads(json.dumps(
        bad["reverse_links"]["entry_to_occurrences"][0],
        ensure_ascii=False,
    ))
    phantom["entry_id"] = "phantom-entry"
    bad["reverse_links"]["entry_to_occurrences"].append(phantom)
    expect_red(
        "red: reverse entry edge cannot invent settled-looking membership",
        bad,
        "reverse_entry_parity",
    )

    # red 27 — typoed plane states cannot bypass neutral candidate checks
    bad = _green_v12_payload()
    for key in list(bad["projection"]["certification"]["plane"]):
        bad["projection"]["certification"]["plane"][key] = "certifed"
    bad["projection"]["whole_word_gloss"] = "settled-looking gloss"
    bad["projection"]["segments"][0]["semantic_class"] = "particle"
    bad["projection"]["segments"][0]["renderer_class"] = "qg-particle"
    _rehash_payload(bad)
    expect_red(
        "red: invalid certification plane state fails closed",
        bad,
        "candidate_public_plane",
    )

    # red 28 — separator-hidden external-source labels in keys
    bad = _green_v12_payload()
    bad["appearance"]["qac_source"] = None
    expect_red(
        "red: external-source key labels never cross the boundary",
        bad,
        "public_boundary",
    )

    # red 29 — private topology embedded in a longer prose value
    bad = _green_v12_payload()
    bad["provenance"]["source_refs"].append(
        "copied from " + "C:" + "/Users/alice/private.json"
    )
    expect_red(
        "red: embedded private path fails topology scan",
        bad,
        "machine_topology",
    )

    # green control — a legal URI scheme is not a Windows drive path
    good = _green_v12_payload()
    good["provenance"]["source_refs"].append(
        "https://example.org/qamus/ref"
    )
    expect_green(
        "green: legal URI is not private machine topology",
        good,
    )

    if failures:
        print("\n%d SELF-TEST CASE(S) FAILED" % len(failures))
        return 1
    print("\nWEBSITE PAYLOAD SELF-TEST PASS")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payloads", nargs="*",
                        help="payload JSON file(s); default: committed "
                             "samples in qamus/examples/website-payloads/")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    paths = args.payloads or sorted(
        glob.glob(str(SAMPLES_DIR / "*.payload.json")))
    if not paths:
        parser.error("no payload files found")
    rc = 0
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        errors = validate_payload(payload)
        if errors:
            rc = 1
            print("FAIL %s" % path)
            for err in errors:
                print("   ", err)
        else:
            print("ok   %s" % path)
    if rc == 0:
        print("WEBSITE PAYLOAD VALIDATION PASS")
    return rc


if __name__ == "__main__":
    sys.exit(main())
