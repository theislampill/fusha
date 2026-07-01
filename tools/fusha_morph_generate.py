"""Dependency-free smoke morphology generator."""

from __future__ import annotations

import argparse
import json
from typing import Any

from fusha_morph_db import all_generation_rows


def generate_surface(request: dict[str, Any]) -> dict[str, Any]:
    generation_key = request.get("generation_key")
    if not generation_key:
        return {"ok": False, "error": "generation_key required"}
    for row in all_generation_rows():
        if row.get("generation_key") == generation_key:
            return {
                "ok": True,
                "generation_key": generation_key,
                "surface": row["surface"],
                "source": "repo_authored",
                "claim": "smoke generator row only",
            }
    return {"ok": False, "generation_key": generation_key, "error": "unknown generation_key"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one smoke surface from a generation key.")
    parser.add_argument("--generation-key", required=True)
    args = parser.parse_args()
    print(json.dumps(generate_surface({"generation_key": args.generation_key}), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
