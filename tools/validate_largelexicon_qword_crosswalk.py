#!/usr/bin/env python3
"""Validate largelexicon qword crosswalk status shards."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from largelexicon_common import PUBLIC_BOUNDARY, QWORD_CROSSWALK_MANIFEST, QWORD_DENOMINATOR_MANIFEST, sha256_file
from largelexicon_table_reader import LargelexiconQwordTable


ROOT = Path(__file__).resolve().parents[1]
MAX_SHARD_BYTES = 10 * 1024 * 1024
ACCEPTED = "canonical_crosswalk_accepted"
PACKET = "source_crosswalk_packet_ready"
DEMOTED = "canonical_crosswalk_demoted"
VALID_STATUSES = frozenset({ACCEPTED, PACKET, DEMOTED})
DEMOTION_WAVE = "rm36-demotion-01"
DEMOTION_REASON = "vowel_preserving_ayah_uniqueness_failed"
REINSTATEMENT_CONDITION = (
    "uniqueness re-proof under _join_surface_key or reviewed occurrence adjudication"
)


def _iter_rows(manifest: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shard in manifest.get("shards") or []:
        rel = shard.get("path")
        if not rel:
            errors.append("crosswalk shard missing path")
            continue
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: shard file missing")
            continue
        if path.stat().st_size > MAX_SHARD_BYTES:
            errors.append(f"{rel}: shard exceeds {MAX_SHARD_BYTES} bytes")
        if shard.get("sha256") != sha256_file(path):
            errors.append(f"{rel}: sha256 mismatch")
        with path.open("r", encoding="utf-8") as handle:
            shard_rows = [json.loads(line) for line in handle if line.strip()]
        if len(shard_rows) != shard.get("row_count"):
            errors.append(f"shard row_count mismatch: {rel}")
        rows.extend(shard_rows)
    return rows


def _sha256_row(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _quran_ref_matches_loc(quran_ref: str | None, loc: str | None) -> bool:
    if not quran_ref or not loc:
        return True
    parts = loc.split(":")
    if len(parts) < 2:
        return False
    return quran_ref == f"{parts[0]}:{parts[1]}"


def _dependency_sha(row: dict[str, Any], kind: str, dep_id: str | None) -> str | None:
    for dep in row.get("source_dependencies") or []:
        if dep.get("kind") == kind and (dep_id is None or dep.get("id") == dep_id):
            return dep.get("sha256")
    return None


def _validate_rows(rows: list[dict[str, Any]], denominator_rows: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    qword_ids: set[str] = set()
    for row in rows:
        label = row.get("row_id") or "<unknown>"
        qword_id = row.get("qword_row_id")
        if not qword_id:
            errors.append(f"{label}: missing qword_row_id")
            continue
        if qword_id in qword_ids:
            errors.append(f"{label}: duplicate qword_row_id {qword_id}")
        qword_ids.add(qword_id)
        if row.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append(f"{label}: public_boundary must stay source-clean")
        status = row.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{label}: invalid crosswalk status {status!r}")
        if not row.get("source_dependencies"):
            errors.append(f"{label}: missing source_dependencies")
        denominator_row = denominator_rows.get(qword_id)
        if not denominator_row:
            errors.append(f"{label}: qword_row_id missing from denominator table")
        else:
            if row.get("entry_id") != denominator_row.get("entry_id"):
                errors.append(f"{label}: entry_id does not match denominator row")
            dep_sha = _dependency_sha(row, "qword_denominator_row", qword_id)
            if dep_sha and dep_sha != _sha256_row(denominator_row):
                errors.append(f"{label}: qword_denominator_row dependency sha mismatch")
        has_canonical_loc = bool(row.get("canonical_quran_loc") or row.get("canonical_wbw_loc"))
        if status == ACCEPTED:
            if not row.get("canonical_quran_loc") or not row.get("canonical_wbw_loc"):
                errors.append(f"{label}: accepted crosswalk cannot have null canonical loc")
            if row.get("packet_class") is not None:
                errors.append(f"{label}: accepted crosswalk must not keep packet_class")
            if row.get("terminal_gate_code") is not None:
                errors.append(f"{label}: accepted crosswalk must not keep terminal_gate_code")
            if row.get("next_action") is not None:
                errors.append(f"{label}: accepted crosswalk must not keep next_action")
            if not _quran_ref_matches_loc(row.get("quran_ref"), row.get("canonical_quran_loc")):
                errors.append(f"{label}: canonical_quran_loc does not match quran_ref")
            if not _quran_ref_matches_loc(row.get("quran_ref"), row.get("canonical_wbw_loc")):
                errors.append(f"{label}: canonical_wbw_loc does not match quran_ref")
        elif status == DEMOTED:
            demotion = row.get("demotion")
            expected_scalar = {
                "wave": DEMOTION_WAVE,
                "reason": DEMOTION_REASON,
                "prior_status": ACCEPTED,
                "reinstatement_condition": REINSTATEMENT_CONDITION,
            }
            if not isinstance(demotion, dict):
                errors.append(f"{label}: demoted crosswalk requires demotion object")
            else:
                if not row.get("canonical_quran_loc") or not row.get("canonical_wbw_loc"):
                    errors.append(f"{label}: demoted crosswalk must retain both canonical locs")
                if not _quran_ref_matches_loc(row.get("quran_ref"), row.get("canonical_quran_loc")):
                    errors.append(f"{label}: demoted canonical_quran_loc does not match quran_ref")
                if not _quran_ref_matches_loc(row.get("quran_ref"), row.get("canonical_wbw_loc")):
                    errors.append(f"{label}: demoted canonical_wbw_loc does not match quran_ref")
                for field, expected in expected_scalar.items():
                    if demotion.get(field) != expected:
                        errors.append(f"{label}: demotion.{field} must be {expected!r}")
                evidence = demotion.get("evidence")
                if not isinstance(evidence, dict):
                    errors.append(f"{label}: demotion.evidence must be an object")
                else:
                    positions = evidence.get("positions")
                    if not isinstance(positions, list) or len(positions) < 2 or not all(
                        isinstance(position, str) and position for position in positions
                    ):
                        errors.append(f"{label}: demotion.evidence.positions requires repeated locations")
                demoted_at_head = demotion.get("demoted_at_head")
                if not isinstance(demoted_at_head, str) or not re.fullmatch(r"[0-9a-f]{40}", demoted_at_head):
                    errors.append(f"{label}: demotion.demoted_at_head must be a 40-character lowercase hex SHA")
            if row.get("packet_class") is not None:
                errors.append(f"{label}: demoted crosswalk must not become a repair packet")
        elif has_canonical_loc:
            errors.append(f"{label}: rows with canonical locs must be {ACCEPTED}")
        if status == PACKET and not row.get("packet_class"):
            errors.append(f"{label}: unresolved crosswalk rows need exact packet_class")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    if not QWORD_CROSSWALK_MANIFEST.exists():
        return [f"missing crosswalk manifest: {QWORD_CROSSWALK_MANIFEST}"]
    manifest = json.loads(QWORD_CROSSWALK_MANIFEST.read_text(encoding="utf-8"))
    denominator = json.loads(QWORD_DENOMINATOR_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("row_count") != denominator.get("row_count"):
        errors.append("crosswalk row_count must equal qword denominator row_count")
    if manifest.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append("crosswalk manifest public_boundary must stay source-clean")
    rows = _iter_rows(manifest, errors)
    if len(rows) != manifest.get("row_count"):
        errors.append("crosswalk materialized rows do not match manifest row_count")
    table = LargelexiconQwordTable.from_repo(ROOT)
    denominator_rows = {row["row_id"]: row for row in table.iter_rows()}
    errors.extend(_validate_rows(rows, denominator_rows))
    summary = table.crosswalk_summary()
    if not summary.get("available"):
        errors.append("table reader crosswalk_summary must report available")
    if summary.get("row_count") != denominator.get("row_count"):
        errors.append("table reader crosswalk_summary row_count mismatch")
    sample = next(table.iter_rows(limit=1), None)
    if sample and not table.crosswalk_for_qword(sample["row_id"]):
        errors.append("table reader crosswalk_for_qword failed for sample denominator row")
    return errors


def self_test() -> int:
    """Exercise crosswalk row validation with isolated in-memory fixtures."""
    qword_id = "llx-qword-0123456789ab-01-01-001"
    denominator_row = {"row_id": qword_id, "entry_id": "0123456789ab"}
    denominator_rows = {qword_id: denominator_row}
    clean_row = {
        "row_id": f"llx-crosswalk-{qword_id}",
        "qword_row_id": qword_id,
        "entry_id": denominator_row["entry_id"],
        "public_boundary": PUBLIC_BOUNDARY,
        "source_dependencies": [{
            "kind": "qword_denominator_row",
            "id": qword_id,
            "sha256": _sha256_row(denominator_row),
        }],
        "status": ACCEPTED,
        "canonical_quran_loc": "1:1:1",
        "canonical_wbw_loc": "1:1:1",
        "quran_ref": "1:1",
        "packet_class": None,
        "terminal_gate_code": None,
        "next_action": None,
    }

    failures: list[str] = []
    clean_errors = _validate_rows([clean_row], denominator_rows)
    if clean_errors:
        failures.append(f"clean fixture should pass, got {clean_errors}")

    demoted_row = {
        **clean_row,
        "status": "canonical_crosswalk_demoted",
        "demotion": {
            "wave": "rm36-demotion-01",
            "reason": "vowel_preserving_ayah_uniqueness_failed",
            "evidence": {"positions": ["1:1:1", "1:1:2"]},
            "prior_status": ACCEPTED,
            "demoted_at_head": "4" * 40,
            "reinstatement_condition": (
                "uniqueness re-proof under _join_surface_key or reviewed occurrence adjudication"
            ),
        },
    }
    demoted_errors = _validate_rows([demoted_row], denominator_rows)
    if demoted_errors:
        failures.append(f"demoted fixture should be valid-but-not-accepted, got {demoted_errors}")
    compiler_inputs = [row for row in [clean_row, demoted_row] if row.get("status") == ACCEPTED]
    if compiler_inputs != [clean_row]:
        failures.append("demoted fixture must be excluded from compiler-input construction")

    cases = [
        (
            "missing denominator target",
            [{**clean_row, "qword_row_id": "llx-qword-0123456789ab-01-01-999"}],
            "qword_row_id missing from denominator table",
        ),
        (
            "mismatched denominator target",
            [{**clean_row, "entry_id": "deadbeef0000"}],
            "entry_id does not match denominator row",
        ),
        (
            "duplicate qword target",
            [clean_row, {**clean_row, "row_id": "duplicate-row"}],
            "duplicate qword_row_id",
        ),
        (
            "accepted-row shape violation",
            [{**clean_row, "canonical_wbw_loc": None}],
            "accepted crosswalk cannot have null canonical loc",
        ),
        (
            "demoted-row retained-location violation",
            [{**demoted_row, "canonical_wbw_loc": None}],
            "demoted crosswalk must retain both canonical locs",
        ),
        (
            "demoted-row malformed evidence",
            [{**demoted_row, "demotion": {**demoted_row["demotion"], "evidence": []}}],
            "demotion.evidence must be an object",
        ),
    ]
    for label, rows, needle in cases:
        errors = _validate_rows(rows, denominator_rows)
        if not any(needle in error for error in errors):
            failures.append(f"{label} not caught: expected {needle!r}, got {errors}")

    if failures:
        for failure in failures:
            print(f"self-test failed: {failure}")
        return 1
    print("self-test ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run isolated in-memory fixture checks")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
