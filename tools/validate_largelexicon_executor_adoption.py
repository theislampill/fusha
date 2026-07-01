#!/usr/bin/env python3
"""Validate that executor-facing docs require largelexicon all-qword adoption."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "qamus" / "procedures" / "largelexicon-rollout-consumption.md"
IMPL_DOC = ROOT / "docs" / "parser" / "largelexicon-largerollout3-implementation.md"
REQUIRED_PHRASES = (
    "largelexicon_table_reader.py",
    "all-visible-qword",
    "source-card",
    "crosswalk",
    "replacement",
    "selected-word closure",
    "not live qamus progress",
)


def validate() -> list[str]:
    errors: list[str] = []
    for path in (DOC, IMPL_DOC):
        if not path.exists():
            errors.append(f"missing executor adoption doc: {path}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in REQUIRED_PHRASES:
            if phrase.lower() not in text:
                errors.append(f"{path.name}: missing required phrase {phrase!r}")
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
