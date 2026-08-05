#!/usr/bin/env python3
"""Load the legacy KC catalog plus append-safe family shards."""
from __future__ import annotations

import json
from pathlib import Path


class KcCatalogError(ValueError):
    pass


# R4: the declared-shard fail-closed gate lives HERE, at the loader's own choke point, so every caller of
# `load_kc_catalog` — the tutor runtime, `build_curriculum_absorption.py`, `fusha_learner_feedback.py` (and
# through it `fusha_cefr_gate.py`), `validate_curriculum_l1l6.py` — inherits it automatically. A gate placed only
# on one caller's own private wrapper (the previous shape) leaves every OTHER direct caller able to silently pick
# up an undeclared shard. Every gate-bearing `curriculum/kc-catalog.d/*.jsonl` shard must be pinned here by name;
# an undeclared shard fails closed rather than silently joining the catalog.
DECLARED_KC_SHARDS = frozenset({
    "tranche-001-derivation-template.jsonl",
    "tranche-001-ma-context.jsonl",
})


def assert_declared_kc_shards(repo_root: str | Path) -> None:
    """Fail closed if curriculum/kc-catalog.d/ contains a shard file not listed in DECLARED_KC_SHARDS."""
    root = Path(repo_root).resolve()
    shard_dir = root / "curriculum" / "kc-catalog.d"
    if not shard_dir.is_dir():
        return
    found = {p.name for p in shard_dir.glob("*.jsonl")}
    undeclared = found - DECLARED_KC_SHARDS
    if undeclared:
        raise KcCatalogError(
            f"undeclared curriculum/kc-catalog.d shard(s) {sorted(undeclared)}: every gate-bearing KC shard "
            "must be pinned in tools.kc_catalog.DECLARED_KC_SHARDS before it can be loaded")


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
    """Return legacy rows followed by rows from lexically sorted JSONL shards. Fails closed (KcCatalogError) if
    curriculum/kc-catalog.d/ contains an undeclared shard — see assert_declared_kc_shards; this is the single
    choke point every caller goes through, so no direct caller can bypass the gate."""
    root = Path(repo_root).resolve()
    assert_declared_kc_shards(root)
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
