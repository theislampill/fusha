#!/usr/bin/env python3
"""Build largelexicon flywheel artifacts from projected candidate rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import PUBLIC_BOUNDARY, read_jsonl, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "qamus" / "examples" / "largelexicon" / "hover-candidates.sample.jsonl"
DEFAULT_OUT = ROOT / "qamus" / "examples" / "largelexicon" / "flywheel-artifacts.sample.jsonl"


ROUTES = {
    "source_crosswalk_packet": ["qamus_source_graph", "qamus_executor"],
    "candidate_for_executor_validation": ["sarf", "nahw", "qamus_executor", "curriculum"],
    "validator_packet": ["schema_validator", "qamus_executor"],
    "parser_packet": ["sarf", "nahw", "parser"],
}


def build(input_path: Path, output_path: Path) -> dict:
    rows = read_jsonl(input_path)
    artifacts = []
    for row in rows:
        artifacts.append(
            {
                "schema": "qamus/largelexicon-flywheel-artifact@1",
                "row_id": row["row_id"],
                "entry_id": row["entry_id"],
                "card_id": row["card_id"],
                "status": row["status"],
                "routes": ROUTES.get(row["status"], ["qamus_executor"]),
                "lesson": "Convert repeated qword findings into reusable sarf, nahw, parser, validator, or curriculum assets.",
                "next_action": row["route"],
                "public_boundary": dict(PUBLIC_BOUNDARY),
                "live_mutation_allowed": False,
            }
        )
    write_jsonl(output_path, artifacts)
    return {"rows": len(artifacts), "out": str(output_path.relative_to(ROOT))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build largelexicon flywheel artifact sample.")
    parser.add_argument("--input", default=str(DEFAULT_IN))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    result = build(Path(args.input), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
