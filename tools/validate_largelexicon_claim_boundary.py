#!/usr/bin/env python3
"""Validate that largelexicon docs and reports do not overclaim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [
    ROOT / "docs" / "parser" / "largelexicon-claim-boundary.md",
    ROOT / "docs" / "parser" / "largelexicon-source-ledger.md",
    ROOT / "docs" / "parser" / "largelexicon-implementation.md",
    ROOT / "qamus" / "reports" / "largelexicon-source-inventory.json",
    ROOT / "qamus" / "reports" / "largelexicon-implementation-ledger.json",
    ROOT / "fusha" / "parser" / "model-cards" / "largelexicon-candidate-engine.model-card.json",
]

FORBIDDEN = {
    "complete classical arabic nlp stack",
    "camel-tools equivalent",
    "madamira equivalent",
    "stanza equivalent",
    "general-purpose grammarly completed",
    "arbitrary text certified",
    "claims live qamus progress",
    "vn closure achieved",
}

REQUIRED = {
    "not live qamus",
    "not arbitrary-text certification",
    "source-clean",
    "candidate",
}


def validate(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    combined: list[str] = []
    for path in paths:
        if not path.exists():
            errors.append(f"missing claim surface: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        combined.append(text)
        for phrase in FORBIDDEN:
            if phrase in text:
                errors.append(f"{path.relative_to(ROOT)}: forbidden overclaim phrase {phrase!r}")
    all_text = "\n".join(combined)
    for phrase in REQUIRED:
        if phrase not in all_text:
            errors.append(f"required phrase absent: {phrase!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon claim boundaries.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--paths", nargs="*")
    args = parser.parse_args()
    paths = [Path(p) for p in args.paths] if args.paths else DEFAULT_PATHS
    errors = validate(paths)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
