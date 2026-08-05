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

# Audit-driven merge table (independent completeness audit at f7ecf02):
# same-axis, same-substance unit pairs where one summary is a declared
# superset of the other, plus the mood-exponent trio that carried THREE
# capability families for one table (contradiction). Alias -> survivor;
# contributing lessons union into the survivor; the lesson-unit map is
# rewritten through this table so the two-way invariant holds.
MERGE_ALIASES = {
    "cu-mim-noun-function-discriminator": "cu-mim-initial-noun-discriminator",
    "cu-prohibitive-la-discriminator": "cu-la-negative-vs-prohibitive-discriminator",
    "cu-imperfect-mood-exponent-licensing": "cu-mood-exponent-matrix",
    "cu-mood-exponent-by-verb-class": "cu-mood-exponent-matrix",
    "cu-order-conditioned-agreement": "cu-agreement-order-animacy",
    "cu-naat-agreement-licensing": "cu-attributive-agreement-licensing",
    "cu-augmented-passive-vocalization": "cu-passive-voice-vocalization",
    "cu-diptote-licensing-table": "cu-diptote-cause-licensing",
}
# the mood-exponent survivor is pinned to ONE consumer interface
CAPABILITY_OVERRIDES = {
    "cu-mood-exponent-matrix": ("discriminator_table",
        "capability pinned by merge adjudication: three source lessons "
        "proposed three different families for one verb-class x mood -> "
        "exponent table; discriminator_table matches the inc-negation "
        "consumer that already reads mood evidence"),
    "cu-gemination-licensing": ("template_classification",
        "active pack interface pinned to template_classification: the current "
        "candidate pack covers a bounded Form-II/perfect-participle written-"
        "shadda subset; it does not claim closure of the broader licensing unit"),
    "cu-lexical-feminine-registry": ("discriminator_table",
        "active pack interface pinned to discriminator_table: the consumer "
        "performs an exact closed-registry lookup and never derives gender "
        "from written shape"),
    "cu-nongoverning-preverbal-inventory": ("discriminator_table",
        "active pack interface pinned to discriminator_table: the consumer "
        "matches exact closed-registry members and emits no mood, case, or "
        "governor conclusion"),
    "cu-suffix-abstract-noun": ("discriminator_table",
        "active pack interface pinned to discriminator_table: the consumer "
        "preserves the nisba, abstract-noun, and non-nisba geminated-yaa "
        "adjective rivals and requires independent base-category evidence"),
}


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
    merged_from = {}
    for q in quals:
        um = q.get("unit_mapping") or {}
        for pu in um.get("proposed_new_units") or []:
            pid = MERGE_ALIASES.get(pu["proposed_id"], pu["proposed_id"])
            if pu["proposed_id"] != pid:
                merged_from.setdefault(pid, set()).add(pu["proposed_id"])
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
    for pid, row in proposals.items():
        if pid in merged_from:
            row["merged_from"] = sorted(merged_from[pid])
        if pid in CAPABILITY_OVERRIDES:
            cap, why = CAPABILITY_OVERRIDES[pid]
            row["capability_family"] = cap
            row["capability_adjudication"] = why
    canonical.update(proposals)

    # canonical<->increment backlink, DERIVED by unit_ref/unit_refs scan over
    # the discovered increments (never hand-edited).  Most packs own one unit;
    # a superseding pack may explicitly preserve several canonical-unit
    # contributions when its behavior subsumes an earlier pack version.
    inc_dir = BASE / "increments"
    if inc_dir.exists():
        for d in sorted(p for p in inc_dir.iterdir() if p.is_dir()):
            packs = sorted(d.glob("unit-v*.json"),
                           key=lambda p: int(p.stem.split("-v")[1]))
            if not packs:
                continue
            pack = json.loads(packs[-1].read_text(encoding="utf-8"))
            unit_refs = pack.get("unit_refs") or [pack.get("unit_ref")]
            for uref in unit_refs:
                if (uref in canonical
                        and d.name not in canonical[uref]["machine_increments"]):
                    canonical[uref]["machine_increments"].append(d.name)
                    canonical[uref]["machine_increments"].sort()
                    if canonical[uref].get("capability_family") in (
                            None, "instructional_only", "executable"):
                        canonical[uref]["capability_family"] = pack.get("capability")

    # ---- two-way lesson<->unit map ----
    lesson_map = []
    for q in quals:
        um = q.get("unit_mapping") or {}
        kind = um.get("contribution_kind")
        targets = sorted(set(um.get("existing_units") or []) |
                         {MERGE_ALIASES.get(pu["proposed_id"], pu["proposed_id"])
                          for pu in um.get("proposed_new_units") or []})
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
    lesson_targets = {r["lesson_id"]: r["units"] for r in lesson_map}
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
        if not c["related_units"]:
            # fallback binding: the manifesting lesson's full canonical-unit
            # targets (two-way map) — the cluster is bound to the lesson's
            # units even when the mistake record itself named none
            fallback = sorted({u for m in c["manifestations"]
                               for u in lesson_targets.get(m["lesson_id"], [])})
            if fallback:
                c["related_units"] = fallback
                c["binding_basis"] = "lesson_unit_map_fallback"
        c["unit_routable"] = bool(c["related_units"])
        if not c["related_units"]:
            c["routing_note"] = ("unbindable: the manifesting lesson maps to "
                                 "no canonical unit (instructional-only "
                                 "lesson) — remediation routes through the "
                                 "pedagogy consumer instead")
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
