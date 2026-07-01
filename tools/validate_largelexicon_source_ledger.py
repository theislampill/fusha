#!/usr/bin/env python3
"""Validate largelexicon source inventory and source-clean sample ledgers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import LEXICON_DIR, REPORT_DIR, public_boundary_errors, read_jsonl


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPORT_DIR / "largelexicon-source-inventory.json"
LEMMA_SAMPLE = LEXICON_DIR / "lemma-source.sample.jsonl"
FORM_SAMPLE = LEXICON_DIR / "form-source.sample.jsonl"


def validate() -> list[str]:
    errors: list[str] = []
    for path in [INVENTORY, LEMMA_SAMPLE, FORM_SAMPLE]:
        if not path.exists():
            errors.append(f"missing required largelexicon artifact: {path.relative_to(ROOT)}")
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
