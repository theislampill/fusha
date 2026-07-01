"""Project Mode A analyses into public-safe hover rows."""

from __future__ import annotations

import argparse
from pathlib import Path

from fusha_mode_a import make_public_projection, read_jsonl, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Project Mode A analysis rows to public hover JSONL.")
    parser.add_argument("--source-rows", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    source_rows = {row["row_id"]: row for row in read_jsonl(Path(args.source_rows))}
    projections = []
    for analysis in read_jsonl(Path(args.analysis)):
        row = source_rows[analysis["source_row_id"]]
        projections.append(make_public_projection(row, analysis))
    write_jsonl(Path(args.out), projections)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
