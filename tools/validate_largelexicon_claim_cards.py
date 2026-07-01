#!/usr/bin/env python3
"""Validate largelexicon claim cards and stronger-claim gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "qamus" / "reports" / "largelexicon-claim-cards.json"
SUPPORTED = {"supported", "supported_candidate_only"}
NOT_SUPPORTED = {"not_supported_yet"}


def validate(path: Path = CARDS) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing claim cards: {path.relative_to(ROOT)}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "fusha/largelexicon/claim-cards@1":
        errors.append("claim-card schema mismatch")
    boundary = data.get("public_boundary") or {}
    if boundary != {"src": "qamus", "kind": "authored", "lang": "en"}:
        errors.append("claim-card public boundary mismatch")
    ids: set[str] = set()
    for index, card in enumerate(data.get("cards") or [], start=1):
        label = f"card:{index}"
        claim_id = card.get("claim_id")
        if not claim_id:
            errors.append(f"{label}: missing claim_id")
        elif claim_id in ids:
            errors.append(f"{label}: duplicate claim_id {claim_id}")
        ids.add(claim_id)
        status = card.get("status")
        if status not in SUPPORTED | NOT_SUPPORTED:
            errors.append(f"{label}: unsupported status {status!r}")
        if status in SUPPORTED:
            if not card.get("evidence"):
                errors.append(f"{label}: supported claim needs evidence")
            if not card.get("validators"):
                errors.append(f"{label}: supported claim needs validators")
        if status in NOT_SUPPORTED and not card.get("required_before_claim"):
            errors.append(f"{label}: not-supported claim needs required_before_claim gates")
    required = {
        "mode_a_qamus_candidate_engine",
        "mode_b_tutoring_candidate_support",
        "mode_c_standalone_candidate_parser",
        "trained_statistical_disambiguator",
        "certified_dependency_irab_parser",
    }
    missing = sorted(required - ids)
    if missing:
        errors.append(f"missing required claim cards: {missing}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon claim cards.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    errors = validate(Path(args.path) if args.path else CARDS)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
