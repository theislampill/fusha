#!/usr/bin/env python3
"""Validate the bounded FB1 fixture and calibration packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import build_clitic_pronoun_producer as producer  # noqa: E402
from tools import typed_claim_contract as tcc  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "qamus" / "examples" / "fb1-clitic-pronoun"
REQUIRED_TAGS = {
    "attached_object_pronoun",
    "attached_possessive_pronoun",
    "attached_subject_pronoun",
    "proclitic_combination",
    "protective_nun_context",
    "boundary_ambiguous_idgham",
}


def _read(path: Path) -> list[dict[str, Any]]:
    return producer._load_jsonl(path)


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in {"gloss_contribution", "morphline", "token_contribution_gloss"} or _contains_forbidden(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden(child) for child in value)
    return False


def validate_packet(
    fixture_dir: Path,
    sample_input: Path,
    sample_output: Path,
    minimum_sample: int = 40,
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    positives = _read(fixture_dir / "positive.jsonl")
    negatives = _read(fixture_dir / "negative.jsonl")
    if len(positives) < 6:
        errors.append("positive fixture count is below six")
    if len(negatives) < 6:
        errors.append("negative fixture count is below six")
    sample_rows = _read(sample_input)
    output_rows = _read(sample_output)
    if len(sample_rows) < minimum_sample:
        errors.append(f"calibration sample has {len(sample_rows)} rows; minimum is {minimum_sample}")
    if len(sample_rows) != len(output_rows):
        errors.append("calibration input/output row counts differ")
    tags = {tag for row in sample_rows for tag in row.get("calibration_tags", [])}
    missing_tags = sorted(REQUIRED_TAGS - tags)
    if missing_tags:
        errors.append("calibration sample misses required sub-shapes: " + ", ".join(missing_tags))
    status_counts = {"candidate": 0, "unresolved": 0}
    for index, record in enumerate(output_rows, 1):
        record_errors = tcc.validate_contract_record(record)
        errors.extend(f"calibrated-output[{index}]: {error}" for error in record_errors)
        status = record.get("projection", {}).get("status")
        if status == "candidate":
            status_counts["candidate"] += 1
        else:
            status_counts["unresolved"] += 1
        if record.get("projection", {}).get("learner_visible") is not False:
            errors.append(f"calibrated-output[{index}]: learner_visible must remain false")
        if _contains_forbidden(record):
            errors.append(f"calibrated-output[{index}]: gloss/morphline text leaked into governed output")
        for fact in record.get("facts", []):
            if fact.get("fact_type") == "protective_nun":
                typed_kind = fact.get("fact_value", {}).get("typed_kind")
                if typed_kind != "sarf.protective_nun":
                    errors.append(f"calibrated-output[{index}]: protective nūn typed_kind is not sarf.protective_nun")
                if "particle" in str(fact.get("fact_value", {}).get("class", "")):
                    errors.append(f"calibrated-output[{index}]: protective nūn was classified as particle")
    return errors, status_counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--sample-input", type=Path)
    parser.add_argument("--sample-output", type=Path)
    parser.add_argument("--minimum-sample", type=int, default=40)
    args = parser.parse_args(argv)
    sample_input = args.sample_input or (args.fixtures / "calibration-sample.input.jsonl")
    sample_output = args.sample_output or (args.fixtures / "calibrated-output.jsonl")
    errors, counts = validate_packet(args.fixtures, sample_input, sample_output, args.minimum_sample)
    if errors:
        for error in errors:
            print("FAIL — " + error)
        return 1
    total = counts["candidate"] + counts["unresolved"]
    rate = (100.0 * counts["unresolved"] / total) if total else 100.0
    print(
        "FB1 CALIBRATION PACKET VALIDATION PASS "
        f"({total} rows; {counts['candidate']} candidate; {counts['unresolved']} unresolved; "
        f"abstention {rate:.1f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
