#!/usr/bin/env python3
"""Validate the generated largelexicon morphology sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import MORPH_EXAMPLE_DIR, public_boundary_errors, read_jsonl


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = MORPH_EXAMPLE_DIR / "largelexicon-stems.sample.jsonl"


def validate(path: Path = SAMPLE) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing stem sample: {path.relative_to(ROOT)}"]
    rows = read_jsonl(path)
    if len(rows) < 100:
        errors.append("largelexicon stem sample must contain at least 100 rows")
    seen: set[str] = set()
    pos_seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        label = f"{path.name}:{i}"
        stem_id = row.get("stem_id")
        if not stem_id:
            errors.append(f"{label}: missing stem_id")
        elif stem_id in seen:
            errors.append(f"{label}: duplicate stem_id {stem_id}")
        seen.add(stem_id)
        pos_seen.add(row.get("pos") or "")
        surface = row.get("surface") or ""
        segment_surface = "".join(seg.get("surface", "") for seg in row.get("visible_segments", []))
        if segment_surface != surface:
            errors.append(f"{label}: visible segments do not concatenate to surface")
        if row.get("pos") == "proper_noun" and row.get("root"):
            errors.append(f"{label}: proper noun must not invent root")
        if not row.get("root") and not row.get("no_root_reason"):
            errors.append(f"{label}: no-root row needs no_root_reason")
        if row.get("source") != "qamus_current_authored":
            errors.append(f"{label}: source must be qamus_current_authored")
        errors.extend(public_boundary_errors(row, label))
    if not {"verb", "noun"} <= pos_seen:
        errors.append(f"sample needs at least verb and noun rows, saw {sorted(pos_seen)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon morphology sample.")
    parser.add_argument("--sample", default=str(SAMPLE))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.sample))
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
