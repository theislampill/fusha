#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the lightweight Fusha tutoring assessment fixtures.

This is intentionally small: it prevents empty/honor-system checkpoint fixtures, source-label leakage, and hard
grammar rows without two-vote flags. It does not grade a learner.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable


REQUIRED = {
    "id",
    "level",
    "concept",
    "prompt",
    "quran_example",
    "expected_answer",
    "accepted_variants",
    "forbidden_answers",
    "required_reasoning",
    "sarf_procedure",
    "nahw_procedure",
    "remediation_route",
    "two_vote_required",
}

LEAK_TERMS = ("QAC", "Quran.com", "Tafsir MCP", "OCR", "source-photo", "/srv/", "informed_by")
HARD_TERMS = (
    "iʿrāb",
    "case",
    "mood",
    "particle",
    "PP",
    "pronoun",
    "exception",
    "vocative",
    "oath",
    "token-only",
    "component",
    "preposition",
)


def _level_numbers(value: object) -> list[int]:
    """Extract numeric roadmap levels from simple strings like "7", "7+", or "8-10"."""
    import re

    return [int(match) for match in re.findall(r"\d+", str(value))]


def _load_jsonl(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: row must be an object")
            row["_line"] = lineno
            rows.append(row)
    return rows


def validate(path: str) -> list[str]:
    errors: list[str] = []
    rows = _load_jsonl(path)
    if not rows:
        return [f"{path}: no rows"]

    ids = set()
    hard_rows = 0
    two_vote_rows = 0
    level_numbers: set[int] = set()
    for row in rows:
        lineno = row.pop("_line")
        missing = REQUIRED - set(row)
        if missing:
            errors.append(f"{path}:{lineno}: missing fields: {', '.join(sorted(missing))}")
            continue
        if row["id"] in ids:
            errors.append(f"{path}:{lineno}: duplicate id {row['id']!r}")
        ids.add(row["id"])
        for field in ("accepted_variants", "forbidden_answers", "required_reasoning"):
            if not isinstance(row[field], list) or not row[field]:
                errors.append(f"{path}:{lineno}: {field} must be a nonempty list")
        if not isinstance(row["two_vote_required"], bool):
            errors.append(f"{path}:{lineno}: two_vote_required must be boolean")
        blob = json.dumps(row, ensure_ascii=False)
        for term in LEAK_TERMS:
            if term in blob:
                errors.append(f"{path}:{lineno}: public assessment row leaks internal/source term {term!r}")
        is_hard = any(term.lower() in blob.lower() for term in HARD_TERMS)
        row_levels = _level_numbers(row["level"])
        level_numbers.update(row_levels)
        is_level_7_plus = any(level >= 7 for level in row_levels)
        if is_hard:
            hard_rows += 1
            if row["two_vote_required"]:
                two_vote_rows += 1
            if is_level_7_plus and not row["two_vote_required"]:
                errors.append(
                    f"{path}:{lineno}: Level 7+ hard-grammar row must set two_vote_required=true"
                )
    if hard_rows == 0:
        errors.append(f"{path}: expected at least one hard-grammar row")
    if two_vote_rows == 0:
        errors.append(f"{path}: expected at least one two_vote_required hard-grammar row")
    if Path(path).name == "level-checkpoints.sample.jsonl":
        required_bands = {
            "absolute-beginner level 0-1": any(level <= 1 for level in level_numbers),
            "middle level 4-6": any(4 <= level <= 6 for level in level_numbers),
            "hard-grammar level 7+": any(level >= 7 for level in level_numbers),
        }
        for label, present in required_bands.items():
            if not present:
                errors.append(f"{path}: canonical checkpoint sample lacks {label} coverage")
    return errors


def self_test() -> int:
    good = {
        "id": "self",
        "level": "7",
        "concept": "particle function",
        "prompt": "Why is this hard?",
        "quran_example": None,
        "expected_answer": "Function requires context.",
        "accepted_variants": ["context decides"],
        "forbidden_answers": ["always one gloss"],
        "required_reasoning": ["particle function named"],
        "sarf_procedure": None,
        "nahw_procedure": "nahw/procedures/particle-decision.md",
        "remediation_route": "nahw/drills/dogfood-nahw-remediation.md",
        "two_vote_required": True,
    }
    bad = dict(good)
    bad["id"] = "bad-level-7-hard-row"
    bad["two_vote_required"] = False
    import tempfile

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        fh.write(json.dumps(good, ensure_ascii=False) + "\n")
        tmp = fh.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        fh.write(json.dumps(bad, ensure_ascii=False) + "\n")
        bad_tmp = fh.name
    try:
        errors = validate(tmp)
        bad_errors = validate(bad_tmp)
    finally:
        os.unlink(tmp)
        os.unlink(bad_tmp)
    if errors:
        print("\n".join(errors))
        return 1
    if not any("Level 7+ hard-grammar row" in err for err in bad_errors):
        print("self-test failed: weak Level 7+ hard-grammar row was accepted")
        return 1
    print("CURRICULUM ASSESSMENT SELF-TEST OK")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.paths:
        ap.error("provide at least one JSONL path or --self-test")
    all_errors: list[str] = []
    for path in args.paths:
        all_errors.extend(validate(path))
    if all_errors:
        print("CURRICULUM ASSESSMENT VALIDATION FAIL")
        for err in all_errors:
            print("  -", err)
        return 1
    print(f"CURRICULUM ASSESSMENT OK - {len(args.paths)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
