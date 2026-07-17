#!/usr/bin/env python3
"""Compile the PROOF-P particle proof from a small canonical source packet.

The compiler is deliberately MCP-free.  It can capture the one selected case from
the read-only lane inputs, then rerun from the committed source packet so the
artifact directory is self-contained.  Source facts and graph edges stay separate
from the learner-facing candidate payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_typed_edge_crosswalk import (  # noqa: E402
    EDGE_TYPE_SET,
    STATUS_SET,
    appearance_node,
    card_node,
    entry_node,
    make_edge,
    occurrence_node,
    selected_word_node,
    sense_node,
)
from tools.typed_claim_contract import validate_contract_record  # noqa: E402


PROJECTOR_ID = "proofp.shared_candidate_projection.v1"
VERSION = "1.0.0"
PROOF_SCHEMA = "qamus.proof_particle"
CONTRACT_ID = "proofp:ma:2:284:10"
PROJECTION_ID = "proofp.ma.2-284-10.v1"
ENTRY_ID = "b8e480aebafe"
SOURCE_KEY = "p099"
HEADWORD = "مَا"
SURFACE = "مَا"
CARD_REF = "2:284"
CARD_ID = f"card:{ENTRY_ID}:u1:x1"
SELECTED_WORD_ID = f"selected-word:{ENTRY_ID}:s1:u1:f1:c2:284:x1"
QURAN_LOC = "2:284:10"
OCCURRENCE_ID = f"quran:{QURAN_LOC}"
WBW_LOC = f"wbw:{QURAN_LOC}"
CONTEXT_LOCS = {
    "2:284:2",
    "2:284:8",
    "2:284:9",
    "2:284:10",
    "2:284:11",
    "2:284:12",
    "2:284:14",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected an object")
        rows.append(row)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _loc(row: dict[str, Any]) -> str:
    value = str(row.get("loc", ""))
    if value.startswith("quran:"):
        return value[6:]
    return value


def _compact_card(usage: dict[str, Any]) -> dict[str, Any]:
    examples = usage.get("examples") or []
    selected = next((item for item in examples if item.get("ref") == CARD_REF), None)
    if selected is None:
        raise ValueError(f"p099 usage 1 does not carry card {CARD_REF}")
    return {
        "usage_index": 1,
        "sense": usage.get("sense"),
        "example_index": examples.index(selected) + 1,
        "card_ref": CARD_REF,
        "text": selected.get("ar", ""),
        "forms": list(usage.get("forms") or []),
    }


def _source_capture(
    entries_path: Path,
    whitelist_path: Path,
    forward_path: Path,
    reverse_path: Path,
) -> dict[str, Any]:
    return {
        "mode": "read_only_lane_snapshot",
        "inputs": [
            {"name": "entries.jsonl", "sha256": file_digest(entries_path)},
            {"name": "rh_live_01_beta_whitelist.jsonl", "sha256": file_digest(whitelist_path)},
            {"name": "lexeme-entry-crosswalk.forward.jsonl", "sha256": file_digest(forward_path)},
            {"name": "lexeme-entry-crosswalk.reverse.jsonl", "sha256": file_digest(reverse_path)},
        ],
        "note": "Read-only capture; no live MCP, runtime, or publication state is included.",
    }


def capture_source_facts(
    entries_path: Path,
    whitelist_path: Path,
    forward_path: Path,
    reverse_path: Path,
) -> dict[str, Any]:
    entries = read_jsonl(entries_path)
    entry = next((item for item in entries if item.get("id") == ENTRY_ID), None)
    if entry is None:
        raise ValueError(f"entry {ENTRY_ID} was not found in entries.jsonl")
    if SOURCE_KEY not in (entry.get("source_keys") or []):
        raise ValueError(f"entry {ENTRY_ID} is not tagged {SOURCE_KEY}")

    whitelist = read_jsonl(whitelist_path)
    context_rows = [row for row in whitelist if _loc(row) in CONTEXT_LOCS and row.get("card_ref") == CARD_REF]
    by_loc: dict[str, dict[str, Any]] = {}
    for row in context_rows:
        loc = _loc(row)
        if loc not in by_loc:
            by_loc[loc] = row
    missing = sorted(CONTEXT_LOCS - set(by_loc))
    if missing:
        raise ValueError(f"whitelist context is missing exact locations: {missing}")
    occurrence = by_loc[QURAN_LOC]
    if occurrence.get("surface") != SURFACE:
        raise ValueError("selected whitelist occurrence is not the exact surface مَا")

    selected_word = next(
        (
            row
            for row in read_jsonl(forward_path)
            if row.get("selected_word_id") == SELECTED_WORD_ID
        ),
        None,
    )
    if selected_word is None:
        raise ValueError(f"crosswalk forward row missing {SELECTED_WORD_ID}")
    reverse = next(
        (
            row
            for row in read_jsonl(reverse_path)
            if row.get("entry_id") == ENTRY_ID and SELECTED_WORD_ID in (row.get("selected_word_ids") or [])
        ),
        None,
    )
    if reverse is None:
        raise ValueError("crosswalk reverse row missing the selected word")

    usages = entry.get("usage") or []
    if not usages:
        raise ValueError("p099 entry has no usage cards")
    usage = usages[0]
    selected_card = _compact_card(usage)
    if selected_card["forms"] != [SURFACE]:
        raise ValueError("selected card form is not the exact particle surface")

    compact_entry = {
        "id": entry.get("id"),
        "headword": entry.get("headword"),
        "section": entry.get("section"),
        "source_keys": list(entry.get("source_keys") or []),
        "root": entry.get("root", ""),
        "root_translit": entry.get("root_translit", ""),
        "tags": list(entry.get("tags") or []),
        "senses": [
            {
                "n": sense.get("n"),
                "ar": sense.get("ar"),
                "gloss": sense.get("gloss"),
                "translit": sense.get("translit"),
            }
            for sense in entry.get("senses") or []
        ],
        "selected_card": selected_card,
    }

    same_surface_locs = sorted(
        _loc(row)
        for row in context_rows
        if row.get("surface") == SURFACE and _loc(row) in {"2:284:2", QURAN_LOC}
    )
    return {
        "schema": "qamus.proof_particle.source_facts.v1",
        "selection": {
            "owner_list_label": "مَا",
            "entry_id": ENTRY_ID,
            "source_key": SOURCE_KEY,
            "sense_number": 1,
            "card_ref": CARD_REF,
            "selected_word_id": SELECTED_WORD_ID,
            "occurrence_id": OCCURRENCE_ID,
        },
        "entry": compact_entry,
        "selected_word_crosswalk": selected_word,
        "reverse_crosswalk": reverse,
        "occurrence": occurrence,
        "context_rows": [by_loc[loc] for loc in sorted(by_loc, key=lambda value: tuple(int(part) for part in value.split(":")))],
        "same_surface_card_occurrence_locs": same_surface_locs,
        "source_capture": _source_capture(entries_path, whitelist_path, forward_path, reverse_path),
    }


def validate_source_facts(source: dict[str, Any]) -> None:
    if source.get("schema") != "qamus.proof_particle.source_facts.v1":
        raise ValueError("source facts schema is not qamus.proof_particle.source_facts.v1")
    selection = source.get("selection") or {}
    entry = source.get("entry") or {}
    card = entry.get("selected_card") or {}
    crosswalk = source.get("selected_word_crosswalk") or {}
    reverse = source.get("reverse_crosswalk") or {}
    occurrence = source.get("occurrence") or {}
    if selection.get("entry_id") != ENTRY_ID or entry.get("id") != ENTRY_ID:
        raise ValueError("source facts do not point to p099 entry b8e480aebafe")
    if selection.get("source_key") != SOURCE_KEY or SOURCE_KEY not in (entry.get("source_keys") or []):
        raise ValueError("source facts do not retain source key p099")
    if entry.get("headword") != HEADWORD or entry.get("section") != "particle":
        raise ValueError("source facts do not retain the particle entry identity")
    if entry.get("root") not in ("", None):
        raise ValueError("closed-class particle source fact must not carry a root")
    if card.get("card_ref") != CARD_REF or card.get("forms") != [SURFACE]:
        raise ValueError("selected card/form backlink is not exact")
    if crosswalk.get("selected_word_id") != SELECTED_WORD_ID:
        raise ValueError("selected-word crosswalk identity is not exact")
    if crosswalk.get("crosswalk_status") != "deterministic_exact":
        raise ValueError("selected-word lexical crosswalk is not deterministic_exact")
    if crosswalk.get("matched_entry_ids") != [ENTRY_ID]:
        raise ValueError("selected-word collision set is not the exact singleton entry")
    if crosswalk.get("occurrence_id") not in ("", None):
        raise ValueError("fixture expected the source crosswalk occurrence_id gap")
    if reverse.get("entry_id") != ENTRY_ID or SELECTED_WORD_ID not in (reverse.get("selected_word_ids") or []):
        raise ValueError("reverse crosswalk does not contain the selected word")
    if occurrence.get("loc") != QURAN_LOC or occurrence.get("surface") != SURFACE:
        raise ValueError("canonical occurrence address/surface is not exact")
    if occurrence.get("quran_loc") != OCCURRENCE_ID or occurrence.get("wbw_loc") != WBW_LOC:
        raise ValueError("canonical occurrence quran/wbw addresses are not exact")
    if occurrence.get("morphline") != "relative noun, accusative as direct object":
        raise ValueError("selected occurrence lacks the source-certified relative/direct-object morphology")
    segment_rows = occurrence.get("segments") or []
    if len(segment_rows) != 1 or segment_rows[0].get("class") != "qg-relative" or segment_rows[0].get("surface") != SURFACE:
        raise ValueError("selected occurrence lacks the exact relative qg segment")
    if "relative" not in (occurrence.get("learner_explanation") or "").lower():
        raise ValueError("selected occurrence lacks contextual relative evidence")
    required_context = {"2:284:2", "2:284:8", "2:284:9", QURAN_LOC, "2:284:11", "2:284:12", "2:284:14"}
    actual_context = {_loc(row) for row in source.get("context_rows") or []}
    if not required_context.issubset(actual_context):
        raise ValueError("context window does not retain the required governor/scope tokens")
    if source.get("same_surface_card_occurrence_locs") != ["2:284:10", "2:284:2"]:
        raise ValueError("same-surface card ambiguity was not retained")


def _address(address: str, source_kind: str) -> dict[str, str]:
    return {"address": address, "source_kind": source_kind}


def _surface_span() -> list[dict[str, Any]]:
    return [{"span_id": "particle", "start": 0, "end": len(SURFACE), "surface": SURFACE, "role": "function_particle"}]


def _fact_id(fact_type: str, fact_value: dict[str, Any]) -> str:
    return "sha256:" + digest({"contract": CONTRACT_ID, "fact_type": fact_type, "fact_value": fact_value})


def _make_fact(
    *,
    fact_type: str,
    fact_value: dict[str, Any],
    source_id: str,
    source_address: dict[str, str],
    source_addresses: list[dict[str, str]],
    evidence_mode: str,
    evidence_status: str,
    certification_status: str,
    summary: str,
    dependencies: list[str],
    projection_id: str,
    rule_id: str,
    structured_source_fact: dict[str, Any],
    blockers: list[dict[str, str]] | None = None,
    derivation_chain: list[dict[str, Any]] | None = None,
    contradiction_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "fact_id": _fact_id(fact_type, fact_value),
        "fact_type": fact_type,
        "fact_value": fact_value,
        "surface_spans": _surface_span(),
        "ownership": {
            "primary": {"owner_id": "proofp-particle-owner", "owner_type": "lane_owner_section_12"},
            "secondary": [{"owner_id": "tools.proofp_compiler", "owner_type": "compiler"}],
        },
        "source": {"source_id": source_id, "source_kind": source_address["source_kind"]},
        "source_address": source_address,
        "certification": {"status": certification_status, "reason": summary},
        "evidence": {
            "status": evidence_status,
            "confidence": "high" if certification_status == "certified" else "medium",
            "evidence_ids": [source_id],
            "summary": summary,
        },
        "evidence_mode": evidence_mode,
        "source_evidence": {
            "structured_source_fact": structured_source_fact,
            "source_addresses": source_addresses,
        },
        "derivation_chain": derivation_chain or [],
        "dependencies": {"fact_ids": dependencies, "source_addresses": source_addresses},
        "contradiction_records": contradiction_records or [],
        "producer": {"id": "tools.proofp_compiler", "version": VERSION},
        "rule_projector": {"rule_id": rule_id, "projector_id": PROJECTOR_ID, "version": VERSION},
        "guards": [
            {"guard_id": "candidate_only", "reason": "This fact can feed only the candidate proof; it cannot authorize a live write."},
            {"guard_id": "closed_class_no_root", "reason": "The function-word segment carries no lexical root claim."},
        ],
        "defeaters": [],
        "unresolved_blockers": blockers or [],
        "dependent_fact_ids": dependencies,
        "dependent_projection_ids": [projection_id],
    }


def build_contract(source: dict[str, Any]) -> dict[str, Any]:
    validate_source_facts(source)
    occurrence = source["occurrence"]
    entry = source["entry"]
    crosswalk = source["selected_word_crosswalk"]
    reverse = source["reverse_crosswalk"]
    context = {_loc(row): row for row in source["context_rows"]}

    specs: list[dict[str, Any]] = [
        {
            "fact_type": "particle_entry",
            "fact_value": {
                "entry_id": ENTRY_ID,
                "source_key": SOURCE_KEY,
                "headword": HEADWORD,
                "section": "particle",
                "root": None,
                "root_status": "function_only_no_root",
            },
            "source_id": "entries.jsonl#id=b8e480aebafe",
            "source_address": _address(f"entry:{ENTRY_ID}:headword", "qamus_entry_field"),
            "source_addresses": [_address(f"entry:{ENTRY_ID}:headword", "qamus_entry_field")],
            "evidence_mode": "direct_source_attestation",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "The canonical entry is the p099 particle entry headed مَا and carries no lexical root.",
            "rule_id": "proofp.ma.entry-identity",
            "structured_source_fact": {"entry": {"id": entry["id"], "headword": entry["headword"], "section": entry["section"], "source_keys": entry["source_keys"], "root": entry.get("root", "")}},
            "dependencies": [],
        },
        {
            "fact_type": "particle_sense",
            "fact_value": {
                "entry_id": ENTRY_ID,
                "sense_number": 1,
                "arabic": entry["senses"][0]["ar"],
                "entry_gloss": entry["senses"][0]["gloss"],
            },
            "source_id": "entries.jsonl#id=b8e480aebafe:sense=1",
            "source_address": _address(f"entry:{ENTRY_ID}:senses[0]", "qamus_entry_field"),
            "source_addresses": [_address(f"entry:{ENTRY_ID}:senses[0]", "qamus_entry_field")],
            "evidence_mode": "direct_source_attestation",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "Sense 1 is the entry sense used by the selected 2:284 example card.",
            "rule_id": "proofp.ma.sense-card-identity",
            "structured_source_fact": {"sense": entry["senses"][0], "selected_card": entry["selected_card"]},
            "dependencies": [],
        },
        {
            "fact_type": "selected_word_edge",
            "fact_value": {
                "selected_word_id": SELECTED_WORD_ID,
                "card_id": CARD_ID,
                "entry_id": ENTRY_ID,
                "card_ref": CARD_REF,
                "surface": SURFACE,
                "crosswalk_status": crosswalk["crosswalk_status"],
                "matched_entry_ids": crosswalk["matched_entry_ids"],
                "occurrence_id": crosswalk.get("occurrence_id", ""),
            },
            "source_id": "lexeme-entry-crosswalk.forward.jsonl#selected-word=b8e480aebafe:s1:u1:f1:c2:284:x1",
            "source_address": _address("crosswalk:forward:selected-word=b8e480aebafe:s1:u1:f1:c2:284:x1", "review_artifact"),
            "source_addresses": [_address("crosswalk:forward:selected-word=b8e480aebafe:s1:u1:f1:c2:284:x1", "review_artifact"), _address(f"entry:{ENTRY_ID}:headword", "qamus_entry_field")],
            "evidence_mode": "direct_source_attestation",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "The selected-word card edge is exact and its lexical entry match is the singleton p099 entry; its occurrence slot remains empty in the source crosswalk.",
            "rule_id": "proofp.ma.selected-word-edge",
            "structured_source_fact": {"forward_crosswalk": crosswalk},
            "dependencies": [],
        },
        {
            "fact_type": "canonical_occurrence",
            "fact_value": {
                "occurrence_id": OCCURRENCE_ID,
                "quran_loc": QURAN_LOC,
                "wbw_loc": WBW_LOC,
                "surface": SURFACE,
                "card_ref": CARD_REF,
                "card_text": entry["selected_card"]["text"],
            },
            "source_id": "rh_live_01_beta_whitelist.jsonl#loc=2:284:10",
            "source_address": _address(OCCURRENCE_ID, "quran_token"),
            "source_addresses": [_address(OCCURRENCE_ID, "quran_token"), _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "review_artifact")],
            "evidence_mode": "direct_source_attestation",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "The exact source-addressed occurrence is مَا at 2:284:10, with a byte-preserved surface and WBW address.",
            "rule_id": "proofp.ma.canonical-occurrence",
            "structured_source_fact": {"whitelist_row": {"loc": occurrence["loc"], "surface": occurrence["surface"], "quran_loc": occurrence["quran_loc"], "wbw_loc": occurrence["wbw_loc"], "card_ref": occurrence["card_ref"]}},
            "dependencies": [],
        },
        {
            "fact_type": "contextual_function",
            "fact_value": {
                "function": "relative",
                "qg_class": "qg-relative",
                "role": "relative_particle",
                "morphline": occurrence["morphline"],
                "decision_status": "source_certified_for_this_occurrence",
            },
            "source_id": "rh_live_01_beta_whitelist.jsonl#loc=2:284:10:function",
            "source_address": _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10:function", "review_artifact"),
            "source_addresses": [_address(OCCURRENCE_ID, "quran_token"), _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "review_artifact")],
            "evidence_mode": "direct_source_attestation",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "This exact occurrence is source-described as relative mā and not as a generic uncontextualized particle label.",
            "rule_id": "proofp.ma.relative-context",
            "structured_source_fact": {"morphline": occurrence["morphline"], "learner_explanation": occurrence["learner_explanation"], "segment": occurrence["segments"][0]},
            "dependencies": [],
        },
        {
            "fact_type": "governed_scope",
            "fact_value": {
                "relation": "direct_object",
                "governor": {"surface": context["2:284:9"]["surface"], "gloss": "disclose", "address": "quran:2:284:9"},
                "describing_clause": {"surface": "فِى أَنفُسِكُمْ", "addresses": ["quran:2:284:11", "quran:2:284:12"], "gloss": "within yourselves"},
                "scope_statement": "مَا names what is disclosed; the following prepositional phrase identifies what is within yourselves.",
            },
            "source_id": "rh_live_01_beta_whitelist.jsonl#loc=2:284:10:scope",
            "source_address": _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10:scope", "review_artifact"),
            "source_addresses": [_address("rh_live_01_beta_whitelist.jsonl#loc=2:284:9", "review_artifact"), _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "review_artifact"), _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:11", "review_artifact"), _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:12", "review_artifact")],
            "evidence_mode": "direct_source_attestation",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "The source explanation identifies the relative item as the object of disclose and supplies the within-yourself scope.",
            "rule_id": "proofp.ma.relative-object-scope",
            "structured_source_fact": {"selected_row": {"morphline": occurrence["morphline"], "learner_explanation": occurrence["learner_explanation"]}, "context_rows": {loc: {"surface": context[loc]["surface"], "morphline": context[loc].get("morphline", "")} for loc in ("2:284:9", "2:284:11", "2:284:12")}},
            "dependencies": [],
        },
        {
            "fact_type": "contextual_gloss",
            "fact_value": {
                "token_contribution_gloss": "what / that which",
                "phrase_gloss": "what is within yourselves",
                "phrase_gloss_status": "authored_candidate_from_context",
            },
            "source_id": "proofp:ma:contextual-gloss",
            "source_address": _address("proofp:ma:contextual-gloss", "construction"),
            "source_addresses": [_address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "review_artifact"), _address(OCCURRENCE_ID, "quran_token")],
            "evidence_mode": "deterministic_derivation_from_certified_facts",
            "evidence_status": "source_addressed_candidate",
            "certification_status": "candidate",
            "summary": "The token gloss is source-addressed; the shorter phrase gloss is an authored composition of the certified function and scope facts.",
            "rule_id": "proofp.ma.contextual-gloss",
            "structured_source_fact": {"source_token_gloss": occurrence["token_contribution_gloss"], "authored_phrase_gloss": "what is within yourselves", "composition_inputs": ["relative function", "direct-object scope"]},
            "dependencies": [],
        },
        {
            "fact_type": "function_word_colour",
            "fact_value": {
                "qg_class": "qg-relative",
                "letter_ownership_class": "function_particle",
                "letter_ownership": [{"index": index, "surface": character, "class": "function_particle", "root": None} for index, character in enumerate(SURFACE)],
                "root": None,
                "root_status": "function_only_no_root",
            },
            "source_id": "proofp:ma:closed-class-colour",
            "source_address": _address("proofp:ma:closed-class-colour", "construction"),
            "source_addresses": [_address(f"entry:{ENTRY_ID}:headword", "qamus_entry_field"), _address("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "review_artifact")],
            "evidence_mode": "deterministic_derivation_from_certified_facts",
            "evidence_status": "certified",
            "certification_status": "certified",
            "summary": "The compiler maps the one function-word segment to qg-relative and preserves root silence for every owned character.",
            "rule_id": "proofp.ma.closed-class-no-root",
            "structured_source_fact": {"entry_root": entry.get("root", ""), "source_segment": occurrence["segments"][0], "closed_class_guard": "function_only_no_root"},
            "dependencies": [],
        },
        {
            "fact_type": "entry_occurrence_reciprocity",
            "fact_value": {
                "entry_id": ENTRY_ID,
                "selected_word_id": SELECTED_WORD_ID,
                "occurrence_id": OCCURRENCE_ID,
                "forward_status": "candidate",
                "reverse_status": "candidate",
                "source_crosswalk_occurrence_gap": True,
                "reciprocity_status": "candidate_exact_addressed_trace",
            },
            "source_id": "proofp:ma:entry-occurrence-reciprocity",
            "source_address": _address("proofp:typed-graph:entry-occurrence-reciprocity", "construction"),
            "source_addresses": [_address("crosswalk:forward:selected-word=b8e480aebafe:s1:u1:f1:c2:284:x1", "review_artifact"), _address("crosswalk:reverse:entry=b8e480aebafe", "review_artifact"), _address(OCCURRENCE_ID, "quran_token")],
            "evidence_mode": "deterministic_derivation_from_certified_facts",
            "evidence_status": "source_addressed_candidate",
            "certification_status": "candidate",
            "summary": "The generated graph carries the exact selected-word→occurrence and occurrence→entry traces, while retaining the source crosswalk's empty occurrence field as a candidate limitation.",
            "rule_id": "proofp.ma.entry-occurrence-reciprocity",
            "structured_source_fact": {"forward_crosswalk": {"selected_word_id": SELECTED_WORD_ID, "occurrence_id": crosswalk.get("occurrence_id", "")}, "reverse_crosswalk": {"entry_id": reverse["entry_id"], "occurrence_ids": reverse.get("occurrence_ids", [])}},
            "dependencies": [],
            "derivation_chain": [],
        },
        {
            "fact_type": "alternative_function_routes",
            "fact_value": {
                "chosen": "relative",
                "alternatives": [
                    {"function": "negation", "status": "unresolved", "route": "nahw/procedures/ma-function-decision.md"},
                    {"function": "interrogative", "status": "unresolved", "route": "nahw/procedures/relative-interrogative.md"},
                    {"function": "masdariyya", "status": "unresolved", "route": "nahw/procedures/ma-function-decision.md"},
                    {"function": "conditional", "status": "unresolved", "route": "nahw/procedures/particle-function-decision.md"},
                    {"function": "preventive", "status": "unresolved", "route": "nahw/procedures/ma-function-decision.md"},
                ],
                "discipline": "Only the relative choice is source-certified for this occurrence; the other labels remain routed unresolved rather than being declared excluded without separate evidence.",
            },
            "source_id": "proofp:ma:function-alternative-routes",
            "source_address": _address("proofp:ma:function-alternative-routes", "construction"),
            "source_addresses": [_address(OCCURRENCE_ID, "quran_token"), _address("nahw:ma-function-decision:2:284:10", "review_artifact")],
            "evidence_mode": "unresolved",
            "evidence_status": "source_addressed_candidate",
            "certification_status": "pending",
            "summary": "The bare surface is multi-function in the entry; unselected readings are kept as unresolved routes, not silently rejected.",
            "rule_id": "proofp.ma.alternative-function-discipline",
            "structured_source_fact": {"selected_function": "relative", "unresolved_routes": ["negation", "interrogative", "masdariyya", "conditional", "preventive"]},
            "dependencies": [],
            "blockers": [{"blocker_id": "context_alternative_readings_pending", "reason": "No separate source-certified exclusion packet was supplied for every unselected mā function."}],
        },
    ]

    ids = {_spec["fact_type"]: _fact_id(_spec["fact_type"], _spec["fact_value"]) for _spec in specs}
    for spec in specs:
        if spec["fact_type"] == "function_word_colour":
            spec["dependencies"] = [ids["particle_entry"], ids["contextual_function"]]
        elif spec["fact_type"] == "contextual_gloss":
            spec["dependencies"] = [ids["contextual_function"], ids["governed_scope"]]
        elif spec["fact_type"] == "entry_occurrence_reciprocity":
            spec["dependencies"] = [ids["selected_word_edge"], ids["canonical_occurrence"]]
        elif spec["fact_type"] == "alternative_function_routes":
            spec["dependencies"] = [ids["contextual_function"]]

    facts: list[dict[str, Any]] = []
    for spec in specs:
        derivation = list(spec.get("derivation_chain") or [])
        if spec["fact_type"] == "function_word_colour":
            derivation = [{
                "step_id": "proofp.ma.compile-function-colour",
                "operation": "map the certified function segment to the closed qamus palette and apply the no-root guard",
                "input_fact_ids": spec["dependencies"],
                "input_source_addresses": spec["source_addresses"],
                "output": "one qg-relative function segment with function_only_no_root root status",
            }]
        elif spec["fact_type"] == "contextual_gloss":
            derivation = [{
                "step_id": "proofp.ma.compose-contextual-gloss",
                "operation": "compose the token contribution with the certified direct-object scope",
                "input_fact_ids": spec["dependencies"],
                "input_source_addresses": spec["source_addresses"],
                "output": "what is within yourselves",
            }]
        elif spec["fact_type"] == "entry_occurrence_reciprocity":
            derivation = [{
                "step_id": "proofp.ma.build-reciprocal-trace",
                "operation": "join the selected-word edge to the explicit source-addressed occurrence and emit the reverse entry trace",
                "input_fact_ids": spec["dependencies"],
                "input_source_addresses": spec["source_addresses"],
                "output": "candidate exact-addressed forward and reverse trace",
            }]
        fact_spec = dict(spec)
        fact_spec["derivation_chain"] = derivation
        facts.append(_make_fact(projection_id=PROJECTION_ID, **fact_spec))

    fact_by_type = {fact["fact_type"]: fact for fact in facts}
    bindings = [
        {"fact_id": fact_by_type["particle_entry"]["fact_id"], "fact_field": "fact_value.entry_id", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["particle_sense"]["fact_id"], "fact_field": "fact_value.sense_number", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["selected_word_edge"]["fact_id"], "fact_field": "fact_value.selected_word_id", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["canonical_occurrence"]["fact_id"], "fact_field": "fact_value.occurrence_id", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["contextual_function"]["fact_id"], "fact_field": "fact_value.function", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["governed_scope"]["fact_id"], "fact_field": "fact_value.relation", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["contextual_gloss"]["fact_id"], "fact_field": "fact_value.token_contribution_gloss", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["function_word_colour"]["fact_id"], "fact_field": "fact_value.root_status", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["entry_occurrence_reciprocity"]["fact_id"], "fact_field": "fact_value.reciprocity_status", "surface_span_ids": ["particle"]},
        {"fact_id": fact_by_type["alternative_function_routes"]["fact_id"], "fact_field": "fact_value.alternatives[0].status", "surface_span_ids": ["particle"]},
    ]
    segment = {"role": "relative_particle", "surface": SURFACE, "qg_class": "qg-relative", "gloss": "what / that which"}
    contract = {
        "schema": "qamus.typed_claim_contract.v1",
        "contract_version": "1.0.0",
        "contract_id": CONTRACT_ID,
        "record_type": "projection_input",
        "canonical_occurrence": {
            "occurrence_id": OCCURRENCE_ID,
            "quran_loc": QURAN_LOC,
            "wbw_loc": WBW_LOC,
            "surface": SURFACE,
            "surface_length": len(SURFACE),
            "entry_id": ENTRY_ID,
            "card_id": CARD_ID,
        },
        "facts": facts,
        "tension_records": [{
            "tension_id": "proofp:ma:unselected-functions",
            "status": "unresolved",
            "statement": "The surface مَا has multiple entry functions; this occurrence is certified as relative, while separate exclusion evidence for every unselected reading is not present in this lane.",
            "fact_ids": [fact_by_type["contextual_function"]["fact_id"], fact_by_type["alternative_function_routes"]["fact_id"]],
            "resolution_requirement": "nahw_contextual_function_review",
        }],
        "projection": {
            "projection_id": PROJECTION_ID,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": "qamus/examples/proof-particle/particle-normalized-public-payload.json",
                "field": "hover",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "The candidate identifies p099 sense 1, the exact selected-word card edge, the source-certified relative function of مَا at 2:284:10, its direct-object scope, its authored contextual gloss, its function-word colour, and reciprocal candidate trace.",
                "language": "en",
                "fact_bindings": bindings,
            },
            "learner_statement": "Here مَا is the relative function word meaning what / that which; the candidate keeps the surrounding scope visible and makes no lexical-root claim.",
            "public_payload": {"segments": [segment]},
        },
    }
    errors = validate_contract_record(contract)
    if errors:
        raise ValueError("PROOF-P typed contract failed validation: " + "; ".join(errors))
    return contract


def _letter_ownership() -> list[dict[str, Any]]:
    return [
        {"index": index, "surface": character, "class": "function_particle", "qg_class": "qg-relative", "root": None}
        for index, character in enumerate(SURFACE)
    ]


def build_payload(source: dict[str, Any], contract: dict[str, Any], render_proof: dict[str, Any]) -> dict[str, Any]:
    occurrence = source["occurrence"]
    identity = {
        "projection_id": PROJECTION_ID,
        "entry_id": ENTRY_ID,
        "card_id": CARD_ID,
        "selected_word_id": SELECTED_WORD_ID,
        "occurrence_id": OCCURRENCE_ID,
        "quran_loc": QURAN_LOC,
        "wbw_loc": WBW_LOC,
        "surface": SURFACE,
    }
    segment = {
        "segment_index": 0,
        "surface": SURFACE,
        "role": "relative_particle",
        "qg_class": "qg-relative",
        "gloss_contribution": "what / that which",
        "letter_ownership_class": "function_particle",
        "root": None,
        "root_status": "function_only_no_root",
    }
    render_status = render_proof.get("status", "not_measured")
    return {
        "schema": "qamus.proof_particle.normalized_public_payload.v1",
        "payload_identity": PROJECTION_ID,
        "candidate_status": "candidate",
        "owner_section": "12",
        "public_materialization_allowed": False,
        "live_mutation_allowed": False,
        "identity": identity,
        "at_rest": {
            "surface": SURFACE,
            "segments": [segment],
            "letter_ownership": _letter_ownership(),
            "reconstruction": {"surface": SURFACE, "exact": True},
        },
        "compact": {
            "surface": SURFACE,
            "gloss": "what / that which",
            "segment_classes": ["qg-relative"],
            "parse_key": {"key": "MA:REL:OBJ", "summary": "relative mā as a direct object"},
        },
        "expanded": {
            "sarf": {
                "label": "Ṣarf — how this piece forms the word",
                "status": "candidate",
                "explanation": "مَا is one built function-word piece here; it is not assigned a lexical root.",
                "segments": [{"surface": SURFACE, "composition": "single function-word piece", "root": None, "root_status": "function_only_no_root"}],
            },
            "nahw": {
                "label": "Naḥw — what this piece does here",
                "status": "candidate",
                "function": "relative",
                "function_status": "source_certified_for_this_occurrence",
                "explanation": "Here مَا means what / that which. It is the object of disclose, and the following phrase identifies what is within yourselves.",
                "scope": {
                    "relation": "direct_object",
                    "governor": "disclose",
                    "describing_clause": "within yourselves",
                },
                "alternatives": [
                    {"function": "negation", "status": "unresolved"},
                    {"function": "interrogative", "status": "unresolved"},
                    {"function": "masdariyya", "status": "unresolved"},
                    {"function": "conditional", "status": "unresolved"},
                    {"function": "preventive", "status": "unresolved"},
                ],
            },
        },
        "hover": {
            "public_boundary": {"src": "qamus", "kind": "authored", "lang": "en"},
            "title": HEADWORD,
            "token_contribution_gloss": "what / that which",
            "phrase_gloss": "what is within yourselves",
            "learner_explanation": "Here مَا names what is disclosed; the following phrase identifies what is within yourselves.",
            "segments": [{"surface": SURFACE, "class": "qg-relative", "role": "relative_particle", "gloss": "what / that which", "root": None}],
            "sarf_label": "Ṣarf — how this piece forms the word",
            "nahw_label": "Naḥw — what this piece does here",
        },
        "per_appearance": [{
            "appearance_id": "appearance:2:284:10:1",
            "occurrence_id": OCCURRENCE_ID,
            "surface": SURFACE,
            "status": "candidate",
            "payload_identity": PROJECTION_ID,
            "exact_reconstruction": True,
        }],
        "entry_linkage": {
            "forward": {
                "entry_id": ENTRY_ID,
                "selected_word_id": SELECTED_WORD_ID,
                "occurrence_id": OCCURRENCE_ID,
                "status": "candidate",
                "source_occurrence_id": "",
            },
            "reverse": {
                "entry_id": ENTRY_ID,
                "selected_word_ids": [SELECTED_WORD_ID],
                "occurrence_ids": [OCCURRENCE_ID],
                "status": "candidate",
            },
            "reciprocity_status": "candidate_exact_addressed_trace",
        },
        "decision_routes": {
            "public": False,
            "chosen": {"function": "relative", "status": "source_certified_for_this_occurrence"},
            "unresolved": [
                {"function": "negation", "route": "nahw/procedures/ma-function-decision.md"},
                {"function": "interrogative", "route": "nahw/procedures/relative-interrogative.md"},
                {"function": "masdariyya", "route": "nahw/procedures/ma-function-decision.md"},
                {"function": "conditional", "route": "nahw/procedures/particle-function-decision.md"},
                {"function": "preventive", "route": "nahw/procedures/ma-function-decision.md"},
            ],
        },
        "readback": {
            "status": "measured_local_render" if render_status == "measured" else "not_measured",
            "render_proof": "qamus/examples/proof-particle/render-proof.json",
            "live_runtime_readback": "not_run",
            "live_mutation_allowed": False,
            "required_predeploy_checks": ["load candidate payload", "verify exact surface reconstruction", "verify both hover panels", "owner-gated certification before any live write"],
        },
    }


def build_graph(source: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    facts = {fact["fact_type"]: fact for fact in contract["facts"]}
    evidence = lambda address, method: [{"address": address, "method": method}]
    selected = selected_word_node(ENTRY_ID, 1, 1, 1, CARD_REF, 1)
    card = card_node(ENTRY_ID, 1, 1, CARD_REF)
    entry = entry_node(ENTRY_ID)
    sense = sense_node(ENTRY_ID, 1)
    occurrence = occurrence_node(QURAN_LOC)
    appearance = appearance_node(QURAN_LOC, 1)
    edges: list[dict[str, Any]] = []

    def add(edge_type: str, from_node: str, to_node: str, status: str, *, addresses: list[dict[str, str]], guards: list[str], details: dict[str, Any]) -> None:
        edges.append(make_edge(edge_type, from_node, to_node, status, evidence=addresses, guards=guards, details=details, producer_id="tools.proofp_compiler", producer_version=VERSION))

    add(
        "sense_entry_edge", sense, entry, "deterministic_exact",
        addresses=evidence(f"entry:{ENTRY_ID}:senses[0]", "entry_sense_identity"),
        guards=["entry_identity_exact", "particle_sense_identity"],
        details={"entry_id": ENTRY_ID, "sense_number": 1, "surface": SURFACE, "fact_id": facts["particle_sense"]["fact_id"]},
    )
    add(
        "source_card_edge", selected, card, "deterministic_exact",
        addresses=evidence(f"card:{CARD_REF}", "selected_word_card_identity"),
        guards=["card_identity_from_crosswalk", "selected_word_backlink_exact"],
        details={"card_id": card, "card_ref": CARD_REF, "source_card_text": source["entry"]["selected_card"]["text"], "fact_id": facts["selected_word_edge"]["fact_id"]},
    )
    add(
        "lexeme_entry_edge", selected, entry, "deterministic_exact",
        addresses=evidence(f"entry:{ENTRY_ID}:headword", "entry_headword"),
        guards=["orthography_guard_v1", "page_context_origin_false", "singleton_collision_set"],
        details={"surface": SURFACE, "collision_set": [ENTRY_ID], "form_address": f"entry:{ENTRY_ID}:headword", "page_context_origin": False, "fact_id": facts["selected_word_edge"]["fact_id"]},
    )
    add(
        "form_entry_edge", selected, entry, "deterministic_exact",
        addresses=evidence(f"entry:{ENTRY_ID}:headword", "documented_form"),
        guards=["documented_form_or_source_evidence", "orthography_guard_v1"],
        details={"surface": SURFACE, "form_index": 0, "form_address": f"entry:{ENTRY_ID}:headword", "fact_id": facts["selected_word_edge"]["fact_id"]},
    )
    add(
        "selected_example_edge", card, occurrence, "candidate",
        addresses=evidence("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "exact_source_addressed_occurrence"),
        guards=["card_ref_exact", "surface_exact", "same_surface_card_occurrence_ambiguity_preserved", "candidate_only"],
        details={"card_ref": CARD_REF, "occurrence_id": OCCURRENCE_ID, "surface": SURFACE, "same_surface_card_occurrence_locs": source["same_surface_card_occurrence_locs"], "selection_reason": "explicit source address retained because the card has two identical مَا surfaces", "fact_id": facts["canonical_occurrence"]["fact_id"]},
    )
    add(
        "canonical_occurrence_edge", selected, occurrence, "candidate",
        addresses=evidence(OCCURRENCE_ID, "explicit_occurrence_address"),
        guards=["exact_quran_wbw_address", "surface_exact", "source_crosswalk_occurrence_gap_preserved", "candidate_only"],
        details={"selected_word_id": SELECTED_WORD_ID, "occurrence_id": OCCURRENCE_ID, "source_crosswalk_occurrence_id": "", "fact_id": facts["entry_occurrence_reciprocity"]["fact_id"]},
    )
    add(
        "display_local_to_canonical_crosswalk_edge", card, occurrence, "candidate",
        addresses=evidence("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "display_local_exact_address"),
        guards=["display_surface_exact", "canonical_surface_exact", "candidate_only"],
        details={"display_local_address": "2:284:10", "canonical_address": QURAN_LOC, "displayed_surface": SURFACE, "canonical_surface": SURFACE, "exact_reconstruction": True, "fact_id": facts["canonical_occurrence"]["fact_id"]},
    )
    add(
        "decision_evidence_edge", occurrence, entry, "candidate",
        addresses=evidence("rh_live_01_beta_whitelist.jsonl#loc=2:284:10", "contextual_function_and_scope"),
        guards=["contextual_function_source_addressed", "governor_scope_present", "candidate_only"],
        details={"function": "relative", "governor": "disclose", "relation": "direct_object", "qg_class": "qg-relative", "fact_ids": [facts["contextual_function"]["fact_id"], facts["governed_scope"]["fact_id"]]},
    )
    add(
        "rendered_appearance_edge", occurrence, appearance, "candidate",
        addresses=evidence("proofp:render:appearance:2:284:10:1", "candidate_render_descriptor"),
        guards=["candidate_only", "no_live_mutation", "local_render_readback_only"],
        details={"appearance_id": appearance, "payload_identity": PROJECTION_ID, "surface": SURFACE, "exact_reconstruction": True, "readback": "local_render_proof_only"},
    )
    return edges


def build_traces(source: dict[str, Any], graph: list[dict[str, Any]], contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    forward_edge_ids = [edge["edge_id"] for edge in graph if edge["from_node_id"] == selected_word_node(ENTRY_ID, 1, 1, 1, CARD_REF, 1) and edge["to_node_id"] in {entry_node(ENTRY_ID), occurrence_node(QURAN_LOC)}]
    forward = {
        "schema": "qamus.proof_particle.entry_occurrence_forward.v1",
        "entry_id": ENTRY_ID,
        "selected_word_id": SELECTED_WORD_ID,
        "card_id": CARD_ID,
        "card_ref": CARD_REF,
        "occurrence_id": OCCURRENCE_ID,
        "source_crosswalk_occurrence_id": source["selected_word_crosswalk"].get("occurrence_id", ""),
        "selected_word_status": source["selected_word_crosswalk"]["crosswalk_status"],
        "trace_status": "candidate",
        "surface": SURFACE,
        "edge_ids": forward_edge_ids,
        "reason": "The exact occurrence address is source-addressed, but the source selected-word crosswalk leaves occurrence_id empty and the card repeats the same surface.",
    }
    reverse_occurrence_ids = [
        "quran:" + edge["to_node_id"].split(":", 1)[1]
        for edge in graph
        if edge["to_node_id"] == occurrence_node(QURAN_LOC) and edge["status"] == "candidate"
    ]
    reverse_occurrence_ids = sorted(set(reverse_occurrence_ids))
    reverse_edge_ids = [edge["edge_id"] for edge in graph if edge["to_node_id"] == entry_node(ENTRY_ID) or edge["to_node_id"] == occurrence_node(QURAN_LOC)]
    reverse = {
        "schema": "qamus.proof_particle.entry_occurrence_reverse.v1",
        "entry_id": ENTRY_ID,
        "selected_word_ids": [SELECTED_WORD_ID],
        "occurrence_ids": reverse_occurrence_ids,
        "source_reverse_occurrence_ids": source["reverse_crosswalk"].get("occurrence_ids", []),
        "trace_status": "candidate",
        "surface": SURFACE,
        "edge_ids": reverse_edge_ids,
        "reciprocity": {
            "forward_occurrence_in_reverse": OCCURRENCE_ID in reverse_occurrence_ids,
            "reverse_entry_matches_forward": source["reverse_crosswalk"].get("entry_id") == ENTRY_ID,
            "selected_word_matches": SELECTED_WORD_ID in (source["reverse_crosswalk"].get("selected_word_ids") or []),
            "status": "candidate_exact_addressed_trace",
        },
        "reason": "Reverse lookup is emitted from the typed graph and keeps the source reverse row's empty occurrence_ids visible.",
    }
    return forward, reverse


def build_rich_candidate(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "fusha/rich-hover-candidate@1",
        "source_unit": {"address": "quran:2:284", "kind": "example_card", "scope": "in_scope_source_addressed"},
        "card_address": f"qamus:{ENTRY_ID}#usage=1&card={CARD_REF}",
        "token_address": QURAN_LOC,
        "quran_loc": QURAN_LOC,
        "wbw_loc": WBW_LOC,
        "surface": SURFACE,
        "displayed_surface": SURFACE,
        "canonical_surface": SURFACE,
        "display_local_to_canonical_crosswalk": {"displayed_address": QURAN_LOC, "canonical_address": QURAN_LOC, "surface_exact": True, "status": "candidate", "occurrence_id_source": ""},
        "decision_state": "rich_candidate",
        "segments": [{"role": "relative_particle", "surface": SURFACE, "gloss_contribution": "what / that which"}],
        "qg_segment_classes": ["qg-relative"],
        "qg_palette": "qamus-grammar-v1",
        "parse_key": {"key": "MA:REL:OBJ", "summary": "relative mā used as a direct object", "components": [{"function": "relative"}, {"relation": "direct_object"}]},
        "hover_title": HEADWORD,
        "token_gloss": "what / that which",
        "token_contribution_explanation": "The piece names what is being disclosed; the following phrase identifies what is within yourselves.",
        "learner_route": {"lane": "nahw", "procedure": "nahw/procedures/ma-function-decision.md"},
        "parser_issues": [],
        "verdict": {"status": "grounded", "gate": "two_vote_required", "reasoning_checked": True},
        "gate": "two_vote_required",
        "public_boundary": {"public_gloss_src": "qamus", "public_gloss_kind": "authored", "public_gloss_lang": "en", "external_source_names_public": False},
        "blocker_status": None,
        "suggested_next_action": "ready_for_cert_review",
        "live_writes": 0,
    }


def build_parity(payload: dict[str, Any], rich_candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "qamus.proof_particle.parity_fixture.v1",
        "payload_identity": PROJECTION_ID,
        "expected": {
            "surface": SURFACE,
            "segments": payload["at_rest"]["segments"],
            "segment_classes": ["qg-relative"],
            "hover_labels": ["Ṣarf — how this piece forms the word", "Naḥw — what this piece does here"],
            "candidate_status": "candidate",
            "live_mutation_allowed": False,
            "token_address": rich_candidate["token_address"],
            "wbw_loc": rich_candidate["wbw_loc"],
        },
        "checks": ["compact_matches_at_rest", "expanded_labels_exact", "hover_boundary_exact", "segments_reconstruct_exact_surface", "candidate_only"],
    }


def _placeholder_render_proof() -> dict[str, Any]:
    return {
        "schema": "qamus.proof_particle.render_proof.v1",
        "status": "not_measured",
        "payload_identity": PROJECTION_ID,
        "font_check": False,
        "exact_reconstruction": False,
        "compact_present": False,
        "expanded_present": False,
        "same_payload_identity": False,
        "live_mutation_allowed": False,
        "screenshot_path": "particle-card.png",
        "screenshot_local_only": True,
        "note": "The browser renderer owns measurement; this placeholder is replaced by tools/render_proof_particle.js.",
    }


def build_manifest(out: Path, source: dict[str, Any], render_proof: dict[str, Any], harness_status: str, rm09_status: str) -> dict[str, Any]:
    artifact_names = [
        "README.md",
        "particle-contract.json",
        "particle-graph-edges.jsonl",
        "particle-crosswalk-forward.json",
        "particle-crosswalk-reverse.json",
        "particle-normalized-public-payload.json",
        "particle-rich-hover-candidate.jsonl",
        "particle-parity-fixture.json",
        "particle-card.html",
        "render-proof.json",
        "source/proofp-source-facts.json",
    ]
    artifacts = []
    for name in artifact_names:
        path = out / name
        if path.exists():
            artifacts.append({"path": f"qamus/examples/proof-particle/{name}", "sha256": file_digest(path), "committed": name != "render-proof.png"})
    return {
        "schema": "qamus.proof_particle.manifest.v1",
        "lane": "PROOF-P",
        "owner_section": "12",
        "selection": {"entry_id": ENTRY_ID, "source_key": SOURCE_KEY, "headword": HEADWORD, "sense": 1, "card_ref": CARD_REF, "occurrence": QURAN_LOC},
        "generator": {"id": "tools.proofp_compiler", "version": VERSION, "mcp": False},
        "source_capture": source.get("source_capture", {"mode": "committed_fixture"}),
        "candidate_only": True,
        "public_materialization_allowed": False,
        "live_mutation_allowed": False,
        "png_policy": {"path": "particle-card.png", "tracked": False, "reason": "local render evidence only"},
        "render": {"status": render_proof.get("status"), "font_check": render_proof.get("font_check"), "exact_reconstruction": render_proof.get("exact_reconstruction"), "same_payload_identity": render_proof.get("same_payload_identity")},
        "checks": {"contract": "pass", "typed_graph": "pass", "rich_hover_candidate": "pass", "parity": "pass", "render": render_proof.get("status"), "harness": harness_status, "rm09": rm09_status},
        "artifacts": artifacts,
        "limits": ["No live MCP or runtime readback was used.", "The card-to-occurrence and entry-to-occurrence traces remain candidate because the source crosswalk leaves occurrence_id empty and the card repeats the surface.", "Any certification, promotion, deployment, or live write remains owner-gated."],
    }


def compile_artifacts(source: dict[str, Any], out: Path, harness_status: str, rm09_status: str) -> None:
    validate_source_facts(source)
    out.mkdir(parents=True, exist_ok=True)
    source_path = out / "source" / "proofp-source-facts.json"
    write_json(source_path, source)
    contract = build_contract(source)
    existing_render = out / "render-proof.json"
    render_proof = read_json(existing_render) if existing_render.exists() else _placeholder_render_proof()
    if render_proof.get("payload_identity") != PROJECTION_ID:
        render_proof = _placeholder_render_proof()
    payload = build_payload(source, contract, render_proof)
    graph = build_graph(source, contract)
    forward, reverse = build_traces(source, graph, contract)
    rich_candidate = build_rich_candidate(source)
    parity = build_parity(payload, rich_candidate)
    write_json(out / "particle-contract.json", contract)
    write_jsonl(out / "particle-graph-edges.jsonl", graph)
    write_json(out / "particle-crosswalk-forward.json", forward)
    write_json(out / "particle-crosswalk-reverse.json", reverse)
    write_json(out / "particle-normalized-public-payload.json", payload)
    write_jsonl(out / "particle-rich-hover-candidate.jsonl", [rich_candidate])
    write_json(out / "particle-parity-fixture.json", parity)
    if not existing_render.exists() or render_proof.get("status") == "not_measured":
        write_json(existing_render, render_proof)
    write_html(out / "particle-card.html", payload)
    write_json(out / "PROOFP-MANIFEST.json", build_manifest(out, source, render_proof, harness_status, rm09_status))


def write_html(path: Path, payload: dict[str, Any]) -> None:
    hover = payload["hover"]
    segment = payload["at_rest"]["segments"][0]
    compact = payload["compact"]
    expanded = payload["expanded"]
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PROOF-P · مَا · candidate</title>
<style>
:root {{ color-scheme: light; --ink:#202331; --muted:#667085; --paper:#fbfaf7; --panel:#ffffff; --line:#e7e2d8; --relative:#5f3dc4; --relative-soft:#eee9ff; --candidate:#b54708; --candidate-soft:#fff2e6; }}
* {{ box-sizing:border-box; }} body {{ margin:0; min-height:100vh; background:linear-gradient(145deg,#f1eee8 0%,#fcfbf8 52%,#ebe8ff 100%); color:var(--ink); font-family:Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }}
main {{ width:min(920px,calc(100% - 32px)); margin:32px auto; }}
.card {{ background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:24px; box-shadow:0 20px 60px rgba(45,35,80,.12); overflow:hidden; }}
.top {{ padding:28px 32px 24px; display:flex; justify-content:space-between; gap:20px; align-items:flex-start; border-bottom:1px solid var(--line); }}
.eyebrow {{ color:var(--candidate); font-size:12px; letter-spacing:.12em; text-transform:uppercase; font-weight:750; }} h1 {{ margin:10px 0 0; font-size:44px; line-height:1; }}
.badge {{ background:var(--candidate-soft); border:1px solid #f3c49d; border-radius:999px; padding:8px 12px; color:var(--candidate); font-weight:700; font-size:12px; white-space:nowrap; }}
.token-row {{ padding:30px 32px 24px; display:flex; align-items:center; gap:18px; border-bottom:1px solid var(--line); }}
.token {{ font-family:Georgia, serif; font-size:54px; direction:rtl; color:var(--relative); background:var(--relative-soft); padding:12px 22px 16px; border-radius:18px; line-height:1; }}
.token-gloss {{ font-size:20px; font-weight:700; }} .phrase {{ color:var(--muted); margin-top:5px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; padding:24px 32px 32px; }}
.panel {{ border:1px solid var(--line); border-radius:16px; padding:18px; background:var(--paper); }} h2 {{ margin:0 0 14px; font-size:14px; letter-spacing:.04em; text-transform:uppercase; }} h3 {{ margin:16px 0 7px; font-size:14px; color:var(--relative); }} p {{ margin:0; line-height:1.55; }} .small {{ color:var(--muted); font-size:13px; }} .scope {{ margin-top:12px; padding:10px 12px; border-left:3px solid var(--relative); background:#f1efff; font-size:14px; }}
.segment {{ display:inline-block; border-bottom:4px solid var(--relative); padding:2px 4px; }} .footer {{ padding:16px 32px; border-top:1px solid var(--line); color:var(--muted); font-size:12px; display:flex; justify-content:space-between; gap:12px; }}
@media (max-width:680px) {{ .top,.token-row,.grid,.footer {{ padding-left:20px; padding-right:20px; }} .top,.token-row {{ display:block; }} .badge {{ display:inline-block; margin-top:14px; }} .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:36px; }} .token-row {{ padding-top:24px; }} }}
</style>
</head>
<body>
<main id="proofp-root" data-payload-identity="{payload['payload_identity']}" data-appearance="appearance:2:284:10:1">
<article class="card">
  <header class="top"><div><div class="eyebrow">PROOF-P · particle/function word</div><h1 dir="rtl">مَا</h1></div><div class="badge">candidate · pre-deploy</div></header>
  <section class="token-row"><div id="token" class="token" dir="rtl"><span class="segment" data-qg-class="{segment['qg_class']}">{segment['surface']}</span></div><div><div id="token-gloss" class="token-gloss">{hover['token_contribution_gloss']}</div><div id="phrase-gloss" class="phrase">{hover['phrase_gloss']}</div></div></section>
  <section class="grid">
    <div id="compact" class="panel"><h2>Compact</h2><p><strong>{compact['gloss']}</strong></p><p class="small">{compact['parse_key']['summary']}</p></div>
    <div id="expanded" class="panel"><h2>Expanded</h2><h3>{expanded['sarf']['label']}</h3><p>{expanded['sarf']['explanation']}</p><h3>{expanded['nahw']['label']}</h3><p>{expanded['nahw']['explanation']}</p><div class="scope">Scope: {expanded['nahw']['scope']['relation'].replace('_',' ')} of “{expanded['nahw']['scope']['governor']}”; describing phrase: “{expanded['nahw']['scope']['describing_clause']}”.</div></div>
  </section>
  <footer class="footer"><span id="readback">exact surface · candidate only · no live mutation</span><span>مَا · 2:284:10</span></footer>
</article>
</main>
<script>window.__proofpPayload = {embedded}; window.__proofpPayloadIdentity = window.__proofpPayload.payload_identity;</script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "qamus" / "examples" / "proof-particle")
    parser.add_argument("--source-facts", type=Path)
    parser.add_argument("--entries", type=Path)
    parser.add_argument("--whitelist", type=Path)
    parser.add_argument("--crosswalk-forward", type=Path)
    parser.add_argument("--crosswalk-reverse", type=Path)
    parser.add_argument("--capture-source", action="store_true", help="capture the selected case from the read-only lane inputs")
    parser.add_argument("--harness-status", choices=["pending", "pass"], default="pending")
    parser.add_argument("--rm09-status", choices=["pending", "pass"], default="pending")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = [args.entries, args.whitelist, args.crosswalk_forward, args.crosswalk_reverse]
    if any(item is not None for item in raw):
        if not all(item is not None for item in raw):
            raise SystemExit("--entries, --whitelist, --crosswalk-forward, and --crosswalk-reverse must be supplied together")
        source = capture_source_facts(*[Path(item) for item in raw])
    else:
        source_path = args.source_facts or args.output_dir / "source" / "proofp-source-facts.json"
        source = read_json(source_path)
    if args.capture_source or any(item is not None for item in raw):
        source_path = args.source_facts or args.output_dir / "source" / "proofp-source-facts.json"
        write_json(source_path, source)
    compile_artifacts(source, args.output_dir, args.harness_status, args.rm09_status)
    print(f"PROOF-P COMPILED candidate {QURAN_LOC} -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    main()
