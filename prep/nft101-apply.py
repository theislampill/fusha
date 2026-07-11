#!/usr/bin/env python3
"""Serialized NF-T10-1 ref correction prepared for owner-authorized later use.

This file is intentionally untracked.  It changes only repo-local public data and
derived artifacts; it never contacts or mutates the live Qamus application.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ENTRY_ID = "1c5f7c9c8e05"
OLD_REF = "4:46"
NEW_REF = "4:64"
USAGE_ZERO_INDEX = 2
EXAMPLE_ZERO_INDEX = 11
EXPECTED_ENTRIES_SHA256 = "a68245e93ce1a8b76858b672a449ff94475abf010e8102575e7c0285c540a78f"
TARGET_QWORD_IDS = (
    "llx-qword-1c5f7c9c8e05-03-12-001",
    "llx-qword-1c5f7c9c8e05-03-12-002",
)
TARGET_LOCS = ("4:64:9", "4:64:10")


class BaselineError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any, *, indent: int = 2) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def apply_entry_edit(entries_path: Path, expected_sha256: str) -> None:
    actual = sha256(entries_path)
    if actual != expected_sha256:
        raise BaselineError(
            f"entries baseline mismatch (expected {expected_sha256}, got {actual}); "
            "the correction may already be applied or the baseline changed"
        )
    lines = entries_path.read_text(encoding="utf-8").splitlines()
    matches = [(index, json.loads(line)) for index, line in enumerate(lines) if json.loads(line).get("id") == ENTRY_ID]
    if len(matches) != 1:
        raise BaselineError(f"expected one {ENTRY_ID} entry, found {len(matches)}")
    line_index, entry = matches[0]
    example = entry["usage"][USAGE_ZERO_INDEX]["examples"][EXAMPLE_ZERO_INDEX]
    if example.get("ref") == NEW_REF:
        raise BaselineError("correction already applied")
    if example.get("ref") != OLD_REF or example.get("ar") != "ظَلَمُوا أَنْفُسَهُمْ":
        raise BaselineError(f"target field is not the approved baseline: {example!r}")
    example["ref"] = NEW_REF
    lines[line_index] = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    entries_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def update_by_quran_ref(root: Path) -> None:
    path = root / "qamus/indexes/current/by-quran-ref.json"
    index = read_json(path)
    old = list(index.get(OLD_REF) or [])
    if ENTRY_ID not in old:
        raise BaselineError(f"{OLD_REF} index does not contain {ENTRY_ID}")
    old.remove(ENTRY_ID)
    index[OLD_REF] = sorted(old)
    index[NEW_REF] = sorted(set(index.get(NEW_REF) or []) | {ENTRY_ID})
    write_json(path, index)


def update_checksums(root: Path) -> None:
    path = root / "qamus/data/current/checksums.json"
    checksums = read_json(path)
    targets = {
        "data/entries.jsonl": root / "qamus/data/current/entries.jsonl",
        "indexes/by-quran-ref.json": root / "qamus/indexes/current/by-quran-ref.json",
    }
    for key, target in targets.items():
        raw = target.read_bytes()
        checksums[key] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    write_json(path, checksums, indent=2)


def replace_target_rows(path: Path, mutate) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    seen: set[str] = set()
    for row in rows:
        qword_id = row.get("qword_row_id") or row.get("row_id")
        if qword_id in TARGET_QWORD_IDS:
            mutate(row)
            seen.add(qword_id)
    if seen != set(TARGET_QWORD_IDS):
        raise BaselineError(f"target rows missing from {path}: {sorted(set(TARGET_QWORD_IDS) - seen)}")
    write_jsonl(path, rows)
    return rows


def update_manifest_shard(manifest_path: Path, shard_path: Path, repo_relative: str) -> None:
    manifest = read_json(manifest_path)
    matches = [item for item in manifest.get("shards", []) if item.get("path") in {repo_relative, shard_path.name}]
    if len(matches) != 1:
        raise BaselineError(f"expected one manifest entry for {repo_relative}, found {len(matches)}")
    matches[0]["sha256"] = sha256(shard_path)
    write_json(manifest_path, manifest)


def update_denominator(root: Path) -> dict[str, dict[str, Any]]:
    shard = root / "qamus/indexes/largelexicon/qword-denominator/v001-v040.jsonl"

    def mutate(row: dict[str, Any]) -> None:
        if row.get("quran_ref") != OLD_REF:
            raise BaselineError(f"{row['row_id']} denominator baseline is {row.get('quran_ref')!r}")
        row["quran_ref"] = NEW_REF

    rows = replace_target_rows(shard, mutate)
    manifest = root / "qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json"
    update_manifest_shard(manifest, shard, "qamus/indexes/largelexicon/qword-denominator/v001-v040.jsonl")
    return {row["row_id"]: row for row in rows if row.get("row_id") in TARGET_QWORD_IDS}


def row_fingerprint(row: dict[str, Any]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def update_crosswalk(root: Path, denominator: dict[str, dict[str, Any]]) -> None:
    shard = root / "qamus/indexes/largelexicon/qword-crosswalk/v011-v020.jsonl"

    def mutate(row: dict[str, Any]) -> None:
        qword_id = row["qword_row_id"]
        if row.get("quran_ref") != OLD_REF or row.get("status") != "source_crosswalk_packet_ready":
            raise BaselineError(f"{row['row_id']} crosswalk baseline drifted")
        row["quran_ref"] = NEW_REF
        deps = row.get("source_dependencies") or []
        dep = next((item for item in deps if item.get("kind") == "qword_denominator_row"), None)
        if dep is None:
            raise BaselineError(f"{row['row_id']} lacks denominator dependency")
        dep["sha256"] = row_fingerprint(denominator[qword_id])

    replace_target_rows(shard, mutate)
    manifest = root / "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json"
    update_manifest_shard(manifest, shard, "qamus/indexes/largelexicon/qword-crosswalk/v011-v020.jsonl")
    generation = root / "qamus/indexes/largelexicon/qword-crosswalk/GENERATION.json"
    update_manifest_shard(generation, shard, "v011-v020.jsonl")


def update_queue(root: Path, denominator: dict[str, dict[str, Any]]) -> None:
    path = root / "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.jsonl"
    rows = read_jsonl(path)
    by_loc = {row.get("canonical_location"): row for row in rows}
    for loc, qword_id in zip(TARGET_LOCS, TARGET_QWORD_IDS, strict=True):
        row = by_loc.get(loc)
        source = denominator[qword_id]
        if row is None or row.get("primary_resolution_family") != "no_qword_candidate" or row.get("candidate_count") != 0:
            raise BaselineError(f"{loc} queue row is not the expected zero-candidate baseline")
        carrier = {
            "card_id": source["card_id"],
            "entry_id": source["entry_id"],
            "qword_row_id": qword_id,
            "row_id": qword_id,
        }
        row.update(
            {
                "candidate_card_ids": [source["card_id"]],
                "candidate_count": 1,
                "candidate_entry_ids": [source["entry_id"]],
                "candidate_equivalence_classes": [source["entry_id"]],
                "candidate_qword_row_ids": [qword_id],
                "dependency_hashes": {qword_id: source["card_text_sha256"]},
                "full_carrier_candidates": [carrier],
                "primary_resolution_family": "unique_qword_candidate",
            }
        )
    write_jsonl(path, rows)
    manifest_path = root / "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.manifest.json"
    manifest = read_json(manifest_path)
    manifest["family_counts"]["no_qword_candidate"] -= 2
    manifest["family_counts"]["unique_qword_candidate"] += 2
    manifest["queue_sha256"] = sha256(path)
    manifest["denominator_files"]["v001-v040.jsonl"] = sha256(
        root / "qamus/indexes/largelexicon/qword-denominator/v001-v040.jsonl"
    )
    manifest["crosswalk_files"]["v011-v020.jsonl"] = sha256(
        root / "qamus/indexes/largelexicon/qword-crosswalk/v011-v020.jsonl"
    )
    write_json(manifest_path, manifest, indent=1)


def update_embedded_manifests(root: Path) -> None:
    path = root / "qamus/indexes/largelexicon/source-clean-fact-tables.meta.json"
    value = read_json(path)
    value["qword_denominator_manifest"] = read_json(
        root / "qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json"
    )
    value["qword_crosswalk_manifest"] = read_json(
        root / "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json"
    )
    write_json(path, value)


def run(command: list[str], root: Path, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(command, cwd=root, env=env, check=False)
    if completed.returncode:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}")


def verify(root: Path) -> None:
    entries = root / "qamus/data/current/entries.jsonl"
    target = next(json.loads(line) for line in entries.read_text(encoding="utf-8").splitlines() if json.loads(line).get("id") == ENTRY_ID)
    assert target["usage"][USAGE_ZERO_INDEX]["examples"][EXAMPLE_ZERO_INDEX]["ref"] == NEW_REF
    denominator_rows = read_jsonl(root / "qamus/indexes/largelexicon/qword-denominator/v001-v040.jsonl")
    matches = [row for row in denominator_rows if row.get("quran_ref") == NEW_REF and row.get("row_id") in TARGET_QWORD_IDS]
    assert [row["row_id"] for row in matches] == list(TARGET_QWORD_IDS)
    queue = {row["canonical_location"]: row for row in read_jsonl(root / "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.jsonl")}
    for loc, qword_id in zip(TARGET_LOCS, TARGET_QWORD_IDS, strict=True):
        row = queue[loc]
        assert row["primary_resolution_family"] == "unique_qword_candidate"
        assert row["candidate_qword_row_ids"] == [qword_id]
    run([sys.executable, "tools/validate_current_qamus_dataset.py"], root)
    run([sys.executable, "tools/validate_largelexicon_table_manifest.py"], root)
    run([sys.executable, "tools/validate_largelexicon_qword_crosswalk.py"], root)


def mutation_files() -> list[str]:
    return [
        "qamus/data/current/entries.jsonl",
        "qamus/data/current/checksums.json",
        "qamus/indexes/current/by-quran-ref.json",
        "qamus/indexes/current/source-address-full.jsonl",
        "qamus/indexes/current/source-address-full.meta.json",
        "qamus/indexes/current/quran-usage-spine-full.jsonl",
        "qamus/indexes/current/quran-usage-spine-full.meta.json",
        "qamus/indexes/current/qamus-entry-field-addresses.jsonl",
        "qamus/indexes/current/qamus-entry-field-addresses.meta.json",
        "qamus/indexes/current/decision-backlinks-full.json",
        "qamus/reports/xanadu-completion-report.md",
        "qamus/reports/source-address-usage-report.md",
        "qamus/indexes/existing_qamus_index.min.json",
        "qamus/indexes/largelexicon/qword-denominator/v001-v040.jsonl",
        "qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json",
        "qamus/indexes/largelexicon/qword-crosswalk/v011-v020.jsonl",
        "qamus/indexes/largelexicon/qword-crosswalk/GENERATION.json",
        "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json",
        "qamus/indexes/largelexicon/source-clean-fact-tables.meta.json",
        "qamus/indexes/largelexicon/RELEASE.json",
        "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.jsonl",
        "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.manifest.json",
    ]


def rollback_snapshot_path(root: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "nft101-rollback"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise BaselineError(f"cannot resolve repository rollback path: {completed.stderr.strip()}")
    return Path(completed.stdout.strip()).resolve()


def snapshot(root: Path) -> Path:
    backup = rollback_snapshot_path(root)
    if backup.exists():
        raise BaselineError(f"rollback snapshot already exists: {backup}")
    for rel in mutation_files():
        source = root / rel
        target = backup / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    write_json(backup / "receipt.json", {"files": mutation_files()})
    return backup


def rollback(root: Path) -> None:
    backup = rollback_snapshot_path(root)
    receipt = read_json(backup / "receipt.json")
    for rel in receipt["files"]:
        shutil.copy2(backup / rel, root / rel)
    shutil.rmtree(backup)
    print("NF-T10-1 rollback restored the pre-apply snapshot")


def apply(root: Path, hover_stage: Path, built_at: str) -> None:
    entries = root / "qamus/data/current/entries.jsonl"
    required_stage = [hover_stage / "wbw-lookup.json", hover_stage / "fusha-hover-token-decisions.jsonl"]
    missing_stage = [str(path) for path in required_stage if not path.is_file()]
    if missing_stage:
        raise BaselineError(f"pinned full hover stage is incomplete: {missing_stage}")
    snapshot(root)
    try:
        apply_entry_edit(entries, EXPECTED_ENTRIES_SHA256)
        update_by_quran_ref(root)
        update_checksums(root)
        denominator = update_denominator(root)
        update_crosswalk(root, denominator)
        update_queue(root, denominator)
        update_embedded_manifests(root)
        run([sys.executable, "tools/build_existing_qamus_index.py", "--write"], root)
        env = dict(os.environ)
        env["QAMUS_HOVER_STAGE"] = str(hover_stage.resolve())
        run([sys.executable, "tools/build_full_source_address_graph.py", "--write"], root, env)
        run([sys.executable, "tools/validate_largelexicon_rows.py", "--write-release", "--built-at", built_at], root)
        verify(root)
    except Exception:
        print("APPLY FAILED; run: python prep/nft101-apply.py --rollback", file=sys.stderr)
        raise
    print("NF-T10-1 correction applied; rollback: python prep/nft101-apply.py --rollback")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--hover-stage", type=Path, help="pinned full hover-stage directory for source-graph regeneration")
    parser.add_argument("--built-at", help="deterministic RELEASE.json timestamp; use the owner-approved apply timestamp")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    root = args.repo.resolve()
    if args.rollback:
        rollback(root)
        return 0
    if args.hover_stage is None or args.built_at is None:
        parser.error("apply requires --hover-stage and --built-at")
    apply(root, args.hover_stage, args.built_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
