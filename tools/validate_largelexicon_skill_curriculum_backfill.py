#!/usr/bin/env python3
"""Validate largelexicon sarf/nahw/curriculum/readme backfill surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import validate_backfillfull_sarf_nahw_largelexicon as backfillfull


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    ROOT / "sarf" / "procedures" / "largelexicon-morphology-expansion.md",
    ROOT / "nahw" / "procedures" / "largelexicon-function-token-routing.md",
    ROOT / "curriculum" / "drills" / "largelexicon-morphology-and-hover.md",
    ROOT / "curriculum" / "largelexicon-tutor-routing.md",
    ROOT / "docs" / "parser" / "largelexicon-implementation.md",
]
REQUIRED_PHRASES = [
    "source-clean",
    "not live qamus",
    "candidate",
    "all visible qword",
    "sarf",
    "nahw",
]


def validate() -> list[str]:
    errors: list[str] = []
    combined: list[str] = []
    for path in REQUIRED_PATHS:
        if not path.exists():
            errors.append(f"missing backfill path: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        combined.append(text)
        if "external gloss" in text and "never copy" not in text:
            errors.append(f"{path.relative_to(ROOT)}: external gloss warning is incomplete")
    all_text = "\n".join(combined)
    for phrase in REQUIRED_PHRASES:
        if phrase not in all_text:
            errors.append(f"required backfill phrase absent: {phrase!r}")
    errors.extend(f"backfillfull: {error}" for error in backfillfull.validate())
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon skill/curriculum backfill.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors, "self_test": bool(args.self_test)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
