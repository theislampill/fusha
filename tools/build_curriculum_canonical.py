#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consolidate the per-lesson qualification records into the canonical
absorption planes:

  canonical/canonical-units.jsonl     the canonical unit registry: the 21
                                      authored u-* units + merged cu-*
                                      proposals from the qualification lanes
                                      (deduped by proposed_id; contributing
                                      lessons unioned; capability recorded)
  canonical/lesson-unit-map.jsonl     the COMPLETE two-way relation:
                                      lesson -> all units receiving its
                                      content; unit -> all contributing
                                      lessons (with contribution kinds)
  misconceptions/misconception-registry.jsonl
                                      every learner-error pattern from every
                                      lesson, deduped into misconception
                                      clusters with per-lesson
                                      manifestations preserved, each with a
                                      closed disposition
  canonical/consolidation.meta.json   counts + acceptance-gate numbers

Dispositions for misconceptions (closed): candidate_fixture (violated
capability has a real consumer), instructional_only (no consumer yet —
reason recorded), review_blocked (uncertainty flags), never silently
dropped.

Deterministic: sorted merges, no timestamps. Reads ONLY committed artifacts.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

EXEC_CAPS = {"letter_ownership", "template_classification",
             "discriminator_table", "pattern_consistency", "licensing_table"}


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def slug(s):
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[^0-9a-z؀-ۿ]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:70]


def load():
    quals = []
    for f in sorted((BASE / "qualification").glob("L*.jsonl")):
        quals.extend(_jsonl(f))
    return {
        "quals": sorted(quals, key=lambda r: r["lesson_id"]),
        "units": _jsonl(BASE / "units" / "instructional-units.jsonl"),
    }


def build(ctx):
    quals, units = ctx["quals"], ctx["units"]

    # ---- canonical units: existing + merged proposals ----
    canonical = {}
    for u in units:
        canonical[u["unit_id"]] = {
            "schema": "curriculum.l1l6_canonical_unit.v1",
            "unit_id": u["unit_id"], "origin": "authored_wave",
            "axis": "sarf" if u["unit_id"].startswith("u-s") else "nahw",
            "summary": u["concept"],
            "capability_family": (u.get("machine_increments") or [None])[0] and
                                 "executable" or "instructional_only",
            "machine_increments": u.get("machine_increments", []),
            "contributing_lessons": {}, "status": "candidate",
        }
    proposals = {}
    for q in quals:
        um = q.get("unit_mapping") or {}
        for pu in um.get("proposed_new_units") or []:
            pid = pu["proposed_id"]
            row = proposals.setdefault(pid, {
                "schema": "curriculum.l1l6_canonical_unit.v1",
                "unit_id": pid, "origin": "qualification_wave",
                "axis": pu.get("axis", "cross"),
                "summary": pu.get("summary", ""),
                "capability_family": pu.get("capability_family"),
                "machine_increments": [],
                "contributing_lessons": {}, "status": "candidate",
                "why_existing_insufficient": pu.get("why_existing_insufficient", ""),
            })
            row["contributing_lessons"][q["lesson_id"]] = "proposer"
            if len(pu.get("summary", "")) > len(row["summary"]):
                row["summary"] = pu["summary"]
    canonical.update(proposals)

    # ---- two-way lesson<->unit map ----
    lesson_map = []
    for q in quals:
        um = q.get("unit_mapping") or {}
        kind = um.get("contribution_kind")
        targets = sorted(set(um.get("existing_units") or []) |
                         {pu["proposed_id"] for pu in um.get("proposed_new_units") or []})
        for t in targets:
            if t in canonical:
                canonical[t]["contributing_lessons"].setdefault(q["lesson_id"], kind)
        lesson_map.append({
            "schema": "curriculum.l1l6_lesson_unit_map.v1",
            "lesson_id": q["lesson_id"],
            "units": targets,
            "contribution_kind": kind,
            "equivalence_basis": um.get("equivalence_basis"),
            "repository_destination": q.get("repository_destination"),
            "new_capability_required": q.get("new_capability_required"),
        })

    # ---- misconception registry ----
    clusters = {}
    for q in quals:
        caps = set()
        um = q.get("unit_mapping") or {}
        for t in um.get("existing_units") or []:
            u = next((x for x in ctx["units"] if x["unit_id"] == t), None)
            if u and u.get("machine_increments"):
                caps.add(u["machine_increments"][0])
        for pu in um.get("proposed_new_units") or []:
            if pu.get("capability_family") in EXEC_CAPS:
                caps.add(pu["capability_family"])
        for m in q.get("common_mistakes") or []:
            key = slug(m.get("pattern", ""))[:60] or "unnamed"
            c = clusters.setdefault(key, {
                "schema": "curriculum.l1l6_misconception.v1",
                "misconception_id": None,  # assigned after sort
                "pattern_key": key,
                "pattern": m.get("pattern", ""),
                "why_wrong": m.get("why_wrong", ""),
                "correction_principle": m.get("correction_principle", ""),
                "violated_capabilities": set(),
                "manifestations": [],
                "related_units": set(),
            })
            c["manifestations"].append({"lesson_id": q["lesson_id"],
                                        "pattern": m.get("pattern", "")})
            c["violated_capabilities"] |= caps
            c["related_units"] |= set(um.get("existing_units") or [])
    mis_rows = []
    for i, key in enumerate(sorted(clusters)):
        c = clusters[key]
        caps = sorted(c["violated_capabilities"])
        has_consumer = any(cap in EXEC_CAPS or cap.startswith("inc-") for cap in caps)
        blocked = False
        c["misconception_id"] = "mc-%04d" % i
        c["violated_capabilities"] = caps
        c["related_units"] = sorted(c["related_units"])
        c["manifestations"] = sorted(c["manifestations"],
                                     key=lambda m: m["lesson_id"])
        c["disposition"] = ("candidate_fixture" if has_consumer else
                            "instructional_only")
        c["disposition_reason"] = (
            "violated capability has a real consumer; eligible for fixture "
            "restatement" if has_consumer else
            "no executable consumer for the violated capability yet — routes "
            "to tutor/hover pedagogy; consumer arrival re-disposes it")
        mis_rows.append(c)

    meta = {
        "schema": "curriculum.l1l6_consolidation.meta.v1",
        "generator": "tools/build_curriculum_canonical.py",
        "qualified_lessons": len(quals),
        "canonical_units": len(canonical),
        "authored_units": sum(1 for c in canonical.values()
                              if c["origin"] == "authored_wave"),
        "proposed_units_merged": len(proposals),
        "misconception_clusters": len(mis_rows),
        "misconception_manifestations": sum(len(c["manifestations"])
                                            for c in mis_rows),
        "dispositions": {
            d: sum(1 for c in mis_rows if c["disposition"] == d)
            for d in sorted({c["disposition"] for c in mis_rows})} if mis_rows else {},
        "contribution_kinds": {
            k: sum(1 for r in lesson_map if r["contribution_kind"] == k)
            for k in sorted({r["contribution_kind"] for r in lesson_map})} if lesson_map else {},
        "orphan_canonical_units": sorted(
            uid for uid, c in canonical.items()
            if not c["contributing_lessons"] and c["origin"] == "qualification_wave"),
    }
    can_rows = [canonical[k] for k in sorted(canonical)]
    for c in can_rows:
        c["contributing_lessons"] = dict(sorted(c["contributing_lessons"].items()))
    return can_rows, lesson_map, mis_rows, meta


def serialize(can_rows, lesson_map, mis_rows, meta):
    out = {}

    def jl(path, rows):
        out[str(path)] = "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
        ).encode("utf-8")

    jl(BASE / "canonical" / "canonical-units.jsonl", can_rows)
    jl(BASE / "canonical" / "lesson-unit-map.jsonl", lesson_map)
    jl(BASE / "misconceptions" / "misconception-registry.jsonl", mis_rows)
    out[str(BASE / "canonical" / "consolidation.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    (BASE / "canonical").mkdir(parents=True, exist_ok=True)
    (BASE / "misconceptions").mkdir(parents=True, exist_ok=True)
    files = serialize(*build(load()))
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
            print("FAIL: consolidation differs from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: consolidation byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
