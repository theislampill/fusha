from __future__ import annotations

from typing import Any

from tools.normalize_ar import norm_strict


def _surface(row: dict[str, Any]) -> str:
    return str(row.get("surface") or row.get("uthmani") or row.get("token") or "")


def align_monotonic_spans(
    engine_tokens: list[dict[str, Any]], gold_tokens: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Join equal norm_strict surface spans monotonically; quarantine boundary artifacts."""
    pairs: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    i = j = 0
    while i < len(engine_tokens) and j < len(gold_tokens):
        ei, gj = i, j
        engine_key = norm_strict(_surface(engine_tokens[i]))
        gold_key = norm_strict(_surface(gold_tokens[j]))
        if not engine_key or not gold_key:
            quarantined.append({"bucket": "tokenization_boundary_artifact", "engine": [i], "gold": [j]})
            i += 1
            j += 1
            continue
        while engine_key != gold_key:
            if len(engine_key) < len(gold_key) and i + 1 < len(engine_tokens):
                i += 1
                engine_key += norm_strict(_surface(engine_tokens[i]))
            elif len(gold_key) < len(engine_key) and j + 1 < len(gold_tokens):
                j += 1
                gold_key += norm_strict(_surface(gold_tokens[j]))
            else:
                break
        engine_indexes = list(range(ei, i + 1))
        gold_indexes = list(range(gj, j + 1))
        if engine_key == gold_key and len(engine_indexes) == len(gold_indexes) == 1:
            pairs.append({"engine_index": ei, "gold_index": gj, "key": engine_key})
        else:
            quarantined.append({
                "bucket": "tokenization_boundary_artifact",
                "engine": engine_indexes,
                "gold": gold_indexes,
                "engine_key": engine_key,
                "gold_key": gold_key,
            })
        i += 1
        j += 1
    if i < len(engine_tokens) or j < len(gold_tokens):
        quarantined.append({
            "bucket": "tokenization_boundary_artifact",
            "engine": list(range(i, len(engine_tokens))),
            "gold": list(range(j, len(gold_tokens))),
        })
    return {"pairs": pairs, "quarantined": quarantined}
