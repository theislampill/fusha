#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_learner_feedback — the learner-feedback hint ladder (P2b deliverable D).

Turns one checker diagnostic into a typed Knowledge-Component Violation Record + an abstainable Point -> Teach ->
Bottom-out ladder. The ladder structure is a standard ITS / model-tracing scaffold (first-principles, NOT an external
research citation). Bottom-out is WITHHELD (null) unless gate==auto_safe AND decision_status==resolved AND
right_answer_wrong_reason_marker==false; otherwise the event carries an escalation in `when_not_to_give_answer`. Hints sit
ON TOP of the gates: they never downgrade a gate, resolve a pending diagnostic, or reveal a withheld answer. Every hint
string is authored-original and source-clean (`leak_sot`). See parserplans/general-fusha-grammar-checker-p2b-learning-cefr/003.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import leak_sot  # noqa: E402
from tools import kc_catalog  # noqa: E402
from tools.fusha_check import IRAB_SENSITIVE_ISSUE_CLASSES, GATE_ALIAS, ISSUE_ROUTE, NAWASIKH_FAMILY_KC  # noqa: E402
from tools import fusha_governor as GOV  # noqa: E402

SCHEMA = "fusha/learner-feedback-event@1"
KC_CATALOG_PATH = os.path.join(_REPO, "curriculum", "kc-catalog.json")
_PUBLIC_BOUNDARY = {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                    "public_gloss_lang": "en", "external_source_names_public": False}
_RAWW_CLASSES = {"governor_not_justified", "weak_irab_reasoning"}

# KC-COVERAGE CONTRACT (RM-45): every checker ISSUE_ROUTE class must map to a Knowledge Component (via a KC's
# `diagnostic_classes`) OR carry an explicit, documented no-KC reason here. The escape hatch exists so a purely
# infrastructural class can be recorded as "intentionally not a learner KC" instead of silently uncovered — it is
# NOT a place to park a teachable grammar class. Keep it empty unless a class genuinely has no learner competency.
# The self-test below asserts full coverage; `curriculum/kc-catalog.json` is the single source of truth for the KCs.
NO_KC_REASON = {}


def issue_route_kc_coverage(by_class):
    """Return (covered, uncovered) ISSUE_ROUTE classes. A class is covered when some KC lists it in
    `diagnostic_classes` OR it has an explicit NO_KC_REASON entry. Pure; used by the self-test and callers."""
    covered, uncovered = [], []
    for cls in sorted(ISSUE_ROUTE):
        if cls in by_class or cls in NO_KC_REASON:
            covered.append(cls)
        else:
            uncovered.append(cls)
    return covered, uncovered


_GENERIC_GOVERNOR_KC_ID = "kc-governor-justification"


def load_kc_catalog(path=KC_CATALOG_PATH):
    if os.path.abspath(path) == os.path.abspath(KC_CATALOG_PATH):
        kcs = kc_catalog.load_kc_catalog(_REPO)
    else:
        with open(path, encoding="utf-8") as fh:
            kcs = json.load(fh)
    by_class = {}
    for kc in kcs:
        for cls in kc.get("diagnostic_classes", []):
            by_class.setdefault(cls, kc)
    # PIN (fail-closed): `possible_governor_unresolved` is the ARBITRARY-TEXT checker's generic issue class.
    # It is deliberately shared by kc-governor-justification AND the five nawasikh family KCs (each family's
    # own KC resolves it separately via NAWASIKH_FAMILY_KC / nawasikh_family_events, which never reads
    # `by_class`). The plain `setdefault` loop above is catalog-FILE-ORDER dependent — a reordered or extended
    # catalog could let a family KC "steal" the generic arbitrary-text mapping merely by appearing earlier in
    # the file. Pin the generic mapping explicitly here so catalog order can never change it; fail closed
    # (raise) if the generic KC is ever missing from the catalog, rather than silently falling through to
    # whichever KC file order happened to pick.
    generic_kc = next((kc for kc in kcs if kc.get("kc_id") == _GENERIC_GOVERNOR_KC_ID), None)
    if generic_kc is None:
        raise ValueError("%s missing from %s; possible_governor_unresolved cannot resolve"
                         % (_GENERIC_GOVERNOR_KC_ID, path))
    by_class["possible_governor_unresolved"] = generic_kc
    return kcs, by_class


def _hint(text, references_cause, governor_address=None):
    t = leak_sot.redact(text) if (text and leak_sot.is_leak(text)) else text
    return {"text": t, "references_cause": bool(references_cause), "governor_address": governor_address, "source_clean": True}


def _examples_for(kc, can_bottom):
    """Build the event examples[] from the KC's authored curriculum_error_examples (Train C).

    A `correction`-kind catalog example is included ONLY when the bottom-out answer is itself safe to show
    (can_bottom) — otherwise the example slot would become a bottom-out side channel. An `error_pattern`-kind
    example is always eligible. The emitted shape is the EXISTING example $def (ar/en/public_boundary) —
    `kind` stays a catalog-only field and is never copied onto the event."""
    out = []
    for ex in kc.get("curriculum_error_examples") or []:
        if ex.get("kind") == "correction" and not can_bottom:
            continue
        text = ex.get("en", "")
        if leak_sot.is_leak(text):
            text = leak_sot.redact(text)
        out.append({"en": text, "public_boundary": dict(_PUBLIC_BOUNDARY)})
    return out


def to_feedback_event(diag, by_class, decision_status="pending"):
    """Build a learner-feedback event for one diagnostic, or None if no KC covers its class."""
    cls = diag.get("issue_class")
    kc = by_class.get(cls)
    if kc is None:
        return None
    irab = cls in IRAB_SENSITIVE_ISSUE_CLASSES
    raww = cls in _RAWW_CLASSES
    gate = GATE_ALIAS.get(diag.get("gate"), diag.get("gate"))
    route = diag.get("route") or {}
    # Bottom-out is withheld unless the answer is safe to give.
    can_bottom = (gate == "auto_safe" and decision_status == "resolved" and not raww)
    pending_rule = kc.get("plain_rule") is None
    point = _hint(kc["point_template"], references_cause=irab)
    # Teach references the CAUSE for an iʿrāb-sensitive class (FAIL-LF-5). A pending-rule KC emits Point-equivalent only.
    if pending_rule:
        teach = _hint(kc["point_template"], references_cause=irab)
    else:
        teach = _hint(kc.get("teach_template") or kc["point_template"], references_cause=True)
    bottom_out = _hint(kc.get("bottom_out_template") or "", references_cause=True) if (can_bottom and not pending_rule) else None
    reason = ("a hard-grammar item requires independent review; the answer is withheld"
              if not can_bottom else "the answer is safe to show at this gate")
    return {
        "knowledge_component": kc["kc_id"],
        "diagnostic_class": cls,
        "point_hint": point,
        "teach_hint": teach,
        "bottom_out_hint": bottom_out,
        "drill_route": kc.get("drill_route"),
        "sarf_route": kc.get("sarf_route"),
        "nahw_route": kc.get("nahw_route"),
        "examples": _examples_for(kc, can_bottom),
        "when_not_to_give_answer": {
            "gate": gate, "reason": reason,
            "route_to": {"lane": route.get("lane", "nahw"), "procedure": route.get("procedure", kc.get("nahw_route") or kc.get("sarf_route") or "nahw/procedures/irab-case-mood.md")},
        },
        "decision_status": decision_status,
        "right_answer_wrong_reason_marker": raww,
        "cefr_level_min": kc.get("cefr_band"),
        "public_boundary": dict(_PUBLIC_BOUNDARY),
    }


def build_events(diagnostics, by_class, decision_status="pending"):
    out = []
    for d in diagnostics or []:
        ev = to_feedback_event(d, by_class, decision_status=decision_status)
        if ev is not None:
            out.append(ev)
    return out


# ---------------------------------------------------------------------------
# TRAIN-B/C L2.M2 nawāsikh diagnostic export — the bounded adapter's feedback-path end.
# ---------------------------------------------------------------------------
def nawasikh_family_events(unit, kcs=None):
    """Adapt one CheckUnit's governor lattice into learner-feedback events for the five genuinely-emitted
    nawāsikh families (`tools.fusha_governor.nawasikh_pending_diagnostics`).

    Reuses `to_feedback_event` UNCHANGED for the hint-ladder/gate/bottom-out-withholding logic — the only new
    behaviour here is resolving each diagnostic's `family` to ITS OWN KC (`fusha_check.NAWASIKH_FAMILY_KC`)
    instead of the single generic `possible_governor_unresolved` KC (`kc-governor-justification`) the arbitrary
    checker's `by_class` dict would otherwise return. A diagnostic whose family has no registered KC (inna-family
    modal force) is skipped — never routed through a substitute KC. `kcs`, when given, is a pre-loaded
    `(kcs_list, by_class)` pair from `load_kc_catalog()`; a fresh load is used when omitted."""
    _kcs, _by_class = kcs if kcs is not None else load_kc_catalog()
    kc_by_id = {kc["kc_id"]: kc for kc in _kcs}
    out = []
    for diag in GOV.nawasikh_pending_diagnostics(unit):
        kc_id = NAWASIKH_FAMILY_KC.get(diag["family"])
        if kc_id is None or kc_id not in kc_by_id:
            continue
        ev = to_feedback_event(diag, {diag["issue_class"]: kc_by_id[kc_id]}, decision_status=diag["decision_status"])
        if ev is not None:
            out.append(ev)
    return out


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def _self_test():
    from tools import fusha_text_check as TC  # lazy
    _kcs, by_class = load_kc_catalog()
    failures = []
    # KC-COVERAGE ASSERTION (RM-45): every ISSUE_ROUTE class -> a KC or an explicit no_kc_reason.
    _covered, _uncovered = issue_route_kc_coverage(by_class)
    for cls in _uncovered:
        failures.append("ISSUE_ROUTE class %r has neither a KC (diagnostic_classes) nor an explicit no_kc_reason" % cls)
    inputs = ["وبالكتابِ", "علم نور", "كتابُهم جديدٌ", "من يقرأ", "العِلمُ نور"]
    seen_classes = set()
    for raw in inputs:
        rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": raw})
        events = build_events(rec["diagnostics"], by_class)
        for ev in events:
            seen_classes.add(ev["diagnostic_class"])
            # bottom-out withheld in arbitrary mode (gate != auto_safe)
            if ev["bottom_out_hint"] is not None:
                failures.append("%s: bottom_out leaked past a non-auto_safe gate" % raw)
            if ev["right_answer_wrong_reason_marker"] and ev["bottom_out_hint"] is not None:
                failures.append("%s: bottom_out present for a right-answer-wrong-reason event" % raw)
            # leak-free hint text
            for h in ("point_hint", "teach_hint"):
                if leak_sot.is_leak(ev[h]["text"]):
                    failures.append("%s: %s leaks" % (raw, h))
            for ex in ev["examples"]:
                if leak_sot.is_leak(ex.get("en", "")):
                    failures.append("%s: example leaks" % raw)
            # teach references the cause for iʿrāb-sensitive classes
            if ev["diagnostic_class"] in IRAB_SENSITIVE_ISSUE_CLASSES and not ev["teach_hint"]["references_cause"]:
                failures.append("%s: iʿrāb-sensitive teach does not reference the cause" % raw)
            # routes resolve on disk
            for rk in ("drill_route", "sarf_route", "nahw_route"):
                p = ev.get(rk)
                if p and not os.path.exists(os.path.join(_REPO, p)):
                    failures.append("%s: %s path %r does not resolve" % (raw, rk, p))
            # KC resolves
            if ev["knowledge_component"] not in {k["kc_id"] for k in _kcs}:
                failures.append("%s: KC does not resolve" % raw)
    if not seen_classes:
        failures.append("no learner-feedback events produced across the fixtures")
    # RED-12: bottom-out stays withheld past a non-auto_safe gate WITH examples now present — examples must never
    # become a bottom-out side channel. Re-run over the same fixtures and require at least one non-empty examples[].
    saw_examples = False
    for raw in inputs:
        rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": raw})
        for ev in build_events(rec["diagnostics"], by_class):
            if ev["examples"]:
                saw_examples = True
            if ev["examples"] and ev["bottom_out_hint"] is not None:
                failures.append("%s: bottom_out present alongside non-empty examples (side-channel leak)" % raw)
    if not saw_examples:
        failures.append("RED-12: no fixture produced a non-empty examples[] (curriculum_error_examples not wired)")

    # NAWASIKH-ADAPTER: each of the five genuinely-emitted families reaches its OWN KC, never the generic
    # kc-governor-justification, never resolved, never a bottom-out.
    _naw_units = {
        "kana_laysa_government": {"input_mode": "arbitrary_typing", "frame_kind": "constructed",
                                  "construction_family": "nawasikh", "source_unit": {"address": "", "scope": "arbitrary"},
                                  "tokens": [{"ref": "tok:0", "surface": "x"}],
                                  "features": {"ism_marking": "raf3", "khabar_marking": "nasb", "regime": "kana_family"}},
        "inna_family_government": {"input_mode": "arbitrary_typing", "frame_kind": "constructed",
                                   "construction_family": "nawasikh", "source_unit": {"address": "", "scope": "arbitrary"},
                                   "tokens": [{"ref": "tok:0", "surface": "x"}],
                                   "features": {"ism_marking": "raf3", "khabar_marking": "nasb", "regime": "inna_family"}},
        "continuative_licensing": {"input_mode": "arbitrary_typing", "frame_kind": "constructed",
                                   "construction_family": "nawasikh", "source_unit": {"address": "", "scope": "arbitrary"},
                                   "tokens": [{"ref": "tok:0", "surface": "x"}],
                                   "features": {"polarity_licenser": "absent", "regime": "kana_family_polarity_licensed"}},
        "qalb_verb_transitivity": {"input_mode": "arbitrary_typing", "frame_kind": "constructed",
                                   "construction_family": "nawasikh", "source_unit": {"address": "", "scope": "arbitrary"},
                                   "tokens": [{"ref": "tok:0", "surface": "x"}],
                                   "features": {"regime": "zanna_family", "sense": "literal_perception"}},
        "stacked_governor_scope": {"input_mode": "arbitrary_typing", "frame_kind": "constructed",
                                   "construction_family": "nawasikh", "source_unit": {"address": "", "scope": "arbitrary"},
                                   "tokens": [{"ref": "tok:0", "surface": "x"}],
                                   "features": {"abrogator_count": 2, "bracketing": "ambiguous"}},
    }
    for family, unit in _naw_units.items():
        evs = nawasikh_family_events(unit, kcs=(_kcs, by_class))
        if not evs:
            failures.append("nawasikh-adapter %s: no event produced" % family)
            continue
        for ev in evs:
            if ev["knowledge_component"] != NAWASIKH_FAMILY_KC[family]:
                failures.append("nawasikh-adapter %s: routed to KC %r, expected %r"
                                % (family, ev["knowledge_component"], NAWASIKH_FAMILY_KC[family]))
            if ev["knowledge_component"] == "kc-governor-justification":
                failures.append("nawasikh-adapter %s: fell back to the generic KC instead of its own" % family)
            if ev["bottom_out_hint"] is not None:
                failures.append("nawasikh-adapter %s: bottom_out must never be given (candidate lattice, never a fact)" % family)
            if ev["decision_status"] != "pending":
                failures.append("nawasikh-adapter %s: decision_status must stay pending" % family)
            errs = _validate_nawasikh_event_shape(ev)
            if errs:
                failures.append("nawasikh-adapter %s: %s" % (family, errs))
    # inna-family MODAL FORCE has no KC: an unclassified/unmapped family must be skipped, never substituted.
    if "inna_modal_force" in NAWASIKH_FAMILY_KC:
        failures.append("nawasikh-adapter: inna_modal_force must NOT be registered (no genuinely emitted class)")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_learner_feedback self-test: Point->Teach->Bottom-out; bottom-out withheld past the gate; cause-referencing; routes resolve; source-clean; nawāsikh five-family export routes to its own KC, never the generic one, never a bottom-out")
    return 0 if not failures else 1


def _validate_nawasikh_event_shape(ev):
    """Minimal inline shape check (kept dependency-free of validate_learner_feedback here): an event's gate is
    off the auto_safe tier and its route resolves on disk. Full schema conformance is asserted by
    tools/validate_learner_feedback.py's own self-test, which this module does not import (would cycle)."""
    gate = (ev.get("when_not_to_give_answer") or {}).get("gate")
    if gate not in ("two_vote_required", "human_source_review_required", "never_auto_resolve"):
        return "gate %r must never be auto_safe" % gate
    proc = (ev.get("when_not_to_give_answer") or {}).get("route_to", {}).get("procedure")
    if proc and not os.path.exists(os.path.join(_REPO, proc)):
        return "route_to.procedure %r does not resolve on disk" % proc
    return None


def emit_fixture(path):
    from tools import fusha_text_check as TC  # lazy
    _kcs, by_class = load_kc_catalog()
    rows = []
    for raw in ["وبالكتابِ", "علم نور", "كتابُهم جديدٌ", "من يقرأ"]:
        rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": raw})
        for ev in build_events(rec["diagnostics"], by_class):
            rows.append(ev)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {"schema": SCHEMA, "generator": "tools/fusha_learner_feedback.py --emit-fixture", "count": len(rows),
            "note": "Learner-feedback hint-ladder events (authored arbitrary inputs). Bottom-out withheld past the gate; "
                    "iʿrāb-sensitive teach references the cause; routes resolve; source-clean; dry-run.",
            "row_schema": ["knowledge_component", "diagnostic_class", "point_hint", "teach_hint", "bottom_out_hint",
                           "examples", "when_not_to_give_answer", "decision_status",
                           "right_answer_wrong_reason_marker", "cefr_level_min"]}
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d feedback events -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Learner-feedback hint ladder (abstainable, dry-run).")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    ap.error("need --self-test or --emit-fixture")


if __name__ == "__main__":
    sys.exit(main())
