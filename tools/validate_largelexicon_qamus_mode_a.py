#!/usr/bin/env python3
"""Validate largelexicon Qamus Mode A worklist shape."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import public_boundary_errors, read_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "qamus" / "examples" / "mode_a_all_qword" / "largelexicon-qamus-mode-a-worklist.sample.jsonl"


def validate(path: Path = DEFAULT_SAMPLE) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing worklist sample: {path.relative_to(ROOT)}"]
    rows = read_jsonl(path)
    if len(rows) < 50:
        errors.append("worklist sample must contain at least 50 rows")
    row_ids: set[str] = set()
    for i, row in enumerate(rows, start=1):
        label = f"{path.name}:{i}"
        row_id = row.get("row_id")
        if row_id in row_ids:
            errors.append(f"{label}: duplicate row_id {row_id}")
        row_ids.add(row_id)
        for key in ["entry_id", "card_id", "qword_index", "visible_surface", "card_text", "quran_ref", "status", "route"]:
            if row.get(key) in (None, ""):
                errors.append(f"{label}: missing {key}")
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"{label}: live_mutation_allowed must be false")
        if row.get("status") not in {"needs_source_address_crosswalk", "candidate_input", "packet_ready"}:
            errors.append(f"{label}: unsupported status {row.get('status')!r}")
        errors.extend(public_boundary_errors(row, label))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon Qamus Mode A worklist sample.")
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.sample))
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
