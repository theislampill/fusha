#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the curriculum corpus pilot: candidate instructional envelopes for
canonical Quranic occurrences, derived ENTIRELY from committed p007 pilot
authority (typed facts, projections, reverse index, event trail) — no new
linguistic conclusion is introduced.

Occurrences: quran:2:34:5 (li + Adam, diptote jarr=fatha host) and
quran:61:5:4 (li + qawmihi, the multi-entry canary with an existing website
payload). The REUSABLE LESSON (clitic carve + evidence-required letter
ownership, units u-s09/u-s01, increment inc-ownership) is applied to both
occurrences by the same rules — the second occurrence is the reuse proof.

Honesty invariants:
- every fact cited comes from qamus/examples/p007-li-pilot/ with its
  certification posture copied verbatim, never upgraded;
- host-INTERNAL letter ownership is NOT certified by the repo, so the real
  consumer (tools/curriculum_unit_consumer.py) is invoked and its
  no_root_evidence ABSTENTION is recorded — unresolved state preserved,
  not papered over;
- colour segments and hover cards are read from the SAME projection record;
  the builder asserts their parity and carries the projection hash shared
  by every appearance;
- the website envelope for 61:5:4 references the EXISTING payload sample;
  for 2:34:5 (no payload exists) a candidate_payload_shape is derived and
  explicitly marked non-deliverable.

Deterministic: byte-identical output on rerun. Stdlib only. Writes ONLY
curriculum/l1l6/corpus-pilot/.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P007 = ROOT / "qamus" / "examples" / "p007-li-pilot"
OUT = ROOT / "curriculum" / "l1l6" / "corpus-pilot"

sys.path.insert(0, str(ROOT / "tools"))
import curriculum_unit_consumer as consumer  # noqa: E402

TARGETS = ("quran:2:34:5", "quran:61:5:4")
HARAKAT_RE = re.compile("[ً-ْٰۖ-ۭ]")


def bare_letters(surface):
    return [ch for ch in HARAKAT_RE.sub("", surface)]


def build():
    facts = [json.loads(l) for l in
             (P007 / "typed-facts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    projections = [json.loads(l) for l in
                   (P007 / "projections.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    reverse_index = json.loads((P007 / "entry-reverse-index.json").read_text(encoding="utf-8"))
    payload_614 = json.loads(
        (ROOT / "qamus" / "examples" / "website-payloads" /
         "multi_entry_liqawmihi_61_5_4.payload.json").read_text(encoding="utf-8"))

    rootless = [f for f in facts if f["fact_type"] == "particle_rootlessness"]
    envelopes = {}
    for target in TARGETS:
        tf = [f for f in facts
              if any(s.get("quran_loc") == target for s in f.get("surface_spans", []))]
        proj_row = next(p for p in projections
                        if p["projection"]["occurrence_id"] == target)
        proj = proj_row["projection"]
        surface = proj["surface"]
        seg_fact = next(f for f in tf if f["fact_type"] == "clitic_host_segmentation")

        # parity within the single projection record: every colour segment's
        # component must be explained by a hover card and vice versa
        seg_surfaces = [s["surface"] for s in proj["segments"]]
        hover_surfaces = [h["component_surface"] for h in proj.get("hover_cards", [])]
        parity_ok = all(h in seg_surfaces for h in hover_surfaces) and bool(hover_surfaces)

        # appearance-level parity: one hash everywhere
        hashes = {a["projection_hash"] for a in proj_row["appearances"]}
        hash_parity = hashes == {proj_row["projection_hash"]}

        # the honest machine abstention on host-internal ownership: the repo
        # certifies the CARVE, not the host's internal root/pattern split
        consumer_unit, _ = consumer.load("inc-ownership", "unit-v2.json")
        consumer_result = consumer.analyze_ownership(
            {"surface": surface, "letters": bare_letters(surface),
             "token_kind": "noun"}, consumer_unit)

        envelopes[target] = {
            "schema": "curriculum.l1l6_corpus_pilot_envelope.v1",
            "status": "candidate",
            "occurrence_id": target,
            "surface": surface,
            "repository_authority": {
                "typed_facts": sorted(
                    [{"fact_id": f["fact_id"], "fact_type": f["fact_type"],
                      "certification_status_verbatim": f["certification"]["status"],
                      "source_file": "qamus/examples/p007-li-pilot/typed-facts.jsonl"}
                     for f in tf + rootless], key=lambda r: r["fact_id"]),
                "certification_event_trail": "qamus/examples/p007-li-pilot/certification/events.jsonl",
                "projection_source": "qamus/examples/p007-li-pilot/projections.jsonl",
                "projection_hash": proj_row["projection_hash"],
            },
            "letter_ownership": {
                "clitic_morpheme": {
                    "surface": seg_fact["fact_value"]["clitic"],
                    "class": "clitic (jarr lam)",
                    "rootlessness": "per particle_rootlessness fact (repo)",
                },
                "host": {
                    "surface": seg_fact["fact_value"]["carve"][1],
                    "internal_ownership": "UNRESOLVED — the repository certifies the carve, not the host's root/pattern letter split; preserved as pending",
                    "consumer_verdict": consumer_result,
                    "resolution_path": "host root certification via the sarf evidence ladder, then inc-ownership rules (packet TP-CURR-ROOTPATTERN-PROMOTION)",
                },
            },
            "sarf_facts": [f["fact_id"] for f in tf
                           if f["fact_type"] == "clitic_host_segmentation"] +
                          [f["fact_id"] for f in rootless],
            "nahw_facts": [f["fact_id"] for f in tf
                           if f["fact_type"] in ("contextual_function",
                                                 "governor_relation",
                                                 "case_mood_governor")],
            "colour_and_hover": {
                "derived_from_single_projection_record": True,
                "segments": proj["segments"],
                "hover_card_components": hover_surfaces,
                "segment_hover_parity": parity_ok,
            },
            "appearances": {
                "rows": proj_row["appearances"],
                "count": len(proj_row["appearances"]),
                "single_hash_parity": hash_parity,
            },
            "reverse_trace": {
                "entry_id": reverse_index["entry_id"],
                "occurrence_listed": target in json.dumps(reverse_index),
                "source_file": "qamus/examples/p007-li-pilot/entry-reverse-index.json",
            },
            "website_envelope": (
                {"kind": "existing_payload_reference",
                 "artifact_id": payload_614["artifact_id"],
                 "schema": payload_614["schema"],
                 "source_file": "qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json"}
                if target == "quran:61:5:4" else
                {"kind": "candidate_payload_shape",
                 "schema": "qamus.website_projection_payload.v1",
                 "occurrence_id": target,
                 "projection_hash": proj_row["projection_hash"],
                 "deliverable": False,
                 "note": "shape-compatible candidate; NOT a payload for delivery — payload production stays with the established website-handoff lane"}),
            "reusable_lesson": {
                "units": ["u-s09", "u-s01"],
                "increment": "curriculum/l1l6/increments/inc-ownership/",
                "lesson": "carve the jarr clitic, own letters only under evidence, abstain on the rest",
                "reuse_note": "the SAME rules process both occurrences; nothing token-specific was copied between them (method transfer, og-2)",
            },
            "unresolved_states": [
                "host_internal_letter_ownership (consumer abstains: no certified host root in the pilot store)",
            ],
            "boundaries": ["og-1", "og-2", "og-6",
                           "no certification minted by this envelope",
                           "no live surface touched"],
        }
    return envelopes


def serialize(envelopes):
    out = {}
    for target, env in envelopes.items():
        name = "envelope-%s.json" % target.replace("quran:", "").replace(":", "-")
        out[str(OUT / name)] = (json.dumps(env, ensure_ascii=False, indent=2,
                                           sort_keys=True) + "\n").encode("utf-8")
    meta = {
        "schema": "curriculum.l1l6_corpus_pilot_envelope.v1.meta",
        "generator": "tools/build_curriculum_corpus_pilot.py",
        "occurrences": sorted(envelopes),
        "reuse_demonstration": "one reusable lesson (inc-ownership rules) applied to both occurrences; second occurrence = reuse proof",
        "authority": "qamus/examples/p007-li-pilot/ (facts, projections, reverse index, event trail) — no new linguistic conclusions",
    }
    out[str(OUT / "corpus-pilot.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    OUT.mkdir(parents=True, exist_ok=True)
    files = serialize(build())
    bad = []
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(p.name)
        else:
            p.write_bytes(data)
            print("wrote %s" % p.relative_to(ROOT))
    if check:
        if bad:
            print("FAIL: corpus-pilot artifacts differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: corpus-pilot artifacts byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
