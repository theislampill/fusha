#!/usr/bin/env python3
"""Compute fail-closed operationalization truth for tranche 001 units.

The computation consumes only committed repository evidence.  Candidate facts
remain candidates; this module measures consumer coverage and never certifies a
linguistic fact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

TRANCHE_001_UNIT_IDS = (
    "cu-grapheme-inventory-and-confusables",
    "cu-orthographic-connectivity-classes",
    "cu-short-vowel-diacritics-and-vocalization-state",
    "u-s06",
    "u-s01",
    "cu-nunation-support-orthography",
    "u-n01",
    "cu-definite-article-assimilation",
)

REAL_CONSUMER_STATUSES = frozenset({
    "operationalized_real_consumer",
    "already_operational_consumer_reverified",
})
PARKABLE_OCCURRENCE_STATES = frozenset({
    "evidence_blocked",
    "sol_integration_blocked",
})
DIMENSION_ORDER = (
    "machine_execution",
    "runtime_misconceptions",
    "error_fixtures",
    "consumer_bindings",
    "occurrence_grounding",
)


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _existing_repo_path(value: str) -> bool:
    return bool(value) and (ROOT / value).is_file()


def _all_kcs() -> list[dict]:
    rows = json.loads(
        (ROOT / "curriculum" / "kc-catalog.json").read_text(encoding="utf-8")
    )
    for path in sorted((ROOT / "curriculum" / "kc-catalog.d").glob("*.jsonl")):
        rows.extend(_jsonl(path))
    return rows


def _runtime_kc_ids() -> set[str]:
    out = set()
    for path in sorted((ROOT / "curriculum" / "drills" / "keys").glob("*.jsonl")):
        for row in _jsonl(path):
            if (
                row.get("kc_id")
                and row.get("id")
                and row.get("prompt")
                and row.get("expected_answer")
                and row.get("remediation_route")
                and _existing_repo_path(row["remediation_route"])
            ):
                out.add(row["kc_id"])
    return out


def close_from_dimensions(dimensions: list[dict]) -> dict:
    by_name = {row["dimension"]: row for row in dimensions}
    missing = [name for name in DIMENSION_ORDER if name not in by_name]
    incomplete = [
        name
        for name in DIMENSION_ORDER
        if name not in by_name or by_name[name].get("satisfied") is not True
    ]
    fully = not incomplete
    basis_payload = json.dumps(
        dimensions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "fully_operationalized": fully,
        "fully_operationalized_basis": (
            "all_required_dimensions_satisfied:sha256:"
            + hashlib.sha256(basis_payload).hexdigest()
            if fully
            else "incomplete_dimensions:" + ",".join(incomplete)
        ),
        "incomplete_dimensions": incomplete,
        "missing_dimensions": missing,
    }


def _machine_dimension(row: dict) -> dict:
    if not row.get("machine_execution_appropriate"):
        return {
            "dimension": "machine_execution",
            "satisfied": True,
            "disposition": "instructional_only",
            "increment_ids": [],
        }
    increments = list(row.get("machine_increments", []))
    missing = []
    for increment_id in increments:
        directory = BASE / "increments" / increment_id
        if not list(directory.glob("unit-v*.json")) or not (
            directory / "fixtures.jsonl"
        ).is_file():
            missing.append(increment_id)
    return {
        "dimension": "machine_execution",
        "satisfied": bool(increments) and not missing,
        "disposition": "pack_backed" if increments and not missing else "pack_missing",
        "increment_ids": increments,
        "missing_increment_ids": missing,
    }


def _runtime_dimension(
    unit_id: str,
    misconceptions: list[dict],
    kcs: list[dict],
    runtime_kcs: set[str],
) -> dict:
    required = {
        row["misconception_id"]
        for row in misconceptions
        if unit_id in row.get("related_units", [])
    }
    covered = {
        misconception_id
        for row in kcs
        if row.get("kc_id") in runtime_kcs
        for misconception_id in row.get("curriculum_misconception_ids", [])
    }
    missing = sorted(required - covered)
    return {
        "dimension": "runtime_misconceptions",
        "satisfied": not missing,
        "total": len(required),
        "covered": len(required & covered),
        "missing_ids": missing,
    }


def _error_fixture_dimension(
    unit_id: str,
    lesson_ids: list[str],
    queue_rows: list[dict],
    trace_rows: list[dict],
) -> dict:
    expected = {
        row["row_id"] for row in queue_rows if row.get("source") in lesson_ids
    }
    traced = {
        row["source_queue_row_id"]
        for row in trace_rows
        if unit_id in row.get("selected_unit_links", [])
        and row.get("outcome") == "runner_loaded_fixture_only"
        and row.get("behaviorally_decided") is False
        and _existing_repo_path(row.get("owning_runner", ""))
        and _existing_repo_path(row.get("owning_skill_bank", ""))
    }
    missing = sorted(expected - traced)
    return {
        "dimension": "error_fixtures",
        "satisfied": not missing,
        "total": len(expected),
        "traced": len(expected & traced),
        "missing_queue_row_ids": missing,
        "posture": "fixture_only_not_behavioral_closure",
    }


def _binding_dimension(
    unit_id: str,
    lesson_ids: list[str],
    bindings: list[dict],
) -> dict:
    rows = [
        row
        for row in bindings
        if unit_id in row.get("unit_ids", [])
        and row.get("binding_status") == "explicit"
        and row.get("contribution_status") in REAL_CONSUMER_STATUSES
        and all(_existing_repo_path(path) for path in row.get("consumer_paths", []))
        and all(_existing_repo_path(path) for path in row.get("test_paths", []))
    ]
    covered_lessons = {
        lesson_id
        for row in rows
        for lesson_id in row.get("lesson_ids", [])
        if lesson_id in lesson_ids
    }
    missing_lessons = sorted(set(lesson_ids) - covered_lessons)
    return {
        "dimension": "consumer_bindings",
        "satisfied": bool(rows) and not missing_lessons,
        "binding_ids": sorted(row["binding_id"] for row in rows),
        "lessons_total": len(lesson_ids),
        "lessons_bound": len(covered_lessons),
        "missing_lesson_ids": missing_lessons,
    }


def _occurrence_dimension(row: dict) -> dict:
    blockers = row.get("blockers", [])
    if not row.get("occurrence_grounding_appropriate"):
        return {
            "dimension": "occurrence_grounding",
            "satisfied": True,
            "disposition": "not_applicable",
        }
    if blockers and all(
        blocker.get("dimension") == "occurrence_grounding"
        and blocker.get("state") in PARKABLE_OCCURRENCE_STATES
        for blocker in blockers
    ):
        return {
            "dimension": "occurrence_grounding",
            "satisfied": True,
            "disposition": "parked",
            "blockers": blockers,
        }
    witnessed = "candidate_occurrence_witnesses" in row.get("states", [])
    return {
        "dimension": "occurrence_grounding",
        "satisfied": witnessed and not blockers,
        "disposition": "committed_candidate_witness" if witnessed else "missing",
        "blockers": blockers,
    }


def build(disposition_rows: list[dict] | None = None) -> dict:
    dispositions = disposition_rows or _jsonl(
        BASE / "canonical" / "unit-dispositions.jsonl"
    )
    by_unit = {row["unit_id"]: row for row in dispositions}
    missing_units = sorted(set(TRANCHE_001_UNIT_IDS) - set(by_unit))
    if missing_units:
        raise ValueError("missing tranche-001 units: " + ", ".join(missing_units))

    misconceptions = _jsonl(
        BASE / "misconceptions" / "misconception-registry.jsonl"
    )
    bindings = _jsonl(
        BASE / "links" / "consumer-operationalization-bindings.jsonl"
    )
    queue_rows = _jsonl(BASE / "reports" / "queues" / "q-error-fixtures.jsonl")
    trace_rows = _jsonl(BASE / "reports" / "mistake-pattern-fixtures.jsonl")
    kcs = _all_kcs()
    runtime_kcs = _runtime_kc_ids()

    rows = []
    for unit_id in TRANCHE_001_UNIT_IDS:
        source = by_unit[unit_id]
        lessons = list(source.get("contributing_lessons", []))
        dimensions = [
            _machine_dimension(source),
            _runtime_dimension(unit_id, misconceptions, kcs, runtime_kcs),
            _error_fixture_dimension(
                unit_id, lessons, queue_rows, trace_rows
            ),
            _binding_dimension(unit_id, lessons, bindings),
            _occurrence_dimension(source),
        ]
        result = close_from_dimensions(dimensions)
        rows.append({
            "unit_id": unit_id,
            "fully_operationalized": result["fully_operationalized"],
            "fully_operationalized_basis": result[
                "fully_operationalized_basis"
            ],
            "incomplete_dimensions": result["incomplete_dimensions"],
            "dimensions": {
                row["dimension"]: {
                    key: value
                    for key, value in row.items()
                    if key != "dimension"
                }
                for row in dimensions
            },
        })
    return {
        "schema": "curriculum.l1l6_tranche_closure.v1",
        "tranche_id": "tranche-001",
        "units": rows,
        "units_total": len(rows),
        "units_fully_operationalized": sum(
            1 for row in rows if row["fully_operationalized"]
        ),
    }


def lesson_closure_truth(
    disposition_rows: list[dict],
    lesson_unit_map: list[dict] | None = None,
) -> dict:
    """Return exact lesson closure from all mapped canonical units."""
    mappings = lesson_unit_map or _jsonl(
        BASE / "canonical" / "lesson-unit-map.jsonl"
    )
    closed_units = {
        row["unit_id"]
        for row in disposition_rows
        if row.get("fully_operationalized") is True
        and row.get("fully_operationalized_basis")
        not in (None, "", "not_yet_computed")
    }
    closed_lessons = []
    incomplete = {}
    for row in mappings:
        lesson_id = row["lesson_id"]
        unit_ids = list(row.get("units", []))
        missing = sorted(set(unit_ids) - closed_units)
        if unit_ids and not missing:
            closed_lessons.append(lesson_id)
        else:
            incomplete[lesson_id] = missing
    return {
        "fully_operationalized_lesson_ids": sorted(closed_lessons),
        "lessons_fully_operationalized": len(closed_lessons),
        "incomplete_unit_ids_by_lesson": dict(sorted(incomplete.items())),
        "basis": "all_mapped_canonical_units_fully_operationalized",
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True))
