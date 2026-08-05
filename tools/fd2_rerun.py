"""Run the bounded FD2 producer-aware compiler over explicit input paths.

The corpus and entries are read-only inputs.  They are deliberately accepted
only as command-line paths so an operational rerun cannot silently fall back
to a workspace-specific external location.  All emitted artifacts contain
repo-relative artifact names and candidate-only claims.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Iterable

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools import build_occurrence_appearance_index
from tools import fd_compiler

# Moved-report banner: emitted by the generator so regeneration stays byte-identical.
HISTORICAL_BANNER = ("> **Historical lane report** (moved from the repo root 2026-08-05). Point-in-time evidence; tallies herein are superseded — current state lives in `docs/current-state.yaml` and the generated ledgers. Do not quote numbers from this file.\n\n")



def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            rows.append(value)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _load_occurrence_index(
    corpus_path: Path,
    entries_path: Path,
    occurrence_index_path: Path | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if occurrence_index_path is not None:
        records = _read_jsonl(occurrence_index_path)
        stats = {
            "source": "explicit occurrence index",
            "unique_locations": len(records),
            "total_appearances": sum(int(row.get("appearance_count", 0)) for row in records),
        }
    else:
        result = build_occurrence_appearance_index.build_index(
            _read_jsonl(corpus_path),
            _read_jsonl(entries_path),
        )
        records = result.records
        stats = dict(result.stats)
        stats["source"] = "merged occurrence index built in memory from explicit corpus and entries paths"
    by_loc = {str(row.get("loc")): row for row in records if row.get("loc")}
    return by_loc, stats


def _producer_reach(verdicts: list[dict[str, Any]]) -> dict[str, Any]:
    family_counts = Counter(str(row.get("morphology_family", "")) for row in verdicts)
    fb_counts = Counter(row.get("producer_status", {}).get("F-B") for row in verdicts)
    fc_counts = Counter(row.get("producer_status", {}).get("F-C") for row in verdicts)
    return {
        "rows": len(verdicts),
        "family_counts": dict(sorted(family_counts.items())),
        "F-B": dict(sorted((str(key), value) for key, value in fb_counts.items())),
        "F-C": dict(sorted((str(key), value) for key, value in fc_counts.items())),
    }


def render_markdown(report: dict[str, Any], verdicts: list[dict[str, Any]]) -> str:
    metrics = report["metrics"]
    movement = report["movement"]
    reach = report.get("producer_reach", {})
    lines = [
        "# FD2 455-Row Producer-Aware Rerun",
        "",
        "This is a bounded candidate rerun of the 455 `verified` rows with the calibrated F-B and F-C producers active.",
        "",
        "## Scope and producer reach",
        "",
        f"- Verified rows compiled: **{report['verified_row_count']}**.",
        "- F-B applies only to `clitic_pronoun_compositions` rows; F-C applies only when its exact source-evidence selector and strict contract builder accept.",
        "- Other families retain their prior state.  Guarded abstention is a queue/blocker, not a producer defect.",
        "- Occurrence parity uses the merged occurrence index supplied or built in memory from the explicitly passed corpus and entries paths.",
        "",
        "| Producer | Reach/status |",
        "|---|---:|",
    ]
    for producer in ("F-B", "F-C"):
        statuses = reach.get(producer, {})
        status_text = ", ".join(f"{key}={value}" for key, value in statuses.items()) or "none"
        lines.append(f"| {producer} | {status_text} |")
    family_counts = reach.get("family_counts", {})
    lines.extend([
        "",
        "| Calibrated input family | Rows |",
        "|---|---:|",
    ])
    for family, count in family_counts.items():
        lines.append(f"| `{family}` | {count} |")

    lines.extend([
        "",
        "## Owner metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
    ])
    for key in fd_compiler.FD2_METRIC_KEYS:
        value = metrics.get(key, 0)
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if isinstance(value, (dict, list)) else str(value)
        lines.append(f"| {key} | `{rendered}` |")

    lines.extend([
        "",
        "## Before → after movement",
        "",
        "| Baseline metric | Before | After | Delta |",
        "|---|---:|---:|---:|",
    ])
    for key in fd_compiler.FD2_BASELINE:
        lines.append(
            f"| {key} | {movement['before'][key]} | {movement['after'][key]} | {movement['delta'][key]:+d} |"
        )
    lines.extend([
        "",
        movement["interpretation"],
        "",
        "## Exact blocker and queue routes",
        "",
        "| Primary blocker | Rows |",
        "|---|---:|",
    ])
    for key, value in sorted(report.get("primary_blocker_counts", {}).items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "| Queue | Rows |",
        "|---|---:|",
        f"| source | {metrics['source/scholar queues'].get('source', 0)} |",
        f"| scholar | {metrics['source/scholar queues'].get('scholar', 0)} |",
        f"| both | {metrics['source/scholar queues'].get('both', 0)} |",
        "",
        "## Newly discovered producer defects",
        "",
    ])
    defects = metrics["newly discovered producer defects"].get("items", [])
    if defects:
        lines.extend([
            "| Location | Producer | Code | Evidence |",
            "|---|---|---|---|",
        ])
        for defect in defects:
            detail = str(defect.get("detail", "")).replace("|", "\\|")
            lines.append(f"| `{defect.get('loc', '')}` | {defect.get('producer', '')} | `{defect.get('code', '')}` | {detail} |")
    else:
        lines.append("None discovered in this bounded rerun.")

    lines.extend([
        "",
        "## EXACT NONCLAIMS",
        "",
        "- **No scholarly certification:** `verified` is the supplied structural input state; this rerun does not certify tafsīr, grammar, morphology, or scholarship.",
        "- **Calibration-scope only:** F-B is restricted to the calibrated clitic-pronoun family, and F-C is restricted to rows meeting its calibrated evidence conditions; no scope expansion is claimed.",
        "- **No live effect:** this run performs no whitelist append, restart, publication, deployment, push, release, or live/runtime mutation.",
        "- **No corpus-wide claim:** the movement table describes these 455 verified rows only.",
        "- **Repeated-appearance parity is an index witness:** it proves reuse of a canonical generated payload identity against the merged occurrence index, not live rendered-page coverage.",
        "",
        "## Artifacts",
        "",
        "- `fd2-455-report.json`",
        "- `fd2-455-verdicts.jsonl`",
        "- `fd2-455-verdicts.meta.json`",
        "- `docs/reports/history/2026-07-16-FD2-REPORT.md`",
        "",
    ])
    return "\n".join(lines)


def run_rerun(
    strat_path: Path,
    verdict_path: Path,
    corpus_path: Path,
    entries_path: Path,
    report_path: Path,
    verdicts_path: Path,
    meta_path: Path,
    markdown_path: Path,
    *,
    occurrence_index_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run FD2 and write all four requested artifacts."""

    strat_rows = _read_jsonl(strat_path)
    input_verdict_rows = _read_jsonl(verdict_path)
    corpus_rows = _read_jsonl(corpus_path)
    entries = _read_jsonl(entries_path)
    occurrence_index, occurrence_stats = _load_occurrence_index(
        corpus_path,
        entries_path,
        occurrence_index_path,
    )
    producer_records = fd_compiler.collect_calibrated_producer_records(
        strat_rows,
        input_verdict_rows,
        corpus_rows,
        corpus_source_name=Path(corpus_path).name,
    )
    row_verdicts, report = fd_compiler.compile_fd2_rows(
        strat_rows,
        input_verdict_rows,
        corpus_rows,
        entries,
        occurrence_index,
        fb_records_by_loc=producer_records["fb_records"],
        fc_records_by_loc=producer_records["fc_records"],
        producer_diagnostics=producer_records,
    )
    report["producer_reach"] = _producer_reach(row_verdicts)
    report["occurrence_index"] = {
        "locations": len(occurrence_index),
        "stats": occurrence_stats,
        "external_paths_embedded": False,
    }
    report["input_artifacts"] = {
        "stratification": Path(strat_path).name,
        "verdicts": Path(verdict_path).name,
        "corpus": Path(corpus_path).name,
        "entries": Path(entries_path).name,
    }
    report["live_mutation_allowed"] = False
    report["candidate_only"] = True
    meta = {
        "schema": "qamus.fd2.455_rerun_verdict_meta.v1",
        "artifact": Path(verdicts_path).name,
        "record_type": "row_verdicts",
        "count": len(row_verdicts),
        "generator": "tools.fd2_rerun",
        "scope": "bounded FD2 455-row candidate rerun",
        "candidate_only": True,
        "live_mutation_allowed": False,
    }
    _write_json(report_path, report)
    _write_jsonl(verdicts_path, row_verdicts)
    _write_json(meta_path, meta)
    Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_path).write_text(HISTORICAL_BANNER + render_markdown(report, row_verdicts), encoding="utf-8")
    return report, row_verdicts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strat-455", required=True, type=Path)
    parser.add_argument("--v575-verdicts", required=True, type=Path)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--entries", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--verdicts", required=True, type=Path)
    parser.add_argument("--verdicts-meta", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--occurrence-index", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report, rows = run_rerun(
        args.strat_455,
        args.v575_verdicts,
        args.corpus,
        args.entries,
        args.report,
        args.verdicts,
        args.verdicts_meta,
        args.markdown,
        occurrence_index_path=args.occurrence_index,
    )
    print(f"FD2 rerun wrote {len(rows)} row verdicts; defects={report['metrics']['newly discovered producer defects']['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
