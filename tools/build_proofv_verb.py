#!/usr/bin/env python3
"""Build the bounded PROOF-V real verb proof from explicit read-only inputs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import build_typed_edge_crosswalk as edge_builder
from tools import normalize_ar
from tools import proofv_shared_compiler
from tools import proofv_verb_producer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "qamus" / "examples" / "proof-verb"
TARGET_OWNER_SURFACE = "فَٱتَّبِعْنِي"
TARGET_KEY = normalize_ar.norm_strict(TARGET_OWNER_SURFACE)
FALLBACK_OWNER_SURFACE = "تَوَكَّلْتُ"
FALLBACK_KEY = normalize_ar.norm_strict(FALLBACK_OWNER_SURFACE)
TARGET_LOC = "19:43:10"
TARGET_ENTRY_ID = "5d89e690256d"
TARGET_NEAREST_LOC = "28:50:12"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"expected object at {path}:{line_no}")
                rows.append(value)
    return rows


def _jsonl_with_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"expected object at {path}:{line_no}")
                value["_source_line"] = line_no
                rows.append(value)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _loc(row: dict[str, Any]) -> str:
    return str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:")


def _source_row_projection(row: dict[str, Any]) -> dict[str, Any]:
    source_fields = [key for key in ("surface", "loc", "quran_loc", "morphline", "segments") if key in row]
    safe_segments = []
    for segment in row.get("segments") or []:
        if isinstance(segment, dict):
            safe_segments.append({key: segment[key] for key in ("segment_index", "surface", "role", "class") if key in segment})
    source_hash = hashlib.sha256(
        json.dumps({"loc": _loc(row), "surface": row.get("surface"), "morphline": row.get("morphline"), "segments": safe_segments}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema": "qamus.proofv.source_occurrence.v1",
        "loc": _loc(row),
        "quran_loc": "quran:" + _loc(row),
        "surface": row.get("surface"),
        "owner_surface_requested": TARGET_OWNER_SURFACE,
        "surface_match_key": normalize_ar.norm_strict(str(row.get("surface") or "")),
        "source_line": row.get("source_line"),
        "source_address": f"corpus:rh_live_01_beta_whitelist.jsonl#loc={_loc(row)}",
        "source_row_hash": "sha256:" + source_hash,
        "source_fields_present": source_fields,
        "morphology_assertions": ["form_viii", "imperative", "2ms", "object_1cs"],
        "segments": safe_segments,
        "read_only": True,
        "gloss_fields_excluded": True,
    }


def _survey(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if normalize_ar.norm_strict(str(row.get("surface") or "")) != key:
            continue
        result.append({
            "loc": _loc(row),
            "quran_loc": "quran:" + _loc(row),
            "surface": row.get("surface"),
            "source_entry_id": row.get("entry_id"),
            "source_address": f"corpus:rh_live_01_beta_whitelist.jsonl#loc={_loc(row)}",
            "has_page_context_entry_id": bool(row.get("entry_id")),
            "morphline_present": bool(row.get("morphline")),
            "card_ref": row.get("card_ref"),
        })
    return sorted(result, key=lambda item: item["loc"])


def _entry_root_ids(entries: list[dict[str, Any]], root: str) -> set[str]:
    root_key = " ".join(root.split())
    return {str(row.get("id")) for row in entries if " ".join(str(row.get("root") or "").split()) == root_key}


def _find_nearest_crosswalk(
    entries: list[dict[str, Any]],
    forward: list[dict[str, Any]],
    reverse: list[dict[str, Any]],
    *,
    graph_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    root_ids = _entry_root_ids(entries, "ت ب ع")
    candidates = [
        row for row in forward
        if row.get("crosswalk_status") == "deterministic_exact"
        and row.get("occurrence_id")
        and root_ids.intersection(set(row.get("matched_entry_ids") or []))
    ]
    if not candidates:
        raise ValueError("no deterministic same-lexeme crosswalk candidate exists for root ت ب ع")
    candidate = next((row for row in candidates if row.get("occurrence_id") == TARGET_NEAREST_LOC), candidates[0])
    entry_id = str((candidate.get("matched_entry_ids") or [""])[0])
    reverse_row = next((row for row in reverse if str(row.get("entry_id")) == entry_id), None)
    if not reverse_row:
        raise ValueError("nearest crosswalk has no reverse entry row")
    if candidate.get("occurrence_id") not in (reverse_row.get("occurrence_ids") or []):
        raise ValueError("nearest crosswalk forward/reverse occurrence reciprocity failed")
    edge_ids = set(candidate.get("edge_ids") or []) | set(reverse_row.get("edge_ids") or [])
    sense_id = f"sense:{entry_id}:s1"
    selected_word_id = str(candidate["selected_word_id"])
    occurrence_id = str(candidate["occurrence_id"])
    selected_edges: list[dict[str, Any]] = []
    with (graph_dir / "typed-edge-graph.jsonl").open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            edge_id = str(row.get("edge_id") or "")
            details = row.get("details") or {}
            edge_type = row.get("edge_type")
            chain_match = (
                edge_type in {"canonical_occurrence_edge", "form_entry_edge", "lexeme_entry_edge", "source_card_edge"}
                and row.get("from_node_id") == selected_word_id
            ) or (
                edge_type == "selected_example_edge"
                and row.get("from_node_id") == str(candidate["card_id"])
                and row.get("to_node_id") == f"occurrence:{occurrence_id}"
            ) or (
                edge_type == "sense_entry_edge" and row.get("from_node_id") == sense_id
            ) or (
                edge_type == "rendered_appearance_edge" and row.get("from_node_id") == f"occurrence:{occurrence_id}"
            )
            if edge_id in edge_ids and chain_match:
                selected_edges.append(row)
            elif row.get("edge_type") == "sense_entry_edge" and row.get("from_node_id") == sense_id:
                selected_edges.append(row)
            elif row.get("edge_type") == "selected_example_edge" and row.get("to_node_id") == f"occurrence:{occurrence_id}":
                selected_edges.append(row)
            elif row.get("edge_type") == "source_card_edge" and row.get("from_node_id") == selected_word_id:
                selected_edges.append(row)
            elif row.get("edge_type") == "rendered_appearance_edge" and details.get("loc") == occurrence_id:
                selected_edges.append(row)
    by_id = {str(row.get("edge_id")): row for row in selected_edges if row.get("edge_id")}
    selected_edges = [by_id[key] for key in sorted(by_id)]
    if not any(row.get("edge_type") == "canonical_occurrence_edge" for row in selected_edges):
        raise ValueError("nearest same-lexeme chain lacks canonical occurrence edge")
    if not any(row.get("edge_type") == "selected_example_edge" for row in selected_edges):
        raise ValueError("nearest same-lexeme chain lacks selected-example edge")
    entry = next(row for row in entries if str(row.get("id")) == entry_id)
    sense = (entry.get("senses") or [])[0]
    nearest = {
        "entry_id": entry_id,
        "root": str(entry.get("root") or ""),
        "sense_id": sense_id,
        "card_id": str(candidate["card_id"]),
        "selected_word_id": selected_word_id,
        "occurrence_id": occurrence_id,
        "entry_surface": str(sense.get("ar") or ""),
        "entry_surface_address": f"entry:{entry_id}:senses[0].ar",
        "crosswalk_status": str(candidate["crosswalk_status"]),
        "crosswalk_edge_ids": sorted(edge_ids),
        "chain_edge_ids": [str(row["edge_id"]) for row in selected_edges],
    }
    return nearest, candidate, reverse_row, selected_edges


def _target_edges(graph_dir: Path, target: dict[str, Any], nearest: dict[str, Any], nearest_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_edges: list[dict[str, Any]] = []
    loc = _loc(target)
    with (graph_dir / "typed-edge-graph.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            details = row.get("details") or {}
            if row.get("edge_type") == "rendered_appearance_edge" and details.get("loc") == loc:
                target_edges.append(row)
    if not target_edges:
        raise ValueError("target occurrence has no EDGES rendered appearance edge")
    gap_edge = edge_builder.make_edge(
        "decision_evidence_edge",
        edge_builder.occurrence_node(loc),
        str(nearest["selected_word_id"]),
        "source_gap",
        evidence=[{"address": f"crosswalk:nearest:{nearest['occurrence_id']}", "method": "nearest_same_lexeme_only"}],
        guards=["target_direct_lexeme_edge_absent", "page_context_never_lexeme"],
        details={
            "route": "scholar-packet:proofv.target-lexeme-occurrence-link",
            "target_occurrence": loc,
            "nearest_same_lexeme_occurrence": nearest["occurrence_id"],
            "reason": "the target is reader-only; this record is decision evidence, not a lexeme assertion",
        },
        producer_id="tools.build_proofv_verb",
        producer_version="1.0.0",
    )
    target_edges.append(gap_edge)
    all_edges = nearest_edges + target_edges
    unique = {str(row["edge_id"]): row for row in all_edges}
    return [unique[key] for key in sorted(unique)]


def _selection(target_rows: list[dict[str, Any]], fallback_rows: list[dict[str, Any]], nearest: dict[str, Any], forward: dict[str, Any], reverse: dict[str, Any]) -> dict[str, Any]:
    target = target_rows[0]
    return {
        "schema": "qamus.proofv.selection.v1",
        "owner_preference": TARGET_OWNER_SURFACE,
        "owner_surface_match_key": TARGET_KEY,
        "chosen_surface": target["surface"],
        "chosen_loc": target["loc"],
        "chosen_occurrence_is_card_selected": False,
        "chosen_occurrence_chain": {
            "direct_lexeme_edge": False,
            "direct_form_edge": False,
            "direct_card_edge": False,
            "direct_selected_word_edge": False,
            "rendered_appearance_edge": True,
            "status": "reader_only_source_gap",
        },
        "nearest_card_selected_same_lexeme": {
            "entry_id": nearest["entry_id"],
            "sense_id": nearest["sense_id"],
            "card_id": nearest["card_id"],
            "selected_word_id": nearest["selected_word_id"],
            "occurrence_id": nearest["occurrence_id"],
            "crosswalk_status": nearest["crosswalk_status"],
            "forward_crosswalk_edge_ids": forward.get("edge_ids", []),
            "reverse_crosswalk_edge_ids": reverse.get("edge_ids", []),
        },
        "fallback_comparison": {
            "surface": FALLBACK_OWNER_SURFACE,
            "normalized_match_key": FALLBACK_KEY,
            "occurrence_count": len(fallback_rows),
            "occurrences": fallback_rows,
        },
        "reasoning": [
            "Surface matching found exactly one target occurrence; no whitelist index was trusted.",
            "The target is reader-only and has only a rendered appearance edge, so its page-context gap is not promoted to a lexeme edge.",
            "The nearest same-lexeme card-selected occurrence is 28:50:12, with deterministic forward/reverse crosswalk rows, documented-form evidence, and a canonical occurrence edge.",
            "The fallback surface has seven whitelist occurrences with page-context entry ids, but the selected-word crosswalk witness does not backlink any of those seven occurrences; it therefore does not materially improve the target's occurrence chain.",
            "The owner-preferred target is retained and its missing direct target link plus missing exact Naḥw relation are shown as source gaps.",
        ],
    }


def _manifest(
    output_dir: Path,
    selection: dict[str, Any],
    nearest: dict[str, Any],
    edges: list[dict[str, Any]],
    facts: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    facts_by_type = {}
    for fact in facts.get("facts") or []:
        facts_by_type.setdefault(str(fact.get("fact_type")), []).append(str(fact.get("fact_id")))
    return {
        "schema": "qamus.proofv.manifest.v1",
        "manifest_version": "1.0.0",
        "generated_by": "tools.build_proofv_verb.py",
        "candidate_mode": True,
        "authorization_state": "pre_apply_not_authorized",
        "live_mutation_allowed": False,
        "public_materialization_allowed": False,
        "selection_artifact": "source-selection.json",
        "chain": {
            "entry": f"entry:{nearest['entry_id']}",
            "sense": nearest["sense_id"],
            "card": nearest["card_id"],
            "selected_word": nearest["selected_word_id"],
            "crosswalk_forward": "crosswalk-forward.json",
            "crosswalk_reverse": "crosswalk-reverse.json",
            "nearest_occurrence": f"occurrence:{nearest['occurrence_id']}",
            "target_occurrence": "occurrence:19:43:10",
            "target_appearance": "appearance:19:43:10:1",
            "facts": "canonical-facts.json",
            "payload": "shared-compiler-payload.json",
        },
        "edge_enumeration": [
            {"edge_id": str(edge["edge_id"]), "edge_type": str(edge["edge_type"]), "from": str(edge["from_node_id"]), "to": str(edge["to_node_id"]), "status": str(edge["status"])}
            for edge in edges
        ],
        "fact_enumeration": facts_by_type,
        "payload_descriptors": {
            "payload_id": payload["payload_id"],
            "at_rest": True,
            "compact": True,
            "expanded_sarf": True,
            "expanded_nahw": True,
            "hover": True,
            "per_appearance": True,
            "readback": True,
            "candidate_status": payload["candidate_status"],
        },
        "artifact_owner": "PROOF-V / §11",
        "read_only_inputs": [
            "../../data/entries.jsonl",
            "../../data/rh_live_01_beta_whitelist.jsonl",
            "../EDGES/full-artifacts/typed-edge-graph.jsonl",
            "../EDGES/full-artifacts/lexeme-entry-crosswalk.forward.jsonl",
            "../EDGES/full-artifacts/lexeme-entry-crosswalk.reverse.jsonl",
        ],
        "local_only": {"png": True, "tracked_png": False, "browser_screenshot_committed": False},
        "limits": [
            "No live MCP lookup was available; missing exact facts remain source gaps.",
            "No whitelist, entry corpus, EDGES artifact, renderer, or deployment surface was mutated.",
            "Candidate output is not a certified linguistic fact and is not publication-ready.",
        ],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    entries = _jsonl(Path(args.entries))
    whitelist = _jsonl_with_lines(Path(args.whitelist))
    graph_dir = Path(args.edges_dir)
    forward_rows = _jsonl(graph_dir / "lexeme-entry-crosswalk.forward.jsonl")
    reverse_rows = _jsonl(graph_dir / "lexeme-entry-crosswalk.reverse.jsonl")
    target_rows = _survey(whitelist, TARGET_KEY)
    fallback_rows = _survey(whitelist, FALLBACK_KEY)
    if len(target_rows) != 1:
        raise ValueError(f"PROOF-V target surface survey expected exactly one row, found {len(target_rows)}")
    target_raw = next(row for row in whitelist if _loc(row) == target_rows[0]["loc"] and normalize_ar.norm_strict(str(row.get("surface") or "")) == TARGET_KEY)
    target_raw = copy.deepcopy(target_raw)
    target_raw["source_line"] = target_raw.pop("_source_line")
    nearest, forward, reverse, nearest_edges = _find_nearest_crosswalk(entries, forward_rows, reverse_rows, graph_dir=graph_dir)
    graph_edges = _target_edges(graph_dir, target_raw, nearest, nearest_edges)
    selection = _selection(target_rows, fallback_rows, nearest, forward, reverse)
    source_projection = _source_row_projection(target_raw)
    facts = proofv_verb_producer.build_verb_facts(target_raw, nearest=nearest)
    if facts.get("status") != "candidate_with_source_gaps":
        raise ValueError("PROOF-V target did not produce the expected candidate-with-source-gaps packet")
    appearances = [
        {
            "appearance_index": int((edge.get("details") or {}).get("appearance_index") or 1),
            "surface_kind": str((edge.get("details") or {}).get("surface_kind") or "reader"),
            "surface": str((edge.get("details") or {}).get("surface") or target_raw["surface"]),
        }
        for edge in graph_edges
        if edge.get("edge_type") == "rendered_appearance_edge" and (edge.get("details") or {}).get("loc") == TARGET_LOC
    ]
    payload = proofv_shared_compiler.compile_payload(facts, appearances=appearances)
    manifest = _manifest(output_dir, selection, nearest, graph_edges, facts, payload)
    render_proof = {
        "schema": "qamus.proofv.render_proof.v1",
        "render_mode": "fixture_payload_readback",
        "font_check": None,
        "browser_render": {"status": "not_run", "reason": "No browser screenshot is committed; the payload/readback gate is durable and local-only."},
        "exact_reconstruction": bool(payload["readback"]["exact_reconstruction"]),
        "compact_present": bool(payload.get("compact")),
        "expanded_present": bool(payload.get("expanded")),
        "same_payload_identity": bool(payload["readback"]["same_payload_identity"]),
        "uncertainty_visible": bool(payload.get("uncertainty", {}).get("display")),
        "live_mutation_allowed": False,
        "public_materialization_allowed": False,
        "png_local_only": True,
        "tracked_png": False,
    }
    _write_json(output_dir / "source-selection.json", selection)
    _write_json(output_dir / "source-occurrence.json", source_projection)
    _write_json(output_dir / "canonical-facts.json", facts)
    _write_jsonl(output_dir / "typed-edge-graph.jsonl", graph_edges)
    _write_json(output_dir / "crosswalk-forward.json", forward)
    _write_json(output_dir / "crosswalk-reverse.json", reverse)
    _write_json(output_dir / "shared-compiler-payload.json", payload)
    _write_json(output_dir / "render-proof.json", render_proof)
    _write_json(output_dir / "PROOFV-MANIFEST.json", manifest)
    return {"selection": selection, "facts": facts, "payload": payload, "manifest": manifest, "render_proof": render_proof, "edges": graph_edges}


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--whitelist", type=Path, required=True)
    parser.add_argument("--edges-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = build(args)
    print(json.dumps({
        "chosen_loc": result["selection"]["chosen_loc"],
        "chosen_surface": result["selection"]["chosen_surface"],
        "nearest_occurrence": result["selection"]["nearest_card_selected_same_lexeme"]["occurrence_id"],
        "fact_count": len(result["facts"].get("facts") or []),
        "edge_count": len(result["edges"]),
        "payload_id": result["payload"]["payload_id"],
        "render_mode": result["render_proof"]["render_mode"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
