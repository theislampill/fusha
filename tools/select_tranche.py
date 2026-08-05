#!/usr/bin/env python3
"""Select deterministic L1-L6 operationalization tranches.

Closure is intentionally fail-closed. A unit counts as closed at time zero
only when the authoritative unit-disposition row explicitly sets
``fully_operationalized`` and supplies a computed basis. Candidate packs,
real-consumer bindings for one plane, and readiness prose are useful partial
evidence, but none independently establishes all-dimension unit closure.

The default command is read-only. Use ``--write`` to regenerate committed
artifacts or ``--check`` to compare them byte-for-byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import curriculum_closure as closure


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = "tools/select_tranche.py"
TRANCHE_PATH = Path("curriculum/l1l6/tranches/tranche-001.json")
BURNDOWN_PATH = Path("curriculum/l1l6/reports/lesson-burndown.json")

INPUT_PATHS = {
    "lessons": Path("curriculum/l1l6/registry/lessons.jsonl"),
    "lesson_unit_map": Path("curriculum/l1l6/canonical/lesson-unit-map.jsonl"),
    "canonical_units": Path("curriculum/l1l6/canonical/canonical-units.jsonl"),
    "unit_dispositions": Path("curriculum/l1l6/canonical/unit-dispositions.jsonl"),
    "absorption_rows": Path("curriculum/l1l6/reports/absorption-ledger.jsonl"),
    "consumer_bindings": Path("curriculum/l1l6/links/consumer-operationalization-bindings.jsonl"),
    "error_fixture_rows": Path("curriculum/l1l6/reports/queues/q-error-fixtures.jsonl"),
    "readiness": Path("curriculum/l1l6/reports/full-curriculum-readiness.json"),
    "bench_report": Path("eval/fusha-bench-v1/report/fusha-bench-report.json"),
}

REAL_CONSUMER_STATUSES = frozenset({
    "operationalized_real_consumer",
    "already_operational_consumer_reverified",
})
NON_COMPUTED_CLOSURE_BASES = frozenset({None, "", "not_yet_computed"})
PARKABLE_BLOCKER_STATES = frozenset({"evidence_blocked", "sol_integration_blocked"})


@dataclass(frozen=True)
class Inputs:
    lessons: list[dict]
    lesson_unit_map: list[dict]
    unit_dispositions: list[dict]
    canonical_units: list[dict]
    absorption_rows: list[dict]
    consumer_bindings: list[dict]
    error_fixture_rows: list[dict]
    readiness: dict
    bench_report: dict
    source_hashes: dict[str, str]


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(root: Path = ROOT) -> Inputs:
    paths = {name: root / relative for name, relative in INPUT_PATHS.items()}
    missing = [str(path.relative_to(root)) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("missing selector inputs: " + ", ".join(sorted(missing)))
    return Inputs(
        lessons=_jsonl(paths["lessons"]),
        lesson_unit_map=_jsonl(paths["lesson_unit_map"]),
        unit_dispositions=_jsonl(paths["unit_dispositions"]),
        canonical_units=_jsonl(paths["canonical_units"]),
        absorption_rows=_jsonl(paths["absorption_rows"]),
        consumer_bindings=_jsonl(paths["consumer_bindings"]),
        error_fixture_rows=_jsonl(paths["error_fixture_rows"]),
        readiness=json.loads(paths["readiness"].read_text(encoding="utf-8")),
        bench_report=json.loads(paths["bench_report"].read_text(encoding="utf-8")),
        source_hashes={
            str(INPUT_PATHS[name]).replace("\\", "/"): _sha256(path)
            for name, path in sorted(paths.items())
        },
    )


def _unique_by(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    duplicates = []
    for row in rows:
        value = row[key]
        if value in out:
            duplicates.append(value)
        out[value] = row
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(sorted(set(duplicates)))}")
    return out


def is_closed_unit(row: dict) -> bool:
    """Return authoritative all-dimension closure, never candidate readiness."""
    return (
        row.get("fully_operationalized") is True
        and row.get("fully_operationalized_basis") not in NON_COMPUTED_CLOSURE_BASES
    )


def plan_tranches(
    lessons: list[dict],
    lesson_unit_map: list[dict],
    unit_dispositions: list[dict],
    *,
    quota: int = 9,
    not_applicable_lesson_ids: set[str] | None = None,
) -> dict:
    """Build a stable greedy plan from exact lesson order and unit closure."""
    if quota < 1:
        raise ValueError("quota must be at least 1")
    not_applicable = set(not_applicable_lesson_ids or ())
    lesson_by_id = _unique_by(lessons, "lesson_id", "lesson ids")
    map_by_lesson = _unique_by(lesson_unit_map, "lesson_id", "lesson-unit map rows")
    unit_by_id = _unique_by(unit_dispositions, "unit_id", "unit dispositions")
    lesson_ids = list(lesson_by_id)
    lesson_order = {lesson_id: index for index, lesson_id in enumerate(lesson_ids)}

    missing_map = sorted(set(lesson_by_id) - set(map_by_lesson))
    extra_map = sorted(set(map_by_lesson) - set(lesson_by_id))
    if missing_map:
        raise ValueError("missing lesson-unit map rows: " + ", ".join(missing_map))
    if extra_map:
        raise ValueError("unknown lesson-unit map rows: " + ", ".join(extra_map))

    mapped_units = {
        unit_id
        for row in lesson_unit_map
        for unit_id in row.get("units", [])
    }
    unknown_units = sorted(mapped_units - set(unit_by_id))
    unmapped_units = sorted(set(unit_by_id) - mapped_units)
    if unknown_units:
        raise ValueError("unknown canonical units: " + ", ".join(unknown_units))
    if unmapped_units:
        raise ValueError("unit dispositions omitted from lesson map: " + ", ".join(unmapped_units))
    unknown_not_applicable = sorted(not_applicable - set(lesson_by_id))
    if unknown_not_applicable:
        raise ValueError("unknown not-applicable lessons: " + ", ".join(unknown_not_applicable))

    lesson_units = {
        lesson_id: tuple(map_by_lesson[lesson_id].get("units", []))
        for lesson_id in lesson_ids
    }
    unit_lessons: dict[str, list[str]] = {unit_id: [] for unit_id in unit_by_id}
    for lesson_id in lesson_ids:
        for unit_id in lesson_units[lesson_id]:
            unit_lessons[unit_id].append(lesson_id)

    closed_units = {
        unit_id for unit_id, row in unit_by_id.items() if is_closed_unit(row)
    }
    contradictory = sorted(
        unit_id
        for unit_id in closed_units
        if any(
            blocker.get("dimension") != "occurrence_grounding"
            or blocker.get("state") not in PARKABLE_BLOCKER_STATES
            for blocker in unit_by_id[unit_id].get("blockers", [])
        )
    )
    if contradictory:
        raise ValueError("closed units still carry blockers: " + ", ".join(contradictory))
    blocked_units = {
        unit_id
        for unit_id, row in unit_by_id.items()
        if unit_id not in closed_units
        and any(
            blocker.get("state") not in PARKABLE_BLOCKER_STATES
            for blocker in row.get("blockers", [])
        )
    }
    parked_units = {
        unit_id
        for unit_id, row in unit_by_id.items()
        if bool(row.get("blockers"))
        and unit_id not in blocked_units
    }

    def lesson_is_closed(lesson_id: str, available_units: set[str]) -> bool:
        units = set(lesson_units[lesson_id])
        return (
            lesson_id not in not_applicable
            and bool(units)
            and not units.intersection(blocked_units)
            and units.issubset(available_units)
        )

    baseline_closed_lessons = {
        lesson_id
        for lesson_id in lesson_ids
        if lesson_is_closed(lesson_id, closed_units)
    }
    ordered_units = sorted(
        unit_by_id,
        key=lambda unit_id: (
            min(lesson_order[lesson_id] for lesson_id in unit_lessons[unit_id]),
            unit_id,
        ),
    )
    selectable_units = [
        unit_id
        for unit_id in ordered_units
        if unit_id not in closed_units and unit_id not in blocked_units
    ]

    tranches = []
    available = set(closed_units)
    flipped = set(baseline_closed_lessons)
    bucket: list[str] = []
    for unit_id in selectable_units:
        bucket.append(unit_id)
        available.add(unit_id)
        newly_flipped = [
            lesson_id
            for lesson_id in lesson_ids
            if lesson_id not in flipped and lesson_is_closed(lesson_id, available)
        ]
        if len(newly_flipped) >= quota:
            tranches.append({
                "tranche_number": len(tranches) + 1,
                "unit_ids": list(bucket),
                "newly_flipped_lesson_ids": newly_flipped,
                "residual": False,
            })
            flipped.update(newly_flipped)
            bucket = []
    if bucket:
        newly_flipped = [
            lesson_id
            for lesson_id in lesson_ids
            if lesson_id not in flipped and lesson_is_closed(lesson_id, available)
        ]
        tranches.append({
            "tranche_number": len(tranches) + 1,
            "unit_ids": list(bucket),
            "newly_flipped_lesson_ids": newly_flipped,
            "residual": len(newly_flipped) < quota,
        })
        flipped.update(newly_flipped)

    lesson_dispositions = {}
    for lesson_id in lesson_ids:
        units = set(lesson_units[lesson_id])
        if lesson_id in not_applicable:
            state = "not_applicable_with_reason"
        elif lesson_id in baseline_closed_lessons:
            state = "fully_operationalized_current_state"
        elif units.intersection(blocked_units):
            state = "blocked"
        elif lesson_id in flipped:
            state = "projected_closed_by_tranche_plan"
        else:
            state = "open_residual"
        lesson_dispositions[lesson_id] = {
            "state": state,
            "unit_ids": list(lesson_units[lesson_id]),
            "blocked_unit_ids": sorted(units.intersection(blocked_units)),
        }

    blocked_rows = []
    for unit_id in ordered_units:
        if unit_id in blocked_units:
            blocked_rows.append({
                "unit_id": unit_id,
                "contributing_lesson_ids": unit_lessons[unit_id],
                "blockers": unit_by_id[unit_id]["blockers"],
            })
    parked_rows = []
    for unit_id in ordered_units:
        if unit_id in parked_units:
            parked_rows.append({
                "unit_id": unit_id,
                "contributing_lesson_ids": unit_lessons[unit_id],
                "blockers": unit_by_id[unit_id]["blockers"],
                "selection_effect": "parked_state_does_not_stall_tranche",
            })
    return {
        "lesson_ids": lesson_ids,
        "lesson_units": lesson_units,
        "unit_lessons": unit_lessons,
        "unit_order": ordered_units,
        "baseline_closed_unit_ids": [u for u in ordered_units if u in closed_units],
        "baseline_closed_lesson_ids": [l for l in lesson_ids if l in baseline_closed_lessons],
        "blocked_unit_ids": [u for u in ordered_units if u in blocked_units],
        "blocked_units": blocked_rows,
        "parked_unit_ids": [u for u in ordered_units if u in parked_units],
        "parked_units": parked_rows,
        "not_applicable_lesson_ids": [l for l in lesson_ids if l in not_applicable],
        "tranches": tranches,
        "lesson_dispositions": lesson_dispositions,
    }


def _production_lines(
    disposition: dict,
    contributing_lessons: list[str],
    error_fixture_lessons: set[str],
) -> list[str]:
    lines = []
    if disposition.get("machine_execution_appropriate"):
        lines.append("line_1_machine_packs")
    if disposition.get("tutor_projection_appropriate"):
        lines.append("line_2_drill_kc_realization")
    if disposition.get("occurrence_grounding_appropriate"):
        lines.append("line_3_occurrence_grounding")
    if set(contributing_lessons).intersection(error_fixture_lessons):
        lines.append("line_4_error_fixtures")
    return lines


def _bench_axes(report: dict) -> dict:
    out = {}
    for axis, row in sorted(report.get("axes", {}).items()):
        metric = row.get("metric") or {}
        out[axis] = {
            "status": row.get("status"),
            "metric_name": metric.get("name"),
            "score": metric.get("score"),
            "numerator": metric.get("numerator"),
            "denominator": metric.get("denominator", row.get("denominator")),
            "delta": metric.get("delta"),
        }
    return out


def build_artifacts(inputs: Inputs, *, quota: int = 9) -> tuple[dict, dict]:
    absorption_by_lesson = _unique_by(
        inputs.absorption_rows, "lesson_id", "absorption rows"
    )
    not_applicable = {
        lesson_id
        for lesson_id, row in absorption_by_lesson.items()
        if row.get("absorption_state") == "not_applicable_with_reason"
    }
    plan = plan_tranches(
        inputs.lessons,
        inputs.lesson_unit_map,
        inputs.unit_dispositions,
        quota=quota,
        not_applicable_lesson_ids=not_applicable,
    )
    canonical_by_unit = _unique_by(
        inputs.canonical_units, "unit_id", "canonical unit rows"
    )
    dispositions = _unique_by(
        inputs.unit_dispositions, "unit_id", "unit dispositions"
    )
    if set(canonical_by_unit) != set(dispositions):
        missing = sorted(set(dispositions) - set(canonical_by_unit))
        extra = sorted(set(canonical_by_unit) - set(dispositions))
        raise ValueError(
            "canonical/disposition unit mismatch: missing canonical=%s; missing disposition=%s"
            % (missing, extra)
        )
    error_fixture_lessons = {
        row["source"] for row in inputs.error_fixture_rows if row.get("source")
    }
    real_bindings = [
        row
        for row in inputs.consumer_bindings
        if row.get("binding_status") == "explicit"
        and row.get("contribution_status") in REAL_CONSUMER_STATUSES
    ]
    real_binding_ids_by_unit: dict[str, list[str]] = {}
    for row in real_bindings:
        for unit_id in row.get("unit_ids", []):
            real_binding_ids_by_unit.setdefault(unit_id, []).append(row["binding_id"])
    for values in real_binding_ids_by_unit.values():
        values.sort()
    closed_unit_ids = set(plan["baseline_closed_unit_ids"])
    partial_real_consumer_unit_ids = (
        set(real_binding_ids_by_unit) - closed_unit_ids
    )

    target_unit_ids = list(closure.TRANCHE_001_UNIT_IDS)
    preserve_tranche_001 = set(target_unit_ids).issubset(dispositions)
    if preserve_tranche_001:
        current_unit_ids = target_unit_ids
    else:
        current_unit_ids = list(
            plan["tranches"][0]["unit_ids"] if plan["tranches"] else []
        )
    current_closed_unit_ids = [
        unit_id
        for unit_id in current_unit_ids
        if is_closed_unit(dispositions[unit_id])
    ]
    first = {
        "tranche_number": 1,
        "unit_ids": current_unit_ids,
        "newly_flipped_lesson_ids": (
            plan["baseline_closed_lesson_ids"]
            if preserve_tranche_001
            else (
                plan["tranches"][0]["newly_flipped_lesson_ids"]
                if plan["tranches"] else []
            )
        ),
        "residual": False,
    }
    first["residual"] = len(first["newly_flipped_lesson_ids"]) < quota
    unit_records = []
    contributing_lessons = []
    seen_lessons = set()
    for unit_id in first["unit_ids"]:
        disposition = dispositions[unit_id]
        lessons = plan["unit_lessons"][unit_id]
        for lesson_id in lessons:
            if lesson_id not in seen_lessons:
                seen_lessons.add(lesson_id)
                contributing_lessons.append(lesson_id)
        canonical = canonical_by_unit[unit_id]
        unit_records.append({
            "unit_id": unit_id,
            "axis": canonical.get("axis"),
            "capability_family": canonical.get("capability_family"),
            "contributing_lesson_ids": lessons,
            "owning_production_lines": _production_lines(
                disposition, lessons, error_fixture_lessons
            ),
            "current_closure": (
                "fully_operationalized"
                if is_closed_unit(disposition)
                else "partially_operationalized"
            ),
            "incomplete_closure_dimensions": disposition.get(
                "incomplete_closure_dimensions", []
            ),
            "current_strongest_state": disposition.get("strongest_state"),
            "real_consumer_binding_ids": real_binding_ids_by_unit.get(unit_id, []),
            "blockers": disposition.get("blockers", []),
        })
    contributing_lessons = [
        lesson_id for lesson_id in plan["lesson_ids"] if lesson_id in seen_lessons
    ]

    blocked_lessons = [
        {
            "lesson_id": lesson_id,
            "blocked_unit_ids": disposition["blocked_unit_ids"],
        }
        for lesson_id, disposition in plan["lesson_dispositions"].items()
        if disposition["state"] == "blocked"
    ]
    authority = {
        "closure_rule": (
            "unit-dispositions fully_operationalized=true with a computed "
            "fully_operationalized_basis; candidate states and plane-specific "
            "consumer bindings remain partial evidence"
        ),
        "inputs": inputs.source_hashes,
    }
    tranche = {
        "schema": "curriculum.l1l6_operationalization_tranche.v1",
        "generator": GENERATOR,
        "tranche_id": "tranche-001",
        "selection": {
            "algorithm": "earliest_contributing_lesson_then_unit_id_greedy",
            "lesson_flip_quota": quota,
            "residual": first["residual"],
        },
        "authority": authority,
        "current_state": {
            "lessons_total": len(inputs.lessons),
            "units_total": len(inputs.unit_dispositions),
            "closed_unit_ids": plan["baseline_closed_unit_ids"],
            "closed_lesson_ids": plan["baseline_closed_lesson_ids"],
            "not_applicable_lesson_ids": plan["not_applicable_lesson_ids"],
            "real_consumer_unit_ids_partial_only": sorted(
                partial_real_consumer_unit_ids
            ),
        },
        "units": unit_records,
        "contributing_lesson_ids": contributing_lessons,
        "fully_operationalized_lesson_ids": first["newly_flipped_lesson_ids"],
        "closure": {
            "units_fully_operationalized": len(current_closed_unit_ids),
            "units_still_partial": len(current_unit_ids) - len(
                current_closed_unit_ids
            ),
            "fully_operationalized_unit_ids": current_closed_unit_ids,
            "newly_fully_operationalized_lesson_ids": first[
                "newly_flipped_lesson_ids"
            ],
            "tranche_closed": (
                len(current_closed_unit_ids) == len(current_unit_ids)
                and len(first["newly_flipped_lesson_ids"]) >= quota
            ),
        },
        "blocked_units": plan["blocked_units"],
        "parked_dimension_blockers": plan["parked_units"],
        "blocked_lessons": blocked_lessons,
        "remaining": {
            "future_tranches_total": len(plan["tranches"]),
            "units_after_tranche_001": (
                len(inputs.unit_dispositions)
                - len(plan["baseline_closed_unit_ids"])
            ),
            "blocked_units": len(plan["blocked_unit_ids"]),
            "parked_dimension_blockers": len(plan["parked_unit_ids"]),
        },
    }

    real_lesson_ids = sorted({
        lesson_id
        for row in real_bindings
        for lesson_id in row.get("lesson_ids", [])
    })
    disposition_counts: dict[str, int] = {}
    for lesson_id in plan["lesson_ids"]:
        planned_state = plan["lesson_dispositions"][lesson_id]["state"]
        if lesson_id in plan["not_applicable_lesson_ids"]:
            state = "not_applicable_with_reason"
        elif lesson_id in plan["baseline_closed_lesson_ids"]:
            state = "fully_operationalized"
        elif planned_state == "blocked":
            state = "blocked"
        elif lesson_id in real_lesson_ids:
            state = "partially_operationalized_real_consumer"
        else:
            state = "open"
        disposition_counts[state] = disposition_counts.get(state, 0) + 1
    units_with_real_consumer = set(real_binding_ids_by_unit)
    unit_counts = {
        "closed": len(plan["baseline_closed_unit_ids"]),
        "blocked": len(plan["blocked_unit_ids"]),
        "real_consumer_partial": len(
            units_with_real_consumer.difference(
                plan["blocked_unit_ids"], plan["baseline_closed_unit_ids"]
            )
        ),
    }
    unit_counts["candidate_or_open"] = (
        len(inputs.unit_dispositions) - sum(unit_counts.values())
    )
    burndown = {
        "schema": "curriculum.l1l6_lesson_burndown.v1",
        "generator": GENERATOR,
        "authority": authority,
        "current_state": {
            "lessons_total": len(inputs.lessons),
            "lessons_by_disposition": dict(sorted(disposition_counts.items())),
            "lessons_with_real_consumer_partial_evidence": len(
                set(real_lesson_ids) - set(plan["baseline_closed_lesson_ids"])
            ),
            "units_total": len(inputs.unit_dispositions),
            "units_by_disposition": unit_counts,
            "unit_overlays": {
                "parked_occurrence_grounding": len(plan["parked_unit_ids"]),
            },
            "readiness_report_lessons_fully_operationalized": (
                inputs.readiness.get("lessons_fully_operationalized")
            ),
            "readiness_report_basis": inputs.readiness.get(
                "lessons_fully_operationalized_basis"
            ),
        },
        "fusha_bench_axes": _bench_axes(inputs.bench_report),
        "forecast": {
            "lesson_flip_quota": quota,
            "future_tranches_total": len(plan["tranches"]),
            "tranches": [
                {
                    "tranche_number": row["tranche_number"] + 1,
                    "units": len(row["unit_ids"]),
                    "newly_flipped_lessons": len(row["newly_flipped_lesson_ids"]),
                    "residual": row["residual"],
                }
                for row in plan["tranches"]
            ],
            "projected_additional_fully_operationalized_lessons": sum(
                len(row["newly_flipped_lesson_ids"]) for row in plan["tranches"]
            ),
            "projected_total_fully_operationalized_lessons": (
                len(plan["baseline_closed_lesson_ids"])
                + sum(
                    len(row["newly_flipped_lesson_ids"])
                    for row in plan["tranches"]
                )
            ),
            "blocked_lessons": len(blocked_lessons),
            "not_applicable_lessons": len(plan["not_applicable_lesson_ids"]),
            "parked_occurrence_grounding_units": len(plan["parked_unit_ids"]),
            "assumption": (
                "projected lesson closure assumes units with parked occurrence "
                "grounding satisfy every non-occurrence closure dimension; "
                "parking is not occurrence evidence or certification"
            ),
        },
        "current_tranche": {
            "tranche_id": "tranche-001",
            "unit_ids": first["unit_ids"],
            "fully_operationalized_lesson_ids": first[
                "newly_flipped_lesson_ids"
            ],
            "units_fully_operationalized": len(current_closed_unit_ids),
            "units_still_partial": len(current_unit_ids) - len(
                current_closed_unit_ids
            ),
            "tranche_closed": (
                len(current_closed_unit_ids) == len(current_unit_ids)
                and len(first["newly_flipped_lesson_ids"]) >= quota
            ),
        },
    }
    return tranche, burndown


def _pretty_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def serialize_outputs(inputs: Inputs, *, quota: int = 9) -> dict[Path, bytes]:
    tranche, burndown = build_artifacts(inputs, quota=quota)
    return {
        TRANCHE_PATH: _pretty_bytes(tranche),
        BURNDOWN_PATH: _pretty_bytes(burndown),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write generated artifacts")
    mode.add_argument("--check", action="store_true", help="check byte freshness")
    parser.add_argument("--quota", type=int, default=9)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    root = args.root.resolve()
    outputs = serialize_outputs(load_inputs(root), quota=args.quota)
    if args.write:
        for relative, payload in sorted(outputs.items(), key=lambda item: str(item[0])):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            print(f"wrote {relative.as_posix()} ({len(payload)} bytes)")
        return 0
    if args.check:
        stale = []
        for relative, payload in sorted(outputs.items(), key=lambda item: str(item[0])):
            path = root / relative
            if not path.exists() or path.read_bytes() != payload:
                stale.append(relative.as_posix())
        if stale:
            print("FAIL: tranche artifacts differ: " + ", ".join(stale))
            return 1
        print("OK: tranche artifacts byte-identical to recompute")
        return 0
    tranche = json.loads(outputs[TRANCHE_PATH].decode("utf-8"))
    print(json.dumps({
        "mode": "read_only",
        "tranche_id": tranche["tranche_id"],
        "selected_units": len(tranche["units"]),
        "fully_operationalized_lessons": len(
            tranche["fully_operationalized_lesson_ids"]
        ),
        "fully_operationalized_units_current_state": len(
            tranche["current_state"]["closed_unit_ids"]
        ),
        "write_required": True,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
