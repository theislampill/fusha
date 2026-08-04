#!/usr/bin/env python3
"""Load the legacy KC catalog plus append-safe family shards."""
from __future__ import annotations

import json
from pathlib import Path


class KcCatalogError(ValueError):
    pass


def _read_legacy(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KcCatalogError(f"{path}: invalid legacy KC catalog: {exc}") from exc
    if not isinstance(value, list):
        raise KcCatalogError(f"{path}: legacy KC catalog must be an array")
    return value


def _read_shard(path: Path) -> list[dict]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise KcCatalogError(f"{path}: cannot read KC shard: {exc}") from exc
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise KcCatalogError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def load_kc_catalog(repo_root: str | Path) -> list[dict]:
    """Return legacy rows followed by rows from lexically sorted JSONL shards."""
    root = Path(repo_root).resolve()
    curriculum = root / "curriculum"
    rows = _read_legacy(curriculum / "kc-catalog.json")
    shard_dir = curriculum / "kc-catalog.d"
    if shard_dir.is_dir():
        for path in sorted(shard_dir.glob("*.jsonl"), key=lambda item: item.name):
            rows.extend(_read_shard(path))

    seen = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise KcCatalogError(f"KC catalog row {index} must be an object")
        kc_id = row.get("kc_id")
        if not isinstance(kc_id, str) or not kc_id.strip():
            raise KcCatalogError(f"KC catalog row {index} is missing kc_id")
        if kc_id in seen:
            raise KcCatalogError(f"duplicate kc_id: {kc_id}")
        seen.add(kc_id)
    return rows


def load_kc_catalog_by_id(repo_root: str | Path) -> dict[str, dict]:
    return {row["kc_id"]: row for row in load_kc_catalog(repo_root)}
