#!/usr/bin/env python3
"""Compile the real PROOF-N noun chain for السُّفَهَاءُ.

This is a candidate-only fixture compiler.  It reads explicitly supplied
source artifacts, calls the shared F-D compiler and FAM2 producer, and writes
deploy-shaped proof artifacts without mutating a source or live surface.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable, Mapping

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam2_lexical_producer
from tools import fd_compiler
from tools.build_typed_edge_crosswalk import SCHEMA as GRAPH_SCHEMA


ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = ROOT / "qamus" / "examples" / "proof-noun-sufaha"
SUFAHA_LOC = "2:13:12"
SUFAHA_SURFACE = "السُّفَهَاءُ"
SUFAHA_BODY = "سُفَهَاء"
LEXICAL_ENTRY_ID = "1ffcc554ec44"
PAGE_CONTEXT_ENTRY_ID = "c59a0161fac8"
SENSE_NODE_ID = f"sense:{LEXICAL_ENTRY_ID}:s1"
SELECTED_WORD_NODE_ID = "selected-word:repair:sufaha:2:13:12"
CARD_NODE_ID = "card:repair:sufaha:2:13:12"
OCCURRENCE_NODE_ID = f"occurrence:{SUFAHA_LOC}"
PROOF_PRODUCER_ID = "tools.proofn_noun_sufaha"
PROOF_PRODUCER_VERSION = "1.0.0"
AUTHORIZATION_STATE = "pre_apply_not_authorized"
READBACK_STATUS = "declared_not_measured"
PUBLIC_LABEL_SARF = "Ṣarf — how this piece forms the word"
PUBLIC_LABEL_NAHW = "Naḥw — what this piece does here"
OWNER_ACCEPTANCE = (
    "demonstrate the COMPLETE chain — entry → sense → card → selected word → "
    "source/card evidence → display-local/canonical crosswalk → canonical occurrence → "
    "certified typed facts → shared compiler → rich-at-rest projection → rich hover → "
    "every repeated appearance → public readback target → reverse trace to entry/card/source."
)

DEFAULT_EVIDENCE = ROOT.parent / "canary-sufaha" / "sufaha-evidence.jsonl"
DEFAULT_WHITELIST = ROOT.parent / "data" / "rh_live_01_beta_whitelist.jsonl"
DEFAULT_ENTRIES = ROOT.parent / "data" / "entries.jsonl"
DEFAULT_EDGES_DIR = ROOT.parent / "lanes" / "EDGES"
DEFAULT_APPEARANCES = ROOT / "qamus" / "indexes" / "occurrence-appearances.jsonl"


def _sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_jsonl_with_lines(path: Path) -> tuple[list[dict[str, Any]], list[int]]:
    rows: list[dict[str, Any]] = []
    lines: list[int] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected an object")
        rows.append(value)
        lines.append(line_number)
    return rows, lines


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _require_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"required read-only input is absent: {resolved}")
    return resolved


def _source_address(kind: str, filename: str, line: int | None = None, selector: str = "") -> str:
    value = f"input:{kind}/{filename}"
    if line is not None:
        value += f"#line={line}"
    if selector:
        value += f"#{selector}"
    return value


def _row_at(rows: list[dict[str, Any]], lines: list[int], predicate, label: str) -> tuple[dict[str, Any], int]:
    for row, line in zip(rows, lines):
        if predicate(row):
            return row, line
    raise ValueError(f"could not resolve {label}")


def _entry_forms(entry: Mapping[str, Any]) -> list[str]:
    forms: list[str] = []
    for usage in entry.get("usage", []) or []:
        if isinstance(usage, Mapping):
            forms.extend(str(value) for value in usage.get("forms", []) or [])
    return forms


def load_inputs(
    *,
    evidence_path: Path | str | None = None,
    whitelist_path: Path | str | None = None,
    entries_path: Path | str | None = None,
    edges_dir: Path | str | None = None,
    appearances_path: Path | str | None = None,
) -> dict[str, Any]:
    """Load the exact source rows needed by the proof, without writing them."""

    evidence_file = _require_file(Path(evidence_path) if evidence_path else DEFAULT_EVIDENCE)
    whitelist_file = _require_file(Path(whitelist_path) if whitelist_path else DEFAULT_WHITELIST)
    entries_file = _require_file(Path(entries_path) if entries_path else DEFAULT_ENTRIES)
    appearances_file = _require_file(Path(appearances_path) if appearances_path else DEFAULT_APPEARANCES)
    edge_root = (Path(edges_dir) if edges_dir else DEFAULT_EDGES_DIR).expanduser().resolve()
    report_file = _require_file(edge_root / "EDGES-REPORT.md")
    summary_file = _require_file(edge_root / "edge-closure-summary.json")
    repair_file = _require_file(edge_root / "full-artifacts" / "sufaha-graph-repair-edges.jsonl")

    evidence_rows, evidence_lines = _read_jsonl_with_lines(evidence_file)
    whitelist_rows, whitelist_lines = _read_jsonl_with_lines(whitelist_file)
    entries, entry_lines = _read_jsonl_with_lines(entries_file)
    appearance_rows, appearance_lines = _read_jsonl_with_lines(appearances_file)
    repair_edges, repair_lines = _read_jsonl_with_lines(repair_file)
    edge_summary = _read_json(summary_file)

    facts = sorted(evidence_rows, key=lambda row: int(row.get("fact", 0)))
    if [int(row.get("fact", 0)) for row in facts] != list(range(1, 12)):
        raise ValueError("the canary packet must contain exactly facts 1..11")
    if any(row.get("status") != "certified" for row in facts):
        raise ValueError("the canary packet contains a non-certified fact")
    lexical_entry, lexical_line = _row_at(
        entries, entry_lines, lambda row: str(row.get("id")) == LEXICAL_ENTRY_ID,
        "the documented lexical entry",
    )
    if _entry_forms(lexical_entry)[1] != SUFAHA_BODY:
        raise ValueError("the documented plural is not usage[0].forms[1]")
    if str(lexical_entry.get("root")) != "س ف ه":
        raise ValueError("the documented lexical entry has an unexpected root")
    whitelist_row, whitelist_line = _row_at(
        whitelist_rows, whitelist_lines,
        lambda row: str(row.get("loc")) == SUFAHA_LOC and str(row.get("surface")) == SUFAHA_SURFACE,
        "the actual 2:13:12 card row",
    )
    if str(whitelist_row.get("entry_id")) != PAGE_CONTEXT_ENTRY_ID:
        raise ValueError("the actual row no longer carries the page-context entry")
    if str(whitelist_row.get("card_ref")) != "2:13":
        raise ValueError("the actual row no longer carries card_ref 2:13")
    appearance_row, appearance_line = _row_at(
        appearance_rows, appearance_lines, lambda row: str(row.get("loc")) == SUFAHA_LOC,
        "the 2:13:12 appearance index row",
    )
    appearances = appearance_row.get("appearances") or []
    if len(appearances) != 2 or int(appearance_row.get("appearance_count", 0)) != 2:
        raise ValueError("the occurrence appearance index must contain exactly two appearances")
    if len(repair_edges) != 9:
        raise ValueError("the EDGES repair chain must contain nine records")

    source_addresses = {
        "evidence": [
            _source_address("canary-sufaha", "sufaha-evidence.jsonl", line, f"fact={number}")
            for number, line in enumerate(evidence_lines, 1)
        ],
        "lexical_entry": _source_address("data", "entries.jsonl", lexical_line, f"id={LEXICAL_ENTRY_ID}"),
        "whitelist_row": _source_address("data", "rh_live_01_beta_whitelist.jsonl", whitelist_line, f"loc={SUFAHA_LOC}"),
        "appearances": _source_address(
            "qamus/indexes", "occurrence-appearances.jsonl", appearance_line, f"loc={SUFAHA_LOC}"
        ),
        "edges_report": "input:lanes/EDGES/EDGES-REPORT.md#sufaha",
        "edge_summary": "input:lanes/EDGES/edge-closure-summary.json#sufaha",
        "repair_edges": [
            _source_address("lanes/EDGES/full-artifacts", "sufaha-graph-repair-edges.jsonl", line, f"record={index}")
            for index, line in enumerate(repair_lines, 1)
        ],
    }
    source_files = {
        "evidence": evidence_file,
        "whitelist": whitelist_file,
        "entries": entries_file,
        "appearances": appearances_file,
        "edges_report": report_file,
        "edge_summary": summary_file,
        "repair_edges": repair_file,
    }
    return {
        "evidence_rows": facts,
        "whitelist_rows": whitelist_rows,
        "whitelist_row": whitelist_row,
        "entries": entries,
        "lexical_entry": lexical_entry,
        "appearance_row": appearance_row,
        "appearances": appearances,
        "repair_edges": repair_edges,
        "edge_summary": edge_summary,
        "source_addresses": source_addresses,
        "source_hashes": {key: _file_sha256(path) for key, path in source_files.items()},
    }


def _edge_id(edge_type: str, from_node_id: str, to_node_id: str, details: Mapping[str, Any]) -> str:
    return "edge:" + _sha256({
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "details": details,
    })[:24]


def _proof_edge(
    edge_type: str,
    from_node_id: str,
    to_node_id: str,
    status: str,
    *,
    evidence: Iterable[Mapping[str, Any]],
    details: Mapping[str, Any] | None = None,
    guards: Iterable[str] = (),
) -> dict[str, Any]:
    if status not in {"candidate", "deterministic_exact"}:
        raise ValueError(f"proofn edge is outside candidate boundary: {status}")
    normalized_details = dict(details or {})
    return {
        "schema": GRAPH_SCHEMA,
        "edge_id": _edge_id(edge_type, from_node_id, to_node_id, normalized_details),
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "from_node_type": from_node_id.split(":", 1)[0],
        "to_node_id": to_node_id,
        "to_node_type": to_node_id.split(":", 1)[0],
        "status": status,
        "evidence": [
            {"address": str(item["address"]), "method": str(item.get("method", ""))}
            for item in evidence
        ],
        "producer": {"id": PROOF_PRODUCER_ID, "version": PROOF_PRODUCER_VERSION},
        "guards": list(guards),
        "details": normalized_details,
    }


def _edge_address(edge: Mapping[str, Any]) -> str:
    return f"qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#{edge['edge_id']}"


def _public_sarf(text: str) -> str:
    if text.startswith("Ṣarf:"):
        text = text[len("Ṣarf:"):].lstrip()
    if text.startswith("Ṣarf boundary:"):
        text = text[len("Ṣarf boundary:"):].lstrip()
    return f"{PUBLIC_LABEL_SARF}: {text}"


def _public_nahw(text: str) -> str:
    if text.startswith("Naḥw:"):
        text = text[len("Naḥw:"):].lstrip()
    return f"{PUBLIC_LABEL_NAHW}: {text}"


def _appearance_addresses(inputs: Mapping[str, Any]) -> list[str]:
    line = inputs["source_addresses"]["appearances"].split("#", 1)[0]
    return [f"{line}#loc={SUFAHA_LOC}#appearance={index}" for index in range(1, 3)]


def _build_edges(
    inputs: Mapping[str, Any],
    contract: Mapping[str, Any],
    payload_id: str,
) -> list[dict[str, Any]]:
    """Retain the EDGES chain, then materialize its missing proof path."""

    edges = copy.deepcopy(inputs["repair_edges"])
    fact_addresses = list(inputs["source_addresses"]["evidence"])
    whitelist_address = inputs["source_addresses"]["whitelist_row"]
    lexical_address = inputs["source_addresses"]["lexical_entry"]
    source_evidence = [
        {"address": address, "method": "certified_packet_exact_address"}
        for address in fact_addresses
    ]
    edges.append(_proof_edge(
        "page_context_entry_edge", OCCURRENCE_NODE_ID, f"entry:{PAGE_CONTEXT_ENTRY_ID}",
        "deterministic_exact",
        evidence=[{"address": whitelist_address, "method": "page_context_entry_id"}],
        details={
            "page_context_only": True, "entry_id": PAGE_CONTEXT_ENTRY_ID,
            "surface": SUFAHA_SURFACE, "loc": SUFAHA_LOC, "never_lexeme_edge": True,
        },
        guards=("page_context_is_not_lexeme", "retain_whitelist_identity"),
    ))
    edges.append(_proof_edge(
        "projection_input_edge", OCCURRENCE_NODE_ID,
        "card:proofn:projection-input:sufaha:2:13:12", "candidate",
        evidence=[{
            "address": "qamus/examples/proof-noun-sufaha/sufaha-contract.json#/canonical_occurrence",
            "method": "shared_compiler_input",
        }],
        details={
            "contract_id": contract["contract_id"], "surface": SUFAHA_SURFACE,
            "canonical_location": SUFAHA_LOC, "source_card": "2:13", "payload_id": payload_id,
        },
        guards=("candidate_projection_input", "canonical_occurrence_exact"),
    ))
    edges.append(_proof_edge(
        "certified_fact_attachment_edge", "card:proofn:projection-input:sufaha:2:13:12",
        f"entry:{LEXICAL_ENTRY_ID}", "candidate", evidence=source_evidence,
        details={
            "fact_count": len(contract["facts"]),
            "certified_fact_count": sum(
                fact["certification"]["status"] == "certified" for fact in contract["facts"]
            ),
            "fact_ids": [fact["fact_id"] for fact in contract["facts"]],
            "packet_addresses": fact_addresses,
        },
        guards=("certified_packet_only", "candidate_attachment", "no_fact_invention"),
    ))
    edges.append(_proof_edge(
        "shared_compiler_edge", "card:proofn:projection-input:sufaha:2:13:12",
        "card:proofn:compiler:fd.shared_candidate_projection.v1", "candidate",
        evidence=[{"address": "tools.fd_compiler:build_sufaha_contract", "method": "shared_compiler_call"}],
        details={
            "producer_id": fd_compiler.PRODUCER_ID,
            "projector_id": fd_compiler.PROJECTOR_ID,
            "projector_version": fd_compiler.PROJECTOR_VERSION,
            "contract_id": contract["contract_id"],
        },
        guards=("shared_compiler_required", "candidate_only"),
    ))
    for artifact_name in (
        "sufaha-normalized-public-payload.json", "compact-projection.json",
        "expanded-sarf.json", "expanded-nahw.json",
    ):
        edges.append(_proof_edge(
            "rich_projection_edge", "card:proofn:compiler:fd.shared_candidate_projection.v1",
            f"card:proofn:projection:{artifact_name}", "candidate",
            evidence=[{
                "address": f"qamus/examples/proof-noun-sufaha/{artifact_name}",
                "method": "generated_projection",
            }],
            details={"artifact": artifact_name, "payload_id": payload_id},
            guards=("same_payload_identity", "candidate_projection"),
        ))
    edges.append(_proof_edge(
        "hover_structure_edge", "card:proofn:projection:expanded-nahw.json",
        "card:proofn:hover:sufaha:2:13:12", "candidate",
        evidence=[{
            "address": "qamus/examples/proof-noun-sufaha/rich-hover.json",
            "method": "generated_hover_structure",
        }],
        details={"payload_id": payload_id, "public_labels": [PUBLIC_LABEL_SARF, PUBLIC_LABEL_NAHW]},
        guards=("rich_hover_compiled_from_payload", "n_lang_clean"),
    ))
    edges.append(_proof_edge(
        "readback_target_edge", "card:proofn:hover:sufaha:2:13:12",
        "card:proofn:readback-target:public:quran:2:13:12", "candidate",
        evidence=[{
            "address": "qamus/examples/proof-noun-sufaha/readback-target.json",
            "method": "declared_target",
        }],
        details={"status": READBACK_STATUS, "live_deployment": False, "payload_id": payload_id},
        guards=("no_live_readback_claim", "candidate_pre_deploy"),
    ))
    for index, address in enumerate(_appearance_addresses(inputs), 1):
        edges.append(_proof_edge(
            "rendered_appearance_edge", OCCURRENCE_NODE_ID, f"appearance:{SUFAHA_LOC}:{index}",
            "candidate", evidence=[{"address": address, "method": "occurrence_appearance_index"}],
            details={
                "appearance_index": index, "canonical_surface": SUFAHA_SURFACE,
                "projection_hash": inputs["appearance_row"]["projection_hash"],
                "payload_id": payload_id, "same_payload_id": True,
                "readback_target_status": READBACK_STATUS,
            },
            guards=("all_indexed_appearances", "candidate_pre_deploy"),
        ))
    for fact_number, (fact, address) in enumerate(zip(contract["facts"], fact_addresses), 1):
        edges.append(_proof_edge(
            "decision_evidence_edge", OCCURRENCE_NODE_ID, f"entry:{LEXICAL_ENTRY_ID}",
            "candidate",
            evidence=[{"address": address, "method": "certified_packet_exact_address"}],
            details={
                "fact_id": fact["fact_id"], "fact_number": fact_number,
                "certification_status": fact["certification"]["status"],
                "packet_address": address,
            },
            guards=("source_fact_not_invented", "candidate_mode_only"),
        ))
    edges.extend([
        _proof_edge(
            "reverse_trace_edge", f"entry:{LEXICAL_ENTRY_ID}", SELECTED_WORD_NODE_ID,
            "candidate", evidence=[{"address": lexical_address, "method": "entry_reverse_trace"}],
            details={"direction": "entry_to_selected_word", "documented_form": SUFAHA_BODY},
            guards=("reverse_entry_trace",),
        ),
        _proof_edge(
            "reverse_trace_edge", CARD_NODE_ID, SELECTED_WORD_NODE_ID, "candidate",
            evidence=[{"address": whitelist_address, "method": "card_reverse_trace"}],
            details={"direction": "card_to_selected_word", "card_ref": "2:13"},
            guards=("reverse_card_trace",),
        ),
        _proof_edge(
            "source_evidence_edge", OCCURRENCE_NODE_ID, f"entry:{LEXICAL_ENTRY_ID}", "candidate",
            evidence=source_evidence,
            details={
                "fact_count": len(contract["facts"]),
                "entry_address": lexical_address,
                "source_card_address": whitelist_address,
                "appearance_index_address": inputs["source_addresses"]["appearances"],
            },
            guards=("exact_packet_backlinks", "candidate_source_trace"),
        ),
    ])
    return edges


def _build_public_views(
    payload: dict[str, Any],
    contract: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> str:
    for component in payload["components"]:
        component["sarf"] = _public_sarf(str(component["sarf"]))
        component["nahw"] = _public_nahw(str(component["nahw"]))
    payload["authorization_state"] = AUTHORIZATION_STATE
    payload["materialization"] = {
        "status": "candidate",
        "public_materialization_allowed": False,
        "live_mutation_allowed": False,
        "reason": "deploy-shaped proof artifact only; no live deployment",
    }
    payload["compiled_from"] = {
        "producer_id": fd_compiler.PRODUCER_ID,
        "projector_id": fd_compiler.PROJECTOR_ID,
        "projector_version": fd_compiler.PROJECTOR_VERSION,
        "contract_id": contract["contract_id"],
        "fact_ids": [fact["fact_id"] for fact in contract["facts"]],
    }
    payload["source_identity_split"] = {
        "lexical_entry_id": LEXICAL_ENTRY_ID,
        "page_context_entry_id": PAGE_CONTEXT_ENTRY_ID,
        "page_context_retained_separately": True,
    }
    payload["readback_target"] = {
        "target_id": "public-readback:quran:2:13:12",
        "status": READBACK_STATUS,
        "route": "public hover target",
        "reason": "candidate pre-deploy artifact; no live deployment",
    }
    payload["rich_explanations"] = {
        "sarf": _public_sarf(str(payload["rich_explanations"]["sarf"])),
        "nahw": _public_nahw(str(payload["rich_explanations"]["nahw"])),
    }
    payload_id = "proofn.payload.sufaha.v1:" + _sha256({
        "surface": payload["canonical_identity"]["surface"],
        "at_rest_spans": payload["at_rest_spans"],
        "comparison": payload["comparison"],
        "components": payload["components"],
        "contract_id": contract["contract_id"],
    })
    payload["payload_id"] = payload_id
    payload["compact_view"] = {
        "payload_id": payload_id,
        "surface": payload["canonical_identity"]["surface"],
        "at_rest_spans": copy.deepcopy(payload["at_rest_spans"]),
        "gloss": "the foolish ones",
        "learner_explanation": "The article, plural body, and final nominative mark are separate visible spans.",
        "public_labels": [PUBLIC_LABEL_SARF, PUBLIC_LABEL_NAHW],
    }
    payload["expanded_view"] = {
        "payload_id": payload_id,
        "surface": payload["canonical_identity"]["surface"],
        "at_rest_spans": copy.deepcopy(payload["at_rest_spans"]),
        "sarf": payload["rich_explanations"]["sarf"],
        "nahw": payload["rich_explanations"]["nahw"],
        "comparison": copy.deepcopy(payload["comparison"]),
        "public_labels": [PUBLIC_LABEL_SARF, PUBLIC_LABEL_NAHW],
    }
    payload["rich_hover"] = {
        "payload_id": payload_id,
        "surface": payload["canonical_identity"]["surface"],
        "gloss": "the foolish ones",
        "learner_explanation": "The plural body سُفَهَاء follows فُعَلَاء and keeps the root س ف ه; the final ُ is a nominative ending because the noun is the subject of آمَنَ.",
        "sarf": payload["rich_explanations"]["sarf"],
        "nahw": payload["rich_explanations"]["nahw"],
        "n_lang_clean": True,
        "public_labels": [PUBLIC_LABEL_SARF, PUBLIC_LABEL_NAHW],
        "typed_fact_ids": [fact["fact_id"] for fact in contract["facts"]],
    }
    payload["appearance_parity"] = {
        "occurrence_id": SUFAHA_LOC,
        "appearance_count": len(inputs["appearances"]),
        "projection_hash": inputs["appearance_row"]["projection_hash"],
        "payload_id": payload_id,
        "parity": True,
        "readback_status": READBACK_STATUS,
        "appearances": [
            {
                "appearance_index": index,
                "node_id": f"appearance:{SUFAHA_LOC}:{index}",
                "source_address": address,
                "payload_id": payload_id,
                "same_payload_id": True,
                "status": "candidate",
                "readback_target": READBACK_STATUS,
            }
            for index, address in enumerate(_appearance_addresses(inputs), 1)
        ],
    }
    return payload_id


def _build_manifest(
    inputs: Mapping[str, Any],
    contract: Mapping[str, Any],
    payload: Mapping[str, Any],
    edges: list[Mapping[str, Any]],
    fam2_record: Mapping[str, Any],
) -> dict[str, Any]:
    by_type: dict[str, list[Mapping[str, Any]]] = {}
    for edge in edges:
        by_type.setdefault(str(edge["edge_type"]), []).append(edge)

    def first(edge_type: str) -> Mapping[str, Any]:
        return by_type[edge_type][0]

    evidence_addresses = list(inputs["source_addresses"]["evidence"])
    chain = [
        {
            "step": "entry",
            "address": inputs["source_addresses"]["lexical_entry"],
            "status": "deterministic_exact",
            "note": "documented lexical entry selected from the exact plural form",
        },
        {
            "step": "sense",
            "address": f"entry:{LEXICAL_ENTRY_ID}:senses[0]",
            "status": "deterministic_exact",
            "edge": _edge_address(first("sense_entry_edge")),
        },
        {
            "step": "card",
            "address": inputs["source_addresses"]["whitelist_row"] + "#card_ref=2:13",
            "status": "candidate",
            "edge": _edge_address(first("source_card_edge")),
        },
        {
            "step": "selected_word",
            "address": _edge_address(first("source_card_edge")),
            "status": "candidate",
            "node_id": SELECTED_WORD_NODE_ID,
        },
        {
            "step": "source_card_evidence",
            "address": inputs["source_addresses"]["whitelist_row"],
            "status": "deterministic_exact",
            "edge": _edge_address(first("display_local_to_canonical_crosswalk_edge")),
        },
        {
            "step": "selected_example",
            "address": _edge_address(first("selected_example_edge")),
            "status": "candidate",
            "target": OCCURRENCE_NODE_ID,
        },
        {
            "step": "display_local_to_canonical_crosswalk",
            "address": _edge_address(first("display_local_to_canonical_crosswalk_edge")),
            "status": "deterministic_exact",
            "surface": SUFAHA_SURFACE,
        },
        {
            "step": "canonical_occurrence",
            "address": _edge_address(first("canonical_occurrence_edge")),
            "status": "deterministic_exact",
            "location": SUFAHA_LOC,
        },
        {
            "step": "typed_facts",
            "address": "qamus/examples/proof-noun-sufaha/sufaha-contract.json#/facts",
            "status": "candidate",
            "fact_count": 11,
            "evidence_addresses": evidence_addresses,
        },
        {
            "step": "certified_fact_attachment",
            "address": _edge_address(first("certified_fact_attachment_edge")),
            "status": "candidate",
            "evidence_addresses": evidence_addresses,
        },
        {
            "step": "shared_compiler",
            "address": "tools/fd_compiler.py#build_sufaha_contract+build_sufaha_payload",
            "status": "candidate",
            "edge": _edge_address(first("shared_compiler_edge")),
        },
        {
            "step": "at_rest_projection",
            "address": "qamus/examples/proof-noun-sufaha/sufaha-normalized-public-payload.json#/at_rest_spans",
            "status": "candidate",
        },
        {
            "step": "compact_projection",
            "address": "qamus/examples/proof-noun-sufaha/compact-projection.json",
            "status": "candidate",
            "payload_id": payload["payload_id"],
        },
        {
            "step": "expanded_sarf_projection",
            "address": "qamus/examples/proof-noun-sufaha/expanded-sarf.json",
            "status": "candidate",
            "label": PUBLIC_LABEL_SARF,
        },
        {
            "step": "expanded_nahw_projection",
            "address": "qamus/examples/proof-noun-sufaha/expanded-nahw.json",
            "status": "candidate",
            "label": PUBLIC_LABEL_NAHW,
        },
        {
            "step": "rich_hover",
            "address": "qamus/examples/proof-noun-sufaha/rich-hover.json",
            "status": "candidate",
            "edge": _edge_address(first("hover_structure_edge")),
        },
        {
            "step": "repeated_appearances",
            "address": inputs["source_addresses"]["appearances"],
            "status": "candidate",
            "appearance_count": len(inputs["appearances"]),
            "edges": [_edge_address(edge) for edge in by_type["rendered_appearance_edge"]],
        },
        {
            "step": "public_readback_target",
            "address": "qamus/examples/proof-noun-sufaha/readback-target.json",
            "status": READBACK_STATUS,
            "edge": _edge_address(first("readback_target_edge")),
        },
        {
            "step": "reverse_trace",
            "address": "qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge_type=reverse_trace_edge",
            "status": "candidate",
            "edges": [_edge_address(edge) for edge in by_type["reverse_trace_edge"]],
        },
    ]
    return {
        "schema": "qamus.proofn.manifest.v1",
        "manifest_version": "1.0.0",
        "lane": "PROOF-N",
        "owner_section": "§10",
        "owner_acceptance_section": "§13",
        "owner_acceptance": OWNER_ACCEPTANCE,
        "mode": "candidate",
        "authorization_state": AUTHORIZATION_STATE,
        "identity": {
            "lexical_entry_id": LEXICAL_ENTRY_ID,
            "page_context_entry_id": PAGE_CONTEXT_ENTRY_ID,
            "canonical_location": SUFAHA_LOC,
            "canonical_occurrence_id": f"quran:{SUFAHA_LOC}",
            "surface": SUFAHA_SURFACE,
            "lexical_body": SUFAHA_BODY,
            "documented_plural_form": SUFAHA_BODY,
            "sense_node_id": SENSE_NODE_ID,
            "card_ref": "2:13",
            "card_node_id": CARD_NODE_ID,
            "selected_word_node_id": SELECTED_WORD_NODE_ID,
            "occurrence_node_id": OCCURRENCE_NODE_ID,
        },
        "source_identity_split": {
            "page_context_edge_target": f"entry:{PAGE_CONTEXT_ENTRY_ID}",
            "lexeme_edge_target": f"entry:{LEXICAL_ENTRY_ID}",
            "page_context_retained_separately": True,
            "selection_basis": "documented-form evidence, not page-context entry_id",
        },
        "chain": chain,
        "artifact_addresses": {
            "contract": "qamus/examples/proof-noun-sufaha/sufaha-contract.json",
            "typed_edge_graph": "qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl",
            "payload": "qamus/examples/proof-noun-sufaha/sufaha-normalized-public-payload.json",
            "compact": "qamus/examples/proof-noun-sufaha/compact-projection.json",
            "expanded_sarf": "qamus/examples/proof-noun-sufaha/expanded-sarf.json",
            "expanded_nahw": "qamus/examples/proof-noun-sufaha/expanded-nahw.json",
            "rich_hover": "qamus/examples/proof-noun-sufaha/rich-hover.json",
            "appearance_parity": "qamus/examples/proof-noun-sufaha/appearance-parity.json",
            "readback_target": "qamus/examples/proof-noun-sufaha/readback-target.json",
            "fam2": "qamus/examples/proof-noun-sufaha/fam2-formation-candidate.json",
            "render_proof": "qamus/examples/proof-noun-sufaha/render-proof.json",
            "validator": "qamus/examples/proof-noun-sufaha/proofn-validation.json",
            "typed_edge_validator": "qamus/examples/proof-noun-sufaha/typed-edge-validation.json",
            "html": "qamus/examples/proof-noun-sufaha/proofn-card.html",
        },
        "source_addresses": inputs["source_addresses"],
        "source_hashes": inputs["source_hashes"],
        "evidence_backlinks": [
            {
                "fact_number": index,
                "fact_id": fact["fact_id"],
                "address": address,
                "status": fact["certification"]["status"],
            }
            for index, (fact, address) in enumerate(zip(contract["facts"], evidence_addresses), 1)
        ],
        "formation": {
            "contract_id": fam2_record["contract_id"],
            "status": fam2_record["projection"]["status"],
            "fact_types": [fact["fact_type"] for fact in fam2_record["facts"]],
            "artifact": "qamus/examples/proof-noun-sufaha/fam2-formation-candidate.json",
        },
        "boundary": {
            "live_mutation_allowed": False,
            "public_materialization_allowed": False,
            "readback_status": READBACK_STATUS,
            "no_live_deployment": True,
            "png_policy": "PNG local-only; no PNG is tracked",
            "jamid_mushtaq_tension": "unresolved",
        },
        "validation": {
            "typed_edge_validator": "all ten named checks on qamus/examples/edges fixture",
            "typed_edge_validation_artifact": "qamus/examples/proof-noun-sufaha/typed-edge-validation.json",
            "proofn_validator": "qamus/examples/proof-noun-sufaha/proofn-validation.json",
            "proofn_validation_status": "generated_after_write",
            "fam2_record_status": fam2_record["projection"]["status"],
        },
    }


def _build_report(
    inputs: Mapping[str, Any],
    contract: Mapping[str, Any],
    payload: Mapping[str, Any],
    edges: list[Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> str:
    edge_by_type: dict[str, list[Mapping[str, Any]]] = {}
    for edge in edges:
        edge_by_type.setdefault(str(edge["edge_type"]), []).append(edge)
    lines = [
        "# PROOF-N noun proof: سُفَهَاءُ",
        "",
        "Status: candidate, deploy-shaped, pre-deploy. No whitelist, renderer, live, publication, or scholarly mutation was performed.",
        "",
        f"Owner acceptance (§13): {OWNER_ACCEPTANCE}",
        "",
        "## Chain walk-through",
        "",
        "The proof uses documented lexical entry 1ffcc554ec44 and retains page-context entry c59a0161fac8 as a separate edge. The actual occurrence is 2:13:12, surface السُّفَهَاءُ, with card reference 2:13.",
        "",
    ]
    for link in manifest["chain"]:
        note = f" — {link['note']}" if link.get("note") else ""
        lines.append(f"- {link['step']} — {link['status']} — {link['address']}{note}")
    lines.extend([
        "",
        "## Owner list and evidence",
        "",
        "| Item | Compiled result | Evidence address |",
        "| --- | --- | --- |",
        f"| lexical entry | {LEXICAL_ENTRY_ID}; documented plural سُفَهَاء | {inputs['source_addresses']['lexical_entry']} and entry:{LEXICAL_ENTRY_ID}:usage[0].forms[1] |",
        f"| page-context entry | {PAGE_CONTEXT_ENTRY_ID}, retained as page context | {inputs['source_addresses']['whitelist_row']} |",
        f"| sense/card/example | {SENSE_NODE_ID}; card 2:13; occurrence {SUFAHA_LOC} | entry:{LEXICAL_ENTRY_ID}:senses[0]; {inputs['source_addresses']['whitelist_row']}; {_edge_address(edge_by_type['selected_example_edge'][0])} |",
        f"| selected word | {SELECTED_WORD_NODE_ID} | {_edge_address(edge_by_type['source_card_edge'][0])} |",
        f"| canonical occurrence | quran:{SUFAHA_LOC} | {_edge_address(edge_by_type['canonical_occurrence_edge'][0])} |",
        f"| display/local crosswalk | exact {SUFAHA_SURFACE} reconstruction | {_edge_address(edge_by_type['display_local_to_canonical_crosswalk_edge'][0])} |",
        f"| certified facts | 11/11 certified and attached | {inputs['source_addresses']['evidence'][0]} through {inputs['source_addresses']['evidence'][-1]}; decision-evidence edges |",
        f"| shared compiler | tools.fd_compiler → {payload['payload_id']} | tools/fd_compiler.py#build_sufaha_contract+build_sufaha_payload |",
        "| at-rest spans | article ال (0,2) + lexical body سُّفَهَاء (2,11) + final ُ (11,12) | qamus/examples/proof-noun-sufaha/sufaha-normalized-public-payload.json#/at_rest_spans |",
        f"| Ṣarf | سَفِيه / سُفَهَاء; فَعِيل / فُعَلَاء; root س ف ه; removed ي; introduced ا and ء | {inputs['source_addresses']['evidence'][0]} through {inputs['source_addresses']['evidence'][7]} |",
        f"| Naḥw | final ُ is nominative, not plural-forming; governor آمَنَ; explicit subject relation | {inputs['source_addresses']['evidence'][9]} and {inputs['source_addresses']['evidence'][10]} |",
        f"| rich hover | shared payload id; public labels {PUBLIC_LABEL_SARF} / {PUBLIC_LABEL_NAHW} | qamus/examples/proof-noun-sufaha/rich-hover.json |",
        f"| repeated appearances | 2/2 indexed appearances carry the same payload id | {inputs['source_addresses']['appearances']} and rendered-appearance edges |",
        "| reverse trace | entry → selected word and card → selected word retained | qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge_type=reverse_trace_edge |",
        "",
        "## Typed graph and validation",
        "",
        "The EDGES candidate repair chain is retained and extended with projection_input_edge and certified_fact_attachment_edge, converting the prior graph-attachment blocker into a candidate graph path.",
        f"The generated graph has {len(edges)} records. Every record is {GRAPH_SCHEMA} and has evidence plus status candidate or deterministic_exact.",
        "The ten existing typed-graph checks are recorded at qamus/examples/proof-noun-sufaha/typed-edge-validation.json.",
        "The committed harness invokes the proofn validator against this fixture; it does not read external source paths.",
        "",
        "## Boundary and honest limits",
        "",
        f"authorization_state={AUTHORIZATION_STATE}; live_mutation_allowed=false; public_materialization_allowed=false.",
        f"The public readback target is {READBACK_STATUS}. No live deployment or public server readback was attempted.",
        "The جامد/مشتق classification tension is retained as unresolved and is not used to create or alter any certified fact.",
        "The final nominative ُ is a Naḥw overlay. It is outside the lexical body and never treated as plural-forming.",
        "Any screenshot produced by the local render witness is local-only; no PNG is tracked.",
        "",
    ])
    return "\n".join(lines)


def build_proof(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Build all in-memory proof artifacts from loaded source inputs."""

    contract = copy.deepcopy(fd_compiler.build_sufaha_contract(inputs["evidence_rows"]))
    contract["canonical_occurrence"]["card_id"] = CARD_NODE_ID
    payload, parity_fixture = fd_compiler.build_sufaha_payload(
        contract, inputs["whitelist_rows"], inputs["entries"]
    )
    payload = copy.deepcopy(payload)
    payload["canonical_identity"]["card_id"] = CARD_NODE_ID
    payload_id = _build_public_views(payload, contract, inputs)
    fam2_record = fam2_lexical_producer.produce_record(
        {
            "loc": SUFAHA_LOC,
            "quran_loc": f"quran:{SUFAHA_LOC}",
            "wbw_loc": f"wbw:{SUFAHA_LOC}",
            "surface": SUFAHA_BODY,
            "entry_id": LEXICAL_ENTRY_ID,
        },
        entries=inputs["entries"],
    )
    if fam2_record["projection"]["status"] != "candidate":
        raise ValueError("the entry-backed FAM2 formation producer did not produce a candidate")
    edges = _build_edges(inputs, contract, payload_id)
    manifest = _build_manifest(inputs, contract, payload, edges, fam2_record)
    report = _build_report(inputs, contract, payload, edges, manifest)
    return {
        "manifest": manifest,
        "contract": contract,
        "payload": payload,
        "parity_fixture": parity_fixture,
        "fam2_record": fam2_record,
        "edges": edges,
        "report": report,
        "payload_id": payload_id,
        "source_inputs": {
            "hashes": inputs["source_hashes"],
            "addresses": inputs["source_addresses"],
        },
    }


def render_proof_html(payload: Mapping[str, Any]) -> str:
    """Delegate HTML generation to the shared compiler."""

    return fd_compiler.render_sufaha_html(dict(payload))


def write_artifacts(proof: Mapping[str, Any], output_dir: Path | str = PROOF_DIR) -> dict[str, Path]:
    """Write the deterministic deploy-shaped proof packet."""

    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "sufaha-contract.json", proof["contract"])
    _write_jsonl(output / "typed-edge-graph.jsonl", proof["edges"])
    _write_json(output / "sufaha-normalized-public-payload.json", proof["payload"])
    _write_json(output / "compact-projection.json", proof["payload"]["compact_view"])
    _write_json(output / "expanded-sarf.json", {
        "schema": "qamus.proofn.expanded_sarf.v1",
        "payload_id": proof["payload_id"],
        "label": PUBLIC_LABEL_SARF,
        "text": proof["payload"]["expanded_view"]["sarf"],
        "comparison": proof["payload"]["comparison"],
        "n_lang_clean": True,
    })
    _write_json(output / "expanded-nahw.json", {
        "schema": "qamus.proofn.expanded_nahw.v1",
        "payload_id": proof["payload_id"],
        "label": PUBLIC_LABEL_NAHW,
        "text": proof["payload"]["expanded_view"]["nahw"],
        "governor": "آمَنَ",
        "subject_relation": "explicit subject",
        "case_ending": "ُ",
        "lexical_body": SUFAHA_BODY,
        "n_lang_clean": True,
    })
    _write_json(output / "rich-hover.json", proof["payload"]["rich_hover"])
    _write_json(output / "appearance-parity.json", proof["payload"]["appearance_parity"])
    _write_json(output / "readback-target.json", proof["payload"]["readback_target"])
    _write_json(output / "fam2-formation-candidate.json", proof["fam2_record"])
    _write_json(output / "parity-fixture.json", proof["parity_fixture"])
    _write_json(output / "source-inputs.json", proof["source_inputs"])
    _write_json(output / "typed-edge-validation.json", {
        "schema": "qamus.proofn.typed_edge_validation.v1",
        "status": "pending_fixture_self_test",
        "ok": False,
        "checks": [],
        "source_fixture": "qamus/examples/edges",
    })
    _write_json(output / "render-proof.json", {
        "schema": "qamus.proofn.render_proof.v1",
        "status": "pending_local_render",
        "font_check": False,
        "exact_reconstruction": False,
        "compact_present": False,
        "expanded_present": False,
        "same_payload_identity": False,
        "appearance_parity": False,
        "live_mutation_allowed": False,
        "readback_target_status": READBACK_STATUS,
        "png_policy": "local-only-not-tracked",
    })
    (output / "proofn-card.html").write_text(render_proof_html(proof["payload"]), encoding="utf-8")
    font_source = ROOT / "qamus" / "examples" / "fd" / "assets" / "KawkabMono-Regular.woff2"
    if not font_source.is_file():
        raise FileNotFoundError(f"shared Kawkab Mono asset is absent: {font_source}")
    (output / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(font_source, output / "assets" / font_source.name)
    _write_json(output / "proofn-validation.json", {"status": "pending_validator_run", "errors": []})
    _write_json(ROOT / "PROOFN-MANIFEST.json", proof["manifest"])
    (ROOT / "PROOFN-REPORT.md").write_text(proof["report"], encoding="utf-8")
    return {
        "manifest": ROOT / "PROOFN-MANIFEST.json",
        "report": ROOT / "PROOFN-REPORT.md",
        "contract": output / "sufaha-contract.json",
        "edges": output / "typed-edge-graph.jsonl",
        "payload": output / "sufaha-normalized-public-payload.json",
        "html": output / "proofn-card.html",
        "render_proof": output / "render-proof.json",
    }


def load_proof_artifacts(proof_dir: Path | str = PROOF_DIR) -> dict[str, Any]:
    """Load the committed proof packet for validator/tests."""

    output = Path(proof_dir).expanduser().resolve()
    manifest_path = ROOT / "PROOFN-MANIFEST.json"
    if output != PROOF_DIR.resolve():
        manifest_path = output.parent.parent.parent / "PROOFN-MANIFEST.json"
    edge_path = output / "typed-edge-graph.jsonl"
    return {
        "manifest": _read_json(manifest_path),
        "contract": _read_json(output / "sufaha-contract.json"),
        "payload": _read_json(output / "sufaha-normalized-public-payload.json"),
        "edges": [
            json.loads(line) for line in edge_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ],
        "parity_fixture": _read_json(output / "parity-fixture.json"),
        "fam2_record": _read_json(output / "fam2-formation-candidate.json"),
        "appearance_parity": _read_json(output / "appearance-parity.json"),
        "render_proof": _read_json(output / "render-proof.json"),
        "typed_edge_validation": _read_json(output / "typed-edge-validation.json"),
        "proofn_validation": _read_json(output / "proofn-validation.json") if (output / "proofn-validation.json").is_file() else {},
        "proof_dir": output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--whitelist", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--edges-dir", type=Path, required=True)
    parser.add_argument("--appearances", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=PROOF_DIR)
    args = parser.parse_args(argv)
    inputs = load_inputs(
        evidence_path=args.evidence,
        whitelist_path=args.whitelist,
        entries_path=args.entries,
        edges_dir=args.edges_dir,
        appearances_path=args.appearances,
    )
    proof = build_proof(inputs)
    paths = write_artifacts(proof, args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
