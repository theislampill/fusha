#!/usr/bin/env python3
"""Shared, candidate-only compiler for the PROOF-V typed-fact envelope."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fd_compiler


PROJECTOR_ID = "proofv.shared_compiler.v1"
VERSION = "1.0.0"
N_LANG_SARF = "Ṣarf — how this piece forms the word"
N_LANG_NAHW = "Naḥw — what this piece does here"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _canonical_ownership(proof: Mapping[str, Any]) -> list[dict[str, Any]]:
    for fact in proof.get("facts") or []:
        if isinstance(fact, Mapping) and fact.get("fact_type") == "proofv_letter_ownership":
            value = fact.get("fact_value") or {}
            ownership = value.get("letter_ownership") or []
            if isinstance(ownership, list) and ownership:
                return [copy.deepcopy(item) for item in ownership if isinstance(item, Mapping)]
    raise ValueError("PROOF-V shared compiler requires canonical proofv_letter_ownership facts")


def _component_bridge(proof: Mapping[str, Any], ownership: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    for item in ownership:
        display_class = str(item.get("display_class") or "qg-unknown")
        role = str(item.get("role") or "component")
        if role == "linking_result_fa":
            fact_type = "function_component"
        elif role == "protective_nun":
            fact_type = "protective_nun"
        elif role == "object_pronoun_1cs":
            fact_type = "clitic_component"
        else:
            fact_type = "host_component"
        facts.append({
            "fact_type": fact_type,
            "fact_value": {
                "segment_index": int(item["base_letter_index"]),
                "surface": str(item["surface"]),
                "role": role,
                "class": display_class,
                "typed_kind": str(item.get("typed_kind") or "sarf.letter_component"),
            },
        })
    return {
        "record_type": "projection_input",
        "canonical_occurrence": copy.deepcopy(proof["canonical_occurrence"]),
        "facts": facts,
        "projection": {"status": "candidate"},
    }


def _segment_text(item: Mapping[str, Any]) -> str:
    role = str(item.get("role") or "written piece")
    labels = {
        "linking_result_fa": "a linking/result fāʾ",
        "hamzat_al_wasl": "the governed hamzat al-waṣl onset",
        "root_radical_shared_with_derivative_infix": "the shared root-first-radical and Form-VIII infix letter",
        "root_radical": "a root radical",
        "protective_nun": "the protective nūn, not a particle",
        "object_pronoun_1cs": "the attached first-person singular object pronoun",
    }
    return labels.get(role, "a typed written piece")


def compile_payload(proof: Mapping[str, Any], *, appearances: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compile all display shapes from the canonical facts in ``proof``."""

    surface = str((proof.get("canonical_occurrence") or {}).get("surface") or "")
    ownership = _canonical_ownership(proof)
    canonical_facts = [
        fact for fact in proof.get("facts") or []
        if isinstance(fact, Mapping) and fact.get("fact_type") and fact.get("fact_id")
    ]
    fact_map = {str(fact["fact_type"]): fact for fact in canonical_facts}
    derived_value = (fact_map.get("derived_verb_evidence", {}).get("fact_value") or {})
    nahw_value = (fact_map.get("nahw_dependency", {}).get("fact_value") or {})
    at_rest_spans = [
        {
            "span_id": f"span:base-letter-{int(item['base_letter_index'])}",
            "start": int(item["start"]),
            "end": int(item["end"]),
            "surface": str(item["surface"]),
            "role": str(item["role"]),
            "display_class": str(item["display_class"]),
            "primary_plane": str(item["primary_plane"]),
            "marks_hover_only": list(item.get("marks") or []),
        }
        for item in ownership
    ]
    reconstructed = "".join(str(span["surface"]) for span in at_rest_spans)
    exact = {
        "passed": reconstructed == surface,
        "expected_surface": surface,
        "joined_surface": reconstructed,
        "span_count": len(at_rest_spans),
        "base_letter_indices_complete": [span["span_id"] for span in at_rest_spans] == [f"span:base-letter-{index}" for index in range(len(at_rest_spans))],
    }
    # Use the existing shared F-D compiler to produce the canonical component
    # view.  PROOF-V then adds its verb-specific letter ownership and Naḥw
    # uncertainty fields around that shared result.
    shared_view = fd_compiler.build_fact_derived_views(
        surface,
        _component_bridge(proof, ownership),
        None,
        source_segments=at_rest_spans,
    )
    payload_id = "proofv.payload:" + _hash({
        "surface": surface,
        "at_rest_spans": at_rest_spans,
        "canonical_fact_ids": sorted(str(fact["fact_id"]) for fact in canonical_facts),
        "uncertainty": proof.get("uncertainty"),
        "shared_payload_id": shared_view.get("payload_id"),
    })[:24]
    uncertainty = copy.deepcopy(proof.get("uncertainty") or {})
    segment_records = []
    for item in ownership:
        segment_records.append({
            "segment_index": int(item["base_letter_index"]),
            "surface": str(item["surface"]),
            "role": str(item["role"]),
            "display_class": str(item["display_class"]),
            "primary_display": True,
            "marks_hover_only": list(item.get("marks") or []),
            "sarf_text": f"{N_LANG_SARF}: {_segment_text(item).capitalize()}.",
            "nahw_text": f"{N_LANG_NAHW}: {_segment_text(item).capitalize()} occupies its overt written span.",
        })
    sarf_text = (
        f"The written pieces preserve the Form {derived_value.get('form', 'candidate')} pattern, the governed onset, "
        "the shared-letter gemination, and the attached pronoun pieces."
    )
    nahw_text = (
        "The exact governor and object relation are still being checked."
        if nahw_value.get("status") == "unresolved"
        else "The Naḥw relation is carried by the canonical typed fact."
    )
    compact_text = "PENDING — the learner gloss is held while the exact relations are checked."
    compact = {"payload_id": payload_id, "surface": surface, "text": compact_text, "uncertainty": uncertainty}
    sarf_fact_types = [
        fact_type for fact_type in (
            "derived_verb_evidence",
            "proofv_letter_ownership",
            "protective_nun",
            "object_pronoun",
        ) if fact_type in fact_map
    ]
    nahw_status = str(nahw_value.get("status") or "unresolved")
    nahw_route = str(nahw_value.get("route") or "scholar-packet:nahw-governor-object:19:43:10")
    expanded = {
        "payload_id": payload_id,
        "surface": surface,
        "sarf": {"label": N_LANG_SARF, "text": sarf_text, "segments": segment_records, "facts": sarf_fact_types},
        "nahw": {"label": N_LANG_NAHW, "text": nahw_text, "status": nahw_status, "route": nahw_route},
        "uncertainty": uncertainty,
    }
    per_appearance = []
    for appearance in appearances:
        per_appearance.append({
            "appearance_index": int(appearance.get("appearance_index") or 0),
            "surface_kind": str(appearance.get("surface_kind") or "reader"),
            "surface": str(appearance.get("surface") or surface),
            "payload_id": payload_id,
            "same_payload_identity": True,
        })
    hover = {
        "status": "pending",
        "text": "PENDING — source review required before a learner gloss is eligible.",
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
    }
    readback = {
        "surface": surface,
        "reconstructed_surface": reconstructed,
        "exact_reconstruction": exact["passed"],
        "compact_payload_id": compact["payload_id"],
        "expanded_payload_id": expanded["payload_id"],
        "same_payload_identity": compact["payload_id"] == expanded["payload_id"] == payload_id,
        "per_appearance_payload_ids": sorted({item["payload_id"] for item in per_appearance}),
    }
    return {
        "schema": "qamus.proofv.shared_compiler_payload.v1",
        "compiler": {
            "id": "tools.fd_compiler.build_fact_derived_views",
            "version": "FD2-carrier-1.0.0",
            "adapter": PROJECTOR_ID,
            "input_fact_types": sorted(str(fact["fact_type"]) for fact in canonical_facts),
            "input_fact_ids": sorted(str(fact["fact_id"]) for fact in canonical_facts),
        },
        "payload_id": payload_id,
        "candidate_status": str(proof.get("status") or "source_gap"),
        "authorization_state": "pre_apply_not_authorized",
        "live_mutation_allowed": False,
        "public_materialization_allowed": False,
        "canonical_occurrence": copy.deepcopy(proof["canonical_occurrence"]),
        "at_rest": {"surface": surface, "spans": at_rest_spans, "exact_reconstruction": exact},
        "compact": compact,
        "expanded": expanded,
        "hover": hover,
        "per_appearance": per_appearance,
        "readback": readback,
        "uncertainty": uncertainty,
        "shared_carrier_view": {"payload_id": shared_view.get("payload_id"), "generated_from_facts": shared_view.get("generated_from_facts"), "n_lang_clean": shared_view.get("n_lang_clean")},
    }


if __name__ == "__main__":
    raise SystemExit("Use tools.build_proofv_verb.py to compile the PROOF-V packet.")
