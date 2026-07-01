#!/usr/bin/env python3
"""Validate the sharded largelexicon table reader contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_table_reader import LargelexiconQwordTable


ROOT = Path(__file__).resolve().parents[1]


def validate() -> list[str]:
    errors: list[str] = []
    table = LargelexiconQwordTable.from_repo(ROOT)
    summary = table.summary()
    if summary.get("row_count", 0) < 100000:
        errors.append("reader row_count unexpectedly low")
    if summary.get("qamus_entry_count") != 2092:
        errors.append(f"reader qamus_entry_count expected 2092, got {summary.get('qamus_entry_count')}")
    if summary.get("entries_with_qword_rows") != summary.get("entry_count"):
        errors.append("reader entries_with_qword_rows must match indexed entry_count")
    if summary.get("entry_count", 0) < 2000:
        errors.append(f"reader indexed entry_count unexpectedly low: {summary.get('entry_count')}")
    first_rows = list(table.iter_rows(limit=3))
    if len(first_rows) != 3:
        errors.append("reader iter_rows(limit=3) did not return three rows")
    elif not all(row.get("row_id") for row in first_rows):
        errors.append("reader iter_rows returned rows without row_id")
    entry_rows = list(table.rows_for_entry("00107b99a50e"))
    if len(entry_rows) < 3:
        errors.append("reader rows_for_entry did not return expected seed entry rows")
    looked_up = table.row_by_id("llx-qword-00107b99a50e-01-01-001")
    if not looked_up or looked_up.get("visible_surface") != "كَٱلَّذِينَ":
        errors.append("reader row_by_id failed for stable seed row")
    missing = table.row_by_id("llx-qword-deadbeef0000-01-01-001")
    if missing is not None:
        errors.append("reader row_by_id must return None for unknown row")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon sharded table reader.")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
