"""Smoke dependency/i'rab candidate baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fusha_disambiguate import disambiguate_rows, read_jsonl


def parse_dependencies(disambiguation_result: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for row in disambiguation_result["token_results"]:
        surface = row["surface"]
        if surface == "لَهُمْ":
            candidates.append(
                {
                    "dependent": surface,
                    "head": "ءَالِهَةٌ",
                    "relation": "prepositional_possession_relation",
                    "irab_view": "jar-majrur relation with attached pronoun",
                    "governor_justification": row["governor_justification"],
                    "confidence": "fixture_high",
                }
            )
        elif surface == "تَعْبُدُوا۟":
            candidates.append(
                {
                    "dependent": surface,
                    "head": "أَلَّا",
                    "relation": "governed_finite_verb",
                    "irab_view": "imperfect verb governed by preceding particle environment",
                    "governor_justification": row["governor_justification"],
                    "confidence": "fixture_high",
                }
            )
        elif surface in {"أَمْ", "أَيَّانَ"}:
            candidates.append(
                {
                    "dependent": surface,
                    "head": "clause",
                    "relation": "function_particle",
                    "irab_view": "contextual function token",
                    "governor_justification": "Fixture-level function decision; broad i'rab remains gated.",
                    "confidence": "fixture_medium",
                }
            )
        elif surface == "ٱلْمُبْطِلُونَ":
            candidates.append(
                {
                    "dependent": surface,
                    "head": "clause_predication",
                    "relation": "nominal_participle_subject_or_agentive",
                    "irab_view": "agentive participial noun in local clause",
                    "governor_justification": "Fixture-level nominal role; case claims remain context-gated.",
                    "confidence": "fixture_medium",
                }
            )
    return {
        "schema": "fusha/dependency-parse-result@1",
        "dependency_candidates": candidates,
        "claim": "smoke dependency/i'rab candidates only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit dependency/i'rab smoke candidates.")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    disambig = disambiguate_rows(read_jsonl(Path(args.input)))
    print(json.dumps(parse_dependencies(disambig), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
