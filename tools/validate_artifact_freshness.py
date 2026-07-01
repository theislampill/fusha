"""Validate generated artifact freshness/retirement metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fusha_mode_a import FRESHNESS_KEYS, read_json


def validate_freshness(obj: dict[str, Any], label: str) -> list[str]:
    missing = sorted(FRESHNESS_KEYS - set(obj))
    errors = [f"{label}: missing freshness field {key}" for key in missing]
    if "supersedes" in obj and not isinstance(obj["supersedes"], list):
        errors.append(f"{label}: supersedes must be an array")
    if "status" in obj and obj["status"] not in {
        "active",
        "active_fixture_only",
        "superseded",
        "stale",
        "retired",
        "draft",
    }:
        errors.append(f"{label}: unsupported status {obj['status']!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate artifact freshness metadata.")
    parser.add_argument("path", nargs="?", help="JSON file to validate.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    path = Path(args.path) if args.path else Path("qamus/examples/mode_a_thin_slice/mode-a-bundle.json")
    data = read_json(path)
    errors = validate_freshness(data, str(path))
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "validated": str(path)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
