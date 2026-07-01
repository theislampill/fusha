"""Dependency-free smoke morphology analyzer."""

from __future__ import annotations

import argparse
import json
from typing import Any

from fusha_morph_db import load_morph_db


def _candidate_from_stem(row: dict[str, Any], rank: int = 1) -> dict[str, Any]:
    segments = row["visible_segments"]
    return {
        "schema": "fusha/morphology-candidate@1",
        "candidate_id": f"morph:{row['stem_id']}",
        "surface": row["surface"],
        "segment_surface": "".join(seg["surface"] for seg in segments),
        "segments": segments,
        "root": row.get("root"),
        "lemma": row.get("lemma"),
        "pos": row.get("pos"),
        "form": row.get("form"),
        "gloss_shape": row.get("gloss_shape"),
        "features": {k: row[k] for k in ["voice", "aspect", "person", "gender", "number"] if k in row},
        "risk_flags": row.get("risk_flags", []),
        "rank": rank,
        "source": row.get("source", "repo_authored"),
        "entry_id": row.get("entry_id"),
    }


def _candidate_from_particle(row: dict[str, Any], rank: int = 1) -> dict[str, Any]:
    segment = {
        "surface": row["surface"],
        "role": "interrogative_time_particle" if row["surface"] == "أَيَّانَ" else "function_particle",
        "qg_class": row["qg_default_class"],
        "gloss": row["gloss_contribution"],
    }
    return {
        "schema": "fusha/morphology-candidate@1",
        "candidate_id": f"morph:{row['particle_id']}",
        "surface": row["surface"],
        "segment_surface": row["surface"],
        "segments": [segment],
        "root": None,
        "lemma": None,
        "pos": row["pos"],
        "form": None,
        "gloss_shape": "function_token",
        "features": {"function_candidates": row.get("function_candidates", [])},
        "risk_flags": row.get("risk_flags", []),
        "rank": rank,
        "source": "repo_authored",
    }


def analyze_surface(surface: str, db_name: str = "smoke") -> list[dict[str, Any]]:
    db = load_morph_db(db_name)
    candidates: list[dict[str, Any]] = []
    for row in db["stems"]:
        if row["surface"] == surface:
            candidates.append(_candidate_from_stem(row, rank=len(candidates) + 1))
    for row in db["particles"]:
        if row["surface"] == surface:
            candidates.append(_candidate_from_particle(row, rank=len(candidates) + 1))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one Arabic surface with the smoke morphology DB.")
    parser.add_argument("--surface", required=True)
    parser.add_argument("--db", choices=["smoke", "largelexicon"], default="smoke")
    args = parser.parse_args()
    print(json.dumps({"surface": args.surface, "db": args.db, "candidates": analyze_surface(args.surface, args.db)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
