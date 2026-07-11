#!/usr/bin/env python3
"""Build deterministic, evidence-complete T11 competing-analyses review packets.

The APPEND population's ``competing_analyses`` rows (append-queue.jsonl,
``primary_class == competing_analyses``) are NOT live: there is no live payload.
The decision each packet asks a reviewer to make is *which bound entry's analysis
(root/section) governs the location's future content* -- with **retaining BOTH
analyses as alternatives a first-class outcome**, since competing readings are
preserved per the charter.

This tool emits fixed review evidence plus a response schema. It records no votes,
conclusions, ledger rows, crosswalk rows, or live mutations. The v2 evidence
method (entry-content extraction, example->occurrence fingerprint mapping,
morphology / homograph record) is IMPORTED from ``tools/build_two_vote_packets``
-- never forked.
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

# Import (never fork) the shared v2 evidence method + helpers.
from tools import build_two_vote_packets as tv  # noqa: E402
from tools.build_two_vote_packets import (  # noqa: E402
    ayah_of,
    build_morphology_record,
    build_occurrence_mapping,
    canonical_bytes,
    canonical_rows_sha256,
    entry_content_for_carrier,
    index_unique,
    input_pin,
    load_gate_ssot,
    load_json,
    load_jsonl,
    loc_key,
    logical_path,
    render_jsonl,
    row_source,
    scrub_source_line,
    sha256_file,
    stable_sha256,
    surah_round_robin,
    verify_repository_baseline,
)

# ---------------------------------------------------------------------------
# Pins and constants
# ---------------------------------------------------------------------------
AUTHORITATIVE_BASELINE_SHA = "69830258bf463cff185ba621a13189093857bddc"
EXPECTED_APPEND_QUEUE_SHA256 = (
    "339ed820b4f5b8af4a8dff26c14de0921b9d447bf2689370067c73a98ef598b0"
)
EXPECTED_ENTRIES_SHA256 = (
    "a68245e93ce1a8b76858b672a449ff94475abf010e8102575e7c0285c540a78f"
)
EXPECTED_LOC_SURFACES_SHA256 = tv.EXPECTED_LOC_SURFACES_SHA256

TARGET_CLASS = "competing_analyses"
PILOT_SIZE = 100

DEFAULT_QUEUE = ROOT / "qamus/indexes/largelexicon/append-queue/append-queue.jsonl"
DEFAULT_ENTRIES = ROOT / "qamus/data/current/entries.jsonl"
DEFAULT_LOC_SURFACES = tv.DEFAULT_LOC_SURFACES
DEFAULT_HOMOGRAPH_KEYS = tv.DEFAULT_HOMOGRAPH_KEYS
DEFAULT_GATES = tv.DEFAULT_GATES
DEFAULT_FACT_SCHEMA = tv.DEFAULT_FACT_SCHEMA
DEFAULT_OUT = ROOT / (
    "qamus/indexes/largelexicon/append-queue/two-vote/packets-pilot-001.jsonl"
)
DEFAULT_MANIFEST = ROOT / (
    "qamus/indexes/largelexicon/append-queue/two-vote/pilot-batch.manifest.json"
)

# Named strata in fixed order (BRIEF: verb-vs-noun, noun-vs-particle,
# same-section-different-root). ``other_section_conflict`` is a documented
# safety bucket; it is never sampled (BRIEF names only three).
NAMED_STRATA = ("verb_vs_noun", "noun_vs_particle", "same_section_different_root")
OTHER_STRATUM = "other_section_conflict"

# A section conflict is a nahw-level (POS) disagreement; a same-section
# root disagreement is a lexical/root-sense disagreement.
STRATUM_GATE_TRIGGERS = {
    "verb_vs_noun": ["advanced_nahw"],
    "noun_vs_particle": ["advanced_nahw"],
    "same_section_different_root": ["multi_sense_root"],
    "other_section_conflict": ["advanced_nahw"],
}

PLACEHOLDER_MARKERS = (
    "dry-run carrier preview",
    "dry run carrier preview",
    "placeholder",
    "todo",
    "tbd",
    "pending gloss",
)

RESPONSE_FIELDS = [
    "decision",
    "governing_entry_id",
    "retained_alternatives",
    "sarf_evidence",
    "nahw_evidence",
    "rationale",
    "gate",
    "abstention_or_blocker",
    "confidence",
    "evidence_hashes",
]
DECISIONS = ["governing_entry", "retain_both_as_alternatives", "abstention"]


# ---------------------------------------------------------------------------
# Placeholder detection (data-integrity trap)
# ---------------------------------------------------------------------------
def text_has_placeholder(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    folded = " ".join(value.casefold().split())
    return any(marker in folded for marker in PLACEHOLDER_MARKERS)


def carrier_placeholder_clear(content: dict[str, Any]) -> bool:
    """A carrier is clear only if its bound example and at least one sense
    gloss carry real (non-placeholder) Arabic and English text."""
    example = (content.get("matching_usage_examples") or [{}])[0].get("content") or {}
    if text_has_placeholder(example.get("ar")) or text_has_placeholder(example.get("en")):
        return False
    senses = content.get("senses") or []
    if not senses:
        return False
    glosses = [sense.get("content", {}).get("gloss") for sense in senses]
    if all(text_has_placeholder(gloss) for gloss in glosses):
        return False
    return True


# ---------------------------------------------------------------------------
# Stratification
# ---------------------------------------------------------------------------
def analysis_sections(row: dict[str, Any]) -> set[str]:
    return {str(item.get("section") or "<none>") for item in row.get("competing_analyses", [])}


def analysis_roots(row: dict[str, Any]) -> set[str]:
    return {str(item.get("root") or "") for item in row.get("competing_analyses", [])}


def stratum_of(row: dict[str, Any]) -> str:
    sections = analysis_sections(row)
    roots = analysis_roots(row)
    if {"verb", "noun"} <= sections:
        return "verb_vs_noun"
    if {"noun", "particle"} <= sections:
        return "noun_vs_particle"
    if len(sections) == 1 and len(roots) >= 2:
        return "same_section_different_root"
    return OTHER_STRATUM


def allocate_proportional(counts: dict[str, int], total: int) -> dict[str, int]:
    """Largest-remainder allocation of ``total`` across the named strata, in
    proportion to population. Empty strata receive zero. Deterministic:
    remainders tie-break by fixed NAMED_STRATA order."""
    eligible = [name for name in NAMED_STRATA if counts.get(name, 0) > 0]
    population = sum(counts.get(name, 0) for name in eligible)
    if population == 0:
        raise ValueError("STOP: no eligible competing_analyses rows to sample")
    exact = {name: total * counts[name] / population for name in eligible}
    base = {name: int(exact[name]) for name in eligible}
    remaining = total - sum(base.values())
    order = sorted(
        eligible,
        key=lambda name: (-(exact[name] - base[name]), NAMED_STRATA.index(name)),
    )
    for name in order[:remaining]:
        base[name] += 1
    for name in eligible:
        if base[name] > counts[name]:
            raise ValueError(f"STOP: stratum {name} over-allocated {base[name]}/{counts[name]}")
    return {name: base.get(name, 0) for name in NAMED_STRATA}


def select_pilot_rows(
    rows: Iterable[dict[str, Any]], *, total: int = PILOT_SIZE
) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, Any]]:
    """Deterministic, stratified pilot selection. Within each stratum rows are
    taken by numeric-surah round-robin (muṣḥaf spread), each surah's rows in
    numeric canonical-location order."""
    by_stratum: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_stratum[stratum_of(row)].append(row)
    counts = {name: len(by_stratum.get(name, [])) for name in (*NAMED_STRATA, OTHER_STRATUM)}
    allocation = allocate_proportional(counts, total)

    selected: list[tuple[str, dict[str, Any]]] = []
    for name in NAMED_STRATA:
        take = allocation[name]
        if take == 0:
            continue
        chosen = surah_round_robin(by_stratum[name], take)
        selected.extend((name, row) for row in chosen)

    if len(selected) != total:
        raise ValueError(f"STOP: pilot selection produced {len(selected)} rows; requires {total}")
    if len({row["canonical_location"] for _name, row in selected}) != total:
        raise ValueError("STOP: pilot selection contains duplicate locations")

    diagnostics = {
        "population_stratum_counts": dict(sorted(counts.items())),
        "allocation": dict(sorted(allocation.items())),
        "same_section_subtypes": {
            "verb_only": sum(
                1
                for row in by_stratum.get("same_section_different_root", [])
                if analysis_sections(row) == {"verb"}
            ),
            "noun_only": sum(
                1
                for row in by_stratum.get("same_section_different_root", [])
                if analysis_sections(row) == {"noun"}
            ),
        },
    }
    return selected, diagnostics


# ---------------------------------------------------------------------------
# Gate resolution (reuse the SSOT loader; resolve stratum triggers locally)
# ---------------------------------------------------------------------------
def gate_for_stratum(stratum: str, gate_ssot: dict[str, Any], gate_path: Path) -> dict[str, Any]:
    triggers = STRATUM_GATE_TRIGGERS[stratum]
    gates = gate_ssot["document"]["gates"]
    trigger_to_tier = gate_ssot["trigger_to_tier"]
    missing = [trigger for trigger in triggers if trigger not in trigger_to_tier]
    if missing:
        raise ValueError(f"STOP: gate SSOT lacks a tier for {stratum}: {missing}")
    tiers = [trigger_to_tier[trigger] for trigger in triggers]
    tier = max(tiers, key=lambda value: gates[value]["rank"])
    return {
        "tier": tier,
        "rank": gates[tier]["rank"],
        "triggers": triggers,
        "requires": gates[tier].get("requires"),
        "source_address": f"{logical_path(gate_path)}#gates/{tier}",
        "loaded_via": "tools.fact_ledger._two_vote_fact_types",
    }


# ---------------------------------------------------------------------------
# Response schema (governing_entry OR retain_both_as_alternatives OR abstention)
# ---------------------------------------------------------------------------
def response_schema(
    gate: dict[str, Any], evidence_hashes: dict[str, str], candidate_entry_ids: list[str]
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
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": RESPONSE_FIELDS,
        "properties": {
            "decision": {"enum": copy.deepcopy(DECISIONS)},
            "governing_entry_id": {"type": ["string", "null"]},
            "retained_alternatives": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "sarf_evidence": copy.deepcopy(evidence_items),
            "nahw_evidence": copy.deepcopy(evidence_items),
            "rationale": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_address", "exact_reason"],
                "properties": {
                    "source_address": {"type": "string", "minLength": 1},
                    "exact_reason": {"type": "string", "minLength": 1},
                },
            },
            "gate": {"const": gate["tier"]},
            "abstention_or_blocker": {"type": ["string", "null"]},
            "confidence": {"enum": ["high", "medium", "low", "abstain"]},
            "evidence_hashes": {"const": copy.deepcopy(evidence_hashes)},
        },
        "allOf": [
            {
                "if": {"properties": {"decision": {"const": "governing_entry"}}},
                "then": {
                    "required": ["governing_entry_id"],
                    "properties": {"governing_entry_id": {"type": "string", "minLength": 1}},
                },
            },
            {
                "if": {"properties": {"decision": {"const": "retain_both_as_alternatives"}}},
                "then": {
                    "required": ["retained_alternatives"],
                    "properties": {
                        "retained_alternatives": {
                            "type": "array",
                            "minItems": 2,
                            "items": {"type": "string", "minLength": 1},
                        }
                    },
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
        "x-candidate-entry-ids": sorted(candidate_entry_ids),
    }


# ---------------------------------------------------------------------------
# Minimal, stdlib-only response validator (enough for this schema's features)
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
    if isinstance(value, str) and value != value:  # pragma: no cover - NaN guard
        return False
    if node_schema.get("minLength") is not None:
        if not isinstance(value, str) or len(value) < node_schema["minLength"]:
            return False
    if isinstance(value, list):
        if node_schema.get("minItems") is not None and len(value) < node_schema["minItems"]:
            return False
        item_schema = node_schema.get("items")
        if isinstance(item_schema, dict):
            if not all(_check(item_schema, item) for item in value):
                return False
    if isinstance(value, dict) and "properties" in node_schema:
        if node_schema.get("additionalProperties") is False:
            allowed = set(node_schema["properties"])
            if set(value) - allowed:
                return False
        for key in node_schema.get("required", []):
            if key not in value:
                return False
        for key, sub in node_schema["properties"].items():
            if key in value and not _check(sub, value[key]):
                return False
    return True


def response_conforms(schema: dict[str, Any], response: Any) -> bool:
    """Structural conformance check covering type/enum/const/required/
    additionalProperties/minItems/minLength and the decision if/then rules."""
    if not _check(schema, response):
        return False
    for clause in schema.get("allOf", []):
        condition = clause.get("if", {})
        if _check({"type": "object", "properties": condition.get("properties", {})}, response) and all(
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
    stratum: str,
    selection_rank: int,
    row: dict[str, Any],
    ayah_rows: list[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
    queue_path: Path,
    entries_path: Path,
    loc_surfaces_path: Path,
    homograph_path: Path,
    homograph_index: dict[str, list[tuple[int, dict[str, Any]]]],
    gate_path: Path,
    gate_ssot: dict[str, Any],
    packet_id_prefix: str = "t11-comp-001",
) -> dict[str, Any]:
    loc = row["canonical_location"]

    context = [
        {
            "loc": item["loc"],
            "surface": item["surface"],
            "source_address": row_source(loc_surfaces_path, item, f"loc={item['loc']}"),
        }
        for item in sorted(ayah_rows, key=lambda entry: loc_key(entry["loc"]))
    ]
    target_context = next((item for item in context if item["loc"] == loc), None)
    if target_context is None:
        raise ValueError(f"STOP: loc-surfaces context lacks target {loc}")
    target_surface = target_context["surface"]

    carriers: list[dict[str, Any]] = []
    for raw in row.get("bound_carriers") or []:
        carrier = {key: raw.get(key) for key in ("entry_id", "card_id", "qword_row_id", "row_id")}
        if any(not carrier[key] for key in carrier):
            raise ValueError(f"STOP: bound carrier at {loc} lacks a full identity: {raw}")
        entry = entries.get(str(carrier["entry_id"]))
        if entry is None:
            raise ValueError(f"STOP: bound carrier entry lookup failed at {loc}: {carrier['entry_id']}")
        carrier["carrier_source_address"] = row_source(
            queue_path, row, f"canonical_location={loc}/bound_carriers/row_id={carrier['row_id']}"
        )
        content = entry_content_for_carrier(carrier, entry, entries_path)
        carrier["candidate_entry_content"] = content
        carrier["placeholder_clear"] = carrier_placeholder_clear(content)
        carrier.update(
            build_occurrence_mapping(carrier, content["matching_usage_examples"][0], context)
        )
        carriers.append(carrier)
    if not carriers:
        raise ValueError(f"STOP: competing_analyses row {loc} has no bound carriers")
    carriers.sort(key=canonical_bytes)

    carriers_uniquely_addressing_target = sorted(
        {
            str(carrier["entry_id"])
            for carrier in carriers
            if carrier["mapping_status"] == "unique"
            and carrier["fingerprint_match_candidates"] == [loc]
        }
    )
    mapping_status = "unique" if carriers_uniquely_addressing_target else "ambiguous"

    morphology_record = build_morphology_record(
        target_loc=loc,
        target_surface=target_surface,
        target_source_address=target_context["source_address"],
        carriers=carriers,
        entries=entries,
        entries_path=entries_path,
        homograph_index=homograph_index,
        homograph_path=homograph_path,
    )

    competing_analyses = copy.deepcopy(row.get("competing_analyses") or [])
    distinct_analyses = {
        "roots": sorted({str(item.get("root") or "") for item in competing_analyses}),
        "sections": sorted({str(item.get("section") or "<none>") for item in competing_analyses}),
        "root_section_pairs": sorted(
            {(str(item.get("root") or ""), str(item.get("section") or "<none>")) for item in competing_analyses}
        ),
    }
    row_content = scrub_source_line(row)
    gate = gate_for_stratum(stratum, gate_ssot, gate_path)

    evidence_hashes = {
        "append_queue_row_sha256": stable_sha256(row_content),
        "ayah_word_context_sha256": stable_sha256(context),
        "candidate_carriers_sha256": stable_sha256(carriers),
        "competing_analyses_sha256": stable_sha256(competing_analyses),
        "gate_ssot_sha256": sha256_file(gate_path),
        "morphology_record_sha256": stable_sha256(morphology_record),
        "target_surface_sha256": stable_sha256(target_surface),
    }
    candidate_entry_ids = [str(carrier["entry_id"]) for carrier in carriers]

    packet = {
        "schema": "qamus.t11_competing_analysis_packet.v1",
        "packet_id": f"{packet_id_prefix}:{selection_rank:03d}:{loc}",
        "pilot_stratum": stratum,
        "selection_rank": selection_rank,
        "canonical_location": loc,
        "target_surface": {
            "value": target_surface,
            "source_address": target_context["source_address"],
        },
        "decision_kind": "which_bound_entry_analysis_governs_or_retain_both",
        "no_live_payload": True,
        "ayah_word_context": context,
        "competing_analyses_summary": {
            "content": competing_analyses,
            "analysis_count": row.get("class_evidence", {}).get("analysis_count"),
            "signal": row.get("class_evidence", {}).get("signal"),
            "source_address": row_source(queue_path, row, f"canonical_location={loc}/competing_analyses"),
        },
        "distinct_analyses": {
            "roots": distinct_analyses["roots"],
            "sections": distinct_analyses["sections"],
            "root_section_pairs": [list(pair) for pair in distinct_analyses["root_section_pairs"]],
        },
        "candidate_carriers": carriers,
        "mapping_status": mapping_status,
        "carriers_uniquely_addressing_target": carriers_uniquely_addressing_target,
        "morphology_record": morphology_record,
        "append_queue_evidence": {
            "content": row_content,
            "source_address": row_source(queue_path, row, f"canonical_location={loc}"),
        },
        "gate": gate,
        "evidence_hashes": evidence_hashes,
        "required_response_schema": response_schema(gate, evidence_hashes, candidate_entry_ids),
        "packet_status": "evidence_packet_only_no_votes_no_conclusions",
    }
    validate_packet(packet)
    packet["packet_sha256"] = stable_sha256(packet)
    return packet


def validate_packet(packet: dict[str, Any]) -> None:
    required = {
        "canonical_location",
        "target_surface",
        "ayah_word_context",
        "competing_analyses_summary",
        "distinct_analyses",
        "candidate_carriers",
        "mapping_status",
        "carriers_uniquely_addressing_target",
        "morphology_record",
        "append_queue_evidence",
        "gate",
        "evidence_hashes",
        "required_response_schema",
    }
    missing = sorted(required - set(packet))
    if missing:
        raise ValueError(f"packet missing fields: {missing}")
    gate = packet.get("gate")
    if not isinstance(gate, dict) or not gate.get("tier"):
        raise ValueError("packet missing gate tier")
    carriers = packet.get("candidate_carriers")
    if not isinstance(carriers, list) or not carriers:
        raise ValueError("packet has no candidate carriers")
    if packet.get("mapping_status") not in {"unique", "ambiguous"}:
        raise ValueError("packet missing a valid mapping_status")
    summary = packet.get("competing_analyses_summary", {})
    if not isinstance(summary.get("content"), list) or len(summary["content"]) < 2:
        raise ValueError("competing_analyses_summary must carry at least two analyses")
    loc = packet["canonical_location"]
    for index, carrier in enumerate(carriers):
        if any(not carrier.get(key) for key in ("entry_id", "card_id", "qword_row_id", "row_id")):
            raise ValueError(f"candidate carrier {index} lacks the full identity")
        content = carrier.get("candidate_entry_content")
        if not isinstance(content, dict):
            raise ValueError(f"candidate carrier {index} missing candidate content")
        for key in ("root", "section", "senses", "matching_usage_examples"):
            if key not in content:
                raise ValueError(f"candidate carrier {index} content missing {key}")
        examples = content.get("matching_usage_examples")
        if not isinstance(examples, list) or not examples:
            raise ValueError(f"candidate carrier {index} has no matching usage example")
        if any(not item.get("content", {}).get("ref") for item in examples):
            raise ValueError(f"candidate carrier {index} matching example lacks ref")
        # Placeholder trap: real evidence may never be placeholder text.
        if carrier.get("placeholder_clear") is not True:
            raise ValueError(
                f"candidate carrier {index} presents placeholder or empty content as evidence"
            )
        if carrier.get("mapping_status") not in {"unique", "ambiguous"}:
            raise ValueError(f"candidate carrier {index} lacks a valid mapping_status")
        occurrences = carrier.get("example_occurrence_candidates")
        fingerprints = carrier.get("occurrence_fingerprints")
        if not isinstance(occurrences, list) or not occurrences:
            raise ValueError(f"candidate carrier {index} has no occurrence candidates")
        if not isinstance(fingerprints, list) or [item.get("loc") for item in fingerprints] != occurrences:
            raise ValueError(f"candidate carrier {index} fingerprints differ from occurrence candidates")
        matches = carrier.get("fingerprint_match_candidates")
        expected = "unique" if isinstance(matches, list) and len(matches) == 1 else "ambiguous"
        if carrier["mapping_status"] != expected:
            raise ValueError(f"candidate carrier {index} mapping status differs from fingerprints")
    derived_unique = sorted(
        {
            str(carrier["entry_id"])
            for carrier in carriers
            if carrier["mapping_status"] == "unique"
            and carrier["fingerprint_match_candidates"] == [loc]
        }
    )
    if packet["carriers_uniquely_addressing_target"] != derived_unique:
        raise ValueError("carriers_uniquely_addressing_target differs from carrier mappings")
    if packet["mapping_status"] != ("unique" if derived_unique else "ambiguous"):
        raise ValueError("packet mapping_status differs from target-addressing carriers")
    response = packet.get("required_response_schema") or {}
    if response.get("required") != RESPONSE_FIELDS:
        raise ValueError("required response schema fields differ from the fixed contract")
    if response.get("properties", {}).get("gate", {}).get("const") != gate["tier"]:
        raise ValueError("required response schema gate differs from packet gate")
    if response.get("properties", {}).get("evidence_hashes", {}).get("const") != packet["evidence_hashes"]:
        raise ValueError("required response schema evidence hashes differ from packet evidence")
    if response.get("properties", {}).get("decision", {}).get("enum") != DECISIONS:
        raise ValueError("required response schema decision enum differs from the fixed contract")
    if "packet_sha256" in packet:
        supplied = packet["packet_sha256"]
        unhashed = {key: value for key, value in packet.items() if key != "packet_sha256"}
        if supplied != stable_sha256(unhashed):
            raise ValueError("packet_sha256 mismatch")


# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------
def build(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = {
        "append_queue": Path(args.queue),
        "entries": Path(args.entries),
        "loc_surfaces": Path(args.loc_surfaces),
        "homograph_keys": Path(args.homograph_keys),
        "grammar_gate_ssot": Path(args.gates),
        "fact_ledger_schema": Path(args.fact_schema),
    }
    for label, path in paths.items():
        if not path.is_file():
            raise ValueError(f"missing input {label}: {path}")
    verify_repository_baseline(AUTHORITATIVE_BASELINE_SHA)
    if sha256_file(paths["append_queue"]) != EXPECTED_APPEND_QUEUE_SHA256:
        raise ValueError("append-queue SHA-256 differs from the pinned input")
    if sha256_file(paths["entries"]) != EXPECTED_ENTRIES_SHA256:
        raise ValueError("entries SHA-256 differs from the pinned input")
    if sha256_file(paths["loc_surfaces"]) != EXPECTED_LOC_SURFACES_SHA256:
        raise ValueError("loc-surfaces SHA-256 differs from f2e079dc pin")

    queue_rows = load_jsonl(paths["append_queue"])
    entry_rows = load_jsonl(paths["entries"])
    loc_rows = load_jsonl(paths["loc_surfaces"])
    homograph_doc = load_json(paths["homograph_keys"])
    entries = index_unique(entry_rows, "id", "entry")

    population = [row for row in queue_rows if row.get("primary_class") == TARGET_CLASS]
    if not population:
        raise ValueError("STOP: no competing_analyses rows in append queue")

    # Self-containment guard: every population row must carry the fields to build
    # a self-contained packet (loc-surfaces coverage + resolvable carriers).
    loc_by_ayah: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in loc_rows:
        loc_by_ayah[ayah_of(row["loc"])].append(row)
    unresolvable = 0
    for row in population:
        loc = row["canonical_location"]
        ayah_rows = loc_by_ayah.get(ayah_of(loc), [])
        if loc not in {item["loc"] for item in ayah_rows}:
            unresolvable += 1
            continue
        for carrier in row.get("bound_carriers") or []:
            if str(carrier.get("entry_id")) not in entries:
                unresolvable += 1
                break
    if unresolvable:
        raise ValueError(
            f"STOP: {unresolvable} competing_analyses rows lack fields for self-contained packets"
        )

    homograph_index: dict[str, list[tuple[int, dict[str, Any]]]] = collections.defaultdict(list)
    for index, row in enumerate(homograph_doc.get("keys") or [], 1):
        key = row.get("norm_key")
        if isinstance(key, str) and key:
            indexed_row = copy.deepcopy(row)
            indexed_row["__risk_flag__"] = homograph_doc.get("risk_flag")
            homograph_index[key].append((index, indexed_row))

    gate_ssot = load_gate_ssot(paths["grammar_gate_ssot"], paths["fact_ledger_schema"])
    selected, diagnostics = select_pilot_rows(population, total=PILOT_SIZE)

    packets: list[dict[str, Any]] = []
    for rank, (stratum, row) in enumerate(selected, 1):
        loc = row["canonical_location"]
        packets.append(
            build_packet(
                stratum=stratum,
                selection_rank=rank,
                row=row,
                ayah_rows=loc_by_ayah.get(ayah_of(loc), []),
                entries=entries,
                queue_path=paths["append_queue"],
                entries_path=paths["entries"],
                loc_surfaces_path=paths["loc_surfaces"],
                homograph_path=paths["homograph_keys"],
                homograph_index=homograph_index,
                gate_path=paths["grammar_gate_ssot"],
                gate_ssot=gate_ssot,
            )
        )

    packet_bytes = render_jsonl(packets)
    stratum_counts = dict(sorted(collections.Counter(p["pilot_stratum"] for p in packets).items()))
    gate_counts = dict(sorted(collections.Counter(p["gate"]["tier"] for p in packets).items()))
    packet_mapping = dict(sorted(collections.Counter(p["mapping_status"] for p in packets).items()))
    carrier_mapping = dict(sorted(collections.Counter(
        carrier["mapping_status"] for p in packets for carrier in p["candidate_carriers"]
    ).items()))
    carriers_per_packet = [len(p["candidate_carriers"]) for p in packets]
    placeholder_clear_all = all(
        carrier["placeholder_clear"] for p in packets for carrier in p["candidate_carriers"]
    )

    manifest = {
        "schema": "qamus.t11_competing_analysis_pilot_manifest.v1",
        "generator": "tools/build_competing_analysis_packets.py",
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "scope": "packets_only_no_votes_no_conclusions_no_ledger_writes_no_crosswalk_writes",
        "decision_object": "which_bound_entry_analysis_governs_OR_retain_both_as_alternatives_OR_abstention",
        "retain_both_is_first_class_outcome": True,
        "no_live_payload": True,
        "population": {
            "primary_class": TARGET_CLASS,
            "row_count": len(population),
            "stratum_counts": diagnostics["population_stratum_counts"],
            "same_section_subtypes": diagnostics["same_section_subtypes"],
            "empty_named_strata": [
                name for name in NAMED_STRATA
                if diagnostics["population_stratum_counts"].get(name, 0) == 0
            ],
        },
        "selection_rule": {
            "pure_function": True,
            "randomness": "none",
            "wall_clock_inputs": "none",
            "total": PILOT_SIZE,
            "stratify_by": "section_conflict_type",
            "strata": list(NAMED_STRATA),
            "allocation_method": "largest_remainder_proportional_to_population_over_nonempty_named_strata",
            "allocation": diagnostics["allocation"],
            "within_stratum_order": "numeric_surah_round_robin_then_numeric_canonical_location",
            "note": (
                "noun_vs_particle is empty in this population (no particle sections); "
                "the 100 rows are split across the two non-empty named strata."
            ),
        },
        "gate_loading": {
            "loader": "tools.fact_ledger._two_vote_fact_types",
            "two_vote_fact_types": gate_ssot["two_vote_fact_types"],
            "stratum_triggers": STRATUM_GATE_TRIGGERS,
        },
        "inputs": {
            "append_queue": input_pin(paths["append_queue"], queue_rows),
            "entries": input_pin(paths["entries"], entry_rows),
            "loc_surfaces": input_pin(paths["loc_surfaces"], loc_rows),
            "homograph_keys": input_pin(paths["homograph_keys"]),
            "grammar_gate_ssot": input_pin(paths["grammar_gate_ssot"]),
            "fact_ledger_schema": input_pin(paths["fact_ledger_schema"]),
        },
        "input_sha_pins": {
            "append_queue": EXPECTED_APPEND_QUEUE_SHA256,
            "entries": EXPECTED_ENTRIES_SHA256,
            "loc_surfaces": EXPECTED_LOC_SURFACES_SHA256,
        },
        "output": {
            "path": logical_path(Path(args.out)),
            "rows": len(packets),
            "sha256": hashlib.sha256(packet_bytes).hexdigest(),
            "stratum_counts": stratum_counts,
            "gate_distribution": gate_counts,
            "packet_mapping_status_counts": packet_mapping,
            "carrier_mapping_status_counts": carrier_mapping,
            "carriers_per_packet_min": min(carriers_per_packet),
            "carriers_per_packet_max": max(carriers_per_packet),
            "carriers_total": sum(carriers_per_packet),
            "all_carriers_placeholder_clear": placeholder_clear_all,
            "packet_sha256_rule": "SHA-256 of canonical compact JSON for the packet before adding packet_sha256.",
        },
        "required_response_fields": RESPONSE_FIELDS,
        "response_decisions": DECISIONS,
        "validation": {
            "self_test": "python tools/build_competing_analysis_packets.py --self-test",
            "rebuild": "python tools/build_competing_analysis_packets.py",
            "rollback": "git revert <commit>",
            "stop_conditions": [
                "append rows lack the fields to build self-contained packets",
                "append-queue / entries / loc-surfaces SHA-256 differs from the pinned inputs",
                "gate SSOT lacks a tier for a stratum trigger",
                "a carrier presents placeholder or empty content as evidence",
                "pilot selection produces the wrong count or duplicate locations",
            ],
        },
    }
    return manifest, packets


def write_outputs(manifest: dict[str, Any], packets: list[dict[str, Any]], out: Path, manifest_path: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render_jsonl(packets))
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def _synthetic_row(loc: str, analyses: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "canonical_location": loc,
        "primary_class": TARGET_CLASS,
        "competing_analyses": [{"root": root, "section": section} for root, section in analyses],
        "class_evidence": {"analysis_count": len(analyses), "signal": "bound_entries_disagree_on_root_or_section"},
        "bound_carriers": [],
    }


def self_test() -> int:
    failures: list[str] = []

    # --- placeholder detection ---
    if not text_has_placeholder("dry-run carrier preview"):
        failures.append("placeholder marker not detected")
    if not text_has_placeholder("   "):
        failures.append("blank text not treated as placeholder")
    if text_has_placeholder("They are like the blind and the deaf."):
        failures.append("real English flagged as placeholder")
    clean_content = {
        "senses": [{"content": {"gloss": "deaf to the truth"}}],
        "matching_usage_examples": [{"content": {"ar": "وَالْأَصَمِّ", "en": "and the deaf", "ref": "11:24"}}],
    }
    if not carrier_placeholder_clear(clean_content):
        failures.append("clean carrier content marked as placeholder")
    trap_content = copy.deepcopy(clean_content)
    trap_content["matching_usage_examples"][0]["content"]["en"] = "TODO"
    if carrier_placeholder_clear(trap_content):
        failures.append("placeholder English carrier content marked clean")

    # --- stratification ---
    if stratum_of(_synthetic_row("2:1:1", [("", "noun"), ("ص م م", "verb")])) != "verb_vs_noun":
        failures.append("verb_vs_noun stratum misclassified")
    if stratum_of(_synthetic_row("2:1:2", [("", "noun"), ("ف ي", "particle")])) != "noun_vs_particle":
        failures.append("noun_vs_particle stratum misclassified")
    if stratum_of(_synthetic_row("2:1:3", [("ص م م", "verb"), ("ع م ي", "verb")])) != "same_section_different_root":
        failures.append("same_section_different_root stratum misclassified")

    # --- allocation determinism + proportionality + empty-stratum handling ---
    alloc = allocate_proportional(
        {"verb_vs_noun": 841, "noun_vs_particle": 0, "same_section_different_root": 3027}, 100
    )
    if alloc != {"verb_vs_noun": 22, "noun_vs_particle": 0, "same_section_different_root": 78}:
        failures.append(f"proportional allocation drifted: {alloc}")
    if sum(alloc.values()) != 100:
        failures.append("allocation does not sum to the pilot size")

    # --- selection determinism under input reordering ---
    synthetic_pop = [
        _synthetic_row("2:5:1", [("", "noun"), ("ص م م", "verb")]),
        _synthetic_row("3:5:1", [("", "noun"), ("ع م ي", "verb")]),
        _synthetic_row("4:5:1", [("ص م م", "verb"), ("ع م ي", "verb")]),
        _synthetic_row("5:5:1", [("ك ت ب", "verb"), ("ق ر ا", "verb")]),
        _synthetic_row("6:5:1", [("ن ص ر", "verb"), ("س م ع", "verb")]),
    ]
    forward, _ = select_pilot_rows(synthetic_pop, total=3)
    reverse, _ = select_pilot_rows(list(reversed(synthetic_pop)), total=3)
    projection = lambda rows: [(name, row["canonical_location"]) for name, row in rows]
    if projection(forward) != projection(reverse):
        failures.append("pilot selection changed under input reordering")
    if len(forward) != 3:
        failures.append("pilot selection produced the wrong count")

    # --- gate resolution ---
    gate_ssot = load_gate_ssot(DEFAULT_GATES, DEFAULT_FACT_SCHEMA)
    for stratum in ("verb_vs_noun", "same_section_different_root"):
        gate = gate_for_stratum(stratum, gate_ssot, DEFAULT_GATES)
        if gate["tier"] != "two_vote_required":
            failures.append(f"gate tier for {stratum} unexpectedly {gate['tier']}")

    # --- end-to-end packet build with a retain-both fixture ---
    entries = {
        "entry-noun": {
            "id": "entry-noun",
            "headword": "الأَصَمّ",
            "root": "",
            "section": "noun",
            "senses": [{"gloss": "deaf to the truth", "n": 1}],
            "usage": [{"forms": ["الأَصَمّ"], "examples": [{"ar": "بُكْمٌ عُمْيٌ", "en": "mute, blind", "ref": "2:18"}]}],
        },
        "entry-verb": {
            "id": "entry-verb",
            "headword": "صَمّ",
            "root": "ص م م",
            "section": "verb",
            "senses": [{"gloss": "to be willfully deaf", "n": 1}],
            "usage": [{"forms": ["صُمّ"], "examples": [{"ar": "بُكْمٌ عُمْيٌ", "en": "mute, blind", "ref": "2:18"}]}],
        },
    }
    retain_both_row = {
        "canonical_location": "2:18:1",
        "primary_class": TARGET_CLASS,
        "competing_analyses": [{"root": "", "section": "noun"}, {"root": "ص م م", "section": "verb"}],
        "class_evidence": {"analysis_count": 2, "signal": "bound_entries_disagree_on_root_or_section"},
        "bound_carriers": [
            {
                "entry_id": "entry-noun",
                "card_id": "entry-noun:u1:e1",
                "qword_row_id": "llx-qword-entry-noun-01-01-001",
                "row_id": "llx-crosswalk-entry-noun-r1",
            },
            {
                "entry_id": "entry-verb",
                "card_id": "entry-verb:u1:e1",
                "qword_row_id": "llx-qword-entry-verb-01-01-001",
                "row_id": "llx-crosswalk-entry-verb-r1",
            },
        ],
    }
    ayah_rows = [
        {"loc": "2:18:1", "surface": "بُكْمٌ"},
        {"loc": "2:18:2", "surface": "عُمْيٌ"},
    ]
    gate_ssot_full = load_gate_ssot(DEFAULT_GATES, DEFAULT_FACT_SCHEMA)
    packet = build_packet(
        stratum="verb_vs_noun",
        selection_rank=1,
        row=retain_both_row,
        ayah_rows=ayah_rows,
        entries=entries,
        queue_path=DEFAULT_QUEUE,
        entries_path=DEFAULT_ENTRIES,
        loc_surfaces_path=DEFAULT_LOC_SURFACES,
        homograph_path=DEFAULT_HOMOGRAPH_KEYS,
        homograph_index={},
        gate_path=DEFAULT_GATES,
        gate_ssot=gate_ssot_full,
    )
    if packet["gate"]["tier"] != "two_vote_required":
        failures.append("retain-both packet has an unexpected gate tier")
    if len(packet["candidate_carriers"]) != 2:
        failures.append("retain-both packet lost a competing carrier")
    if packet["packet_sha256"] != stable_sha256(
        {k: v for k, v in packet.items() if k != "packet_sha256"}
    ):
        failures.append("retain-both packet sha mismatch")

    # Determinism: identical rebuild yields an identical packet.
    packet_again = build_packet(
        stratum="verb_vs_noun",
        selection_rank=1,
        row=copy.deepcopy(retain_both_row),
        ayah_rows=list(reversed(ayah_rows)),
        entries=entries,
        queue_path=DEFAULT_QUEUE,
        entries_path=DEFAULT_ENTRIES,
        loc_surfaces_path=DEFAULT_LOC_SURFACES,
        homograph_path=DEFAULT_HOMOGRAPH_KEYS,
        homograph_index={},
        gate_path=DEFAULT_GATES,
        gate_ssot=gate_ssot_full,
    )
    if packet_again["packet_sha256"] != packet["packet_sha256"]:
        failures.append("packet build changed under ayah-context reordering")

    # Retain-both is a FIRST-CLASS, schema-valid outcome.
    schema = packet["required_response_schema"]
    retain_both_response = {
        "decision": "retain_both_as_alternatives",
        "governing_entry_id": None,
        "retained_alternatives": ["entry-noun", "entry-verb"],
        "sarf_evidence": [{"source_address": "qamus/data/current/entries.jsonl#id=entry-verb/root", "exact_reason": "root ص م م attested"}],
        "nahw_evidence": [{"source_address": "loc-surfaces#loc=2:18:1", "exact_reason": "either reading fits the context"}],
        "rationale": {"source_address": "append-queue#canonical_location=2:18:1", "exact_reason": "both analyses are defensible; preserve as alternatives"},
        "gate": "two_vote_required",
        "abstention_or_blocker": None,
        "confidence": "medium",
        "evidence_hashes": packet["evidence_hashes"],
    }
    if not response_conforms(schema, retain_both_response):
        failures.append("retain-both response rejected by its own required schema")
    # A retain-both decision with fewer than two alternatives must FAIL.
    bad_retain = copy.deepcopy(retain_both_response)
    bad_retain["retained_alternatives"] = ["entry-noun"]
    if response_conforms(schema, bad_retain):
        failures.append("retain-both accepted with fewer than two alternatives")
    # A governing_entry decision without an id must FAIL.
    bad_governing = copy.deepcopy(retain_both_response)
    bad_governing["decision"] = "governing_entry"
    bad_governing["governing_entry_id"] = None
    if response_conforms(schema, bad_governing):
        failures.append("governing_entry accepted without a governing_entry_id")
    # A well-formed governing_entry decision must PASS.
    good_governing = copy.deepcopy(retain_both_response)
    good_governing["decision"] = "governing_entry"
    good_governing["governing_entry_id"] = "entry-verb"
    if not response_conforms(schema, good_governing):
        failures.append("well-formed governing_entry response rejected")
    # Unknown decision / extra property must FAIL.
    bad_enum = copy.deepcopy(retain_both_response)
    bad_enum["decision"] = "publish"
    if response_conforms(schema, bad_enum):
        failures.append("unknown decision accepted by schema")
    extra = copy.deepcopy(retain_both_response)
    extra["surprise"] = 1
    if response_conforms(schema, extra):
        failures.append("additional property accepted by schema")

    # --- placeholder trap at packet level: a placeholder carrier must raise ---
    placeholder_entries = copy.deepcopy(entries)
    placeholder_entries["entry-verb"]["usage"][0]["examples"][0]["en"] = "pending gloss"
    try:
        build_packet(
            stratum="verb_vs_noun",
            selection_rank=1,
            row=copy.deepcopy(retain_both_row),
            ayah_rows=ayah_rows,
            entries=placeholder_entries,
            queue_path=DEFAULT_QUEUE,
            entries_path=DEFAULT_ENTRIES,
            loc_surfaces_path=DEFAULT_LOC_SURFACES,
            homograph_path=DEFAULT_HOMOGRAPH_KEYS,
            homograph_index={},
            gate_path=DEFAULT_GATES,
            gate_ssot=gate_ssot_full,
        )
    except ValueError as exc:
        if "placeholder" not in str(exc):
            failures.append("placeholder trap raised the wrong error")
    else:
        failures.append("placeholder carrier content was accepted as evidence")

    # --- render determinism ---
    rows = [{"selection_rank": 2, "value": "ب"}, {"selection_rank": 1, "value": "ا"}]
    if render_jsonl(rows) != render_jsonl(list(reversed(rows))):
        failures.append("packet bytes changed under input reordering")

    if failures:
        raise AssertionError("; ".join(failures))
    print("SELFTESTS=OK FAILURES=0 (incl. retain-both fixture + placeholder trap)")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--queue", default=DEFAULT_QUEUE)
    result.add_argument("--entries", default=DEFAULT_ENTRIES)
    result.add_argument("--loc-surfaces", default=DEFAULT_LOC_SURFACES)
    result.add_argument("--homograph-keys", default=DEFAULT_HOMOGRAPH_KEYS)
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
    print(json.dumps(manifest["output"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
