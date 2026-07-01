"""Small governor-justification facade for smoke parser rows."""

from __future__ import annotations

import argparse
import json

from fusha_disambiguate import GOVERNORS


def main() -> int:
    parser = argparse.ArgumentParser(description="Return smoke governor justification for a surface.")
    parser.add_argument("--surface", required=True)
    args = parser.parse_args()
    result = {
        "surface": args.surface,
        "governor_justification": GOVERNORS.get(args.surface),
        "claim": "fixture-level governor note only",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
