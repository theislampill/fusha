#!/usr/bin/env python3
"""Validate meta-transclusive projection queues and closure boards.

This is the durable Fusha-side guard for the VN-00 ANDON class where a public
page looked "complete" while source-clean sarf/nahw/typed-edge facts were not
actually projected into the hover/color payload.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
COMPLETE_WORDS = ("complete", "handled", "already_clean", "visual_close_ready", "visual_complete")
COMPLETE_WORD_PATTERNS = tuple(
    re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    for word in COMPLETE_WORDS
)
REQUIRED_FAMILIES = {
    "source_clean_fact_available_but_not_projected",
    "function_token_flat",
    "peer_payload_richer_than_current",
    "object_or_possessive_suffix_hidden",
    "root_known_but_hidden",
    "finite_prefix_hidden",
}
REQUIRED_TARGET_AREAS = {"validator", "meta_lattice_projection"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            row["_file"] = str(path)
            row["_line"] = line_no
            rows.append(row)
    return rows


def _split_families(value: Any) -> set[str]:
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value or "").replace(";", ",").split(",")
    return {str(part).strip() for part in parts if str(part).strip()}


def _label(row: dict[str, Any]) -> str:
    file_part = row.get("_file")
    line_part = row.get("_line")
    where = f"{file_part}:{line_part}: " if file_part and line_part else ""
    return f"{where}{row.get('source_key') or row.get('example_page') or row.get('surface') or '<row>'}"


def completion_wording_violation(row: dict[str, Any]) -> bool:
    """Return whether a row claims completion while projection failures remain."""
    if not row.get("projection_failures"):
        return False
    text = json.dumps(row, ensure_ascii=False).lower()
    for pattern in COMPLETE_WORD_PATTERNS:
        for match in pattern.finditer(text):
            prefix = text[:match.start()]
            if re.search(r"\b(?:not|un)[\s_-]*$", prefix):
                continue
            return True
    return False


def validate_board(board_path: Path | None, page_status_paths: Iterable[Path]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if not board_path:
        return errors, {"open_projection_rows": 0}
    board = _read_json(board_path)
    rows: list[dict[str, Any]] = board.get("rows") or []
    open_rows = [row for row in rows if row.get("projection_state") != "projection_clean" or row.get("projection_failures")]
    for row in rows:
        if completion_wording_violation(row):
            errors.append(f"{_label(row)}: completion wording with projection failures")
        if row.get("projection_state") == "projection_clean" and row.get("projection_failures"):
            errors.append(f"{_label(row)}: projection_clean with failures")

    complete_pages: set[str] = set()
    for path in page_status_paths:
        if not path.exists():
            errors.append(f"{path}: page-status file missing")
            continue
        data = _read_json(path) if path.suffix.lower() == ".json" else [_read_jsonl(path)]
        items: list[dict[str, Any]] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, list):
                    items.extend(item)
                elif isinstance(item, dict):
                    items.append(item)
        elif isinstance(data, dict):
            items = [data]
        for item in items:
            if str(item.get("page_status") or "") == "visual_complete":
                complete_pages.add(str(item.get("source_key") or ""))
    failures_by_page = Counter(str(row.get("source_key")) for row in open_rows)
    for page in sorted(complete_pages):
        if failures_by_page.get(page):
            errors.append(f"{page}: page_status visual_complete but {failures_by_page[page]} meta-lattice projection rows remain open")

    return errors, {
        "open_projection_rows": len(open_rows),
        "projection_state_counts": dict(Counter(str(row.get("projection_state")) for row in rows)),
        "projection_failure_counts": dict(Counter(f for row in rows for f in (row.get("projection_failures") or []))),
        "open_rows_by_page": dict(failures_by_page),
    }


def _is_family_summary(row: dict[str, Any]) -> bool:
    return (
        str(row.get("loc") or "") == "multiple"
        or str(row.get("surface") or "").startswith("multiple")
        or bool(row.get("example_pages"))
    ) and bool(row.get("proposed_file_or_queue"))


def validate_queue(
    queue_path: Path | None,
    typed_edge_queue_path: Path | None,
    *,
    require_exact_rows: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    if queue_path:
        rows.extend(_read_jsonl(queue_path))
    if typed_edge_queue_path:
        rows.extend(_read_jsonl(typed_edge_queue_path))
    if not rows:
        return errors, {"queue_rows": 0, "failure_family_counts": {}}

    family_counts: Counter[str] = Counter()
    target_area_counts: Counter[str] = Counter()
    missing_group_key = 0
    missing_hash_or_qword = 0
    family_summary_rows = 0
    exact_family_counts: Counter[str] = Counter()
    for row in rows:
        families = _split_families(row.get("failure_family"))
        for family in families:
            family_counts[family] += 1
        for area in row.get("fusha_target_area") or []:
            target_area_counts[str(area)] += 1
        status = str(row.get("status") or "")
        if status == "queued":
            group_key = row.get("exact_transclusion_group_key")
            qword_row_id = row.get("qword_row_id")
            exact = bool(group_key or qword_row_id or row.get("public_payload_hash"))
            if exact:
                for family in families:
                    exact_family_counts[family] += 1
            elif _is_family_summary(row) and not require_exact_rows:
                family_summary_rows += 1
            else:
                missing_group_key += 1
                errors.append(f"{_label(row)}: queued projection row lacks exact_transclusion_group_key or qword_row_id")
                if not (row.get("public_payload_hash") or row.get("qword_row_id") or row.get("exact_transclusion_group_key")):
                    missing_hash_or_qword += 1
                    errors.append(f"{_label(row)}: queued projection row lacks public payload hash, qword id, and exact group key")
        if families & REQUIRED_FAMILIES:
            areas = set(row.get("fusha_target_area") or [])
            if not (areas & REQUIRED_TARGET_AREAS or "typed_edge_transclusion" in areas or "sarf" in areas or "nahw" in areas):
                errors.append(f"{_label(row)}: critical projection family lacks validator/meta/sarf/nahw target area")

    missing_families = sorted(REQUIRED_FAMILIES - set(family_counts))
    for family in missing_families:
        errors.append(f"required failure family missing from projection queues: {family}")
    if require_exact_rows:
        missing_exact = sorted(REQUIRED_FAMILIES - set(exact_family_counts))
        for family in missing_exact:
            errors.append(f"required failure family lacks exact projection row: {family}")

    return errors, {
        "queue_rows": len(rows),
        "failure_family_counts": dict(family_counts),
        "exact_failure_family_counts": dict(exact_family_counts),
        "target_area_counts": dict(target_area_counts),
        "family_summary_rows": family_summary_rows,
        "missing_group_key_or_qword_rows": missing_group_key,
        "missing_hash_or_qword_rows": missing_hash_or_qword,
    }


def run_validation(
    *,
    board: Path | None,
    page_status: list[Path],
    queue: Path | None,
    typed_edge_queue: Path | None,
    allow_open: bool,
    require_exact_rows: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    board_errors, board_report = validate_board(board, page_status)
    queue_errors, queue_report = validate_queue(queue, typed_edge_queue, require_exact_rows=require_exact_rows)
    errors.extend(board_errors)
    errors.extend(queue_errors)
    open_projection_rows = board_report.get("open_projection_rows", 0)
    if open_projection_rows and not allow_open:
        errors.append(f"{open_projection_rows} open projection rows remain; pass --allow-open for diagnostic mode only")
    return {
        "schema": "qamus/validate-meta-transclusion-projection-report@1",
        "ok": not errors,
        "errors": errors,
        **board_report,
        **queue_report,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        board = base / "board.json"
        status = base / "status.jsonl"
        queue = base / "queue.jsonl"
        typed = base / "typed.jsonl"
        board.write_text(
            json.dumps(
                {
                    "rows": [
                        {"source_key": "v001", "projection_state": "visual_complete", "projection_failures": ["root_known_but_hidden"]},
                        {"source_key": "v002", "projection_state": "projection_clean", "projection_failures": ["function_token_flat"]},
                        {"source_key": "v003", "projection_state": "reopened_not_complete", "projection_failures": ["x"]},
                        {"source_key": "v004", "projection_state": "unhandled", "projection_failures": ["x"]},
                        {"source_key": "v005", "projection_state": "needs_work", "projection_failures": ["x"], "note": "page NOT complete"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        status.write_text(json.dumps({"source_key": "v001", "page_status": "visual_complete"}, ensure_ascii=False) + "\n", encoding="utf-8")
        family_rows = []
        for family in sorted(REQUIRED_FAMILIES):
            family_rows.append(
                {
                    "status": "queued",
                    "failure_family": family,
                    "fusha_target_area": ["validator", "meta_lattice_projection"],
                    "qword_row_id": f"llx-qword-aaaaaaaaaaaa-01-01-{len(family_rows)+1:03d}",
                    "surface": family,
                }
            )
        family_rows.append(
            {
                "status": "queued",
                "failure_family": "article_host_undersegmented",
                "fusha_target_area": ["validator"],
                "loc": "multiple",
                "surface": "multiple article hosts",
                "example_pages": ["VN-00"],
                "proposed_file_or_queue": "family-summary-index",
            }
        )
        queue.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in family_rows) + "\n", encoding="utf-8")
        typed.write_text("", encoding="utf-8")
        failing = run_validation(board=board, page_status=[status], queue=queue, typed_edge_queue=typed, allow_open=False)
        clean_board = base / "clean-board.json"
        clean_status = base / "clean-status.jsonl"
        clean_board.write_text(json.dumps({"rows": [{"source_key": "v003", "projection_state": "projection_clean", "projection_failures": []}]}, ensure_ascii=False), encoding="utf-8")
        clean_status.write_text(json.dumps({"source_key": "v003", "page_status": "needs_work"}, ensure_ascii=False) + "\n", encoding="utf-8")
        passing = run_validation(board=clean_board, page_status=[clean_status], queue=queue, typed_edge_queue=typed, allow_open=False)
        wording_errors = [err for err in failing["errors"] if "completion wording" in err]
        ok = (
            (not failing["ok"])
            and passing["ok"]
            and len(wording_errors) == 1
            and wording_errors[0].startswith("v001:")
        )
        print(json.dumps({"ok": ok, "failing_errors": failing["errors"], "passing": passing}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path)
    parser.add_argument("--page-status", action="append", default=[], type=Path)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--typed-edge-queue", type=Path)
    parser.add_argument("--allow-open", action="store_true", help="Diagnostic mode: report open board rows without failing solely for openness.")
    parser.add_argument("--require-exact-rows", action="store_true", help="Fail family-summary rows unless each required family also has exact qword/group payload rows.")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    report = run_validation(
        board=args.board,
        page_status=args.page_status,
        queue=args.queue,
        typed_edge_queue=args.typed_edge_queue,
        allow_open=args.allow_open,
        require_exact_rows=args.require_exact_rows,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
