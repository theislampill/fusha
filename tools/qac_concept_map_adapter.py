#!/usr/bin/env python3
"""Parse a QAC predicate-style concept map for internal routing metadata.

The concept map is NOT a translation source and MUST NOT generate public hover
text. It is useful only for internal semantic routing, curriculum grouping, and
review prioritization.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


TRIPLE_RE = re.compile(r"^\((?P<rel>[a-z-]+)\s+(?P<subject>[^\s()]+)\s+(?P<object>[^\s()]+)\)$")
ALLOWED_RELATIONS = {
    "subclass",
    "instance",
    "name-of",
    "son-of",
    "daughter-of",
    "adopted-son-of",
}
PERSON_CLASSES = {"person", "prophet", "messenger", "apostle", "woman", "man"}
PLACE_CLASSES = {"place", "city", "mountain", "valley", "land"}
GROUP_CLASSES = {"people", "tribe", "nation", "community"}
OBJECT_CLASSES = {"plant", "body-part", "book", "scripture", "false-deity"}


@dataclass(frozen=True)
class RelationTriple:
    rel: str
    subject: str
    object: str
    line_no: int


def iter_relation_triples(text: str) -> list[RelationTriple]:
    triples: list[RelationTriple] = []
    in_fence = False
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not line or line.startswith(";"):
            continue
        # Prefer fenced predicate blocks, but accept bare predicate lines too.
        if not in_fence and not line.startswith("("):
            continue
        match = TRIPLE_RE.match(line)
        if not match:
            continue
        rel = match.group("rel")
        if rel not in ALLOWED_RELATIONS:
            continue
        triples.append(
            RelationTriple(
                rel=rel,
                subject=match.group("subject"),
                object=match.group("object"),
                line_no=line_no,
            )
        )
    return triples


class ConceptGraph:
    def __init__(self, triples: list[RelationTriple]) -> None:
        self.triples = triples

    @classmethod
    def from_path(cls, path: Path) -> "ConceptGraph":
        return cls(iter_relation_triples(path.read_text(encoding="utf-8")))

    def relations(self, rel: str) -> list[RelationTriple]:
        return [triple for triple in self.triples if triple.rel == rel]

    def classes(self, concept: str) -> set[str]:
        return {triple.object for triple in self.triples if triple.rel == "instance" and triple.subject == concept}

    def instances(self, class_id: str) -> set[str]:
        return {triple.subject for triple in self.triples if triple.rel == "instance" and triple.object == class_id}

    def superclasses(self, class_id: str) -> set[str]:
        return {triple.object for triple in self.triples if triple.rel == "subclass" and triple.subject == class_id}

    def names_of(self, concept: str) -> set[str]:
        return {triple.subject for triple in self.triples if triple.rel == "name-of" and triple.object == concept}

    def kinship(self, concept: str) -> list[RelationTriple]:
        return [
            triple
            for triple in self.triples
            if triple.rel in {"son-of", "daughter-of", "adopted-son-of"}
            and (triple.subject == concept or triple.object == concept)
        ]

    def semantic_flags(self, concept: str) -> set[str]:
        direct = self.classes(concept)
        inherited = set(direct)
        frontier = list(direct)
        while frontier:
            cur = frontier.pop()
            for parent in self.superclasses(cur):
                if parent not in inherited:
                    inherited.add(parent)
                    frontier.append(parent)
        flags = set()
        if inherited & PERSON_CLASSES:
            flags.add("person_or_name_review")
        if inherited & PLACE_CLASSES:
            flags.add("place_review")
        if inherited & GROUP_CLASSES:
            flags.add("people_group_review")
        if inherited & OBJECT_CLASSES:
            flags.add("semantic_category_review")
        if self.names_of(concept) or self.kinship(concept):
            flags.add("relationship_metadata_internal_only")
        return flags

    def summary(self) -> dict:
        relation_counts = {rel: len(self.relations(rel)) for rel in sorted(ALLOWED_RELATIONS)}
        concepts = sorted({triple.subject for triple in self.triples} | {triple.object for triple in self.triples})
        return {
            "relation_counts": relation_counts,
            "concept_count": len(concepts),
            "public_hover_source": False,
            "allowed_use": [
                "internal_semantic_routing",
                "concept_aware_blocker_labels",
                "curriculum_grouping",
                "review_prioritization",
            ],
            "prohibited_use": [
                "hover_translation",
                "public_provenance",
                "automatic_token_closure",
                "override_sarf_nahw_irab_or_context",
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Path to qac_concept_map.md")
    parser.add_argument("--concept", help="Emit semantic flags for one concept id")
    args = parser.parse_args()

    graph = ConceptGraph.from_path(args.path)
    payload = graph.summary()
    if args.concept:
        payload["concept"] = {
            "id": args.concept,
            "classes": sorted(graph.classes(args.concept)),
            "names_of": sorted(graph.names_of(args.concept)),
            "kinship": [asdict(triple) for triple in graph.kinship(args.concept)],
            "semantic_flags": sorted(graph.semantic_flags(args.concept)),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
