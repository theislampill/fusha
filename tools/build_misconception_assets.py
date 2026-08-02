#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Operationalize the misconception registry into consumable assets:

  misconceptions/fixture-candidates.jsonl   one NORMALIZED fixture-candidate
      record per candidate_fixture cluster — the shape Sol's promotion
      process consumes (wrong-reasoning pattern, correction, minimal
      contrast, target consumer, evidence status). Source-visible answers
      are marked as such: these are candidates, never independent evals.
  misconceptions/remediation-projections.jsonl   for every
      instructional_only cluster, a REAL remediation artifact emitted by the
      registered pedagogical_projection consumer (not a Markdown stub).

Deterministic; CI recompute-gated; candidate plane only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

sys.path.insert(0, str(ROOT / "tools"))
import curriculum_unit_consumer as consumer  # noqa: E402


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    registry = _jsonl(BASE / "misconceptions" / "misconception-registry.jsonl")
    pack, _ = consumer.load("inc-pedagogy")

    fixtures, remediations = [], []
    for c in registry:
        if c["disposition"] == "candidate_fixture":
            fixtures.append({
                "schema": "curriculum.l1l6_misconception_fixture_candidate.v1",
                "candidate_id": "fc-" + c["misconception_id"],
                "misconception_id": c["misconception_id"],
                "violated_capabilities": c["violated_capabilities"],
                "wrong_reasoning_pattern": c["pattern"],
                "why_wrong": c["why_wrong"],
                "correction_procedure": c["correction_principle"],
                "minimal_positive_contrast": ("apply the correction "
                                              "principle to the same frame: "
                                              + c["correction_principle"]),
                "adversarial_case_note": ("the pattern itself IS the "
                                          "adversarial case: a consumer "
                                          "tempted into it must be caught"),
                "target_consumer": "tools/curriculum_unit_consumer.py",
                "target_units": c["related_units"],
                "source_lessons": sorted({m["lesson_id"]
                                          for m in c["manifestations"]}),
                "evidence_status": ("source-visible (lesson-derived, "
                                    "clean-room restated); usable as a "
                                    "regression fixture AFTER review — NEVER "
                                    "as independent evaluation"),
                "promotion": "Sol review; no candidate-to-certified auto-promotion",
                "status": "candidate",
            })
        elif c["disposition"] == "instructional_only":
            data = {
                "fact_ref": (c["related_units"][0] if c["related_units"]
                             else "misconception:" + c["misconception_id"]),
                "purpose": c["correction_principle"],
                "recognition": c["pattern"],
                "procedure": c["why_wrong"],
                "error_warning": c["pattern"],
                "contrast": c["correction_principle"],
                "destination": "tutor remediation routing",
            }
            result = consumer.analyze_pedagogy({"data": data}, pack)
            remediations.append({
                "schema": "curriculum.l1l6_misconception_remediation.v1",
                "misconception_id": c["misconception_id"],
                "compiled_by": "tools/curriculum_unit_consumer.py analyze_pedagogy",
                "result": result,
                "status": "candidate",
            })
    return fixtures, remediations


def serialize(fixtures, remediations):
    out = {}
    out[str(BASE / "misconceptions" / "fixture-candidates.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in fixtures
    ).encode("utf-8")
    out[str(BASE / "misconceptions" / "remediation-projections.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in remediations
    ).encode("utf-8")
    out[str(BASE / "misconceptions" / "assets.meta.json")] = (json.dumps({
        "schema": "curriculum.l1l6_misconception_assets.meta.v1",
        "generator": "tools/build_misconception_assets.py",
        "fixture_candidates": len(fixtures),
        "remediation_projections": len(remediations),
        "remediations_candidate_projected": sum(
            1 for r in remediations if r["result"]["decision"] == "candidate_projected"),
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
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
            print("FAIL: misconception assets differ: %s" % ", ".join(bad))
            return 1
        print("OK: misconception assets byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
