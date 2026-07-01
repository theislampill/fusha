"""Load repo-authored Fusha morphology databases.

The default DB remains the small smoke database. The opt-in ``largelexicon`` DB
adds generated Qamus-authored sample stems; it is a candidate layer, not a
general Classical Arabic parser certification.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MORPH_ROOT = ROOT / "fusha" / "morphology"
LARGELEXICON_STEMS = MORPH_ROOT / "examples" / "largelexicon-stems.sample.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


@lru_cache(maxsize=4)
def load_morph_db(db: str = "smoke") -> dict[str, list[dict[str, Any]]]:
    if db not in {"smoke", "largelexicon"}:
        raise ValueError(f"unsupported morph DB {db!r}; expected smoke or largelexicon")
    data = MORPH_ROOT / "data"
    rows = {
        "prefixes": read_jsonl(data / "prefixes.jsonl"),
        "stems": read_jsonl(data / "stems.sample.jsonl"),
        "suffixes": read_jsonl(data / "suffixes.jsonl"),
        "particles": read_jsonl(data / "particles.jsonl"),
        "patterns": read_jsonl(data / "patterns.jsonl"),
        "compat_prefix_stem": read_jsonl(data / "compatibility-prefix-stem.jsonl"),
        "compat_stem_suffix": read_jsonl(data / "compatibility-stem-suffix.jsonl"),
        "compat_prefix_suffix": read_jsonl(data / "compatibility-prefix-suffix.jsonl"),
    }
    if db == "largelexicon" and LARGELEXICON_STEMS.exists():
        large_stems = read_jsonl(LARGELEXICON_STEMS)
        for row in large_stems:
            row.setdefault("source", "qamus_current_authored")
            row.setdefault("risk_flags", []).append("largelexicon_sample_candidate")
        rows["stems"] = rows["stems"] + large_stems
        rows["largelexicon_stems"] = large_stems
    else:
        rows["largelexicon_stems"] = []
    rows["db"] = [{"name": db, "claim": "candidate morphology data; not arbitrary-text certification"}]
    return rows


def all_generation_rows(db_name: str = "smoke") -> list[dict[str, Any]]:
    db = load_morph_db(db_name)
    return db["stems"] + db["particles"]
