#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import leak_sot
from tools.rm38.pins import load_pins

HERE = Path(__file__).resolve().parent
FORBIDDEN_SCORE_KEYS = {"aggregate_accuracy", "overall_score"}
ALLOWED_SUFFIXES = {".py", ".json", ".jsonl"}


def validate_split_non_overlap(dev_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> None:
    dev = {str(row.get("unit_id")) for row in dev_rows if row.get("unit_id")}
    test = {str(row.get("unit_id")) for row in test_rows if row.get("unit_id")}
    overlap = sorted(dev & test)
    if overlap:
        raise ValueError(f"unit {overlap[0]} appears in both dev and test")


def validate_no_collapsed_score(value: Any, path: str = "report") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_SCORE_KEYS:
                raise ValueError(f"forbidden collapsed score key {key} at {path}")
            validate_no_collapsed_score(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_collapsed_score(child, f"{path}[{index}]")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_repository() -> None:
    errors = []
    pins_path = HERE / "data-pins.json"
    card_path = HERE / "model-card.rm38.json"
    fixture_path = HERE / "fixtures" / "synthetic-20.jsonl"
    try:
        pins = load_pins(pins_path)
        for source, pin in sorted(pins["sources"].items()):
            for key in ("sha256", "distribution_url", "attribution", "license", "license_url", "filename"):
                if not pin.get(key):
                    errors.append(f"{source} pin missing {key}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    try:
        card = _read_json(card_path)
        validate_no_collapsed_score(card)
        expected_claim = "RM-38 external-gold comparison; per-layer; no aggregate score; abstention-accounted; EQTB syntax partly DL-silver; QAC consult-only"
        if card.get("claim") != expected_claim:
            errors.append("model-card claim boundary drifted")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    try:
        rows = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line]
        if len(rows) != 20:
            errors.append("synthetic fixture must contain exactly 20 rows")
        if any(not str(row.get("unit_id", "")).startswith("synthetic:") for row in rows):
            errors.append("fixture contains a non-synthetic unit_id")
        if leak_sot.scan_obj(rows):
            errors.append("synthetic fixture triggers source-leak scanner")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    for path in HERE.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            errors.append(f"unexpected possible corpus artifact: {path.relative_to(ROOT)}")
        if path.stat().st_size > 250_000:
            errors.append(f"unexpectedly large committed artifact: {path.relative_to(ROOT)}")
    if errors:
        raise ValueError("; ".join(errors))


def _self_test() -> None:
    validate_no_collapsed_score({"source": "synthetic", "coverage": {"value": 1.0}})
    try:
        validate_no_collapsed_score({"overall_score": 1.0})
    except ValueError:
        pass
    else:
        raise AssertionError("collapsed score guard did not fail closed")
    try:
        validate_split_non_overlap([{"unit_id": "synthetic:x"}], [{"unit_id": "synthetic:x"}])
    except ValueError:
        pass
    else:
        raise AssertionError("split overlap guard did not fail closed")
    validate_repository()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the RM-38 source-clean evaluation harness.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            _self_test()
            print("RM-38 validator self-test OK")
        else:
            validate_repository()
            print("RM-38 evaluation harness validation OK")
        return 0
    except (AssertionError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"RM-38 validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
