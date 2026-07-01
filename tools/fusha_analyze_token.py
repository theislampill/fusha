"""Analyze one Qamus Mode A token row from JSON on stdin or --input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fusha_mode_a import analyze_source_row


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one source-addressed Qamus token row.")
    parser.add_argument("--input", help="JSON file. Defaults to stdin.")
    args = parser.parse_args()
    if args.input:
        row = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        row = json.load(sys.stdin)
    print(json.dumps(analyze_source_row(row), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
