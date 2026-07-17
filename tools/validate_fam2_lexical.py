"""Fixture-only validator for the FAM2 lexical formation lane."""

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
from tools import fam2_lexical_producer as producer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "qamus" / "examples" / "fam2-lexical"
FORBIDDEN_TRACKED_PATTERNS = (
    r"[A-Za-z]:[\\/]",
    r"file://",
    r"/(?:srv|var)/",
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)


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
    required = {
        "sufaha-label-only-canary",
        "sound-plural-not-broken",
        "missing-singular-ababil",
        "noun-adjective-homograph",
    }
    if not required <= {item.get("fixture_id") for item in fixtures}:
        _fail(errors, "required FAM2 adversarial fixture is missing")
    produced: dict[str, dict[str, Any]] = {}
    for item in fixtures:
        try:
            record = producer.produce_record(item["row"], entries=entries, pattern_registry=patterns)
        except Exception as exc:
            _fail(errors, f"fixture {item.get('fixture_id')} raised: {exc}")
            continue
        produced[str(item["fixture_id"])] = record
        if producer.validate_formation_record(record):
            _fail(errors, f"fixture {item.get('fixture_id')} failed typed validation")
        if item.get("expected_status") == "candidate" and record["projection"]["status"] != "candidate":
            _fail(errors, f"positive fixture {item.get('fixture_id')} abstained")
        if item.get("expected_status") != "candidate":
            blocker_ids = {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers", [])
            }
            if item.get("expected_blocker") not in blocker_ids:
                _fail(errors, f"fixture {item.get('fixture_id')} lost blocker {item.get('expected_blocker')}")
            if record["projection"].get("claim") is not None:
                _fail(errors, f"fixture {item.get('fixture_id')} projected a claim")

    proof = produced.get("sufaha-proof")
    if proof is None:
        _fail(errors, "sufaha proof fixture did not produce a record")
    else:
        formation = next(
            fact for fact in proof["facts"] if fact.get("fact_type") == "formation_evidence"
        )
        value = formation["fact_value"]
        if proof["canonical_occurrence"]["quran_loc"] != "2:13:12":
            _fail(errors, "sufaha proof does not bind 2:13:12")
        if value.get("singular_surface") != "سَفِيه" or value.get("plural_surface") != "سُفَهَاء":
            _fail(errors, "sufaha proof lost the entry-backed singular/plural pair")
        if value.get("pattern_pair", {}).get("name") != "فَعِيل → فُعَلَاء":
            _fail(errors, "sufaha proof lost the named pattern pair")
        if value.get("reconstruction_proof", {}).get("passed") is not True:
            _fail(errors, "sufaha proof reconstruction did not pass")
        copy_view = proof["projection"]["public_payload"].get("learner_copy", {})
        if copy_view.get("n_lang_clean") is not True:
            _fail(errors, "sufaha learner copy failed N-LANG")
        if not copy_view.get("sarf", "").startswith("Ṣarf — how this piece forms the word"):
            _fail(errors, "sufaha learner copy lacks Ṣarf")
        if not copy_view.get("nahw", "").startswith("Naḥw — what this piece does here"):
            _fail(errors, "sufaha learner copy lacks Naḥw")

    canary = produced.get("sufaha-label-only-canary")
    if canary is None:
        _fail(errors, "sufaha label-only canary did not produce a record")
    else:
        if any(fact.get("fact_type") == "formation_evidence" for fact in canary["facts"]):
            _fail(errors, "sufaha label-only canary projected formation evidence")
        blocker_ids = {
            blocker["blocker_id"]
            for fact in canary["facts"]
            for blocker in fact.get("unresolved_blockers", [])
        }
        if "entry_lookup_missing" not in blocker_ids:
            _fail(errors, "sufaha label-only canary lacks entry_lookup_missing")

    registered = {item["projector_id"] for item in fact_projectors.REGISTRY.list_contracts()}
    if fact_projectors.FAM2_LEXICAL_PROJECTOR_ID not in registered:
        _fail(errors, "FAM2 projector is not registered")
    else:
        projection = fact_projectors.REGISTRY.run(
            fact_projectors.FAM2_LEXICAL_PROJECTOR_ID,
            singular_surface="سَفِيه",
            plural_surface="سُفَهَاء",
            pattern_id="broken.fa3il_to_fu3alaa",
            pattern_registry=patterns,
        )
        if projection.get("status") != "candidate" or projection.get("materialization_allowed") is not False:
            _fail(errors, "registered FAM2 projector did not return a candidate-only match")

    for path in (fixtures_dir / "pattern-registry.jsonl", fixtures_dir / "entry-fixtures.jsonl", fixtures_dir / "producer-fixtures.jsonl"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                _fail(errors, f"fixture contains forbidden external path pattern {pattern!r}: {path.name}")
    return errors


def validate_packet(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    generated = fixtures_dir / "generated"
    sample_path = generated / "calibration-sample.jsonl"
    if not sample_path.exists():
        return ["generated calibration packet is missing"]
    records = _load_jsonl(sample_path)
    if len(records) < 40:
        _fail(errors, f"calibration packet has only {len(records)} records")
    for index, record in enumerate(records):
        record_errors = producer.validate_formation_record(record)
        if record_errors:
            _fail(errors, f"calibration record {index} failed: {'; '.join(record_errors[:3])}")
    for name, expected_type in (
        ("formation-facts.jsonl", "projection_input"),
        ("unresolved-records.jsonl", "unresolved_projection"),
        ("fixture-formation-facts.jsonl", "projection_input"),
        ("fixture-unresolved-records.jsonl", "unresolved_projection"),
    ):
        path = generated / name
        if not path.exists():
            _fail(errors, f"calibration artifact missing: {name}")
            continue
        for index, record in enumerate(_load_jsonl(path)):
            if record.get("record_type") != expected_type:
                _fail(errors, f"{name}:{index} has wrong record_type")
            record_errors = producer.validate_formation_record(record)
            if record_errors:
                _fail(errors, f"{name}:{index} failed: {'; '.join(record_errors[:3])}")
    fixture_positive = _load_jsonl(generated / "fixture-formation-facts.jsonl")
    fixture_shapes = {
        next(
            fact["fact_value"]["sub_shape"]
            for fact in record["facts"]
            if fact.get("fact_type") == "formation_evidence"
        )
        for record in fixture_positive
    }
    if not producer.SUBSHAPES <= fixture_shapes:
        _fail(errors, "fixture formation packet does not span all six bounded sub-shapes")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args(argv)
    if not args.self_test and not args.fixtures:
        parser.error("--self-test or --fixtures is required")
    errors = validate_fixture_boundary(args.fixtures)
    if not errors and not args.self_test:
        errors.extend(validate_packet(args.fixtures))
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    if args.self_test:
        print("FAM2 LEXICAL PRODUCER SELF-TEST PASS")
    else:
        print("FAM2 LEXICAL PRODUCER FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
