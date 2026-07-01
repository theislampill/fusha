#!/usr/bin/env python3
"""Validate largelexicon source inventory and source-clean sample ledgers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import (
    ALLOWLIST,
    FORM_FULL,
    FORM_SAMPLE,
    FULL_TABLE_META,
    LEMMA_FULL,
    LEMMA_SAMPLE,
    QWORD_DENOMINATOR_ENTRY_INDEX,
    QWORD_DENOMINATOR_FULL,
    QWORD_DENOMINATOR_MANIFEST,
    QWORD_DENOMINATOR_SOURCE_REPAIR,
    REPORT_DIR,
    STEM_FULL,
    public_boundary_errors,
    read_jsonl,
)
from validate_largelexicon_table_manifest import validate as validate_qword_manifest


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPORT_DIR / "largelexicon-source-inventory.json"
FULL_JSONL_TABLES = [LEMMA_FULL, FORM_FULL, STEM_FULL]
FULL_TABLE_ARTIFACTS = [
    *FULL_JSONL_TABLES,
    QWORD_DENOMINATOR_MANIFEST,
    QWORD_DENOMINATOR_ENTRY_INDEX,
    QWORD_DENOMINATOR_SOURCE_REPAIR,
]


def _validate_rows(path: Path, rows: list[dict], minimum_rows: int, schema: str, errors: list[str]) -> None:
    if len(rows) < minimum_rows:
        errors.append(f"{path.relative_to(ROOT)}: expected at least {minimum_rows} rows, got {len(rows)}")
    row_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        label = f"{path.name}:{index}"
        if row.get("schema") != schema:
            errors.append(f"{label}: schema mismatch {row.get('schema')!r}")
        errors.extend(public_boundary_errors(row, label))
        if row.get("source_status") not in {"qamus_current_authored", None}:
            errors.append(f"{label}: source_status must be qamus_current_authored when present")
        if row.get("source") not in {"qamus_current_authored", None}:
            errors.append(f"{label}: source must be qamus_current_authored when present")
        if row.get("live_mutation_allowed") is not None and row.get("live_mutation_allowed") is not False:
            errors.append(f"{label}: live_mutation_allowed must be false when present")
        unique_id = row.get("row_id") or row.get("stem_id") or row.get("form_id") or row.get("entry_id")
        if unique_id:
            if unique_id in row_ids:
                errors.append(f"{label}: duplicate id {unique_id}")
            row_ids.add(unique_id)


def validate() -> list[str]:
    errors: list[str] = []
    for path in [INVENTORY, LEMMA_SAMPLE, FORM_SAMPLE, ALLOWLIST, FULL_TABLE_META, *FULL_TABLE_ARTIFACTS]:
        if not path.exists():
            errors.append(f"missing required largelexicon artifact: {path.relative_to(ROOT)}")
    if QWORD_DENOMINATOR_FULL.exists():
        errors.append(f"{QWORD_DENOMINATOR_FULL.relative_to(ROOT)} must not be committed; use the sharded manifest")
    if errors:
        return errors
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if inv.get("schema") != "fusha/largelexicon/source-inventory@1":
        errors.append("inventory schema mismatch")
    counts = inv.get("counts") or {}
    if counts.get("entries") != 2092:
        errors.append(f"expected 2092 Qamus entries, got {counts.get('entries')}")
    if counts.get("listed_forms", 0) < 7000:
        errors.append("listed_forms unexpectedly low")
    if "claim_boundary" not in inv:
        errors.append("inventory missing claim_boundary")
    lemma_rows = read_jsonl(LEMMA_SAMPLE)
    form_rows = read_jsonl(FORM_SAMPLE)
    if len(lemma_rows) < 50:
        errors.append("lemma sample must contain at least 50 rows")
    if not form_rows:
        errors.append("form sample is empty")
    for index, row in enumerate(lemma_rows + form_rows, start=1):
        label = f"sample:{index}"
        errors.extend(public_boundary_errors(row, label))
        if row.get("source_status") != "qamus_current_authored":
            errors.append(f"{label}: source_status must be qamus_current_authored")
        if not row.get("entry_id"):
            errors.append(f"{label}: missing entry_id")
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    allowed = {table["path"]: table for table in allowlist.get("tables") or []}
    for path in FULL_JSONL_TABLES:
        rel = path.relative_to(ROOT).as_posix()
        table = allowed.get(rel)
        if not table:
            errors.append(f"{rel}: not present in source-clean table allowlist")
            continue
        if table.get("commit_allowed") is not True:
            errors.append(f"{rel}: allowlist must explicitly set commit_allowed=true")
        if table.get("raw_external_allowed") is not False:
            errors.append(f"{rel}: allowlist must explicitly set raw_external_allowed=false")
        _validate_rows(path, read_jsonl(path), table.get("minimum_rows", 1), table["schema"], errors)
    qword_rel = QWORD_DENOMINATOR_MANIFEST.relative_to(ROOT).as_posix()
    qword_table = allowed.get(qword_rel)
    if not qword_table:
        errors.append(f"{qword_rel}: not present in source-clean table allowlist")
    else:
        if qword_table.get("storage") != "sharded_jsonl_manifest":
            errors.append(f"{qword_rel}: allowlist storage must be sharded_jsonl_manifest")
        if qword_table.get("entry_index_path") != QWORD_DENOMINATOR_ENTRY_INDEX.relative_to(ROOT).as_posix():
            errors.append(f"{qword_rel}: allowlist entry_index_path mismatch")
        if qword_table.get("commit_allowed") is not True:
            errors.append(f"{qword_rel}: allowlist must explicitly set commit_allowed=true")
        if qword_table.get("raw_external_allowed") is not False:
            errors.append(f"{qword_rel}: allowlist must explicitly set raw_external_allowed=false")
    errors.extend(validate_qword_manifest(QWORD_DENOMINATOR_MANIFEST))
    meta = json.loads(FULL_TABLE_META.read_text(encoding="utf-8"))
    counts = meta.get("counts") or {}
    if counts.get("lemma_source_rows") != 2092:
        errors.append("full table meta must record 2092 lemma rows")
    if counts.get("qword_denominator_rows", 0) < 100000:
        errors.append("full table meta qword denominator count unexpectedly low")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon source ledger.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate()
    result = {"ok": not errors, "errors": errors, "self_test": bool(args.self_test)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
