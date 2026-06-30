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
from tools.fusha_check import IRAB_SENSITIVE_ISSUE_CLASSES, GATE_ALIAS  # noqa: E402

SCHEMA = "fusha/learner-feedback-event@1"
KC_CATALOG_PATH = os.path.join(_REPO, "curriculum", "kc-catalog.json")
_PUBLIC_BOUNDARY = {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                    "public_gloss_lang": "en", "external_source_names_public": False}
_RAWW_CLASSES = {"governor_not_justified", "weak_irab_reasoning"}


def load_kc_catalog(path=KC_CATALOG_PATH):
    kcs = json.load(open(path, encoding="utf-8"))
    by_class = {}
    for kc in kcs:
        for cls in kc.get("diagnostic_classes", []):
            by_class.setdefault(cls, kc)
    return kcs, by_class


def _hint(text, references_cause, governor_address=None):
    t = leak_sot.redact(text) if (text and leak_sot.is_leak(text)) else text
    return {"text": t, "references_cause": bool(references_cause), "governor_address": governor_address, "source_clean": True}


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
        "examples": [],
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
# self-test
# ---------------------------------------------------------------------------
def _self_test():
    from tools import fusha_text_check as TC  # lazy
    _kcs, by_class = load_kc_catalog()
    failures = []
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
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_learner_feedback self-test: Point->Teach->Bottom-out; bottom-out withheld past the gate; cause-referencing; routes resolve; source-clean")
    return 0 if not failures else 1


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
                           "when_not_to_give_answer", "decision_status", "right_answer_wrong_reason_marker", "cefr_level_min"]}
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
