#!/usr/bin/env python3
"""Unit checks for the internal-only QAC concept-map adapter."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.qac_concept_map_adapter import ConceptGraph, iter_relation_triples


SAMPLE = """
```lisp
(subclass prophet person)
(subclass city place)
(subclass plant object)
(instance salih messenger)
(instance aad people)
(instance badr city)
(instance fig plant)
(name-of ahmad muhammad)
(daughter-of maryam imran)
```
"""


def check(name: str, cond: bool) -> None:
    if not cond:
        raise AssertionError(name)
    print("ok  " + name)


def main() -> int:
    triples = iter_relation_triples(SAMPLE)
    graph = ConceptGraph(triples)
    summary = graph.summary()

    check("parses predicate triples", len(triples) == 9)
    check("counts relation inventory", summary["relation_counts"]["instance"] == 4)
    check("keeps concept map internal only", summary["public_hover_source"] is False)
    check("does not allow hover translation", "hover_translation" in summary["prohibited_use"])
    check("finds class instances", graph.instances("city") == {"badr"})
    check("finds superclasses", graph.superclasses("city") == {"place"})
    check("flags places", "place_review" in graph.semantic_flags("badr"))
    check("flags semantic categories", "semantic_category_review" in graph.semantic_flags("fig"))
    check("keeps kinship internal", "relationship_metadata_internal_only" in graph.semantic_flags("maryam"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
