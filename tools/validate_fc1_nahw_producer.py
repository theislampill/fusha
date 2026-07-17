#!/usr/bin/env python3
"""Validator for the bounded FC1 naḥw producer packet and fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.fc_nahw_producer import (  # noqa: E402
    FACT_TYPE,
    PROJECTOR_ID,
    build_dependency_fact,
    build_unresolved_record,
    surface_is_preserved,
    validate_dependency_fact,
)
from tools.typed_claim_contract import validate_contract_record  # noqa: E402


FC1_DIR = ROOT / "qamus" / "examples" / "fc1-nahw"
FIXTURE_PATH = FC1_DIR / "producer-fixtures.jsonl"
POSITIVE_PATH = FC1_DIR / "fc1-calibrated-sample.jsonl"
UNRESOLVED_PATH = FC1_DIR / "fc1-unresolved-sample.jsonl"
SUMMARY_PATH = FC1_DIR / "fc1-calibration-summary.json"
PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]workspace[\\/]ai[\\/]in[\\/]andon-projection[\\/]lanes", re.I),
    re.compile(r"(?:^|[/\\])lanes[/\\]FC1(?:[/\\]|$)", re.I),
    re.compile(r"(?:^|[/\\])lane-workspace(?:[/\\]|$)", re.I),
)


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(value)
    return rows


def _path_leaks(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(_path_leaks(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_path_leaks(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in PATH_PATTERNS:
            if pattern.search(value):
                errors.append(f"{path} contains a lane-workspace path")
                break
    return errors


def _fixture_errors() -> list[str]:
    errors: list[str] = []
    fixtures = _read_jsonl(FIXTURE_PATH)
    positives = [item for item in fixtures if item.get("expect") == "accept"]
    rejects = [item for item in fixtures if item.get("expect") == "reject"]
    unresolved = [item for item in fixtures if item.get("expect") == "unresolved"]
    if len(positives) < 5:
        errors.append("fewer than five positive producer fixtures")
    if len(rejects) < 5:
        errors.append("fewer than five adversarial producer fixtures")
    required_ids = {
        "adversarial-bare-role",
        "adversarial-missing-governor",
        "adversarial-estimated-without-reason",
        "adversarial-surface-repaint",
        "adversarial-morphology-leak",
    }
    present_ids = {str(item.get("id")) for item in fixtures}
    for fixture_id in sorted(required_ids - present_ids):
        errors.append(f"required adversarial fixture missing: {fixture_id}")
    if not unresolved:
        errors.append("missing-governor abstention fixture is absent")
    for fixture in positives:
        try:
            fact = build_dependency_fact(fixture["input"], source_record_id=f"fixture:{fixture['id']}")
        except (TypeError, ValueError) as exc:
            errors.append(f"positive fixture {fixture.get('id')} rejected: {exc}")
            continue
        errors.extend(f"{fixture.get('id')}: {error}" for error in validate_dependency_fact(fact))
        if fact["fact_value"].get("projected_surface") != fixture["input"].get("projected_surface"):
            errors.append(f"{fixture.get('id')}: projected surface was changed")
    for fixture in rejects:
        try:
            fact = build_dependency_fact(fixture["input"], source_record_id=f"fixture:{fixture['id']}")
        except (TypeError, ValueError):
            continue
        if not validate_dependency_fact(fact):
            errors.append(f"adversarial fixture accepted: {fixture.get('id')}")
    for fixture in unresolved:
        try:
            record = build_unresolved_record(
                fixture["input"], blocker="fixture requires exact governor evidence", source_record_id=f"fixture:{fixture['id']}"
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"unresolved fixture {fixture.get('id')} failed: {exc}")
            continue
        errors.extend(f"{fixture.get('id')}: {error}" for error in validate_contract_record(record))
        if record["projection"].get("status") != "syntax_pending" or record["projection"].get("claim") is not None:
            errors.append(f"{fixture.get('id')}: unresolved fixture did not abstain")
    return errors


def _record_errors(record: dict[str, Any], *, expected_status: str, index: int) -> list[str]:
    errors: list[str] = []
    errors.extend(f"record[{index}] F-A: {error}" for error in validate_contract_record(record))
    errors.extend(f"record[{index}] path: {error}" for error in _path_leaks(record))
    projection = record.get("projection") or {}
    if expected_status == "candidate":
        if record.get("record_type") != "projection_input" or projection.get("status") != "candidate":
            errors.append(f"record[{index}] is not a candidate projection")
        facts = record.get("facts") or []
        if len(facts) != 1:
            errors.append(f"record[{index}] must contain exactly one FC1 fact")
        for fact in facts:
            if fact.get("fact_type") != FACT_TYPE:
                errors.append(f"record[{index}] has a non-FC1 fact type")
            errors.extend(f"record[{index}] naḥw: {error}" for error in validate_dependency_fact(fact))
            value = fact.get("fact_value") or {}
            canonical_surface = (record.get("canonical_occurrence") or {}).get("surface")
            if not surface_is_preserved(canonical_surface, value.get("source_surface")):
                errors.append(f"record[{index}] source surface does not equal canonical surface")
            if not surface_is_preserved(value.get("source_surface"), value.get("projected_surface")):
                errors.append(f"record[{index}] projected surface repaints lexical text")
    else:
        if record.get("record_type") != "unresolved_projection" or projection.get("status") != "syntax_pending":
            errors.append(f"record[{index}] is not syntax_pending")
        if projection.get("claim") is not None or projection.get("learner_visible") is not True:
            errors.append(f"record[{index}] unresolved projection must be learner-visible with null claim")
        facts = record.get("facts") or []
        if len(facts) != 1 or facts[0].get("evidence_mode") != "unresolved":
            errors.append(f"record[{index}] unresolved fact must carry evidence_mode=unresolved")
        value = (facts[0].get("fact_value") or {}) if facts else {}
        if value.get("status") != "unresolved" or value.get("governor") is not None:
            errors.append(f"record[{index}] unresolved fact must not guess a governor")
        canonical_surface = (record.get("canonical_occurrence") or {}).get("surface")
        if not surface_is_preserved(canonical_surface, value.get("source_surface")):
            errors.append(f"record[{index}] unresolved surface is not preserved")
    return errors


def validate_packet(
    positive_rows: Sequence[dict[str, Any]],
    unresolved_rows: Sequence[dict[str, Any]],
    summary: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if len(positive_rows) < 30:
        errors.append(f"positive calibration packet has {len(positive_rows)} rows; expected at least 30")
    if len(unresolved_rows) < 3:
        errors.append(f"unresolved calibration packet has {len(unresolved_rows)} rows; expected at least 3")
    positive_locs = [row.get("canonical_occurrence", {}).get("quran_loc") for row in positive_rows]
    unresolved_locs = [row.get("canonical_occurrence", {}).get("quran_loc") for row in unresolved_rows]
    if len(set(positive_locs)) != len(positive_locs):
        errors.append("positive calibration locations are not unique")
    if len(set(unresolved_locs)) != len(unresolved_locs):
        errors.append("unresolved calibration locations are not unique")
    for index, record in enumerate(positive_rows):
        errors.extend(_record_errors(record, expected_status="candidate", index=index))
    for index, record in enumerate(unresolved_rows):
        errors.extend(_record_errors(record, expected_status="unresolved", index=index))
    roles = {row["facts"][0]["fact_value"].get("role") for row in positive_rows if row.get("facts")}
    for required_role in {"subject", "object", "preposition_to_governed", "mood", "pronoun_attachment", "agreement"}:
        if required_role not in roles:
            errors.append(f"calibration packet lacks priority role {required_role}")
    if summary is not None:
        expected_rate = len(unresolved_rows) / (len(positive_rows) + len(unresolved_rows))
        if summary.get("positive_count") != len(positive_rows) or summary.get("unresolved_count") != len(unresolved_rows):
            errors.append("calibration summary counts do not match packet files")
        if abs(float(summary.get("abstention_rate", -1)) - expected_rate) > 1e-12:
            errors.append("calibration summary abstention rate does not recompute")
        if summary.get("source_stratified_row_count") != 455:
            errors.append("calibration summary does not identify the 455-row stratified source")
        if summary.get("source_verdict_row_count") != 575:
            errors.append("calibration summary does not identify the 575-row verdict input")
    return errors


def validate_fixtures() -> list[str]:
    errors = _fixture_errors()
    if POSITIVE_PATH.is_file() and UNRESOLVED_PATH.is_file():
        summary = _read_json(SUMMARY_PATH) if SUMMARY_PATH.is_file() else None
        errors.extend(validate_packet(_read_jsonl(POSITIVE_PATH), _read_jsonl(UNRESOLVED_PATH), summary))
    else:
        errors.append("committed calibration packet JSONL files are missing")
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        errors = _fixture_errors()
        if errors:
            print("FC1 NAHW PRODUCER SELF-TEST FAIL")
            for error in errors:
                print(f"- {error}")
            return 1
        print("FC1 NAHW PRODUCER SELF-TEST PASS")
        return 0
    if args.fixtures:
        directory = args.fixtures
        positive_path = directory / "fc1-calibrated-sample.jsonl"
        unresolved_path = directory / "fc1-unresolved-sample.jsonl"
        summary_path = directory / "fc1-calibration-summary.json"
        if not positive_path.is_file() or not unresolved_path.is_file():
            print("FC1 NAHW PRODUCER FIXTURES FAIL")
            print("- committed calibration JSONL files are missing")
            return 1
        try:
            errors = validate_packet(
                _read_jsonl(positive_path),
                _read_jsonl(unresolved_path),
                _read_json(summary_path) if summary_path.is_file() else None,
            )
            errors.extend(_path_leaks(_read_jsonl(positive_path)))
            errors.extend(_path_leaks(_read_jsonl(unresolved_path)))
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
        if errors:
            print("FC1 NAHW PRODUCER FIXTURES FAIL")
            for error in errors:
                print(f"- {error}")
            return 1
        print("FC1 NAHW PRODUCER FIXTURES PASS")
        return 0
    parser.error("choose --self-test or --fixtures <repo artifact directory>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
