#!/usr/bin/env python3
"""Validate the private-acquisition -> source-clean projection boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "sources" / "private-acquisition-cache-policy.md"
PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}
FORBIDDEN_PUBLIC_MARKERS = (
    "mcp",
    "tafsir",
    "qac",
    "quran.com",
    "quran foundation",
    "raw_response",
    "ocr",
    "/srv/",
    "c:\\",
    "api_key",
    "bearer",
    "token",
)


def validate_projection_row(row: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    if row.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append(f"{label}: source-clean projection must have {PUBLIC_BOUNDARY!r}")
    public_text = json.dumps(row.get("public_projection") or row, ensure_ascii=False).lower()
    for marker in FORBIDDEN_PUBLIC_MARKERS:
        if marker in public_text:
            errors.append(f"{label}: forbidden public marker {marker!r}")
    if row.get("raw_private_cache") or row.get("private_evidence_ref"):
        errors.append(f"{label}: source-clean projection must not carry raw/private evidence pointers")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    if not POLICY.exists():
        errors.append(f"missing private cache policy doc: {POLICY}")
    else:
        text = POLICY.read_text(encoding="utf-8").lower()
        for phrase in ("private", "source-clean", "never committed", "src=qamus", "kind=authored", "lang=en"):
            if phrase not in text:
                errors.append(f"policy doc missing phrase: {phrase}")
    sample = {
        "schema": "fusha/private-acquisition-source-clean-projection@1",
        "fact_class": "root_pos_confirmation",
        "public_boundary": PUBLIC_BOUNDARY,
        "public_projection": {"root": "ل ج أ", "pos": "noun", "src": "qamus", "kind": "authored", "lang": "en"},
    }
    errors.extend(validate_projection_row(sample, "self-test sample"))
    leaking = {
        "schema": "fusha/private-acquisition-source-clean-projection@1",
        "public_boundary": PUBLIC_BOUNDARY,
        "public_projection": {"src": "qac", "kind": "imported", "lang": "en"},
    }
    if not validate_projection_row(leaking, "negative leak sample"):
        errors.append("negative leak sample should fail")
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
