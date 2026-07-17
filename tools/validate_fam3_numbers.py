"""Fixture and packet validator for the FAM3 number-word producer."""

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
from tools import fam3_number_producer as producer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "qamus" / "examples" / "fam3-numbers"
FORBIDDEN_TRACKED_PATTERNS = (
    r"[A-Za-z]:[\\/]",
    r"file://",
    r"/(?:srv|var)/",
)
REQUIRED_FIXTURES = {
    "label-only-ordinal",
    "wrong-gender-seven",
    "homograph-seven-number-lion",
    "context-only-entry",
}
REPORT_SUBSHAPES = {
    "bare_cardinal",
    "gender_polarity_cardinal",
    "ordinals",
    "compound_11_19",
    "tens",
    "fractions",
    "first_last_edge",
    "other_number_form",
    "unclassified",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)


def _blocker_ids(record: dict[str, Any]) -> set[str]:
    return {
        str(blocker["blocker_id"])
        for fact in record.get("facts", [])
        for blocker in fact.get("unresolved_blockers", [])
        if isinstance(blocker, dict) and blocker.get("blocker_id")
    }


def _formation(record: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (fact for fact in record.get("facts", []) if fact.get("fact_type") == "formation_evidence"),
        None,
    )


def _pending(record: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (fact for fact in record.get("facts", []) if fact.get("fact_type") == "number_formation_pending"),
        None,
    )


def _validate_candidate(record: dict[str, Any], fixture_id: str, errors: list[str]) -> None:
    formation = _formation(record)
    if record.get("projection", {}).get("status") != "candidate" or formation is None:
        _fail(errors, f"positive fixture {fixture_id} did not produce a candidate formation fact")
        return
    value = formation.get("fact_value") or {}
    proof = value.get("reconstruction_proof") or {}
    payload = record["projection"].get("public_payload") or {}
    learner = payload.get("learner_copy") or {}
    if formation.get("evidence_mode") != "paired_form_inference":
        _fail(errors, f"positive fixture {fixture_id} lacks paired_form_inference")
    if proof.get("passed") is not True or not proof.get("source_addresses"):
        _fail(errors, f"positive fixture {fixture_id} lacks reconstruction proof")
    source_addresses = (formation.get("source_evidence") or {}).get("source_addresses", [])
    if not any(str(item.get("address", "")).startswith("entry:") for item in source_addresses):
        _fail(errors, f"positive fixture {fixture_id} lacks entry source address")
    if not any(str(item.get("address", "")).startswith("registry:") for item in source_addresses):
        _fail(errors, f"positive fixture {fixture_id} lacks registry source address")
    if payload.get("authorization_state") != "pre_apply_not_authorized":
        _fail(errors, f"positive fixture {fixture_id} is not candidate-only")
    if payload.get("public_materialization_allowed") is True or payload.get("live_mutation_allowed") is True:
        _fail(errors, f"positive fixture {fixture_id} enables mutation")
    if not str(learner.get("payload_id", "")).startswith("fd.fam3.payload:"):
        _fail(errors, f"positive fixture {fixture_id} lacks FAM3 learner payload namespace")
    if learner.get("n_lang_clean") is not True:
        _fail(errors, f"positive fixture {fixture_id} learner copy is not N-LANG clean")
    if "Ṣarf — how this piece forms the word" not in str(learner.get("sarf", "")):
        _fail(errors, f"positive fixture {fixture_id} lacks public Ṣarf label")
    if "Naḥw — what this piece does here" not in str(learner.get("nahw", "")):
        _fail(errors, f"positive fixture {fixture_id} lacks public Naḥw label")


def validate_fixture_boundary(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    entries = _load_jsonl(fixtures_dir / "entry-fixtures.jsonl")
    fixtures = _load_jsonl(fixtures_dir / "producer-fixtures.jsonl")
    patterns = producer.load_pattern_registry(fixtures_dir / "pattern-registry.jsonl")
    positives = [item for item in fixtures if item.get("expected_status") == "candidate"]
    negatives = [item for item in fixtures if item.get("expected_status") != "candidate"]
    if len(positives) < 6:
        _fail(errors, f"fixture boundary has only {len(positives)} positives")
    if len(negatives) < 6:
        _fail(errors, f"fixture boundary has only {len(negatives)} adversarial negatives")
    fixture_ids = {str(item.get("fixture_id")) for item in fixtures}
    if not REQUIRED_FIXTURES <= fixture_ids:
        _fail(errors, "required FAM3 adversarial fixture is missing")
    produced: dict[str, dict[str, Any]] = {}
    for item in fixtures:
        fixture_id = str(item.get("fixture_id"))
        try:
            record = producer.produce_record(item["row"], entries=entries, pattern_registry=patterns)
        except Exception as exc:
            _fail(errors, f"fixture {fixture_id} raised: {exc}")
            continue
        produced[fixture_id] = record
        record_errors = producer.validate_number_record(record)
        if record_errors:
            _fail(errors, f"fixture {fixture_id} failed typed validation: {'; '.join(record_errors[:3])}")
        if item.get("expected_status") == "candidate":
            _validate_candidate(record, fixture_id, errors)
            formation = _formation(record)
            if formation and formation.get("fact_value", {}).get("sub_shape") != item.get("expected_sub_shape"):
                _fail(errors, f"positive fixture {fixture_id} changed sub-shape")
        else:
            if record.get("projection", {}).get("status") == "candidate":
                _fail(errors, f"adversarial fixture {fixture_id} projected a candidate")
            if item.get("expected_blocker") not in _blocker_ids(record):
                _fail(errors, f"fixture {fixture_id} lost blocker {item.get('expected_blocker')}")
            if record.get("projection", {}).get("claim") is not None:
                _fail(errors, f"adversarial fixture {fixture_id} projected a claim")
            if _formation(record) is not None:
                _fail(errors, f"adversarial fixture {fixture_id} emitted formation evidence")

    homograph = produced.get("homograph-seven-number-lion")
    if homograph and "homograph_ambiguity" not in _blocker_ids(homograph):
        _fail(errors, "homograph fixture did not retain its ambiguity blocker")
    label_only = produced.get("label-only-ordinal")
    if label_only and "entry_lookup_missing" not in _blocker_ids(label_only):
        _fail(errors, "label-only ordinal did not route to entry_lookup_missing")

    registered = {item["projector_id"] for item in fact_projectors.REGISTRY.list_contracts()}
    if fact_projectors.FAM3_NUMBER_PROJECTOR_ID not in registered:
        _fail(errors, "FAM3 number projector is not registered")
    else:
        projection = fact_projectors.REGISTRY.run(
            fact_projectors.FAM3_NUMBER_PROJECTOR_ID,
            base_surface="أَلْف",
            observed_surface="أُلُوف",
            pattern_id="cardinal.base_to_number_form",
            context={"entry_direct": True},
            pattern_registry=patterns,
        )
        if projection.get("status") != "candidate" or projection.get("materialization_allowed") is not False:
            _fail(errors, "registered FAM3 projector did not return a candidate-only match")

    for path in (
        fixtures_dir / "pattern-registry.jsonl",
        fixtures_dir / "entry-fixtures.jsonl",
        fixtures_dir / "producer-fixtures.jsonl",
    ):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                _fail(errors, f"fixture contains forbidden external path pattern {pattern!r}: {path.name}")
    return errors


def validate_packet(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    generated = fixtures_dir / "generated"
    sample_path = generated / "calibration-sample.jsonl"
    summary_path = generated / "calibration-summary.json"
    if not sample_path.exists() or not summary_path.exists():
        return ["generated calibration packet is missing"]
    records = _load_jsonl(sample_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if len(records) != 57:
        _fail(errors, f"calibration packet has {len(records)} records, expected 57")
    candidates = [record for record in records if record.get("projection", {}).get("status") == "candidate"]
    unresolved = [record for record in records if record not in candidates]
    if summary.get("sample_size") != 57 or summary.get("family_population") != 57:
        _fail(errors, "calibration summary does not certify the full 57-row family")
    if summary.get("candidate_count") != len(candidates) or summary.get("unresolved_count") != len(unresolved):
        _fail(errors, "calibration summary counts do not match the packet")
    if summary.get("candidate_mode") != "pre_apply_not_authorized" or summary.get("materialization") != "none":
        _fail(errors, "calibration summary is not candidate-only")
    populations = summary.get("sub_shape_populations") or {}
    if not REPORT_SUBSHAPES <= set(populations):
        _fail(errors, "calibration summary lacks a required number sub-shape bucket")
    if sum(int(item.get("population", 0)) for item in populations.values()) != 57:
        _fail(errors, "sub-shape populations do not sum to 57")
    for index, record in enumerate(records):
        record_errors = producer.validate_number_record(record)
        if record_errors:
            _fail(errors, f"calibration record {index} failed: {'; '.join(record_errors[:3])}")
        target = record.get("projection", {}).get("materialization_target", {})
        if target.get("public_materialization_allowed") or target.get("live_mutation_allowed"):
            _fail(errors, f"calibration record {index} enables mutation")
    for name, expected_type in (
        ("formation-facts.jsonl", "projection_input"),
        ("unresolved-records.jsonl", None),
        ("fixture-formation-facts.jsonl", "projection_input"),
        ("fixture-unresolved-records.jsonl", None),
    ):
        path = generated / name
        if not path.exists():
            _fail(errors, f"calibration artifact missing: {name}")
            continue
        artifact_records = _load_jsonl(path)
        expected_records = candidates if name == "formation-facts.jsonl" else unresolved if name == "unresolved-records.jsonl" else artifact_records
        if name == "formation-facts.jsonl" and len(artifact_records) != len(candidates):
            _fail(errors, "formation artifact count does not match candidates")
        if name == "unresolved-records.jsonl" and len(artifact_records) != len(unresolved):
            _fail(errors, "unresolved artifact count does not match abstentions")
        for index, record in enumerate(artifact_records):
            if expected_type and record.get("record_type") != expected_type:
                _fail(errors, f"{name}:{index} has wrong record_type")
            record_errors = producer.validate_number_record(record)
            if record_errors:
                _fail(errors, f"{name}:{index} failed: {'; '.join(record_errors[:3])}")
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
    print("FAM3 NUMBER PRODUCER SELF-TEST PASS" if args.self_test else "FAM3 NUMBER PRODUCER FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
