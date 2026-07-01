"""Analyze a JSONL card/worklist of Qamus Mode A source-addressed rows."""

from __future__ import annotations

import argparse
from pathlib import Path

from fusha_mode_a import analyze_source_row, read_jsonl, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Qamus Mode A source-addressed qword rows.")
    parser.add_argument("--input", required=True, help="Input JSONL source rows.")
    parser.add_argument("--out", required=True, help="Output JSONL analysis rows.")
    args = parser.parse_args()
    rows = read_jsonl(Path(args.input))
    write_jsonl(Path(args.out), [analyze_source_row(row) for row in rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
