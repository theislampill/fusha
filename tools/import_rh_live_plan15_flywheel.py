"""Import RH-LIVE Plan 15 parser-gap route packets as public-safe samples.

The input bundle is an executor-local artifact and may contain private local
paths. This tool reads that bundle, strips executor provenance, and emits a
small Fusha sample plus meta file. The sample is a flywheel queue, not a live
Qamus payload and not a parser-completeness claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "qamus" / "examples" / "rh_live_plan15_parser_flywheel.sample.jsonl"
DEFAULT_META = ROOT / "qamus" / "examples" / "rh_live_plan15_parser_flywheel.sample.meta.json"
SCHEMA = "qamus/flywheel-artifact@1"

PRIVATE_RE = re.compile(
    r"(?:[A-Za-z]:\\|/srv/|qamus\.dawah\.wiki|ssh|password|secret|api[_-]?key|bearer|BEGIN .*PRIVATE)",
    re.IGNORECASE,
)

ROUTE_MAP: dict[str, dict[str, Any]] = {
    "lexicon_entry_needed": {
        "routes": ["parser", "sarf", "qamus_mode_a_validator"],
        "lesson": "Parser produced only partial structure for {surface}; queue a Qamus-derived lexicon or stem fact instead of guessing a root.",
        "unlock": "populate reusable lemma/root/stem evidence for repeated RH-LIVE qwords with the same source-addressed pattern",
    },
    "stem_entry_needed": {
        "routes": ["parser", "sarf", "qamus_mode_a_validator"],
        "lesson": "Parser did not have a certified stem entry for {surface}; queue the exact visible stem and inflection pieces instead of collapsing the token to a broad gloss.",
        "unlock": "populate reusable stem entries and morphology compatibility facts for repeated RH-LIVE qwords with the same segment signature",
    },
    "governor_irab_fixture_needed": {
        "routes": ["parser", "nahw", "qamus_mode_a_validator"],
        "lesson": "{surface} needs source-addressed governor/i'rab reasoning before the hover can be certified.",
        "unlock": "turn fixture-level governor gaps into reusable nahw and i'rab validation cases",
    },
    "parser_interface_ok": {
        "routes": ["parser", "qamus_mode_a_validator"],
        "lesson": "Parser structure for {surface} is useful as a gate/factory interface, but live coverage still needs Qamus validation.",
        "unlock": "reuse parser-known segment and qg projection checks without claiming arbitrary-text parser completeness",
    },
    "particle_function_rule_needed": {
        "routes": ["parser", "nahw", "qamus_mode_a_validator"],
        "lesson": "{surface} is a function-token cluster; queue a function-specific particle rule/eval instead of a generic gloss.",
        "unlock": "convert repeated particle-function clusters into a bulk-safe nahw factory lane",
    },
    "pattern_rule_needed": {
        "routes": ["parser", "sarf", "qamus_mode_a_validator"],
        "lesson": "{surface} needs a reusable morphology pattern or compatibility rule before bulk RH-LIVE reuse.",
        "unlock": "promote repeated morphology clusters into a reusable sarf parser rule",
    },
    "proper_name_no_root_needed": {
        "routes": ["parser", "sarf", "qamus_mode_a_validator"],
        "lesson": "{surface} needs explicit proper-name/no-root handling; do not fabricate a root.",
        "unlock": "teach no-root proper-name handling as a reusable parser and sarf fixture",
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSONL: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_fusha_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
        )
    except OSError:
        return None
    commit = proc.stdout.strip()
    if proc.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        return None
    return commit


def safe_id(value: Any, fallback: str) -> str:
    raw = str(value or fallback)
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "-", raw).strip("-")
    return cleaned or fallback


def card_id(row: dict[str, Any]) -> str:
    source_key = safe_id(row.get("source_key") or row.get("entry_id"), "unknown-entry")
    ref = safe_id(row.get("card_ref"), "unknown-ref")
    index = safe_id(row.get("card_index"), "x")
    return f"{source_key}-card-{index}-{ref}"


def row_id(row: dict[str, Any], route: str, index: int) -> str:
    source_key = safe_id(row.get("source_key") or row.get("entry_id"), "unknown-entry")
    loc = safe_id(row.get("loc"), f"row-{index}")
    return f"plan15-{route}-{source_key}-{loc}-{index}"


def sanitize_segment(segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "class": segment.get("class"),
        "label": segment.get("label"),
        "role": segment.get("role"),
        "surface": segment.get("surface"),
    }


def sanitize_segments_needed(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    needed: list[str] = []
    for item in raw:
        if isinstance(item, str):
            needed.append(item)
            continue
        if isinstance(item, dict):
            parts = []
            for key in ("role", "class", "surface"):
                value = item.get(key)
                if value:
                    parts.append(f"{key}={value}")
            if parts:
                needed.append(";".join(parts))
            continue
        if item is not None:
            needed.append(str(item))
    return needed


def make_artifact(row: dict[str, Any], route: str, index: int) -> dict[str, Any]:
    mapping = ROUTE_MAP[route]
    surface = str(row.get("surface") or row.get("loc") or "this qword")
    artifact = {
        "schema": SCHEMA,
        "row_id": row_id(row, route, index),
        "entry_id": safe_id(row.get("source_key") or row.get("entry_id"), "unknown-entry"),
        "card_id": card_id(row),
        "routes": mapping["routes"],
        "reusable_lesson": mapping["lesson"].format(surface=surface),
        "future_unlock": mapping["unlock"],
        "flywheel_route": route,
        "scope": row.get("scope"),
        "loc": row.get("loc"),
        "surface": surface,
        "parser_status": row.get("parser_status"),
        "root_null": row.get("root_null"),
        "lemma_null": row.get("lemma_null"),
        "confidence_gate": row.get("confidence_gate"),
        "segments_found": [sanitize_segment(s) for s in row.get("segments_found", [])],
        "segments_needed": sanitize_segments_needed(row.get("segments_needed", [])),
        "qg_classes": row.get("row_qg_classes", []),
        "claim_boundary": {
            "live_qamus_payload": False,
            "arbitrary_text_parser_claim": False,
            "parser_oracle_claim": False,
        },
    }
    return artifact


def validate_artifact(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["schema", "row_id", "entry_id", "card_id", "routes", "reusable_lesson", "future_unlock"]
    for key in required:
        if not row.get(key):
            errors.append(f"{row.get('row_id', '<no-row-id>')}: missing {key}")
    if row.get("schema") != SCHEMA:
        errors.append(f"{row.get('row_id')}: wrong schema {row.get('schema')!r}")
    text = json.dumps(row, ensure_ascii=False, sort_keys=True)
    if PRIVATE_RE.search(text):
        errors.append(f"{row.get('row_id')}: private path/secret pattern leaked")
    return errors


def resolve_under_root(path: Path) -> Path:
    if path.is_absolute():
        return path
    return ROOT / path


def resolve_route_file(route_summary: Path, raw_path: str) -> Path:
    route_path = Path(raw_path)
    if route_path.is_absolute():
        return route_path
    for base in (route_summary.parent, *route_summary.parent.parents, ROOT, Path.cwd()):
        candidate = base / route_path
        if candidate.exists():
            return candidate
    return route_summary.parent / route_path


def import_samples(
    route_summary: Path,
    output_jsonl: Path,
    meta_json: Path,
    sample_per_route: int,
    all_rows: bool,
) -> int:
    output_jsonl = resolve_under_root(output_jsonl)
    meta_json = resolve_under_root(meta_json)
    summary = read_json(route_summary)
    route_files = summary.get("route_files", {})
    route_counts = summary.get("route_counts", {})
    rows: list[dict[str, Any]] = []
    sampled_counts: Counter[str] = Counter()

    for route in ROUTE_MAP:
        file_info = route_files.get(route)
        if not file_info:
            continue
        route_path = resolve_route_file(route_summary, file_info["path"])
        if not route_path.exists():
            raise SystemExit(f"route file missing for {route}: {route_path}")
        for index, row in enumerate(iter_jsonl(route_path), 1):
            if not all_rows and sampled_counts[route] >= sample_per_route:
                break
            rows.append(make_artifact(row, route, index))
            sampled_counts[route] += 1

    errors = [error for row in rows for error in validate_artifact(row)]
    if errors:
        for error in errors:
            print(error)
        return 1

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    meta = {
        "schema": "qamus/rh-live-plan15-parser-flywheel-sample-meta@1",
        "generator": "tools/import_rh_live_plan15_flywheel.py",
        "fusha_commit": current_fusha_commit(),
        "input_summary_sha256": sha256_file(route_summary),
        "route_counts": route_counts,
        "sample_counts": dict(sampled_counts),
        "sample_mode": "all_rows" if all_rows else "sample",
        "sample_rows": len(rows),
        "claim_boundary": {
            "live_qamus_payload": False,
            "live_qamus_coverage_claim": False,
            "arbitrary_text_parser_claim": False,
            "parser_oracle_claim": False,
            "raw_executor_paths_vendored": False,
        },
        "output_jsonl": output_jsonl.relative_to(ROOT).as_posix(),
    }
    meta_json.parent.mkdir(parents=True, exist_ok=True)
    meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output": output_jsonl.relative_to(ROOT).as_posix(),
                "meta": meta_json.relative_to(ROOT).as_posix(),
                "sample_rows": len(rows),
                "sample_counts": dict(sampled_counts),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route-summary", required=True, type=Path)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--meta-json", default=DEFAULT_META, type=Path)
    parser.add_argument("--sample-per-route", default=3, type=int)
    parser.add_argument("--all-rows", action="store_true")
    args = parser.parse_args()

    return import_samples(args.route_summary, args.output_jsonl, args.meta_json, args.sample_per_route, args.all_rows)


if __name__ == "__main__":
    raise SystemExit(main())
