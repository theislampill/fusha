#!/usr/bin/env python3
"""Validate Q7 tranche fixtures, exact parity, lineage, and row/hash round trips."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fact_ledger, tranche1_projection
from tools import validate_dependency_lattice
from tools import validate_morphosyntax_token_metadata


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "qamus" / "schemas"
EXPECTED_STATUS = {
    "3:141:4": "candidate",
    "24:31:76": "candidate",
    "2:34:5": "candidate",
    "39:63:3": "candidate",
    "22:18:9": "unresolved",
    "2:13:12": "source_gap",
    "7:54:23": "producer_pending",
    "5:2:12": "syntax_pending",
}
SCHEMA_FILES = {
    "fact-ledger.jsonl": "fact-ledger-row.schema.json",
    "morphology-lattice.jsonl": "morphology-candidate-lattice.schema.json",
    "dependency-lattice.jsonl": "dependency-candidate-lattice.schema.json",
    "morphosyntax-token.jsonl": "morphosyntax-token.schema.json",
    "canonical-hover-payload.jsonl": "canonical-hover-payload.schema.json",
    "public-hover-projections.jsonl": "public-hover-projection.schema.json",
    "projection-crosswalk.jsonl": "tranche1-projection-crosswalk.schema.json",
}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError("%s:%d: invalid JSON: %s" % (path.name, line_number, exc)) from exc
    return rows


def _read_raw_by_loc(path: Path, wanted: set[str] | None = None) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    rows: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            raw = line.rstrip("\r\n")
            if not raw:
                continue
            row = json.loads(raw)
            loc = row.get("loc")
            if wanted is not None and loc not in wanted:
                continue
            if loc in rows:
                raise ValueError("%s:%d: duplicate loc %s" % (path.name, line_number, loc))
            rows[loc] = (raw, row)
    return rows


def _schema(name: str) -> Dict[str, Any]:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    if name == "public-hover-projection.schema.json":
        boundary = json.loads((SCHEMA_DIR / "public-private-boundary.schema.json").read_text(encoding="utf-8"))
        schema = copy.deepcopy(schema)
        schema["properties"]["public_boundary"] = boundary
    return schema


def _schema_errors(row: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    fact_ledger._validate_node(row, schema, "$", errors, schema)
    return errors


def _loc_for(artifact: str, row: Dict[str, Any]) -> str:
    if artifact == "public-hover-projections.jsonl":
        return str(row.get("canonical_quran_loc"))
    if artifact == "canonical-hover-payload.jsonl":
        return str((row.get("private_trace") or {}).get("loc"))
    if artifact == "fact-ledger.jsonl":
        return str((row.get("subject_identity") or {}).get("loc"))
    if artifact == "morphology-lattice.jsonl":
        return str(row.get("token_ref"))
    if artifact == "dependency-lattice.jsonl":
        return str((row.get("source_unit") or {}).get("address", "")).removeprefix("quran:")
    return str(row.get("loc") or row.get("quran_loc"))


def _bare(surface: str) -> str:
    result = []
    for char in unicodedata.normalize("NFD", surface or ""):
        if char == "ٰ":
            result.append("ا")
        elif unicodedata.combining(char) or char == "ـ" or "\u06d6" <= char <= "\u06ed":
            continue
        else:
            result.append("ا" if char == "ٱ" else char)
    return "".join(result)


def _collect_flag_values(value: Any, key: str) -> List[Any]:
    found: List[Any] = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == key:
                found.append(child)
            found.extend(_collect_flag_values(child, key))
    elif isinstance(value, list):
        for child in value:
            found.extend(_collect_flag_values(child, key))
    return found


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        out = set(value)
        for child in value.values():
            out.update(_all_keys(child))
        return out
    if isinstance(value, list):
        out: set[str] = set()
        for child in value:
            out.update(_all_keys(child))
        return out
    return set()


def validate_tranche(
    fixture_dir: Path,
    whitelist_path: Path | None = None,
    source_commit: str | None = None,
) -> List[str]:
    """Return concrete validation errors; an empty list is a full fixture pass."""

    fixture_dir = Path(fixture_dir)
    errors: List[str] = []
    required = {
        "source-canaries.jsonl",
        "normalized-public-payload.jsonl",
        "unresolved-queue.jsonl",
        "dom-consumption.expectations.jsonl",
        "renderer-completeness.jsonl",
        "rich-hover-norm.jsonl",
        *SCHEMA_FILES,
    }
    missing = sorted(name for name in required if not (fixture_dir / name).is_file())
    if missing:
        return ["missing fixture artifact: " + name for name in missing]

    try:
        artifacts = {name: _read_jsonl(fixture_dir / name) for name in required if name != "source-canaries.jsonl"}
        fixture_source = _read_raw_by_loc(fixture_dir / "source-canaries.jsonl")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]

    # Structural schema checks, including embedded local $refs.
    for artifact, schema_name in SCHEMA_FILES.items():
        schema = _schema(schema_name)
        for index, row in enumerate(artifacts[artifact]):
            for message in _schema_errors(row, schema):
                errors.append("schema %s[%d]: %s" % (artifact, index, message))

    # Reuse the hard validators for their non-schema invariants.
    _n, morph_errors = validate_morphosyntax_token_metadata.validate_file(
        str(fixture_dir / "morphosyntax-token.jsonl")
    )
    errors.extend("morphosyntax: " + message for message in morph_errors)
    for index, lattice in enumerate(artifacts["dependency-lattice.jsonl"]):
        for condition, message in validate_dependency_lattice.validate_lattice(lattice):
            errors.append("dependency[%d] cond %s: %s" % (index, condition, message))

    normalized = artifacts["normalized-public-payload.jsonl"]
    projections = artifacts["public-hover-projections.jsonl"]
    queue = artifacts["unresolved-queue.jsonl"]
    crosswalk = artifacts["projection-crosswalk.jsonl"]
    dom = artifacts["dom-consumption.expectations.jsonl"]
    facts = artifacts["fact-ledger.jsonl"]
    canonical = artifacts["canonical-hover-payload.jsonl"]
    renderer = artifacts["renderer-completeness.jsonl"]
    rich = artifacts["rich-hover-norm.jsonl"]

    def by_loc(artifact: str, rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            loc = _loc_for(artifact, row)
            if loc in result:
                errors.append("duplicate %s row for %s" % (artifact, loc))
            result[loc] = row
        return result

    normalized_by_loc = by_loc("normalized-public-payload.jsonl", normalized)
    projection_by_loc = by_loc("public-hover-projections.jsonl", projections)
    queue_by_loc = by_loc("unresolved-queue.jsonl", queue)
    crosswalk_by_loc = by_loc("projection-crosswalk.jsonl", crosswalk)
    dom_by_loc = by_loc("dom-consumption.expectations.jsonl", dom)
    facts_by_loc = by_loc("fact-ledger.jsonl", facts)
    canonical_by_loc = by_loc("canonical-hover-payload.jsonl", canonical)
    renderer_by_loc = by_loc("renderer-completeness.jsonl", renderer)
    rich_by_loc = by_loc("rich-hover-norm.jsonl", rich)

    expected_locs = set(EXPECTED_STATUS)
    if set(normalized_by_loc) != expected_locs:
        errors.append("4+4 routing: normalized locations differ from the eight-canary policy")
    if len(projections) != 4 or set(projection_by_loc) != {loc for loc, status in EXPECTED_STATUS.items() if status == "candidate"}:
        errors.append("4+4 routing: expected exactly four candidate projections")
    queue_locs = {loc for loc, status in EXPECTED_STATUS.items() if status != "candidate"}
    if len(queue) != 4 or set(queue_by_loc) != queue_locs:
        errors.append("4+4 routing: expected exactly four typed queue records")
    if len(crosswalk) != 8 or set(crosswalk_by_loc) != expected_locs:
        errors.append("row/hash round trip: crosswalk must cover all eight locations exactly once")
    if len(fixture_source) != 8 or set(fixture_source) != expected_locs:
        errors.append("source parity: source-canaries must contain all eight exact rows")

    live_scan = [
        *normalized, *projections, *queue, *crosswalk, *dom, *facts, *canonical,
        *renderer, *rich, *artifacts["morphology-lattice.jsonl"],
        *artifacts["dependency-lattice.jsonl"], *artifacts["morphosyntax-token.jsonl"],
    ]
    if any(value is not False for row in live_scan for value in _collect_flag_values(row, "live_mutation_allowed")):
        errors.append("zero live mutation: every live_mutation_allowed flag must be false")
    if any(value is not False for row in live_scan for value in _collect_flag_values(row, "public_materialization_allowed")):
        errors.append("zero live mutation: every public_materialization_allowed flag must be false")

    whitelist_rows: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    if whitelist_path is not None:
        try:
            whitelist_rows = _read_raw_by_loc(Path(whitelist_path), expected_locs)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append("source parity: " + str(exc))
        if set(whitelist_rows) != expected_locs:
            errors.append("source parity: whitelist does not supply all eight exact rows")

    for loc, expected_status in EXPECTED_STATUS.items():
        source_pair = fixture_source.get(loc)
        normalized_row = normalized_by_loc.get(loc)
        crosswalk_row = crosswalk_by_loc.get(loc)
        fact_row = facts_by_loc.get(loc)
        dom_row = dom_by_loc.get(loc)
        if not all((source_pair, normalized_row, crosswalk_row, fact_row, dom_row)):
            continue
        source_raw, source_row = source_pair
        source_hash = tranche1_projection.raw_hash(source_raw)
        if source_row.get("surface") != normalized_row.get("surface"):
            errors.append("surface parity %s: normalized surface differs from source" % loc)
        if "".join(segment.get("surface", "") for segment in source_row.get("segments") or []) != source_row.get("surface"):
            errors.append("segment parity %s: source segments do not reconstruct source surface" % loc)
        if normalized_row.get("status") != expected_status or crosswalk_row.get("status") != expected_status:
            errors.append("4+4 routing %s: status differs from policy" % loc)
        if normalized_row.get("source_row_hash") != source_hash or crosswalk_row.get("source_row_hash") != source_hash:
            errors.append("row/hash round trip %s: source hash mismatch" % loc)
        if source_commit is not None:
            if normalized_row.get("source_commit") != source_commit or crosswalk_row.get("source_commit") != source_commit:
                errors.append("row/hash round trip %s: source commit mismatch" % loc)
        if whitelist_rows and loc in whitelist_rows:
            whitelist_raw, whitelist_row = whitelist_rows[loc]
            if whitelist_raw != source_raw or whitelist_row != source_row:
                errors.append("source parity %s: fixture source row differs byte-for-byte from whitelist" % loc)
        fact_ids = normalized_row.get("fact_ids")
        if fact_ids != [fact_row.get("fact_id")] or crosswalk_row.get("fact_ids") != fact_ids:
            errors.append("row/hash round trip %s: fact ID linkage mismatch" % loc)
        if fact_ledger.compute_fact_id(fact_row) != fact_row.get("fact_id"):
            errors.append("row/hash round trip %s: fact ID is not recomputable" % loc)
        if (normalized_row.get("producer"), normalized_row.get("projector_id"), normalized_row.get("version")) != (
            crosswalk_row.get("producer"), crosswalk_row.get("projector_id"), crosswalk_row.get("version")
        ):
            errors.append("row/hash round trip %s: producer/projector/version lineage mismatch" % loc)

        candidate = expected_status == "candidate"
        output_row = projection_by_loc.get(loc) if candidate else queue_by_loc.get(loc)
        if output_row is None:
            continue
        if tranche1_projection.row_hash(output_row) != crosswalk_row.get("output_row_hash"):
            errors.append("output hash %s: crosswalk does not round-trip to %s" % (loc, crosswalk_row.get("output_artifact")))
        expected_artifact = "public-hover-projections.jsonl" if candidate else "unresolved-queue.jsonl"
        if crosswalk_row.get("output_artifact") != expected_artifact:
            errors.append("row/hash round trip %s: output artifact mismatch" % loc)

        if candidate:
            public_segments = output_row.get("segments") or []
            if "".join(segment.get("surface", "") for segment in public_segments) != output_row.get("surface"):
                errors.append("segment parity %s: public segments do not reconstruct exact surface" % loc)
            source_segments = source_row.get("segments") or []
            mappings = crosswalk_row.get("field_mappings") or []
            if not (len(source_segments) == len(public_segments) == len(mappings)):
                errors.append("field mapping %s: segment and mapping counts differ" % loc)
            for index, (source_segment, public_segment, mapping) in enumerate(zip(source_segments, public_segments, mappings)):
                if public_segment.get("gloss") != source_segment.get("gloss_contribution") or mapping.get("gloss") != source_segment.get("gloss_contribution"):
                    errors.append("field mapping %s segment %d: gloss_contribution -> gloss drift" % (loc, index))
                if public_segment.get("qg_class") != source_segment.get("class") or mapping.get("qg_class") != source_segment.get("class"):
                    errors.append("field mapping %s segment %d: class -> qg_class drift" % (loc, index))
            if normalized_row.get("public_payload", {}).get("segments") != public_segments:
                errors.append("row/hash round trip %s: normalized/public segment payload drift" % loc)
            if not dom_row.get("hover_expected") or dom_row.get("live_dom_assertion_performed") is not False:
                errors.append("DOM expectation %s: candidate must be fixture-expected without live assertion" % loc)
            if dom_row.get("expected_qg_classes") != [segment.get("class") for segment in source_segments]:
                errors.append("DOM expectation %s: qg class expectations drift from source" % loc)
            canonical_row = canonical_by_loc.get(loc)
            renderer_row = renderer_by_loc.get(loc)
            rich_row = rich_by_loc.get(loc)
            if not all((canonical_row, renderer_row, rich_row)):
                errors.append("row/hash round trip %s: candidate sidecar is missing" % loc)
            else:
                if canonical_row.get("public_payload") != renderer_row.get("public_payload"):
                    errors.append("row/hash round trip %s: canonical/renderer payload drift" % loc)
                if rich_row.get("learner_explanation") != output_row.get("learner_explanation"):
                    errors.append("row/hash round trip %s: rich learner text drift" % loc)
        else:
            if not output_row.get("blocker") or not isinstance(output_row.get("route"), dict):
                errors.append("4+4 routing %s: typed queue record lacks blocker or route" % loc)
            if "public_payload" in output_row or "public_payload" in normalized_row:
                errors.append("4+4 routing %s: unresolved row must not carry a public payload" % loc)
            if dom_row.get("hover_expected") is not False or dom_row.get("expected_qg_classes") != []:
                errors.append("DOM expectation %s: queued row must not be consumed" % loc)

    source_gap = queue_by_loc.get("2:13:12", {})
    for forbidden_key in ("root", "candidate_root", "template", "singular", "morphline", "segments", "public_payload"):
        if forbidden_key in _all_keys(source_gap):
            errors.append("source_gap 2:13:12: guessed field %s is present" % forbidden_key)
    if queue_by_loc.get("7:54:23", {}).get("status") != "producer_pending":
        errors.append("producer pending 7:54:23: generic source segment did not remain queued")
    if queue_by_loc.get("5:2:12", {}).get("status") != "syntax_pending":
        errors.append("syntax pending 5:2:12: no-evidence syntax canary did not remain queued")
    if _bare(fixture_source.get("39:63:3", ("", {}))[1].get("surface", "")) != _bare(
        fixture_source.get("22:18:9", ("", {}))[1].get("surface", "")
    ):
        errors.append("same-surface parity: positive and adversarial heavens rows do not share a bare surface")
    if queue_by_loc.get("22:18:9", {}).get("status") != "unresolved":
        errors.append("same-surface parity: fused adversary did not remain unresolved")

    return errors


def _counts(fixture_dir: Path) -> Tuple[int, int, int]:
    normalized = _read_jsonl(fixture_dir / "normalized-public-payload.jsonl")
    candidates = sum(row.get("status") == "candidate" for row in normalized)
    return len(normalized), candidates, len(normalized) - candidates


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_dir", type=Path)
    parser.add_argument("--whitelist", type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args(argv)
    errors = validate_tranche(args.fixture_dir, args.whitelist, args.source_commit)
    if errors:
        print("TRANCHE1 VALIDATION FAIL")
        for error in errors:
            print("FAIL - " + error)
        print("SUMMARY errors=%d" % len(errors))
        return 1
    total, candidates, queued = _counts(args.fixture_dir)
    print("TRANCHE1 VALIDATION PASS")
    print("PASS - schema validation: all typed fixture rows conform")
    print("PASS - exact source surface and segment parity: 8/8")
    print("PASS - exact gloss_contribution/class to gloss/qg_class mapping: 4/4 candidates")
    print("PASS - row/hash round trip: 8/8 source and output hashes recompute")
    print("PASS - routing: 4 candidate projections + 4 typed queue records")
    print("PASS - DOM consumption expectations: 4 consume + 4 abstain; live assertions 0")
    print("PASS - same-surface adversary: segmented candidate + fused unresolved")
    print("PASS - live mutation authorization: 0")
    print("SUMMARY canonical=%d candidates=%d queued=%d errors=0" % (total, candidates, queued))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
