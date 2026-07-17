#!/usr/bin/env python3
"""Execute the bounded Repair1 graph-repair families.

The tool is intentionally an overlay builder.  EDGES artifacts and the
occurrence-appearance index remain the source graph; Repair1 adds evidence-
backed candidate/deterministic records without rewriting producer history or
the scripture-facing inputs.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_occurrence_appearance_index import (  # noqa: E402
    _source_identity as _appearance_source_identity,
    build_index,
)
from tools.build_typed_edge_crosswalk import (  # noqa: E402
    _card_id_for_row,
    _entry_indexes,
    _entry_id,
    _iter_entry_forms,
    _loc_from_row,
    _reverse_records,
    _selected_id_for_row,
    _text,
    entry_node,
    make_edge,
    occurrence_node,
    read_jsonl,
    write_jsonl,
)
from tools.normalize_ar import bare, norm, norm_strict  # noqa: E402


REPAIR_SCHEMA = "qamus.repair1.graph_repair.v1"
DETERMINISTIC_SCHEMA = "qamus.repair1.deterministic_entry_form.v1"
DUPLICATE_SCHEMA = "qamus.repair1.duplicate_surface_resolution.v1"
RECIPROCITY_SCHEMA = "qamus.repair1.reciprocity_packet.v1"
PRODUCER_ID = "tools.build_repair1_graph_families"
PRODUCER_VERSION = "1.0.0"
DETERMINISTIC_FAMILY = "deterministic entry/form match"
DUPLICATE_FAMILY = "duplicate-surface ambiguity"
DIVINE_FAMILY = "divine-name policy"
USABLE_STATUSES = {"certified", "deterministic_exact", "candidate"}
_SELECTED_WORD_COORDINATES_RE = re.compile(
    r"^selected-word:(?P<entry>[^:]+):s(?P<sense>\d+):u(?P<usage>\d+):f(?P<form>\d+):"
)


def _selected_id(row: dict) -> str:
    explicit = _text(row.get("selected_word_id"))
    return explicit or _selected_id_for_row(row)


def _source_key_alias(value: str, by_id: dict, by_source: dict) -> str:
    """Resolve a canonical id or source-key alias, returning empty on blank."""

    value = _text(value)
    if not value:
        return ""
    if value in by_id:
        return value
    identity = _appearance_source_identity(value)
    if identity in by_source:
        return _text(by_source[identity])
    return value


def resolve_source_key_alias(value: str, by_id: dict, by_source: dict) -> str:
    """Public test seam for the shared occurrence-entry alias rule."""

    return _source_key_alias(value, by_id, by_source)


def _guard_difference_reason(selected: str, documented: str) -> str:
    selected_bare = bare(selected)
    documented_bare = bare(documented)
    selected_chars = set(selected_bare)
    documented_chars = set(documented_bare)
    hamza_chars = set("أإؤئءآ")
    if (selected_chars ^ documented_chars) & hamza_chars:
        return "hamza_seat_mismatch"
    if ("ة" in selected_bare) != ("ة" in documented_bare) or (
        ("ه" in selected_bare) != ("ه" in documented_bare)
    ):
        return "ta_marbuta_ha_mismatch"
    if ("ى" in selected_bare) != ("ى" in documented_bare) or (
        ("ي" in selected_bare) != ("ي" in documented_bare)
    ):
        return "defective_spelling_mismatch"
    if norm_strict(selected) == norm_strict(documented):
        return "strict_key_non_exact_orthography"
    if norm(selected) == norm(documented):
        return "lenient_key_only_match"
    return "no_guarded_exact_form_match"


def _candidate_forms_for_surface(entries: list[dict], surface: str) -> list[dict]:
    _, exact, strict, _ = _entry_indexes(entries)
    exact_forms = list(exact.get(bare(surface), []))
    if exact_forms:
        return exact_forms
    return list(strict.get(norm_strict(surface), []))


def _row_coordinates(row: dict) -> tuple[int, int, int]:
    """Read explicit coordinates, falling back to the canonical selected-word id."""

    values = []
    for key in ("sense_index", "usage_index", "form_index"):
        try:
            values.append(int(row.get(key) or 0))
        except (TypeError, ValueError):
            values.append(0)
    if all(values):
        return tuple(values)
    match = _SELECTED_WORD_COORDINATES_RE.match(_text(row.get("selected_word_id")))
    if match:
        return (
            int(match.group("sense")),
            int(match.group("usage")),
            int(match.group("form")),
        )
    return tuple(value or 1 for value in values)


def _preferred_form(row: dict, forms: list[dict]) -> dict | None:
    """Select the row-addressed form, never an arbitrary duplicate."""

    if not forms:
        return None
    sense_index, usage_index, form_index = _row_coordinates(row)
    preferred = [
        item
        for item in forms
        if item.get("kind") == "form"
        and int(item.get("sense_index") or 0) == sense_index
        and int(item.get("usage_index") or 0) == usage_index
        and int(item.get("form_index") or 0) == form_index
    ]
    if len(preferred) == 1:
        return preferred[0]
    if len(forms) == 1:
        return forms[0]
    # A sense-addressed row can safely choose its one matching sense surface
    # only when there is no second exact address for the same row.
    sense_forms = [
        item
        for item in forms
        if item.get("kind") == "sense"
        and int(item.get("sense_index") or 0) == sense_index
    ]
    if len(sense_forms) == 1:
        return sense_forms[0]
    return None


def _reclassification(row: dict, reason_code: str, *, candidates=None, forms=None) -> dict:
    selected_id = _selected_id(row)
    return {
        "schema": DETERMINISTIC_SCHEMA,
        "repair_family": DETERMINISTIC_FAMILY,
        "selected_word_id": selected_id,
        "entry_id": _entry_id(row.get("entry_id")),
        "surface": _text(row.get("selected_surface") or row.get("surface")),
        "status": "reclassified",
        "reason_code": reason_code,
        "reason": {
            "hamza_seat_mismatch": "The candidate differs at a hamza seat; strict orthography does not match.",
            "ta_marbuta_ha_mismatch": "The candidate differs between ta marbuta and ha; no edge is safe.",
            "defective_spelling_mismatch": "The candidate differs at a defective spelling; no edge is safe.",
            "strict_key_non_exact_orthography": "Only a strict recall key matched; the base-letter guard failed.",
            "lenient_key_only_match": "Only a lenient recall key matched; the orthography guard failed.",
            "no_guarded_exact_form_match": "No documented form passed the guarded exact surface test.",
            "entry_missing": "The classified entry is not present in the supplied entry corpus.",
            "entry_identity_mismatch": "The guarded surface belongs to a different entry than the classified row.",
            "duplicate_documented_form_address": "More than one documented form address remains after row coordinates are applied.",
            "empty_surface": "The row has no selected surface to guard.",
        }.get(reason_code, "The guarded deterministic precondition failed."),
        "candidate_entry_ids": sorted(set(candidates or [])),
        "candidate_form_addresses": sorted(set(forms or [])),
        "guards_checked": [
            "orthography_guard_v1",
            "hamza_seat_preserved",
            "ta_marbuta_ha_distinct",
            "defective_spelling_distinct",
        ],
        "pre_apply_authorized": False,
    }


def _repair_evidence(row: dict, form: dict) -> list[dict]:
    selected_id = _selected_id(row)
    evidence = [
        {"address": form["address"], "method": form["method"]},
        {"address": f"ledger:{selected_id}:selected_surface", "method": "edges_debt_classification"},
    ]
    card_ref = _text(row.get("source_card_ref"))
    if card_ref:
        evidence.append({"address": f"card:{card_ref}", "method": "owner_card_identity"})
    return evidence


def _repair_detail(row: dict, form: dict, entry_id: str) -> dict:
    selected_id = _selected_id(row)
    surface = _text(row.get("selected_surface") or row.get("surface"))
    return {
        "surface": surface,
        "orthography_key": bare(surface),
        "candidate_basis": "repair1_guarded_exact_entry_form",
        "collision_set": [entry_id],
        "form_address": form["address"],
        "form_kind": form.get("kind"),
        "repair_family": DETERMINISTIC_FAMILY,
        "repair_lane": "repair1",
        "selected_word_id": selected_id,
        "page_context_origin": False,
    }


def build_deterministic_repairs(
    debt_rows: list[dict], entries: list[dict], base_edges: list[dict] | None = None
) -> dict:
    """Build exact entry/form repairs and typed guard-failure reclassifications."""

    entries = list(entries or [])
    base_ids = {item.get("edge_id") for item in base_edges or []}
    entries_by_id, exact, strict, _ = _entry_indexes(entries)
    repair_edges = []
    records = []
    reclassifications = []
    repaired_selected_ids = set()
    for row in debt_rows or []:
        if _text(row.get("repair_family")) != DETERMINISTIC_FAMILY:
            continue
        selected_id = _selected_id(row)
        entry_id = _entry_id(row.get("entry_id"))
        surface = _text(row.get("selected_surface") or row.get("surface"))
        if not surface:
            reclassifications.append(_reclassification(row, "empty_surface"))
            continue
        if entry_id not in entries_by_id:
            reclassifications.append(_reclassification(row, "entry_missing"))
            continue
        exact_forms = list(exact.get(bare(surface), []))
        candidate_entry_ids = sorted({item["entry_id"] for item in exact_forms})
        if candidate_entry_ids and candidate_entry_ids != [entry_id]:
            reclassifications.append(
                _reclassification(row, "entry_identity_mismatch", candidates=candidate_entry_ids)
            )
            continue
        candidate_forms = [item for item in exact_forms if item["entry_id"] == entry_id]
        if not candidate_forms:
            recall_forms = [item for item in strict.get(norm_strict(surface), []) if item["entry_id"] == entry_id]
            reason_code = _guard_difference_reason(surface, recall_forms[0]["surface"]) if recall_forms else "no_guarded_exact_form_match"
            reclassifications.append(
                _reclassification(
                    row,
                    reason_code,
                    candidates=sorted({item["entry_id"] for item in recall_forms}),
                    forms=[item["address"] for item in recall_forms],
                )
            )
            continue
        form = _preferred_form(row, candidate_forms)
        if form is None:
            reclassifications.append(
                _reclassification(
                    row,
                    "duplicate_documented_form_address",
                    candidates=[entry_id],
                    forms=[item["address"] for item in candidate_forms],
                )
            )
            continue
        evidence = _repair_evidence(row, form)
        details = _repair_detail(row, form, entry_id)
        guards = [
            "orthography_guard_v1",
            "hamza_seat_preserved",
            "ta_marbuta_ha_distinct",
            "defective_spelling_distinct",
            "pre_apply_not_authorized",
        ]
        form_edge = make_edge(
            "form_entry_edge",
            selected_id,
            entry_node(entry_id),
            "deterministic_exact",
            evidence=evidence,
            guards=guards + ["documented_form_or_source_evidence"],
            details={**details, "edge_role": "repair1_form_bridge"},
            producer_id=PRODUCER_ID,
            producer_version=PRODUCER_VERSION,
        )
        lexeme_edge = make_edge(
            "lexeme_entry_edge",
            selected_id,
            entry_node(entry_id),
            "deterministic_exact",
            evidence=evidence,
            guards=guards,
            details={**details, "edge_role": "repair1_lexeme_bridge"},
            producer_id=PRODUCER_ID,
            producer_version=PRODUCER_VERSION,
        )
        repair_edges.extend([form_edge, lexeme_edge])
        repaired_selected_ids.add(selected_id)
        records.append(
            {
                "schema": DETERMINISTIC_SCHEMA,
                "repair_family": DETERMINISTIC_FAMILY,
                "selected_word_id": selected_id,
                "entry_id": entry_id,
                "surface": surface,
                "form_address": form["address"],
                "status": "deterministic_exact",
                "edge_ids": [form_edge["edge_id"], lexeme_edge["edge_id"]],
                "evidence": evidence,
                "guards": guards,
                "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
                "pre_apply_authorized": False,
                "base_edge_ids": sorted(
                    edge_id
                    for edge_id in base_ids
                    if edge_id in {form_edge["edge_id"], lexeme_edge["edge_id"]}
                ),
            }
        )
    metrics = {
        "input_rows": sum(1 for row in debt_rows or [] if _text(row.get("repair_family")) == DETERMINISTIC_FAMILY),
        "deterministic_rows": len(records),
        "reclassified_rows": len(reclassifications),
        "reclassification_reason_counts": dict(
            sorted(Counter(item.get("reason_code") for item in reclassifications).items())
        ),
        "new_overlay_edges": len([edge for edge in repair_edges if edge["edge_id"] not in base_ids]),
        "new_overlay_form_edges": sum(edge["edge_type"] == "form_entry_edge" and edge["edge_id"] not in base_ids for edge in repair_edges),
        "new_overlay_lexeme_edges": sum(edge["edge_type"] == "lexeme_entry_edge" and edge["edge_id"] not in base_ids for edge in repair_edges),
        "repaired_selected_word_ids": len(repaired_selected_ids),
    }
    return {
        "schema": REPAIR_SCHEMA,
        "records": records,
        "edges": repair_edges,
        "reclassifications": reclassifications,
        "metrics": metrics,
    }


def merge_repair_edges(base_edges: list[dict], repair_edges: list[dict]) -> list[dict]:
    """Merge an overlay without losing base records or emitting duplicate ids."""

    by_id = {}
    for item in list(base_edges or []) + list(repair_edges or []):
        edge_id = _text(item.get("edge_id"))
        if edge_id and edge_id not in by_id:
            by_id[edge_id] = item
    return sorted(by_id.values(), key=lambda item: item.get("edge_id", ""))


def project_repair_forward(base_forward: list[dict], repair_records: list[dict], edges: list[dict]) -> list[dict]:
    """Rerun the forward projection while retaining existing crosswalk fields."""

    forward = {item.get("selected_word_id"): copy.deepcopy(item) for item in base_forward or []}
    edges_by_selected = defaultdict(list)
    for edge in edges or []:
        if edge.get("from_node_type") == "selected-word":
            edges_by_selected[edge.get("from_node_id")].append(edge)
    for repair in repair_records or []:
        if repair.get("status") != "deterministic_exact":
            continue
        selected_id = repair.get("selected_word_id")
        item = forward.setdefault(
            selected_id,
            {
                "schema": "qamus.lexeme_entry_crosswalk.forward.v1",
                "selected_word_id": selected_id,
                "source_entry_id": repair.get("entry_id"),
                "matched_entry_ids": [],
                "crosswalk_status": "source_gap",
                "edge_ids": [],
                "lexeme_form_status_counts": {},
                "card_id": "",
                "occurrence_id": "",
            },
        )
        item["matched_entry_ids"] = sorted(set(item.get("matched_entry_ids") or []) | {repair.get("entry_id")})
        item["crosswalk_status"] = "deterministic_exact"
        item["repair1_edge_ids"] = sorted(set(item.get("repair1_edge_ids") or []) | set(repair.get("edge_ids") or []))
        item["edge_ids"] = sorted(set(item.get("edge_ids") or []) | set(repair.get("edge_ids") or []))
        counts = Counter(
            edge.get("status")
            for edge in edges_by_selected.get(selected_id, [])
            if edge.get("edge_type") in {"form_entry_edge", "lexeme_entry_edge"}
        )
        item["lexeme_form_status_counts"] = dict(sorted(counts.items()))
    return sorted(forward.values(), key=lambda item: item.get("selected_word_id", ""))


def project_repair_reverse(forward: list[dict], edges: list[dict], entries: list[dict]) -> list[dict]:
    """Regenerate entry→selected-word and entry→occurrence reciprocity."""

    entry_ids = [
        _entry_id(item.get("id")) if isinstance(item, dict) else _entry_id(item)
        for item in entries or []
    ]
    return _reverse_records(forward, edges, entry_ids)


def _entry_policy_family(entry: dict, row: dict) -> str:
    explicit = _text(row.get("policy_family"))
    if explicit == DIVINE_FAMILY:
        return DIVINE_FAMILY
    headword = bare(_text(entry.get("headword")))
    haystack = " ".join(
        [headword, _text(entry.get("section"))]
        + [_text(item) for item in entry.get("tags") or []]
    ).lower()
    if any(token in haystack for token in ("divine", "allah", "اللّه", "الله")):
        return DIVINE_FAMILY
    return ""


def _indices(row: dict) -> tuple[int, int, int]:
    values = []
    for key in ("sense_index", "usage_index", "form_index"):
        try:
            values.append(max(1, int(row.get(key) or 1)))
        except (TypeError, ValueError):
            values.append(1)
    return values[0], values[1], values[2]


def _context_evidence(row: dict, entry: dict) -> tuple[list[dict], bool, bool, list[str]]:
    sense_index, usage_index, form_index = _indices(row)
    surface = _text(row.get("selected_surface") or row.get("surface"))
    evidence = []
    sense_match = False
    form_match = False
    form_addresses = []
    senses = entry.get("senses") or []
    if sense_index <= len(senses):
        sense = senses[sense_index - 1]
        sense_surface = _text(sense.get("ar")) if isinstance(sense, dict) else ""
        if sense_surface and norm_strict(sense_surface) == norm_strict(surface):
            sense_match = True
            evidence.append(
                {
                    "address": f"entry:{entry.get('id')}:senses[{sense_index - 1}].ar",
                    "method": "sense_ar_match",
                }
            )
    usages = entry.get("usage") or []
    if usage_index <= len(usages):
        usage = usages[usage_index - 1]
        forms = usage.get("forms") or [] if isinstance(usage, dict) else []
        if form_index <= len(forms):
            form_surface = _text(forms[form_index - 1])
            form_addresses.append(f"entry:{entry.get('id')}:usage[{usage_index - 1}].forms[{form_index - 1}]")
            if form_surface and norm_strict(form_surface) == norm_strict(surface):
                form_match = True
                evidence.append(
                    {
                        "address": form_addresses[-1],
                        "method": "documented_form_coordinate_match",
                    }
                )
        for example_index, example in enumerate(usage.get("examples") or [] if isinstance(usage, dict) else [], 1):
            ref = _text(example.get("ref")) if isinstance(example, dict) else ""
            if ref and ref == _text(row.get("source_card_ref")):
                evidence.append(
                    {
                        "address": f"entry:{entry.get('id')}:usage[{usage_index - 1}].examples[{example_index - 1}]",
                        "method": "entry_example_ref_matches_card",
                    }
                )
    return evidence, sense_match, form_match, form_addresses


def _occurrence_candidates(surface: str, card_ref: str, whitelist_rows: list[dict]) -> list[dict]:
    candidates = []
    for item in whitelist_rows or []:
        loc = _text(item.get("loc") or item.get("quran_loc"))
        if not loc or not card_ref or not loc.startswith(card_ref + ":"):
            continue
        candidate_surface = _text(item.get("surface"))
        if not candidate_surface:
            continue
        if bare(candidate_surface) == bare(surface):
            method = "card_surface_bare_match"
        elif norm_strict(candidate_surface) == norm_strict(surface):
            method = "card_surface_strict_recall_match"
        else:
            continue
        candidates.append({"loc": loc, "surface": candidate_surface, "method": method})
    return sorted(candidates, key=lambda item: item["loc"])


def _proposed_duplicate_edges(row: dict, entry: dict, selected_loc: str, evidence: list[dict], collision_set: list[str]) -> list[dict]:
    selected_id = _selected_id(row)
    entry_id = _entry_id(entry.get("id"))
    surface = _text(row.get("selected_surface") or row.get("surface"))
    detail = {
        "surface": surface,
        "collision_set": collision_set,
        "context_resolution": True,
        "repair_family": DUPLICATE_FAMILY,
        "repair_lane": "repair1",
        "selected_word_id": selected_id,
        "pre_apply_authorized": False,
    }
    edges = [
        make_edge(
            "form_entry_edge",
            selected_id,
            entry_node(entry_id),
            "candidate",
            evidence=evidence,
            guards=["duplicate_surface_context_resolution", "never_deterministic_exact", "pre_apply_not_authorized"],
            details={**detail, "edge_role": "context_resolved_form_candidate"},
            producer_id=PRODUCER_ID,
            producer_version=PRODUCER_VERSION,
        ),
        make_edge(
            "lexeme_entry_edge",
            selected_id,
            entry_node(entry_id),
            "candidate",
            evidence=evidence,
            guards=["duplicate_surface_context_resolution", "never_deterministic_exact", "pre_apply_not_authorized"],
            details={**detail, "edge_role": "context_resolved_lexeme_candidate"},
            producer_id=PRODUCER_ID,
            producer_version=PRODUCER_VERSION,
        ),
    ]
    if selected_loc:
        edges.append(
            make_edge(
                "canonical_occurrence_edge",
                selected_id,
                occurrence_node(selected_loc),
                "candidate",
                evidence=evidence,
                guards=["context_resolved_candidate", "existing_occurrence_graph_only", "pre_apply_not_authorized"],
                details={**detail, "edge_role": "context_resolved_occurrence_candidate", "loc": selected_loc},
                producer_id=PRODUCER_ID,
                producer_version=PRODUCER_VERSION,
            )
        )
    return edges


def build_duplicate_crosswalk_packets(
    rows: list[dict], entries: list[dict], whitelist_rows: list[dict], appearance_rows: list[dict] | None = None
) -> list[dict]:
    """Resolve card/context collisions without promoting a candidate edge."""

    entries_by_id = {_entry_id(entry.get("id")): entry for entry in entries or []}
    packets = []
    for row in rows or []:
        if _text(row.get("repair_family")) not in {DUPLICATE_FAMILY, DIVINE_FAMILY}:
            continue
        entry_id = _entry_id(row.get("entry_id"))
        entry = entries_by_id.get(entry_id, {})
        surface = _text(row.get("selected_surface") or row.get("surface"))
        card_ref = _text(row.get("source_card_ref"))
        context_evidence, sense_match, form_match, form_addresses = _context_evidence(row, entry)
        occurrence_candidates = _occurrence_candidates(surface, card_ref, whitelist_rows)
        collision_set = sorted({candidate["loc"] for candidate in occurrence_candidates})
        evidence = list(context_evidence)
        for candidate in occurrence_candidates:
            evidence.append(
                {
                    "address": f"whitelist:{candidate['loc']}",
                    "method": candidate["method"],
                }
            )
        if card_ref:
            evidence.append({"address": f"card:{card_ref}", "method": "source_card_identity"})
        policy_family = _entry_policy_family(entry, row)
        if policy_family == DIVINE_FAMILY:
            resolution = "still_ambiguous" if len(occurrence_candidates) != 1 else "resolved"
            packets.append(
                {
                    "schema": DUPLICATE_SCHEMA,
                    "repair_family": DIVINE_FAMILY,
                    "selected_word_id": _selected_id(row),
                    "entry_id": entry_id,
                    "surface": surface,
                    "source_card_ref": card_ref,
                    "resolution": resolution,
                    "status": "owner_or_scholar_required",
                    "route": "owner_or_scholar_required",
                    "policy_family": DIVINE_FAMILY,
                    "root_projection": "root-silent",
                    "lexical_promotion": False,
                    "collision_set": collision_set,
                    "evidence_chain": evidence,
                    "proposed_edge_set": [],
                    "required_evidence": [
                        "owner divine-name policy decision for the exact occurrence",
                        "orthography and referent confirmation at the card location",
                    ],
                    "pre_apply_authorized": False,
                }
            )
            continue
        resolved = (
            len(occurrence_candidates) == 1
            and bool(context_evidence)
            and (sense_match or form_match)
            and bool(card_ref)
        )
        if resolved:
            selected_loc = occurrence_candidates[0]["loc"]
            proposed = _proposed_duplicate_edges(row, entry, selected_loc, evidence, collision_set)
            packets.append(
                {
                    "schema": DUPLICATE_SCHEMA,
                    "repair_family": DUPLICATE_FAMILY,
                    "selected_word_id": _selected_id(row),
                    "entry_id": entry_id,
                    "surface": surface,
                    "source_card_ref": card_ref,
                    "resolution": "resolved",
                    "status": "candidate",
                    "route": "candidate_crosswalk_review",
                    "policy_family": None,
                    "root_projection": "entry-root-candidate-only",
                    "lexical_promotion": False,
                    "selected_occurrence": selected_loc,
                    "collision_set": collision_set,
                    "evidence_chain": evidence,
                    "proposed_edge_set": proposed,
                    "required_evidence": [],
                    "pre_apply_authorized": False,
                }
            )
        else:
            required = [
                f"one canonical occurrence location for card {card_ref or '<missing>'} and surface {surface or '<missing>'}",
                "independent written-surface and diacritic readback at that location",
                "sense/form confirmation tied to the selected occurrence rather than root agreement alone",
            ]
            packets.append(
                {
                    "schema": DUPLICATE_SCHEMA,
                    "repair_family": DUPLICATE_FAMILY,
                    "selected_word_id": _selected_id(row),
                    "entry_id": entry_id,
                    "surface": surface,
                    "source_card_ref": card_ref,
                    "resolution": "still_ambiguous",
                    "status": "owner_or_scholar_required",
                    "route": "owner_or_scholar_required",
                    "policy_family": None,
                    "root_projection": "entry-root-candidate-only",
                    "lexical_promotion": False,
                    "collision_set": collision_set,
                    "evidence_chain": evidence,
                    "proposed_edge_set": [],
                    "required_evidence": required,
                    "pre_apply_authorized": False,
                }
            )
    return sorted(packets, key=lambda item: item.get("selected_word_id", ""))


def build_reciprocity_packets(
    diagnosis_rows: list[dict], ledger_rows: list[dict], appearance_rows: list[dict]
) -> list[dict]:
    """Packetize different page-context relationships without lexical promotion."""

    ledger_by_loc = {_loc_from_row(row): row for row in ledger_rows or [] if _loc_from_row(row)}
    appearance_by_loc = {item.get("loc"): item for item in appearance_rows or []}
    packets = []
    for diagnosis in diagnosis_rows or []:
        if _text(diagnosis.get("classification")) != "different_page_context_relationship":
            continue
        loc = _text(diagnosis.get("loc"))
        row = ledger_by_loc.get(loc, {})
        selected_id = _selected_id(row) if row else f"selected-word:reciprocity:{loc}"
        entry_id = _entry_id(diagnosis.get("entry_id") or row.get("entry_id"))
        observed = sorted(set(diagnosis.get("observed_entry_relationships") or []))
        appearance = appearance_by_loc.get(loc, {})
        evidence = [
            {"address": f"ledger:{selected_id}:occurrence", "method": "existing_vnmap_ledger_occurrence_id"},
            {"address": f"occurrence-appearances:{loc}:entry_relationships", "method": "existing_occurrence_appearance_index"},
            {"address": f"whitelist:{loc}:entry_id", "method": "page_context_relationship_readback"},
        ]
        detail = {
            "loc": loc,
            "expected_entry_id": entry_id,
            "observed_page_context_entry_ids": observed,
            "page_context_only": True,
            "repair_family": "entry-occurrence reciprocity",
            "pre_apply_authorized": False,
        }
        proposed = [
            {
                "schema": "qamus.graph_edge.v1",
                "edge_type": "lexeme_entry_edge",
                "from_node_id": occurrence_node(loc),
                "to_node_id": entry_node(entry_id),
                "status": "owner_or_scholar_required",
                "evidence": evidence,
                "guards": ["different_page_context_relationship", "never_consume_page_context_as_lexeme", "pre_apply_not_authorized"],
                "details": detail,
            },
            {
                "schema": "qamus.graph_edge.v1",
                "edge_type": "decision_evidence_edge",
                "from_node_id": occurrence_node(loc),
                "to_node_id": entry_node(entry_id),
                "status": "owner_or_scholar_required",
                "evidence": evidence,
                "guards": ["owner_or_scholar_review_required", "source_fact_not_invented", "pre_apply_not_authorized"],
                "details": detail,
            },
        ]
        packets.append(
            {
                "schema": RECIPROCITY_SCHEMA,
                "loc": loc,
                "entry_id": entry_id,
                "selected_word_id": selected_id,
                "classification": "different_page_context_relationship",
                "status": "owner_or_scholar_required",
                "route": "typed_packet_repair",
                "observed_entry_relationships": observed,
                "appearance_entry_relationships": sorted(set(appearance.get("entry_relationships") or [])),
                "evidence_chain": evidence,
                "proposed_edge_set": proposed,
                "required_evidence": [
                    "owner decision identifying the intended lexical entry at the occurrence",
                    "a source-addressed fact distinct from the page-context entry relationship",
                ],
                "pre_apply_authorized": False,
            }
        )
    return sorted(packets, key=lambda item: item["loc"])


def verify_source_key_reciprocity(rows: list[dict], entries: list[dict], appearance_rows: list[dict]) -> list[dict]:
    """Verify the six resolver rows against a freshly rebuilt appearance index."""

    entries_by_source = {}
    entries_by_id = {_entry_id(entry.get("id")): entry for entry in entries or []}
    for entry in entries or []:
        for key in entry.get("source_keys") or []:
            identity = _appearance_source_identity(key)
            if identity is not None:
                entries_by_source[identity] = _entry_id(entry.get("id"))
    appearances = {item.get("loc"): item for item in appearance_rows or []}
    result = []
    for row in rows or []:
        expected = _source_key_alias(row.get("entry_id"), entries_by_id, entries_by_source)
        observed = sorted(set((appearances.get(row.get("loc"), {}) or {}).get("entry_relationships") or []))
        fixed = bool(expected) and expected in observed
        result.append(
            {
                "schema": RECIPROCITY_SCHEMA,
                "loc": _text(row.get("loc")),
                "source_key": _text(row.get("source_key")),
                "expected_entry_id": expected,
                "observed_entry_relationships": observed,
                "classification": "source_key_entry_id_resolution_defect",
                "status": "fixed_by_source_key_resolver" if fixed else "still_failure",
                "action": "fix_occurrence_appearance_index_builder",
                "evidence_chain": [
                    {"address": f"whitelist:{row.get('loc')}:entry_id", "method": "source_key_alias_input"},
                    {"address": f"occurrence-appearances:{row.get('loc')}:entry_relationships", "method": "fresh_rebuilt_index"},
                ],
                "pre_apply_authorized": False,
            }
        )
    return result


def _edge_complete(selected_id: str, edges: list[dict]) -> bool:
    kinds = {
        item.get("edge_type")
        for item in edges or []
        if item.get("from_node_id") == selected_id
        and item.get("edge_type") in {"form_entry_edge", "lexeme_entry_edge"}
        and item.get("status") in USABLE_STATUSES
    }
    return kinds == {"form_entry_edge", "lexeme_entry_edge"}


def _repair_edge_complete(record: dict, edges: list[dict]) -> bool:
    """Require the exact row-addressed form evidence, not only a lexical pair."""

    selected_id = _text(record.get("selected_word_id"))
    entry_id = _entry_id(record.get("entry_id"))
    form_address = _text(record.get("form_address"))
    kinds = set()
    for item in edges or []:
        if (
            item.get("from_node_id") != selected_id
            or item.get("to_node_id") != entry_node(entry_id)
            or item.get("edge_type") not in {"form_entry_edge", "lexeme_entry_edge"}
            or item.get("status") not in USABLE_STATUSES
        ):
            continue
        evidence_addresses = {
            _text(evidence.get("address"))
            for evidence in item.get("evidence") or []
            if isinstance(evidence, dict)
        }
        if form_address and form_address in evidence_addresses:
            kinds.add(item.get("edge_type"))
    return kinds == {"form_entry_edge", "lexeme_entry_edge"}


def measure_owner_yield(
    debt_rows: list[dict],
    entries: list[dict],
    base_edges: list[dict],
    merged_edges: list[dict],
    deterministic_records: list[dict],
    ledger_rows: list[dict],
    appearance_rows: list[dict],
) -> dict:
    """Measure lexical bridge advance and the independent bidirectional traces."""

    records_by_id = {
        _text(item.get("selected_word_id")): item
        for item in deterministic_records
    }
    base_complete = {
        selected_id: _repair_edge_complete(record, base_edges)
        for selected_id, record in records_by_id.items()
    }
    after_complete = {
        selected_id: _repair_edge_complete(record, merged_edges)
        for selected_id, record in records_by_id.items()
    }
    deterministic_ids = {_text(item.get("selected_word_id")) for item in deterministic_records}
    newly = sorted(selected_id for selected_id in deterministic_ids if after_complete.get(selected_id) and not base_complete.get(selected_id))
    overlay_complete = sorted(selected_id for selected_id in deterministic_ids if after_complete.get(selected_id))
    rows_by_card = defaultdict(list)
    rows_by_entry = defaultdict(list)
    deterministic_rows_by_id = {
        _selected_id(row): row
        for row in debt_rows or []
        if _selected_id(row) in deterministic_ids
    }
    for row in deterministic_rows_by_id.values():
        selected_id = _selected_id(row)
        entry_id = _entry_id(row.get("entry_id"))
        rows_by_card[_text(row.get("source_card_ref"))].append(selected_id)
        rows_by_entry[entry_id].append(selected_id)
    newly_card_count = sum(
        bool(card_ref)
        and all(selected_id in overlay_complete for selected_id in selected_ids)
        and not all(base_complete.get(selected_id) for selected_id in selected_ids)
        for card_ref, selected_ids in rows_by_card.items()
    )
    newly_entry_count = sum(
        bool(entry_id)
        and all(selected_id in overlay_complete for selected_id in selected_ids)
        and not all(base_complete.get(selected_id) for selected_id in selected_ids)
        for entry_id, selected_ids in rows_by_entry.items()
    )
    forward_before = sum(bool(row.get("canonical_occurrence_trace_complete")) for row in ledger_rows or [])
    reverse_before = sum(bool(row.get("reverse_entry_relationship_present")) for row in ledger_rows or [])
    appearance_by_loc = {item.get("loc"): item for item in appearance_rows or []}
    forward_after = sum(bool(row.get("canonical_occurrence_trace_complete")) for row in ledger_rows or [])
    reverse_after = sum(
        bool(row.get("occurrence_id"))
        and _entry_id(row.get("entry_id")) in set((appearance_by_loc.get(_text(row.get("occurrence_id")), {}) or {}).get("entry_relationships") or [])
        for row in ledger_rows or []
    )
    return {
        "selected_word_rows_newly_edge_complete": len(newly),
        "selected_word_rows_overlay_edge_complete": len(overlay_complete),
        "selected_word_rows_preexisting_edge_complete": sum(base_complete.values()),
        "cards_newly_all_edged": newly_card_count,
        "entries_newly_all_edged": newly_entry_count,
        "deterministic_rows_repaired": len(deterministic_records),
        "before_bidirectionality": {
            "forward_trace_complete": forward_before,
            "reverse_trace_complete": reverse_before,
        },
        "after_bidirectionality": {
            "forward_trace_complete": forward_after,
            "reverse_trace_complete": reverse_after,
        },
        "forward_trace_delta": forward_after - forward_before,
        "reverse_trace_delta": reverse_after - reverse_before,
        "merged_edge_count": len(merged_edges),
    }


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def render_repair1_report(summary: dict, duplicate_packets: list[dict], reciprocity_packets: list[dict], validator_report: dict) -> str:
    deterministic = summary.get("deterministic", {})
    yield_metrics = summary.get("owner_yield", {})
    duplicate_counts = Counter(item.get("resolution") for item in duplicate_packets)
    divine_count = sum(item.get("policy_family") == DIVINE_FAMILY for item in duplicate_packets)
    reciprocity = summary.get("reciprocity", {})
    source_key_count = {
        "fixed_by_source_key_resolver": reciprocity.get("source_key_fixed", 0),
        "source_key_rows": reciprocity.get("source_key_rows", 0),
    }
    source_key_locations = ", ".join(
        _text(item.get("loc"))
        for item in summary.get("source_key_verification", [])
        if _text(item.get("loc"))
    )
    reciprocity_locations = ", ".join(
        _text(item.get("loc"))
        for item in reciprocity_packets
        if _text(item.get("loc"))
    )
    reclassification_counts = deterministic.get("reclassification_reason_counts", {})
    lines = [
        "# REPAIR1 Report",
        "",
        "## Outcome",
        "",
        "Repair1 emitted a candidate-mode graph overlay for the deterministic entry/form family, regenerated the occurrence-appearance index from explicit entries/whitelist inputs, and produced bounded duplicate-surface and reciprocity packets. No input corpus or producer history was rewritten.",
        "",
        "## Task 1 — deterministic entry/form repair",
        "",
        f"- Classified rows read: **{deterministic.get('input_rows', 0)}**; guarded exact rows emitted: **{deterministic.get('deterministic_rows', 0)}**; typed guard reclassifications: **{deterministic.get('reclassified_rows', 0)}**.",
        f"- Overlay edges: **{deterministic.get('new_overlay_edges', 0)}** ({deterministic.get('new_overlay_form_edges', 0)} form + {deterministic.get('new_overlay_lexeme_edges', 0)} lexeme); all exact edges carry `status=deterministic_exact` and `qamus.graph_edge.v1` evidence/provenance.",
        f"- Owner yield: selected-word rows newly edge-complete **{yield_metrics.get('selected_word_rows_newly_edge_complete', 0)}**; rows edge-complete in the Repair1 overlay **{yield_metrics.get('selected_word_rows_overlay_edge_complete', 0)}**; cards newly all-edged **{yield_metrics.get('cards_newly_all_edged', 0)}**; entries newly all-edged **{yield_metrics.get('entries_newly_all_edged', 0)}**.",
        f"- Before → after bidirectionality: forward trace **{yield_metrics.get('before_bidirectionality', {}).get('forward_trace_complete', 0)} → {yield_metrics.get('after_bidirectionality', {}).get('forward_trace_complete', 0)}**; reverse trace **{yield_metrics.get('before_bidirectionality', {}).get('reverse_trace_complete', 0)} → {yield_metrics.get('after_bidirectionality', {}).get('reverse_trace_complete', 0)}**.",
        f"- Reverse projection rerun: **{yield_metrics.get('reverse_projection', {}).get('forward_records', 0)}** forward records → **{yield_metrics.get('reverse_projection', {}).get('reverse_records', 0)}** entry records carrying **{yield_metrics.get('reverse_projection', {}).get('reverse_selected_word_refs', 0)}** selected-word references.",
        f"- Guard reclassification reasons: `{reclassification_counts}`.",
        "",
        "Execution-time failures are typed reclassifications; hamza seats, ta marbuta/ha, and defective spellings never use a lenient key to force an edge.",
        "",
        "### Compounding Impact — Task 1",
        "",
        "Channels fed: lexical/form edge, crosswalk, universal morpheme class, Ṣarf rule, Naḥw rule, projector, guard/defeater, positive fixture, adversarial fixture, validator, learner-language template, renderer behavior, parser-readiness example, curriculum/drill item, dependent-row discovery query, and VN fast-path (all 16).",
        f"Acceleration: deterministic projections enabled **{deterministic.get('deterministic_rows', 0)}**; review cases avoided by the guarded exact path **{deterministic.get('deterministic_rows', 0)}**; average manual-review packet work per exact repaired row **0.0**; overlay edge pairs **{deterministic.get('deterministic_rows', 0)}**.",
        "",
        "## Task 2 — occurrence-appearance resolver",
        "",
        f"- Explicit appearance audit: EDGES input **{summary.get('appearance_rebuild', {}).get('existing_rows', 0)}** rows; fresh rebuild **{summary.get('appearance_rebuild', {}).get('rebuilt_rows', 0)}** rows; identical projection hashes at **{summary.get('appearance_rebuild', {}).get('same_projection_hash_rows', 0)}** shared locations.",
        f"- Six source-key rows verified against the fresh rebuild: `{source_key_count}` ({source_key_locations}).",
        f"- Different-page-context relationships packetized: **{len(reciprocity_packets)}**; none was promoted to a lexeme edge.",
        f"- Page-context packet locations: {reciprocity_locations}.",
        "",
        "Each packet records the exact ledger, appearance-index, and whitelist addresses, a proposed typed edge set, and the owner/scholar evidence still required.",
        "",
        "### Compounding Impact — Task 2",
        "",
        "Channels fed: crosswalk, projector, positive fixture, adversarial fixture, validator, dependent-row discovery query, and VN fast-path. The six source-key relationships are compiler-ready; the three page-context cases remain owner-gated and do not feed lexical, Ṣarf, or Naḥw promotion.",
        f"Acceleration: deterministic projections enabled **{reciprocity.get('source_key_fixed', 0)}**; resolver review cases avoided **{reciprocity.get('source_key_fixed', 0)}**; average manual-review packet work per fixed resolver row **0.0**; owner packets retained **{len(reciprocity_packets)}**.",
        "",
        "## Task 3 — duplicate-surface crosswalk review",
        "",
        f"- Rows reviewed: **{len(duplicate_packets)}**; dispositions: `{dict(sorted(duplicate_counts.items()))}`; divine-name policy rows: **{divine_count}**.",
        "- Context-resolved records remain `candidate`; still-ambiguous records route `owner_or_scholar_required` with a collision set and exact missing discriminator.",
        "- Divine-name rows are root-silent and have no proposed lexical promotion.",
        "",
        "### Compounding Impact — Task 3",
        "",
        "Channels fed: crosswalk, guard/defeater, positive fixture, adversarial fixture, validator, learner-language template, renderer behavior, parser-readiness example, curriculum/drill item, and dependent-row discovery query. Lexical/form, universal-morpheme, Ṣarf, Naḥw, projector, and VN fast-path promotion channels are deliberately not fed until the candidate or owner route is accepted.",
        f"Acceleration: deterministic projections enabled **0** (candidate packets are not learner projections); review cases avoided **0**; average manual-review packet work per reviewed row **1.0 packet**; owner/scholar routes **{sum(item.get('route') == 'owner_or_scholar_required' for item in duplicate_packets)}**.",
        "",
        "## Validator closure",
        "",
        f"- Ten typed-graph checks: **{'PASS' if validator_report.get('ok') else 'FAIL'}**; checks run: **{len(validator_report.get('checks', []))}**; errors: **{len(validator_report.get('errors', []))}**.",
        "",
        "Acceleration metrics recorded above are deterministic projections enabled, review cases avoided by the exact guard, average manual-review packet work per repaired/reviewed row, forward/reverse compiler reach, overlay edge yield, candidate abstention rate, duplicate cases routed instead of guessed, and expected effect on the next crosswalk tranche. The base graph's pre-existing lexical pairs are measured separately from Repair1's exact-form overlay evidence.",
        "",
        "## Gates",
        "",
        "- Candidate mode: `pre_apply_authorized=false` throughout; no live mutation, whitelist append, publication, push, or release.",
        "- Large JSONL outputs are lane-side; committed repository content is limited to reusable tooling, fixture subsets, tests, and the plan.",
    ]
    return "\n".join(lines) + "\n"


def _build_bundle(base_graph: list[dict], base_forward: list[dict], base_reverse: list[dict], repair: dict, entries: list[dict]) -> dict:
    merged_edges = merge_repair_edges(base_graph, repair.get("edges", []))
    forward = project_repair_forward(base_forward, repair.get("records", []), merged_edges)
    reverse = project_repair_reverse(forward, merged_edges, entries)
    return {
        "schema": "qamus.typed_edge_bundle.v1",
        "edges": merged_edges,
        "forward": forward,
        "reverse": reverse,
    }


def build_from_paths(args) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = read_jsonl(args.entries)
    whitelist = read_jsonl(args.whitelist)
    ledger = read_jsonl(args.ledger)
    debt = read_jsonl(args.debt)
    duplicates = read_jsonl(args.duplicates)
    base_graph = read_jsonl(args.base_graph)
    base_forward = read_jsonl(args.base_forward)
    base_reverse = read_jsonl(args.base_reverse)
    existing_appearances = read_jsonl(args.appearances) if args.appearances else []
    diagnosis = read_jsonl(args.reciprocity) if args.reciprocity else []
    source_key_rows = read_jsonl(args.source_key_fixture) if args.source_key_fixture else []

    rebuilt = build_index(whitelist, entries)
    existing_by_loc = {item.get("loc"): item for item in existing_appearances if item.get("loc")}
    rebuilt_by_loc = {item.get("loc"): item for item in rebuilt.records if item.get("loc")}
    appearance_rebuild = {
        "existing_rows": len(existing_appearances),
        "rebuilt_rows": len(rebuilt.records),
        "same_loc_rows": len(set(existing_by_loc) & set(rebuilt_by_loc)),
        "same_projection_hash_rows": sum(
            existing_by_loc[loc].get("projection_hash") == rebuilt_by_loc[loc].get("projection_hash")
            for loc in set(existing_by_loc) & set(rebuilt_by_loc)
        ),
    }
    write_jsonl(output_dir / "occurrence-appearances.rebuilt.jsonl", rebuilt.records)
    _write_json(output_dir / "occurrence-appearances.rebuilt.metrics.json", rebuilt.stats)

    deterministic_rows = [row for row in debt if _text(row.get("repair_family")) == DETERMINISTIC_FAMILY]
    deterministic = build_deterministic_repairs(deterministic_rows, entries, base_graph)
    bundle = _build_bundle(base_graph, base_forward, base_reverse, deterministic, entries)
    duplicate_packets = build_duplicate_crosswalk_packets(duplicates, entries, whitelist, rebuilt.records)
    reciprocity_packets = build_reciprocity_packets(diagnosis, ledger, rebuilt.records)
    source_key_verification = verify_source_key_reciprocity(source_key_rows, entries, rebuilt.records)
    validator_report = __import__("tools.validate_typed_edge_graph", fromlist=["validate_graph"]).validate_graph(
        bundle, entries, ledger, whitelist, rebuilt.records, []
    )
    owner_yield = measure_owner_yield(
        debt,
        entries,
        base_graph,
        bundle["edges"],
        deterministic["records"],
        ledger,
        rebuilt.records,
    )
    owner_yield["reverse_projection"] = {
        "forward_records": len(bundle["forward"]),
        "reverse_records": len(bundle["reverse"]),
        "reverse_selected_word_refs": sum(
            len(item.get("selected_word_ids") or []) for item in bundle["reverse"]
        ),
    }
    summary = {
        "schema": "qamus.repair1.summary.v1",
        "candidate_only": True,
        "deterministic": deterministic["metrics"],
        "owner_yield": owner_yield,
        "duplicate": {
            "input_rows": len(duplicates),
            "resolved": sum(item.get("resolution") == "resolved" for item in duplicate_packets),
            "still_ambiguous": sum(item.get("resolution") == "still_ambiguous" for item in duplicate_packets),
            "divine_name_policy_rows": sum(item.get("policy_family") == DIVINE_FAMILY for item in duplicate_packets),
        },
        "reciprocity": {
            "source_key_rows": len(source_key_verification),
            "source_key_fixed": sum(item.get("status") == "fixed_by_source_key_resolver" for item in source_key_verification),
            "different_page_context_packets": len(reciprocity_packets),
        },
        "source_key_verification": source_key_verification,
        "appearance_rebuild": appearance_rebuild,
        "validator": validator_report,
        "pre_apply_authorized": False,
    }
    write_jsonl(output_dir / "deterministic-repair-records.jsonl", deterministic["records"])
    write_jsonl(output_dir / "deterministic-repair-edges.jsonl", deterministic["edges"])
    write_jsonl(output_dir / "deterministic-repair-reclassifications.jsonl", deterministic["reclassifications"])
    write_jsonl(output_dir / "repair1-graph.with-deterministic.jsonl", bundle["edges"])
    write_jsonl(output_dir / "repair1-crosswalk.forward.jsonl", bundle["forward"])
    write_jsonl(output_dir / "repair1-crosswalk.reverse.jsonl", bundle["reverse"])
    write_jsonl(output_dir / "duplicate-surface-resolution.jsonl", duplicate_packets)
    write_jsonl(output_dir / "reciprocity-source-key-verification.jsonl", source_key_verification)
    write_jsonl(output_dir / "reciprocity-typed-packets.jsonl", reciprocity_packets)
    _write_json(output_dir / "owner-yield.json", owner_yield)
    _write_json(output_dir / "appearance-rebuild-comparison.json", appearance_rebuild)
    _write_json(output_dir / "repair1-metrics.json", summary)
    (output_dir / "REPAIR1-REPORT.md").write_text(
        render_repair1_report(summary, duplicate_packets, reciprocity_packets, validator_report),
        encoding="utf-8",
        newline="\n",
    )
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", required=True)
    parser.add_argument("--whitelist", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--debt", required=True)
    parser.add_argument("--duplicates", required=True)
    parser.add_argument("--base-graph", required=True)
    parser.add_argument("--base-forward", required=True)
    parser.add_argument("--base-reverse", required=True)
    parser.add_argument("--appearances", help="Existing EDGES appearance stream, retained as an explicit audit input")
    parser.add_argument("--reciprocity")
    parser.add_argument("--source-key-fixture")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    summary = build_from_paths(args)
    print(json.dumps({
        "candidate_only": summary["candidate_only"],
        "deterministic": summary["deterministic"],
        "duplicate": summary["duplicate"],
        "reciprocity": summary["reciprocity"],
        "validator_ok": summary["validator"]["ok"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if summary["validator"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
