#!/usr/bin/env python3
"""Promote the committed largelexicon @1 tables onto their unchanged target schemas.

The committed @1 tables are IMMUTABLE migration inputs: this tool never writes a
byte into them, never edits a target schema, and never weakens a schema to accept
legacy output. It deterministically derives, for every source identity, exactly
one disposition:

``carried``      the migrated candidate satisfies the unchanged target schema;
``flagged``      a structural migration blocker (row-forbidden extra field that
                 carries semantic content a schema/owner decision must place);
``quarantined``  a semantic blocker (risk flags, root shape, surface shape, stem
                 annotation completeness) or a boundary-constant divergence.

Losslessness is proved, not asserted: every source identity appears exactly once
across the three dispositions, with a source locator and a source-row hash.

Row-forbidden constants are hoisted, never dropped:

* the four *safety* constants (``live_mutation_allowed``, ``public_boundary``,
  ``source``, ``source_status``) become validated manifest-level provenance. A row
  whose safety constant diverges from the canonical boundary is QUARANTINED — the
  public/source/live boundary is never weakened by hoisting;
* the varying *derivation* provenance (``resolution_*``) becomes a manifest-level
  variant table with a stable ``provenance_variant_id`` recorded per accounted row,
  so no row loses provenance to the migration.

Carried rows are regenerable, not duplicated into the tree: the committed release
carries their canonical digest, a bounded sample lands under
``qamus/indexes/largelexicon/target-schema/``, and ``--emit-carried`` writes the
full tables under gitignored ``out/`` for consumers that want them on disk.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

# The largelexicon tool family imports flat sibling modules; keep that working
# whether this module is loaded as ``promote_...`` or as ``tools.promote_...``.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_largelexicon_rows as validator  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = "tools/promote_largelexicon_target_schema.py"
TARGET_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "target-schema"
RELEASE_NAME = "TARGET-RELEASE.json"
RELEASE_SCHEMA = "qamus/largelexicon-target-release@1"
LEDGER_ROW_SCHEMA = "qamus/largelexicon-target-disposition-row@1"
LEDGER_META_SCHEMA = "qamus/largelexicon-target-disposition-meta@1"
SAMPLE_ROW_SCHEMA = "qamus/largelexicon-target-carried-sample@1"
DEFAULT_CARRIED_DIR = ROOT / "out" / "largelexicon-target-schema"
SAMPLE_PER_FAMILY = 4
# Bounded committed sample per (disposition, family). The FULL ledgers are large
# regenerable outputs and live under gitignored out/ per the sample-plus-generator
# rule; the release carries their canonical digests so nothing is unverifiable.
LEDGER_SAMPLE_PER_FAMILY = 5

DISPOSITIONS = ("carried", "flagged", "quarantined")

IDENTITY_FIELDS = {
    "lemma-source": "entry_id",
    "form-source": "form_id",
    "stem-source": "stem_id",
    "qword-denominator": "row_id",
    "qword-crosswalk": "row_id",
}

# The row-forbidden safety constants. These define the public/source/live
# boundary and are hoisted to manifest level only while every row agrees.
BOUNDARY_CONSTANT_FIELDS = ("live_mutation_allowed", "public_boundary", "source", "source_status")
CANONICAL_BOUNDARY = {
    "live_mutation_allowed": False,
    "public_boundary": {"kind": "authored", "lang": "en", "src": "qamus"},
    "source": "qamus_current_authored",
    "source_status": "qamus_current_authored",
}

# Row-forbidden derivation provenance. Genuinely varying, so it is hoisted into a
# manifest-level variant table rather than collapsed into one constant.
DERIVATION_PROVENANCE_FIELDS = (
    "resolution_normalizer",
    "resolution_source",
    "resolution_wbw_lookup_built_at",
    "resolution_wbw_lookup_sha256",
)

HOISTED_FIELDS = frozenset(BOUNDARY_CONSTANT_FIELDS) | frozenset(DERIVATION_PROVENANCE_FIELDS)

SEMANTIC_DEFECT_FAMILIES = frozenset(
    {"risk_flags", "root_shape_or_reason", "surface_shape", "stem_annotation_completeness"}
)

BOUNDARY_DIVERGENCE = "boundary_constant_divergence"


class PromotionError(RuntimeError):
    """Raised when the migration cannot proceed without losing or laundering data."""


def canonical_line(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def review_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def row_sha256(row: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_text(row).encode("utf-8")).hexdigest()


def surface_field(family_name: str) -> str:
    if family_name == "lemma-source":
        return "lemma"
    if family_name.startswith("qword-"):
        return "visible_surface"
    return "surface"


def target_row_schema(family: validator.Family) -> str:
    return validator.read_json(ROOT / family.schema_path)["properties"]["schema"]["const"]


def provenance_variant(source: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return the stable id and payload of a row's hoisted derivation provenance."""

    payload = {field: source[field] for field in DERIVATION_PROVENANCE_FIELDS if field in source}
    if not payload:
        return "pv-none", payload
    digest = hashlib.sha256(canonical_text(payload).encode("utf-8")).hexdigest()
    return "pv-" + digest[:16], payload


def ledger_record(family_name: str, identity_field: str, accounting: dict[str, Any]) -> dict[str, Any]:
    """The canonical disposition record for one non-carried identity."""

    return {
        "defect_families": accounting["defect_families"],
        "disposition": accounting["disposition"],
        "family": family_name,
        "identity": accounting[identity_field],
        "identity_field": identity_field,
        "provenance_variant_id": accounting["provenance_variant_id"],
        "reasons": accounting["reasons"],
        "schema": LEDGER_ROW_SCHEMA,
        "source_locator": accounting["source_locator"],
        "source_row_sha256": accounting["source_row_sha256"],
    }


def deterministic_sample(rows: list[dict[str, Any]], per_family: int = LEDGER_SAMPLE_PER_FAMILY) -> list[dict[str, Any]]:
    """The first ``per_family`` rows of each family in canonical order. Deterministic."""

    seen: Counter[str] = Counter()
    sample: list[dict[str, Any]] = []
    for row in rows:
        family = str(row["family"])
        if seen[family] < per_family:
            seen[family] += 1
            sample.append(row)
    return sample


def bind_ledger_records(
    actual: list[dict[str, Any]], expected: dict[tuple[str, str], dict[str, Any]], *, label: str
) -> list[str]:
    """Bind ledger records to the recomputed expectation, field by field.

    Counts and duplicate checks are not enough: a substituted identity, a tampered
    source-row hash, a rewritten reason and a swapped provenance variant can all
    keep counts intact. Every record is matched by (family, identity) and then
    compared field-for-field against the value recomputed from the immutable
    source rows.
    """

    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(actual):
        key = (str(row.get("family")), str(row.get("identity")))
        if key in seen:
            problems.append(f"{label}[{index}]: duplicate ledger record for {key[0]}/{key[1]}")
            continue
        seen.add(key)
        want = expected.get(key)
        if want is None:
            problems.append(
                f"{label}[{index}]: {key[0]}/{key[1]} is not a recomputed non-carried identity (extra or substituted)"
            )
            continue
        for field in sorted(want):
            if row.get(field) != want[field]:
                problems.append(
                    "%s[%d]: %s/%s field %r does not match the recomputation" % (label, index, key[0], key[1], field)
                )
        if set(row) != set(want):
            problems.append(
                "%s[%d]: %s/%s carries unexpected or missing fields %s"
                % (label, index, key[0], key[1], sorted(set(row) ^ set(want)))
            )
    return problems


def boundary_divergences(source: dict[str, Any]) -> list[str]:
    """Names of safety constants whose row value is not the canonical boundary."""

    return sorted(
        field
        for field in BOUNDARY_CONSTANT_FIELDS
        if field in source and source[field] != CANONICAL_BOUNDARY[field]
    )


def field_changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field in sorted(set(before) | set(after)):
        if field not in before:
            changes.append(
                {"field": field, "kind": "added", "reason": "target structural requirement", "value": after[field]}
            )
        elif field not in after:
            reason = "hoisted to manifest provenance" if field in HOISTED_FIELDS else "target row-schema boundary"
            changes.append({"field": field, "kind": "removed", "reason": reason, "value": before[field]})
        elif before[field] != after[field]:
            changes.append(
                {
                    "after": after[field],
                    "before": before[field],
                    "field": field,
                    "kind": "changed",
                    "reason": "target schema migration",
                }
            )
    return changes


def migrate_candidate(
    family: validator.Family, source: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Deterministically derive the target-schema candidate for one @1 source row."""

    candidate = copy.deepcopy(source)
    candidate["schema"] = target_row_schema(family)
    for field in sorted(validator.ROW_CONSTANT_FIELDS):
        candidate.pop(field, None)

    field = surface_field(family.name)
    if any(character.isspace() for character in str(candidate.get(field, ""))):
        marker = "lemma_is_multiword" if family.name == "lemma-source" else "surface_is_multiword"
        candidate[marker] = True
        candidate["multiword_reason"] = "source @1 surface contains whitespace; semantic split not migrated"

    if family.name == "stem-source":
        annotations = (candidate.get("pattern"), candidate.get("form"), candidate.get("features"))
        if annotations == (None, None, {}):
            for name in ("pattern", "form", "features"):
                candidate.pop(name, None)
    return candidate, field_changes(source, candidate)


def classify_disposition(
    errors: list[dict[str, str]], divergences: list[str]
) -> tuple[str, list[str]]:
    """Assign exactly one disposition and its precise reasons."""

    if divergences:
        return "quarantined", [f"{BOUNDARY_DIVERGENCE}: {name}" for name in divergences]
    if not errors:
        return "carried", ["candidate satisfies the unchanged target schema"]
    defect_families = sorted({error["defect_family"] for error in errors})
    if SEMANTIC_DEFECT_FAMILIES.intersection(defect_families):
        return "quarantined", [f"semantic review required: {name}" for name in defect_families]
    return "flagged", [f"structural migration blocker: {name}" for name in defect_families]


def assert_single_source_version(family_name: str, versions: Counter[str]) -> None:
    """Reject a source table that mixes row-schema versions."""

    if len(versions) != 1:
        raise PromotionError(
            "mixed source row-schema versions in %s: %s"
            % (family_name, ",".join(sorted(versions)))
        )


def assert_single_carried_version(family_name: str, versions: Counter[str], expected: str) -> None:
    """Reject carried output that mixes versions or misses the target version."""

    if len(versions) > 1:
        raise PromotionError(
            "mixed carried row-schema versions in %s: %s" % (family_name, ",".join(sorted(versions)))
        )
    if versions and next(iter(versions)) != expected:
        raise PromotionError(
            "carried rows in %s declare %s, not the target %s"
            % (family_name, next(iter(versions)), expected)
        )


def assert_lossless_accounting(
    source_ids: list[str], accounted: list[dict[str, Any]], identity_field: str
) -> None:
    """Every source identity has exactly one disposition and zero silent drops."""

    accounted_ids = [str(row[identity_field]) for row in accounted]
    source_duplicates = sorted(key for key, count in Counter(source_ids).items() if count != 1)
    duplicates = sorted(key for key, count in Counter(accounted_ids).items() if count != 1)
    missing = sorted(set(source_ids) - set(accounted_ids))
    extra = sorted(set(accounted_ids) - set(source_ids))
    invalid = sorted(
        str(row.get(identity_field, "<missing>"))
        for row in accounted
        if row.get("disposition") not in DISPOSITIONS
    )
    problems: list[str] = []
    if source_duplicates:
        problems.append("source_duplicate=" + ",".join(source_duplicates))
    if duplicates:
        problems.append("duplicate=" + ",".join(duplicates))
    if missing:
        problems.append("missing=" + ",".join(missing))
    if extra:
        problems.append("extra=" + ",".join(extra))
    if invalid:
        problems.append("invalid_disposition=" + ",".join(invalid))
    if problems:
        raise PromotionError("losslessness accounting failed: " + "; ".join(problems))


def iter_family_dispositions(
    family: validator.Family,
) -> Iterator[tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]]:
    """Yield ``(source, carried_or_none, accounting)`` for every row of one family."""

    schema = validator.read_json(ROOT / family.schema_path)
    identity_field = IDENTITY_FIELDS[family.name]
    target = schema["properties"]["schema"]["const"]
    for source_path, line_no, source in validator.iter_family_rows(family):
        candidate, changes = migrate_candidate(family, source)
        errors = validator.schema_errors(candidate, schema)
        divergences = boundary_divergences(source)
        disposition, reasons = classify_disposition(errors, divergences)
        variant_id, _payload = provenance_variant(source)
        accounting = {
            "change_codes": [f"{change['kind']}:{change['field']}" for change in changes],
            "defect_families": sorted({error["defect_family"] for error in errors}),
            "disposition": disposition,
            "family": family.name,
            identity_field: str(source[identity_field]),
            "provenance_variant_id": variant_id,
            "reasons": reasons,
            "source_locator": f"{source_path}:{line_no}",
            "source_row_sha256": row_sha256(source),
            "source_row_schema": source.get("schema"),
        }
        carried = candidate if disposition == "carried" else None
        if carried is not None and carried.get("schema") != target:
            raise PromotionError(
                "carried row %s does not declare the target schema" % accounting[identity_field]
            )
        yield source, carried, accounting


def carried_rows(family: validator.Family) -> Iterator[dict[str, Any]]:
    """Regenerate the carried target-schema rows of one family, in manifest order."""

    for _source, carried, _accounting in iter_family_dispositions(family):
        if carried is not None:
            yield carried


def source_snapshot() -> dict[str, str]:
    paths: set[Path] = {ROOT / "qamus" / "indexes" / "largelexicon" / "RELEASE.json"}
    for family in validator.FAMILIES:
        paths.update(validator.family_paths(family))
        paths.add(ROOT / family.schema_path)
        if family.manifest_path:
            paths.add(ROOT / family.manifest_path)
    return {path.relative_to(ROOT).as_posix(): validator.sha256_file(path) for path in sorted(paths)}


def git_head() -> str:
    """Reported for humans only. It is deliberately NOT part of the release payload:
    binding a commit sha would make the release stale after every unrelated commit,
    while the per-path source_sha256 map already binds the exact inputs."""

    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def promote(*, carried_sink: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the full migration and return the release plus both disposition ledgers."""

    baseline = source_snapshot()
    current_release = validator.read_json(validator.RELEASE_PATH)
    tables: dict[str, Any] = {}
    flagged: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    accounted_total = 0
    source_total = 0

    for family in validator.FAMILIES:
        identity_field = IDENTITY_FIELDS[family.name]
        target = target_row_schema(family)
        source_ids: list[str] = []
        accounted: list[dict[str, Any]] = []
        source_versions: Counter[str] = Counter()
        carried_versions: Counter[str] = Counter()
        variants: dict[str, dict[str, Any]] = {}
        variant_counts: Counter[str] = Counter()
        boundary_seen: dict[str, Any] = {}
        boundary_present: Counter[str] = Counter()
        counts: Counter[str] = Counter()
        reason_counts: Counter[str] = Counter()
        carried_digest = hashlib.sha256()
        carried_count = 0
        sink = None if carried_sink is None else carried_sink.setdefault(family.name, [])

        for source, carried, accounting in iter_family_dispositions(family):
            source_ids.append(str(source[identity_field]))
            accounted.append(accounting)
            source_versions[str(source.get("schema"))] += 1
            variant_id = accounting["provenance_variant_id"]
            variant_counts[variant_id] += 1
            if variant_id not in variants:
                variants[variant_id] = provenance_variant(source)[1]
            for field in BOUNDARY_CONSTANT_FIELDS:
                if field in source:
                    boundary_present[field] += 1
                    boundary_seen.setdefault(field, source[field])
            counts[accounting["disposition"]] += 1
            reason_counts.update(accounting["reasons"])
            if carried is not None:
                carried_versions[str(carried["schema"])] += 1
                carried_digest.update(canonical_line(carried))
                carried_count += 1
                if len(samples) < SAMPLE_PER_FAMILY * (list(validator.FAMILIES).index(family) + 1):
                    samples.append({"family": family.name, "row": carried, "schema": SAMPLE_ROW_SCHEMA})
                if sink is not None:
                    sink.append(carried)
            else:
                record = ledger_record(family.name, identity_field, accounting)
                (flagged if accounting["disposition"] == "flagged" else quarantined).append(record)

        assert_single_source_version(family.name, source_versions)
        assert_single_carried_version(family.name, carried_versions, target)
        assert_lossless_accounting(source_ids, accounted, identity_field)

        # Exact per-family coverage: every one of the four safety constants is
        # declared present-on-every-row or explicitly absent from the family. A
        # partially present constant is a migration defect, not a silent subset.
        row_total = len(source_ids)
        hoisted_boundary: dict[str, Any] = {}
        for field in BOUNDARY_CONSTANT_FIELDS:
            present = boundary_present.get(field, 0)
            if present == 0:
                hoisted_boundary[field] = {
                    "coverage": "absent_from_family",
                    "rows_present": 0,
                    "rows_total": row_total,
                    "value": None,
                }
                continue
            if present != row_total:
                raise PromotionError(
                    "boundary constant %s is present on only %d of %d %s rows"
                    % (field, present, row_total, family.name)
                )
            if boundary_seen[field] != CANONICAL_BOUNDARY[field]:
                raise PromotionError(
                    "manifest-level boundary constant %s for %s is not canonical" % (field, family.name)
                )
            hoisted_boundary[field] = {
                "coverage": "all_rows",
                "rows_present": present,
                "rows_total": row_total,
                "value": boundary_seen[field],
            }

        current = current_release["tables"][family.name]
        tables[family.name] = {
            "carried_row_count": carried_count,
            "carried_sha256": carried_digest.hexdigest(),
            "carried_sha256_scope": "canonical compact target-schema JSONL bytes for carried rows in manifest order",
            "disposition_counts": {name: counts.get(name, 0) for name in DISPOSITIONS},
            "identity_field": identity_field,
            "provenance": {
                "boundary_constants": hoisted_boundary,
                "derivation_variants": [
                    {"provenance_variant_id": key, "row_count": variant_counts[key], "values": variants[key]}
                    for key in sorted(variants)
                ],
            },
            "reason_counts": dict(sorted(reason_counts.items())),
            "source": {
                "path": family.row_path or family.manifest_path,
                "row_count": len(source_ids),
                "row_schema": next(iter(source_versions)),
                "sha256": current["sha256"],
                "storage": current["storage"],
            },
            "target_row_schema": target,
            "target_schema_path": family.schema_path,
            "target_schema_sha256": validator.sha256_file(ROOT / family.schema_path),
            "validation": {
                "pass_rows": carried_count,
                "validated_against": "unchanged committed target schema",
                "violation_rows": 0,
            },
        }
        totals.update(counts)
        accounted_total += len(accounted)
        source_total += len(source_ids)

    if source_snapshot() != baseline:
        raise PromotionError("immutability invariant failed: a committed source byte changed during promotion")

    release = {
        "baseline": {"source_sha256": baseline},
        "carried_output": {
            "committed_sample": "qamus/indexes/largelexicon/target-schema/carried-rows.sample.jsonl",
            "full_output_policy": "regenerable; write with --emit-carried into gitignored out/ (sample + generator rule)",
            "generator": TOOL_PATH,
        },
        "ledgers": {
            name: ledger_release_entry(name, rows)
            for name, rows in (("flagged", flagged), ("quarantined", quarantined))
        },
        "determinism": {"stable_input_order": True, "stable_json_keys": True, "timestamps_omitted": True},
        "immutability": {
            "committed_sources_byte_untouched": True,
            "live_mutation_allowed": False,
            "target_schemas_modified": False,
        },
        "losslessness": {
            "accounted_row_count": accounted_total,
            "disposition_counts": {name: totals.get(name, 0) for name in DISPOSITIONS},
            "silent_drop_count": 0,
            "source_row_count": source_total,
        },
        "schema": RELEASE_SCHEMA,
        "supersedes_posture": {
            "note": (
                "qamus/indexes/largelexicon/RELEASE.json continues to describe the immutable @1 tables and "
                "honestly reports their target-schema violations; this release describes the derived carried "
                "target-schema tables only"
            ),
            "v1_release_path": "qamus/indexes/largelexicon/RELEASE.json",
        },
        "tables": tables,
    }
    return {"flagged": flagged, "quarantined": quarantined, "release": release, "samples": samples}


def ledger_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_line(row) for row in rows)


def ledger_release_entry(disposition: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Canonical custody record: full-ledger digest plus the bounded sample digest."""

    sample = deterministic_sample(rows)
    return {
        "committed_sample_path": f"qamus/indexes/largelexicon/target-schema/{disposition}-identities.sample.jsonl",
        "defect_family_counts": dict(
            sorted(Counter(name for row in rows for name in row["defect_families"]).items())
        ),
        "disposition": disposition,
        "family_counts": dict(sorted(Counter(row["family"] for row in rows).items())),
        "full_output_path": f"out/largelexicon-target-schema/{disposition}-identities.jsonl",
        "full_output_policy": (
            "large regenerable output; the full ledger is written under gitignored out/ by "
            "--write or --emit-carried, and is bound here by canonical digest"
        ),
        "reason_counts": dict(sorted(Counter(reason for row in rows for reason in row["reasons"]).items())),
        "row_count": len(rows),
        "row_schema": LEDGER_ROW_SCHEMA,
        "sample_rule": f"first {LEDGER_SAMPLE_PER_FAMILY} records of each family in canonical order",
        "sample_row_count": len(sample),
        "sample_sha256": hashlib.sha256(ledger_bytes(sample)).hexdigest(),
        "sha256": hashlib.sha256(ledger_bytes(rows)).hexdigest(),
        "sha256_scope": "canonical compact JSONL bytes of the complete ledger in family/manifest order",
    }


def ledger_meta(rows: list[dict[str, Any]], disposition: str, serialized: bytes) -> dict[str, Any]:
    """Pretty sidecar for the COMMITTED bounded sample, hash-bound to the full ledger."""

    sample = deterministic_sample(rows)
    sample_bytes = ledger_bytes(sample)
    return {
        "disposition": disposition,
        "full_ledger_row_count": len(rows),
        "full_ledger_sha256": hashlib.sha256(serialized).hexdigest(),
        "full_output_path": f"out/largelexicon-target-schema/{disposition}-identities.jsonl",
        "generator": TOOL_PATH,
        "note": (
            "bounded committed sample; the complete ledger is a large regenerable output kept under "
            "gitignored out/ and bound by full_ledger_sha256"
        ),
        "row_count": len(sample),
        "row_schema": LEDGER_ROW_SCHEMA,
        "sample_family_counts": dict(sorted(Counter(row["family"] for row in sample).items())),
        "sample_rule": f"first {LEDGER_SAMPLE_PER_FAMILY} records of each family in canonical order",
        "schema": LEDGER_META_SCHEMA,
        "sha256": hashlib.sha256(sample_bytes).hexdigest(),
    }


def sample_meta(samples: list[dict[str, Any]], serialized: bytes) -> dict[str, Any]:
    return {
        "family_counts": dict(sorted(Counter(row["family"] for row in samples).items())),
        "generator": TOOL_PATH,
        "note": "illustrative carried rows only; regenerate the full tables with --emit-carried",
        "row_count": len(samples),
        "row_schema": SAMPLE_ROW_SCHEMA,
        "schema": "qamus/largelexicon-target-carried-sample-meta@1",
        "sha256": hashlib.sha256(serialized).hexdigest(),
    }


def rendered_artifacts(result: dict[str, Any]) -> dict[str, bytes]:
    """Only bounded, reviewable artifacts are tracked. Full ledgers go to out/."""

    artifacts: dict[str, bytes] = {RELEASE_NAME: review_json(result["release"]).encode("utf-8")}
    for disposition in ("flagged", "quarantined"):
        rows = result[disposition]
        full_bytes = ledger_bytes(rows)
        sample_bytes = ledger_bytes(deterministic_sample(rows))
        artifacts[f"{disposition}-identities.sample.jsonl"] = sample_bytes
        artifacts[f"{disposition}-identities.sample.meta.json"] = review_json(
            ledger_meta(rows, disposition, full_bytes)
        ).encode("utf-8")
    carried_sample_bytes = ledger_bytes(result["samples"])
    artifacts["carried-rows.sample.jsonl"] = carried_sample_bytes
    artifacts["carried-rows.sample.meta.json"] = review_json(
        sample_meta(result["samples"], carried_sample_bytes)
    ).encode("utf-8")
    return artifacts


def write_artifacts(target_dir: Path, artifacts: dict[str, bytes]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        (target_dir / name).write_bytes(payload)


def emit_ledgers(directory: Path, result: dict[str, Any]) -> dict[str, str]:
    """Write the FULL ledgers under gitignored out/ and return their digests."""

    if not directory.resolve().is_relative_to((ROOT / "out").resolve()):
        raise PromotionError("full ledgers may only be written under the gitignored out/ tree")
    directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for disposition in ("flagged", "quarantined"):
        payload = ledger_bytes(result[disposition])
        (directory / f"{disposition}-identities.jsonl").write_bytes(payload)
        written[disposition] = hashlib.sha256(payload).hexdigest()
    return written


def emit_carried(directory: Path, carried: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for family_name, rows in sorted(carried.items()):
        payload = ledger_bytes(rows)
        path = directory / f"{family_name}.target.jsonl"
        path.write_bytes(payload)
        written[family_name] = hashlib.sha256(payload).hexdigest()
    return written


# --------------------------------------------------------------------------- #
# freshness gate — consumers must fail closed on a stale or validation-red release
# --------------------------------------------------------------------------- #
def release_path(target_dir: Path | None = None) -> Path:
    return (target_dir or TARGET_DIR) / RELEASE_NAME


def read_release(target_dir: Path | None = None) -> dict[str, Any]:
    path = release_path(target_dir)
    if not path.exists():
        raise PromotionError("target-schema release is absent: " + path.relative_to(ROOT).as_posix())
    return validator.read_json(path)


def release_blockers(release: dict[str, Any], *, snapshot: dict[str, str] | None = None) -> list[str]:
    """Return every reason a consumer must refuse this release. Empty means usable."""

    blockers: list[str] = []
    if release.get("schema") != RELEASE_SCHEMA:
        blockers.append("release schema is not " + RELEASE_SCHEMA)
        return blockers
    current = snapshot if snapshot is not None else source_snapshot()
    tables = release.get("tables") or {}
    for family in validator.FAMILIES:
        item = tables.get(family.name)
        if item is None:
            blockers.append(f"{family.name}: absent from the target release")
            continue
        expected_schema_sha = current.get(family.schema_path)
        if item.get("target_schema_sha256") != expected_schema_sha:
            blockers.append(f"{family.name}: target schema changed since the release was built")
        if item.get("target_row_schema") != target_row_schema(family):
            blockers.append(f"{family.name}: released target row schema is stale")
        validation = item.get("validation") or {}
        if validation.get("violation_rows") != 0:
            blockers.append(f"{family.name}: release is validation-red")
        if validation.get("pass_rows") != item.get("carried_row_count"):
            blockers.append(f"{family.name}: pass_rows does not equal the carried row count")
        boundary = (item.get("provenance") or {}).get("boundary_constants") or {}
        if set(boundary) != set(CANONICAL_BOUNDARY):
            blockers.append(
                f"{family.name}: boundary provenance must declare all four safety constants explicitly"
            )
        for field, entry in sorted(boundary.items()):
            if field not in CANONICAL_BOUNDARY or not isinstance(entry, dict):
                blockers.append(f"{family.name}: boundary constant {field} is not a declared coverage record")
                continue
            coverage = entry.get("coverage")
            if coverage == "absent_from_family":
                if entry.get("rows_present") != 0 or entry.get("value") is not None:
                    blockers.append(f"{family.name}: boundary constant {field} claims absence inconsistently")
            elif coverage == "all_rows":
                if entry.get("value") != CANONICAL_BOUNDARY[field]:
                    blockers.append(f"{family.name}: hoisted boundary constant {field} is not canonical")
                if entry.get("rows_present") != entry.get("rows_total") or not entry.get("rows_total"):
                    blockers.append(f"{family.name}: boundary constant {field} is only partially covered")
            else:
                blockers.append(f"{family.name}: boundary constant {field} has an unknown coverage {coverage!r}")
    released_sources = (release.get("baseline") or {}).get("source_sha256") or {}
    for path, digest in sorted(released_sources.items()):
        if current.get(path) != digest:
            blockers.append(f"{path}: committed bytes changed since the release was built")
    for path in sorted(set(current) - set(released_sources)):
        blockers.append(f"{path}: source is not bound by the release baseline")
    return blockers


def assert_release_usable(release: dict[str, Any], *, snapshot: dict[str, str] | None = None) -> None:
    blockers = release_blockers(release, snapshot=snapshot)
    if blockers:
        raise PromotionError("target-schema release is not usable: " + "; ".join(blockers))


def carried_table(family_name: str, *, target_dir: Path | None = None) -> list[dict[str, Any]]:
    """Read-through accessor: regenerate one carried table behind the freshness gate."""

    release = read_release(target_dir)
    assert_release_usable(release)
    family = next(item for item in validator.FAMILIES if item.name == family_name)
    rows = list(carried_rows(family))
    digest = hashlib.sha256(ledger_bytes(rows)).hexdigest()
    if digest != release["tables"][family_name]["carried_sha256"]:
        raise PromotionError(f"{family_name}: regenerated carried rows do not match the released digest")
    return rows


# --------------------------------------------------------------------------- #
# self-test
# --------------------------------------------------------------------------- #
def _expect_error(callable_: Any, expected: str, assertions: list[int]) -> None:
    try:
        callable_()
    except PromotionError as error:
        assert expected in str(error), f"expected {expected!r} in {error}"
        assertions[0] += 1
    else:
        raise AssertionError("red-first fixture was not rejected: " + expected)


def run_self_test() -> int:
    assertions = [0]
    lemma = next(item for item in validator.FAMILIES if item.name == "lemma-source")

    # --- lossless accounting: missing, duplicate and unknown dispositions fail ---
    source_ids = ["row-a", "row-b", "row-c"]
    accounted = [
        {"row_id": "row-a", "disposition": "carried"},
        {"row_id": "row-b", "disposition": "flagged"},
        {"row_id": "row-c", "disposition": "quarantined"},
    ]
    assert_lossless_accounting(source_ids, accounted, "row_id")
    assertions[0] += 1
    _expect_error(lambda: assert_lossless_accounting(source_ids, accounted[:-1], "row_id"), "missing=row-c", assertions)
    _expect_error(
        lambda: assert_lossless_accounting(source_ids, [*accounted, accounted[0]], "row_id"),
        "duplicate=row-a",
        assertions,
    )
    _expect_error(
        lambda: assert_lossless_accounting(
            source_ids, [*accounted[:-1], {"row_id": "row-c", "disposition": "lost"}], "row_id"
        ),
        "invalid_disposition=row-c",
        assertions,
    )
    _expect_error(
        lambda: assert_lossless_accounting(source_ids, [*accounted, {"row_id": "row-d", "disposition": "carried"}], "row_id"),
        "extra=row-d",
        assertions,
    )
    _expect_error(
        lambda: assert_lossless_accounting(["row-a", "row-a"], [accounted[0]], "row_id"),
        "source_duplicate=row-a",
        assertions,
    )

    # --- mixed schema versions fail closed on both sides ---
    _expect_error(
        lambda: assert_single_source_version("lemma-source", Counter({"@1": 2, "@2": 1})),
        "mixed source row-schema versions",
        assertions,
    )
    _expect_error(
        lambda: assert_single_carried_version("lemma-source", Counter({"a@2": 1, "a@1": 1}), "a@2"),
        "mixed carried row-schema versions",
        assertions,
    )
    _expect_error(
        lambda: assert_single_carried_version("lemma-source", Counter({"a@1": 1}), "a@2"),
        "not the target",
        assertions,
    )

    # --- boundary divergence quarantines; it never rides through as carried ---
    good = validator.good_rows()["lemma-source"]
    legacy = copy.deepcopy(good)
    legacy["schema"] = "fusha/largelexicon/lemma-source@1"
    legacy.update(
        {
            "live_mutation_allowed": False,
            "public_boundary": {"kind": "authored", "lang": "en", "src": "qamus"},
            "source_status": "qamus_current_authored",
        }
    )
    candidate, changes = migrate_candidate(lemma, legacy)
    schema = validator.read_json(ROOT / lemma.schema_path)
    assert not validator.schema_errors(candidate, schema), "clean legacy row must migrate carried"
    assert classify_disposition([], boundary_divergences(legacy))[0] == "carried"
    assertions[0] += 1
    assert {change["field"] for change in changes if change["kind"] == "removed"} == {
        "live_mutation_allowed",
        "public_boundary",
        "source_status",
    }
    assertions[0] += 1

    for field, bad in (
        ("live_mutation_allowed", True),
        ("public_boundary", {"kind": "imported", "lang": "en", "src": "external"}),
        ("source_status", "external_import"),
    ):
        diverged = copy.deepcopy(legacy)
        diverged[field] = bad
        divergences = boundary_divergences(diverged)
        assert divergences == [field], divergences
        disposition, reasons = classify_disposition([], divergences)
        assert disposition == "quarantined", (field, disposition)
        assert reasons == [f"{BOUNDARY_DIVERGENCE}: {field}"], reasons
        assertions[0] += 1

    # --- varying derivation provenance keeps a distinct hoisted variant id ---
    first = dict(legacy, resolution_source="local_wbw_lookup_surface_alignment")
    second = dict(legacy, resolution_source="two_vote_review_adjudication")
    assert provenance_variant(first)[0] != provenance_variant(second)[0]
    assert provenance_variant(first)[0] == provenance_variant(dict(first))[0]
    assert provenance_variant(legacy)[0] == "pv-none"
    assertions[0] += 1

    # --- semantic vs structural disposition split ---
    assert classify_disposition([{"defect_family": "risk_flags"}], [])[0] == "quarantined"
    assert classify_disposition([{"defect_family": "additional_property"}], [])[0] == "flagged"
    assert classify_disposition([], [])[0] == "carried"
    assertions[0] += 1

    # --- a stale or validation-red release must be refused by consumers ---
    snapshot = {"qamus/schemas/x.json": "aaa", "qamus/data/y.jsonl": "bbb"}
    fake_family_names = [family.name for family in validator.FAMILIES]
    healthy_tables = {
        name: {
            "carried_row_count": 3,
            "provenance": {
                "boundary_constants": {
                    field: {"coverage": "all_rows", "rows_present": 3, "rows_total": 3, "value": value}
                    for field, value in CANONICAL_BOUNDARY.items()
                }
            },
            "target_row_schema": target_row_schema(
                next(item for item in validator.FAMILIES if item.name == name)
            ),
            "target_schema_sha256": "schema-sha-" + name,
            "validation": {"pass_rows": 3, "violation_rows": 0},
        }
        for name in fake_family_names
    }
    schema_snapshot = {
        family.schema_path: "schema-sha-" + family.name for family in validator.FAMILIES
    }
    healthy_snapshot = {**schema_snapshot, "qamus/data/y.jsonl": "bbb"}
    healthy = {
        "schema": RELEASE_SCHEMA,
        "baseline": {"source_sha256": healthy_snapshot},
        "tables": healthy_tables,
    }
    assert release_blockers(healthy, snapshot=healthy_snapshot) == []
    assertions[0] += 1

    stale = json.loads(json.dumps(healthy))
    stale["baseline"]["source_sha256"]["qamus/data/y.jsonl"] = "ccc"
    assert any("changed since the release was built" in item for item in release_blockers(stale, snapshot=healthy_snapshot))
    assertions[0] += 1

    red = json.loads(json.dumps(healthy))
    red["tables"][fake_family_names[0]]["validation"]["violation_rows"] = 7
    assert any("validation-red" in item for item in release_blockers(red, snapshot=healthy_snapshot))
    assertions[0] += 1

    mismatched = json.loads(json.dumps(healthy))
    mismatched["tables"][fake_family_names[0]]["validation"]["pass_rows"] = 2
    assert any("pass_rows does not equal" in item for item in release_blockers(mismatched, snapshot=healthy_snapshot))
    assertions[0] += 1

    weakened = json.loads(json.dumps(healthy))
    weakened["tables"][fake_family_names[0]]["provenance"]["boundary_constants"]["live_mutation_allowed"]["value"] = True
    assert any("is not canonical" in item for item in release_blockers(weakened, snapshot=healthy_snapshot))
    assertions[0] += 1

    schema_moved = json.loads(json.dumps(healthy))
    moved_snapshot = dict(healthy_snapshot)
    moved_snapshot[validator.FAMILIES[0].schema_path] = "rewritten"
    assert any(
        "target schema changed" in item for item in release_blockers(schema_moved, snapshot=moved_snapshot)
    )
    assertions[0] += 1

    unbound = json.loads(json.dumps(healthy))
    extra_snapshot = {**healthy_snapshot, "qamus/data/z.jsonl": "ddd"}
    assert any("not bound by the release baseline" in item for item in release_blockers(unbound, snapshot=extra_snapshot))
    assertions[0] += 1

    _expect_error(lambda: assert_release_usable(red, snapshot=healthy_snapshot), "validation-red", assertions)

    # --- ledger records must bind field-for-field to the recomputation ---
    truth = [
        {
            "defect_families": ["risk_flags"],
            "disposition": "quarantined",
            "family": "lemma-source",
            "identity": "aaaaaaaaaaaa",
            "identity_field": "entry_id",
            "provenance_variant_id": "pv-none",
            "reasons": ["semantic review required: risk_flags"],
            "schema": LEDGER_ROW_SCHEMA,
            "source_locator": "fusha/lexicon/largelexicon/lemma-source.full.jsonl:7",
            "source_row_sha256": "1" * 64,
        },
        {
            "defect_families": ["additional_property"],
            "disposition": "flagged",
            "family": "qword-crosswalk",
            "identity": "llx-crosswalk-row-b",
            "identity_field": "row_id",
            "provenance_variant_id": "pv-abc",
            "reasons": ["structural migration blocker: additional_property"],
            "schema": LEDGER_ROW_SCHEMA,
            "source_locator": "qamus/indexes/largelexicon/qword-crosswalk/x.jsonl:3",
            "source_row_sha256": "2" * 64,
        },
    ]
    expected_map = {(row["family"], row["identity"]): row for row in truth}
    assert bind_ledger_records(copy.deepcopy(truth), expected_map, label="ledger") == []
    assertions[0] += 1

    tampers = (
        ("identity substitution", 0, "identity", "bbbbbbbbbbbb", "not a recomputed non-carried identity"),
        ("source-hash tamper", 0, "source_row_sha256", "9" * 64, "field 'source_row_sha256' does not match"),
        ("reason tamper", 0, "reasons", ["semantic review required: nothing"], "field 'reasons' does not match"),
        ("provenance tamper", 1, "provenance_variant_id", "pv-zzz", "field 'provenance_variant_id' does not match"),
        ("disposition tamper", 1, "disposition", "carried", "field 'disposition' does not match"),
        ("defect tamper", 1, "defect_families", ["risk_flags"], "field 'defect_families' does not match"),
        ("locator tamper", 0, "source_locator", "elsewhere:1", "field 'source_locator' does not match"),
    )
    for name, index, field, value, expected_message in tampers:
        rows = copy.deepcopy(truth)
        rows[index][field] = value
        problems = bind_ledger_records(rows, expected_map, label="ledger")
        assert any(expected_message in problem for problem in problems), (name, problems)
        assertions[0] += 1

    missing = bind_ledger_records(copy.deepcopy(truth[:1]), expected_map, label="ledger")
    assert missing == [], "bind reports per-record problems; absence is caught by count/digest binding"
    extra = copy.deepcopy(truth) + [dict(truth[0], identity="cccccccccccc")]
    assert any("extra or substituted" in problem for problem in bind_ledger_records(extra, expected_map, label="ledger"))
    assertions[0] += 1
    duplicated = copy.deepcopy(truth) + [copy.deepcopy(truth[0])]
    assert any("duplicate ledger record" in problem for problem in bind_ledger_records(duplicated, expected_map, label="ledger"))
    assertions[0] += 1
    dropped_field = copy.deepcopy(truth)
    dropped_field[0].pop("provenance_variant_id")
    assert any("unexpected or missing fields" in problem for problem in bind_ledger_records(dropped_field, expected_map, label="ledger"))
    assertions[0] += 1

    # --- the bounded sample rule is deterministic and family-bounded ---
    many = [dict(truth[0], identity=f"id{index:03d}") for index in range(12)]
    sample = deterministic_sample(many)
    assert len(sample) == LEDGER_SAMPLE_PER_FAMILY
    assert sample == deterministic_sample(many)
    assert [row["identity"] for row in sample] == [f"id{index:03d}" for index in range(LEDGER_SAMPLE_PER_FAMILY)]
    assertions[0] += 1

    # --- full ledgers may never be written into a tracked path ---
    _expect_error(
        lambda: emit_ledgers(ROOT / "qamus" / "indexes", {"flagged": [], "quarantined": []}),
        "only be written under the gitignored out/ tree",
        assertions,
    )

    # --- boundary coverage must be exact per family ---
    partial = json.loads(json.dumps(healthy))
    partial["tables"][fake_family_names[0]]["provenance"]["boundary_constants"]["source"] = {
        "coverage": "all_rows",
        "rows_present": 2,
        "rows_total": 5,
        "value": CANONICAL_BOUNDARY["source"],
    }
    assert any("partially covered" in item for item in release_blockers(partial, snapshot=healthy_snapshot))
    assertions[0] += 1
    incomplete = json.loads(json.dumps(healthy))
    incomplete["tables"][fake_family_names[0]]["provenance"]["boundary_constants"].pop("source")
    assert any(
        "declare all four safety constants" in item for item in release_blockers(incomplete, snapshot=healthy_snapshot)
    )
    assertions[0] += 1

    print(
        review_json(
            {
                "assertions": assertions[0],
                "ok": True,
                "schema": "qamus/largelexicon-target-promotion-self-test@1",
            }
        ),
        end="",
    )
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true", help="write the committed target-schema artifacts")
    parser.add_argument("--check", action="store_true", help="fail closed when the committed artifacts drift")
    parser.add_argument("--emit-carried", type=Path, nargs="?", const=DEFAULT_CARRIED_DIR, default=None)
    parser.add_argument("--target-dir", type=Path, default=TARGET_DIR)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        return run_self_test()

    sink: dict[str, Any] | None = {} if args.emit_carried is not None else None
    result = promote(carried_sink=sink)
    artifacts = rendered_artifacts(result)

    if args.write:
        write_artifacts(args.target_dir, artifacts)
        emit_ledgers(DEFAULT_CARRIED_DIR, result)
    if args.check:
        drift = [
            name
            for name, payload in sorted(artifacts.items())
            if not (args.target_dir / name).exists() or (args.target_dir / name).read_bytes() != payload
        ]
        if drift:
            raise SystemExit("target-schema artifacts are stale or non-deterministic: " + ", ".join(drift))
        assert_release_usable(result["release"])
    if sink is not None:
        result["release"]["carried_output"]["emitted"] = {
            "directory": args.emit_carried.as_posix(),
            "sha256": emit_carried(args.emit_carried, sink),
        }

    print(review_json(result["release"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
