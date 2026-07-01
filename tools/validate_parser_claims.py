"""Claim-boundary validator for Fusha parser/checker artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [
    ROOT / "docs" / "parser" / "claim-boundary.md",
    ROOT / "docs" / "parser" / "fusha-cli-contract.md",
    ROOT / "docs" / "parser" / "qamustyping3-implementation.md",
    ROOT / "docs" / "parser" / "qamustyping4-implementation.md",
    ROOT / "docs" / "parser" / "source-ledger-and-split-policy.md",
    ROOT / "qamus" / "reports" / "qamus-mode-a-thin-slice-report.md",
    ROOT / "qamus" / "reports" / "qamus-mode-a-implementation-ledger.json",
    ROOT / "qamus" / "reports" / "qamustyping3-implementation-ledger.json",
    ROOT / "qamus" / "reports" / "qamustyping4-implementation-ledger.json",
    ROOT / "qamus" / "reports" / "qamus-mode-a-parser-stack-report.md",
    ROOT / "docs" / "parser" / "largelexicon-claim-boundary.md",
    ROOT / "docs" / "parser" / "largelexicon-source-ledger.md",
    ROOT / "docs" / "parser" / "largelexicon-implementation.md",
    ROOT / "qamus" / "reports" / "largelexicon-implementation-ledger.json",
    ROOT / "qamus" / "reports" / "largelexicon-claim-cards.json",
    ROOT / "fusha" / "parser" / "model-cards" / "rule-ranked-baseline.model-card.json",
    ROOT / "fusha" / "parser" / "eval" / "qamustyping3-eval-matrix.json",
    ROOT / "fusha" / "parser" / "eval" / "qamustyping4-eval-matrix.json",
]

FORBIDDEN_PHRASES = {
    "complete classical arabic grammarly",
    "camel-tools equivalent",
    "madamira equivalent",
    "stanza equivalent",
    "trained dependency parser passes",
    "claims live qamus progress",
    "vn closure achieved",
}

REQUIRED_DISCLAIMERS = {
    "not live qamus",
    "not arbitrary-text",
}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate parser/checker claim boundaries.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--paths", nargs="*", default=[str(p) for p in DEFAULT_PATHS])
    args = parser.parse_args()
    errors: list[str] = []
    combined = []
    for raw_path in args.paths:
        path = Path(raw_path)
        text = read_text(path)
        if not text:
            errors.append(f"missing claim surface: {path}")
            continue
        combined.append(text)
        for phrase in FORBIDDEN_PHRASES:
            if phrase in text:
                errors.append(f"{path}: forbidden claim phrase {phrase!r}")
    all_text = "\n".join(combined)
    for phrase in REQUIRED_DISCLAIMERS:
        if phrase not in all_text:
            errors.append(f"required claim-boundary phrase absent: {phrase!r}")
    result = {
        "ok": not errors,
        "checked": args.paths,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
