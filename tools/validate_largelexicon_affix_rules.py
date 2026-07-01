#!/usr/bin/env python3
"""Validate largelexicon affix compatibility rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "fusha" / "morphology" / "data" / "largelexicon-affix-compatibility.json"
PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}
REQUIRED = {
    "attached_preposition_ba",
    "attached_preposition_lam",
    "conjunction_waw",
    "result_or_resumption_fa",
    "suffix_pronoun_object_or_possessive",
    "sound_plural_suffix",
    "derivative_prefix_mim",
    "tanwin_alif_not_na",
}


def validate() -> list[str]:
    errors: list[str] = []
    data = json.loads(RULES.read_text(encoding="utf-8"))
    if data.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append("affix rules public_boundary must stay source-clean")
    ids = {row.get("id") for row in data.get("rules") or []}
    missing = REQUIRED - ids
    if missing:
        errors.append(f"missing required affix rules: {sorted(missing)}")
    for row in data.get("rules") or []:
        if not row.get("role"):
            errors.append(f"{row.get('id')}: missing role")
        if not row.get("safe_projection"):
            errors.append(f"{row.get('id')}: missing safe_projection")
        if row.get("id") in {"attached_preposition_ba", "attached_preposition_lam"} and not row.get("features_added", {}).get(
            "requires_nahw"
        ):
            errors.append(f"{row.get('id')}: attached prepositions must require nahw")
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
