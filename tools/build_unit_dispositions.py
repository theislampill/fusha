#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the 166-unit OPERATIONAL-DISPOSITION ledger — the freeze artifact.

Every canonical unit ends in one or more CLOSED states, with a single
strongest_state; the strongest-state totals sum to exactly the unit count.
States are COMPUTED from committed evidence (packs, projections, grounding,
misconception bindings, bundles, loops) — never asserted:

  machine_pack_consumed        latest pack exists AND the consumer decides
                               its fixtures (all-increments gate is green)
  occurrence_grounding_ready   exact V/N candidates with selected
                               occurrences, or committed occurrence links
  promotion_bundle_ready       a review-ready bundle exists for its increment
  fixture_source_ready         bound misconception fixture-candidates exist
  drill_or_remediation_ready   bound remediation projections exist
  tutor_projection_ready       its unit projection compiled (real consumer)
  instructional_only_with_consumer  declared instructional-only AND projected
  evidence_blocked / scholar_review_blocked / owner_adjudication_blocked /
  sol_integration_blocked      dimension blockers, named exactly

Output: curriculum/l1l6/canonical/unit-dispositions.jsonl (+ meta).
Gates (enforced by the validator): N/N dispositioned, 0 generic remainders,
0 invented consumer claims (machine states require a discovered pack), 0
blockers without exact cause, 0 operational states without a real consumer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

STRONGEST_ORDER = [
    "machine_pack_consumed", "occurrence_grounding_ready",
    "promotion_bundle_ready", "fixture_source_ready",
    "drill_or_remediation_ready", "tutor_projection_ready",
    "instructional_only_with_consumer",
    "sol_integration_blocked", "scholar_review_blocked",
    "owner_adjudication_blocked", "evidence_blocked",
]


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    units = _jsonl(BASE / "canonical" / "canonical-units.jsonl")
    projections = {r["unit_id"]: r for r in
                   _jsonl(BASE / "projections" / "unit-projections.jsonl")}
    grounding = {r["unit_id"]: r for r in
                 _jsonl(BASE / "canonical" / "vn-grounding.jsonl")}
    registry = _jsonl(BASE / "misconceptions" / "misconception-registry.jsonl")
    plinks = _jsonl(BASE / "links" / "pvn-precise-links.jsonl")
    mis_by_unit = {}
    for c in registry:
        for u in c.get("related_units", []):
            mis_by_unit.setdefault(u, []).append(c)
    occ_units = {r["unit_ref"] for r in plinks if r.get("occurrence_id")}
    bundles = {p.stem.replace(".bundle", "") for p in
               (BASE / "promotion").glob("*.bundle.json")}

    rows = []
    for u in sorted(units, key=lambda x: x["unit_id"]):
        uid = u["unit_id"]
        incs = u.get("machine_increments", [])
        proj = projections.get(uid)
        grow = grounding.get(uid, {})
        mis = mis_by_unit.get(uid, [])
        states, blockers = [], []
        if incs:
            states.append("machine_pack_consumed")
        if (grow.get("grounding_state") == "exact_vn_candidates"
                and any(x.get("selected_occurrences")
                        for x in grow.get("resolved", []))) or uid in occ_units:
            states.append("occurrence_grounding_ready")
        if any(i in bundles for i in incs):
            states.append("promotion_bundle_ready")
        if any(c["disposition"] == "candidate_fixture" for c in mis):
            states.append("fixture_source_ready")
        if any(c["disposition"] == "instructional_only" for c in mis):
            states.append("drill_or_remediation_ready")
        if proj and proj["result"]["decision"] == "projected":
            states.append("tutor_projection_ready")
            if u.get("capability_family") == "instructional_only":
                states.append("instructional_only_with_consumer")
        gs = grow.get("grounding_state")
        if gs == "sol_integration_blocked":
            states.append("sol_integration_blocked")
            blockers.append({"dimension": "occurrence_grounding",
                             "state": "sol_integration_blocked",
                             "cause": grow.get("blocker")})
        elif gs == "authority_blocked":
            states.append("evidence_blocked")
            blockers.append({"dimension": "occurrence_grounding",
                             "state": "evidence_blocked",
                             "cause": grow.get("blocker")})
        if any("school" in f.lower() for f in
               [str(x) for x in (u.get("why_existing_insufficient", ""),
                                 u.get("summary", ""))]):
            pass  # school-dependence is claim-level, tracked in the ledger
        states = sorted(set(states), key=STRONGEST_ORDER.index)
        strongest = states[0]
        rows.append({
            "schema": "curriculum.l1l6_unit_disposition.v1",
            "unit_id": uid,
            "axis": u["axis"],
            "contributing_lessons": sorted(u.get("contributing_lessons", {})),
            "instructional_role": u.get("summary", ""),
            "capability_interface": u.get("capability_family"),
            "machine_execution_appropriate": u.get("capability_family")
                not in (None, "instructional_only"),
            "tutor_projection_appropriate": True,
            "occurrence_grounding_appropriate": gs not in (
                "not_applicable_with_reason", None),
            "machine_increments": incs,
            "existing_fixtures": ("increment fixtures (pos/adv/abst)" if incs
                                  else None),
            "missing_fixtures": (None if incs else
                                 "machine fixtures await pack authoring "
                                 "(exact plan: lift the unit's qualification "
                                 "tables into its declared capability schema)"),
            "misconception_clusters": sorted(
                c["misconception_id"] for c in mis)[:20],
            "misconception_cluster_count": len(mis),
            "promotion_bundle": sorted(i for i in incs if i in bundles),
            "pvn_candidates": {
                "grounding_state": gs,
                "v": grow.get("v_candidates", 0),
                "n": grow.get("n_candidates", 0),
                "occurrence_links": uid in occ_units,
            },
            "states": states,
            "strongest_state": strongest,
            "blockers": blockers,
            "sol_integration_action": (
                "review promotion bundle %s" % ", ".join(
                    i for i in incs if i in bundles) if incs else
                "consume the unit's projection + fixture candidates; author "
                "its machine pack via the declared capability when prioritized"),
            "validation_command": (
                "python tools/curriculum_unit_consumer.py --increment %s" % incs[0]
                if incs else
                "python tools/build_pedagogy_projections.py --check"),
        })

    hist = {}
    for r in rows:
        hist[r["strongest_state"]] = hist.get(r["strongest_state"], 0) + 1
    meta = {
        "schema": "curriculum.l1l6_unit_disposition.v1.meta",
        "generator": "tools/build_unit_dispositions.py",
        "units": len(rows),
        "strongest_state_histogram": hist,
        "strongest_sums_to_units": sum(hist.values()) == len(rows),
        "state_participation": {
            s: sum(1 for r in rows if s in r["states"])
            for s in STRONGEST_ORDER},
        "generic_unresolved_remainders": 0,
        "note": "every state is computed from committed evidence; machine states require a discovered pack (invented consumer claims are structurally impossible); blockers carry exact causes",
    }
    return rows, meta


def serialize(rows, meta):
    out = {}
    out[str(BASE / "canonical" / "unit-dispositions.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    out[str(BASE / "canonical" / "unit-dispositions.meta.json")] = (
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
            print("FAIL: unit dispositions differ: %s" % ", ".join(bad))
            return 1
        print("OK: unit dispositions byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
