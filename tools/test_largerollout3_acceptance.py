#!/usr/bin/env python3
"""Acceptance smoke for the largerollout3 implementation packet."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_PATHS = [
    "tools/build_qamus_source_card_repair_worklist.py",
    "tools/validate_qamus_source_card_repairs.py",
    "tools/build_largelexicon_qword_crosswalk.py",
    "tools/validate_largelexicon_qword_crosswalk.py",
    "tools/validate_largelexicon_transclusion.py",
    "tools/validate_private_acquisition_projection.py",
    "tools/validate_largelexicon_affix_rules.py",
    "tools/validate_largelexicon_executor_adoption.py",
    "qamus/repairs/source-card-examples/source-card-repair-worklist.jsonl",
    "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json",
    "fusha/morphology/data/largelexicon-affix-compatibility.json",
    "sources/private-acquisition-cache-policy.md",
    "qamus/examples/largelexicon/dependency-irab-decisions.sample.jsonl",
    "docs/parser/largelexicon-largerollout3-implementation.md",
]


def validate() -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"missing required largerollout3 path: {rel}")

    crosswalk_manifest = ROOT / "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json"
    denominator_manifest = ROOT / "qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json"
    if crosswalk_manifest.exists() and denominator_manifest.exists():
        crosswalk = json.loads(crosswalk_manifest.read_text(encoding="utf-8"))
        denominator = json.loads(denominator_manifest.read_text(encoding="utf-8"))
        if crosswalk.get("row_count") != denominator.get("row_count"):
            errors.append("crosswalk row_count must equal qword denominator row_count")
        if crosswalk.get("public_boundary") != {"src": "qamus", "kind": "authored", "lang": "en"}:
            errors.append("crosswalk manifest public_boundary must stay source-clean")

    repair_worklist = ROOT / "qamus/repairs/source-card-examples/source-card-repair-worklist.jsonl"
    if repair_worklist.exists():
        rows = [json.loads(line) for line in repair_worklist.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not any(row.get("source_key") == "n993" and row.get("entry_id") == "2a071cd0b50e" for row in rows):
            errors.append("source-card repair worklist must include n993 / 2a071cd0b50e")

    return errors


def main() -> int:
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
