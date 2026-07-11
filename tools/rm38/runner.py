#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
for entry in (str(ROOT), str(TOOLS)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from tools.fusha_clitic_splitter import split_clitics
from tools.fusha_morph_analyze import analyze_surface
from tools.fusha_morphology_lattice import build_morphology_lattice
from tools.rm38.alignment import align_monotonic_spans
from tools.rm38.load_eqtb import load_eqtb
from tools.rm38.load_quranmorph import load_quranmorph
from tools.rm38.metrics import derive_score_bin_edges, evaluate_layer
from tools.rm38.pins import PinError, load_pins
from tools.rm38.validate import validate_no_collapsed_score

HERE = Path(__file__).resolve().parent
LAYERS = ("segmentation", "pos", "lemma", "root", "features", "governor")


def split_for_unit(unit_id: str, seed: str) -> str:
    digest = hashlib.sha256(f"{seed}\0{unit_id}".encode("utf-8")).digest()
    return "dev" if int.from_bytes(digest[:8], "big") % 100 < 20 else "test"


def _voweled(surface: str) -> bool:
    return any(unicodedata.category(ch) == "Mn" for ch in surface)


def _engine_output(surface: str, token_id: str) -> dict[str, Any]:
    segment_candidates = split_clitics(surface)
    smoke_candidates = analyze_surface(surface, "smoke")
    if smoke_candidates:
        candidates = smoke_candidates
    else:
        lattice = build_morphology_lattice(
            token_id, surface, segment_candidates, _voweled(surface), source_addressed=False
        )
        candidates = lattice["candidates"]
    top_segments = (segment_candidates[0].get("segments") if segment_candidates else None) or [
        {"surface": surface, "role": "stem"}
    ]
    resolved = len(segment_candidates) == 1 and len(candidates) == 1
    return {
        "segments": [{"surface": item.get("surface", ""), "role": item.get("role")} for item in top_segments],
        "candidates": candidates,
        "status": "resolved" if resolved else "pending",
        "governor": None,
        "relation": None,
    }


def _evaluation_rows(gold_rows: list[dict[str, Any]], source: str, split: str, seed: str) -> list[dict[str, Any]]:
    output = []
    for index, gold in enumerate(gold_rows, 1):
        surface = str(gold.get("surface") or "")
        unit_id = str(gold.get("unit_id") or "")
        if not surface or not unit_id:
            raise ValueError(f"{source} row {index} lacks a surface or stable ayah/unit id")
        if split_for_unit(unit_id, seed) != split:
            continue
        token_id = str(gold.get("token_id") or f"{unit_id}:{index}")
        output.append({
            "unit_id": unit_id,
            "token_id": token_id,
            "surface": surface,
            "engine": _engine_output(surface, token_id),
            source: gold,
        })
    return output


def attach_other_gold(primary_rows: list[dict[str, Any]], other_rows: list[dict[str, Any]], other_source: str) -> None:
    """Strict-align another oracle by ayah and attach only one-to-one norm_strict spans."""
    primary_by_unit: dict[str, list[dict[str, Any]]] = {}
    other_by_unit: dict[str, list[dict[str, Any]]] = {}
    for row in primary_rows:
        primary_by_unit.setdefault(str(row.get("unit_id") or ""), []).append(row)
    for row in other_rows:
        other_by_unit.setdefault(str(row.get("unit_id") or ""), []).append(row)
    for unit_id, primary_unit in primary_by_unit.items():
        other_unit = other_by_unit.get(unit_id)
        if not unit_id or not other_unit:
            continue
        for row in primary_unit:
            row["_inter_gold_unit_present"] = True
        result = align_monotonic_spans(primary_unit, other_unit)
        for pair in result["pairs"]:
            other_row = other_unit[pair["gold_index"]]
            primary_unit[pair["engine_index"]][other_source] = other_row.get(other_source, other_row)
        for item in result["quarantined"]:
            for index in item.get("engine", []):
                if 0 <= index < len(primary_unit):
                    primary_unit[index]["_inter_gold_unalignable"] = True


def run_evaluation(args: argparse.Namespace) -> list[Path]:
    pins = load_pins(Path(args.pins))
    quranmorph = load_quranmorph(Path(args.quranmorph), pins["sources"]["quranmorph"])
    eqtb = load_eqtb(Path(args.eqtb), pins["sources"]["eqtb"])
    requested_layers = LAYERS if args.layer == "all" else (args.layer,)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    source_rows = {
        "quranmorph": _evaluation_rows(quranmorph, "quranmorph", args.split, pins["split_seed"]),
        "eqtb": _evaluation_rows(eqtb, "eqtb", args.split, pins["split_seed"]),
    }
    attach_other_gold(source_rows["quranmorph"], source_rows["eqtb"], "eqtb")
    attach_other_gold(source_rows["eqtb"], source_rows["quranmorph"], "quranmorph")
    dev_rows = source_rows
    if args.split == "test":
        dev_rows = {
            "quranmorph": _evaluation_rows(quranmorph, "quranmorph", "dev", pins["split_seed"]),
            "eqtb": _evaluation_rows(eqtb, "eqtb", "dev", pins["split_seed"]),
        }
        attach_other_gold(dev_rows["quranmorph"], dev_rows["eqtb"], "eqtb")
        attach_other_gold(dev_rows["eqtb"], dev_rows["quranmorph"], "quranmorph")
    for source, rows in source_rows.items():
        source_pin = pins["sources"][source]
        for layer in requested_layers:
            report = evaluate_layer(
                rows,
                source=source,
                layer=layer,
                split=args.split,
                citation=source_pin["attribution"],
                license_name=source_pin["license"],
                score_bin_edges=derive_score_bin_edges(dev_rows[source]),
                score_edge_source="dev",
            )
            validate_no_collapsed_score(report)
            path = out_dir / f"{source}-{layer}-report.json"
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            written.append(path)
    return written


def _fixture_rows() -> list[dict[str, Any]]:
    path = HERE / "fixtures" / "synthetic-20.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _self_test() -> None:
    rows = _fixture_rows()
    if len(rows) != 20:
        raise AssertionError("synthetic fixture row count drifted")
    root = evaluate_layer(rows[:1], source="quranmorph", layer="root", split="dev")
    if root["buckets"]["abstention"] != 1 or root["buckets"]["root_mismatch"]:
        raise AssertionError("abstention accounting drifted")
    pos = evaluate_layer(rows[7:8], source="quranmorph", layer="pos", split="dev")
    if pos["candidate_recall@1"]["value"] != 0.0 or pos["candidate_recall@k"]["value"] != 1.0:
        raise AssertionError("candidate recall accounting drifted")
    governor = evaluate_layer(rows[6:7], source="eqtb", layer="governor", split="test")
    if governor.get("eqtb_syntax_is_partly_dl_silver") is not True:
        raise AssertionError("EQTB silver flag missing")
    validate_no_collapsed_score({"reports": [root, pos, governor]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RM-38 layer-wise external-gold evaluation runner.")
    parser.add_argument("--quranmorph", help="user-local QuranMorph file")
    parser.add_argument("--eqtb", help="user-local EQTB file")
    parser.add_argument("--pins", default=str(HERE / "data-pins.json"), help="tracked SHA-256 pins file")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--layer", choices=(*LAYERS, "all"), default="all")
    parser.add_argument("--out", default=str(ROOT / "out" / "rm38"))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--emit-fixture", help="copy the synthetic mini-fixture to this path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.emit_fixture:
            destination = Path(args.emit_fixture)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE / "fixtures" / "synthetic-20.jsonl", destination)
        if args.self_test:
            _self_test()
            print("RM-38 evaluation runner self-test OK")
            return 0
        if not args.quranmorph or not args.eqtb:
            raise ValueError("--quranmorph and --eqtb are required unless --self-test is used")
        written = run_evaluation(args)
        print(json.dumps({"written": [str(path) for path in written]}, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, PinError, AssertionError, json.JSONDecodeError) as exc:
        print(f"RM-38 evaluation refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
