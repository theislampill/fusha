#!/usr/bin/env python3
"""Dry-run the RM-22 largelexicon @1 to target-schema regeneration rehearsal.

The tool reads the committed tables and emits reports only. It never writes a
table, manifest, schema, or release file.

Migration semantics are NOT re-implemented here: the candidate derivation, the
disposition rules, and the losslessness proof all come from
``tools/promote_largelexicon_target_schema.py``, so the rehearsal can never drift
away from the promotion it rehearses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import promote_largelexicon_target_schema as promoter
import validate_largelexicon_rows as validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "qamus" / "reports" / "rm22-regeneration-rehearsal"
TOOL_PATH = "tools/rehearse_largelexicon_regeneration.py"
REPORT_SCHEMA = "qamus/rm22-regeneration-rehearsal@1"
ACCOUNTING_SCHEMA = "qamus/rm22-regeneration-accounting-row@1"
DISPOSITIONS = frozenset(promoter.DISPOSITIONS)
IDENTITY_FIELDS = promoter.IDENTITY_FIELDS
STRUCTURAL_CONSTANTS = validator.ROW_CONSTANT_FIELDS
migrate_candidate = promoter.migrate_candidate


def canonical_line(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def review_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def row_digest(row: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_line(row)).hexdigest()


def assert_lossless_accounting(
    source_rows: Iterable[dict[str, Any]], accounting_rows: Iterable[dict[str, Any]], identity_field: str
) -> None:
    """Delegate to the promotion's proof so rehearsal and promotion cannot diverge."""

    promoter.assert_lossless_accounting(
        [str(row[identity_field]) for row in source_rows], list(accounting_rows), identity_field
    )


field_changes = promoter.field_changes


def classify_disposition(errors: list[dict[str, str]], divergences: list[str] | None = None) -> tuple[str, list[str]]:
    return promoter.classify_disposition(errors, divergences or [])


def source_snapshot() -> dict[str, str]:
    paths: set[Path] = {ROOT / "qamus" / "indexes" / "largelexicon" / "RELEASE.json"}
    for family in validator.FAMILIES:
        paths.update(validator.family_paths(family))
        if family.manifest_path:
            paths.add(ROOT / family.manifest_path)
    return {path.relative_to(ROOT).as_posix(): validator.sha256_file(path) for path in sorted(paths)}


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def rehearse() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current_release = validator.read_json(validator.RELEASE_PATH)
    baseline = source_snapshot()
    all_accounting: list[dict[str, Any]] = []
    family_reports: list[dict[str, Any]] = []
    would_be_tables: dict[str, Any] = {}

    for family in validator.FAMILIES:
        schema = validator.read_json(ROOT / family.schema_path)
        identity_field = IDENTITY_FIELDS[family.name]
        source_rows: list[dict[str, Any]] = []
        accounting_rows: list[dict[str, Any]] = []
        disposition_counts: Counter[str] = Counter()
        change_kind_counts: Counter[str] = Counter()
        reason_counts: Counter[str] = Counter()
        output_digest = hashlib.sha256()
        carried_count = 0

        for source_path, line_no, source in validator.iter_family_rows(family):
            source_rows.append(source)
            candidate, changes = migrate_candidate(family, source)
            errors = validator.schema_errors(candidate, schema)
            disposition, reasons = classify_disposition(errors, promoter.boundary_divergences(source))
            identity = str(source[identity_field])
            if disposition == "carried":
                output_digest.update(canonical_line(candidate))
                carried_count += 1
            disposition_counts[disposition] += 1
            change_kind_counts.update(change["kind"] for change in changes)
            reason_counts.update(reasons)
            accounting = {
                "change_class": "structural" if changes else "unchanged",
                "change_codes": [f"{change['kind']}:{change['field']}" for change in changes],
                "disposition": disposition,
                "family": family.name,
                identity_field: identity,
                "reasons": reasons,
                "source_locator": f"{source_path}:{line_no}",
                "validation_defect_families": sorted({error["defect_family"] for error in errors}),
            }
            accounting_rows.append(accounting)
            all_accounting.append(accounting)

        assert_lossless_accounting(source_rows, accounting_rows, identity_field)
        current = current_release["tables"][family.name]
        would_be = {
            "accounted_row_count": len(accounting_rows),
            "carried_row_count": carried_count,
            "quarantined_or_flagged_row_count": len(accounting_rows) - carried_count,
            "sha256": output_digest.hexdigest(),
            "sha256_scope": "canonical compact @2 JSONL bytes for carried rows in committed manifest order",
            "target_row_schema": schema["properties"]["schema"]["const"],
        }
        would_be_tables[family.name] = would_be
        family_reports.append(
            {
                "accounting_ok": True,
                "change_kind_counts": dict(sorted(change_kind_counts.items())),
                "disposition_counts": dict(sorted(disposition_counts.items())),
                "family": family.name,
                "identity_field": identity_field,
                "release_comparison": {
                    "current": {"row_count": current["row_count"], "sha256": current["sha256"], "row_schema": current["source_row_schema"]},
                    "would_be": would_be,
                },
                "reason_counts": dict(sorted(reason_counts.items())),
                "source_row_count": len(source_rows),
            }
        )

    after = source_snapshot()
    if after != baseline:
        raise RuntimeError("dry-run invariant failed: committed table or manifest bytes changed during rehearsal")
    totals = Counter(row["disposition"] for row in all_accounting)
    summary = {
        "baseline": {"git_head": git_head(), "source_sha256": baseline},
        "determinism": {"timestamps_omitted": True, "stable_input_order": True, "stable_json_keys": True},
        "dry_run": {"committed_sources_byte_untouched": True, "live_mutation_allowed": False},
        "families": family_reports,
        "generator": TOOL_PATH,
        "losslessness": {
            "accounted_row_count": len(all_accounting),
            "disposition_counts": dict(sorted(totals.items())),
            "silent_drop_count": 0,
            "source_row_count": sum(item["source_row_count"] for item in family_reports),
        },
        "migration": {
            "classification": "structural-only rehearsal; semantic defects are quarantined",
            "row_additions": 0,
            "row_removals_from_would_be_tables": totals["flagged"] + totals["quarantined"],
            "row_removals_silently_dropped": 0,
        },
        "release_manifest_comparison": {"current_schema": current_release["schema"], "would_be_tables": would_be_tables},
        "schema": REPORT_SCHEMA,
    }
    return summary, all_accounting


def compact_accounting(accounting: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    profiles = sorted({tuple(row["change_codes"]) for row in accounting})
    profile_ids = {profile: f"cp{index:02d}" for index, profile in enumerate(profiles, start=1)}
    compact: list[dict[str, Any]] = []
    for row in accounting:
        identity_field = IDENTITY_FIELDS[row["family"]]
        compact.append(
            {
                "change_profile": profile_ids[tuple(row["change_codes"])],
                "defects": row["validation_defect_families"],
                "disposition": row["disposition"],
                "family": row["family"],
                "row_key": row[identity_field],
            }
        )
    return compact, {profile_ids[profile]: list(profile) for profile in profiles}


def accounting_bytes(accounting: list[dict[str, Any]]) -> tuple[bytes, dict[str, list[str]]]:
    compact, profiles = compact_accounting(accounting)
    return b"".join(canonical_line(row) for row in compact), profiles


def write_reports(report_dir: Path, summary: dict[str, Any], accounting: list[dict[str, Any]]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "migration-report.json").write_text(review_json(summary), encoding="utf-8", newline="\n")
    serialized, profiles = accounting_bytes(accounting)
    (report_dir / "row-accounting.jsonl").write_bytes(serialized)
    meta = {
        "change_profiles": profiles,
        "dispositions": sorted(DISPOSITIONS),
        "generator": TOOL_PATH,
        "identity_fields": IDENTITY_FIELDS,
        "row_count": len(accounting),
        "row_schema": ACCOUNTING_SCHEMA,
        "schema": "qamus/rm22-regeneration-accounting-meta@1",
        "sha256": hashlib.sha256(serialized).hexdigest(),
    }
    (report_dir / "row-accounting.meta.json").write_text(review_json(meta), encoding="utf-8", newline="\n")


def run_self_test() -> int:
    source = [{"row_id": "row-a"}, {"row_id": "row-b"}, {"row_id": "row-c"}]
    accounted = [
        {"row_id": "row-a", "disposition": "carried"},
        {"row_id": "row-b", "disposition": "flagged"},
        {"row_id": "row-c", "disposition": "quarantined"},
    ]
    assert_lossless_accounting(source, accounted, "row_id")
    assertions = 1
    fixtures = [
        (accounted[:-1], "missing=row-c"),
        ([*accounted, accounted[0]], "duplicate=row-a"),
        ([*accounted[:-1], {"row_id": "row-c", "disposition": "lost"}], "invalid_disposition=row-c"),
    ]
    for fixture, expected in fixtures:
        try:
            assert_lossless_accounting(source, fixture, "row_id")
        except promoter.PromotionError as error:
            assert expected in str(error), error
            assertions += 1
        else:
            raise AssertionError(f"red-first accounting fixture was not rejected: {expected}")
    print(review_json({"assertions": assertions, "ok": True, "schema": "qamus/rm22-rehearsal-self-test@1"}), end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check", action="store_true", help="compare generated reports with committed reports")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    summary, accounting = rehearse()
    if args.check:
        expected_summary = review_json(summary)
        expected_accounting, profiles = accounting_bytes(accounting)
        actual_summary = (args.report_dir / "migration-report.json").read_text(encoding="utf-8")
        actual_accounting = (args.report_dir / "row-accounting.jsonl").read_bytes()
        expected_meta = {
            "change_profiles": profiles,
            "dispositions": sorted(DISPOSITIONS),
            "generator": TOOL_PATH,
            "identity_fields": IDENTITY_FIELDS,
            "row_count": len(accounting),
            "row_schema": ACCOUNTING_SCHEMA,
            "schema": "qamus/rm22-regeneration-accounting-meta@1",
            "sha256": hashlib.sha256(expected_accounting).hexdigest(),
        }
        actual_meta = (args.report_dir / "row-accounting.meta.json").read_text(encoding="utf-8")
        if actual_summary != expected_summary or actual_accounting != expected_accounting or actual_meta != review_json(expected_meta):
            raise SystemExit("rehearsal reports are stale or non-deterministic")
    else:
        write_reports(args.report_dir, summary, accounting)
    print(review_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
