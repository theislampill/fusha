#!/usr/bin/env python3
"""Build deterministic, self-contained T11 rebind two-vote review packets.

Population: the enriched class-2 rebind queue (``rebind-queue.v2.jsonl``), the
``existing_entry_rebind`` routing class only -- the *surface-anchored* host
candidates (documented form, legal clitic-peel, or norm_strict surface hit).
The skeleton-tier ``existing_entry_rebind_candidate`` rows are NOT in this wave;
they need confirm-at-vote treatment later.

These rows are NOT live: there is no live payload. The decision each packet asks
a reviewer to make is whether the mis-bound target location should be *rebound
to a proposed host entry*, its *current binding retained*, sent to *authoring*
(no proposed host fits), or *abstained* (with a blocker class).

This tool emits fixed review evidence plus a response schema. It records no
votes, conclusions, ledger rows, crosswalk rows, or live mutations
(candidate-generation only; zero canonical mutation). The v2 evidence method
(entry-content extraction + example->occurrence fingerprint mapping) is IMPORTED
from ``tools/build_two_vote_packets`` -- never forked. Derived roots are read
verbatim from the v2 enrichment (RM40 lookup-only boundary; no root generation
here). For homograph rows (``homograph_multiple_roots``) every competing derived
root is presented with no pre-ranking.
"""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import (never fork) the shared v2 evidence method + deterministic helpers.
from tools.build_two_vote_packets import (  # noqa: E402
    ayah_of,
    build_occurrence_mapping,
    canonical_bytes,
    candidate_role,
    entry_content_for_carrier,
    index_unique,
    input_pin,
    load_gate_ssot,
    load_jsonl,
    loc_key,
    logical_path,
    render_jsonl,
    row_source,
    scrub_source_line,
    sha256_file,
    stable_sha256,
    verify_repository_baseline,
)

# ---------------------------------------------------------------------------
# Pins and constants (merged main after PR #67; refuse to run on drift)
# ---------------------------------------------------------------------------
AUTHORITATIVE_BASELINE_SHA = "9eee6187981ad9abf6b41985e0fa05f3fd6619e2"
EXPECTED_REBIND_V2_SHA256 = (
    "783e916ec4a5c0970ebaf7c616d87e6133959dde6c39ef252b07663c1aea53c9"
)
EXPECTED_ENTRIES_SHA256 = (
    "b742fde5a8c1a6f04cdf104e0e12fb374ed0d5349eb6a3ace7e34ba2f9e1c15d"
)
EXPECTED_LOC_SURFACES_SHA256 = (
    "97efbaca345d5f23d9e9c699eef155f5bf4e06bb725e430729a8962b1573d227"
)
EXPECTED_DECIDABLE_PACKETS_SHA256 = (
    "ecb34710f3ef93726ab1633d79a8de7fc88d9735c8b0833c47fd1062e0b67740"
)
EXPECTED_FUNCWORD_V2_SHA256 = (
    "a40aabf38e3337e1b5ccbffa411df702c89a8fb8f2e2660218414bca220d5bd7"
)

TARGET_CLASS = "existing_entry_rebind"
SKELETON_CLASS = "existing_entry_rebind_candidate"
POPULATION_COUNT = 1248
HOMOGRAPH_COUNT = 94
DECLARED_GATE = "two_vote_required"
CONTEXT_RADIUS = 4  # +/- 4 vocalized words around the target token

# Root-sense disagreement over which existing entry hosts the surface: a
# lexical/root-sense decision -> two_vote_required (parity with the decidable
# same_section_different_root stratum).
REBIND_GATE_TRIGGERS = ["multi_sense_root"]

DEFAULT_QUEUE = ROOT / "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.v2.jsonl"
DEFAULT_ENTRIES = ROOT / "qamus/data/current/entries.jsonl"
DEFAULT_LOC_SURFACES = ROOT / "qamus/indexes/quran-loc-surface/index.jsonl"
DEFAULT_DECIDABLE_PACKETS = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-decidable.jsonl"
)
DEFAULT_FUNCWORD_QUEUE = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.v2.jsonl"
)
DEFAULT_GATES = ROOT / "nahw/evals/grammar-decision-gates.json"
DEFAULT_FACT_SCHEMA = ROOT / "qamus/schemas/fact-ledger-row.schema.json"
DEFAULT_OUT = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-rebind.jsonl"
)
DEFAULT_MANIFEST = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-rebind.manifest.json"
)

PACKET_SCHEMA = "qamus.t11_rebind_two_vote_packet.v1"
MANIFEST_SCHEMA = "qamus.t11_rebind_two_vote_packet_manifest.v1"
PACKET_ID_PREFIX = "t11-class2-rebind"

RESPONSE_FIELDS = [
    "decision",
    "host_entry_id",
    "retain_rationale",
    "requires_authoring_note",
    "sarf_evidence",
    "nahw_evidence",
    "gate",
    "abstention_or_blocker",
    "confidence",
    "packet_id",
    "canonical_location",
    "packet_sha256",
    "evidence_hashes",
]
DECISIONS = [
    "rebind_to_host",
    "retain_current_binding",
    "requires_authoring",
    "abstention",
]
CONFIDENCE = ["high", "medium", "low", "abstain"]

PLACEHOLDER_MARKERS = (
    "dry-run carrier preview",
    "dry run carrier preview",
    "placeholder",
    "todo",
    "tbd",
    "pending gloss",
)


# ---------------------------------------------------------------------------
# Population selection + disjointness
# ---------------------------------------------------------------------------
def population_rows(queue_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in queue_rows
        if (row.get("enrichment") or {}).get("routing_class") == TARGET_CLASS
    ]
    locations: set[str] = set()
    for row in rows:
        loc = (row.get("target") or {}).get("canonical_location")
        if not isinstance(loc, str) or not loc:
            raise ValueError("STOP: rebind population row lacks target.canonical_location")
        if loc in locations:
            raise ValueError(f"STOP: rebind population duplicates location {loc}")
        locations.add(loc)
    return sorted(rows, key=lambda row: loc_key(row["target"]["canonical_location"]))


def _target_locations(rows: Iterable[dict[str, Any]], label: str) -> set[str]:
    locations: set[str] = set()
    for row in rows:
        loc = (row.get("target") or {}).get("canonical_location")
        if not isinstance(loc, str) or not loc:
            raise ValueError(f"STOP: {label} row lacks target.canonical_location")
        locations.add(loc)
    return locations


def prove_disjointness(
    rebind_locations: set[str],
    decidable_rows: Iterable[dict[str, Any]],
    funcword_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Prove the rebind two-vote population is disjoint from the decidable and
    funcword two-vote populations."""
    decidable_locations = {
        row.get("canonical_location")
        for row in decidable_rows
        if row.get("canonical_location")
    }
    funcword_locations = _target_locations(funcword_rows, "funcword queue")
    overlaps = {
        "rebind_decidable": sorted(rebind_locations & decidable_locations, key=loc_key),
        "rebind_funcword": sorted(rebind_locations & funcword_locations, key=loc_key),
    }
    if any(overlaps.values()):
        counts = {name: len(values) for name, values in overlaps.items()}
        raise ValueError(f"STOP: rebind two-vote population overlap detected: {counts}")
    return {
        "all_pairwise_overlaps_zero": True,
        "rebind_count": len(rebind_locations),
        "decidable_count": len(decidable_locations),
        "funcword_count": len(funcword_locations),
        "overlap_counts": {name: len(values) for name, values in overlaps.items()},
        "overlapping_locations": overlaps,
    }


# ---------------------------------------------------------------------------
# Placeholder detection (data-integrity trap on host snapshots)
# ---------------------------------------------------------------------------
def text_has_placeholder(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    folded = " ".join(value.casefold().split())
    return any(marker in folded for marker in PLACEHOLDER_MARKERS)


# ---------------------------------------------------------------------------
# Gate resolution (reuse the SSOT loader)
# ---------------------------------------------------------------------------
def gate_for_rebind(gate_ssot: dict[str, Any], gate_path: Path) -> dict[str, Any]:
    gates = gate_ssot["document"]["gates"]
    trigger_to_tier = gate_ssot["trigger_to_tier"]
    missing = [t for t in REBIND_GATE_TRIGGERS if t not in trigger_to_tier]
    if missing:
        raise ValueError(f"STOP: gate SSOT lacks a tier for rebind triggers: {missing}")
    tier = max(
        (trigger_to_tier[t] for t in REBIND_GATE_TRIGGERS),
        key=lambda value: gates[value]["rank"],
    )
    if tier != DECLARED_GATE:
        raise ValueError(
            f"STOP: resolved gate tier {tier!r} differs from the v2-declared gate {DECLARED_GATE!r}"
        )
    return {
        "tier": tier,
        "rank": gates[tier]["rank"],
        "triggers": list(REBIND_GATE_TRIGGERS),
        "requires": gates[tier].get("requires"),
        "review_gate": "two_vote_existing_rebind",
        "source_address": f"{logical_path(gate_path)}#gates/{tier}",
        "loaded_via": "tools.fact_ledger._two_vote_fact_types",
    }


# ---------------------------------------------------------------------------
# Ayah context window (+/- CONTEXT_RADIUS vocalized words)
# ---------------------------------------------------------------------------
def ayah_window(
    loc: str, ayah_rows: list[dict[str, Any]], loc_surfaces_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordered = sorted(ayah_rows, key=lambda item: loc_key(item["loc"]))
    positions = [item["loc"] for item in ordered]
    if loc not in positions:
        raise ValueError(f"STOP: loc-surfaces context lacks target {loc}")
    index = positions.index(loc)
    window = ordered[max(0, index - CONTEXT_RADIUS): index + CONTEXT_RADIUS + 1]
    context = [
        {
            "loc": item["loc"],
            "surface": item["surface"],
            "source_address": row_source(loc_surfaces_path, item, f"loc={item['loc']}"),
        }
        for item in window
    ]
    target_context = next(item for item in context if item["loc"] == loc)
    return context, target_context


# ---------------------------------------------------------------------------
# Derived target roots (verbatim from v2 enrichment; no ranking, no generation)
# ---------------------------------------------------------------------------
def derived_target_roots(row: dict[str, Any], queue_path: Path, loc: str) -> dict[str, Any]:
    enrichment = row.get("enrichment") or {}
    raw = enrichment.get("derived_target_roots") or []
    roots: list[dict[str, Any]] = []
    for item in raw:
        root = str(item.get("root") or "")
        methods = sorted({str(m) for m in (item.get("derivation_methods") or [])})
        roots.append({"root": root, "derivation_methods": methods})
    roots.sort(key=canonical_bytes)
    homograph = bool(enrichment.get("homograph_multiple_roots"))
    return {
        "source_address": row_source(
            queue_path, row, f"canonical_location={loc}/enrichment/derived_target_roots"
        ),
        "homograph_multiple_roots": homograph,
        "root_derivation_boundary": str(
            enrichment.get("root_derivation_boundary") or "lookup_only_no_generation_rm40"
        ),
        "presentation": "all competing derived roots, no pre-ranking (RM40 lookup-only; no root generation)",
        "roots": roots,
    }


# ---------------------------------------------------------------------------
# Current mis-binding evidence
# ---------------------------------------------------------------------------
def enrich_misbound_carriers(
    row: dict[str, Any],
    *,
    loc: str,
    context: list[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
    entries_path: Path,
    queue_path: Path,
    proposed_host_ids: set[str],
    distractor_host_ids: set[str],
) -> list[dict[str, Any]]:
    misbound = row.get("misbound_carriers") or {}
    raw_carriers = misbound.get("bound_carriers") or []
    carriers: list[dict[str, Any]] = []
    for raw in raw_carriers:
        carrier = {key: raw.get(key) for key in ("entry_id", "card_id", "qword_row_id", "row_id")}
        if any(not carrier[key] for key in carrier):
            raise ValueError(f"STOP: mis-bound carrier at {loc} lacks a full identity: {raw}")
        entry_id = str(carrier["entry_id"])
        entry = entries.get(entry_id)
        if entry is None:
            raise ValueError(f"STOP: mis-bound carrier entry lookup failed at {loc}: {entry_id}")
        carrier["carrier_source_address"] = row_source(
            queue_path, row, f"canonical_location={loc}/misbound_carriers/row_id={carrier['row_id']}"
        )
        content = entry_content_for_carrier(carrier, entry, entries_path)
        carrier["candidate_entry_content"] = content
        carrier.update(build_occurrence_mapping(carrier, content["matching_usage_examples"][0], context))
        carrier["candidate_role"] = candidate_role(carrier["fingerprint_match_candidates"], loc)
        carrier["is_proposed_host"] = entry_id in proposed_host_ids
        carrier["neighbor_distractor"] = entry_id in distractor_host_ids
        carriers.append(carrier)
    carriers.sort(key=canonical_bytes)
    return carriers


def current_misbinding_evidence(
    row: dict[str, Any],
    *,
    loc: str,
    context: list[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
    entries_path: Path,
    queue_path: Path,
    proposed_host_ids: set[str],
    distractor_host_ids: set[str],
) -> dict[str, Any]:
    misbound = row.get("misbound_carriers") or {}
    competing = copy.deepcopy(misbound.get("competing_analyses") or [])
    carriers = enrich_misbound_carriers(
        row,
        loc=loc,
        context=context,
        entries=entries,
        entries_path=entries_path,
        queue_path=queue_path,
        proposed_host_ids=proposed_host_ids,
        distractor_host_ids=distractor_host_ids,
    )
    evidence = {
        "source_address": misbound.get("source_address")
        or row_source(queue_path, row, f"canonical_location={loc}/misbound_carriers"),
        "competing_analyses": competing,
        "distinct_bound_roots": sorted(
            {str(r) for r in (misbound.get("distinct_bound_roots") or [])}
        ),
        "diagnosis": misbound.get("diagnosis"),
        "misbound_carriers_available": bool(carriers),
        "misbound_carriers": carriers,
        "adjudication_rule": row.get("adjudication_rule"),
        "abstention_class": row.get("abstention_class"),
    }
    return evidence


# ---------------------------------------------------------------------------
# Proposed host entries (verbatim v2 snapshots; neutral ordering; trap check)
# ---------------------------------------------------------------------------
def proposed_hosts(row: dict[str, Any], loc: str) -> tuple[list[dict[str, Any]], list[str], set[str]]:
    enrichment = row.get("enrichment") or {}
    raw_hosts = enrichment.get("proposed_host_entries") or []
    if not raw_hosts:
        raise ValueError(f"STOP: rebind row {loc} has no proposed host entries")
    hosts: list[dict[str, Any]] = []
    entry_ids: list[str] = []
    distractor_ids: set[str] = set()
    for raw in raw_hosts:
        entry_id = str(raw.get("entry_id") or "")
        if not entry_id:
            raise ValueError(f"STOP: proposed host at {loc} lacks entry_id")
        snapshot = copy.deepcopy(raw)
        # Data-integrity trap: a host presented as evidence may never be placeholder text.
        for sense in snapshot.get("sense_glosses") or []:
            if text_has_placeholder(sense.get("gloss_first_words")):
                raise ValueError(
                    f"STOP: proposed host {entry_id} at {loc} presents placeholder gloss as evidence"
                )
        hosts.append(snapshot)
        entry_ids.append(entry_id)
        if snapshot.get("neighbor_distractor"):
            distractor_ids.add(entry_id)
    hosts.sort(key=canonical_bytes)
    return hosts, sorted(set(entry_ids)), distractor_ids


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
def response_schema(
    *,
    gate: dict[str, Any],
    evidence_hashes: dict[str, str],
    packet_id: str,
    loc: str,
    proposed_host_entry_ids: list[str],
) -> dict[str, Any]:
    evidence_items = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["source_address", "exact_reason"],
            "properties": {
                "source_address": {"type": "string", "minLength": 1},
                "exact_reason": {"type": "string", "minLength": 1},
            },
        },
    }
    rationale_object = {
        "type": "object",
        "additionalProperties": False,
        "required": ["source_address", "exact_reason"],
        "properties": {
            "source_address": {"type": "string", "minLength": 1},
            "exact_reason": {"type": "string", "minLength": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": RESPONSE_FIELDS,
        "properties": {
            "decision": {"enum": copy.deepcopy(DECISIONS)},
            "host_entry_id": {"type": ["string", "null"]},
            "retain_rationale": {
                "anyOf": [copy.deepcopy(rationale_object), {"type": "null"}]
            },
            "requires_authoring_note": {"type": ["string", "null"]},
            "sarf_evidence": copy.deepcopy(evidence_items),
            "nahw_evidence": copy.deepcopy(evidence_items),
            "gate": {"const": gate["tier"]},
            "abstention_or_blocker": {"type": ["string", "null"]},
            "confidence": {"enum": copy.deepcopy(CONFIDENCE)},
            # Verbatim echo fields the responder must copy back unchanged.
            "packet_id": {"const": packet_id},
            "canonical_location": {"const": loc},
            "packet_sha256": {"type": "string", "minLength": 64},
            "evidence_hashes": {"const": copy.deepcopy(evidence_hashes)},
        },
        "allOf": [
            {
                "if": {"properties": {"decision": {"const": "rebind_to_host"}}},
                "then": {
                    "required": ["host_entry_id"],
                    "properties": {
                        "host_entry_id": {
                            "type": "string",
                            "minLength": 1,
                            "enum": copy.deepcopy(proposed_host_entry_ids),
                        }
                    },
                },
            },
            {
                "if": {"properties": {"decision": {"const": "retain_current_binding"}}},
                "then": {
                    "required": ["retain_rationale"],
                    "properties": {"retain_rationale": copy.deepcopy(rationale_object)},
                },
            },
            {
                "if": {"properties": {"decision": {"const": "requires_authoring"}}},
                "then": {
                    "required": ["requires_authoring_note"],
                    "properties": {"requires_authoring_note": {"type": "string", "minLength": 1}},
                },
            },
            {
                "if": {"properties": {"decision": {"const": "abstention"}}},
                "then": {
                    "required": ["abstention_or_blocker"],
                    "properties": {"abstention_or_blocker": {"type": "string", "minLength": 1}},
                },
            },
        ],
        "x-proposed-host-entry-ids": copy.deepcopy(proposed_host_entry_ids),
    }


# ---------------------------------------------------------------------------
# Minimal, stdlib-only JSON-schema-subset validator (generic, not domain logic)
# ---------------------------------------------------------------------------
def _type_ok(value: Any, spec: Any) -> bool:
    types = spec if isinstance(spec, list) else [spec]
    for name in types:
        if name == "null" and value is None:
            return True
        if name == "string" and isinstance(value, str):
            return True
        if name == "array" and isinstance(value, list):
            return True
        if name == "object" and isinstance(value, dict):
            return True
    return False


def _check(node_schema: dict[str, Any], value: Any) -> bool:
    if "const" in node_schema and value != node_schema["const"]:
        return False
    if "enum" in node_schema and value not in node_schema["enum"]:
        return False
    if "type" in node_schema and not _type_ok(value, node_schema["type"]):
        return False
    if "anyOf" in node_schema and not any(_check(sub, value) for sub in node_schema["anyOf"]):
        return False
    if node_schema.get("minLength") is not None:
        if not isinstance(value, str) or len(value) < node_schema["minLength"]:
            return False
    if isinstance(value, list):
        if node_schema.get("minItems") is not None and len(value) < node_schema["minItems"]:
            return False
        item_schema = node_schema.get("items")
        if isinstance(item_schema, dict) and not all(_check(item_schema, item) for item in value):
            return False
    if isinstance(value, dict) and "properties" in node_schema:
        if node_schema.get("additionalProperties") is False:
            if set(value) - set(node_schema["properties"]):
                return False
        for key in node_schema.get("required", []):
            if key not in value:
                return False
        for key, sub in node_schema["properties"].items():
            if key in value and not _check(sub, value[key]):
                return False
    return True


def response_conforms(schema: dict[str, Any], response: Any) -> bool:
    if not _check(schema, response):
        return False
    for clause in schema.get("allOf", []):
        condition = clause.get("if", {})
        if all(
            _check(spec, response.get(key))
            for key, spec in condition.get("properties", {}).items()
        ):
            then = clause["then"]
            for key in then.get("required", []):
                if key not in response:
                    return False
            for key, spec in then.get("properties", {}).items():
                if key in response and not _check(spec, response[key]):
                    return False
    return True


# ---------------------------------------------------------------------------
# Packet build
# ---------------------------------------------------------------------------
def build_packet(
    *,
    selection_rank: int,
    row: dict[str, Any],
    ayah_rows: list[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
    entries_path: Path,
    queue_path: Path,
    loc_surfaces_path: Path,
    gate_path: Path,
    gate_ssot: dict[str, Any],
) -> dict[str, Any]:
    loc = row["target"]["canonical_location"]
    context, target_context = ayah_window(loc, ayah_rows, loc_surfaces_path)
    target_surface = target_context["surface"]

    target_block = row.get("target") or {}
    norm_strict_value = target_block.get("norm_strict")
    if not isinstance(target_surface, str) or not target_surface:
        raise ValueError(f"STOP: rebind target {loc} lacks a vocalized surface")

    hosts, proposed_host_entry_ids, distractor_ids = proposed_hosts(row, loc)
    roots = derived_target_roots(row, queue_path, loc)
    misbinding = current_misbinding_evidence(
        row,
        loc=loc,
        context=context,
        entries=entries,
        entries_path=entries_path,
        queue_path=queue_path,
        proposed_host_ids=set(proposed_host_entry_ids),
        distractor_host_ids=distractor_ids,
    )
    gate = gate_for_rebind(gate_ssot, gate_path)

    target = {
        "canonical_location": loc,
        "surface": {"value": target_surface, "source_address": target_context["source_address"]},
        "norm_strict": {
            "value": norm_strict_value,
            "source_address": row_source(queue_path, row, f"canonical_location={loc}/target/norm_strict"),
        },
    }

    evidence_hashes = {
        "rebind_row_sha256": stable_sha256(scrub_source_line(row)),
        "target_surface_sha256": stable_sha256(target_surface),
        "ayah_word_context_sha256": stable_sha256(context),
        "derived_target_roots_sha256": stable_sha256(roots),
        "proposed_host_entries_sha256": stable_sha256(hosts),
        "current_misbinding_evidence_sha256": stable_sha256(misbinding),
        "gate_ssot_sha256": sha256_file(gate_path),
    }
    packet_id = f"{PACKET_ID_PREFIX}:{selection_rank:03d}:{loc}"

    packet = {
        "schema": PACKET_SCHEMA,
        "packet_id": packet_id,
        "selection_rank": selection_rank,
        "canonical_location": loc,
        "routing_class": TARGET_CLASS,
        "decision_kind": "rebind_target_to_host_OR_retain_current_binding_OR_requires_authoring_OR_abstention",
        "no_live_payload": True,
        "candidate_only": True,
        "homograph_multiple_roots": roots["homograph_multiple_roots"],
        "target": target,
        "ayah_word_context": context,
        "derived_target_roots": roots,
        "current_misbinding_evidence": misbinding,
        "proposed_host_entries": hosts,
        "proposed_host_entry_ids": proposed_host_entry_ids,
        "rebind_queue_evidence": {
            "content": scrub_source_line(row),
            "source_address": row_source(queue_path, row, f"canonical_location={loc}"),
        },
        "gate": gate,
        "evidence_hashes": evidence_hashes,
        "required_response_schema": response_schema(
            gate=gate,
            evidence_hashes=evidence_hashes,
            packet_id=packet_id,
            loc=loc,
            proposed_host_entry_ids=proposed_host_entry_ids,
        ),
        "packet_status": "evidence_packet_only_no_votes_no_conclusions",
    }
    validate_packet(packet)
    packet["packet_sha256"] = stable_sha256(packet)
    return packet


def validate_packet(packet: dict[str, Any]) -> None:
    required = {
        "canonical_location",
        "routing_class",
        "target",
        "ayah_word_context",
        "derived_target_roots",
        "current_misbinding_evidence",
        "proposed_host_entries",
        "proposed_host_entry_ids",
        "gate",
        "evidence_hashes",
        "required_response_schema",
    }
    missing = sorted(required - set(packet))
    if missing:
        raise ValueError(f"packet missing fields: {missing}")
    if packet["routing_class"] != TARGET_CLASS:
        raise ValueError("packet routing_class is not existing_entry_rebind")
    gate = packet.get("gate")
    if not isinstance(gate, dict) or gate.get("tier") != DECLARED_GATE:
        raise ValueError("packet gate tier is not two_vote_required")
    hosts = packet.get("proposed_host_entries")
    if not isinstance(hosts, list) or not hosts:
        raise ValueError("packet has no proposed host entries")
    derived = sorted({str(h.get("entry_id")) for h in hosts})
    if packet["proposed_host_entry_ids"] != derived:
        raise ValueError("proposed_host_entry_ids differ from the proposed host snapshots")
    # Homograph presentation invariant: >=2 competing derived roots, no ranking key.
    roots = packet["derived_target_roots"]["roots"]
    if packet["homograph_multiple_roots"] and len({r["root"] for r in roots}) < 2:
        raise ValueError("homograph packet presents fewer than two competing derived roots")
    for index, root in enumerate(roots):
        if set(root) != {"root", "derivation_methods"}:
            raise ValueError(f"derived root {index} carries a ranking or extra field")
    # Mis-bound carriers, when present, must be fully addressed evidence.
    for index, carrier in enumerate(packet["current_misbinding_evidence"]["misbound_carriers"]):
        for key in ("entry_id", "card_id", "qword_row_id", "row_id", "candidate_entry_content"):
            if not carrier.get(key):
                raise ValueError(f"mis-bound carrier {index} lacks {key}")
        if carrier.get("mapping_status") not in {"unique", "ambiguous"}:
            raise ValueError(f"mis-bound carrier {index} lacks a valid mapping_status")
        occurrences = carrier.get("example_occurrence_candidates")
        fingerprints = carrier.get("occurrence_fingerprints")
        if not isinstance(occurrences, list) or not occurrences:
            raise ValueError(f"mis-bound carrier {index} has no occurrence candidates")
        if not isinstance(fingerprints, list) or [f.get("loc") for f in fingerprints] != occurrences:
            raise ValueError(f"mis-bound carrier {index} fingerprints differ from occurrences")
        if carrier.get("candidate_role") not in {"aligns_to_target_token", "host_lexeme_incidental"}:
            raise ValueError(f"mis-bound carrier {index} lacks a valid candidate_role")
    # Response schema contract.
    response = packet.get("required_response_schema") or {}
    if response.get("required") != RESPONSE_FIELDS:
        raise ValueError("required response schema fields differ from the fixed contract")
    if response.get("properties", {}).get("gate", {}).get("const") != gate["tier"]:
        raise ValueError("required response schema gate differs from packet gate")
    if response.get("properties", {}).get("evidence_hashes", {}).get("const") != packet["evidence_hashes"]:
        raise ValueError("required response schema evidence hashes differ from packet evidence")
    if response.get("properties", {}).get("decision", {}).get("enum") != DECISIONS:
        raise ValueError("required response schema decision enum differs from the fixed contract")
    if response.get("properties", {}).get("packet_id", {}).get("const") != packet["packet_id"]:
        raise ValueError("required response schema packet_id echo differs from packet")
    if response.get("properties", {}).get("canonical_location", {}).get("const") != packet["canonical_location"]:
        raise ValueError("required response schema canonical_location echo differs from packet")
    if "packet_sha256" in packet:
        unhashed = {key: value for key, value in packet.items() if key != "packet_sha256"}
        if packet["packet_sha256"] != stable_sha256(unhashed):
            raise ValueError("packet_sha256 mismatch")


# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------
def build(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = {
        "rebind_queue": Path(args.queue),
        "entries": Path(args.entries),
        "loc_surfaces": Path(args.loc_surfaces),
        "decidable_packets": Path(args.decidable_packets),
        "funcword_queue": Path(args.funcword_queue),
        "grammar_gate_ssot": Path(args.gates),
        "fact_ledger_schema": Path(args.fact_schema),
    }
    for label, path in paths.items():
        if not path.is_file():
            raise ValueError(f"missing input {label}: {path}")
    verify_repository_baseline(AUTHORITATIVE_BASELINE_SHA)

    pins = {
        "rebind_queue": (paths["rebind_queue"], EXPECTED_REBIND_V2_SHA256),
        "entries": (paths["entries"], EXPECTED_ENTRIES_SHA256),
        "loc_surfaces": (paths["loc_surfaces"], EXPECTED_LOC_SURFACES_SHA256),
        "decidable_packets": (paths["decidable_packets"], EXPECTED_DECIDABLE_PACKETS_SHA256),
        "funcword_queue": (paths["funcword_queue"], EXPECTED_FUNCWORD_V2_SHA256),
    }
    for label, (path, expected) in pins.items():
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"STOP: {label} SHA-256 {actual} differs from the pinned input {expected}"
            )

    queue_rows = load_jsonl(paths["rebind_queue"])
    entry_rows = load_jsonl(paths["entries"])
    loc_rows = load_jsonl(paths["loc_surfaces"])
    decidable_rows = load_jsonl(paths["decidable_packets"])
    funcword_rows = load_jsonl(paths["funcword_queue"])
    entries = index_unique(entry_rows, "id", "entry")
    gate_ssot = load_gate_ssot(paths["grammar_gate_ssot"], paths["fact_ledger_schema"])

    population = population_rows(queue_rows)
    if len(population) != POPULATION_COUNT:
        raise ValueError(
            f"STOP: rebind population is {len(population)} rows; requires {POPULATION_COUNT}"
        )
    skeleton_count = sum(
        1 for row in queue_rows if (row.get("enrichment") or {}).get("routing_class") == SKELETON_CLASS
    )

    rebind_locations = {row["target"]["canonical_location"] for row in population}
    disjointness = prove_disjointness(rebind_locations, decidable_rows, funcword_rows)

    loc_by_ayah: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in loc_rows:
        loc_by_ayah[ayah_of(row["loc"])].append(row)

    packets: list[dict[str, Any]] = []
    for rank, row in enumerate(population, 1):
        loc = row["target"]["canonical_location"]
        packets.append(
            build_packet(
                selection_rank=rank,
                row=row,
                ayah_rows=loc_by_ayah.get(ayah_of(loc), []),
                entries=entries,
                entries_path=paths["entries"],
                queue_path=paths["rebind_queue"],
                loc_surfaces_path=paths["loc_surfaces"],
                gate_path=paths["grammar_gate_ssot"],
                gate_ssot=gate_ssot,
            )
        )

    packet_bytes = render_jsonl(packets)
    homograph_packets = sum(1 for p in packets if p["homograph_multiple_roots"])
    if homograph_packets != HOMOGRAPH_COUNT:
        raise ValueError(
            f"STOP: {homograph_packets} homograph packets; requires {HOMOGRAPH_COUNT}"
        )
    carrier_packets = sum(
        1 for p in packets if p["current_misbinding_evidence"]["misbound_carriers"]
    )
    hosts_per_packet = [len(p["proposed_host_entries"]) for p in packets]

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generator": "tools/build_rebind_two_vote_packets.py",
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "scope": "packets_only_no_votes_no_conclusions_no_ledger_writes_no_crosswalk_writes",
        "decision_object": "rebind_to_host_OR_retain_current_binding_OR_requires_authoring_OR_abstention",
        "candidate_only": True,
        "no_live_payload": True,
        "zero_canonical_mutation": True,
        "population": {
            "routing_class": TARGET_CLASS,
            "surface_anchored_only": True,
            "row_count": len(population),
            "expected_row_count": POPULATION_COUNT,
            "unpacketed_rows": 0,
            "homograph_rows": homograph_packets,
            "expected_homograph_rows": HOMOGRAPH_COUNT,
            "rows_with_misbound_carriers": carrier_packets,
            "excluded_skeleton_class": SKELETON_CLASS,
            "excluded_skeleton_row_count": skeleton_count,
            "excluded_skeleton_note": (
                "existing_entry_rebind_candidate rows are the skeleton recall tier; "
                "they need confirm-at-vote treatment in a later wave and are NOT in this population"
            ),
            "sort_key": "numeric canonical_location",
        },
        "disjointness_proof": disjointness,
        "gate_loading": {
            "loader": "tools.fact_ledger._two_vote_fact_types",
            "two_vote_fact_types": gate_ssot["two_vote_fact_types"],
            "rebind_gate_triggers": REBIND_GATE_TRIGGERS,
            "resolved_tier": DECLARED_GATE,
        },
        "inputs": {
            "rebind_queue_v2": input_pin(paths["rebind_queue"], queue_rows),
            "entries": input_pin(paths["entries"], entry_rows),
            "loc_surfaces": input_pin(paths["loc_surfaces"], loc_rows),
            "decidable_packets": input_pin(paths["decidable_packets"], decidable_rows),
            "funcword_queue_v2": input_pin(paths["funcword_queue"], funcword_rows),
            "grammar_gate_ssot": input_pin(paths["grammar_gate_ssot"]),
            "fact_ledger_schema": input_pin(paths["fact_ledger_schema"]),
        },
        "input_sha_pins": {
            "rebind_queue_v2": EXPECTED_REBIND_V2_SHA256,
            "entries": EXPECTED_ENTRIES_SHA256,
            "loc_surfaces": EXPECTED_LOC_SURFACES_SHA256,
            "decidable_packets": EXPECTED_DECIDABLE_PACKETS_SHA256,
            "funcword_queue_v2": EXPECTED_FUNCWORD_V2_SHA256,
        },
        "output": {
            "path": logical_path(Path(args.out)),
            "rows": len(packets),
            "sha256": hashlib.sha256(packet_bytes).hexdigest(),
            "homograph_packets": homograph_packets,
            "packets_with_misbound_carriers": carrier_packets,
            "hosts_per_packet_min": min(hosts_per_packet),
            "hosts_per_packet_max": max(hosts_per_packet),
            "hosts_total": sum(hosts_per_packet),
            "packet_sha256s": [
                {"canonical_location": p["canonical_location"], "packet_sha256": p["packet_sha256"]}
                for p in packets
            ],
            "packet_sha256_rule": "SHA-256 of canonical compact JSON for the packet before adding packet_sha256.",
        },
        "required_response_fields": RESPONSE_FIELDS,
        "response_decisions": DECISIONS,
        "confidence_enum": CONFIDENCE,
        "context_radius_words": CONTEXT_RADIUS,
        "determinism": {
            "stdlib_only": True,
            "wall_clock_fields": False,
            "double_build_required": True,
        },
        "validation": {
            "self_test": "python tools/build_rebind_two_vote_packets.py --self-test",
            "rebuild": "python tools/build_rebind_two_vote_packets.py",
            "rollback": "git revert <commit>",
            "stop_conditions": [
                "rebind population is not exactly 1248 existing_entry_rebind rows",
                "homograph packet count is not exactly 94",
                "rebind population overlaps the decidable or funcword two-vote populations",
                "an input SHA-256 differs from its pinned value",
                "a mis-bound carrier does not resolve to entry content + occurrence fingerprint",
                "a proposed host presents placeholder gloss as evidence",
            ],
        },
    }
    return manifest, packets


def write_outputs(
    manifest: dict[str, Any], packets: list[dict[str, Any]], out: Path, manifest_path: Path
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render_jsonl(packets))
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


# ---------------------------------------------------------------------------
# Self-test (red-first: count / join / disjointness / schema failures)
# ---------------------------------------------------------------------------
def _host(entry_id: str, root: str, *, distractor: bool = False, gloss: str = "a real gloss") -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "entry_source_address": f"qamus/data/current/entries.jsonl#id={entry_id}",
        "headword": "هَادِي",
        "root": root,
        "section": "noun",
        "match_confidence": "documented_form_exact",
        "neighbor_distractor": distractor,
        "example_refs": ["2:2"],
        "sense_glosses": [{"n": 1, "gloss_first_words": gloss}],
        "derivation_methods": ["documented_form_exact"],
    }


def self_test() -> int:
    failures: list[str] = []

    # --- placeholder detection ---
    if not text_has_placeholder("pending gloss"):
        failures.append("placeholder marker not detected")
    if text_has_placeholder("mute, dumb"):
        failures.append("real gloss flagged as placeholder")

    # --- population filter + count + duplicate trap ---
    queue = [
        {"target": {"canonical_location": "2:2:2"}, "enrichment": {"routing_class": TARGET_CLASS}},
        {"target": {"canonical_location": "2:2:1"}, "enrichment": {"routing_class": TARGET_CLASS}},
        {"target": {"canonical_location": "2:2:9"}, "enrichment": {"routing_class": SKELETON_CLASS}},
    ]
    pop = population_rows(queue)
    if [r["target"]["canonical_location"] for r in pop] != ["2:2:1", "2:2:2"]:
        failures.append("population filter/sort dropped or mis-ordered rows")
    dup = queue + [{"target": {"canonical_location": "2:2:2"}, "enrichment": {"routing_class": TARGET_CLASS}}]
    try:
        population_rows(dup)
    except ValueError as exc:
        if "duplicate" not in str(exc):
            failures.append("duplicate population location raised the wrong error")
    else:
        failures.append("duplicate population location passed the uniqueness gate")

    # --- disjointness proof (clean + overlap) ---
    proof = prove_disjointness(
        {"2:2:1", "2:2:2"},
        [{"canonical_location": "2:2:3"}],
        [{"target": {"canonical_location": "2:2:4"}}],
    )
    if proof.get("all_pairwise_overlaps_zero") is not True:
        failures.append("clean disjointness proof did not report zero overlaps")
    for bad in (
        ([{"canonical_location": "2:2:1"}], [{"target": {"canonical_location": "2:2:4"}}]),
        ([{"canonical_location": "2:2:3"}], [{"target": {"canonical_location": "2:2:2"}}]),
    ):
        try:
            prove_disjointness({"2:2:1", "2:2:2"}, bad[0], bad[1])
        except ValueError as exc:
            if "overlap" not in str(exc):
                failures.append("disjointness overlap raised the wrong error")
        else:
            failures.append("disjointness proof accepted an overlapping population")

    # --- ayah window (+/- 4) ---
    ayah_rows = [{"loc": f"2:2:{i}", "surface": f"w{i}"} for i in range(1, 12)]
    context, target_context = ayah_window("2:2:6", ayah_rows, DEFAULT_LOC_SURFACES)
    if [c["loc"] for c in context] != [f"2:2:{i}" for i in range(2, 11)]:
        failures.append("ayah window is not +/- 4 around the target")
    if target_context["loc"] != "2:2:6":
        failures.append("ayah window lost the target token")
    try:
        ayah_window("2:2:99", ayah_rows, DEFAULT_LOC_SURFACES)
    except ValueError as exc:
        if "lacks target" not in str(exc):
            failures.append("missing target in ayah context raised the wrong error")
    else:
        failures.append("missing target in ayah context passed the coverage gate")

    # --- gate resolution ---
    gate_ssot = load_gate_ssot(DEFAULT_GATES, DEFAULT_FACT_SCHEMA)
    gate = gate_for_rebind(gate_ssot, DEFAULT_GATES)
    if gate["tier"] != DECLARED_GATE:
        failures.append(f"rebind gate resolved to {gate['tier']!r} not two_vote_required")

    # --- end-to-end packet build (homograph fixture) ---
    entries = {
        "host-a": {
            "id": "host-a",
            "headword": "هَادِي",
            "root": "ه د ي",
            "section": "noun",
            "senses": [{"gloss": "a guide", "n": 1}],
            "usage": [{"forms": ["هُدًى"], "examples": [{"ar": "ذَٰلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ هُدًى", "en": "guidance", "ref": "2:2"}]}],
        },
    }
    row = {
        "schema": "qamus.class2_rebind_candidate.v2",
        "gate": DECLARED_GATE,
        "review_state": "pending",
        "target": {"canonical_location": "2:2:6", "surface": "هُدًى", "norm_strict": "هدي"},
        "enrichment": {
            "routing_class": TARGET_CLASS,
            "homograph_multiple_roots": True,
            "root_derivation_boundary": "lookup_only_no_generation_rm40",
            "derived_target_roots": [
                {"root": "ه د ي", "derivation_methods": ["root_skeleton_strict"]},
                {"root": "ه د و", "derivation_methods": ["root_skeleton_weak_folded"]},
            ],
            "proposed_host_entries": [
                _host("host-a", "ه د ي"),
                _host("host-b", "ه د و", distractor=True),
            ],
        },
        "misbound_carriers": {
            "source_address": "qamus/indexes/largelexicon/append-queue/append-queue.jsonl#canonical_location=2:2:6/competing_analyses",
            "competing_analyses": [{"root": "ه د ي", "section": "noun"}, {"root": "ه د و", "section": "noun"}],
            "diagnosis": "bound entries are neighboring-token co-occurrences",
            "distinct_bound_roots": ["ه د و", "ه د ي"],
        },
        "abstention_class": "boundary_reclassification_host_evidence_needed",
    }
    ayah_ctx = [
        {"loc": "2:2:1", "surface": "ذَٰلِكَ"},
        {"loc": "2:2:2", "surface": "الْكِتَابُ"},
        {"loc": "2:2:3", "surface": "لَا"},
        {"loc": "2:2:4", "surface": "رَيْبَ"},
        {"loc": "2:2:5", "surface": "فِيهِ"},
        {"loc": "2:2:6", "surface": "هُدًى"},
        {"loc": "2:2:7", "surface": "لِّلْمُتَّقِينَ"},
    ]
    packet = build_packet(
        selection_rank=1,
        row=row,
        ayah_rows=ayah_ctx,
        entries=entries,
        entries_path=DEFAULT_ENTRIES,
        queue_path=DEFAULT_QUEUE,
        loc_surfaces_path=DEFAULT_LOC_SURFACES,
        gate_path=DEFAULT_GATES,
        gate_ssot=gate_ssot,
    )
    if packet["homograph_multiple_roots"] is not True:
        failures.append("homograph packet lost its homograph flag")
    if len(packet["derived_target_roots"]["roots"]) != 2:
        failures.append("homograph packet lost a competing derived root")
    if packet["proposed_host_entry_ids"] != ["host-a", "host-b"]:
        failures.append("proposed host ids drifted")
    if packet["packet_sha256"] != stable_sha256({k: v for k, v in packet.items() if k != "packet_sha256"}):
        failures.append("packet sha mismatch")

    # Determinism under input reordering.
    packet_again = build_packet(
        selection_rank=1,
        row=copy.deepcopy(row),
        ayah_rows=list(reversed(ayah_ctx)),
        entries=entries,
        entries_path=DEFAULT_ENTRIES,
        queue_path=DEFAULT_QUEUE,
        loc_surfaces_path=DEFAULT_LOC_SURFACES,
        gate_path=DEFAULT_GATES,
        gate_ssot=gate_ssot,
    )
    if packet_again["packet_sha256"] != packet["packet_sha256"]:
        failures.append("packet build changed under ayah-context reordering")

    # --- response schema: all four decisions ---
    schema = packet["required_response_schema"]
    base = {
        "decision": "rebind_to_host",
        "host_entry_id": "host-a",
        "retain_rationale": None,
        "requires_authoring_note": None,
        "sarf_evidence": [{"source_address": "x#a", "exact_reason": "root ه د ي attested"}],
        "nahw_evidence": [{"source_address": "x#b", "exact_reason": "fits the context"}],
        "gate": DECLARED_GATE,
        "abstention_or_blocker": None,
        "confidence": "high",
        "packet_id": packet["packet_id"],
        "canonical_location": "2:2:6",
        "packet_sha256": packet["packet_sha256"],
        "evidence_hashes": packet["evidence_hashes"],
    }
    if not response_conforms(schema, base):
        failures.append("well-formed rebind_to_host response rejected")
    bad_host = copy.deepcopy(base)
    bad_host["host_entry_id"] = "not-a-proposed-host"
    if response_conforms(schema, bad_host):
        failures.append("rebind_to_host accepted a non-proposed host id")
    no_host = copy.deepcopy(base)
    no_host["host_entry_id"] = None
    if response_conforms(schema, no_host):
        failures.append("rebind_to_host accepted without a host_entry_id")
    retain = copy.deepcopy(base)
    retain["decision"] = "retain_current_binding"
    retain["host_entry_id"] = None
    retain["retain_rationale"] = {"source_address": "x#c", "exact_reason": "current binding is correct"}
    if not response_conforms(schema, retain):
        failures.append("well-formed retain_current_binding response rejected")
    retain_bad = copy.deepcopy(retain)
    retain_bad["retain_rationale"] = None
    if response_conforms(schema, retain_bad):
        failures.append("retain_current_binding accepted without a rationale")
    authoring = copy.deepcopy(base)
    authoring["decision"] = "requires_authoring"
    authoring["host_entry_id"] = None
    authoring["requires_authoring_note"] = "no proposed host fits the target lexeme"
    if not response_conforms(schema, authoring):
        failures.append("well-formed requires_authoring response rejected")
    authoring_bad = copy.deepcopy(authoring)
    authoring_bad["requires_authoring_note"] = None
    if response_conforms(schema, authoring_bad):
        failures.append("requires_authoring accepted without an authoring note")
    abstain = copy.deepcopy(base)
    abstain["decision"] = "abstention"
    abstain["host_entry_id"] = None
    abstain["abstention_or_blocker"] = "boundary_reclassification_host_evidence_needed"
    if not response_conforms(schema, abstain):
        failures.append("well-formed abstention response rejected")
    abstain_bad = copy.deepcopy(abstain)
    abstain_bad["abstention_or_blocker"] = None
    if response_conforms(schema, abstain_bad):
        failures.append("abstention accepted without a blocker class")
    unknown = copy.deepcopy(base)
    unknown["decision"] = "publish"
    if response_conforms(schema, unknown):
        failures.append("unknown decision accepted by schema")
    extra = copy.deepcopy(base)
    extra["surprise"] = 1
    if response_conforms(schema, extra):
        failures.append("additional property accepted by schema")
    wrong_echo = copy.deepcopy(base)
    wrong_echo["canonical_location"] = "9:9:9"
    if response_conforms(schema, wrong_echo):
        failures.append("wrong canonical_location echo accepted by schema")

    # --- placeholder trap at host level ---
    trap_row = copy.deepcopy(row)
    trap_row["enrichment"]["proposed_host_entries"][0]["sense_glosses"][0]["gloss_first_words"] = "TODO"
    try:
        build_packet(
            selection_rank=1,
            row=trap_row,
            ayah_rows=ayah_ctx,
            entries=entries,
            entries_path=DEFAULT_ENTRIES,
            queue_path=DEFAULT_QUEUE,
            loc_surfaces_path=DEFAULT_LOC_SURFACES,
            gate_path=DEFAULT_GATES,
            gate_ssot=gate_ssot,
        )
    except ValueError as exc:
        if "placeholder" not in str(exc):
            failures.append("host placeholder trap raised the wrong error")
    else:
        failures.append("placeholder host gloss was accepted as evidence")

    # --- render determinism ---
    rows = [{"selection_rank": 2, "value": "ب"}, {"selection_rank": 1, "value": "ا"}]
    if render_jsonl(rows) != render_jsonl(list(reversed(rows))):
        failures.append("packet bytes changed under input reordering")

    if failures:
        raise AssertionError("; ".join(failures))
    print("SELFTESTS=OK FAILURES=0 (count/join/disjointness/schema/homograph/placeholder)")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--queue", default=DEFAULT_QUEUE)
    result.add_argument("--entries", default=DEFAULT_ENTRIES)
    result.add_argument("--loc-surfaces", default=DEFAULT_LOC_SURFACES)
    result.add_argument("--decidable-packets", default=DEFAULT_DECIDABLE_PACKETS)
    result.add_argument("--funcword-queue", default=DEFAULT_FUNCWORD_QUEUE)
    result.add_argument("--gates", default=DEFAULT_GATES)
    result.add_argument("--fact-schema", default=DEFAULT_FACT_SCHEMA)
    result.add_argument("--out", default=DEFAULT_OUT)
    result.add_argument("--manifest", default=DEFAULT_MANIFEST)
    result.add_argument("--self-test", action="store_true")
    return result


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    if args.self_test:
        return self_test()
    manifest, packets = build(args)
    write_outputs(manifest, packets, Path(args.out), Path(args.manifest))
    print(json.dumps(manifest["output"]["sha256"], ensure_ascii=False))
    print(json.dumps({k: v for k, v in manifest["output"].items() if k != "packet_sha256s"}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
