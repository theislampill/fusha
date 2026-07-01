"""Transparent rule-ranked disambiguation baseline for smoke fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fusha_morph_analyze import analyze_surface


GATES = {
    "أَمْ": ("function_token_context_fixture", ["function_token", "local_context"]),
    "أَيَّانَ": ("function_token_context_fixture", ["function_token", "vocalized_surface"]),
    "لَهُمْ": ("preposition_attachment_fixture", ["preposition", "attached_pronoun", "pp_attachment"]),
    "تَعْبُدُوا۟": ("governed_verb_fixture", ["finite_verb", "previous_governor_particle"]),
    "ٱلْمُبْطِلُونَ": ("nominal_participle_fixture", ["active_participle", "plural_suffix"]),
}

GOVERNORS = {
    "لَهُمْ": "The lam relation attaches to the following nominal phrase in the local fixture; the pronoun remains governed by the preposition.",
    "تَعْبُدُوا۟": "The verb is governed by the preceding أَلَّا environment in the smoke fixture; mood remains context-marked.",
}


def disambiguate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for row in rows:
        surface = row["surface"]
        candidates = analyze_surface(surface)
        gate, reason_features = GATES.get(surface, ("abstain_unknown_surface", ["unknown_surface"]))
        abstention = not candidates or gate == "abstain_unknown_surface"
        ranked = [
            {
                "candidate_ref": cand["candidate_id"],
                "score": 1.0 if idx == 0 else max(0.1, 0.8 - idx * 0.1),
                "rank": idx + 1,
                "calibration": "fixture_high" if idx == 0 else "fixture_low",
            }
            for idx, cand in enumerate(candidates)
        ]
        results.append(
            {
                "surface": surface,
                "loc": row.get("loc"),
                "chosen_candidate_ref": ranked[0]["candidate_ref"] if ranked else None,
                "ranked_candidates": ranked,
                "abstention": abstention,
                "gate": gate,
                "reason_features": reason_features,
                "governor_justification": GOVERNORS.get(surface),
                "unsafe_if_public": abstention,
            }
        )
    return {
        "schema": "fusha/disambiguation-result@1",
        "token_results": results,
        "summary": {
            "tokens": len(results),
            "resolved": sum(1 for row in results if not row["abstention"]),
            "abstained": sum(1 for row in results if row["abstention"]),
        },
        "claim": "rule-ranked smoke baseline only",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run rule-ranked Fusha disambiguation on JSONL rows.")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    print(json.dumps(disambiguate_rows(read_jsonl(Path(args.input))), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
