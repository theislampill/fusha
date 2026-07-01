#!/usr/bin/env python3
"""Validate Qamus source-card/example repair worklists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from largelexicon_common import PUBLIC_BOUNDARY, SOURCE_CARD_REPAIR_META, SOURCE_CARD_REPAIR_WORKLIST


FORBIDDEN = ("mcp", "tafsir", "qac", "quran.com", "/srv/", "c:\\", "ocr_dump", "raw_response")


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(path: Path = SOURCE_CARD_REPAIR_WORKLIST) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing source-card repair worklist: {path}"]
    rows = _rows(path)
    if not rows:
        errors.append("source-card repair worklist is empty")
    if not any(row.get("source_key") == "n993" and row.get("entry_id") == "2a071cd0b50e" for row in rows):
        errors.append("source-card repair worklist must include n993 / 2a071cd0b50e")
    for index, row in enumerate(rows, start=1):
        label = f"row {index} {row.get('row_id')}"
        for field in ("row_id", "entry_id", "source_key", "source_photo_ref", "candidate_quran_ref", "required_decision"):
            if not row.get(field):
                errors.append(f"{label}: missing {field}")
        if row.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append(f"{label}: public_boundary must be {PUBLIC_BOUNDARY!r}")
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"{label}: live_mutation_allowed must be false")
        if row.get("repair_status") not in {"owner_source_confirmation_required", "accepted_source_repair", "rejected"}:
            errors.append(f"{label}: unexpected repair_status {row.get('repair_status')!r}")
        text = json.dumps(row, ensure_ascii=False).lower()
        for forbidden in FORBIDDEN:
            if forbidden in text:
                errors.append(f"{label}: forbidden private/public leak marker {forbidden!r}")
    if SOURCE_CARD_REPAIR_META.exists():
        meta = json.loads(SOURCE_CARD_REPAIR_META.read_text(encoding="utf-8"))
        if meta.get("row_count") != len(rows):
            errors.append("source-card repair meta row_count mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--path", type=Path, default=SOURCE_CARD_REPAIR_WORKLIST)
    args = parser.parse_args()
    errors = validate(args.path)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
