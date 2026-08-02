#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Candidate DRILL records for the existing instructional system (Sol repair
8): promotion/adapter artifacts only — nothing here is tutor-consumed, drill-
run, or runtime-integrated; ordinary integration is Sol-owned via the tutor/
KC adapter (see reports/sol-adapter-manifest.json).

One record per misconception fixture-candidate: stable drill id, capability
+ misconception link, prerequisites/difficulty from the contributing
lessons, prompt/input specification, expected rubric, explanation,
answer-leakage posture, abstention behaviour, intended existing runtime
consumer and the exact adapter requirement.

Output: curriculum/l1l6/drills-candidates/drill-candidates.jsonl (+ meta).
Deterministic; candidate plane only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    fcs = _jsonl(BASE / "misconceptions" / "fixture-candidates.jsonl")
    rows = []
    for fc in fcs:
        lessons = fc.get("source_lessons", [])
        level = min((int(l[1]) for l in lessons), default=1)
        rows.append({
            "schema": "curriculum.l1l6_drill_candidate.v1",
            "drill_id": "dr-" + fc["misconception_id"],
            "status": "candidate_not_runtime_integrated",
            "capability_link": fc["violated_capabilities"],
            "misconception_link": fc["misconception_id"],
            "unit_links": fc["target_units"],
            "prerequisites": "the linked units' prerequisite chains "
                             "(units/unit-dependencies.jsonl)",
            "difficulty_band": "L%d-origin (curriculum level of the source "
                               "lessons)" % level,
            "prompt_specification": ("present a frame instantiating the "
                                      "wrong-reasoning pattern and ask the "
                                      "learner to detect/correct it: "
                                      + fc["wrong_reasoning_pattern"]),
            "expected_rubric": fc["correction_procedure"],
            "explanation": fc["why_wrong"],
            "answer_leakage_posture": ("source-visible: derived from lesson-"
                                        "answered material; NEVER usable as "
                                        "independent assessment"),
            "abstention_behaviour": ("frames whose deciding evidence is "
                                      "absent must be excluded or marked "
                                      "undecidable — the drill never forces "
                                      "a choice the evidence cannot license"),
            "intended_runtime_consumer": ("the EXISTING tutor/drill runtime "
                                           "(curriculum/drills/ keys schema + "
                                           "tools/fusha_learner_feedback.py "
                                           "KC records)"),
            "adapter_requirement": ("Sol tutor/KC adapter: map drill_id -> "
                                     "KC id, wrap in the gate ladder, route "
                                     "remediation via misconception_link; "
                                     "this repo does NOT write tutor state"),
        })
    meta = {
        "schema": "curriculum.l1l6_drill_candidate.v1.meta",
        "generator": "tools/build_candidate_drills.py",
        "rows": len(rows),
        "runtime_integrated": 0,
        "honesty": "0 drills are runnable in the ordinary tutor today; these are complete promotion/adapter artifacts awaiting the Sol-owned integration",
    }
    return rows, meta


def serialize(rows, meta):
    out = {}
    out[str(BASE / "drills-candidates" / "drill-candidates.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    out[str(BASE / "drills-candidates" / "drill-candidates.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    (BASE / "drills-candidates").mkdir(parents=True, exist_ok=True)
    files = serialize(*build())
    bad = []
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(p.name)
        else:
            p.write_bytes(data)
            print("wrote %s (%d bytes)" % (p.relative_to(ROOT), len(data)))
    if check:
        if bad:
            print("FAIL: drill candidates differ: %s" % ", ".join(bad))
            return 1
        print("OK: drill candidates byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
