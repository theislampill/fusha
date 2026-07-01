"""Load the repo-authored Fusha morphology smoke database."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MORPH_ROOT = ROOT / "fusha" / "morphology"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


@lru_cache(maxsize=1)
def load_morph_db() -> dict[str, list[dict[str, Any]]]:
    data = MORPH_ROOT / "data"
    return {
        "prefixes": read_jsonl(data / "prefixes.jsonl"),
        "stems": read_jsonl(data / "stems.sample.jsonl"),
        "suffixes": read_jsonl(data / "suffixes.jsonl"),
        "particles": read_jsonl(data / "particles.jsonl"),
        "patterns": read_jsonl(data / "patterns.jsonl"),
        "compat_prefix_stem": read_jsonl(data / "compatibility-prefix-stem.jsonl"),
        "compat_stem_suffix": read_jsonl(data / "compatibility-stem-suffix.jsonl"),
        "compat_prefix_suffix": read_jsonl(data / "compatibility-prefix-suffix.jsonl"),
    }


def all_generation_rows() -> list[dict[str, Any]]:
    db = load_morph_db()
    return db["stems"] + db["particles"]
