#!/usr/bin/env python3
"""Project largelexicon Mode A worklist rows into candidate/packet rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_mode_a import ALLOWED_QG_CLASSES
from fusha_standalone_parse import parse_text
from largelexicon_common import PUBLIC_BOUNDARY, read_jsonl, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "qamus" / "examples" / "mode_a_all_qword" / "largelexicon-qamus-mode-a-worklist.sample.jsonl"
DEFAULT_OUT = ROOT / "qamus" / "examples" / "largelexicon" / "hover-candidates.sample.jsonl"


def _project(row: dict) -> dict:
    parsed = parse_text(row["visible_surface"], document_id=row["row_id"], db="largelexicon")
    token = (parsed.get("tokens") or [{}])[0]
    segments = token.get("qg_segments") or []
    segment_surface = "".join(seg.get("surface", "") for seg in segments)
    parser_gate = token.get("confidence_gate")
    missing_source = not row.get("canonical_quran_loc") or not row.get("canonical_wbw_loc")
    bad_classes = sorted({seg.get("class") for seg in segments if seg.get("class") not in ALLOWED_QG_CLASSES})
    if bad_classes:
        status = "validator_packet"
        route = "executor_validator_patch_ready"
    elif missing_source:
        status = "source_crosswalk_packet"
        route = "executor_source_crosswalk_patch_ready"
    elif parser_gate in {"likely_from_internal_pattern", "pending_context"}:
        status = "candidate_for_executor_validation"
        route = "executor_validation_queue"
    else:
        status = "parser_packet"
        route = "executor_parser_or_sarf_nahw_packet_ready"
    return {
        "schema": "qamus/largelexicon-hover-candidate@1",
        "row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "qword_index": row["qword_index"],
        "visible_surface": row["visible_surface"],
        "segment_surface": segment_surface,
        "segments": segments,
        "qg_classes": [seg.get("class") for seg in segments],
        "token_contribution": (token.get("hover_preview") or {}).get("token_contribution_gloss"),
        "parser_gate": parser_gate,
        "status": status,
        "route": route,
        "canonical_quran_loc": row.get("canonical_quran_loc"),
        "canonical_wbw_loc": row.get("canonical_wbw_loc"),
        "source_crosswalk_required": missing_source,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "live_mutation_allowed": False,
        "claim": "candidate or packet for Qamus executor; not live Qamus progress",
    }


def project(input_path: Path, output_path: Path) -> dict:
    rows = read_jsonl(input_path)
    projected = [_project(row) for row in rows]
    write_jsonl(output_path, projected)
    counts: dict[str, int] = {}
    for row in projected:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    try:
        out = str(output_path.relative_to(ROOT))
    except ValueError:
        out = str(output_path)
    return {"rows": len(projected), "counts": counts, "out": out}


def main() -> int:
    parser = argparse.ArgumentParser(description="Project largelexicon Qamus hover candidates.")
    parser.add_argument("--input", default=str(DEFAULT_IN))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    result = project(Path(args.input), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
