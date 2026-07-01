"""Evaluate smoke morphology analysis/generation against authored fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_morph_analyze import analyze_surface
from fusha_morph_generate import generate_surface


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fusha" / "morphology" / "examples" / "morphology-smoke.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate morphology smoke fixtures.")
    parser.add_argument("--fixture", default=str(FIXTURE))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    rows = read_jsonl(Path(args.fixture))
    for row in rows:
        analyses = analyze_surface(row["surface"])
        if not analyses:
            errors.append(f"{row['surface']}: no analyses")
            continue
        best = analyses[0]
        if best["segment_surface"] != row["surface"]:
            errors.append(f"{row['surface']}: segment concat mismatch")
        expected_roles = row.get("expected_roles", [])
        actual_roles = [seg["role"] for seg in best["segments"]]
        if expected_roles and actual_roles != expected_roles:
            errors.append(f"{row['surface']}: roles {actual_roles} != {expected_roles}")
        if row.get("expected_root") != best.get("root"):
            errors.append(f"{row['surface']}: root {best.get('root')} != {row.get('expected_root')}")
        if row.get("generate_from"):
            generated = generate_surface(row["generate_from"])
            if generated.get("surface") != row["surface"]:
                errors.append(f"{row['surface']}: generator produced {generated.get('surface')}")
    result = {
        "ok": not errors,
        "rows": len(rows),
        "errors": errors,
        "claim": "smoke morphology only; not broad analyzer/generator certification",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
