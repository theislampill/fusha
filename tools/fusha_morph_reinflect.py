"""Tiny reinflection facade over the smoke generator."""

from __future__ import annotations

import argparse
import json

from fusha_morph_analyze import analyze_surface
from fusha_morph_generate import generate_surface


def reinflect(surface: str, generation_key: str) -> dict:
    analyses = analyze_surface(surface)
    generated = generate_surface({"generation_key": generation_key})
    return {
        "schema": "fusha/reinflection-result@1",
        "input_surface": surface,
        "input_candidates": analyses,
        "requested_generation_key": generation_key,
        "generated": generated,
        "claim": "smoke reinflection only; no broad paradigm coverage",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reinflect through an explicit smoke generation key.")
    parser.add_argument("--surface", required=True)
    parser.add_argument("--generation-key", required=True)
    args = parser.parse_args()
    print(json.dumps(reinflect(args.surface, args.generation_key), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
