#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Join certified P007 attachment geometry onto every corpus appearance.

This Train D component consumes the 117,117-row corpus projection manifest and
the append-only P007 geometry certification store.  It emits one disposition
row per appearance of each exact ``deterministic-attachment-geometry``
occurrence.  The output carries certified sub-token geometry only: it cannot
mint entry/sense/lexeme identity, function, meaning, root, Nahw, semantic
colour, hover content, website payloads, live output, or deployment claims.

The surface gate is occurrence-wide.  A mixed-surface occurrence is held in
full; an exact-looking appearance from that occurrence is never projected by
itself.  No network or live mutation is performed.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
import unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools import build_corpus_projection_manifest as corpus_manifest  # noqa: E402
from tools.certify_typed_fact import TypedFactCertificationStore  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA = "qamus.corpus_fact_projection_disposition.v1"
BASELINE_SCHEMA = "qamus.corpus_fact_projection_baseline.v1"
BUILDER_ID = "build_corpus_fact_projection_batch"
BUILDER_VERSION = "1.0.0"
COHORT = "deterministic-attachment-geometry"
FACT_TYPES = (
    "attachment_geometry",
    "surface_reconstruction_nfc",
    "token_host_boundary",
)
FORBIDDEN_FACT_VALUE_KEYS = {
    "case",
    "case_or_mood",
    "contextual_function",
    "function",
    "gloss",
    "governed_expression",
    "governor",
    "irab",
    "meaning",
    "particle_entry",
    "root",
    "sense",
    "sense_n",
}

DEFAULT_REVERSE_UNIVERSE = os.path.join(
    REPO_ROOT, "qamus", "lattice", "p007-reverse-universe.jsonl")
DEFAULT_TYPED_FACTS = os.path.join(
    REPO_ROOT, "qamus", "certification", "p007-geometry-wave", "typed-facts.jsonl")
DEFAULT_EVENTS = os.path.join(
    REPO_ROOT, "qamus", "certification", "p007-geometry-wave", "events.jsonl")
DEFAULT_BASELINE_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "reports", "p007-geometry-corpus-projection-baseline.json")
DEFAULT_SAMPLE_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "examples", "p007-geometry-corpus-projection.sample.jsonl")
DEFAULT_SAMPLE_META_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "examples", "p007-geometry-corpus-projection.sample.meta.json")

# This batch is intentionally bound to the current component-1 population
# spine.  Drift is an Andon stop, not an invitation to silently recalculate a
# new cohort under an old report name.
EXPECTED_CORPUS_ROWS = 117117
# Re-pinned 2026-08-05: owner particle-plan renumber (P-00..P-05) relabeled
# universe rows; cohort identity proven unchanged by every other EXPECTED_*
# gate below (rows, occurrence ids, facts, events, appearances).
EXPECTED_CORPUS_SHA256 = "3bd07678486732ce5dc5771e1ed353e8f6aa15015cae4e4089ed6708e5f628e2"
EXPECTED_OCCURRENCES = 454
EXPECTED_FACTS = 1362
EXPECTED_EVENTS = 4086
EXPECTED_APPEARANCES = 985
EXPECTED_OCCURRENCE_ID_SHA256 = (
    "49ef4431360d87a22a8e7def89076cfcfb2df129fa381e05dbee96c764f3529b")
EXPECTED_APPEARANCE_ID_SHA256 = (
    "b3ee61976dcb711c5bb03babc3cf23412e7c1b574fb5b72125ba3b496ce45dc6")
EXPECTED_OCCURRENCE_POSTURES = {
    "exact_all_appearances": 385,
    "mixed_surface": 15,
    "variant_only": 54,
}
EXPECTED_APPEARANCE_POSTURES = {
    "exact_all_appearances": 820,
    "mixed_surface": 50,
    "variant_only": 115,
}
EXPECTED_OCCURRENCE_DISPOSITIONS = {
    "geometry_projection_ready": 385,
    "appearance_surface_variant_mapping_required": 69,
}
EXPECTED_APPEARANCE_DISPOSITIONS = {
    "geometry_projection_ready": 820,
    "appearance_surface_variant_mapping_required": 165,
}


class ProjectionBuildError(ValueError):
    """Raised when a closed input, certification trail, or join drifts."""


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                raise ProjectionBuildError(f"blank JSONL line at {path}:{line_no}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProjectionBuildError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise ProjectionBuildError(f"JSONL row must be an object at {path}:{line_no}")
            rows.append(row)
    return rows


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha256_prefixed(value):
    return "sha256:" + _sha256_bytes(_canonical(value).encode("utf-8"))


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl_bytes(rows):
    return ("".join(_canonical(row) + "\n" for row in rows)).encode("utf-8")


def _pretty_json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _newline_hash(values):
    return _sha256_bytes(("".join(str(value) + "\n" for value in values)).encode("utf-8"))


def _nfc(value):
    return unicodedata.normalize("NFC", value or "")


def _require(condition, message):
    if not condition:
        raise ProjectionBuildError(message)


def _load_corpus_rows(path=None):
    """Load a supplied component-1 manifest, or rebuild it through its owner."""

    if path:
        rows = _read_jsonl(path)
    else:
        rows, _stats, _context = corpus_manifest.build_manifest(
            corpus_manifest.DEFAULT_ENTRIES,
            corpus_manifest.DEFAULT_UNIVERSE,
            corpus_manifest.DEFAULT_UNIVERSE_OCC,
            corpus_manifest.DEFAULT_APPEARANCE_INDEX,
            corpus_manifest.DEFAULT_PARTICLE_MATRIX,
        )
    manifest_sha256 = _sha256_bytes(_jsonl_bytes(rows))
    _require(
        len(rows) == EXPECTED_CORPUS_ROWS,
        f"corpus manifest row-count drift: found {len(rows)}, expected {EXPECTED_CORPUS_ROWS}",
    )
    _require(
        manifest_sha256 == EXPECTED_CORPUS_SHA256,
        "corpus manifest hash drift: "
        f"found {manifest_sha256}, expected {EXPECTED_CORPUS_SHA256}",
    )
    appearance_ids = [row.get("appearance_id") for row in rows]
    _require(all(appearance_ids), "corpus manifest contains an empty appearance_id")
    _require(
        len(appearance_ids) == len(set(appearance_ids)),
        "corpus manifest contains duplicate appearance_id values",
    )
    return rows, manifest_sha256


def _load_geometry_cohort(path):
    all_rows = _read_jsonl(path)
    rows = [row for row in all_rows if row.get("partition") == COHORT]
    _require(
        len(rows) == EXPECTED_OCCURRENCES,
        f"geometry cohort drift: found {len(rows)}, expected {EXPECTED_OCCURRENCES}",
    )
    locs = [row.get("canonical_loc") for row in rows]
    occurrence_ids = [row.get("occurrence_id") for row in rows]
    _require(all(locs) and all(occurrence_ids), "geometry cohort contains an empty location")
    _require(len(locs) == len(set(locs)), "geometry cohort contains duplicate canonical_loc values")
    occurrence_hash = _newline_hash(occurrence_ids)
    _require(
        occurrence_hash == EXPECTED_OCCURRENCE_ID_SHA256,
        "geometry occurrence population hash drift: "
        f"found {occurrence_hash}, expected {EXPECTED_OCCURRENCE_ID_SHA256}",
    )
    for row in rows:
        loc = row["canonical_loc"]
        _require(row["occurrence_id"] == f"quran:{loc}", f"{loc}: occurrence_id mismatch")
        certification = row.get("geometry_certification") or {}
        _require(certification.get("state") == "certified", f"{loc}: geometry not certified")
        fact_ids = certification.get("fact_ids") or []
        _require(len(fact_ids) == 3 and len(set(fact_ids)) == 3,
                 f"{loc}: geometry certification must name exactly three facts")
    return rows, occurrence_hash


def validate_geometry_fact_scope(fact):
    """Fail closed if a geometry fact tries to carry a semantic claim."""

    fact_id = fact.get("fact_id") or "<missing-fact-id>"
    fact_type = fact.get("fact_type")
    _require(fact_type in FACT_TYPES, f"{fact_id}: forbidden fact_type {fact_type!r}")
    fact_value = fact.get("fact_value") or {}
    _require(isinstance(fact_value, dict), f"{fact_id}: fact_value must be an object")
    bad_keys = sorted(FORBIDDEN_FACT_VALUE_KEYS & set(fact_value))
    _require(not bad_keys, f"{fact_id}: geometry fact carries forbidden semantic keys {bad_keys}")


def _validate_certification_store(events, typed_by_id, events_path):
    """Delegate trail validity/state folding to the canonical certifier API."""

    _require(
        len(events) == EXPECTED_EVENTS,
        f"certification event-count drift: found {len(events)}, expected {EXPECTED_EVENTS}",
    )

    absolute_events_path = os.path.abspath(events_path)
    store = TypedFactCertificationStore(os.path.dirname(absolute_events_path))
    _require(
        os.path.abspath(store.events_path) == absolute_events_path,
        "certification events input must be the canonical events.jsonl store filename",
    )
    trail_errors = store.validate_trail()
    _require(
        not trail_errors,
        "canonical certification trail validation failed: " + "; ".join(trail_errors[:8]),
    )

    # The certifier owns event validity and state-machine semantics. Both APIs
    # are read explicitly: state() supplies the effective records, while
    # status_by_id() is the canonical status projection consumed below.
    canonical_state = store.state()
    status_by_id = store.status_by_id()
    _require(set(canonical_state) == set(status_by_id),
             "canonical certification state/status projections disagree")
    _require(
        all(canonical_state[fact_id].get("status") == status
            for fact_id, status in status_by_id.items()),
        "canonical certification state/status values disagree",
    )

    # Payload equality is a separate input-closure check, not a second state
    # machine: register events must carry exactly the committed typed facts.
    register_events = [event for event in events if event.get("event_type") == "register"]
    registered_by_id = {}
    for event in register_events:
        fact_id = event.get("fact_id")
        _require(fact_id and fact_id not in registered_by_id,
                 f"duplicate or empty registered fact_id: {fact_id!r}")
        fact = event.get("fact")
        _require(isinstance(fact, dict), f"registered fact {fact_id} has no payload")
        registered_by_id[fact_id] = fact
    _require(
        set(registered_by_id) == set(typed_by_id),
        "certification register set differs from typed-facts.jsonl",
    )
    for fact_id, typed_fact in typed_by_id.items():
        _require(
            _canonical(registered_by_id[fact_id]) == _canonical(typed_fact),
            f"registered fact {fact_id} differs from typed-facts.jsonl",
        )
    _require(
        collections.Counter(status_by_id.values()) == {"certified": EXPECTED_FACTS},
        f"latest effective certification state is not exactly {EXPECTED_FACTS} certified facts",
    )
    return status_by_id


def _facts_by_location(typed_facts, events, cohort_rows, events_path):
    _require(
        len(typed_facts) == EXPECTED_FACTS,
        f"typed-fact count drift: found {len(typed_facts)}, expected {EXPECTED_FACTS}",
    )
    typed_by_id = {}
    by_loc = collections.defaultdict(dict)
    for fact in typed_facts:
        fact_id = fact.get("fact_id")
        _require(fact_id and fact_id not in typed_by_id, f"duplicate or empty fact_id: {fact_id!r}")
        fact_type = fact.get("fact_type")
        validate_geometry_fact_scope(fact)
        address = ((fact.get("source_address") or {}).get("address") or "")
        _require(address.startswith("quran:"), f"{fact_id}: source address is not a quran token")
        loc = address[len("quran:"):]
        _require(fact_type not in by_loc[loc], f"{loc}: duplicate {fact_type} fact")
        typed_by_id[fact_id] = fact
        by_loc[loc][fact_type] = fact

    state = _validate_certification_store(events, typed_by_id, events_path)
    cohort_by_loc = {row["canonical_loc"]: row for row in cohort_rows}
    _require(set(by_loc) == set(cohort_by_loc), "geometry fact locations differ from cohort locations")
    expected_types = set(FACT_TYPES)
    for loc, facts in by_loc.items():
        _require(set(facts) == expected_types, f"{loc}: fact types are not exactly {sorted(FACT_TYPES)}")
        expected_ids = set(cohort_by_loc[loc]["geometry_certification"]["fact_ids"])
        actual_ids = {fact["fact_id"] for fact in facts.values()}
        _require(actual_ids == expected_ids, f"{loc}: reverse-universe fact-id set mismatch")
        _require(all(state[fact_id] == "certified" for fact_id in actual_ids),
                 f"{loc}: a geometry fact is not latest-event certified")
        _verify_geometry(loc, cohort_by_loc[loc], facts)
    return dict(by_loc), state


def _verify_geometry(loc, cohort_row, facts):
    geom = facts["attachment_geometry"]["fact_value"]
    recon = facts["surface_reconstruction_nfc"]["fact_value"]
    boundary = facts["token_host_boundary"]["fact_value"]
    token = _nfc(geom.get("surface_nfc"))
    _require(token, f"{loc}: empty certified token surface")
    _require(token == _nfc(recon.get("surface_nfc")), f"{loc}: reconstruction surface fork")
    _require(token == _nfc(boundary.get("surface_nfc")), f"{loc}: boundary surface fork")
    _require(token == _nfc(cohort_row.get("universe_surface")),
             f"{loc}: certified surface differs from reverse-universe surface")
    component = _nfc(geom.get("component_surface"))
    host = _nfc(boundary.get("host_remainder_surface"))
    _require(_nfc(component + host) == token, f"{loc}: component + host does not reconstruct token")
    _require(_nfc(recon.get("clitic")) == component, f"{loc}: reconstruction clitic fork")
    _require(_nfc(recon.get("remainder")) == host, f"{loc}: reconstruction host fork")
    char_span = geom.get("char_span") or {}
    start, end = char_span.get("start"), char_span.get("end")
    _require(start == 0 and isinstance(end, int) and 0 < end < len(token),
             f"{loc}: component span is not a proper sub-token prefix")
    _require(_nfc(token[start:end]) == component, f"{loc}: component char span does not slice token")
    _require(boundary.get("boundary_char_index") == end, f"{loc}: boundary char index fork")
    _require(_nfc(token[end:]) == host, f"{loc}: host char span does not slice token")


def _surface_posture(appearances, reference_surface):
    exact = [_nfc(row.get("displayed_surface")) == reference_surface for row in appearances]
    if all(exact):
        return "exact_all_appearances"
    if any(exact):
        return "mixed_surface"
    return "variant_only"


def _geometry_projection(loc, cohort_row, facts):
    geom = facts["attachment_geometry"]["fact_value"]
    boundary = facts["token_host_boundary"]["fact_value"]
    token = _nfc(geom["surface_nfc"])
    component_end = geom["char_span"]["end"]
    projection = {
        "schema": "qamus.certified_geometry_projection.v1",
        "occurrence_id": f"quran:{loc}",
        "certification": "partial_certified_geometry_only",
        "certified_facts": {
            fact_type: facts[fact_type]["fact_value"] for fact_type in FACT_TYPES
        },
        "fact_ids": {
            fact_type: facts[fact_type]["fact_id"] for fact_type in FACT_TYPES
        },
        "span_geometry": {
            "token_surface_nfc": token,
            "token_char_span": {"start": 0, "end": len(token)},
            "component_surface": _nfc(geom["component_surface"]),
            "component_char_span": dict(geom["char_span"]),
            "component_base_letter_span": dict(geom["base_letter_span"]),
            "host_surface": _nfc(boundary["host_remainder_surface"]),
            "host_char_span": {"start": component_end, "end": len(token)},
            "component_is_subtoken": True,
        },
        "reverse_trace": {
            "cohort_row": f"qamus/lattice/p007-reverse-universe.jsonl#{cohort_row['matrix_id']}",
            "certification_store": "qamus/certification/p007-geometry-wave/events.jsonl",
            "typed_fact_ids": sorted(fact["fact_id"] for fact in facts.values()),
        },
    }
    return projection, _sha256_prefixed(projection)


def build_batch(
        corpus_manifest_path=None,
        reverse_universe_path=DEFAULT_REVERSE_UNIVERSE,
        typed_facts_path=DEFAULT_TYPED_FACTS,
        events_path=DEFAULT_EVENTS):
    corpus_rows, corpus_sha256 = _load_corpus_rows(corpus_manifest_path)
    cohort_rows, occurrence_hash = _load_geometry_cohort(reverse_universe_path)
    typed_facts = _read_jsonl(typed_facts_path)
    events = _read_jsonl(events_path)
    facts_by_loc, effective_state = _facts_by_location(
        typed_facts, events, cohort_rows, events_path)

    cohort_by_loc = {row["canonical_loc"]: row for row in cohort_rows}
    corpus_by_loc = collections.defaultdict(list)
    for row in corpus_rows:
        loc = row.get("canonical_loc")
        if loc in cohort_by_loc:
            corpus_by_loc[loc].append(row)
    _require(set(corpus_by_loc) == set(cohort_by_loc),
             "corpus manifest does not contain every geometry cohort occurrence")

    all_joined_ids = []
    occurrence_postures = {}
    for loc, cohort_row in cohort_by_loc.items():
        joined_ids = {row["appearance_id"] for row in corpus_by_loc[loc]}
        reverse_ids = set((cohort_row.get("appearances") or {}).get("ids") or [])
        _require(joined_ids == reverse_ids, f"{loc}: appearance-set mismatch")
        all_joined_ids.extend(joined_ids)
        reference = _nfc(cohort_row["universe_surface"])
        occurrence_postures[loc] = _surface_posture(corpus_by_loc[loc], reference)

    _require(len(all_joined_ids) == EXPECTED_APPEARANCES,
             f"appearance-count drift: found {len(all_joined_ids)}, expected {EXPECTED_APPEARANCES}")
    _require(len(all_joined_ids) == len(set(all_joined_ids)),
             "an appearance joined to more than one geometry occurrence")
    appearance_hash = _newline_hash(sorted(all_joined_ids))
    _require(
        appearance_hash == EXPECTED_APPEARANCE_ID_SHA256,
        "geometry appearance population hash drift: "
        f"found {appearance_hash}, expected {EXPECTED_APPEARANCE_ID_SHA256}",
    )

    occurrence_posture_counts = dict(collections.Counter(occurrence_postures.values()))
    appearance_posture_counts = dict(collections.Counter(
        posture
        for loc, posture in occurrence_postures.items()
        for _row in corpus_by_loc[loc]
    ))
    _require(occurrence_posture_counts == EXPECTED_OCCURRENCE_POSTURES,
             f"occurrence surface-posture drift: {occurrence_posture_counts}")
    _require(appearance_posture_counts == EXPECTED_APPEARANCE_POSTURES,
             f"appearance surface-posture drift: {appearance_posture_counts}")

    projections = {}
    for loc, cohort_row in cohort_by_loc.items():
        projections[loc] = _geometry_projection(loc, cohort_row, facts_by_loc[loc])

    output_rows = []
    for corpus_row in corpus_rows:
        loc = corpus_row.get("canonical_loc")
        if loc not in cohort_by_loc:
            continue
        posture = occurrence_postures[loc]
        disposition = (
            "geometry_projection_ready"
            if posture == "exact_all_appearances"
            else "appearance_surface_variant_mapping_required"
        )
        reference = _nfc(cohort_by_loc[loc]["universe_surface"])
        appearance_posture = (
            "exact_nfc"
            if _nfc(corpus_row.get("displayed_surface")) == reference
            else "surface_variant"
        )
        projection, projection_hash = projections[loc]
        candidate_refs = corpus_row.get("particle_function_candidate_refs") or []
        output_rows.append({
            "schema": SCHEMA,
            "cohort": COHORT,
            "canonical_loc": loc,
            "occurrence_id": f"quran:{loc}",
            "appearance_id": corpus_row["appearance_id"],
            "occurrence_surface_posture": posture,
            "appearance_surface_posture": appearance_posture,
            "certified_reference_surface_nfc": reference,
            "displayed_surface": corpus_row.get("displayed_surface"),
            "downstream_disposition": disposition,
            "disposition_reason": (
                "every corpus appearance is NFC-identical to the certified token surface"
                if disposition == "geometry_projection_ready"
                else "the whole occurrence is held until an explicit appearance-surface variant "
                     "mapping exists; exact-looking members of a mixed occurrence are not projected"
            ),
            "geometry_projection_hash": projection_hash,
            "geometry_projection": projection,
            "corpus_context": {
                "card_owner_entry_id": corpus_row.get("entry_id"),
                "card_ref": corpus_row.get("card_ref"),
                "selected": bool(corpus_row.get("selected")),
                "card_owner_is_not_token_lexeme": True,
                "particle_function_candidate_ref_count": len(candidate_refs),
                "candidate_refs_are_not_nahw_or_semantic_authority": True,
            },
            "semantic_boundaries": {
                "token_lexeme": "not_projected_geometry_only",
                "particle_entry_identity": "not_projected_geometry_only",
                "particle_sense": "not_projected_geometry_only",
                "particle_function": "not_projected_geometry_only",
                "meaning": "not_projected_geometry_only",
                "root": "not_projected_geometry_only",
                "nahw": "not_available_candidate_refs_are_not_nahw",
                "colour": "boundary_available_no_semantic_colour",
                "hover": "not_available_missing_full_token_facts",
            },
            "delivery": {
                "website_payload": "not_generated",
                "live_output": "not_generated",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
        })

    occurrence_dispositions = {}
    for loc, posture in occurrence_postures.items():
        occurrence_dispositions[loc] = (
            "geometry_projection_ready"
            if posture == "exact_all_appearances"
            else "appearance_surface_variant_mapping_required"
        )
    occurrence_disposition_counts = dict(collections.Counter(occurrence_dispositions.values()))
    appearance_disposition_counts = dict(collections.Counter(
        row["downstream_disposition"] for row in output_rows))
    _require(occurrence_disposition_counts == EXPECTED_OCCURRENCE_DISPOSITIONS,
             f"occurrence disposition drift: {occurrence_disposition_counts}")
    _require(appearance_disposition_counts == EXPECTED_APPEARANCE_DISPOSITIONS,
             f"appearance disposition drift: {appearance_disposition_counts}")
    _require(len(output_rows) == EXPECTED_APPEARANCES, "output row count is not appearance-complete")

    fact_type_counts = dict(collections.Counter(fact["fact_type"] for fact in typed_facts))
    output_sha256 = _sha256_bytes(_jsonl_bytes(output_rows))
    baseline = {
        "schema": BASELINE_SCHEMA,
        "generator": {"id": BUILDER_ID, "version": BUILDER_VERSION},
        "inputs": {
            "corpus_projection_manifest_sha256": corpus_sha256,
            "p007_reverse_universe_sha256": _sha256_file(reverse_universe_path),
            "typed_facts_sha256": _sha256_file(typed_facts_path),
            "certification_events_sha256": _sha256_file(events_path),
        },
        "selection": {
            "partition": COHORT,
            "join_key": "exact canonical_loc",
            "appearance_policy": "include every corpus-manifest appearance at each selected location",
        },
        "certification_store": {
            "hash_chain_valid": True,
            "event_count": len(events),
            "registered_fact_count": len(typed_facts),
            "effective_status_counts": dict(collections.Counter(effective_state.values())),
            "fact_type_counts": fact_type_counts,
        },
        "population": {
            "source_corpus_manifest_rows": len(corpus_rows),
            "occurrences": len(cohort_rows),
            "certified_facts": len(typed_facts),
            "certification_events": len(events),
            "appearances": len(output_rows),
            "location_hash": occurrence_hash,
            "occurrence_id_sha256": occurrence_hash,
            "appearance_hash": appearance_hash,
            "appearance_id_sha256": appearance_hash,
            "occurrence_surface_posture_counts": occurrence_posture_counts,
            "appearance_surface_posture_counts": appearance_posture_counts,
        },
        "downstream_dispositions": {
            "occurrences": occurrence_disposition_counts,
            "appearances": appearance_disposition_counts,
            "occurrence_wide_surface_gate": True,
            "partial_mixed_occurrence_projection_allowed": False,
        },
        "certification_boundary": "partial_certified_geometry_only",
        "semantic_boundaries": {
            "colour": "boundary_available_no_semantic_colour",
            "hover": "not_available_missing_full_token_facts",
            "semantic_rich_colour_gains": 0,
            "hover_gains": 0,
            "token_identity_function_sense_meaning_root_nahw_gains": 0,
        },
        "delivery_boundary": {
            "website_payloads_generated": 0,
            "live_outputs_generated": 0,
            "public_materialization_allowed": False,
            "live_mutation_allowed": False,
        },
        "full_output": {"row_count": len(output_rows), "sha256": output_sha256},
        "verification": {
            "closed_input_counts_and_hashes_match": True,
            "event_trail_latest_state_certified": True,
            "exact_three_fact_types_per_occurrence": True,
            "appearance_sets_match_reverse_universe": True,
            "component_and_token_spans_distinct": True,
            "nfc_reconstruction_valid": True,
            "one_projection_hash_per_occurrence": True,
            "occurrence_wide_surface_gate_enforced": True,
            "website_and_live_output_zero": True,
        },
    }
    context = {
        "occurrence_postures": occurrence_postures,
        "occurrence_dispositions": occurrence_dispositions,
    }
    return output_rows, baseline, context


SAMPLE_SELECTION_RULE = (
    "Occurrence-complete deterministic sample in source order: take whole occurrence groups, "
    "prioritizing mixed_surface, then variant_only, then exact_all_appearances, and continue "
    "round-robin until at least sample_size rows are present. A mixed occurrence is never "
    "partially sampled."
)


def select_sample(rows, sample_size):
    by_loc = collections.defaultdict(list)
    loc_order = []
    for row in rows:
        loc = row["canonical_loc"]
        if loc not in by_loc:
            loc_order.append(loc)
        by_loc[loc].append(row)
    queues = {
        posture: [loc for loc in loc_order if by_loc[loc][0]["occurrence_surface_posture"] == posture]
        for posture in ("mixed_surface", "variant_only", "exact_all_appearances")
    }
    selected_locs = []
    selected_count = 0
    while selected_count < sample_size and any(queues.values()):
        for posture in ("mixed_surface", "variant_only", "exact_all_appearances"):
            if queues[posture]:
                loc = queues[posture].pop(0)
                selected_locs.append(loc)
                selected_count += len(by_loc[loc])
                if selected_count >= sample_size:
                    break
    selected = set(selected_locs)
    return [row for row in rows if row["canonical_loc"] in selected]


def _write_bytes(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def _check_bytes(path, expected, label):
    if not os.path.exists(path):
        raise ProjectionBuildError(f"CHECK FAIL - missing {label}: {path}")
    with open(path, "rb") as handle:
        actual = handle.read()
    if actual != expected:
        raise ProjectionBuildError(f"CHECK FAIL - stale {label}: {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-manifest",
                        help="existing component-1 117,117-row JSONL; default rebuilds through its owner")
    parser.add_argument("--reverse-universe", default=DEFAULT_REVERSE_UNIVERSE)
    parser.add_argument("--typed-facts", default=DEFAULT_TYPED_FACTS)
    parser.add_argument("--events", default=DEFAULT_EVENTS)
    parser.add_argument("--output", help="full 985-row JSONL output (normally under out/)")
    parser.add_argument("--baseline-output", default=DEFAULT_BASELINE_OUTPUT)
    parser.add_argument("--sample-output", default=DEFAULT_SAMPLE_OUTPUT)
    parser.add_argument("--sample-meta-output", default=DEFAULT_SAMPLE_META_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=48)
    parser.add_argument("--check", action="store_true",
                        help="rebuild and require byte-identical output/baseline/sample artifacts")
    args = parser.parse_args(argv)

    try:
        rows, baseline, _context = build_batch(
            args.corpus_manifest, args.reverse_universe, args.typed_facts, args.events)
        sample_rows = select_sample(rows, max(1, args.sample_size))
        sample_meta = {
            "schema": SCHEMA,
            "builder": {"id": BUILDER_ID, "version": BUILDER_VERSION},
            "source_full_output_row_count": len(rows),
            "source_full_output_sha256": baseline["full_output"]["sha256"],
            "sample_row_count": len(sample_rows),
            "sample_sha256": _sha256_bytes(_jsonl_bytes(sample_rows)),
            "sample_selection_rule": SAMPLE_SELECTION_RULE,
        }
        output_bytes = _jsonl_bytes(rows)
        baseline_bytes = _pretty_json_bytes(baseline)
        sample_bytes = _jsonl_bytes(sample_rows)
        sample_meta_bytes = _pretty_json_bytes(sample_meta)

        if args.check:
            if args.output:
                _check_bytes(args.output, output_bytes, "full projection batch")
            _check_bytes(args.baseline_output, baseline_bytes, "baseline")
            _check_bytes(args.sample_output, sample_bytes, "sample")
            _check_bytes(args.sample_meta_output, sample_meta_bytes, "sample metadata")
            print("CHECK PASS - projection batch and committed artifacts are byte-identical")
        else:
            if args.output:
                _write_bytes(args.output, output_bytes)
                print(f"full projection batch written: {os.path.abspath(args.output)}")
            _write_bytes(args.baseline_output, baseline_bytes)
            _write_bytes(args.sample_output, sample_bytes)
            _write_bytes(args.sample_meta_output, sample_meta_bytes)
            print(f"baseline written: {os.path.abspath(args.baseline_output)}")
            print(f"sample written: {os.path.abspath(args.sample_output)} rows={len(sample_rows)}")
        print(
            "occurrences=454 facts=1362 events=4086 appearances=985 "
            "ready=385/820 mapping_required=69/165 website_payloads=0 live_outputs=0"
        )
        return 0
    except (OSError, ProjectionBuildError, ValueError) as exc:
        print(f"BUILD FAIL - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
