#!/usr/bin/env python3
"""Build the generated largelexicon morphology sample/full outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import STEM_FULL, STEM_SAMPLE, iter_entries, stem_rows_for_entry, write_jsonl


def build(sample_size: int, out_dir: Path | None = None, commit_full: bool = False) -> dict:
    stems = [stem for entry in iter_entries() for stem in stem_rows_for_entry(entry)]
    sample = stems[:sample_size]
    write_jsonl(STEM_SAMPLE, sample)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(out_dir / "largelexicon-stems.full.jsonl", stems)
    if commit_full:
        write_jsonl(STEM_FULL, stems)
    return {
        "schema": "fusha/largelexicon/morph-db-build-report@1",
        "sample_rows": len(sample),
        "full_rows_available": len(stems),
        "committed_full": commit_full,
        "claim": "generated Qamus-authored morphology candidates; not arbitrary-text certification",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build largelexicon morphology DB artifacts.")
    parser.add_argument("--sample-size", type=int, default=320)
    parser.add_argument("--out-dir")
    parser.add_argument("--commit-full", action="store_true")
    args = parser.parse_args()
    result = build(args.sample_size, Path(args.out_dir) if args.out_dir else None, args.commit_full)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
