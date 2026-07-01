#!/usr/bin/env python3
"""Validate transclusion dependencies for largerollout3 artifacts."""

from __future__ import annotations

import argparse
import json

from largelexicon_common import QWORD_CROSSWALK_MANIFEST
from largelexicon_table_reader import LargelexiconQwordTable


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
REQUIRED_DEP_KINDS = {"qword_denominator_row", "entry", "source_card", "table_manifest"}


def validate() -> list[str]:
    errors: list[str] = []
    if not QWORD_CROSSWALK_MANIFEST.exists():
        return [f"missing crosswalk manifest: {QWORD_CROSSWALK_MANIFEST}"]
    manifest = json.loads(QWORD_CROSSWALK_MANIFEST.read_text(encoding="utf-8"))
    contract = manifest.get("transclusion_contract") or {}
    if contract.get("requires_source_dependencies") is not True:
        errors.append("crosswalk manifest must require source dependencies")
    table = LargelexiconQwordTable.from_repo(ROOT)
    checked = 0
    for row in table.iter_crosswalk_rows(limit=200):
        checked += 1
        kinds = {dep.get("kind") for dep in row.get("source_dependencies") or []}
        missing = REQUIRED_DEP_KINDS - kinds
        if missing:
            errors.append(f"{row.get('row_id')}: missing dependency kinds {sorted(missing)}")
        qword = table.row_by_id(row.get("qword_row_id") or "")
        if not qword:
            errors.append(f"{row.get('row_id')}: reverse qword lookup failed")
        elif qword.get("entry_id") != row.get("entry_id"):
            errors.append(f"{row.get('row_id')}: reverse qword entry_id mismatch")
    if checked == 0:
        errors.append("no crosswalk rows checked")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
