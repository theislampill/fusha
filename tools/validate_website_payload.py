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

PAYLOAD_SCHEMA = "qamus.website_projection_payload.v1"
ACCEPTED_MAJOR = 1

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

# RM-09: no server filesystem paths cross the boundary, anywhere in a payload.
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


def projection_hash(projection: dict) -> str:
    """sha256 over the canonical serialization of the fact plane (§5)."""
    blob = json.dumps(projection, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _learner_fields(projection: dict):
    """Yield (field_name, text) for every learner-facing field (§11)."""
    for key in ("whole_word_gloss", "learner_explanation",
                "rootless_pedagogy"):
        yield key, projection.get(key)
    unresolved = projection.get("unresolved")
    if isinstance(unresolved, dict):
        yield "unresolved.message", unresolved.get("message")
    for i, seg in enumerate(projection.get("segments") or []):
        if not isinstance(seg, dict):
            continue
        for key in ("gloss", "sarf_note", "nahw_note"):
            yield "segments[%d].%s" % (i, key), seg.get(key)
    for i, card in enumerate(projection.get("hover_cards") or []):
        if not isinstance(card, dict):
            continue
        for key in ("contextual_gloss", "sarf_note", "nahw_note", "reason"):
            yield "hover_cards[%d].%s" % (i, key), card.get(key)


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
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(version or ""))
    if not match:
        errors.append("envelope_version: schema_version %r is not semver"
                      % version)
    elif int(match.group(1)) != ACCEPTED_MAJOR:
        errors.append(
            "envelope_version: schema_version %r has major %s, validator "
            "accepts major %d only (breaking changes are an owner decision, "
            "contract §9)" % (version, match.group(1), ACCEPTED_MAJOR))
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
    if isinstance(projection, dict):
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
    reverse = payload.get("reverse_links") or {}
    for app in reverse.get("occurrence_to_appearances") or []:
        if not isinstance(app, dict):
            continue
        listed = app.get("projection_hash")
        if listed is not None and listed != want:
            errors.append(
                "hash_fork: appearance %s lists projection_hash %s but the "
                "canonical occurrence hash is %s — same occurrence must "
                "carry the same projection everywhere (contract §5)"
                % (app.get("appearance_id"), listed, want))


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
    check_prose_leak(payload, errors)
    check_segment_reconstruction(payload, errors)
    check_unresolved_and_rootless(payload, errors)
    check_provenance(payload, errors)
    check_no_server_paths(payload, errors)
    check_p007_authority(payload, errors)
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
               bad, "server_paths")

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
