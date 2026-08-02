#!/usr/bin/env python3
"""Build the two p007 website-handoff samples from canonical p007 facts.

These are candidate, non-deliverable envelopes.  They adapt the canonical
occurrence projection to the website schema; they do not create linguistic
facts, resolve the candidate sense, or resolve the uncompared governor
relation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P007 = ROOT / "qamus" / "examples" / "p007-li-pilot"
OUT = ROOT / "qamus" / "examples" / "website-payloads"
UNIVERSE = ROOT / "qamus" / "lattice" / "example-ayah-universe.jsonl"

TARGETS = {
    "quran:2:34:5": {
        "filename": "p007_li_adam_clean.payload.json",
        "artifact_id": "artifact:p007:2:34:5",
        "appearance_id": "6e35cbb25054:u0:x0:w4",
        "host_gloss": "Adam",
        "learner_explanation": (
            "The joined lam contributes the prepositional function; Adam is "
            "its governed host. The exact sense link and governor relation "
            "remain unresolved."
        ),
    },
    "quran:12:31:24": {
        "filename": "p007_lillahi_fused.payload.json",
        "artifact_id": "artifact:p007:12:31:24",
        "appearance_id": "0135b6be178e:u0:x0:w2",
        "host_gloss": "Allah",
        "learner_explanation": (
            "The joined lam contributes the prepositional function and is "
            "written fused with the following name. The exact sense link and "
            "governor relation remain unresolved."
        ),
    },
}


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def _hash(projection: dict) -> str:
    blob = json.dumps(projection, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _renderer_segments(source: dict, host_gloss: str, hover: dict,
                       fact_ids: list[str]) -> list[dict]:
    rows = []
    cursor = 0
    segmentation_ids = [fact_id for fact_id in fact_ids
                        if fact_id.endswith(":seg")]
    for index, segment in enumerate(source.get("segments") or []):
        surface = unicodedata.normalize("NFC", segment["surface"])
        is_clitic = index == 0
        rows.append({
            "segment_index": index,
            "surface": surface,
            "char_start": cursor,
            "char_end": cursor + len(surface),
            "semantic_class": segment["role"],
            "renderer_class": segment["colour_class"],
            "gloss": "for / to" if is_clitic else host_gloss,
            "sarf_note": hover.get("sarf_note") if is_clitic else None,
            "nahw_note": hover.get("nahw_note") if is_clitic else None,
            "fact_ids": fact_ids if is_clitic else segmentation_ids,
        })
        cursor += len(surface)
    return rows


def build() -> dict[str, dict]:
    projections = {
        row["projection"]["occurrence_id"]: row
        for row in _jsonl(P007 / "projections.jsonl")
    }
    facts = _jsonl(P007 / "typed-facts.jsonl")
    appearances = {
        row["appearance_id"]: row for row in _jsonl(UNIVERSE)
    }
    result = {}
    for occurrence_id, spec in TARGETS.items():
        source_row = projections[occurrence_id]
        source = source_row["projection"]
        source_hover = copy.deepcopy((source.get("hover_cards") or [])[0])
        relevant_facts = []
        for fact in facts:
            spans = fact.get("surface_spans") or []
            if any(span.get("quran_loc") == occurrence_id for span in spans) \
                    or fact.get("fact_type") == "particle_rootlessness":
                relevant_facts.append(fact["fact_id"])
        relevant_facts = sorted(relevant_facts)
        segments = _renderer_segments(
            source, spec["host_gloss"], source_hover, relevant_facts)
        surface = "".join(row["surface"] for row in segments)
        source_hover["component_surface"] = segments[0]["surface"]
        source_hover.setdefault("particle_identity", {}).pop("sense", None)
        source_hover["fact_ids"] = relevant_facts

        reverse_rows = []
        for source_appearance in source_row.get("appearances") or []:
            appearance_id = source_appearance["appearance_id"]
            row = appearances[appearance_id]
            reverse_rows.append({
                "appearance_id": appearance_id,
                "page_id": "entry:%s" % row["entry_id"],
                "page_kind": "entry",
                "projection_hash": None,
            })
        chosen = appearances[spec["appearance_id"]]
        projection = {
            "occurrence_id": occurrence_id,
            "surface": surface,
            "normalization": "NFC",
            "kind": "particle_clitic_word",
            "segments": segments,
            "whole_word_gloss": source_hover.get("contextual_gloss"),
            "learner_explanation": spec["learner_explanation"],
            "entry_links": [{
                "entry_id": "b10a1ee04666",
                "sense_id": None,
                "relation_kind": "clitic_component_of_entry",
                "segment_index": 0,
            }],
            "entry_link_state": "linked",
            "morpheme_spans": [{
                "morpheme_occurrence_id": "mocc:p007:%s" %
                                          occurrence_id.removeprefix("quran:"),
                "segment_index": 0,
                "char_start": segments[0]["char_start"],
                "char_end": segments[0]["char_end"],
            }],
            "root": None,
            "rootless_pedagogy": source.get("rootless_pedagogy"),
            "hover_cards": [source_hover],
            "unresolved": {
                "state": "canonical_dependencies_unresolved",
                "message": (
                    "The exact dictionary sense and the governor relation "
                    "remain under review; the certified segmentation, "
                    "function, governor identity, and case are preserved."
                ),
                "dependencies": source.get("unresolved_dependencies") or [],
            },
            "certification": {
                "status": "unresolved",
                "plane": source.get("certification_plane") or {},
            },
            "evidence_refs": relevant_facts,
        }
        projection_hash = _hash(projection)
        for row in reverse_rows:
            row["projection_hash"] = projection_hash
        payload = {
            "schema": "qamus.website_projection_payload.v1",
            "schema_version": "1.0.0",
            "payload_kind": "occurrence_projection",
            "occurrence_id": occurrence_id,
            "artifact_id": spec["artifact_id"],
            "candidate_only": True,
            "deliverable": False,
            "source_projection_hash": source_row["projection_hash"],
            "appearance": {
                "appearance_id": spec["appearance_id"],
                "page_id": "entry:%s" % chosen["entry_id"],
                "page_kind": "entry",
                "page_local": {
                    "selected_highlight": bool(chosen.get("selected")),
                    "entry_relationship": (
                        "entry_relation" if
                        chosen.get("appearance_index_entry_linked") else
                        "context_only"
                    ),
                    "focus": "example-card",
                    "navigation": [],
                },
            },
            "projection": projection,
            "projection_hash": projection_hash,
            "reverse_links": {
                "occurrence_to_appearances": reverse_rows,
                "entry_to_occurrences": [],
            },
            "provenance": {
                "provenance_class": "certified",
                "built_by": "tools/build_p007_website_payloads.py",
                "source_refs": [
                    "qamus/examples/p007-li-pilot/projections.jsonl#%s" %
                    occurrence_id,
                    "qamus/examples/p007-li-pilot/certification/events.jsonl",
                ],
            },
        }
        result[spec["filename"]] = payload
    return result


def serialize(payloads: dict[str, dict]) -> dict[Path, bytes]:
    return {
        OUT / filename: (
            json.dumps(payload, ensure_ascii=False, indent=2,
                       sort_keys=True) + "\n"
        ).encode("utf-8")
        for filename, payload in payloads.items()
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    bad = []
    for path, data in sorted(serialize(build()).items()):
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                bad.append(path.name)
        else:
            path.write_bytes(data)
            print("wrote %s" % path.relative_to(ROOT))
    if bad:
        print("FAIL: p007 website payload drift: %s" % ", ".join(bad))
        return 1
    if args.check:
        print("P007 WEBSITE PAYLOADS FRESH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
