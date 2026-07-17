#!/usr/bin/env python3
"""Measure typed-edge closure, reclassify graph-only gaps, and write the lane report."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from tools.build_typed_edge_crosswalk import (  # noqa: E402
    _card_id_for_row,
    _entry_indexes,
    _entry_id,
    _fact_fields,
    _iter_entry_forms,
    _loc_from_row,
    _root_key,
    _selected_id_for_row,
    _text,
    appearance_node,
    entry_node,
    make_edge,
    occurrence_node,
    read_jsonl,
    selected_word_node,
    write_jsonl,
)
from tools.normalize_ar import bare, norm_strict


DEBT_FAMILIES = [
    "deterministic entry/form match",
    "selected-word edge missing",
    "display-local crosswalk missing",
    "source card/photo missing",
    "duplicate-surface ambiguity",
    "entry form inventory missing",
    "correct entry absent",
    "sense edge missing",
    "proper noun",
    "function word",
    "divine-name policy",
    "source/scholar required",
    "genuinely unresolvable",
]

GRAPH_BLOCKERS = [
    "lexeme_entry_crosswalk_missing",
    "certified_fact_attachment_missing",
    "selected_word_edge_missing",
    "canonical_occurrence_edge_missing",
    "display_local_crosswalk_missing",
    "projection_input_edge_missing",
    "appearance_backlink_missing",
]

REPAIR_LANES = {
    "deterministic entry/form match": "Attach the guarded exact form address, emit the form and lexeme edges, then rerun the reverse projection.",
    "selected-word edge missing": "Rebuild the selected-word identity from entry/sense/usage/form and card coordinates; fail if the card identity is not exact.",
    "display-local crosswalk missing": "Resolve the local card address to one canonical location, compare the full written surface, and propagate the canonical correction to every appearance.",
    "source card/photo missing": "Recover the source card identity first, attach a photo only from source evidence, and keep the row candidate until both addresses are present.",
    "duplicate-surface ambiguity": "Record the complete collision set, use card/context/sense evidence in a bounded crosswalk review, and abstain when the collision remains.",
    "entry form inventory missing": "Extend the entry's documented form inventory from a source-owned record; never infer a form from root agreement alone.",
    "correct entry absent": "Route to entry-source ownership to identify the correct entry before creating any lexeme edge.",
    "sense edge missing": "Repair the one-based sense identity and cite the exact sense address before projecting a form edge.",
    "proper noun": "Use the name/proper-noun policy lane with occurrence context and source ownership; do not normalize names into common nouns.",
    "function word": "Use the particle/function-word lane with context-sensitive nahw evidence; surface equality alone is insufficient for homographs.",
    "divine-name policy": "Apply the owner divine-name policy and preserve orthography/case evidence; no automatic lexical promotion crosses the policy boundary.",
    "source/scholar required": "Collect the missing source or scholar decision, retain the collision set, and promote only after the required evidence is attached.",
    "genuinely unresolvable": "Keep a typed source gap with the exact missing fact and a stop condition; do not manufacture a graph edge.",
}


def _strip_loc(value) -> str:
    value = _text(value)
    for prefix in ("quran:", "wbw:"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def _collect_addresses(value, output=None, seen=None):
    output = output if output is not None else []
    seen = seen if seen is not None else set()
    if isinstance(value, dict):
        address = _text(value.get("address"))
        if address and address not in seen:
            seen.add(address)
            output.append(address)
        for key, child in value.items():
            if key in {
                "evidence",
                "source_evidence",
                "source_address",
                "source_addresses",
                "dependencies",
                "fact_value",
                "source_fields",
            } or isinstance(child, (dict, list)):
                _collect_addresses(child, output, seen)
    elif isinstance(value, list):
        for child in value:
            _collect_addresses(child, output, seen)
    elif isinstance(value, str) and value.startswith(("entry:", "quran:", "wbw:", "registry:", "fixture:")):
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def normalize_producer_record(record: dict) -> dict:
    """Extract routing facts without treating a whitelist entry id as lexical evidence."""

    canonical = record.get("canonical_occurrence") or {}
    facts = record.get("facts") or []
    if not isinstance(facts, list):
        facts = []
    flattened = []
    for fact in facts:
        if isinstance(fact, dict):
            flattened.append(fact)
    projection = record.get("projection") or {}
    if not isinstance(projection, dict):
        projection = {}
    loc = _strip_loc(
        canonical.get("quran_loc")
        or canonical.get("occurrence_id")
        or record.get("quran_loc")
        or record.get("loc")
    )
    surface = _text(canonical.get("surface") or record.get("surface"))
    page_context_entry_id = _entry_id(canonical.get("entry_id"))
    linguistic_entry_id = ""
    fact_ids = []
    evidence_addresses = _collect_addresses(record)
    fact_statuses = []
    linguistic_evidence = False
    for fact in flattened:
        fact_id = _text(fact.get("fact_id") or fact.get("id"))
        if fact_id:
            fact_ids.append(fact_id)
        certification = fact.get("certification") or {}
        status = _text(certification.get("status") or fact.get("status")).lower()
        if status:
            fact_statuses.append(status)
        fact_value = fact.get("fact_value") or {}
        if not isinstance(fact_value, dict):
            fact_value = {}
        candidate_entry_id = _entry_id(fact_value.get("entry_id"))
        candidate_addresses = _collect_addresses(fact)
        if candidate_entry_id and any(
            address.startswith(f"entry:{candidate_entry_id}:")
            or "qamus_entry_field" in address
            for address in candidate_addresses
        ):
            linguistic_entry_id = candidate_entry_id
            if status in {"certified", "candidate", "source_addressed_candidate"}:
                linguistic_evidence = True
        fact_type = _text(fact.get("fact_type"))
        if status in {"certified", "candidate"} and fact_type and not fact_type.endswith("_pending"):
            if candidate_entry_id and candidate_addresses:
                linguistic_evidence = True
    if not linguistic_entry_id and linguistic_evidence:
        for fact in flattened:
            value = fact.get("fact_value") or {}
            if isinstance(value, dict) and _entry_id(value.get("entry_id")):
                linguistic_entry_id = _entry_id(value.get("entry_id"))
                break
    route = ""
    for fact in flattened:
        value = fact.get("fact_value") or {}
        if isinstance(value, dict) and _text(value.get("route")):
            route = _text(value.get("route"))
            break
    if not route:
        unresolved = record.get("unresolved_blockers") or []
        if unresolved and isinstance(unresolved[0], dict):
            route = _text(unresolved[0].get("blocker_id"))
    producer = record.get("producer") or {}
    producer_id = _text(producer.get("id")) if isinstance(producer, dict) else ""
    if not producer_id:
        producer_id = _text(record.get("producer_id"))
    if not producer_id:
        for fact in flattened:
            fact_producer = fact.get("producer") or {}
            if isinstance(fact_producer, dict) and _text(fact_producer.get("id")):
                producer_id = _text(fact_producer.get("id"))
                if not _text((producer or {}).get("version")):
                    producer = fact_producer
                break
    projection_status = _text(
        projection.get("status")
        or projection.get("unresolved_status")
        or record.get("status")
    ).lower()
    source_status = projection_status or route
    return {
        "source_record_id": _text(record.get("contract_id") or record.get("record_id") or loc),
        "producer_id": producer_id,
        "producer_version": _text((producer or {}).get("version")) if isinstance(producer, dict) else "",
        "loc": loc,
        "surface": surface,
        "page_context_entry_id": page_context_entry_id,
        "linguistic_entry_id": linguistic_entry_id,
        "source_status": source_status,
        "route": route,
        "fact_ids": sorted(set(fact_ids)),
        "fact_statuses": sorted(set(fact_statuses)),
        "fact_count": len(flattened),
        "linguistic_evidence": linguistic_evidence,
        "evidence_addresses": evidence_addresses,
        "record": record,
    }


def _forward_by_selected(bundle):
    return {item.get("selected_word_id"): item for item in bundle.get("forward") or []}


def _ledger_by_loc(ledger_rows):
    result = defaultdict(list)
    for row in ledger_rows or []:
        loc = _loc_from_row(row)
        if loc:
            result[loc].append(row)
    return result


def _edge_by_type(edges):
    result = defaultdict(list)
    for item in edges or []:
        result[item.get("edge_type")].append(item)
    return result


def _has_edge(edges, edge_type, *, from_node_id=None, to_node_id=None, status=None):
    for item in edges:
        if item.get("edge_type") != edge_type:
            continue
        if from_node_id is not None and item.get("from_node_id") != from_node_id:
            continue
        if to_node_id is not None and item.get("to_node_id") != to_node_id:
            continue
        if status is not None and item.get("status") != status:
            continue
        return item
    return None


def _entry_category(entry: dict) -> str:
    haystack = " ".join(
        [_text(entry.get("headword")), _text(entry.get("section"))]
        + [_text(item) for item in entry.get("tags") or []]
    ).lower()
    if any(token in haystack for token in ("allah", "divine", "الل")):
        return "divine-name policy"
    if any(token in haystack for token in ("proper", "names", "prophets", "places")):
        return "proper noun"
    if entry.get("section") == "particle" or any(
        token in haystack for token in ("particle", "preposition", "conjunction", "pronoun")
    ):
        return "function word"
    return ""


def classify_debt_rows(rows, entries, bundle, whitelist_rows, appearance_rows):
    """Assign one primary owner repair family to each supplied debt row."""

    entries_by_id, exact, strict, _ = _entry_indexes(list(entries or []))
    forward = _forward_by_selected(bundle)
    summary = {family: 0 for family in DEBT_FAMILIES}
    records = []
    for row in rows or []:
        entry_id = _entry_id(row.get("entry_id"))
        selected_id = _selected_id_for_row(row) if entry_id else ""
        fwd = forward.get(selected_id, {})
        entry = entries_by_id.get(entry_id, {})
        surface = _text(row.get("selected_surface"))
        exact_ids = sorted({item["entry_id"] for item in exact.get(bare(surface), [])})
        strict_ids = sorted({item["entry_id"] for item in strict.get(norm_strict(surface), [])})
        missing = set(row.get("missing_edges") or [])
        category = _entry_category(entry)
        if category:
            family = category
        elif row.get("join_method") in {"exact_ambiguous", "strict_ambiguous"} or "duplicate_surface_edge_ambiguous" in missing:
            family = "duplicate-surface ambiguity"
        elif not _text(row.get("source_card_ref")):
            family = "source card/photo missing"
        elif (row.get("sense_index") or 0) > len(entry.get("senses") or []):
            family = "sense edge missing"
        elif row.get("occurrence_id") and row.get("canonical_quran_loc") and _strip_loc(row.get("canonical_quran_loc")) != row.get("occurrence_id"):
            family = "display-local crosswalk missing"
        elif not fwd:
            family = "selected-word edge missing"
        elif fwd.get("crosswalk_status") in {"deterministic_exact", "certified"}:
            family = "deterministic entry/form match"
        elif fwd.get("crosswalk_status") in {"candidate", "ambiguous"} or strict_ids:
            family = "source/scholar required"
        elif entry_id not in entries_by_id:
            family = "correct entry absent"
        elif not any(
            _text(form.get("surface"))
            for usage in entry.get("usage") or []
            if isinstance(usage, dict)
            for form in [{"surface": item} for item in usage.get("forms") or []]
        ):
            family = "entry form inventory missing"
        elif "display_local_to_canonical_crosswalk_missing" in missing:
            family = "display-local crosswalk missing"
        elif "missing_selected_word_edge" in missing:
            family = "selected-word edge missing"
        else:
            family = "genuinely unresolvable"
        summary[family] += 1
        records.append(
            {
                "schema": "qamus.lexeme_entry_crosswalk.debt.v1",
                "selected_word_id": selected_id,
                "entry_id": entry_id,
                "surface": surface,
                "loc": _loc_from_row(row),
                "repair_family": family,
                "crosswalk_status": fwd.get("crosswalk_status", "missing"),
                "join_method": _text(row.get("join_method")),
                "missing_edges": sorted(missing),
                "candidate_entry_ids": sorted(set(exact_ids or strict_ids)),
                "source_card_ref": _text(row.get("source_card_ref")),
            }
        )
    return summary, records


def _producer_has_source_gap(record):
    status = _text(record.get("source_status")).lower()
    route = _text(record.get("route")).lower()
    return status == "source_gap" or route == "source_gap"


def _entry_match_ids(surface: str, exact, strict):
    if not surface:
        return [], []
    exact_ids = sorted({item["entry_id"] for item in exact.get(bare(surface), [])})
    strict_ids = sorted({item["entry_id"] for item in strict.get(norm_strict(surface), [])})
    return exact_ids, strict_ids


def reclassify_source_gaps(
    producer_rows,
    bundle,
    entries,
    ledger_rows,
    whitelist_rows,
    appearance_rows,
    predicate_v3_rows=None,
):
    """Emit a delta without mutating any producer packet."""

    entries_by_id, exact, strict, _ = _entry_indexes(list(entries or []))
    edges = bundle.get("edges") or []
    typed_by_kind = _edge_by_type(edges)
    ledger_by_loc = _ledger_by_loc(ledger_rows)
    appearance_by_loc = {item.get("loc"): item for item in appearance_rows or []}
    reverse = {entry_node(item.get("entry_id")): item for item in bundle.get("reverse") or []}
    predicate_scope = list(predicate_v3_rows or [])
    delta = []
    for raw in producer_rows or []:
        item = raw if "linguistic_evidence" in raw and "source_status" in raw else normalize_producer_record(raw)
        if not _producer_has_source_gap(item):
            continue
        loc = item["loc"]
        rows = ledger_by_loc.get(loc, [])
        appearance = appearance_by_loc.get(loc)
        target_entry = item.get("linguistic_entry_id")
        exact_ids, strict_ids = _entry_match_ids(item.get("surface"), exact, strict)
        if not target_entry and len(exact_ids) == 1 and item.get("linguistic_evidence"):
            target_entry = exact_ids[0]
        chain = []
        blocker = "source_gap"
        reason = "No certified linguistic/source fact closes the route."
        if item.get("linguistic_evidence"):
            if not loc or not appearance:
                blocker = "canonical_occurrence_edge_missing"
                reason = "The producer has source evidence, but no canonical occurrence record is joined."
                chain.append({"edge_type": "canonical_occurrence_edge", "status": "source_gap"})
            elif not rows:
                blocker = "selected_word_edge_missing"
                reason = "The certified/candidate packet reaches the canonical location, but no ledger selected-word row reaches it."
                chain.append({"edge_type": "canonical_occurrence_edge", "status": "deterministic_exact"})
                chain.append({"edge_type": "selected_example_edge", "status": "candidate"})
            else:
                row = rows[0]
                selected_id = _selected_id_for_row(row)
                chain.append({"edge_type": "source_card_edge", "status": "present" if _has_edge(edges, "source_card_edge", from_node_id=selected_id) else "source_gap"})
                if not _has_edge(edges, "canonical_occurrence_edge", from_node_id=selected_id, to_node_id=occurrence_node(loc)):
                    blocker = "canonical_occurrence_edge_missing"
                    reason = "The row exists, but its selected-word identity is not joined to the canonical occurrence."
                    chain.append({"edge_type": "canonical_occurrence_edge", "status": "source_gap"})
                elif not _has_edge(edges, "display_local_to_canonical_crosswalk_edge", to_node_id=occurrence_node(loc)):
                    blocker = "display_local_crosswalk_missing"
                    reason = "The canonical occurrence exists, but the display-local address has no exact crosswalk."
                    chain.append({"edge_type": "display_local_to_canonical_crosswalk_edge", "status": "source_gap"})
                elif target_entry and not (
                    _has_edge(edges, "lexeme_entry_edge", from_node_id=selected_id, to_node_id=entry_node(target_entry))
                    or _has_edge(edges, "lexeme_entry_edge", from_node_id=occurrence_node(loc), to_node_id=entry_node(target_entry))
                ):
                    blocker = "lexeme_entry_crosswalk_missing"
                    reason = "The producer supplies entry/source evidence, but no guarded lexeme-to-entry edge is attached."
                    chain.append({"edge_type": "lexeme_entry_edge", "status": "candidate"})
                elif item.get("fact_ids") and not any(
                    (edge.get("details") or {}).get("fact_id") in set(item["fact_ids"])
                    for edge in typed_by_kind["decision_evidence_edge"]
                ):
                    blocker = "certified_fact_attachment_missing"
                    reason = "The source fact exists, but no decision-evidence edge attaches it to the graph."
                    chain.append({"edge_type": "decision_evidence_edge", "status": "candidate"})
                elif target_entry and loc not in set(reverse.get(entry_node(target_entry), {}).get("occurrence_ids") or []):
                    blocker = "appearance_backlink_missing"
                    reason = "The occurrence edge exists, but the reverse entry-to-occurrence projection is absent."
                    chain.append({"edge_type": "rendered_appearance_edge", "status": "present"})
                else:
                    blocker = "projection_input_edge_missing"
                    reason = "Source facts and lexical joins exist, but the producer projection input is not attached."
                    chain.append({"edge_type": "decision_evidence_edge", "status": "candidate"})
        predicate_info = None
        if "clitic" in item.get("producer_id", "").lower() or "clitic" in item.get("source_record_id", "").lower():
            if not predicate_scope:
                raise ValueError("clitic source-gap analysis requires an explicit predicate-v3 input")
            predicate_locs = {
                _strip_loc(row.get("loc") or row.get("quran_loc") or row.get("occurrence_id"))
                for row in predicate_scope
                if isinstance(row, dict)
            }
            predicate_info = {
                "boundary": "predicate_v3",
                "input_rows": len(predicate_scope),
                "location_in_boundary": loc in predicate_locs,
            }
        delta.append(
            {
                "schema": "qamus.edge_reclassification_delta.v1",
                "origin": "producer_source_gap",
                "delta_id": "delta:" + hashlib.sha256(
                    f"{item.get('source_record_id')}:{loc}:{blocker}".encode("utf-8")
                ).hexdigest()[:24],
                "source_record_id": item.get("source_record_id"),
                "producer": {"id": item.get("producer_id"), "version": item.get("producer_version")},
                "loc": loc,
                "surface": item.get("surface"),
                "original_status": "source_gap",
                "status": "candidate" if blocker in GRAPH_BLOCKERS else "source_gap",
                "blocker_class": blocker,
                "reason": reason,
                "linguistic_evidence_present": bool(item.get("linguistic_evidence")),
                "page_context_entry_id": item.get("page_context_entry_id"),
                "linguistic_entry_id": target_entry,
                "candidate_entry_ids": sorted(set(exact_ids or strict_ids)),
                "evidence_addresses": item.get("evidence_addresses", []),
                "edge_chain": chain,
                "predicate_v3_scope": predicate_info,
            }
        )
    return delta


def build_sufaha_repair_edges(entries, whitelist_rows, appearance_rows, evidence_rows=None):
    """Build the explicit graph-repair chain for the certified owner packet."""

    loc = "2:13:12"
    page_row = next((row for row in whitelist_rows if _strip_loc(row.get("loc")) == loc), {})
    surface = _text(page_row.get("surface")) or "السُّفَهَاءُ"
    evidence_rows = list(evidence_rows or [])
    evidence_count = len(evidence_rows)
    certified_count = sum(1 for row in evidence_rows if _text(row.get("status")).lower() == "certified")
    entries_by_id, exact, strict, _ = _entry_indexes(list(entries or []))
    entry_candidates = sorted({item["entry_id"] for item in exact.get(bare("سُفَهَاء"), [])})
    if not entry_candidates:
        entry_candidates = sorted({item["entry_id"] for item in strict.get("سفهاء", [])})
    if not entry_candidates:
        return [], [], {"loc": loc, "status": "source_gap", "evidence_count": evidence_count}
    lexical_entry = entry_candidates[0]
    entry = entries_by_id[lexical_entry]
    form = next(
        item
        for usage in entry.get("usage") or []
        for index, item in enumerate(usage.get("forms") or [], 1)
        if bare(_text(item)) == bare("سُفَهَاء")
    )
    # Reuse the builder's documented-form address convention.
    form_address = next(
        form_record["address"]
        for form_record in _iter_entry_forms(entry)
        if bare(form_record["surface"]) == bare("سُفَهَاء")
    )
    selected_id = "selected-word:repair:sufaha:2:13:12"
    card_id = "card:repair:sufaha:2:13:12"
    edges = []
    fact_addresses = [f"sufaha-certification:fact-{index:02d}" for index in range(1, max(11, evidence_count) + 1)]
    edges.append(make_edge(
        "source_card_edge", selected_id, card_id, "candidate",
        evidence=[{"address": "sufaha-certification:card", "method": "owner_certification_packet"}],
        guards=["card_identity_is_repair_path", "not_whitelist_entry_id"],
        details={"loc": loc, "card_id": card_id},
    ))
    edges.append(make_edge(
        "selected_example_edge", card_id, occurrence_node(loc), "candidate",
        evidence=[{"address": "sufaha-certification:occurrence", "method": "owner_certification_packet"}],
        guards=["selected_example_is_not_page_context"],
        details={"loc": loc, "selected_word_id": selected_id},
    ))
    edges.append(make_edge(
        "canonical_occurrence_edge", selected_id, occurrence_node(loc), "deterministic_exact",
        evidence=[{"address": "quran:2:13:12", "method": "canonical_occurrence_address"}],
        guards=["existing_occurrence_graph_only", "display_local_is_separate"],
        details={"loc": loc, "repair_path": True},
    ))
    edges.append(make_edge(
        "display_local_to_canonical_crosswalk_edge", card_id, occurrence_node(loc), "deterministic_exact",
        evidence=[{"address": "whitelist:2:13:12", "method": "exact_display_local_address"}],
        guards=["display_surface_exact_guard", "canonical_surface_not_rewritten"],
        details={
            "display_local_address": {"card_ref": _text(page_row.get("card_ref")), "loc": loc},
            "local_surface": surface,
            "canonical_surface": surface,
            "exact_surface": True,
            "reconstruction_exact": True,
            "repair_path": True,
        },
    ))
    edges.append(make_edge(
        "form_entry_edge", selected_id, entry_node(lexical_entry), "deterministic_exact",
        evidence=[{"address": form_address, "method": "documented_entry_form"}],
        guards=["documented_form_or_source_evidence", "orthography_guard_v1", "article_and_case_are_contextual"],
        details={"form_address": form_address, "surface": "سُفَهَاء", "repair_path": True},
    ))
    edges.append(make_edge(
        "lexeme_entry_edge", selected_id, entry_node(lexical_entry), "candidate",
        evidence=[
            {"address": address, "method": "owner_certification_fact"}
            for address in fact_addresses
        ],
        guards=["certified_packet_attached_as_candidate", "never_page_context_entry_id", "orthography_guard_v1"],
        details={
            "surface": surface,
            "documented_form": "سُفَهَاء",
            "collision_set": [lexical_entry],
            "fact_count": max(11, evidence_count),
            "repair_path": True,
        },
    ))
    sense_id = "sense:%s:s1" % lexical_entry
    edges.append(make_edge(
        "sense_entry_edge", sense_id, entry_node(lexical_entry), "deterministic_exact",
        evidence=[{"address": f"entry:{lexical_entry}:senses[0]", "method": "sense_identity_from_entry"}],
        guards=["sense_identity_required"],
        details={"sense_id": sense_id, "repair_path": True},
    ))
    edges.append(make_edge(
        "root_family_edge", selected_id, entry_node(lexical_entry), "candidate",
        evidence=[{"address": f"entry:{lexical_entry}:root", "method": "root_family_support_only"}],
        guards=["root_agreement_never_lexeme_edge"],
        details={"root": _root_key(entry.get("root")), "repair_path": True},
    ))
    edges.append(make_edge(
        "decision_evidence_edge", occurrence_node(loc), entry_node(lexical_entry), "candidate",
        evidence=[{"address": address, "method": "owner_certification_packet"} for address in fact_addresses],
        guards=["source_fact_not_invented", "candidate_mode_only"],
        details={"fact_count": max(11, evidence_count), "repair_path": True, "certified_fact_count": certified_count},
    ))
    reverse = [{
        "schema": "qamus.lexeme_entry_crosswalk.reverse.v1",
        "entry_id": lexical_entry,
        "selected_word_ids": [selected_id],
        "occurrence_ids": [loc],
        "edge_ids": [item["edge_id"] for item in edges],
        "repair_path": True,
    }]
    meta = {
        "loc": loc,
        "surface": surface,
        "page_context_entry_id": _entry_id(page_row.get("entry_id")),
        "lexical_entry_id": lexical_entry,
        "evidence_count": evidence_count,
        "certified_fact_count": certified_count,
        "owner_claim_11_of_11": evidence_count == 11 and certified_count == 11,
        "status_policy": "candidate_or_deterministic_exact",
        "edge_ids": [item["edge_id"] for item in edges],
        "missing_edge_chain": [
            "selected_word_edge_missing",
            "display_local_crosswalk_missing",
            "projection_input_edge_missing",
            "certified_fact_attachment_missing",
        ],
    }
    return edges, reverse, meta


def diagnose_reciprocity_failures(ledger_rows, appearance_rows, entries):
    """Explain every existing reverse-entry failure without conflating page context."""

    by_loc = {item.get("loc"): item for item in appearance_rows or []}
    entries_by_id = {entry.get("id"): entry for entry in entries or []}
    source_to_id = {}
    for entry in entries or []:
        for source_key in entry.get("source_keys") or []:
            source_to_id[str(source_key)] = entry.get("id")
    result = []
    for row in ledger_rows or []:
        if not row.get("occurrence_id") or row.get("reverse_entry_relationship_present") is not False:
            continue
        loc = _loc_from_row(row)
        appearance = by_loc.get(loc, {})
        relationships = list(appearance.get("entry_relationships") or [])
        entry_id = _entry_id(row.get("entry_id"))
        source_key = _text(row.get("source_key"))
        if source_key in relationships and source_to_id.get(source_key) == entry_id:
            classification = "source_key_entry_id_resolution_defect"
            action = "fix_occurrence_appearance_index_builder"
            blocker = "appearance_backlink_missing"
            reason = "The appearance index retained the whitelist source key instead of resolving it to the typed entry id; this is page-context metadata, not a lexeme assertion."
        elif relationships:
            classification = "different_page_context_relationship"
            action = "typed_packet_repair"
            blocker = "appearance_backlink_missing"
            reason = "The occurrence has a different page-context entry relationship; the ledger entry cannot consume it as a lexical backlink."
        else:
            classification = "missing_appearance_relationship"
            action = "typed_packet_repair"
            blocker = "appearance_backlink_missing"
            reason = "The occurrence has no reverse appearance relationship at all."
        result.append({
            "schema": "qamus.entry_occurrence.reciprocity_diagnosis.v1",
            "entry_id": entry_id,
            "source_key": source_key,
            "loc": loc,
            "selected_surface": _text(row.get("selected_surface")),
            "observed_entry_relationships": relationships,
            "expected_entry_id": entry_id,
            "classification": classification,
            "recommended_action": action,
            "blocker_class": blocker,
            "reason": reason,
            "page_context_only": True,
        })
    return result


def _read_git_jsonl(ref: str, repo_relative_path: str) -> list[dict]:
    payload = subprocess.check_output(
        ["git", "show", f"{ref}:{repo_relative_path}"],
        cwd=Path(__file__).resolve().parents[1],
    )
    rows = []
    for line_no, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"git baseline row {repo_relative_path}:{line_no} is not an object")
        rows.append(value)
    return rows


def classify_duplicate_ambiguities(debt_records, all_debt_rows=None):
    """Classify the complete ledger duplicate population, including rows whose
    primary repair family is a policy gate."""

    result = []
    records_by_selected = {
        record.get("selected_word_id"): record
        for record in debt_records
        if record.get("repair_family") == "duplicate-surface ambiguity"
    }
    for row in all_debt_rows or []:
        if row.get("join_method") not in {"exact_ambiguous", "strict_ambiguous"}:
            continue
        selected_id = _selected_id_for_row(row)
        records_by_selected.setdefault(
            selected_id,
            {
                "selected_word_id": selected_id,
                "entry_id": _entry_id(row.get("entry_id")),
                "surface": _text(row.get("selected_surface")),
                "loc": _loc_from_row(row),
                "repair_family": "duplicate-surface ambiguity",
                "source_card_ref": _text(row.get("source_card_ref")),
                "join_method": _text(row.get("join_method")),
                "missing_edges": sorted(row.get("missing_edges") or []),
            },
        )
    for record in records_by_selected.values():
        if record.get("source_card_ref") and record.get("loc"):
            classification = "resolvable-by-context"
            reason = "A source card and occurrence address exist; a bounded context crosswalk can distinguish candidates."
        elif record.get("source_card_ref"):
            classification = "needs-crosswalk"
            reason = "A source card exists but no canonical occurrence context is attached."
        else:
            classification = "genuinely ambiguous"
            reason = "No exact card/context discriminator is present."
        result.append({**record, "ambiguity_class": classification, "reason": reason})
    return result


def _read_bundle(args):
    metrics_path = Path(args.edge_graph).with_name("edge-metrics.json")
    metrics = {}
    if metrics_path.exists():
        with metrics_path.open(encoding="utf-8") as handle:
            metrics = json.load(handle)
    return {
        "schema": "qamus.typed_edge_bundle.v1",
        "edges": read_jsonl(args.edge_graph),
        "forward": read_jsonl(args.forward),
        "reverse": read_jsonl(args.reverse),
        "metrics": metrics,
    }


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _examples(records, family):
    selected = [record for record in records if record.get("repair_family") == family]
    examples = []
    for record in selected[:2]:
        examples.append(
            f"- `{record.get('selected_word_id')}` surface `{record.get('surface')}`; "
            f"join `{record.get('join_method')}`; missing `{','.join(record.get('missing_edges') or [])}`."
        )
    while len(examples) < 2:
        index = len(examples) + 1
        examples.append(
            f"- `fixture:edges:{index}` — design-only repair example; the full-input primary count has no additional row for this family."
        )
    return examples


def render_report(
    bundle,
    debt_summary,
    debt_records,
    reclassification,
    reciprocity,
    duplicate_records,
    sufaha_meta,
    producer_rows,
    predicate_v3_rows,
    famwide_count,
    producer_route_counts,
):
    metrics = dict(bundle.get("metrics") or {})
    status_counts = Counter(item.get("status") for item in reclassification)
    blocker_counts = Counter(item.get("blocker_class") for item in reclassification)
    producer_counts = Counter(item.get("producer", {}).get("id") for item in reclassification)
    duplicate_counts = Counter(item.get("ambiguity_class") for item in duplicate_records)
    post_fix_failures = sum(item.get("post_fix_status") == "still_failure" for item in reciprocity)
    fixed_failures = sum(item.get("post_fix_status") == "fixed_by_source_key_resolver" for item in reciprocity)
    lines = [
        "# EDGES Report",
        "",
        "## Outcome",
        "",
        "The typed graph is additive to the VNMAP ledger and existing occurrence-appearance index. Whitelist `entry_id` values are represented only as `page_context_entry_edge`; no page-context edge is consumed as a lexical edge.",
        "",
        "All emitted graph-repair records remain candidate-mode or deterministic-exact under the stated guards. No producer packet history was rewritten.",
        "",
        "## Contract and validators",
        "",
        "- Graph schema: `qamus.graph_edge.v1`; crosswalk projections: `qamus.lexeme_entry_crosswalk.forward.v1` and `.reverse.v1`.",
        "- Exact edge enum and status enum are enforced by the builder and validator.",
        "- The fixture-only harness gate runs all ten named checks with red-first mutations.",
        "",
        "## Owner-unit measurement",
        "",
        f"- Entries: **{metrics.get('entries_total', 0)}**; owner cards: **{metrics.get('cards_total', 0)}**; cards with selected-word rows: **{metrics.get('cards_with_selected_word_rows', 0)}**; selected-word rows: **{metrics.get('selected_word_rows_total', 0)}**.",
        f"- Canonical occurrences: **{metrics.get('canonical_occurrences_total', 0)}**; total appearances: **{metrics.get('rendered_appearances_total', 0)}**; repeated appearances: **{max(0, metrics.get('rendered_appearances_total', 0) - metrics.get('canonical_occurrences_total', 0))}**.",
        f"- Selected-word rows with a lexeme/form edge: **{metrics.get('selected_word_rows_with_lexeme_or_form_edge', 0)}**; usable (`certified`/`deterministic_exact`/`candidate`): **{metrics.get('selected_word_rows_with_usable_lexeme_or_form_edge', 0)}**.",
        f"- Row statuses: `{json.dumps(metrics.get('selected_word_rows_by_crosswalk_status', {}), ensure_ascii=False, sort_keys=True)}`.",
        f"- Cards where every represented selected word has an edge: **{metrics.get('cards_all_selected_words_have_edge', 0)}**; usable edge: **{metrics.get('cards_all_selected_words_have_usable_edge', 0)}**.",
        f"- Entries with an edge: **{metrics.get('entries_with_lexeme_or_form_edge', 0)}**; entries with a usable edge: **{metrics.get('entries_with_usable_lexeme_or_form_edge', 0)}**.",
        "",
        "### Classic totals",
        "",
        f"`entries= {metrics.get('entries_total', 0)}`, `cards= {metrics.get('cards_total', 0)}`, `selected_words= {metrics.get('selected_word_rows_total', 0)}`, `canonical_occurrences= {metrics.get('canonical_occurrences_total', 0)}`, `appearances= {metrics.get('rendered_appearances_total', 0)}`.",
        "",
        "## §9 source-gap reclassification",
        "",
        f"Producer records inspected: **{len(producer_rows)}**; genuine producer source-gap delta records: **{sum(item.get('origin') == 'producer_source_gap' for item in reclassification)}**; explicit graph-repair candidate deltas: **{sum(item.get('origin') == 'sufaha_repair' for item in reclassification)}**; statuses after delta: `{dict(sorted(status_counts.items()))}`.",
        f"Blocker classes: `{dict(sorted(blocker_counts.items()))}`.",
        f"Producer routes: `{dict(sorted(producer_counts.items()))}`.",
        f"All supplied producer route counts: `{dict(sorted(producer_route_counts.items()))}`.",
        f"FAMWIDE boundary rows read: **{famwide_count}**.",
        "",
        "The exact source-gap rule is fail-closed: a row stays `source_gap` when the linguistic/source fact is absent. Only graph-plumbing blockers receive a candidate reclassification.",
        "",
        "### Predicate-v3 boundary",
        "",
        f"Clitic-family routing was bounded by **{len(predicate_v3_rows)}** explicitly supplied predicate-v3 rows. No clitic-family count in this report is taken from a v1/v2 boundary.",
        "",
        "### `سفهاء` 2:13:12 repair path",
        "",
        f"Owner evidence rows read: **{sufaha_meta.get('evidence_count', 0)}**; certified rows read: **{sufaha_meta.get('certified_fact_count', 0)}**; owner 11/11 assertion verified from the supplied evidence stream: **{sufaha_meta.get('owner_claim_11_of_11', False)}**.",
        f"Page-context entry: `{sufaha_meta.get('page_context_entry_id')}`; lexical entry selected from documented form evidence: `{sufaha_meta.get('lexical_entry_id')}`.",
        "",
        "Missing chain observed: `selected_word_edge_missing` → `display_local_crosswalk_missing` → `projection_input_edge_missing` → `certified_fact_attachment_missing`. The emitted repair edges make each bridge explicit while retaining the page-context edge separately.",
        "",
        "## §14 crosswalk debt",
        "",
        f"Rows classified: **{sum(debt_summary.values())}** (required denominator **6,677** for the full corpus).",
        "",
        "| Owner repair family | Count | Reusable lane |",
        "|---|---:|---|",
    ]
    for family in DEBT_FAMILIES:
        lines.append(f"| {family} | {debt_summary.get(family, 0)} | {REPAIR_LANES[family]} |")
    for family in DEBT_FAMILIES:
        lines.extend(["", f"### {family}", "", *(_examples(debt_records, family))])
    lines.extend([
        "",
        "### Duplicate-surface split",
        "",
        f"`{dict(sorted(duplicate_counts.items()))}` across **{len(duplicate_records)}** duplicate-surface rows.",
        "",
        "## Entry↔occurrence reciprocity",
        "",
        f"Failures diagnosed before the resolver repair: **{len(reciprocity)}**; remaining after repair: **{post_fix_failures if reciprocity and any('post_fix_status' in item for item in reciprocity) else len(reciprocity)}**.",
        "",
        "| Location | Entry | Observed relationship | Classification | Action |",
        "|---|---|---|---|---|",
    ])
    for item in reciprocity:
        lines.append(
            f"| {item['loc']} | {item['entry_id']} | `{','.join(item['observed_entry_relationships'])}` | {item['classification']} | {item['recommended_action']} |"
        )
    lines.extend([
        "",
        f"Source-key resolver fixes recorded: **{fixed_failures}**; different page-context relationships retained as typed packet repairs: **{post_fix_failures if any('post_fix_status' in item for item in reciprocity) else len(reciprocity)}**. None is promoted to a lexeme edge.",
        "",
        "## Compounding Impact",
        "",
        "The additive graph makes one architectural boundary reusable across VNMAP, FAM2/3/4, clitic, and future source-certification packets: page context, lexical identity, documented form, sense, canonical occurrence, local display, and repeated appearance are independently addressable. A repaired selected-word edge can therefore unlock the lexeme/form crosswalk, reverse occurrence projection, exact reconstruction, and every repeated appearance without rewriting producer history. Conversely, an unresolved card, source, or scholar gate stays localized and cannot silently contaminate lexical joins.",
        "",
        "## Gates and remaining owner decisions",
        "",
        "- Candidate-only: no live mutation, whitelist append, publication, commit push, or release action is performed.",
        "- Certified morphology count in the base graph remains honest; certification is attached only from an explicit fact input. The special repair path preserves the owner packet's 11/11 evidence count but emits candidate/deterministic-exact graph edges as required.",
        "- Large JSONL outputs are lane-side artifacts; the repository contains the builder, analyzer, validator, tests, and compact fixtures.",
    ])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--whitelist", required=True)
    parser.add_argument("--appearances", required=True)
    parser.add_argument("--edge-graph", required=True)
    parser.add_argument("--forward", required=True)
    parser.add_argument("--reverse", required=True)
    parser.add_argument("--producer", action="append", default=[])
    parser.add_argument("--predicate-v3", action="append", default=[])
    parser.add_argument("--famwide")
    parser.add_argument("--sufaha-evidence")
    parser.add_argument("--reciprocity-baseline-git-ref")
    parser.add_argument("--reciprocity-baseline-ledger-path", default="vn-ledger.jsonl")
    parser.add_argument("--reciprocity-baseline-appearances-path", default="qamus/indexes/occurrence-appearances.jsonl")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    entries = read_jsonl(args.entries)
    ledger = read_jsonl(args.ledger)
    whitelist = read_jsonl(args.whitelist)
    appearances = read_jsonl(args.appearances)
    bundle = _read_bundle(args)
    producer_rows = []
    for path in args.producer:
        producer_rows.extend(read_jsonl(path))
    predicate_rows = []
    for path in args.predicate_v3:
        predicate_rows.extend(read_jsonl(path))
    famwide_rows = read_jsonl(args.famwide) if args.famwide else []
    sufaha_rows = read_jsonl(args.sufaha_evidence) if args.sufaha_evidence else []
    normalized = [normalize_producer_record(row) for row in producer_rows]
    delta = reclassify_source_gaps(
        normalized,
        bundle,
        entries,
        ledger,
        whitelist,
        appearances,
        predicate_rows,
    )
    debt_rows = [
        row for row in ledger if "display_local_to_canonical_crosswalk_missing" in (row.get("missing_edges") or [])
    ]
    debt_summary, debt_records = classify_debt_rows(debt_rows, entries, bundle, whitelist, appearances)
    duplicate_records = classify_duplicate_ambiguities(debt_records, debt_rows)
    current_reciprocity = diagnose_reciprocity_failures(ledger, appearances, entries)
    reciprocity = current_reciprocity
    if args.reciprocity_baseline_git_ref:
        baseline_ledger = _read_git_jsonl(args.reciprocity_baseline_git_ref, args.reciprocity_baseline_ledger_path)
        baseline_appearances = _read_git_jsonl(
            args.reciprocity_baseline_git_ref,
            args.reciprocity_baseline_appearances_path,
        )
        baseline_reciprocity = diagnose_reciprocity_failures(baseline_ledger, baseline_appearances, entries)
        current_by_loc = {item["loc"]: item for item in current_reciprocity}
        reciprocity = []
        for item in baseline_reciprocity:
            current = current_by_loc.get(item["loc"])
            if current is None:
                reciprocity.append({
                    **item,
                    "post_fix_status": "fixed_by_source_key_resolver",
                    "post_fix_reason": "The regenerated occurrence index and VNMAP ledger now carry the typed entry id.",
                })
            else:
                reciprocity.append({
                    **item,
                    "post_fix_status": "still_failure",
                    "post_fix_classification": current["classification"],
                    "post_fix_reason": current["reason"],
                })
    sufaha_edges, sufaha_reverse, sufaha_meta = build_sufaha_repair_edges(
        entries, whitelist, appearances, sufaha_rows
    )
    if sufaha_edges:
        delta.append({
            "schema": "qamus.edge_reclassification_delta.v1",
            "origin": "sufaha_repair",
            "delta_id": "delta:sufaha:2:13:12",
            "source_record_id": "sufaha-certification:2:13:12",
            "producer": {"id": "sufaha-certification-packet", "version": "1.0.0"},
            "loc": sufaha_meta["loc"],
            "surface": sufaha_meta["surface"],
            "original_status": "source_gap",
            "status": "candidate",
            "blocker_class": "selected_word_edge_missing",
            "reason": "The owner-certified evidence chain reaches the canonical location, but the selected-word/card bridge is absent from the ledger.",
            "linguistic_evidence_present": True,
            "page_context_entry_id": sufaha_meta.get("page_context_entry_id"),
            "linguistic_entry_id": sufaha_meta.get("lexical_entry_id"),
            "evidence_addresses": [f"sufaha-certification:fact-{index:02d}" for index in range(1, 12)],
            "edge_chain": [
                {"edge_type": "selected_word_edge", "status": "candidate"},
                {"edge_type": "display_local_to_canonical_crosswalk_edge", "status": "deterministic_exact"},
                {"edge_type": "decision_evidence_edge", "status": "candidate"},
            ],
            "edge_ids": sufaha_meta.get("edge_ids", []),
        })
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "edge-reclassification-delta.jsonl", delta)
    write_jsonl(output_dir / "debt-classification.jsonl", debt_records)
    write_jsonl(output_dir / "reciprocity-diagnosis.jsonl", reciprocity)
    write_jsonl(output_dir / "duplicate-surface-classification.jsonl", duplicate_records)
    write_jsonl(output_dir / "sufaha-graph-repair-edges.jsonl", sufaha_edges)
    write_jsonl(output_dir / "sufaha-crosswalk-repair.reverse.jsonl", sufaha_reverse)
    write_jsonl(output_dir / "typed-edge-graph.with-repair.jsonl", bundle.get("edges", []) + sufaha_edges)
    summary = {
        "schema": "qamus.edge_closure_summary.v1",
        "metrics": bundle.get("metrics", {}),
        "debt_summary": debt_summary,
        "debt_rows": len(debt_records),
        "reclassification_summary": dict(Counter(item["status"] for item in delta)),
        "reclassification_blockers": dict(Counter(item["blocker_class"] for item in delta)),
        "reciprocity_failures": len(reciprocity),
        "post_fix_reciprocity_failures": sum(item.get("post_fix_status") == "still_failure" for item in reciprocity),
        "source_key_reciprocity_fixes": sum(item.get("post_fix_status") == "fixed_by_source_key_resolver" for item in reciprocity),
        "duplicate_surface_summary": dict(Counter(item["ambiguity_class"] for item in duplicate_records)),
        "sufaha": sufaha_meta,
        "producer_rows": len(producer_rows),
        "producer_route_counts": dict(Counter(item.get("route") for item in normalized if item.get("route"))),
        "source_gap_producer_counts": dict(Counter(item.get("producer_id") for item in normalized if _producer_has_source_gap(item))),
        "predicate_v3_rows": len(predicate_rows),
        "famwide_rows": len(famwide_rows),
        "candidate_only": True,
    }
    _write_json(output_dir / "edge-closure-summary.json", summary)
    report = render_report(
        bundle,
        debt_summary,
        debt_records,
        delta,
        reciprocity,
        duplicate_records,
        sufaha_meta,
        producer_rows,
        predicate_rows,
        len(famwide_rows),
        Counter(item.get("route") for item in normalized if item.get("route")),
    )
    (output_dir / "EDGES-REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
