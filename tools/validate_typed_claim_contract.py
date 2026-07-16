#!/usr/bin/env python3
"""CLI gate for the F-A governed typed-claim contract."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import typed_claim_contract as tcc


def _load_one_jsonl(path: Path) -> list[dict]:
    return tcc.read_jsonl(path)


def validate_fixture_dir(fixture_dir: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts = {
        "governed": 0,
        "prose_rejected": 0,
        "legacy": 0,
        "alias": 0,
        "unresolved_statuses": 0,
    }

    invalid_path = fixture_dir / "prose-only.invalid.jsonl"
    for index, row in enumerate(_load_one_jsonl(invalid_path), 1):
        row_errors = tcc.validate_contract_record(row)
        if not any(tcc.PROSE_ONLY_ERROR in error for error in row_errors):
            errors.append(f"{invalid_path.name}[{index}] did not reject prose-only input")
        else:
            counts["prose_rejected"] += 1

    valid_path = fixture_dir / "tranche1-canary.valid.jsonl"
    for index, row in enumerate(_load_one_jsonl(valid_path), 1):
        row_errors = tcc.validate_contract_record(row)
        if row_errors:
            errors.extend(f"{valid_path.name}[{index}]: {error}" for error in row_errors)
        else:
            counts["governed"] += 1

    legacy_path = fixture_dir / "legacy-valid.jsonl"
    for index, row in enumerate(_load_one_jsonl(legacy_path), 1):
        row_errors = tcc.validate_legacy_record(row)
        if row_errors:
            errors.extend(f"{legacy_path.name}[{index}]: {error}" for error in row_errors)
        else:
            counts["legacy"] += 1

    alias_path = fixture_dir / "alias-normalization.jsonl"
    for index, fixture in enumerate(_load_one_jsonl(alias_path), 1):
        normalized = tcc.normalize_aliases(fixture.get("input"))
        if normalized != fixture.get("expected"):
            errors.append(f"{alias_path.name}[{index}]: normalized output differs from expected")
        output_errors = tcc.assert_no_deprecated_aliases(normalized)
        if output_errors:
            errors.extend(f"{alias_path.name}[{index}]: {error}" for error in output_errors)
        else:
            counts["alias"] += 1

    try:
        mapping = tcc.validate_unresolved_language_map(fixture_dir / "unresolved-language-map.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"unresolved-language-map.json: {exc}")
    else:
        counts["unresolved_statuses"] = len(mapping)

    return errors, counts


def run_self_test(fixture_dir: Path) -> int:
    errors, counts = validate_fixture_dir(fixture_dir)
    valid = _load_one_jsonl(fixture_dir / "tranche1-canary.valid.jsonl")[0]
    legacy = json.loads((fixture_dir / "legacy-valid.jsonl").read_text(encoding="utf-8"))
    legacy_bad = copy.deepcopy(legacy)
    legacy_bad["learner_visible"] = True
    legacy_bad_errors = tcc.validate_legacy_record(legacy_bad)
    if not any("learner_visible" in error for error in legacy_bad_errors):
        errors.append("self-test: legacy learner-visible mutation was accepted")
    alias_errors = tcc.assert_no_deprecated_aliases({"qg_class": "qg-negative"})
    if not alias_errors:
        errors.append("self-test: deprecated output alias was accepted")
    if not valid.get("facts"):
        errors.append("self-test: governed canary has no facts")
    if errors:
        for error in errors:
            print("FAIL — " + error)
        return 1
    print(
        "FA TYPED-CLAIM CONTRACT SELF-TEST PASS "
        f"({counts['governed']} governed, {counts['prose_rejected']} prose rejected, "
        f"{counts['legacy']} legacy internal, {counts['alias']} aliases normalized, "
        f"{counts['unresolved_statuses']} unresolved mappings)"
    )
    return 0


def validate_input(path: Path) -> int:
    errors: list[str] = []
    rows = _load_one_jsonl(path)
    for index, row in enumerate(rows, 1):
        errors.extend(f"{path.name}[{index}]: {error}" for error in tcc.validate_contract_record(row))
    if errors:
        for error in errors:
            print("FAIL — " + error)
        return 1
    print(f"FA TYPED-CLAIM CONTRACT INPUT PASS ({len(rows)} governed rows)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_test(args.fixtures or (tcc.ROOT / "qamus" / "examples" / "fa-contract"))
    if args.fixtures:
        errors, counts = validate_fixture_dir(args.fixtures)
        if errors:
            for error in errors:
                print("FAIL — " + error)
            return 1
        print(
            "FA TYPED-CLAIM CONTRACT FIXTURES PASS "
            f"({counts['governed']} governed, {counts['prose_rejected']} prose rejected, "
            f"{counts['legacy']} legacy internal, {counts['alias']} aliases normalized, "
            f"{counts['unresolved_statuses']} unresolved mappings)"
        )
        return 0
    if args.input:
        return validate_input(args.input)
    parser.error("one of --self-test, --fixtures, or --input is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
