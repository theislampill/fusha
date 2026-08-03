#!/usr/bin/env python3
"""Validate largelexicon qg projection/candidate rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_mode_a import ALLOWED_QG_CLASSES
from largelexicon_common import public_boundary_errors, read_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "qamus" / "examples" / "largelexicon" / "hover-candidates.sample.jsonl"


def validate(path: Path = DEFAULT_SAMPLE) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing projection sample: {path.relative_to(ROOT)}"]
    rows = read_jsonl(path)
    if len(rows) < 50:
        errors.append("projection sample must contain at least 50 rows")
    statuses: set[str] = set()
    for i, row in enumerate(rows, start=1):
        label = f"{path.name}:{i}"
        statuses.add(row.get("status") or "")
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"{label}: live_mutation_allowed must be false")
        segment_surface = row.get("segment_surface")
        segments = row.get("segments") or []
        # R8: a withheld stem (collision, or a fully empty qg_segments row) is
        # not required to reconstruct visible_surface; every OTHER row still
        # must, so the concatenation invariant is not relaxed for them.
        if segment_surface is not None and segment_surface != row.get("visible_surface"):
            errors.append(f"{label}: segment_surface does not equal visible_surface")
        if not segments and row.get("token_contribution") is not None:
            errors.append(f"{label}: token_contribution must be null when segments is empty")
        bad = set(row.get("qg_classes") or []) - ALLOWED_QG_CLASSES
        if bad:
            errors.append(f"{label}: unsupported qg classes {sorted(bad)}")
        if row.get("status") not in {
            "candidate_for_executor_validation",
            "source_crosswalk_packet",
            "validator_packet",
            "parser_packet",
        }:
            errors.append(f"{label}: unsupported status {row.get('status')!r}")
        errors.extend(public_boundary_errors(row, label))
    if "source_crosswalk_packet" not in statuses:
        errors.append("sample should contain source_crosswalk_packet rows to prove non-live routing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon qg projection sample.")
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.sample))
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
