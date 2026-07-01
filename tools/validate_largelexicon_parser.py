#!/usr/bin/env python3
"""Validate parser consumption of the largelexicon sample layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_standalone_parse import parse_text
from largelexicon_common import LEXICON_DIR, read_jsonl


SAMPLE = LEXICON_DIR / "lemma-source.sample.jsonl"


def validate() -> list[str]:
    errors: list[str] = []
    if not SAMPLE.exists():
        return ["missing largelexicon lemma sample"]
    rows = read_jsonl(SAMPLE)
    probes = []
    for row in rows:
        forms = row.get("forms") or []
        forms = [form for form in forms if form and " " not in form.strip()]
        if row.get("root") and forms:
            probes.append((forms[0], row["entry_id"]))
        if len(probes) >= 8:
            break
    if len(probes) < 5:
        errors.append("need at least five rooted parser probes from largelexicon sample")
    for surface, entry_id in probes:
        parsed = parse_text(surface, document_id=f"largelexicon:{entry_id}", db="largelexicon")
        tokens = parsed.get("tokens") or []
        if len(tokens) != 1:
            errors.append(f"{surface}: expected one token parse")
            continue
        top = (tokens[0].get("morphology_candidates") or [{}])[0]
        if top.get("evidence_class") not in {"seed_lexicon", "largelexicon_sample", "pinned_pattern"}:
            errors.append(f"{surface}: unexpected evidence_class {top.get('evidence_class')!r}")
        if parsed.get("summary", {}).get("live_writes") != 0:
            errors.append(f"{surface}: parser must report zero live_writes")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon parser sample consumption.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors, "self_test": bool(args.self_test)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
