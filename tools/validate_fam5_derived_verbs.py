"""Fixture, registry, and committed-packet validator for FAM5."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fact_projectors
from tools import fam5_derived_verb_producer as producer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "qamus" / "examples" / "fam5-derived-verbs"
FORBIDDEN_TRACKED_PATTERNS = (
    r"[A-Za-z]:[\\/]",
    r"file://",
    r"/(?:srv|var)/",
    r"https?://",
)
REQUIRED_FIXTURES = {
    "surface-template-only",
    "form-viii-naive-assimilation",
    "form-viii-naive-gemination-split",
    "passive-diacritic-mismatch",
    "energic-boundary-missing",
    "quadriliteral-forced-triliteral",
    "hamzat-al-wasl-unmarked",
    "weak-root-transformation-missing",
}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)


def _blockers(record: dict[str, Any]) -> set[str]:
    return {
        str(blocker.get("blocker_id"))
        for fact in record.get("facts", [])
        for blocker in fact.get("unresolved_blockers", [])
        if isinstance(blocker, dict) and blocker.get("blocker_id")
    }


def validate_fixture_boundary(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    entries = _jsonl(fixtures_dir / "entry-fixtures.jsonl")
    fixtures = _jsonl(fixtures_dir / "producer-fixtures.jsonl")
    registry = producer.load_derived_form_registry(fixtures_dir / "derived-form-registry.jsonl")
    positives = [item for item in fixtures if item.get("expected_status") == "candidate"]
    negatives = [item for item in fixtures if item.get("expected_status") != "candidate"]
    if len(positives) < 6:
        _fail(errors, f"FAM5 fixture boundary has only {len(positives)} positive fixtures")
    if len(negatives) < 8:
        _fail(errors, f"FAM5 fixture boundary has only {len(negatives)} adversarial fixtures")
    if not REQUIRED_FIXTURES <= {str(item.get("fixture_id")) for item in fixtures}:
        _fail(errors, "FAM5 required adversarial fixture is missing")
    produced: dict[str, dict[str, Any]] = {}
    for item in fixtures:
        fixture_id = str(item.get("fixture_id"))
        try:
            record = producer.produce_record(item["row"], entries=entries, form_registry=registry)
        except Exception as exc:
            _fail(errors, f"fixture {fixture_id} raised: {exc}")
            continue
        produced[fixture_id] = record
        record_errors = producer.validate_derived_verb_record(record)
        if record_errors:
            _fail(errors, f"fixture {fixture_id} failed typed validation: {'; '.join(record_errors[:4])}")
        if item.get("expected_status") == "candidate":
            if record["projection"]["status"] != "candidate":
                _fail(errors, f"positive fixture {fixture_id} abstained")
            derived = next((fact for fact in record["facts"] if fact.get("fact_type") == "derived_verb_evidence"), None)
            if not derived or (derived.get("fact_value") or {}).get("template", {}).get("pattern_id") != item.get("expected_pattern"):
                _fail(errors, f"positive fixture {fixture_id} lost its expected registered pattern")
        else:
            if record["projection"]["status"] == "candidate":
                _fail(errors, f"adversarial fixture {fixture_id} projected a candidate")
            if item.get("expected_blocker") not in _blockers(record):
                _fail(errors, f"fixture {fixture_id} lost blocker {item.get('expected_blocker')}")
            if record["projection"].get("claim") is not None:
                _fail(errors, f"adversarial fixture {fixture_id} projected a claim")
    geminate = produced.get("positive-form-viii-passive-geminate")
    if geminate:
        value = next(fact for fact in geminate["facts"] if fact.get("fact_type") == "derived_verb_evidence")["fact_value"]
        if value.get("gemination", {}).get("treatment") != "C_shared_written_letter":
            _fail(errors, "Form-VIII positive lost Treatment-C gemination discipline")
        if sum(1 for segment in value.get("surface_segments", []) if segment.get("letter") == "ث") != 1:
            _fail(errors, "Form-VIII positive naively split the written geminate")
    registered = {item["projector_id"] for item in fact_projectors.REGISTRY.list_contracts()}
    if fact_projectors.FAM5_DERIVED_VERB_PROJECTOR_ID not in registered:
        _fail(errors, "FAM5 derived-verb projector is not registered")
    else:
        projection = fact_projectors.REGISTRY.run(
            fact_projectors.FAM5_DERIVED_VERB_PROJECTOR_ID,
            surface="أَكْمَلْتُ",
            root="ك م ل",
            pattern_id="derived.form_iv.perfect_active.1cs",
            form_registry=registry,
            entry_surface="أَكْمَلْتُ",
            evidence_certified=True,
            v575_verified=True,
        )
        if projection.get("status") != "candidate" or projection.get("materialization_allowed") is not False:
            _fail(errors, "registered FAM5 projector did not return a candidate-only result")
        abstained = fact_projectors.REGISTRY.run(
            fact_projectors.FAM5_DERIVED_VERB_PROJECTOR_ID,
            surface="دَرَّسَ",
            root="د ر س",
            pattern_id="derived.form_ii.perfect_active.3ms",
            form_registry=registry,
            entry_surface=None,
            evidence_certified=False,
            v575_verified=True,
        )
        if abstained.get("status") != "abstained" or abstained.get("route") != "source_gap":
            _fail(errors, "FAM5 projector allowed a surface-only claim")
    for path in (
        fixtures_dir / "README.md",
        fixtures_dir / "derived-form-registry.jsonl",
        fixtures_dir / "entry-fixtures.jsonl",
        fixtures_dir / "producer-fixtures.jsonl",
    ):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                _fail(errors, f"fixture contains forbidden external path pattern {pattern!r}: {path.name}")
    if list(fixtures_dir.rglob("*.png")):
        _fail(errors, "FAM5 fixtures contain image artifacts")
    return errors


def validate_packet(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    generated = fixtures_dir / "generated"
    sample_path = generated / "calibration-sample.jsonl"
    summary_path = generated / "calibration-summary.json"
    if not sample_path.exists() or not summary_path.exists():
        return ["generated FAM5 calibration packet is missing"]
    records = _jsonl(sample_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if len(records) != 7:
        _fail(errors, f"FAM5 calibration packet has {len(records)} rows, expected 7")
    candidates = [record for record in records if record.get("projection", {}).get("status") == "candidate"]
    unresolved = [record for record in records if record not in candidates]
    if summary.get("working_set_count") != 7 or summary.get("candidate_count") != len(candidates) or summary.get("abstention_count") != len(unresolved):
        _fail(errors, "FAM5 summary counts do not match packet rows")
    expected_forms = {
        "II": {"population": 1, "candidate": 0, "abstention": 1},
        "IV": {"population": 4, "candidate": 1, "abstention": 3},
        "VIII": {"population": 1, "candidate": 1, "abstention": 0},
        "quadriliteral": {"population": 1, "candidate": 1, "abstention": 0},
    }
    if summary.get("forms") != expected_forms:
        _fail(errors, f"FAM5 form-class precision/abstention metrics drifted: {summary.get('forms')!r}")
    if summary.get("mode") != "candidate_only" or summary.get("authorization_state") != "pre_apply_not_authorized":
        _fail(errors, "FAM5 summary is not candidate-only")
    if len(summary.get("source_survey") or []) != 7 or len(summary.get("row_outcomes") or []) != 7:
        _fail(errors, "FAM5 source survey does not cover all seven rows")
    for index, record in enumerate(records):
        record_errors = producer.validate_derived_verb_record(record)
        if record_errors:
            _fail(errors, f"FAM5 calibration record {index} failed: {'; '.join(record_errors[:4])}")
        target = record.get("projection", {}).get("materialization_target", {})
        if target.get("public_materialization_allowed") or target.get("live_mutation_allowed"):
            _fail(errors, f"FAM5 calibration record {index} enables mutation")
    for name, expected_count in (("derived-verb-facts.jsonl", len(candidates) * 2), ("unresolved-records.jsonl", len(unresolved))):
        path = generated / name
        if not path.exists():
            _fail(errors, f"FAM5 calibration artifact missing: {name}")
            continue
        artifact_records = _jsonl(path)
        if len(artifact_records) != expected_count:
            _fail(errors, f"{name} count is {len(artifact_records)}, expected {expected_count}")
        if name == "unresolved-records.jsonl":
            for index, record in enumerate(artifact_records):
                record_errors = producer.validate_derived_verb_record(record)
                if record_errors:
                    _fail(errors, f"{name}:{index} failed: {'; '.join(record_errors[:4])}")
    if list(generated.rglob("*.png")):
        _fail(errors, "FAM5 generated packet contains image artifacts")
    for path in generated.glob("*.json*"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                _fail(errors, f"generated FAM5 artifact contains forbidden external path pattern {pattern!r}: {path.name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args(argv)
    errors = validate_fixture_boundary(args.fixtures)
    if not errors and not args.self_test:
        errors.extend(validate_packet(args.fixtures))
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print("FAM5 DERIVED-VERB PRODUCER SELF-TEST PASS" if args.self_test else "FAM5 DERIVED-VERB PRODUCER FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
