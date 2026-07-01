"""Validate the rule-ranked parser/disambiguation baseline fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_disambiguate import disambiguate_rows
from fusha_dependency_parse import parse_dependencies


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fusha" / "parser" / "examples" / "parser-smoke.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate parser baseline smoke fixtures.")
    parser.add_argument("--fixture", default=str(FIXTURE))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    rows = read_jsonl(Path(args.fixture))
    disambig = disambiguate_rows(rows)
    deps = parse_dependencies(disambig)
    errors: list[str] = []
    by_surface = {row["surface"]: row for row in disambig["token_results"]}
    for fixture in rows:
        result = by_surface.get(fixture["surface"])
        if not result:
            errors.append(f"{fixture['surface']}: missing disambiguation result")
            continue
        if fixture.get("expected_abstention") != result["abstention"]:
            errors.append(f"{fixture['surface']}: abstention {result['abstention']} != {fixture.get('expected_abstention')}")
        if fixture.get("expected_gate") and result["gate"] != fixture["expected_gate"]:
            errors.append(f"{fixture['surface']}: gate {result['gate']} != {fixture['expected_gate']}")
        if fixture.get("requires_governor") and not result.get("governor_justification"):
            errors.append(f"{fixture['surface']}: missing governor justification")
    if not deps["dependency_candidates"]:
        errors.append("no dependency candidates emitted")
    result = {
        "ok": not errors,
        "rows": len(rows),
        "resolved": disambig["summary"]["resolved"],
        "abstained": disambig["summary"]["abstained"],
        "dependency_candidates": len(deps["dependency_candidates"]),
        "claim": "rule-ranked smoke parser only; no trained dependency parser certification",
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
