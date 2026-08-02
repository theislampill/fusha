#!/usr/bin/env python3
"""Validate the sharded largelexicon table reader contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import promote_largelexicon_target_schema as promoter
from largelexicon_table_reader import TARGET_FAMILIES, LargelexiconQwordTable, LargelexiconTargetTables


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
    errors.extend(validate_target_reader())
    return errors


def validate_target_reader() -> list[str]:
    """The target reader must open only behind the freshness gate and fail closed."""

    errors: list[str] = []
    try:
        target = LargelexiconTargetTables.open()
    except promoter.PromotionError as error:
        return ["target reader refused the committed release: " + str(error)]
    summary = target.summary()
    families = summary.get("families") or {}
    if set(families) != set(TARGET_FAMILIES):
        errors.append("target reader does not expose exactly the five target families")
    for name, item in sorted(families.items()):
        counts = item.get("disposition_counts") or {}
        if item.get("carried_row_count") != counts.get("carried"):
            errors.append(f"{name}: reader carried_row_count disagrees with the release dispositions")
        if not str(item.get("target_row_schema", "")).endswith("@2"):
            errors.append(f"{name}: reader exposes a non-target row schema")
    if set(target.dependency_hashes()) != set(TARGET_FAMILIES):
        errors.append("target reader dependency hashes do not cover every family")
    try:
        target.carried("not-a-family")
    except KeyError:
        pass
    else:
        errors.append("target reader accepted an unknown family")
    stale = json.loads(json.dumps(target.release))
    stale["tables"]["lemma-source"]["validation"]["violation_rows"] = 3
    if not promoter.release_blockers(stale):
        errors.append("target reader gate accepts a validation-red release")
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
