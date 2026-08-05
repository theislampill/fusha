#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the 166-unit OPERATIONAL-DISPOSITION ledger — the freeze artifact.

Every canonical unit ends in one or more CLOSED states, with a single
strongest_state; the strongest-state totals sum to exactly the unit count.
States are COMPUTED from committed evidence (packs, projections, grounding,
misconception bindings, bundles, loops) — never asserted. Candidate/readiness
states remain separate from exact real-consumer bindings, which are recorded
per consumer plane and never promote linguistic certification:

  candidate_pack_harnessed     a discovered machine pack exists and the
                               NON-AUTHORITATIVE fixture harness decides its
                               fixtures (development evidence only)
  candidate_occurrence_witnesses  canonical-surface-verified same-entry
                               selected witnesses, or committed occurrence
                               links (card_display_only never counts)
  promotion_bundle_prepared    a Sol-reviewable bundle exists for its
                               increment (nothing applied automatically)
  fixture_source_candidate     bound misconception fixture-candidates exist
  candidate_remediation_material  bound remediation projections exist
  candidate_presentation_template  its unit projection compiled through the
                               presentation-template contract (not tutor-
                               consumed)
  instructional_only_candidate_presentation  declared instructional-only AND
                               carries a candidate presentation template
  evidence_blocked / scholar_review_blocked / owner_adjudication_blocked /
  sol_integration_blocked      dimension blockers, named exactly

Output: curriculum/l1l6/canonical/unit-dispositions.jsonl (+ meta).
Gates (enforced by the validator): N/N dispositioned, 0 generic remainders,
0 invented consumer claims (machine states require a discovered pack), 0
blockers without exact cause.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import build_curriculum_absorption as absorption
import curriculum_closure as closure

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

STRONGEST_ORDER = [
    "candidate_pack_harnessed", "candidate_occurrence_witnesses",
    "promotion_bundle_prepared", "fixture_source_candidate",
    "candidate_remediation_material", "candidate_presentation_template",
    "instructional_only_candidate_presentation",
    "sol_integration_blocked", "scholar_review_blocked",
    "owner_adjudication_blocked", "evidence_blocked",
]


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def build(bindings=None):
    bindings = (absorption.load_consumer_bindings()
                if bindings is None else bindings)
    consumer_truth = absorption.consumer_operationalization_truth(bindings)
    real_rows_by_unit = {}
    pending_rows_by_unit = {}
    for binding in consumer_truth["real_bindings"]:
        for unit_id in binding.get("unit_ids", []):
            real_rows_by_unit.setdefault(unit_id, []).append(binding)
    for binding in consumer_truth["pending_bindings"]:
        for unit_id in binding.get("unit_ids", []):
            pending_rows_by_unit.setdefault(unit_id, []).append(binding)
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
        real_consumers = real_rows_by_unit.get(uid, [])
        pending_consumers = pending_rows_by_unit.get(uid, [])
        states, blockers = [], []
        if incs:
            states.append("candidate_pack_harnessed")
        if (grow.get("grounding_state") == "exact_vn_candidates"
                and any(w.get("canonical_surface_verified")
                        for x in grow.get("resolved", [])
                        for w in x.get("selected_witnesses", []))
                ) or uid in occ_units:
            # card_display_only witnesses never count: the state claims a
            # CANONICAL occurrence witness (Sol fix-request round 2)
            states.append("candidate_occurrence_witnesses")
        if any(i in bundles for i in incs):
            states.append("promotion_bundle_prepared")
        if any(c["disposition"] == "candidate_fixture" for c in mis):
            states.append("fixture_source_candidate")
        if any(c["disposition"] == "instructional_only" for c in mis):
            states.append("candidate_remediation_material")
        if proj and proj["result"]["decision"] == "candidate_projected":
            states.append("candidate_presentation_template")
            if u.get("capability_family") == "instructional_only":
                states.append("instructional_only_candidate_presentation")
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
            "real_consumer_bindings": [{
                "binding_id": binding["binding_id"],
                "consumer_paths": binding["consumer_paths"],
                "consumer_plane": binding["consumer_plane"],
                "consumer_train": binding["consumer_train"],
                "contribution_status": binding["contribution_status"],
                "test_paths": binding["test_paths"],
            } for binding in sorted(real_consumers,
                                    key=lambda r: r["binding_id"])],
            "pending_consumer_bindings": [{
                "binding_id": binding["binding_id"],
                "consumer_plane": binding["consumer_plane"],
                "consumer_train": binding["consumer_train"],
                "contribution_status": binding["contribution_status"],
                "proposed_destination_paths": binding.get(
                    "proposed_destination_paths", []),
            } for binding in sorted(pending_consumers,
                                    key=lambda r: r["binding_id"])],
            "operationalized_planes": sorted({
                binding["consumer_plane"] for binding in real_consumers}),
            "pending_consumer_planes": sorted({
                binding["consumer_plane"] for binding in pending_consumers}),
            "fully_operationalized": False,
            "fully_operationalized_basis": "not_yet_computed",
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

    closure_report = closure.build(rows)
    closure_by_unit = {
        row["unit_id"]: row for row in closure_report["units"]
    }
    for row in rows:
        result = closure_by_unit.get(row["unit_id"])
        if result is None:
            continue
        row["fully_operationalized"] = result["fully_operationalized"]
        row["fully_operationalized_basis"] = result[
            "fully_operationalized_basis"
        ]
        row["occurrence_grounding_parked"] = result[
            "occurrence_grounding_parked"
        ]
        row["satisfied_vacuously_dimension_ids"] = result[
            "satisfied_vacuously_dimension_ids"
        ]
        row["closure_dimensions"] = result["dimensions"]
        row["incomplete_closure_dimensions"] = result[
            "incomplete_dimensions"
        ]

    lesson_closure = closure.lesson_closure_truth(rows)
    fully_closed_lessons = set(
        lesson_closure["fully_operationalized_lesson_ids"]
    )
    real_consumer_lessons = set(
        consumer_truth["real_consumer_lesson_ids"]
    )

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
        "explicit_runtime_unit_bindings": len(set(
            consumer_truth["new_real_unit_ids_by_plane"].get(
                "tutor_runtime", [])
            + consumer_truth["reverified_unit_ids_by_plane"].get(
                "tutor_runtime", []))),
        "explicit_analytical_unit_bindings": len(set(
            consumer_truth["new_real_unit_ids_by_plane"].get(
                "nahw_analytical", [])
            + consumer_truth["reverified_unit_ids_by_plane"].get(
                "nahw_analytical", []))),
        "new_real_consumer_unit_bindings": sum(
            len(ids) for ids in
            consumer_truth["new_real_unit_ids_by_plane"].values()),
        "reverified_consumer_unit_bindings": sum(
            len(ids) for ids in
            consumer_truth["reverified_unit_ids_by_plane"].values()),
        "pending_authoring_unit_bindings": sum(
            len(ids) for ids in
            consumer_truth["pending_unit_ids_by_plane"].values()),
        "units_fully_operationalized": closure_report[
            "units_fully_operationalized"
        ],
        "units_closed_with_parked_occurrence_grounding": closure_report[
            "units_closed_with_parked_occurrence_grounding"
        ],
        "units_closed_with_vacuous_dimensions": closure_report[
            "units_closed_with_vacuous_dimensions"
        ],
        "unit_ids_closed_with_vacuous_dimensions": closure_report[
            "unit_ids_closed_with_vacuous_dimensions"
        ],
        "units_partially_operationalized": sum(
            1
            for row in closure_report["units"]
            if not row["fully_operationalized"]
            and bool(row["dimensions"])
        ),
        "lessons_partially_operationalized": len(
            real_consumer_lessons - fully_closed_lessons
        ),
        "lessons_fully_operationalized": len(fully_closed_lessons),
        "lessons_fully_operationalized_basis": lesson_closure["basis"],
        "note": "candidate readiness states remain separate from exact plane-specific consumer bindings; no binding certifies a linguistic fact or marks a whole lesson operationalized",
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
