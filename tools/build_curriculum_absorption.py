#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the full-curriculum absorption ledgers, generated work queues and
readiness report — ENTIRELY from committed artifacts (CI-recomputable; the
private corpus is not needed because the section inventory is committed).

Outputs (curriculum/l1l6/reports/):
  absorption-ledger.jsonl(+meta)   one controlling row per lesson (226)
  section-ledger.jsonl(+meta)      one row per substantive section, closed
                                   class vocabulary, unclassified = 0
  section-completeness.json        the required completeness report
  queues/q-*.jsonl (+meta)         10 deterministic work queues
  full-curriculum-readiness.json   honest-denominator readiness numbers

State ladder (closed): metadata_only < structurally_parsed <
semantically_qualified < unitized < skill_mapped < fixture_mapped <
occurrence_grounded < candidate_fixture_harness_exercised < backpropagated;
plus review_blocked / not_applicable_with_reason.

Honesty rules: a lesson advances ONLY on explicit evidence (a claim citing
it, a unit listing it, a candidate fixture harness covering its increment,
a precise occurrence link). Ordinary tutor behavior is recorded separately
and never promotes lesson knowledge. Domain association alone never advances state — it is
recorded separately. backpropagated is 0 today (no promotion accepted).
Deterministic; stdlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import kc_catalog
import curriculum_closure

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"
RPT = BASE / "reports"
CONSUMER_BINDINGS = BASE / "links" / "consumer-operationalization-bindings.jsonl"

REAL_CONSUMER_STATUSES = frozenset({
    "operationalized_real_consumer",
    "already_operational_consumer_reverified",
})

SARF_DOMAINS = {"script_phonology", "roots_patterns", "derivation",
                "clitics_affixes", "paradigms", "inflection",
                "morphology_general"}
NAHW_DOMAINS = {"case_mood", "particles", "governance", "syntactic_relations",
                "hidden_structure", "ambiguity", "contextual_interpretation"}

STATE_ORDER = ["metadata_only", "structurally_parsed", "semantically_qualified",
               "unitized", "skill_mapped", "fixture_mapped",
               "occurrence_grounded", "candidate_fixture_harness_exercised",
               "backpropagated"]

NEXT_ACTION_BY_STATE = {
    "structurally_parsed": "author qualified claims for this lesson's propositions (queue q-lesson-qualification)",
    "semantically_qualified": "author or extend a semantic unit citing this lesson (queue q-unit-authoring)",
    "unitized": "map the unit to an executable skill surface (crosswalk rows)",
    "skill_mapped": "derive fixtures into the unit's increment (queue q-error-fixtures / q-paradigm-consumer)",
    "fixture_mapped": "ground the unit on exact occurrences (queue q-pvn-grounding)",
    "occurrence_grounded": "exercise the population through the candidate consumer (flywheel runner)",
    "candidate_fixture_harness_exercised": "emit/refresh the promotion bundle for Sol review (queue q-scholar-owner-review)",
    "backpropagated": "complete",
}


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_consumer_bindings():
    """Load explicit lesson/unit-to-consumer evidence without inference."""
    return _jsonl(CONSUMER_BINDINGS) if CONSUMER_BINDINGS.exists() else []


def consumer_operationalization_truth(bindings=None):
    """Partition exact consumer evidence by plane and contribution posture."""
    bindings = load_consumer_bindings() if bindings is None else bindings
    real = [
        row for row in bindings
        if row.get("binding_status") == "explicit"
        and row.get("contribution_status") in REAL_CONSUMER_STATUSES
    ]
    pending = [
        row for row in bindings
        if row.get("binding_status") == "pending_authoring"
        and row.get("contribution_status") == "pending_authoring"
    ]

    def ids_by_plane(rows, key):
        out = {}
        for row in rows:
            out.setdefault(row["consumer_plane"], set()).update(row.get(key, []))
        return {plane: sorted(ids) for plane, ids in sorted(out.items())}

    def binding_ids_by_subject(rows, key):
        out = {}
        for row in rows:
            for subject_id in row.get(key, []):
                out.setdefault(subject_id, set()).add(row["binding_id"])
        return {sid: sorted(ids) for sid, ids in sorted(out.items())}

    new_real = [r for r in real
                if r["contribution_status"] == "operationalized_real_consumer"]
    reverified = [r for r in real if r["contribution_status"] ==
                  "already_operational_consumer_reverified"]
    runtime_item_ids = sorted({item for r in real
                               if r["consumer_plane"] == "tutor_runtime"
                               for item in r.get("runtime_item_ids", [])})
    candidate_drill_ids = sorted({item for r in real
                                  if r["consumer_plane"] == "tutor_runtime"
                                  for item in r.get("candidate_drill_ids", [])})
    real_lesson_ids = sorted({lid for r in real for lid in r.get("lesson_ids", [])})
    return {
        "bindings": bindings,
        "real_bindings": real,
        "pending_bindings": pending,
        "real_consumer_lesson_ids": real_lesson_ids,
        "real_consumer_unit_ids": sorted({uid for r in real
                                           for uid in r.get("unit_ids", [])}),
        "real_binding_ids_by_lesson": binding_ids_by_subject(real, "lesson_ids"),
        "real_binding_ids_by_unit": binding_ids_by_subject(real, "unit_ids"),
        "pending_binding_ids_by_lesson": binding_ids_by_subject(
            pending, "lesson_ids"),
        "pending_binding_ids_by_unit": binding_ids_by_subject(
            pending, "unit_ids"),
        "new_real_unit_ids_by_plane": ids_by_plane(new_real, "unit_ids"),
        "reverified_unit_ids_by_plane": ids_by_plane(reverified, "unit_ids"),
        "pending_unit_ids_by_plane": ids_by_plane(pending, "unit_ids"),
        "real_lesson_ids_by_plane": ids_by_plane(real, "lesson_ids"),
        "pending_lesson_ids_by_plane": ids_by_plane(pending, "lesson_ids"),
        "runtime_item_ids": runtime_item_ids,
        "candidate_drill_ids": candidate_drill_ids,
        "lessons_partially_operationalized": len(real_lesson_ids),
        "lessons_fully_operationalized": 0,
        "lessons_fully_operationalized_basis": "not_yet_computed",
    }


def load():
    quals = []
    qdir = BASE / "qualification"
    if qdir.exists():
        for f in sorted(qdir.glob("L*.jsonl")):
            quals.extend(_jsonl(f))
    lum_p = BASE / "canonical" / "lesson-unit-map.jsonl"
    ctx = {
        "quals": {q["lesson_id"]: q for q in quals},
        "lesson_unit_map": ({r["lesson_id"]: r for r in _jsonl(lum_p)}
                            if lum_p.exists() else {}),
        "lessons": _jsonl(BASE / "registry" / "lessons.jsonl"),
        "sections": _jsonl(BASE / "registry" / "section-inventory.jsonl"),
        "concepts": _jsonl(BASE / "graph" / "concepts.jsonl"),
        "edges": _jsonl(BASE / "graph" / "concept-edges.jsonl"),
        "units": _jsonl(BASE / "units" / "instructional-units.jsonl"),
        "claims": _jsonl(BASE / "ledger" / "claim-ledger.jsonl"),
        "families": _jsonl(BASE / "ledger" / "claim-families.jsonl"),
        "plinks": _jsonl(BASE / "links" / "pvn-precise-links.jsonl"),
        "flinks": _jsonl(BASE / "links" / "pvn-candidate-links.jsonl"),
        "manifest": _jsonl(BASE / "custody" / "source-manifest.jsonl"),
        "misconceptions": _jsonl(
            BASE / "misconceptions" / "misconception-registry.jsonl"),
    }
    return ctx


def ordinary_tutor_runtime_truth(ctx, bindings=None):
    """Derive the ordinary runtime's bounded L1-L6 evidence.

    A drill-key row with a kc_id is behaviorally consumed by the ordinary
    tutor. The KC catalog's explicit curriculum_misconception_ids provide an
    indirect path to lesson manifestations. related_units are deliberately
    ignored: they are candidate routing context, not runtime unit bindings.
    """
    key_rows = []
    for path in sorted((ROOT / "curriculum" / "drills" / "keys").glob("*.jsonl")):
        key_rows.extend(r for r in _jsonl(path) if r.get("kc_id"))
    kc_rows = kc_catalog.load_kc_catalog(ROOT)
    kc_by_id = {r["kc_id"]: r for r in kc_rows}
    emittable_kcs = sorted({r["kc_id"] for r in key_rows})
    missing_kcs = sorted(set(emittable_kcs) - set(kc_by_id))
    if missing_kcs:
        raise ValueError("runtime drill rows cite missing KCs: %s" % missing_kcs)

    misconception_by_id = {
        r["misconception_id"]: r for r in ctx["misconceptions"]
    }
    lesson_kcs = {}
    for kc_id in emittable_kcs:
        for misconception_id in kc_by_id[kc_id].get(
                "curriculum_misconception_ids", []):
            misconception = misconception_by_id.get(misconception_id)
            if misconception is None:
                raise ValueError(
                    "KC %s cites missing misconception %s"
                    % (kc_id, misconception_id)
                )
            for manifestation in misconception.get("manifestations", []):
                lesson_kcs.setdefault(manifestation["lesson_id"], set()).add(kc_id)

    operationalization = consumer_operationalization_truth(bindings)
    tutor_rows = [r for r in operationalization["real_bindings"]
                  if r["consumer_plane"] == "tutor_runtime"]
    explicit_lesson_bindings = {
        lesson_id
        for row in key_rows
        for lesson_id in row.get("lesson_ids", [])
    }
    explicit_lesson_bindings.update(
        lesson_id for row in tutor_rows for lesson_id in row.get("lesson_ids", [])
    )
    explicit_unit_bindings = {
        unit_id
        for row in key_rows
        for unit_id in row.get("unit_ids", [])
    }
    explicit_unit_bindings.update(
        unit_id for row in tutor_rows for unit_id in row.get("unit_ids", [])
    )
    runtime_ids = {row["id"] for row in key_rows}
    bound_runtime_ids = {
        item for row in tutor_rows for item in row.get("runtime_item_ids", [])
    }
    missing_runtime_ids = sorted(bound_runtime_ids - runtime_ids)
    if missing_runtime_ids:
        raise ValueError("consumer bindings cite missing runtime drills: %s" %
                         missing_runtime_ids)
    candidate_rows = {
        row["drill_id"]: row for row in
        _jsonl(BASE / "drills-candidates" / "drill-candidates.jsonl")
    }
    candidate_ids = {
        item for row in tutor_rows for item in row.get("candidate_drill_ids", [])
    }
    missing_candidate_ids = sorted(candidate_ids - set(candidate_rows))
    if missing_candidate_ids:
        raise ValueError("consumer bindings cite missing candidate drills: %s" %
                         missing_candidate_ids)
    promoted_candidate_ids = sorted(
        item for item in candidate_ids
        if candidate_rows[item].get("status") != "candidate_not_runtime_integrated"
    )
    return {
        "drill_key_rows": len(key_rows),
        "emittable_kc_ids": emittable_kcs,
        "emittable_knowledge_components": len(emittable_kcs),
        "indirect_lesson_kcs": {
            lesson_id: sorted(kc_ids)
            for lesson_id, kc_ids in sorted(lesson_kcs.items())
        },
        "indirectly_linked_lessons": len(lesson_kcs),
        "explicit_lesson_ids": sorted(explicit_lesson_bindings),
        "explicit_lesson_bindings": len(explicit_lesson_bindings),
        "explicit_unit_ids": sorted(explicit_unit_bindings),
        "explicit_canonical_unit_bindings": len(explicit_unit_bindings),
        "bound_runtime_item_ids": sorted(bound_runtime_ids),
        "bound_runtime_item_count": len(bound_runtime_ids),
        "candidate_drill_spec_ids": sorted(candidate_ids),
        "candidate_drill_specs_promoted": len(promoted_candidate_ids),
        "lesson_content_fully_operationalized": False,
        "lesson_content_fully_operationalized_basis": "not_yet_computed",
        "binding_note": (
            "runtime behavior is proven by committed drill-key rows plus exact "
            "explicit consumer-binding rows; candidate drill specifications "
            "remain candidate_not_runtime_integrated; related_units never "
            "establish a runtime canonical-unit binding"
        ),
    }


def explicit_other_train_linkage(train_id):
    """Count only closed-form explicit consumer binding rows in the authoritative consumer binding manifest
    (never other, unrelated link files under curriculum/l1l6/links/, e.g. the PVN link files, which carry no
    consumer_train field and would otherwise be globbed and silently no-op)."""
    lesson_ids, unit_ids = set(), set()
    for row in load_consumer_bindings():
        if (row.get("consumer_train") != train_id
                or row.get("binding_status") != "explicit"):
            continue
        lesson_ids.update(row.get("lesson_ids", []))
        unit_ids.update(row.get("unit_ids", []))
    return {
        "explicit_lesson_bindings": len(lesson_ids),
        "explicit_unit_bindings": len(unit_ids),
        "binding_basis": (
            "curriculum/l1l6/links/consumer-operationalization-bindings.jsonl rows with matching "
            "consumer_train and binding_status=explicit"
        ),
    }


def fixture_harnessed_increments():
    """Candidate increments covered by the non-authoritative fixture harness."""
    inc_dir = BASE / "increments"
    return sorted(p.name for p in inc_dir.iterdir() if p.is_dir())


def _campaign_numbers(ctx, ledger, section_rows, completeness):
    """The §13 completion-report numbers, computed, never asserted."""
    can_p = BASE / "canonical" / "canonical-units.jsonl"
    mis_p = BASE / "misconceptions" / "misconception-registry.jsonl"
    cans = _jsonl(can_p) if can_p.exists() else []
    mis = _jsonl(mis_p) if mis_p.exists() else []
    quals = ctx["quals"]
    inspected = sum(1 for q in quals.values() if q.get("inspected"))
    qualified = sum(1 for q in quals.values()
                    if q.get("linguistic_propositions"))
    instructional_only = sum(
        1 for q in quals.values()
        if (q.get("unit_mapping") or {}).get("contribution_kind") == "instructional_only")
    represented = sum(1 for r in ledger
                      if (r.get("qualification") or {}).get("canonical_units")
                      or r["semantic_units_explicit"])
    error_lessons_processed = sum(
        1 for r in ledger
        if r["learner_errors"] == 0 or
        (quals.get(r["lesson_id"], {}).get("common_mistakes")))
    unit_sections = [s for s in section_rows
                     if s["absorption_class"] == "semantic_instructional_unit"]
    return {
        "lessons_semantically_inspected": inspected,
        "lessons_semantically_qualified": qualified,
        "lessons_represented_by_canonical_units": represented,
        "lessons_instructional_only_with_reason": instructional_only,
        "lessons_merely_structurally_parsed": sum(
            1 for r in ledger if r["absorption_state"] == "structurally_parsed"),
        "sections_linked_to_canonical_units": sum(
            1 for s in unit_sections if s["detail"].get("explicitly_unitized")),
        "sections_still_only_domain_classified": sum(
            1 for s in unit_sections if not s["detail"].get("explicitly_unitized"))
            + completeness["candidate_for_cleanroom_authorship"],
        "canonical_units_total": len(cans),
        "canonical_units_sarf": sum(1 for c in cans if c["axis"] == "sarf"),
        "canonical_units_nahw": sum(1 for c in cans if c["axis"] == "nahw"),
        "canonical_units_cross": sum(1 for c in cans if c["axis"] == "cross"),
        "canonical_units_with_machine_pack": sum(
            1 for c in cans if c.get("machine_increments")),
        "misconception_clusters": len(mis),
        "misconception_manifestations": sum(len(m["manifestations"]) for m in mis),
        "error_section_lessons_processed": error_lessons_processed,
        "pack_authoring_remaining": sum(
            1 for c in cans if not c.get("machine_increments")
            and c.get("capability_family") not in (None, "instructional_only")),
        "honesty": "canonical units from the qualification wave are AUTHORED CANDIDATE UNITS (summary, capability family, contributing lessons, two-way map); their machine packs are the bounded remaining executable work, not silent gaps",
    }


def build(ctx, unit_dispositions=None):
    bindings = load_consumer_bindings()
    operationalization = consumer_operationalization_truth(bindings)
    if unit_dispositions is None:
        # Recompute rather than trusting a possibly stale generated ledger.
        # The import is deliberately local: build_unit_dispositions imports
        # this module only for consumer-binding helpers.
        import build_unit_dispositions
        unit_dispositions, _ = build_unit_dispositions.build(bindings=bindings)
    lesson_closure = curriculum_closure.lesson_closure_truth(
        unit_dispositions,
        list(ctx["lesson_unit_map"].values()),
    )
    fully_operationalized_lesson_ids = set(
        lesson_closure["fully_operationalized_lesson_ids"]
    )
    real_consumer_lesson_ids = set(
        operationalization["real_consumer_lesson_ids"]
    )
    operationalization["lessons_fully_operationalized"] = len(
        fully_operationalized_lesson_ids
    )
    operationalization["lessons_partially_operationalized"] = len(
        real_consumer_lesson_ids - fully_operationalized_lesson_ids
    )
    operationalization["lessons_fully_operationalized_basis"] = (
        lesson_closure["basis"]
    )
    runtime_truth = ordinary_tutor_runtime_truth(ctx, bindings=bindings)
    runtime_lesson_kcs = runtime_truth["indirect_lesson_kcs"]
    binding_by_id = {r["binding_id"]: r for r in bindings}
    concepts_by_lesson = {}
    for c in ctx["concepts"]:
        concepts_by_lesson.setdefault(c["lesson_id"], []).append(c)
    revisit_targets = {e["to"] for e in ctx["edges"] if e["kind"] == "concept_revisited"}

    claims_by_lesson = {}
    for c in ctx["claims"]:
        lid = (c.get("source_ref") or {}).get("lesson_id")
        if lid and lid != "corpus-wide":
            claims_by_lesson.setdefault(lid, []).append(c["claim_id"])
    for c in ctx["families"]:
        for lid in (c.get("source_scope") or {}).get("lesson_refs") or []:
            claims_by_lesson.setdefault(lid, []).append(c["claim_id"])

    units_by_lesson = {}
    units_by_domain = {}
    for u in ctx["units"]:
        for lid in u.get("lesson_refs") or []:
            units_by_lesson.setdefault(lid, []).append(u["unit_id"])
        units_by_domain.setdefault(u["concept_node_query"]["domain"], []).append(u["unit_id"])
    unit_index = {u["unit_id"]: u for u in ctx["units"]}

    ran = set(fixture_harnessed_increments())
    unit_occ_links = {}
    for r in ctx["plinks"]:
        if r.get("occurrence_id"):
            unit_occ_links.setdefault(r["unit_ref"], []).append(r["occurrence_id"])

    # ---------------- absorption ledger ----------------
    ledger = []
    for l in sorted(ctx["lessons"], key=lambda r: r["lesson_id"]):
        lid = l["lesson_id"]
        cs = concepts_by_lesson.get(lid, [])
        domains = sorted({c["domain"] for c in cs})
        explicit_units = sorted(units_by_lesson.get(lid, []))
        assoc_units = sorted({u for d in domains for u in units_by_domain.get(d, [])})
        claims = sorted(set(claims_by_lesson.get(lid, [])))
        incs = sorted({unit_index[u]["backprop_destination"].rstrip("/").split("/")[-1]
                       for u in explicit_units
                       if unit_index[u]["backprop_destination"].startswith(
                           "curriculum/l1l6/increments/")})
        occs = sorted({o for u in explicit_units for o in unit_occ_links.get(u, [])})

        qual = ctx["quals"].get(lid)
        lum = ctx["lesson_unit_map"].get(lid)
        canon_units = sorted(lum["units"]) if lum else []
        instructional_only_no_units = bool(
            qual and not canon_units and not units_by_lesson.get(lid)
            and (qual.get("unit_mapping") or {}).get("contribution_kind")
            == "instructional_only")
        state = "structurally_parsed"
        if qual and qual.get("linguistic_propositions"):
            state = "semantically_qualified"
        if instructional_only_no_units:
            state = "not_applicable_with_reason"
        if canon_units or explicit_units:
            state = "unitized"
            if explicit_units or any(u.startswith("u-") for u in canon_units):
                state = "skill_mapped"
            if incs:
                state = "fixture_mapped"
                if occs:
                    state = "occurrence_grounded"
                if set(incs) & ran:
                    state = "candidate_fixture_harness_exercised"

        sarf_dest = sorted({unit_index[u]["skill_surface"] for u in assoc_units
                            if u.startswith("u-s")})
        nahw_dest = sorted({unit_index[u]["skill_surface"] for u in assoc_units
                            if u.startswith("u-n")})
        pvn = ("exact_occurrences" if occs else
               "entry_links" if any(unit_index[u]["unit_id"] in
                                    {r["unit_ref"] for r in ctx["plinks"]}
                                    for u in assoc_units) else
               "family_links" if assoc_units else "no_corpus_bridge")

        real_binding_ids = operationalization[
            "real_binding_ids_by_lesson"].get(lid, [])
        pending_binding_ids = operationalization[
            "pending_binding_ids_by_lesson"].get(lid, [])
        real_planes = sorted({binding_by_id[bid]["consumer_plane"]
                              for bid in real_binding_ids})
        pending_planes = sorted({binding_by_id[bid]["consumer_plane"]
                                 for bid in pending_binding_ids})
        tutor_binding_ids = [bid for bid in real_binding_ids
                             if binding_by_id[bid]["consumer_plane"] ==
                             "tutor_runtime"]

        counts = l["counts"]
        ledger.append({
            "schema": "curriculum.l1l6_absorption_row.v1",
            "lesson_id": lid,
            "level_id": l["level_id"], "module_id": l["module_id"],
            "substantive_sections": {
                "concepts": len(cs),
                "reading_passages": counts["reading_passages"],
                "learner_error_sections": counts["common_mistakes_sections"],
                "quiz_questions": counts["quiz_questions"],
                "vocabulary_rows": counts["vocabulary_table_rows"],
            },
            "instructional_concepts": [c["concept_id"] for c in cs],
            "linguistic_claims": claims,
            "qualification": ({
                "inspected": bool(qual.get("inspected")),
                "propositions": len(qual.get("linguistic_propositions") or []),
                "contribution_kind": (qual.get("unit_mapping") or {}).get("contribution_kind"),
                "canonical_units": canon_units,
            } if qual else None),
            "morphology_topics": sorted(set(domains) & SARF_DOMAINS),
            "syntax_topics": sorted(set(domains) & NAHW_DOMAINS),
            "learner_errors": counts["common_mistakes_sections"],
            "contrasts": sum(1 for c in cs if c["domain"] == "ambiguity"),
            "paradigms": sum(1 for c in cs if c["domain"] == "paradigms"),
            "exercises": {"quiz_questions": counts["quiz_questions"],
                          "material_class": "questions_without_verified_answer_keys"},
            "custody_status": "private_source_custody_metadata_only",
            "semantic_units_explicit": explicit_units,
            "semantic_units_domain_associated": assoc_units,
            "candidate_increments": incs,
            "sarf_destinations": sarf_dest,
            "nahw_destinations": nahw_dest,
            "runtime_tutor_evidence": {
                "indirect_lesson_link": lid in runtime_lesson_kcs,
                "emittable_kc_ids": runtime_lesson_kcs.get(lid, []),
                "explicit_binding_ids": tutor_binding_ids,
                "binding_basis": (
                    "explicit consumer binding"
                    if tutor_binding_ids else
                    "KC curriculum_misconception_ids -> misconception manifestations"
                    if lid in runtime_lesson_kcs else None
                ),
                "lesson_contribution_operationalized": bool(tutor_binding_ids),
                "mapped_unit_closure_reached": (
                    lid in fully_operationalized_lesson_ids
                ),
                "mapped_unit_closure_basis": (
                    lesson_closure["basis"]
                    if lid in fully_operationalized_lesson_ids
                    else "mapped_units_incomplete"
                ),
            },
            "consumer_operationalization": {
                "status": ("fully_operationalized"
                           if lid in fully_operationalized_lesson_ids
                           else "partially_operationalized" if real_binding_ids
                           else "pending_authoring" if pending_binding_ids
                           else "not_operationalized"),
                "real_binding_ids": real_binding_ids,
                "pending_binding_ids": pending_binding_ids,
                "operationalized_planes": real_planes,
                "pending_planes": pending_planes,
                "fully_operationalized": (
                    lid in fully_operationalized_lesson_ids
                ),
                "fully_operationalized_basis": (
                    lesson_closure["basis"]
                    if lid in fully_operationalized_lesson_ids
                    else "mapped_units_incomplete"
                ),
            },
            "tutor_drill_destinations": (
                ["ordinary tutor runtime via emittable KC drill-key rows"]
                if lid in runtime_lesson_kcs or tutor_binding_ids else []),
            "candidate_tutor_drill_destinations": (
                ["candidate drill packets derived from learner-error material"]
                if counts["common_mistakes_sections"] else []) + [
                "curriculum/tutor-runtime-routing.md (candidate method routing)"],
            "pvn_opportunity": pvn,
            "exact_occurrences": occs,
            "unresolved_qualification_work": (
                [] if claims else ["no qualified claim cites this lesson yet"]),
            "blockers": (["quiz keys blocked on TP-CURR-QUIZ-KEY-REVIEW (certifier-class)"]
                         if counts["quiz_questions"] else []),
            "absorption_state": state,
            "next_action": (
                "none required — instructional-method material (no linguistic "
                "unit applicable; reason: %s); routed to the instructional-"
                "methods crosswalk" % (qual.get("instructional_purpose", "")[:80])
                if state == "not_applicable_with_reason"
                else NEXT_ACTION_BY_STATE[state]),
        })

    # ---------------- section ledger ----------------
    covered_domains = set(units_by_domain)
    section_rows = []
    for s in ctx["sections"]:
        kind = s["kind"]
        cls, detail = None, None
        if kind == "concept":
            cid_prefix = "c-%s-" % s["lesson_id"].lower().replace(".", "-")
            heading = s.get("heading", "")
            match = next((c for c in concepts_by_lesson.get(s["lesson_id"], [])
                          if c["heading"] == heading), None)
            domain = match["domain"] if match else None
            lesson_instr_only = (
                (ctx["quals"].get(s["lesson_id"], {}).get("unit_mapping") or
                 {}).get("contribution_kind") == "instructional_only"
                and not ctx["lesson_unit_map"].get(s["lesson_id"], {}).get("units"))
            if lesson_instr_only:
                cls = "excluded_with_reason"
                detail = {"reason": "instructional-method material — the lesson "
                          "is qualified instructional_only with no linguistic "
                          "unit applicable; routed via its qualification record "
                          "to the instructional-methods crosswalk"}
            elif match and match["concept_id"] in revisit_targets:
                cls = "duplicate_revisit"
            elif domain == "paradigms" or "table" in heading.lower():
                cls = "paradigm"
            elif domain == "ambiguity":
                cls = "contrast_set"
            elif domain in covered_domains:
                cls = "semantic_instructional_unit"
                detail = {"unitized_by": units_by_domain[domain],
                          "explicitly_unitized": bool(
                              s["lesson_id"] in {l for u in units_by_domain[domain]
                                                 for l in unit_index[u].get("lesson_refs", [])}
                              or ctx["lesson_unit_map"].get(s["lesson_id"], {}).get("units"))}
            elif ctx["lesson_unit_map"].get(s["lesson_id"], {}).get("units"):
                # the qualification campaign gave this lesson canonical units,
                # so the section has a real semantic destination even though
                # its DOMAIN had no authored-wave unit
                cls = "semantic_instructional_unit"
                detail = {"unitized_by": sorted(
                              ctx["lesson_unit_map"][s["lesson_id"]]["units"]),
                          "explicitly_unitized": True,
                          "via": "qualification_campaign"}
            else:
                cls = "candidate_for_cleanroom_authorship"
                detail = {"uncovered_domain": domain}
        elif kind == "reading_passage":
            cls = "reading_passage_application"
        elif kind == "passage_translation":
            cls = "excluded_with_reason"
            detail = {"reason": "translation prose is private-custody source content; no metadata value beyond the passage row"}
        elif kind == "vocabulary_support":
            cls = "vocabulary_support"
        elif kind in ("quiz_header", "quiz_question"):
            cls = "exercise_source"
        elif kind == "learner_error_section":
            cls = "learner_error_source"
        elif kind == "supporting_example_group":
            cls = "supporting_example_group"
        elif kind == "apparatus":
            cls = "non_linguistic_apparatus"
        row = {"schema": "curriculum.l1l6_section_ledger_row.v1",
               "section_id": s["section_id"], "lesson_id": s["lesson_id"],
               "kind": kind, "absorption_class": cls}
        if detail:
            row["detail"] = detail
        section_rows.append(row)

    hist = {}
    for r in section_rows:
        hist[r["absorption_class"]] = hist.get(r["absorption_class"], 0) + 1
    unit_sections = [r for r in section_rows
                     if r["absorption_class"] == "semantic_instructional_unit"]
    completeness = {
        "schema": "curriculum.l1l6_section_completeness.v1",
        "total_substantive_sections": len(section_rows),
        "class_histogram": hist,
        "unitized": sum(1 for r in unit_sections
                        if r["detail"]["explicitly_unitized"]),
        "mapped_but_not_unitized": sum(1 for r in unit_sections
                                       if not r["detail"]["explicitly_unitized"]),
        "candidate_for_cleanroom_authorship":
            hist.get("candidate_for_cleanroom_authorship", 0),
        "excluded_with_reason": hist.get("excluded_with_reason", 0),
        "unclassified": sum(1 for r in section_rows
                            if r["absorption_class"] is None),
        "honesty_note": "a domain label maps a section to unit machinery; it does NOT mean the section's knowledge is absorbed — absorption is the lesson-state ladder + claims + fixtures",
    }

    # ---------------- queues ----------------
    def qrow(qid, i, source, reason, deps, paths, evidence, consumer,
             canary_pos, canary_adv, abstention, done, unlocks):
        return {"schema": "curriculum.l1l6_queue_row.v1",
                "queue": qid, "row_id": "%s-%04d" % (qid, i),
                "source": source, "reason_selected": reason,
                "dependencies": deps, "permitted_output_paths": paths,
                "evidence_requirement": evidence, "target_consumer": consumer,
                "canaries": {"positive": canary_pos, "adversarial": canary_adv},
                "abstention_requirement": abstention,
                "completion_condition": done, "downstream_unlocks": unlocks}

    queues = {}
    q = queues["q-lesson-qualification"] = []
    for i, row in enumerate(r for r in ledger
                            if r["absorption_state"] == "structurally_parsed"):
        q.append(qrow("q-lesson-qualification", i, row["lesson_id"],
                      "no qualified claim cites this lesson",
                      ["private corpus read (custody boundary)"],
                      ["curriculum/l1l6/ledger/claim-families.jsonl"],
                      "restated original-wording claims with closed statuses",
                      "tools/validate_curriculum_l1l6.py ledger_qualification",
                      "a paradigm-true claim verified against repo authority",
                      "an overgeneralization in the lesson detected and guarded",
                      "uncertain propositions -> analysis-dependent/pending, never resolved",
                      "lesson state advances to semantically_qualified",
                      ["q-unit-authoring row for the lesson's domain cluster"]))
    q = queues["q-unit-authoring"] = []
    uncovered = {}
    for r in section_rows:
        if r["absorption_class"] == "candidate_for_cleanroom_authorship":
            d = r["detail"]["uncovered_domain"]
            uncovered.setdefault(d, []).append(r["lesson_id"])
    for i, (d, lids) in enumerate(sorted(uncovered.items())):
        q.append(qrow("q-unit-authoring", i, "domain:%s (%d sections)" % (d, len(lids)),
                      "concept domain has no semantic unit",
                      ["clean-room authorship (no lesson prose)"],
                      ["curriculum/l1l6/units/instructional-units.jsonl",
                       "curriculum/l1l6/units/unit-dependencies.jsonl"],
                      "unit fields complete per curriculum.l1l6_instructional_unit schema",
                      "tools/validate_curriculum_l1l6.py units_semantic",
                      "unit recognition criteria decide a standard example",
                      "unit guards reject an og-2 style overgeneralization",
                      "content without evidence stays candidate; abstention conditions declared",
                      "domain covered; affected sections reclassify as semantic_instructional_unit",
                      ["q-sarf-backprop or q-nahw-backprop rows for the new unit"]))
    for axis in ("sarf", "nahw"):
        qid = "q-%s-backprop" % axis
        q = queues[qid] = []
        i = 0
        for u in ctx["units"]:
            if not u["unit_id"].startswith("u-s" if axis == "sarf" else "u-n"):
                continue
            q.append(qrow(qid, i, u["unit_id"],
                          "unit knowledge must reach the %s skill plane" % axis,
                          ["Sol review", "owner adjudication for rule-registry entry"],
                          ["curriculum/l1l6/promotion/"],
                          "promotion bundle complete (reference, procedure, ladder, pack, fixtures, occurrences)",
                          u["skill_surface"],
                          "positive fixtures pass in the candidate consumer",
                          "adversarial fixtures pass (incl. wrong-reason where iʿrāb-bearing)",
                          "abstention fixtures preserved; no candidate->certified auto-promotion",
                          "bundle emitted under curriculum/l1l6/promotion/ and referenced by the review queue",
                          ["skill-registry candidate rows (Sol-owned step)"]))
            i += 1
    q = queues["q-error-fixtures"] = []
    for i, row in enumerate(r for r in ledger if r["learner_errors"] > 0):
        q.append(qrow("q-error-fixtures", i, row["lesson_id"],
                      "%d learner-error sections await restatement" % row["learner_errors"],
                      ["private corpus read", "TP-CURR-MISTAKES-TO-FIXTURES discipline"],
                      ["curriculum/l1l6/reports/mistake-pattern-fixtures.jsonl"],
                      "original-wording restatement; independently selected words",
                      "target eval family by dominant domain: %s" %
                      (row["morphology_topics"] + row["syntax_topics"] or ["general"])[0],
                      "restated wrong/right pair discriminates",
                      "og-2 surface-generalized fixture rejected at authoring",
                      "patterns without clear repo target recorded as capability gaps",
                      "fixtures emitted + target family named",
                      ["adversarial rows for the relevant increment"]))
    q = queues["q-paradigm-consumer"] = []
    for i, row in enumerate(r for r in ledger if r["paradigms"] > 0):
        q.append(qrow("q-paradigm-consumer", i, row["lesson_id"],
                      "%d paradigm sections map to generative machinery" % row["paradigms"],
                      ["the consumed paradigm store (crosswalk row xs-03)"],
                      ["curriculum/l1l6/reports/"],
                      "paradigm slots cross-checked against tools/fusha_paradigm_generate.py output",
                      "tools/fusha_paradigm_generate.py",
                      "a generated slot matches the curriculum-staged paradigm",
                      "a curriculum simplification contradicting the store is flagged",
                      "unverifiable slots abstain",
                      "cross-check report emitted",
                      ["fixture rows for divergences"]))
    q = queues["q-pvn-grounding"] = []
    i = 0
    for row in ledger:
        if row["pvn_opportunity"] in ("family_links", "entry_links"):
            q.append(qrow("q-pvn-grounding", i, row["lesson_id"],
                          "lesson has %s but no exact occurrence link" % row["pvn_opportunity"],
                          ["per-occurrence evidence (never surface similarity)",
                           "tools/build_curriculum_occurrence_bridge.py interface"],
                          ["curriculum/l1l6/links/pvn-precise-links.jsonl (via builder plan)"],
                          "occurrence-level evidence rows; iʿrāb-bearing facts two-vote gated",
                          "tools/build_curriculum_pvn_links.py",
                          "an exact occurrence with committed authority links cleanly",
                          "a surface-similarity link candidate is REJECTED",
                          "no authority -> stays family-level with reason",
                          "lesson pvn_opportunity becomes exact_occurrences",
                          ["q-hover-pedagogy rows for the grounded entries"]))
            i += 1
    q = queues["q-hover-pedagogy"] = []
    for i, r in enumerate([r for r in ctx["plinks"] if r["link_class"] == "entry"]):
        q.append(qrow("q-hover-pedagogy", i, r["source_key"],
                      "entry linked to unit %s awaits hover-pedagogy material" % r["unit_ref"],
                      ["reviewed unit content", "existing hover projection plane (Sol)"],
                      ["curriculum/l1l6/reports/particle-function-inventory.jsonl"],
                      "hover fields from the increment's declared set only",
                      r["increment"],
                      "hover component teaches the discriminator, not just the label",
                      "a bare-label hover (no reason) is rejected",
                      r["ambiguity_abstention"],
                      "pedagogy rows emitted for the entry",
                      ["website-projection candidates (owner-gated deploy plane)"]))
    q = queues["q-tutor-adoption"] = []
    for i, m in enumerate(["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]):
        q.append(qrow("q-tutor-adoption", i, "instructional-methods.md#%s" % m,
                      "extracted method awaiting gate-wrapped tutor routing",
                      ["TP-CURR-TUTOR-METHOD-ROUTING packet"],
                      ["curriculum/l1l6/reports/tutor-method-routing.jsonl"],
                      "every routed answer path carries the gate ladder",
                      "curriculum/tutor-runtime-routing.md surfaces (integration note, not edit)",
                      "method routes with gate_wrap intact",
                      "a route that would bypass validate_linguistic_decisions is rejected",
                      "hints never downgrade a gate",
                      "method routed or explicitly deferred",
                      ["learner-session KC records"]))
    q = queues["q-scholar-owner-review"] = []
    i = 0
    for c in ctx["families"]:
        if c["status"] in ("school-dependent", "analysis-dependent"):
            q.append(qrow("q-scholar-owner-review", i, c["claim_id"],
                          "status %s requires attributed review, never a vote" % c["status"],
                          ["scholar/arbitration routing (docs/blockers.yaml discipline)"],
                          ["curriculum/l1l6/ledger/claim-families.jsonl (status only)"],
                          "documented school positions with attribution",
                          "human review lane",
                          "alternatives recorded with attribution",
                          "an unattributed resolution attempt is rejected",
                          "never resolved by preference; stays attributed if genuine",
                          "claim carries reviewed attribution record",
                          ["dependent unit/fixture refinements"]))
            i += 1
    for inc in sorted(fixture_harnessed_increments()):
        q.append(qrow("q-scholar-owner-review", i, "increment:%s" % inc,
                      "candidate increment awaits promotion review",
                      ["promotion bundle", "Sol review", "owner adjudication"],
                      ["curriculum/l1l6/promotion/"],
                      "bundle complete; regression command green",
                      "tools/curriculum_unit_consumer.py",
                      "bundle's positive fixtures green",
                      "bundle's adversarial fixtures green",
                      "no auto-promotion; rollback condition recorded",
                      "owner decision recorded",
                      ["skill-registry candidate rows"]))
        i += 1

    # ---------------- readiness report ----------------
    st = {}
    for r in ledger:
        st[r["absorption_state"]] = st.get(r["absorption_state"], 0) + 1
    level_denominators = {}
    for row in ledger:
        level_denominators[row["level_id"]] = (
            level_denominators.get(row["level_id"], 0) + 1
        )
    drill_meta = json.loads(
        (BASE / "drills-candidates" / "drill-candidates.meta.json")
        .read_text(encoding="utf-8")
    )
    readiness = {
        "schema": "curriculum.l1l6_full_readiness.v1",
        "source_lessons": len(ledger),
        "lessons_fully_accounted": len(ledger),
        "substantive_sections_classified": {
            "classified": len(section_rows) - completeness["unclassified"],
            "total": len(section_rows)},
        "semantic_units_authored": len(ctx["units"]),
        "lessons_covered_by_authored_units": {
            "explicit_lesson_refs": sum(1 for r in ledger if r["semantic_units_explicit"]),
            "domain_associated_only": sum(1 for r in ledger
                                          if not r["semantic_units_explicit"]
                                          and r["semantic_units_domain_associated"])},
        "lessons_mapped_to_sarf": sum(1 for r in ledger if r["sarf_destinations"]),
        "lessons_mapped_to_nahw": sum(1 for r in ledger if r["nahw_destinations"]),
        "lesson_denominators_by_level": dict(sorted(level_denominators.items())),
        "lessons_mapped_to_tutor_drills": runtime_truth[
            "explicit_lesson_bindings"],
        "lessons_partially_operationalized": operationalization[
            "lessons_partially_operationalized"],
        "lessons_fully_operationalized": operationalization[
            "lessons_fully_operationalized"],
        "lessons_fully_operationalized_basis": operationalization[
            "lessons_fully_operationalized_basis"],
        "canonical_units_with_real_consumers": len(
            operationalization["real_consumer_unit_ids"]),
        "consumer_operationalization": {
            "new_real_unit_ids_by_plane": operationalization[
                "new_real_unit_ids_by_plane"],
            "reverified_unit_ids_by_plane": operationalization[
                "reverified_unit_ids_by_plane"],
            "pending_unit_ids_by_plane": operationalization[
                "pending_unit_ids_by_plane"],
            "real_lesson_ids_by_plane": operationalization[
                "real_lesson_ids_by_plane"],
            "pending_lesson_ids_by_plane": operationalization[
                "pending_lesson_ids_by_plane"],
        },
        "lessons_indirectly_linked_to_runtime_tutor_drills": runtime_truth[
            "indirectly_linked_lessons"],
        "ordinary_tutor_runtime": {
            "drill_key_rows": runtime_truth["drill_key_rows"],
            "emittable_knowledge_components": runtime_truth[
                "emittable_knowledge_components"],
            "emittable_kc_ids": runtime_truth["emittable_kc_ids"],
            "indirectly_linked_lessons": runtime_truth[
                "indirectly_linked_lessons"],
            "explicit_lesson_bindings": runtime_truth[
                "explicit_lesson_bindings"],
            "explicit_canonical_unit_bindings": runtime_truth[
                "explicit_canonical_unit_bindings"],
            "bound_runtime_item_ids": runtime_truth[
                "bound_runtime_item_ids"],
            "bound_runtime_item_count": runtime_truth[
                "bound_runtime_item_count"],
            "candidate_drill_spec_ids": runtime_truth[
                "candidate_drill_spec_ids"],
            "candidate_drill_specs_promoted": runtime_truth[
                "candidate_drill_specs_promoted"],
            "lesson_content_fully_operationalized": runtime_truth[
                "lesson_content_fully_operationalized"],
            "lesson_content_fully_operationalized_basis": runtime_truth[
                "lesson_content_fully_operationalized_basis"],
            "binding_note": runtime_truth["binding_note"],
        },
        "candidate_drill_packets": {
            "rows": drill_meta["rows"],
            "runtime_integrated": drill_meta["runtime_integrated"],
            "status": "candidate_not_runtime_integrated",
        },
        "other_train_l1l6_linkage": {
            "train_b": explicit_other_train_linkage("train_b"),
            "train_c": explicit_other_train_linkage("train_c"),
            "train_d": explicit_other_train_linkage("train_d"),
            "train_e": explicit_other_train_linkage("train_e"),
        },
        "lessons_with_exact_pvn_links": sum(1 for r in ledger
                                            if r["pvn_opportunity"] == "exact_occurrences"),
        "lessons_with_entry_level_links": sum(1 for r in ledger
                                              if r["pvn_opportunity"] == "entry_links"),
        "lessons_with_family_only_links": sum(1 for r in ledger
                                              if r["pvn_opportunity"] == "family_links"),
        "lessons_with_no_corpus_bridge": sum(1 for r in ledger
                                             if r["pvn_opportunity"] == "no_corpus_bridge"),
        "state_histogram": st,
        "campaign_13": _campaign_numbers(ctx, ledger, section_rows, completeness),
        "queues": {k: len(v) for k, v in sorted(queues.items())},
        "separation_note": (
            "lesson METADATA coverage is %d/%d; semantic KNOWLEDGE coverage "
            "is the claims+units numbers; CAPABILITY fixture-harness coverage "
            "is candidate evidence; ordinary tutor CONSUMER coverage is %d "
            "runtime key rows across %d emittable KCs with %d indirect lesson "
            "links and %d explicit canonical-unit bindings; the %d candidate "
            "drill packets remain runtime_integrated=%d; OCCURRENCE coverage "
            "is the exact-link lessons — these denominators are never merged"
            % (len(ledger), len(ledger), runtime_truth["drill_key_rows"],
               runtime_truth["emittable_knowledge_components"],
               runtime_truth["indirectly_linked_lessons"],
               runtime_truth["explicit_canonical_unit_bindings"],
               drill_meta["rows"], drill_meta["runtime_integrated"])
        ),
    }
    return ledger, section_rows, completeness, queues, readiness


def serialize(ledger, section_rows, completeness, queues, readiness):
    out = {}

    def jl(path, rows):
        out[str(path)] = "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
        ).encode("utf-8")

    def jo(path, obj):
        out[str(path)] = (json.dumps(obj, ensure_ascii=False, indent=2,
                                     sort_keys=True) + "\n").encode("utf-8")

    jl(RPT / "absorption-ledger.jsonl", ledger)
    jo(RPT / "absorption-ledger.meta.json", {
        "schema": "curriculum.l1l6_absorption_row.v1.meta",
        "generator": "tools/build_curriculum_absorption.py",
        "rows": len(ledger),
        "state_histogram": readiness["state_histogram"]})
    jl(RPT / "section-ledger.jsonl", section_rows)
    jo(RPT / "section-ledger.meta.json", {
        "schema": "curriculum.l1l6_section_ledger_row.v1.meta",
        "generator": "tools/build_curriculum_absorption.py",
        "rows": len(section_rows),
        "class_histogram": completeness["class_histogram"]})
    jo(RPT / "section-completeness.json", completeness)
    for qid, rows in sorted(queues.items()):
        jl(RPT / "queues" / ("%s.jsonl" % qid), rows)
    jo(RPT / "queues" / "queues.meta.json", {
        "schema": "curriculum.l1l6_queue_row.v1.meta",
        "generator": "tools/build_curriculum_absorption.py",
        "queues": {k: len(v) for k, v in sorted(queues.items())}})
    jo(RPT / "full-curriculum-readiness.json", readiness)
    return out


def main(argv):
    check = "--check" in argv
    (RPT / "queues").mkdir(parents=True, exist_ok=True)
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
            print("FAIL: absorption artifacts differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: absorption artifacts byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
