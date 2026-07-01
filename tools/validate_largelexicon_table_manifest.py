#!/usr/bin/env python3
"""Validate largelexicon sharded table manifests and bidirectional indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from largelexicon_common import PUBLIC_BOUNDARY, public_boundary_errors


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.manifest.json"
ENTRY_INDEX = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.entry-shard-index.json"
SOURCE_REPAIR = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.source-card-repair.json"
LEGACY_MONOLITH = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.full.jsonl"
MAX_SHARD_BYTES = 10 * 1024 * 1024
ROW_ID_RE = re.compile(r"^llx-qword-([0-9a-f]{12})-\d{2}-\d{2}-\d{3}$")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line.strip():
                yield line_no, json.loads(line)


def validate(manifest_path: Path = MANIFEST) -> list[str]:
    errors: list[str] = []
    if LEGACY_MONOLITH.exists():
        errors.append(f"{LEGACY_MONOLITH.relative_to(ROOT)} must be replaced by sharded manifest storage")
    if not manifest_path.exists():
        return errors + [f"missing qword denominator manifest: {manifest_path.relative_to(ROOT)}"]
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != "qamus/largelexicon-qword-denominator-manifest@1":
        errors.append("manifest schema mismatch")
    if manifest.get("table_schema") != "qamus/largelexicon-qword-denominator@1":
        errors.append("manifest table_schema mismatch")
    if manifest.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append("manifest public_boundary mismatch")
    if manifest.get("primary_key") != "row_id":
        errors.append("manifest primary_key must be row_id")
    if manifest.get("entry_index_path") != str(ENTRY_INDEX.relative_to(ROOT)).replace("\\", "/"):
        errors.append("manifest entry_index_path mismatch")
    if manifest.get("source_card_repair_path") != str(SOURCE_REPAIR.relative_to(ROOT)).replace("\\", "/"):
        errors.append("manifest source_card_repair_path mismatch")
    shards = manifest.get("shards") or []
    if not shards:
        errors.append("manifest must list at least one shard")
    if not ENTRY_INDEX.exists():
        errors.append(f"missing entry shard index: {ENTRY_INDEX.relative_to(ROOT)}")
        entry_index = {}
    else:
        entry_index = _read_json(ENTRY_INDEX)
        if entry_index.get("schema") != "qamus/largelexicon-qword-entry-shard-index@1":
            errors.append("entry shard index schema mismatch")
        if entry_index.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append("entry shard index public_boundary mismatch")
    if not SOURCE_REPAIR.exists():
        errors.append(f"missing source-card repair packet: {SOURCE_REPAIR.relative_to(ROOT)}")
        source_repair = {}
    else:
        source_repair = _read_json(SOURCE_REPAIR)
        if source_repair.get("schema") != "qamus/largelexicon-qword-source-card-repair-list@1":
            errors.append("source-card repair schema mismatch")
        if source_repair.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append("source-card repair public_boundary mismatch")

    seen_row_ids: set[str] = set()
    seen_entry_ids: set[str] = set()
    total_rows = 0
    shard_paths: set[str] = set()
    for shard in shards:
        rel = shard.get("path")
        if not rel:
            errors.append("shard missing path")
            continue
        if "\\" in rel:
            errors.append(f"{rel}: shard path must use POSIX separators")
        if rel in shard_paths:
            errors.append(f"{rel}: duplicate shard path")
        shard_paths.add(rel)
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: shard file missing")
            continue
        if path.stat().st_size > MAX_SHARD_BYTES:
            errors.append(f"{rel}: shard exceeds {MAX_SHARD_BYTES} bytes")
        actual_sha = _sha256_file(path)
        if shard.get("sha256") != actual_sha:
            errors.append(f"{rel}: sha256 mismatch")
        shard_rows = 0
        first_row_id = None
        last_row_id = None
        for line_no, row in _iter_jsonl(path):
            shard_rows += 1
            total_rows += 1
            label = f"{rel}:{line_no}"
            if row.get("schema") != manifest.get("table_schema"):
                errors.append(f"{label}: row schema mismatch")
            errors.extend(public_boundary_errors(row, label))
            if row.get("live_mutation_allowed") is not False:
                errors.append(f"{label}: live_mutation_allowed must be false")
            row_id = row.get("row_id")
            match = ROW_ID_RE.match(row_id or "")
            if not match:
                errors.append(f"{label}: invalid row_id {row_id!r}")
                continue
            entry_id = match.group(1)
            if row.get("entry_id") != entry_id:
                errors.append(f"{label}: row_id entry_id does not match row.entry_id")
            if row_id in seen_row_ids:
                errors.append(f"{label}: duplicate row_id {row_id}")
            seen_row_ids.add(row_id)
            seen_entry_ids.add(entry_id)
            first_row_id = first_row_id or row_id
            last_row_id = row_id
            entry_info = (entry_index.get("entries") or {}).get(entry_id)
            if not entry_info:
                errors.append(f"{label}: entry_id absent from entry shard index")
            elif entry_info.get("path") != rel:
                errors.append(f"{label}: entry shard index points to {entry_info.get('path')!r}")
        if shard.get("row_count") != shard_rows:
            errors.append(f"{rel}: row_count mismatch {shard.get('row_count')} != {shard_rows}")
        if shard_rows and shard.get("first_row_id") != first_row_id:
            errors.append(f"{rel}: first_row_id mismatch")
        if shard_rows and shard.get("last_row_id") != last_row_id:
            errors.append(f"{rel}: last_row_id mismatch")

    if manifest.get("row_count") != total_rows:
        errors.append(f"manifest row_count mismatch {manifest.get('row_count')} != {total_rows}")
    if manifest.get("row_count", 0) < 100000:
        errors.append("manifest row_count unexpectedly low")
    if manifest.get("qamus_entry_count") != 2092:
        errors.append(f"manifest qamus_entry_count expected 2092, got {manifest.get('qamus_entry_count')}")
    if manifest.get("entries_with_qword_rows") != len(seen_entry_ids):
        errors.append("manifest entries_with_qword_rows mismatch")
    repair_ids = {row.get("entry_id") for row in source_repair.get("repairs") or []}
    if set(manifest.get("entries_without_qword_rows") or []) != repair_ids:
        errors.append("source-card repair packet must cover entries_without_qword_rows exactly")
    for row in source_repair.get("repairs") or []:
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"source-card repair {row.get('entry_id')}: live_mutation_allowed must be false")
        if row.get("entry_id") == "2a071cd0b50e":
            hint = row.get("repair_hint") or {}
            if hint.get("source_photo_page_image") != "pg443.jpeg" or hint.get("candidate_quran_ref") != "42:47":
                errors.append("n993 source-card repair must preserve pg443.jpeg / 42:47 hint")
    if ENTRY_INDEX.exists():
        entries = entry_index.get("entries") or {}
        if entry_index.get("entry_count") != len(entries):
            errors.append("entry shard index entry_count mismatch")
        if entry_index.get("qamus_entry_count") != manifest.get("qamus_entry_count"):
            errors.append("entry shard index qamus_entry_count mismatch")
        if entry_index.get("entries_without_qword_rows") != manifest.get("entries_without_qword_rows"):
            errors.append("entry shard index entries_without_qword_rows mismatch")
        if set(entries) != seen_entry_ids:
            errors.append("entry shard index entries do not match shard row entry_ids")
        indexed_paths = {info.get("path") for info in entries.values()}
        if indexed_paths - shard_paths:
            errors.append(f"entry shard index references unknown shard paths: {sorted(indexed_paths - shard_paths)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sharded largelexicon qword denominator storage.")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.manifest))
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
