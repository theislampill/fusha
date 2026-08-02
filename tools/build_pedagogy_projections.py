#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile a candidate pedagogical projection for EVERY canonical unit by
running the REAL pedagogical_projection consumer (inc-pedagogy's latest
contract) over inputs assembled from the unit's contributing lessons'
qualification records. No teaching text is authored here: every field is a
pure function of qualified data; a unit whose records lack the required
inputs gets an honest ABSTENTION row (reason + missing keys), never invented
content.

Output: curriculum/l1l6/projections/unit-projections.jsonl (+ meta).
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


def _join(parts, limit=3):
    seen = []
    for p in parts:
        if p and p not in seen:
            seen.append(p)
        if len(seen) >= limit:
            break
    return "; ".join(seen) if seen else None


def build():
    units = _jsonl(BASE / "canonical" / "canonical-units.jsonl")
    quals = {}
    for f in sorted((BASE / "qualification").glob("L*.jsonl")):
        for q in _jsonl(f):
            quals[q["lesson_id"]] = q
    pack, _ = consumer.load("inc-pedagogy")

    rows = []
    for u in sorted(units, key=lambda x: x["unit_id"]):
        contribs = [quals[l] for l in sorted(u.get("contributing_lessons", {}))
                    if l in quals]
        rivals = _join([f for q in contribs for f in q.get("uncertainty_flags", [])
                        if any(k in f.lower() for k in
                               ("school", "rival", "dispute", "analysis-dependent"))], 2)
        data = {
            "fact_ref": u["unit_id"],
            "purpose": _join([q.get("instructional_purpose") for q in contribs], 1)
                       or u.get("summary"),
            "recognition": _join([r for q in contribs
                                  for r in q.get("recognition_criteria", [])]),
            "procedure": _join([r for q in contribs
                                for r in q.get("procedures", [])]),
            "conditions_exceptions": _join(
                [r for q in contribs for r in
                 (q.get("conditions", []) + q.get("exceptions", []))]),
            "prerequisites": _join([r for q in contribs
                                    for r in q.get("prerequisite_knowledge", [])]),
            "error_warning": _join([m.get("pattern") for q in contribs
                                    for m in q.get("common_mistakes", [])], 2),
            "contrast": _join([r for q in contribs
                               for r in q.get("contrasts", [])], 2),
            "rival_notice": rivals,
            "destination": _join([q.get("tutor_drill_relevance") for q in contribs], 1)
                           or "tutor prerequisite routing",
        }
        data = {k: v for k, v in data.items() if v is not None}
        result = consumer.analyze_pedagogy({"data": data}, pack)
        rows.append({
            "schema": "curriculum.l1l6_unit_projection.v1",
            "unit_id": u["unit_id"],
            "axis": u["axis"],
            "compiled_by": "tools/curriculum_unit_consumer.py analyze_pedagogy (inc-pedagogy latest contract)",
            "contributing_lessons": sorted(u.get("contributing_lessons", {})),
            "result": result,
            "status": "candidate",
        })
    # the de-authorized consumer emits candidate_projected (Sol fix-request
    # round 2, finding 6: comparing against the retired "projected" label
    # made every row count as abstained while also counting as projected)
    projected = sum(1 for r in rows if r["result"]["decision"] == "candidate_projected")
    abstained = [r["unit_id"] for r in rows
                 if r["result"]["decision"] != "candidate_projected"]
    meta = {
        "schema": "curriculum.l1l6_unit_projection.v1.meta",
        "generator": "tools/build_pedagogy_projections.py",
        "units": len(rows),
        "candidate_projected": projected,
        "abstained": len(abstained),
        "abstained_units": abstained,
        "abstention_honesty": "abstained units lack required qualified inputs (recognition evidence, purpose or fact_ref); their projections are NOT authored around the gap — the gap routes to unit-record enrichment",
        "with_error_warning": sum(
            1 for r in rows if r["result"].get("fields", {}).get("common_error_warning")),
        "with_unresolved_notice": sum(
            1 for r in rows if r["result"].get("fields", {}).get("unresolved_notice")),
    }
    return rows, meta


def serialize(rows, meta):
    out = {}
    out[str(BASE / "projections" / "unit-projections.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    out[str(BASE / "projections" / "unit-projections.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
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
            print("FAIL: unit projections differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: unit projections byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
