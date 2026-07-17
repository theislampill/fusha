"""Fixture, registry, and committed-packet validator for FAM4."""

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
from tools import fam4_finite_verb_producer as producer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "qamus" / "examples" / "fam4-finite-verbs"
FORBIDDEN_TRACKED_PATTERNS = (
    r"[A-Za-z]:[\\/]",
    r"file://",
    r"/(?:srv|var)/",
    r"https?://",
)
REQUIRED_FIXTURES = {
    "label-only-tense-no-affix",
    "weak-hidden-radical",
    "derived-form-owner-gated",
    "subject-object-suffix-boundary",
    "nonverb-swept-into-family",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _finite(record: dict[str, Any]) -> dict[str, Any] | None:
    return next((fact for fact in record.get("facts", []) if fact.get("fact_type") == "finite_verb_evidence"), None)


def _pending(record: dict[str, Any]) -> dict[str, Any] | None:
    return next((fact for fact in record.get("facts", []) if fact.get("fact_type") == "finite_verb_pending"), None)


def validate_fixture_boundary(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    entries = _load_jsonl(fixtures_dir / "entry-fixtures.jsonl")
    fixtures = _load_jsonl(fixtures_dir / "producer-fixtures.jsonl")
    registry = producer.load_affix_registry(fixtures_dir / "verb-affix-registry.jsonl")
    weak_registry = producer.load_weak_root_registry(fixtures_dir / "weak-root-defeater-registry.jsonl")
    positives = [item for item in fixtures if item.get("expected_status") == "candidate"]
    negatives = [item for item in fixtures if item.get("expected_status") != "candidate"]
    if len(positives) < 6:
        _fail(errors, f"FAM4 fixture boundary has only {len(positives)} positive fixtures")
    if len(negatives) < 6:
        _fail(errors, f"FAM4 fixture boundary has only {len(negatives)} adversarial fixtures")
    if not REQUIRED_FIXTURES <= {str(item.get("fixture_id")) for item in fixtures}:
        _fail(errors, "FAM4 required adversarial fixture is missing")
    produced: dict[str, dict[str, Any]] = {}
    for item in fixtures:
        fixture_id = str(item.get("fixture_id"))
        try:
            record = producer.produce_record(item["row"], entries=entries, affix_registry=registry, weak_root_registry=weak_registry)
        except Exception as exc:
            _fail(errors, f"fixture {fixture_id} raised: {exc}")
            continue
        produced[fixture_id] = record
        record_errors = producer.validate_finite_verb_record(record)
        if record_errors:
            _fail(errors, f"fixture {fixture_id} failed typed validation: {'; '.join(record_errors[:4])}")
        expected_status = item.get("expected_status")
        if expected_status == "candidate":
            if record["projection"]["status"] != "candidate":
                _fail(errors, f"positive fixture {fixture_id} abstained")
            finite = _finite(record)
            if not finite or finite["fact_value"].get("pattern_id") != item.get("expected_pattern"):
                _fail(errors, f"positive fixture {fixture_id} lost its expected registered pattern")
        else:
            if record["projection"]["status"] == "candidate":
                _fail(errors, f"adversarial fixture {fixture_id} projected a candidate")
            if item.get("expected_blocker") not in _blockers(record):
                _fail(errors, f"fixture {fixture_id} lost blocker {item.get('expected_blocker')}")
            if record["projection"].get("claim") is not None:
                _fail(errors, f"adversarial fixture {fixture_id} projected a claim")
            if _finite(record) is not None:
                _fail(errors, f"adversarial fixture {fixture_id} emitted finite-verb evidence")

    object_record = produced.get("positive-object-suffix")
    subject_record = produced.get("positive-past-1cp-subject")
    if object_record and object_record["projection"]["status"] == "candidate":
        affixes = _finite(object_record)["fact_value"].get("affixes", [])
        if not affixes or affixes[-1].get("role") != "object_suffix" or affixes[-1].get("class") != "qg-object-pronoun":
            _fail(errors, "object suffix fixture was not typed as qg-object-pronoun")
    if subject_record and subject_record["projection"]["status"] == "candidate":
        affixes = _finite(subject_record)["fact_value"].get("affixes", [])
        if not affixes or affixes[-1].get("role") != "subject_marker" or affixes[-1].get("class") != "qg-subject-pronoun":
            _fail(errors, "subject suffix fixture was not typed as qg-subject-pronoun")

    registered = {item["projector_id"] for item in fact_projectors.REGISTRY.list_contracts()}
    if fact_projectors.FAM4_FINITE_VERB_PROJECTOR_ID not in registered:
        _fail(errors, "FAM4 finite-verb projector is not registered")
    else:
        projection = fact_projectors.REGISTRY.run(
            fact_projectors.FAM4_FINITE_VERB_PROJECTOR_ID,
            surface="جَعَلْنَا",
            root="ج ع ل",
            pattern_id="form_i.perfect_active.1cp_subject",
            affix_registry=registry,
        )
        if projection.get("status") != "candidate" or projection.get("materialization_allowed") is not False:
            _fail(errors, "registered FAM4 projector did not return a candidate-only result")

    for path in (
        fixtures_dir / "README.md",
        fixtures_dir / "verb-affix-registry.jsonl",
        fixtures_dir / "weak-root-defeater-registry.jsonl",
        fixtures_dir / "entry-fixtures.jsonl",
        fixtures_dir / "producer-fixtures.jsonl",
    ):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                _fail(errors, f"fixture contains forbidden external path pattern {pattern!r}: {path.name}")
    if list(fixtures_dir.rglob("*.png")):
        _fail(errors, "FAM4 fixtures contain tracked image artifacts")
    if not any(item.get("owner_next") == "derived_verbs" and item.get("transformation_registered") is False for item in weak_registry):
        _fail(errors, "weak-root registry lacks a future derived_verbs owner gate")
    return errors


def validate_packet(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    generated = fixtures_dir / "generated"
    sample_path = generated / "calibration-sample.jsonl"
    summary_path = generated / "calibration-summary.json"
    if not sample_path.exists() or not summary_path.exists():
        return ["generated FAM4 calibration packet is missing"]
    records = _load_jsonl(sample_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if len(records) != 12:
        _fail(errors, f"FAM4 calibration packet has {len(records)} rows, expected 12")
    candidates = [record for record in records if record.get("projection", {}).get("status") == "candidate"]
    unresolved = [record for record in records if record not in candidates]
    if summary.get("family_population") != 12 or summary.get("sample_size") != 12:
        _fail(errors, "FAM4 summary does not certify the full 12-row population")
    if summary.get("candidate_count") != len(candidates) or summary.get("unresolved_count") != len(unresolved):
        _fail(errors, "FAM4 summary counts do not match packet rows")
    if summary.get("candidate_mode") != "pre_apply_not_authorized" or summary.get("materialization") != "none":
        _fail(errors, "FAM4 summary is not candidate-only")
    if (summary.get("source_survey") or {}).get("all_rows_processed") != 12:
        _fail(errors, "FAM4 source survey does not cover all 12 rows")
    for index, record in enumerate(records):
        record_errors = producer.validate_finite_verb_record(record)
        if record_errors:
            _fail(errors, f"FAM4 calibration record {index} failed: {'; '.join(record_errors[:4])}")
        target = record.get("projection", {}).get("materialization_target", {})
        if target.get("public_materialization_allowed") or target.get("live_mutation_allowed"):
            _fail(errors, f"FAM4 calibration record {index} enables mutation")
    for name, expected_count in (
        ("finite-verb-facts.jsonl", len(candidates)),
        ("unresolved-records.jsonl", len(unresolved)),
        ("fixture-finite-verb-facts.jsonl", None),
        ("fixture-unresolved-records.jsonl", None),
    ):
        path = generated / name
        if not path.exists():
            _fail(errors, f"FAM4 calibration artifact missing: {name}")
            continue
        artifact_records = _load_jsonl(path)
        if expected_count is not None and len(artifact_records) != expected_count:
            _fail(errors, f"{name} count does not match packet")
        for index, record in enumerate(artifact_records):
            record_errors = producer.validate_finite_verb_record(record)
            if record_errors:
                _fail(errors, f"{name}:{index} failed: {'; '.join(record_errors[:4])}")
    if list(generated.rglob("*.png")):
        _fail(errors, "FAM4 generated packet contains image artifacts")
    for path in generated.glob("*.json*"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                _fail(errors, f"generated FAM4 artifact contains forbidden external path pattern {pattern!r}: {path.name}")
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
    print("FAM4 FINITE-VERB PRODUCER SELF-TEST PASS" if args.self_test else "FAM4 FINITE-VERB PRODUCER FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
