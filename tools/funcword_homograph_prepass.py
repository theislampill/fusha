#!/usr/bin/env python3
"""Build the exact-diacritic v2 function-word candidate queue.

This is a candidate-generation pre-pass. It never edits the v1 queue or any
canonical Qamus artifact, and it deliberately stops at a homograph family when
sentence context is still needed to choose the function.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.jsonl"
DEFAULT_LOC_SURFACE = ROOT / "qamus/indexes/quran-loc-surface/index.jsonl"
DEFAULT_RULES = ROOT / "nahw/rules/funcword-homograph-prepass-rules.json"
DEFAULT_CALIBRATION = ROOT / ".inputs/funcword-review-cal.jsonl"
DEFAULT_OUTPUT_QUEUE = ROOT / "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.v2.jsonl"
DEFAULT_REPORT = ROOT / "qamus/reports/funcword-homograph-prepass.report.json"

RULE_SCHEMA = "qamus.funcword_homograph_prepass_rules.v1"
ROW_SCHEMA = "qamus.class2_funcword_candidate.v2"
REPORT_SCHEMA = "qamus.funcword_homograph_prepass_report.v1"
LILLAHI_NOTE = "lillahi_fused_divine_name"
REGEX_META = frozenset(".^$*+?{}[]\\|()")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank JSONL row: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row is not an object: {path}:{line_number}")
        rows.append(value)
    return rows


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def load_rules(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != RULE_SCHEMA:
        raise ValueError(f"unexpected rule schema: {payload.get('schema')!r}")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty array")

    seen_ids: set[str] = set()
    seen_surfaces: set[str] = set()
    validated = []
    for index, raw_rule in enumerate(rules, 1):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"rule {index} must be an object")
        rule = copy.deepcopy(raw_rule)
        rule_id = _require_nonempty_string(rule.get("rule_id"), f"rule {index} rule_id")
        if rule_id in seen_ids:
            raise ValueError(f"duplicate rule id: {rule_id}")
        seen_ids.add(rule_id)
        _require_nonempty_string(rule.get("from_particle_class"), f"{rule_id} from_particle_class")
        _require_nonempty_string(rule.get("after_particle_class"), f"{rule_id} after_particle_class")
        _require_nonempty_string(rule.get("reason"), f"{rule_id} reason")
        categories = rule.get("calibration_categories")
        if not isinstance(categories, list) or not categories:
            raise ValueError(f"{rule_id} calibration_categories must be non-empty")
        if any(not isinstance(item, str) or not item for item in categories):
            raise ValueError(f"{rule_id} calibration_categories must contain strings")
        surfaces = rule.get("exact_surfaces")
        if not isinstance(surfaces, list) or not surfaces:
            raise ValueError(f"{rule_id} exact_surfaces must be non-empty")
        for surface in surfaces:
            if not isinstance(surface, str) or not surface:
                raise ValueError(f"{rule_id} exact surface must be a non-empty string")
            if any(character in REGEX_META for character in surface):
                raise ValueError(f"{rule_id} exact surface must be literal: {surface!r}")
            if surface in seen_surfaces:
                raise ValueError(f"duplicate exact surface across rules: {surface!r}")
            seen_surfaces.add(surface)
        validated.append(rule)
    return validated


def _matching_rules(
    particle_class: str, canonical_surface: str, rules: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        rule
        for rule in rules
        if rule["from_particle_class"] == particle_class
        and canonical_surface in rule["exact_surfaces"]
    ]


def apply_prepass_row(
    row: dict[str, Any], canonical_surface: str, rules: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy(row)
    before = result.get("particle_class")
    if not isinstance(before, str) or not before:
        raise ValueError("queue row has no particle_class")
    target = result.get("target")
    if not isinstance(target, dict):
        raise ValueError("queue row has no target object")
    target["surface"] = canonical_surface

    matches = _matching_rules(before, canonical_surface, rules)
    if len(matches) > 1:
        location = target.get("canonical_location")
        raise ValueError(f"multiple pre-pass rules match {location}: {canonical_surface!r}")
    rule = matches[0] if matches else None
    after = rule["after_particle_class"] if rule else before

    result["schema"] = ROW_SCHEMA
    result["particle_class_before"] = before
    result["particle_class_after"] = after
    result["particle_class"] = after
    result["prepass_rule"] = rule["rule_id"] if rule else None
    if result.get("boundary_note") == LILLAHI_NOTE:
        result["boundary_route"] = "divine_name_entry"
    return result


def _index_unique(rows: Iterable[dict[str, Any]], field: str, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} row has no {field}")
        if value in indexed:
            raise ValueError(f"duplicate {label} {field}: {value}")
        indexed[value] = row
    return indexed


def _calibration_report(
    calibration_rows: list[dict[str, Any]],
    v2_by_loc: dict[str, dict[str, Any]],
    rules_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    citations = []
    residual = []
    for calibration in calibration_rows:
        location = calibration.get("canonical_location")
        if location not in v2_by_loc:
            raise ValueError(f"calibration location absent from v2 queue: {location}")
        result = v2_by_loc[location]
        rule_id = result["prepass_rule"]
        category = calibration.get("taxonomy_category")
        before = calibration.get("queue_particle_class")
        if rule_id and calibration.get("queue_class_agreement") == "mismatch":
            rule = rules_by_id[rule_id]
            reproduced = (
                before == result["particle_class_before"]
                and category in rule["calibration_categories"]
                and result["particle_class_after"] == rule["after_particle_class"]
            )
            citations.append({
                "calibration_category": category,
                "canonical_location": location,
                "homograph_correction_reproduced": reproduced,
                "particle_class_after": result["particle_class_after"],
                "particle_class_before": result["particle_class_before"],
                "prepass_rule": rule_id,
                "surface": result["target"]["surface"],
            })
        elif calibration.get("queue_class_agreement") != "match":
            residual.append({
                "canonical_location": location,
                "disposition": calibration.get("disposition"),
                "queue_class_agreement": calibration.get("queue_class_agreement"),
                "reason": "outside the three approved exact-diacritic homograph families",
                "surface": result["target"]["surface"],
                "taxonomy_category": category,
            })

    reproduced_count = sum(row["homograph_correction_reproduced"] for row in citations)
    shortfalls = [row for row in citations if not row["homograph_correction_reproduced"]]
    return {
        "agreement_basis": (
            "Exact-diacritic homograph correction: the pre-pass selects the calibrated lexeme "
            "family; sentence-context subclasses remain for nahw review."
        ),
        "citations": citations,
        "context_subclass_policy": (
            "Family-level only; this pre-pass does not guess conditional versus relative, "
            "interrogative, or negative function."
        ),
        "diacritic_decidable_rows": len(citations),
        "homograph_corrections_reproduced": reproduced_count,
        "minimum_required": 28,
        "residual_calibration_findings": residual,
        "shortfalls": shortfalls,
    }


def build_outputs(
    queue_rows: list[dict[str, Any]],
    loc_surface_rows: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    calibration_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    surface_by_loc = {
        location: row["surface"]
        for location, row in _index_unique(loc_surface_rows, "loc", "loc-surface").items()
    }
    v2_rows = []
    seen_locations: set[str] = set()
    for row in queue_rows:
        target = row.get("target")
        location = target.get("canonical_location") if isinstance(target, dict) else None
        if not isinstance(location, str) or not location:
            raise ValueError("queue row has no target canonical_location")
        if location in seen_locations:
            raise ValueError(f"duplicate queue location: {location}")
        seen_locations.add(location)
        if location not in surface_by_loc:
            raise ValueError(f"queue location absent from loc-surface index: {location}")
        v2_rows.append(apply_prepass_row(row, surface_by_loc[location], rules))

    v2_by_loc = {row["target"]["canonical_location"]: row for row in v2_rows}
    rules_by_id = {rule["rule_id"]: rule for rule in rules}
    rule_counts = Counter(row["prepass_rule"] for row in v2_rows if row["prepass_rule"])
    unchanged_count = sum(row["prepass_rule"] is None for row in v2_rows)
    boundary_count = sum(
        row.get("boundary_route") == "divine_name_entry" for row in v2_rows
    )
    report = {
        "artifact": "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.v2.jsonl",
        "boundary_routes": {"divine_name_entry": boundary_count},
        "calibration_agreement": _calibration_report(
            calibration_rows, v2_by_loc, rules_by_id
        ),
        "candidate_only": True,
        "generation_command": "python tools/funcword_homograph_prepass.py",
        "input_artifacts": {
            "calibration": ".inputs/funcword-review-cal.jsonl",
            "loc_surface": "qamus/indexes/quran-loc-surface/index.jsonl",
            "rules": "nahw/rules/funcword-homograph-prepass-rules.json",
            "v1_queue": "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.jsonl",
        },
        "per_rule_counts": {
            rule["rule_id"]: rule_counts.get(rule["rule_id"], 0) for rule in rules
        },
        "row_counts": {
            "changed": len(v2_rows) - unchanged_count,
            "total": len(v2_rows),
            "unchanged": unchanged_count,
        },
        "schema": REPORT_SCHEMA,
        "v1_queue_untouched": True,
    }
    agreement = report["calibration_agreement"]
    if agreement["homograph_corrections_reproduced"] < agreement["minimum_required"]:
        raise ValueError(
            "calibration agreement below minimum: "
            f"{agreement['homograph_corrections_reproduced']} < {agreement['minimum_required']}"
        )
    if boundary_count != 11:
        raise ValueError(f"expected 11 divine-name boundary routes, got {boundary_count}")
    return v2_rows, report


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    return text.encode("utf-8")


def pretty_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def write_outputs(
    v2_rows: list[dict[str, Any]],
    report: dict[str, Any],
    output_queue: Path,
    output_report: Path,
) -> None:
    output_queue.parent.mkdir(parents=True, exist_ok=True)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_queue.write_bytes(jsonl_bytes(v2_rows))
    output_report.write_bytes(pretty_json_bytes(report))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--loc-surface", type=Path, default=DEFAULT_LOC_SURFACE)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--output-queue", type=Path, default=DEFAULT_OUTPUT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.calibration.is_file():
        raise SystemExit(f"calibration input is required to build the report: {args.calibration}")
    v2_rows, report = build_outputs(
        read_jsonl(args.queue),
        read_jsonl(args.loc_surface),
        load_rules(args.rules),
        read_jsonl(args.calibration),
    )
    write_outputs(v2_rows, report, args.output_queue, args.report)
    agreement = report["calibration_agreement"]
    print(
        "FUNCWORD PREPASS PASS: "
        f"rows={report['row_counts']['total']} "
        f"changed={report['row_counts']['changed']} "
        f"calibration={agreement['homograph_corrections_reproduced']}/"
        f"{agreement['diacritic_decidable_rows']} "
        f"divine_name_routes={report['boundary_routes']['divine_name_entry']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
