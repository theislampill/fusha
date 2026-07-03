#!/usr/bin/env python3
"""Validate largelexicon qword crosswalk status shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from largelexicon_common import PUBLIC_BOUNDARY, QWORD_CROSSWALK_MANIFEST, QWORD_DENOMINATOR_MANIFEST, sha256_file
from largelexicon_table_reader import LargelexiconQwordTable


ROOT = Path(__file__).resolve().parents[1]
MAX_SHARD_BYTES = 10 * 1024 * 1024
ACCEPTED = "canonical_crosswalk_accepted"


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
        if row.get("status") == ACCEPTED:
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
        elif has_canonical_loc:
            errors.append(f"{label}: rows with canonical locs must be {ACCEPTED}")
        if row.get("status") != ACCEPTED and not row.get("packet_class"):
            errors.append(f"{label}: unresolved crosswalk rows need exact packet_class")
    summary = table.crosswalk_summary()
    if not summary.get("available"):
        errors.append("table reader crosswalk_summary must report available")
    if summary.get("row_count") != denominator.get("row_count"):
        errors.append("table reader crosswalk_summary row_count mismatch")
    sample = next(table.iter_rows(limit=1), None)
    if sample and not table.crosswalk_for_qword(sample["row_id"]):
        errors.append("table reader crosswalk_for_qword failed for sample denominator row")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
