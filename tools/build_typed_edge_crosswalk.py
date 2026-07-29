#!/usr/bin/env python3
"""Build the canonical typed-edge graph and lexeme-to-entry projections.

The existing VNMAP ledger is the selected-word/card input and the existing
occurrence-appearance index is the canonical occurrence input.  This module
adds typed edges beside those artifacts; it deliberately does not reinterpret
the whitelist ``entry_id`` field as a lexical assertion.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.normalize_ar import bare, norm_strict


SCHEMA = "qamus.graph_edge.v1"
CROSSWALK_FORWARD_SCHEMA = "qamus.lexeme_entry_crosswalk.forward.v1"
CROSSWALK_REVERSE_SCHEMA = "qamus.lexeme_entry_crosswalk.reverse.v1"
PRODUCER_ID = "tools.build_typed_edge_crosswalk"
PRODUCER_VERSION = "1.0.0"

EDGE_TYPES = [
    "page_context_entry_edge",
    "selected_example_edge",
    "lexeme_entry_edge",
    "form_entry_edge",
    "sense_entry_edge",
    "root_family_edge",
    "canonical_occurrence_edge",
    "display_local_to_canonical_crosswalk_edge",
    "source_card_edge",
    "source_photo_edge",
    "rendered_appearance_edge",
    "decision_evidence_edge",
    "citation_form_display_edge",
]

# Particle-specific typed edge kinds (PARTICLE-CONTRACTS lane, 2026-07-29).
# Same vocabulary, same qamus.graph_edge.v1 row shape — NOT a parallel graph.
# Per-kind required-field and certification constraints live in
# qamus/schemas/particle-edge-ontology.schema.json and are enforced by
# tools/validate_particle_projection_parity.py (which also asserts this list
# and the schema enum never drift apart).
PARTICLE_EDGE_TYPES = [
    "particle_entry_candidate_edge",
    "particle_entry_certified_edge",
    "particle_sense_candidate_edge",
    "particle_sense_certified_edge",
    "particle_function_edge",
    "clitic_host_edge",
    "governor_edge",
    "governed_expression_edge",
    "scope_edge",
    "coordination_edge",
    "condition_edge",
    "negation_scope_edge",
    "relative_antecedent_edge",
    "pronoun_referent_edge",
    "particle_occurrence_appearance_edge",
    "particle_entry_reverse_occurrence_edge",
    "source_evidence_edge",
    "decision_or_two_vote_edge",
]
EDGE_TYPES = EDGE_TYPES + PARTICLE_EDGE_TYPES
EDGE_TYPE_SET = set(EDGE_TYPES)
STATUSES = [
    "certified",
    "deterministic_exact",
    "candidate",
    "ambiguous",
    "source_gap",
    "owner_or_scholar_required",
    "rejected",
]
STATUS_SET = set(STATUSES)
# "source" (evidence address nodes) and "decision" (two-vote / adjudication
# artifact nodes) added for the particle edge kinds; membership-only, additive.
NODE_TYPES = ["entry", "sense", "card", "selected-word", "occurrence", "appearance", "source", "decision"]
NODE_TYPE_SET = set(NODE_TYPES)
_SOURCE_KEY_RE = re.compile(r"^([A-Za-z]+)0*(\d+)$")


@dataclass
class GraphBuildResult:
    """Small attribute-compatible wrapper used by callers and tests."""

    bundle: dict

    def __getitem__(self, key):
        return self.bundle[key]

    def get(self, key, default=None):
        return self.bundle.get(key, default)


def read_jsonl(path: str | Path) -> list[dict]:
    """Read a JSONL object stream with line-aware errors."""

    path = Path(path)
    if path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return list(value)
        raise ValueError(f"expected JSON object/list at {path}")
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            rows.append(value)
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _entry_id(value) -> str:
    return _text(value)


def _node(kind: str, value: str) -> str:
    if kind not in NODE_TYPE_SET:
        raise ValueError(f"unsupported node type: {kind}")
    value = _text(value)
    if not value or ":" in kind:
        raise ValueError(f"invalid {kind} node value: {value!r}")
    return f"{kind}:{value}"


def entry_node(entry_id: str) -> str:
    return _node("entry", entry_id)


def sense_node(entry_id: str, sense_index: int) -> str:
    return _node("sense", f"{entry_id}:s{int(sense_index)}")


def card_node(entry_id: str, usage_index: int, example_index: int, card_ref: str = "") -> str:
    # The entry/usage/example tuple is the stable identity.  The human card
    # reference remains evidence and cannot make two entry cards collide.
    suffix = f"{entry_id}:u{int(usage_index)}:x{int(example_index)}"
    return _node("card", suffix)


def selected_word_node(
    entry_id: str,
    sense_index: int,
    usage_index: int,
    form_index: int,
    card_ref: str = "",
    example_index: int = 0,
    occurrence_id: str = "",
) -> str:
    suffix = f"{entry_id}:s{int(sense_index)}:u{int(usage_index)}:f{int(form_index)}"
    if _text(card_ref):
        suffix += f":c{_text(card_ref)}"
    if example_index:
        suffix += f":x{int(example_index)}"
    if _text(occurrence_id):
        suffix += f":o{_text(occurrence_id)}"
    return _node("selected-word", suffix)


def occurrence_node(loc: str) -> str:
    return _node("occurrence", loc)


def appearance_node(loc: str, index: int) -> str:
    return _node("appearance", f"{loc}:{int(index)}")


def _edge_id(edge_type: str, from_node_id: str, to_node_id: str, details: dict) -> str:
    identity = {
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "details": details,
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"edge:{digest}"


def make_edge(
    edge_type: str,
    from_node_id: str,
    to_node_id: str,
    status: str,
    *,
    evidence=None,
    guards=None,
    details=None,
    producer_id: str = PRODUCER_ID,
    producer_version: str = PRODUCER_VERSION,
) -> dict:
    if edge_type not in EDGE_TYPE_SET:
        raise ValueError(f"unknown edge type: {edge_type}")
    if status not in STATUS_SET:
        raise ValueError(f"unknown edge status: {status}")
    from_type = from_node_id.split(":", 1)[0]
    to_type = to_node_id.split(":", 1)[0]
    if from_type not in NODE_TYPE_SET or to_type not in NODE_TYPE_SET:
        raise ValueError(f"untyped graph endpoint: {from_node_id!r}, {to_node_id!r}")
    evidence = [item for item in (evidence or []) if isinstance(item, dict)]
    evidence = [
        {"address": _text(item.get("address")), "method": _text(item.get("method"))}
        for item in evidence
    ]
    details = dict(details or {})
    record = {
        "schema": SCHEMA,
        "edge_id": _edge_id(edge_type, from_node_id, to_node_id, details),
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "from_node_type": from_type,
        "to_node_id": to_node_id,
        "to_node_type": to_type,
        "status": status,
        "evidence": evidence,
        "producer": {"id": producer_id, "version": producer_version},
        "guards": sorted(set(_text(item) for item in (guards or []) if _text(item))),
    }
    if details:
        record["details"] = details
    return record


def _surface_keys(surface: str) -> tuple[str, str]:
    return bare(surface), norm_strict(surface)


def _root_key(root) -> str:
    if isinstance(root, (list, tuple)):
        return " ".join(_text(item) for item in root).strip()
    return " ".join(_text(root).split())


def _iter_entry_forms(entry: dict):
    """Yield documented surface records using the repository's 1-based indices."""

    entry_id = _entry_id(entry.get("id"))
    if not entry_id:
        return
    seen = set()
    headword = _text(entry.get("headword"))
    if headword:
        key = (headword, 0, 0, 0, "headword")
        seen.add(key)
        yield {
            "surface": headword,
            "sense_index": 1,
            "usage_index": 0,
            "form_index": 0,
            "address": f"entry:{entry_id}:headword",
            "method": "entry_headword",
            "kind": "headword",
        }
    for sense_index, sense in enumerate(entry.get("senses") or [], 1):
        surface = _text(sense.get("ar")) if isinstance(sense, dict) else ""
        if surface:
            key = (surface, sense_index, 0, 0, "sense")
            if key not in seen:
                seen.add(key)
                yield {
                    "surface": surface,
                    "sense_index": sense_index,
                    "usage_index": 0,
                    "form_index": 0,
                    "address": f"entry:{entry_id}:senses[{sense_index - 1}].ar",
                    "method": "entry_sense_identity",
                    "kind": "sense",
                }
    for usage_index, usage in enumerate(entry.get("usage") or [], 1):
        usage_sense = usage.get("sense") if isinstance(usage, dict) else None
        try:
            sense_index = int(usage_sense or usage_index)
        except (TypeError, ValueError):
            sense_index = usage_index
        for form_index, surface in enumerate((usage or {}).get("forms") or [], 1):
            surface = _text(surface)
            if not surface:
                continue
            key = (surface, sense_index, usage_index, form_index, "form")
            if key in seen:
                continue
            seen.add(key)
            yield {
                "surface": surface,
                "sense_index": sense_index,
                "usage_index": usage_index,
                "form_index": form_index,
                "address": (
                    f"entry:{entry_id}:usage[{usage_index - 1}].forms[{form_index - 1}]"
                ),
                "method": "documented_entry_form",
                "kind": "form",
            }


def _entry_indexes(entries: list[dict]):
    by_id = {}
    exact = defaultdict(list)
    strict = defaultdict(list)
    roots = defaultdict(list)
    for entry in entries:
        entry_id = _entry_id(entry.get("id"))
        if not entry_id:
            continue
        by_id[entry_id] = entry
        roots[_root_key(entry.get("root"))].append(entry_id)
        for form in _iter_entry_forms(entry):
            form = dict(form)
            form["entry_id"] = entry_id
            form["root"] = _root_key(entry.get("root"))
            exact[bare(form["surface"])].append(form)
            strict[norm_strict(form["surface"])].append(form)
    return by_id, exact, strict, roots


def _source_identity(value):
    match = _SOURCE_KEY_RE.fullmatch(_text(value).strip("/"))
    if not match:
        return None
    return match.group(1).lower(), int(match.group(2))


def _page_context_resolver(entries: list[dict]):
    by_id = {_entry_id(entry.get("id")): _entry_id(entry.get("id")) for entry in entries}
    by_source = {}
    for entry in entries:
        entry_id = _entry_id(entry.get("id"))
        if not entry_id:
            continue
        for source_key in entry.get("source_keys") or []:
            identity = _source_identity(source_key)
            if identity is not None:
                by_source[identity] = entry_id
    return by_id, by_source


def _resolve_page_context_entry(raw_entry_id, resolver):
    raw_entry_id = _entry_id(raw_entry_id)
    by_id, by_source = resolver
    if raw_entry_id in by_id:
        return raw_entry_id
    identity = _source_identity(raw_entry_id)
    return by_source.get(identity, raw_entry_id)


def _page_context_rows(whitelist_rows):
    result = defaultdict(list)
    for row in whitelist_rows:
        loc = _text(row.get("loc") or row.get("quran_loc"))
        if loc:
            result[loc].append(row)
    return result


def _appearance_surface(record: dict, source_by_loc: dict, appearance: dict) -> str:
    return _text(
        appearance.get("canonical_surface")
        or appearance.get("surface")
        or record.get("canonical_surface")
        or record.get("surface")
        or (source_by_loc.get(record.get("loc"), {}) or {}).get("surface")
    )


def _loc_from_row(row: dict) -> str:
    # The ledger keeps the display-local occurrence id and the canonical Quran
    # location separately for three repaired examples.  Canonical joins must
    # prefer the canonical Quran address; the local address remains evidence.
    for key in ("canonical_quran_loc", "quran_loc"):
        value = _text(row.get(key))
        if value.startswith("quran:"):
            return value.split(":", 1)[1]
        if value:
            return value
    for key in ("loc", "occurrence_id", "canonical_occurrence_id", "occurrence"):
        value = _text(row.get(key))
        if value.startswith("occurrence:"):
            return value.split(":", 1)[1]
        if value:
            return value
    address = row.get("display_local_address") or {}
    return _text(address.get("display_loc"))


def _indices_for_row(row: dict) -> tuple[int, int, int, int]:
    entry_id = _entry_id(row.get("entry_id"))
    def integer(key, default=1):
        try:
            return int(row.get(key) or default)
        except (TypeError, ValueError):
            return default
    return entry_id, integer("sense_index"), integer("usage_index"), integer("form_index")


def _card_example_index(row: dict) -> int:
    address = row.get("display_local_address") or {}
    for key in ("entry_example_index", "whitelist_example_card_index", "example_index"):
        try:
            if address.get(key) is not None:
                return max(1, int(address[key]))
        except (TypeError, ValueError):
            pass
    return 1


def _card_id_for_row(row: dict, entry_id: str, usage_index: int) -> str:
    return card_node(entry_id, usage_index, _card_example_index(row), _text(row.get("source_card_ref")))


def _selected_id_for_row(row: dict) -> str:
    entry_id, sense_index, usage_index, form_index = _indices_for_row(row)
    return selected_word_node(
        entry_id,
        sense_index,
        usage_index,
        form_index,
        _text(row.get("source_card_ref")),
        _card_example_index(row),
        _loc_from_row(row),
    )


def _fact_fields(fact: dict) -> dict:
    """Flatten common producer fact/projection shapes without changing them."""

    result = dict(fact)
    for nested_key in ("fact", "canonical_occurrence", "projection", "decision"):
        nested = result.get(nested_key)
        if isinstance(nested, dict):
            for key, value in nested.items():
                result.setdefault(key, value)
    result["fact_id"] = _text(
        result.get("fact_id") or result.get("id") or result.get("fact_key")
    )
    result["loc"] = _loc_from_row(result)
    result["entry_id"] = _entry_id(result.get("entry_id"))
    result["selected_surface"] = _text(
        result.get("selected_surface") or result.get("surface") or result.get("displayed_surface")
    )
    if not isinstance(result.get("evidence"), list):
        addresses = result.get("source_addresses") or result.get("addresses") or []
        if isinstance(addresses, str):
            addresses = [addresses]
        result["evidence"] = [
            {"address": _text(address), "method": "producer_source_address"}
            for address in addresses
            if _text(address)
        ]
    return result


def _fact_matches_row(fact: dict, row: dict, selected_id: str) -> bool:
    fact = _fact_fields(fact)
    fact_selected = _text(fact.get("selected_word_id"))
    if fact_selected and fact_selected == selected_id:
        return True
    fact_loc = _text(fact.get("loc"))
    row_loc = _loc_from_row(row)
    if fact_loc and row_loc and fact_loc == row_loc:
        fact_entry = _entry_id(fact.get("entry_id"))
        row_entry = _entry_id(row.get("entry_id"))
        fact_surface = _text(fact.get("selected_surface"))
        row_surface = _text(row.get("selected_surface"))
        return (not fact_entry or fact_entry == row_entry) and (
            not fact_surface or fact_surface == row_surface
        )
    return False


def _status_for_exact(facts: list[dict]) -> str:
    for fact in facts:
        status = _text(fact.get("status")).lower()
        certification = _text(fact.get("certification_status")).lower()
        if status == "certified" or certification == "certified":
            return "certified"
    return "deterministic_exact"


def _evidence_for_form(form: dict) -> list[dict]:
    return [{"address": form["address"], "method": form["method"]}]


def _append_edge(edges: list[dict], seen: set[str], *args, **kwargs) -> dict:
    item = make_edge(*args, **kwargs)
    if item["edge_id"] not in seen:
        seen.add(item["edge_id"])
        edges.append(item)
    return item


def _entry_page_edges(edges, seen, page_rows, loc, page_resolver):
    for row in page_rows.get(loc, []):
        page_entry = _entry_id(row.get("entry_id"))
        if not page_entry:
            continue
        resolved_page_entry = _resolve_page_context_entry(page_entry, page_resolver)
        surface = _text(row.get("surface"))
        _append_edge(
            edges,
            seen,
            "page_context_entry_edge",
            occurrence_node(loc),
            entry_node(resolved_page_entry),
            "deterministic_exact",
            evidence=[
                {
                    "address": f"whitelist:{loc}:entry_id",
                    "method": "whitelist_entry_id_page_context",
                }
            ],
            guards=["entry_id_is_verse_context", "never_lexeme_edge"],
            details={
                "loc": loc,
                "surface": surface,
                "page_context_only": True,
                "raw_entry_id": page_entry,
                "resolved_entry_id": resolved_page_entry,
                "source_key": _text(row.get("source_key")),
            },
        )


def _appearance_edges(edges, seen, appearance_rows, source_by_loc):
    for record in appearance_rows:
        loc = _text(record.get("loc"))
        if not loc:
            continue
        appearances = record.get("appearances") or []
        for index, appearance in enumerate(appearances, 1):
            surface = _appearance_surface(record, source_by_loc, appearance)
            _append_edge(
                edges,
                seen,
                "rendered_appearance_edge",
                occurrence_node(loc),
                appearance_node(loc, index),
                "deterministic_exact",
                evidence=[
                    {
                        "address": f"occurrence-appearances:{loc}:appearances[{index - 1}]",
                        "method": "existing_occurrence_appearance_index",
                    }
                ],
                guards=["canonical_projection_hash_present"],
                details={
                    "loc": loc,
                    "appearance_index": index,
                    "surface": surface,
                    "canonical_surface": _text(record.get("canonical_surface") or surface),
                    "surface_kind": _text(appearance.get("surface_kind")),
                    "entry_id": _entry_id(appearance.get("entry_id")),
                    "projection_hash": _text(record.get("projection_hash")),
                },
            )


def _source_and_relation_edges(edges, seen, row, selected_id, entry_id, usage_index, occurrence_id):
    card_id = _card_id_for_row(row, entry_id, usage_index)
    card_ref = _text(row.get("source_card_ref"))
    card_status = "deterministic_exact" if card_ref else "source_gap"
    card_method = "ledger_source_card_identity" if card_ref else "ledger_card_identity_missing"
    source_card = _append_edge(
        edges,
        seen,
        "source_card_edge",
        selected_id,
        card_id,
        card_status,
        evidence=[{"address": f"card:{card_ref}", "method": card_method}] if card_ref else [],
        guards=["card_identity_from_ledger"],
        details={"card_ref": card_ref, "source_card_text": _text(row.get("source_card_text"))},
    )
    photo_present = bool(row.get("source_photo_present"))
    _append_edge(
        edges,
        seen,
        "source_photo_edge",
        selected_id,
        card_id,
        "deterministic_exact" if photo_present else "source_gap",
        evidence=[{"address": f"card:{card_ref}:photo", "method": "ledger_source_photo"}]
        if photo_present
        else [],
        guards=["photo_is_source_evidence"],
        details={"card_ref": card_ref, "present": photo_present},
    )
    if occurrence_id:
        _append_edge(
            edges,
            seen,
            "selected_example_edge",
            card_id,
            occurrence_node(occurrence_id),
            "deterministic_exact",
            evidence=[
                {
                    "address": f"card:{card_ref}:example",
                    "method": "ledger_display_local_example",
                }
            ]
            if card_ref
            else [],
            guards=["selected_example_is_not_page_context"],
            details={"card_ref": card_ref, "selected_word_id": selected_id},
        )
    return card_id, source_card


def _surface_candidates(selected_surface, exact, strict):
    exact_candidates = list(exact.get(bare(selected_surface), [])) if selected_surface else []
    if exact_candidates:
        return "exact", exact_candidates
    strict_candidates = list(strict.get(norm_strict(selected_surface), [])) if selected_surface else []
    if strict_candidates:
        return "strict", strict_candidates
    return "none", []


def _make_crosswalk_edges(
    edges,
    seen,
    row,
    entries_by_id,
    exact,
    strict,
    roots,
    facts_by_row,
    page_entry_ids,
    source_by_loc=None,
):
    entry_id, sense_index, usage_index, form_index = _indices_for_row(row)
    if not entry_id:
        return None
    selected_surface = _text(row.get("selected_surface"))
    occurrence_id = _loc_from_row(row)
    selected_id = selected_word_node(
        entry_id,
        sense_index,
        usage_index,
        form_index,
        _text(row.get("source_card_ref")),
        _card_example_index(row),
        occurrence_id,
    )
    card_id, _ = _source_and_relation_edges(
        edges, seen, row, selected_id, entry_id, usage_index, occurrence_id
    )
    if occurrence_id:
        _append_edge(
            edges,
            seen,
            "canonical_occurrence_edge",
            selected_id,
            occurrence_node(occurrence_id),
            "deterministic_exact",
            evidence=[
                {
                    "address": f"ledger:{selected_id}:occurrence",
                    "method": "existing_vnmap_ledger_occurrence_id",
                }
            ],
            guards=["existing_occurrence_graph_only"],
            details={"loc": occurrence_id, "selected_word_id": selected_id},
        )
    address = row.get("display_local_address") or {}
    local_surface = _text(
        row.get("displayed_selected_surface") or row.get("displayed_surface") or selected_surface
    )
    if occurrence_id:
        canonical_surface = _text((source_by_loc or {}).get(occurrence_id, {}).get("surface")) or local_surface
        display_exact = bool(local_surface) and bare(local_surface) == bare(canonical_surface)
        _append_edge(
            edges,
            seen,
            "display_local_to_canonical_crosswalk_edge",
            card_id,
            occurrence_node(occurrence_id),
            "deterministic_exact" if display_exact else ("source_gap" if not local_surface else "ambiguous"),
            evidence=[
                {
                    "address": f"ledger:{address.get('card_ref') or row.get('source_card_ref')}:display_local",
                    "method": "exact_display_local_address",
                }
            ]
            if local_surface
            else [],
            guards=["display_surface_exact_guard", "canonical_surface_not_rewritten"],
            details={
                "display_local_address": address,
                "local_surface": local_surface,
                "canonical_surface": canonical_surface,
                "exact_surface": display_exact,
                "reconstruction_exact": display_exact,
                "selected_word_id": selected_id,
            },
        )

    match_kind, candidates = _surface_candidates(selected_surface, exact, strict)
    facts = facts_by_row.get(selected_id, [])
    # A strict-normalized match is recall only.  It is never promoted through
    # hamza-seat, ta marbuta/ha, or defective-letter differences.
    candidate_ids = sorted({item["entry_id"] for item in candidates})
    if match_kind == "exact" and len(candidate_ids) == 1:
        candidate_entry_id = candidate_ids[0]
        form = next(item for item in candidates if item["entry_id"] == candidate_entry_id)
        status = _status_for_exact(facts)
        details = {
            "surface": selected_surface,
            "orthography_key": bare(selected_surface),
            "candidate_basis": "exact_orthography_guarded_surface",
            "collision_set": candidate_ids,
            "form_address": form["address"],
            "page_context_origin": False,
        }
        lexeme = _append_edge(
            edges,
            seen,
            "lexeme_entry_edge",
            selected_id,
            entry_node(candidate_entry_id),
            status,
            evidence=_evidence_for_form(form),
            guards=[
                "orthography_guard_v1",
                "hamza_seat_preserved",
                "ta_marbuta_ha_distinct",
                "defective_spelling_distinct",
            ],
            details=details,
        )
        _append_edge(
            edges,
            seen,
            "form_entry_edge",
            selected_id,
            entry_node(candidate_entry_id),
            status,
            evidence=_evidence_for_form(form),
            guards=["documented_form_or_source_evidence", "orthography_guard_v1"],
            details={**details, "form_index": form.get("form_index", 0)},
        )
        _append_edge(
            edges,
            seen,
            "sense_entry_edge",
            sense_node(candidate_entry_id, form.get("sense_index") or sense_index),
            entry_node(candidate_entry_id),
            status,
            evidence=[
                {
                    "address": f"entry:{candidate_entry_id}:senses[{int(form.get('sense_index') or sense_index) - 1}]",
                    "method": "sense_identity_from_documented_form",
                }
            ],
            guards=["sense_identity_required"],
            details={"sense_id": sense_node(candidate_entry_id, form.get("sense_index") or sense_index)},
        )
        if occurrence_id and status == "certified":
            _append_edge(
                edges,
                seen,
                "lexeme_entry_edge",
                occurrence_node(occurrence_id),
                entry_node(candidate_entry_id),
                status,
                evidence=_evidence_for_form(form)
                + [{"address": f"occurrence:{occurrence_id}", "method": "certified_fact_attachment"}],
                guards=["certified_morphology_attached", "not_page_context_entry_id"],
                details={
                    **details,
                    "origin": "certified_occurrence_crosswalk",
                    "selected_word_id": selected_id,
                },
            )
        return {
            "selected_word_id": selected_id,
            "entry_id": entry_id,
            "matched_entry_ids": [candidate_entry_id],
            "status": status,
            "edge_kind": "exact",
            "card_id": card_id,
            "occurrence_id": occurrence_id,
            "facts": facts,
            "lexeme_edge": lexeme,
        }

    if match_kind == "exact" and len(candidate_ids) > 1:
        collision_set = candidate_ids
        for candidate_entry_id in collision_set:
            _append_edge(
                edges,
                seen,
                "lexeme_entry_edge",
                selected_id,
                entry_node(candidate_entry_id),
                "ambiguous",
                evidence=[
                    {
                        "address": f"ledger:{selected_id}:selected_surface",
                        "method": "exact_surface_collision",
                    }
                ],
                guards=["orthography_guard_v1", "duplicate_surface_abstention"],
                details={
                    "surface": selected_surface,
                    "collision_set": collision_set,
                    "candidate_basis": "exact_orthography_guarded_surface",
                },
            )
        return {
            "selected_word_id": selected_id,
            "entry_id": entry_id,
            "matched_entry_ids": collision_set,
            "status": "ambiguous",
            "edge_kind": "ambiguous",
            "card_id": card_id,
            "occurrence_id": occurrence_id,
            "facts": facts,
        }

    if match_kind == "strict":
        collision_set = candidate_ids
        for candidate_entry_id in collision_set:
            _append_edge(
                edges,
                seen,
                "lexeme_entry_edge",
                selected_id,
                entry_node(candidate_entry_id),
                "ambiguous" if len(collision_set) > 1 else "candidate",
                evidence=[
                    {
                        "address": f"ledger:{selected_id}:selected_surface",
                        "method": "strict_normalized_recall_only",
                    }
                ],
                guards=["orthography_mismatch_abstention", "never_fuzzy_promote"],
                details={
                    "surface": selected_surface,
                    "collision_set": collision_set,
                    "candidate_basis": "strict_normalized_recall",
                },
            )
        return {
            "selected_word_id": selected_id,
            "entry_id": entry_id,
            "matched_entry_ids": collision_set,
            "status": "ambiguous" if len(collision_set) > 1 else "candidate",
            "edge_kind": "strict",
            "card_id": card_id,
            "occurrence_id": occurrence_id,
            "facts": facts,
        }

    entry = entries_by_id.get(entry_id)
    root = _root_key((entry or {}).get("root"))
    root_candidates = list(roots.get(root, [])) if root else []
    for candidate_entry_id in root_candidates:
        _append_edge(
            edges,
            seen,
            "root_family_edge",
            selected_id,
            entry_node(candidate_entry_id),
            "candidate",
            evidence=[
                {
                    "address": f"entry:{candidate_entry_id}:root",
                    "method": "root_agreement_only",
                }
            ],
            guards=["root_agreement_never_lexeme_edge"],
            details={"root": root, "surface": selected_surface},
        )
    return {
        "selected_word_id": selected_id,
        "entry_id": entry_id,
        "matched_entry_ids": [],
        "status": "source_gap",
        "edge_kind": "none",
        "card_id": card_id,
        "occurrence_id": occurrence_id,
        "facts": facts,
    }


def _attach_facts(fact_rows, ledger_rows):
    facts_by_row = defaultdict(list)
    for fact in fact_rows:
        normalized = _fact_fields(fact)
        for row in ledger_rows:
            entry_id, sense_index, usage_index, form_index = _indices_for_row(row)
            selected_id = _selected_id_for_row(row)
            if _fact_matches_row(normalized, row, selected_id):
                facts_by_row[selected_id].append(normalized)
                break
    return facts_by_row


def _forward_record(info, edges_by_from):
    selected_id = info["selected_word_id"]
    relevant = edges_by_from.get(selected_id, [])
    statuses = Counter(
        item["status"]
        for item in relevant
        if item["edge_type"] in {"lexeme_entry_edge", "form_entry_edge"}
    )
    return {
        "schema": CROSSWALK_FORWARD_SCHEMA,
        "selected_word_id": selected_id,
        "source_entry_id": info["entry_id"],
        "matched_entry_ids": info["matched_entry_ids"],
        "crosswalk_status": info["status"],
        "edge_ids": sorted(item["edge_id"] for item in relevant),
        "lexeme_form_status_counts": dict(sorted(statuses.items())),
        "card_id": info["card_id"],
        "occurrence_id": info["occurrence_id"],
    }


def _reverse_records(forward, edges, entries):
    edges_by_pair = defaultdict(list)
    for edge_item in edges:
        if edge_item["edge_type"] not in {"lexeme_entry_edge", "form_entry_edge"}:
            continue
        edges_by_pair[(edge_item["from_node_id"], edge_item["to_node_id"])].append(edge_item)
    by_entry = {entry_node(entry_id): {"entry_id": entry_id} for entry_id in entries}
    for record in by_entry.values():
        record.update({"schema": CROSSWALK_REVERSE_SCHEMA, "selected_word_ids": [], "occurrence_ids": [], "edge_ids": []})
    for item in forward:
        for candidate in item["matched_entry_ids"]:
            record = by_entry.setdefault(
                entry_node(candidate),
                {
                    "schema": CROSSWALK_REVERSE_SCHEMA,
                    "entry_id": candidate,
                    "selected_word_ids": [],
                    "occurrence_ids": [],
                    "edge_ids": [],
                },
            )
            if item["selected_word_id"] not in record["selected_word_ids"]:
                record["selected_word_ids"].append(item["selected_word_id"])
            record["edge_ids"].extend(
                edge_item["edge_id"]
                for edge_item in edges_by_pair.get(
                    (item["selected_word_id"], entry_node(candidate)), []
                )
            )
        if item["occurrence_id"] and item["matched_entry_ids"]:
            for candidate in item["matched_entry_ids"]:
                status = item["crosswalk_status"]
                if status not in {"source_gap", "rejected"}:
                    record = by_entry[entry_node(candidate)]
                    if item["occurrence_id"] not in record["occurrence_ids"]:
                        record["occurrence_ids"].append(item["occurrence_id"])
    for edge_item in edges:
        if edge_item["edge_type"] != "lexeme_entry_edge" or edge_item["status"] != "certified":
            continue
        if edge_item["from_node_type"] != "occurrence":
            continue
        entry_id = edge_item["to_node_id"].split(":", 1)[1]
        record = by_entry.setdefault(
            edge_item["to_node_id"],
            {
                "schema": CROSSWALK_REVERSE_SCHEMA,
                "entry_id": entry_id,
                "selected_word_ids": [],
                "occurrence_ids": [],
                "edge_ids": [],
            },
        )
        loc = edge_item["from_node_id"].split(":", 1)[1]
        if loc not in record["occurrence_ids"]:
            record["occurrence_ids"].append(loc)
        record["edge_ids"].append(edge_item["edge_id"])
    for record in by_entry.values():
        record["selected_word_ids"] = sorted(set(record["selected_word_ids"]))
        record["occurrence_ids"] = sorted(set(record["occurrence_ids"]))
        record["edge_ids"] = sorted(set(record["edge_ids"]))
    return sorted(by_entry.values(), key=lambda item: item["entry_id"])


def _metrics(forward, reverse, edges, entries, ledger_rows, appearance_rows):
    usable = {"certified", "deterministic_exact", "candidate"}
    lexeme_form = [
        item
        for item in edges
        if item["edge_type"] in {"lexeme_entry_edge", "form_entry_edge"}
        and item["from_node_type"] == "selected-word"
    ]
    rows_by_crosswalk_status = Counter(item["crosswalk_status"] for item in forward)
    edge_by_status = Counter(item["status"] for item in lexeme_form)
    rows_any = sum(1 for item in forward if item["crosswalk_status"] not in {"source_gap", "rejected"})
    rows_usable = sum(1 for item in forward if item["crosswalk_status"] in usable)
    card_groups = defaultdict(list)
    entry_groups = defaultdict(list)
    for item in forward:
        card_groups[item["card_id"]].append(item)
        entry_groups[item["source_entry_id"]].append(item)
    cards_any = sum(1 for rows in card_groups.values() if all(row["crosswalk_status"] not in {"source_gap", "rejected"} for row in rows))
    cards_usable = sum(1 for rows in card_groups.values() if all(row["crosswalk_status"] in usable for row in rows))
    entries_any = sum(1 for rows in entry_groups.values() if any(row["crosswalk_status"] not in {"source_gap", "rejected"} for row in rows))
    entries_usable = sum(1 for rows in entry_groups.values() if any(row["crosswalk_status"] in usable for row in rows))
    cards_total = sum(
        len(usage.get("examples") or [])
        for entry in entries
        for usage in (entry.get("usage") or [])
        if isinstance(usage, dict)
    )
    return {
        "entries_total": len(entries),
        "cards_total": cards_total,
        "cards_with_selected_word_rows": len(card_groups),
        "cards_without_selected_word_rows": max(0, cards_total - len(card_groups)),
        "selected_word_rows_total": len(ledger_rows),
        "canonical_occurrences_total": len(appearance_rows),
        "rendered_appearances_total": sum(len(item.get("appearances") or []) for item in appearance_rows),
        "selected_word_rows_with_lexeme_or_form_edge": rows_any,
        "selected_word_rows_with_usable_lexeme_or_form_edge": rows_usable,
        "selected_word_rows_by_crosswalk_status": dict(sorted(rows_by_crosswalk_status.items())),
        "lexeme_form_edges_by_status": dict(sorted(edge_by_status.items())),
        "cards_all_selected_words_have_edge": cards_any,
        "cards_all_selected_words_have_usable_edge": cards_usable,
        "entries_with_lexeme_or_form_edge": entries_any,
        "entries_with_usable_lexeme_or_form_edge": entries_usable,
        "lexeme_form_edge_totals": dict(sorted(Counter(item["edge_type"] for item in lexeme_form).items())),
    }


def build_graph(
    *,
    entries,
    ledger_rows,
    whitelist_rows,
    appearance_rows,
    fact_rows=None,
    predicate_v3_rows=None,
):
    """Build a typed graph bundle from decoded source rows."""

    entries = list(entries or [])
    ledger_rows = list(ledger_rows or [])
    whitelist_rows = list(whitelist_rows or [])
    appearance_rows = list(appearance_rows or [])
    fact_rows = list(fact_rows or [])
    entries_by_id, exact, strict, roots = _entry_indexes(entries)
    page_resolver = _page_context_resolver(entries)
    page_rows = _page_context_rows(whitelist_rows)
    source_by_loc = {row.get("loc"): row for row in whitelist_rows if _text(row.get("loc"))}
    for loc in sorted(set(page_rows) | {row.get("loc") for row in appearance_rows if row.get("loc")}):
        _ = loc
    edges = []
    seen = set()
    for loc in sorted(page_rows):
        _entry_page_edges(edges, seen, page_rows, loc, page_resolver)
    _appearance_edges(edges, seen, appearance_rows, source_by_loc)
    facts_by_row = _attach_facts(fact_rows, ledger_rows)
    infos = []
    for row in ledger_rows:
        info = _make_crosswalk_edges(
            edges,
            seen,
            row,
            entries_by_id,
            exact,
            strict,
            roots,
            facts_by_row,
            {item["to_node_id"] for item in edges if item["edge_type"] == "page_context_entry_edge"},
            source_by_loc,
        )
        if info:
            infos.append(info)
        if info and info["occurrence_id"]:
            occurrence = occurrence_node(info["occurrence_id"])
            for fact in info["facts"]:
                fact_evidence = fact.get("evidence") or []
                target = entry_node(fact.get("entry_id") or info["entry_id"])
                _append_edge(
                    edges,
                    seen,
                    "decision_evidence_edge",
                    occurrence,
                    target,
                    "certified" if _text(fact.get("status")).lower() == "certified" else "candidate",
                    evidence=fact_evidence,
                    guards=["producer_fact_attached", "source_fact_not_invented"],
                    details={"fact_id": fact.get("fact_id"), "selected_word_id": info["selected_word_id"]},
                )
    # A fact is attached only when it matched a ledger selected word.  This
    # intentionally leaves unmatched facts visible to the orphan validator.
    for info in infos:
        if info["occurrence_id"] and info["status"] == "certified" and info["matched_entry_ids"]:
            candidate = info["matched_entry_ids"][0]
            form_edge = next(
                (
                    item
                    for item in edges
                    if item["edge_type"] == "form_entry_edge"
                    and item["from_node_id"] == info["selected_word_id"]
                    and item["to_node_id"] == entry_node(candidate)
                ),
                None,
            )
            if form_edge:
                _append_edge(
                    edges,
                    seen,
                    "lexeme_entry_edge",
                    occurrence_node(info["occurrence_id"]),
                    entry_node(candidate),
                    "certified",
                    evidence=form_edge["evidence"]
                    + [{"address": f"occurrence:{info['occurrence_id']}", "method": "certified_fact_attachment"}],
                    guards=["certified_morphology_attached", "not_page_context_entry_id"],
                    details={
                        "origin": "certified_occurrence_crosswalk",
                        "selected_word_id": info["selected_word_id"],
                        "surface": next(
                            item["details"].get("surface", "")
                            for item in edges
                            if item["edge_type"] == "lexeme_entry_edge"
                            and item["from_node_id"] == info["selected_word_id"]
                            and item["to_node_id"] == entry_node(candidate)
                        ),
                    },
                )
    edges_by_from = defaultdict(list)
    for edge in edges:
        edges_by_from[edge["from_node_id"]].append(edge)
    forward = [_forward_record(info, edges_by_from) for info in infos]
    reverse = _reverse_records(forward, edges, entries_by_id)
    return {
        "schema": "qamus.typed_edge_bundle.v1",
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "edges": sorted(edges, key=lambda item: item["edge_id"]),
        "forward": sorted(forward, key=lambda item: item["selected_word_id"]),
        "reverse": reverse,
        "metrics": _metrics(forward, reverse, edges, entries, ledger_rows, appearance_rows),
        "predicate_v3_rows": len(predicate_v3_rows or []),
    }


# --------------------------------------------------------------------------- #
# citation_form_display_edge emission (GRAPH-BACKLINK-REPAIR-PREP-2026-07-29 §1/§2)
#
# 4,930 of the 6,677 crosswalk-missing selected-word rows are dictionary
# citation forms rendered display-locally: the entry page shows a lemma that is
# NOT a token of the cited āyah.  Forcing a display_local_to_canonical crosswalk
# for them would assert a FALSE canonical loc.  This mode re-types them with a
# truthful lexeme-level edge (selected-word -> entry) that NEVER carries a
# canonical loc (``no_canonical_loc_guard``); Qurʾānic witnesses elsewhere are
# recorded as recall evidence only.  The remaining 1,747 attachable rows are
# emitted as a deterministic authoring queue (Queue A), 2-vote-routed for the
# ambiguous multi-position cases.
# --------------------------------------------------------------------------- #
CITATION_PRODUCER = {"id": "citation_form_display.v1", "version": "1"}
CITATION_RETIRES_SATISFIED_BY_DESIGN = [
    "display_local_to_canonical_crosswalk_missing",
    "missing_quran_wbw_edge",
    "canonical_occurrence_appearance_missing",
]
_CROSSWALK_MISSING = "display_local_to_canonical_crosswalk_missing"
_MAX_WITNESS_EVIDENCE = 3


def _nfc(value: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", _text(value))


def _card_refs(row: dict):
    refs = []
    for ref in row.get("source_card_refs") or []:
        parts = str(ref).split(":")
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            refs.append((int(parts[0]), int(parts[1])))
    return refs


def classify_attachability(row, by_ayah, strict_corpus, lenient_corpus):
    """Classify one crosswalk-missing row per the §2 sweep method.

    Returns (klass, payload) where klass is one of: multiword, attach_exact,
    attach_norm, ambiguous, cite_elsewhere_strict, cite_lenient, cite_never,
    empty.
    """

    from tools.normalize_ar import norm, norm_strict

    selected = _nfc(row.get("selected_surface"))
    if not selected:
        return "empty", {}
    if " " in selected:
        return "multiword", {}
    tokens = [
        (loc, surface)
        for ref in _card_refs(row)
        for loc, surface in by_ayah.get(ref, [])
    ]
    exact_locs = sorted({loc for loc, surface in tokens if _nfc(surface) == selected})
    if exact_locs:
        if len(exact_locs) == 1:
            return "attach_exact", {"attach_locs": exact_locs}
        return "ambiguous", {"attach_locs": exact_locs, "tier": "exact"}
    strict_key = norm_strict(selected)
    strict_locs = sorted({loc for loc, surface in tokens if norm_strict(surface) == strict_key})
    if strict_locs:
        if len(strict_locs) == 1:
            return "attach_norm", {"attach_locs": strict_locs}
        return "ambiguous", {"attach_locs": strict_locs, "tier": "strict_normalized"}
    witness = strict_corpus.get(strict_key) or []
    if witness:
        return "cite_elsewhere_strict", {"witness_locs": sorted(witness)}
    lenient_witness = lenient_corpus.get(norm(selected)) or []
    if lenient_witness:
        return "cite_lenient", {"witness_locs": sorted(lenient_witness)}
    return "cite_never", {}


def _citation_status(selected: str, entry: dict, exact_index) -> tuple[str, str]:
    """Packet §1 rule 3: reuse the status vocabulary, never extend it."""

    own_surfaces = {_nfc(form["surface"]) for form in _iter_entry_forms(entry or {})}
    collision_ids = sorted({item["entry_id"] for item in exact_index.get(bare(selected), [])})
    if len(collision_ids) > 1:
        return "ambiguous", ",".join(collision_ids)
    if _nfc(selected) in own_surfaces:
        return "deterministic_exact", ""
    return "candidate", ""


def build_citation_display(entries, ledger_rows, corpus_rows):
    """Emit citation-display edges (Queue B) + the attachable queue (Queue A)."""

    from tools.normalize_ar import norm, norm_strict

    entries = list(entries or [])
    entries_by_id, exact_index, _strict_index, _roots = _entry_indexes(entries)
    by_ayah = defaultdict(list)
    strict_corpus = defaultdict(list)
    lenient_corpus = defaultdict(list)
    for token in corpus_rows or []:
        loc = _text(token.get("loc"))
        surface = _text(token.get("surface"))
        parts = loc.split(":")
        if len(parts) != 3:
            continue
        by_ayah[(int(parts[0]), int(parts[1]))].append((loc, surface))
        strict_corpus[norm_strict(surface)].append(loc)
        lenient_corpus[norm(surface)].append(loc)

    display_basis_by_class = {
        "multiword": "multiword_phrase",
        "cite_elsewhere_strict": "corpus_witness_elsewhere",
        "cite_lenient": "corpus_witness_elsewhere",
        "cite_never": "never_a_corpus_token",
    }
    witness_method_by_class = {
        "cite_elsewhere_strict": "surface_match_strict_witness_only",
        "cite_lenient": "surface_match_lenient_witness_only",
    }
    edges = []
    queue = []
    seen = set()
    counts = Counter()
    guard_blocked = 0
    for row in ledger_rows or []:
        if _CROSSWALK_MISSING not in (row.get("missing_edges") or []):
            continue
        counts["crosswalk_missing_rows"] += 1
        klass, payload = classify_attachability(row, by_ayah, strict_corpus, lenient_corpus)
        counts[klass] += 1
        entry_id = _entry_id(row.get("entry_id"))
        if not entry_id:
            counts["skipped_no_entry_id"] += 1
            continue
        selected_id = _selected_id_for_row(row)
        selected = _nfc(row.get("selected_surface"))
        base = {
            "entry_id": entry_id,
            "source_key": _text(row.get("source_key")),
            "proposal_vn_tranche": _text(row.get("proposal_vn_tranche")),
            "selected_surface": selected,
            "selected_word_id": selected_id,
            "card_refs": [f"{s}:{a}" for s, a in _card_refs(row)],
        }
        if klass in ("attach_exact", "attach_norm", "ambiguous"):
            tier = payload.get("tier") or (
                "exact" if klass == "attach_exact" else "strict_normalized"
            )
            status = "ambiguous" if klass == "ambiguous" else "candidate"
            review_route = (
                "two_vote_disambiguation"
                if klass == "ambiguous"
                else ("none_deterministic_prefill" if klass == "attach_exact"
                      else "orthography_guard_then_two_vote")
            )
            queue.append({
                "schema": "qamus.crosswalk_attach_queue.v1",
                **base,
                "match_tier": tier,
                "attach_locs": payload["attach_locs"],
                "status": status,
                "review_route": review_route,
                "proposed_edge_type": "display_local_to_canonical_crosswalk_edge",
                "producer": dict(CITATION_PRODUCER),
            })
            continue
        if klass in ("empty",):
            continue
        # Queue B: citation_form_display_edge.  no_canonical_loc_guard: a row
        # that still carries a canonical loc claim may not be re-typed here.
        if _text(row.get("occurrence_id")) or _text(row.get("canonical_quran_loc")):
            guard_blocked += 1
            counts["no_canonical_loc_guard_blocked"] += 1
            continue
        status, collision = _citation_status(selected, entries_by_id.get(entry_id), exact_index)
        usage_index = int(row.get("usage_index") or 1)
        example_index = _card_example_index(row)
        evidence = [{
            "address": f"qamus:{entry_id}#field=usage[{usage_index - 1}].examples[{example_index - 1}]",
            "method": "display_local_render",
        }]
        witness_locs = payload.get("witness_locs") or []
        for loc in witness_locs[:_MAX_WITNESS_EVIDENCE]:
            evidence.append({
                "address": f"quran:{loc}",
                "method": witness_method_by_class[klass],
            })
        details = {
            **base,
            "display_basis": display_basis_by_class[klass],
            "witness_tier": {"cite_elsewhere_strict": "strict",
                             "cite_lenient": "lenient"}.get(klass),
            "witness_loc_count": len(witness_locs),
            "collision_set": collision or None,
            "retires_as_satisfied_by_design": list(CITATION_RETIRES_SATISFIED_BY_DESIGN),
        }
        details = {key: value for key, value in details.items() if value not in (None, "")}
        item = make_edge(
            "citation_form_display_edge",
            selected_id,
            entry_node(entry_id),
            status,
            evidence=evidence,
            guards=["no_canonical_loc_guard", "orthography_guard_v1"],
            details=details,
            producer_id=CITATION_PRODUCER["id"],
            producer_version=CITATION_PRODUCER["version"],
        )
        item["display_basis"] = display_basis_by_class[klass]
        if item["edge_id"] not in seen:
            seen.add(item["edge_id"])
            edges.append(item)

    violations = citation_guard_violations(edges)
    if violations:
        raise ValueError("no_canonical_loc_guard violated: " + "; ".join(violations[:5]))
    metrics = {
        "schema": "qamus.citation_form_display.metrics.v1",
        "producer": dict(CITATION_PRODUCER),
        "classification_counts": dict(sorted(counts.items())),
        "queue_a_rows": len(queue),
        "queue_b_edges": len(edges),
        "queue_b_status_counts": dict(sorted(Counter(item["status"] for item in edges).items())),
        "queue_b_display_basis_counts": dict(sorted(Counter(item["display_basis"] for item in edges).items())),
        "queue_a_status_counts": dict(sorted(Counter(item["status"] for item in queue).items())),
        "no_canonical_loc_guard_blocked": guard_blocked,
        "retires_as_satisfied_by_design": list(CITATION_RETIRES_SATISFIED_BY_DESIGN),
        "candidate_only": True,
    }
    return {"edges": edges, "queue": queue, "metrics": metrics}


def citation_guard_violations(edges) -> list[str]:
    """no_canonical_loc_guard: a citation edge may not target/carry a canonical
    loc, and the stream may not co-emit a canonical_occurrence_edge for the same
    selected-word node."""

    violations = []
    citation_nodes = set()
    for item in edges or []:
        if item.get("edge_type") != "citation_form_display_edge":
            continue
        citation_nodes.add(item.get("from_node_id"))
        if item.get("to_node_type") not in {"entry", "sense"}:
            violations.append(f"citation edge targets non-lexeme node: {item.get('edge_id')}")
        details = item.get("details") or {}
        for key in ("loc", "occurrence_id", "canonical_quran_loc", "attach_locs"):
            if details.get(key):
                violations.append(f"citation edge carries canonical loc claim: {item.get('edge_id')}")
        for ev in item.get("evidence") or []:
            method = _text(ev.get("method"))
            if _text(ev.get("address")).startswith("quran:") and "witness_only" not in method:
                violations.append(f"citation witness evidence is not witness-only: {item.get('edge_id')}")
        if "no_canonical_loc_guard" not in (item.get("guards") or []):
            violations.append(f"citation edge missing no_canonical_loc_guard: {item.get('edge_id')}")
    for item in edges or []:
        if item.get("edge_type") == "canonical_occurrence_edge" and item.get("from_node_id") in citation_nodes:
            violations.append(
                f"canonical_occurrence_edge co-emitted for citation node: {item.get('edge_id')}"
            )
    return violations


def _write_pretty_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _write_bundle(bundle: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "typed-edge-graph.jsonl", bundle["edges"])
    write_jsonl(output_dir / "lexeme-entry-crosswalk.forward.jsonl", bundle["forward"])
    write_jsonl(output_dir / "lexeme-entry-crosswalk.reverse.jsonl", bundle["reverse"])
    with (output_dir / "edge-metrics.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(bundle["metrics"], handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def build_from_paths(args) -> dict:
    entries = read_jsonl(args.entries)
    ledger = read_jsonl(args.ledger)
    whitelist = read_jsonl(args.whitelist)
    appearances = read_jsonl(args.appearances)
    facts = []
    for path in args.fact:
        facts.extend(read_jsonl(path))
    predicate = []
    for path in args.predicate_v3:
        predicate.extend(read_jsonl(path))
    bundle = build_graph(
        entries=entries,
        ledger_rows=ledger,
        whitelist_rows=whitelist,
        appearance_rows=appearances,
        fact_rows=facts,
        predicate_v3_rows=predicate,
    )
    _write_bundle(bundle, Path(args.output_dir))
    return bundle


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--whitelist")
    parser.add_argument("--appearances")
    parser.add_argument("--fact", action="append", default=[])
    parser.add_argument("--predicate-v3", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--emit-citation-display", action="store_true",
                        help="emit citation_form_display_edge stream (Queue B) + "
                             "the attachable crosswalk queue (Queue A) from the "
                             "crosswalk-missing ledger rows")
    parser.add_argument("--corpus",
                        help="quran-loc-surface index JSONL (citation-display mode)")
    args = parser.parse_args(argv)
    if args.emit_citation_display:
        if not args.corpus:
            parser.error("--emit-citation-display requires --corpus")
        result = build_citation_display(
            read_jsonl(args.entries),
            read_jsonl(args.ledger),
            read_jsonl(args.corpus),
        )
        output_dir = Path(args.output_dir)
        write_jsonl(output_dir / "citation-display-edges.jsonl", result["edges"])
        write_jsonl(output_dir / "crosswalk-attach-queue.jsonl", result["queue"])
        _write_pretty_json(
            output_dir / "citation-display-edges.meta.json",
            {**result["metrics"],
             "artifact": "citation-display-edges.jsonl",
             "regenerate": ("python tools/build_typed_edge_crosswalk.py --emit-citation-display "
                            "--entries qamus/data/current/entries.jsonl --ledger vn-ledger.jsonl "
                            "--corpus qamus/indexes/quran-loc-surface/index.jsonl "
                            "--output-dir qamus/lattice")},
        )
        _write_pretty_json(
            output_dir / "crosswalk-attach-queue.meta.json",
            {"schema": "qamus.crosswalk_attach_queue.meta.v1",
             "artifact": "crosswalk-attach-queue.jsonl",
             "rows": len(result["queue"]),
             "status_counts": result["metrics"]["queue_a_status_counts"],
             "producer": dict(CITATION_PRODUCER),
             "candidate_only": True,
             "regenerate": ("python tools/build_typed_edge_crosswalk.py --emit-citation-display "
                            "--entries qamus/data/current/entries.jsonl --ledger vn-ledger.jsonl "
                            "--corpus qamus/indexes/quran-loc-surface/index.jsonl "
                            "--output-dir qamus/lattice")},
        )
        print(json.dumps(result["metrics"], ensure_ascii=False, sort_keys=True))
        return 0
    if not (args.whitelist and args.appearances):
        parser.error("--whitelist and --appearances are required outside citation-display mode")
    bundle = build_from_paths(args)
    print(json.dumps(bundle["metrics"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
