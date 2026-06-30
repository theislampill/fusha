#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_learner_feedback — conformance gate for learner-feedback hint-ladder events (P2b deliverable D).

Validates each event against qamus/schemas/learner-feedback-event.schema.json, then the FAIL-LF conditions:

  LF-1  bottom_out_hint populated while when_not_to_give_answer.gate != auto_safe (Bottom-out leaked past a gate).
  LF-2  bottom_out_hint populated while decision_status==pending OR right_answer_wrong_reason_marker==true.
  LF-3  any point/teach/bottom_out text, or any examples[].en, trips leak_sot.scan() (public-boundary tripwire).
  LF-4  drill_route / sarf_route / nahw_route does not resolve on disk (procedure-existence gate).
  LF-5  teach_hint.references_cause==false for an iʿrāb-sensitive diagnostic_class (Teach must point at the cause).
  LF-6  a gate value not on the canonical 4-tier.
  LF-7  knowledge_component does not resolve to a KC in curriculum/kc-catalog.json.
  LF-8  an examples[] entry whose public_boundary is not source-clean.
  LF-9  diagnostic_class not in the closed fusha-text-check diagnostic set (no invented classes).
  LF-10 iʿrāb metalanguage in a hint whose cefr_level_min is a beginner band (guards 'C2 terminology on A1').

CLI: python3 tools/validate_learner_feedback.py [events.jsonl] | --self-test. Stdlib only; exit non-zero on any violation.
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools.validate_linguistic_decisions import validate_schema  # noqa: E402
from tools import leak_sot  # noqa: E402
from tools.fusha_check import IRAB_SENSITIVE_ISSUE_CLASSES  # noqa: E402
from tools import fusha_learner_feedback as LF  # noqa: E402

_EVENT_SCHEMA = json.load(open(os.path.join(_REPO, "qamus", "schemas", "learner-feedback-event.schema.json"), encoding="utf-8"))
_HINT_SCHEMA = _EVENT_SCHEMA["$defs"]["hint"]
_TC_SCHEMA = json.load(open(os.path.join(_REPO, "qamus", "schemas", "fusha-text-check.schema.json"), encoding="utf-8"))
_DIAG_CLASSES = set(_TC_SCHEMA["$defs"]["diagnostic"]["properties"]["issue_class"]["enum"])
_GATES = {"auto_safe", "two_vote_required", "human_source_review_required", "never_auto_resolve"}
_BEGINNER = {"pre_A1", "A1", "A2"}
# iʿrāb metalanguage that must not surface at a beginner band
_IRAB_META_RE = re.compile(r"\biʿr[aā]b\b|\birab\b|\bgovern(or|ing)\b|ʿāmil|\bmajr[uū]r\b|\bmarf[uū]ʿ?\b|\bman[sṣ][uū]b\b"
                           r"|\bcase ending\b|\bjussive\b|\bgenitive\b|\bnominative\b|\baccusative\b|\bf[aā]ʿil\b", re.I)
_KC_IDS = {k["kc_id"] for k in LF.load_kc_catalog()[0]}


def _hints(ev):
    yield "point_hint", ev.get("point_hint")
    yield "teach_hint", ev.get("teach_hint")
    if ev.get("bottom_out_hint") is not None:
        yield "bottom_out_hint", ev.get("bottom_out_hint")


def validate_event(ev):
    errors = []
    cls = ev.get("diagnostic_class", "?")
    for e in validate_schema(ev, _EVENT_SCHEMA):
        errors.append(("schema", "%s: %s" % (cls, e)))
    # explicit hint subobject validation (the schema reaches them via $ref/oneOf the mini-validator does not resolve)
    for label, h in _hints(ev):
        if isinstance(h, dict):
            for e in validate_schema(h, _HINT_SCHEMA):
                errors.append(("schema", "%s.%s: %s" % (cls, label, e)))
    wn = ev.get("when_not_to_give_answer") or {}
    gate = wn.get("gate")
    bottom = ev.get("bottom_out_hint")
    # LF-1
    if bottom is not None and gate != "auto_safe":
        errors.append(("LF-1", "%s: bottom_out present while gate=%r != auto_safe" % (cls, gate)))
    # LF-2
    if bottom is not None and (ev.get("decision_status") == "pending" or ev.get("right_answer_wrong_reason_marker")):
        errors.append(("LF-2", "%s: bottom_out present while pending / right-answer-wrong-reason" % cls))
    # LF-3
    for label, h in _hints(ev):
        if isinstance(h, dict) and leak_sot.is_leak(h.get("text") or ""):
            errors.append(("LF-3", "%s.%s leaks" % (cls, label)))
    for ex in ev.get("examples") or []:
        if leak_sot.is_leak(ex.get("en") or ""):
            errors.append(("LF-3", "%s: example.en leaks" % cls))
    # LF-4
    for rk in ("drill_route", "sarf_route", "nahw_route"):
        p = ev.get(rk)
        if p and not os.path.exists(os.path.join(_REPO, p)):
            errors.append(("LF-4", "%s: %s %r does not resolve on disk" % (cls, rk, p)))
    # LF-5
    if cls in IRAB_SENSITIVE_ISSUE_CLASSES and not (ev.get("teach_hint") or {}).get("references_cause"):
        errors.append(("LF-5", "%s: iʿrāb-sensitive teach does not reference the cause" % cls))
    # LF-6
    if gate not in _GATES:
        errors.append(("LF-6", "%s: gate %r off the 4-tier" % (cls, gate)))
    # LF-7
    if ev.get("knowledge_component") not in _KC_IDS:
        errors.append(("LF-7", "%s: knowledge_component %r does not resolve to a KC" % (cls, ev.get("knowledge_component"))))
    # LF-8
    for ex in ev.get("examples") or []:
        pb = ex.get("public_boundary") or {}
        if pb.get("external_source_names_public") is not False or pb.get("public_gloss_src") != "qamus":
            errors.append(("LF-8", "%s: example public_boundary not source-clean" % cls))
    # LF-9
    if cls not in _DIAG_CLASSES:
        errors.append(("LF-9", "%s: diagnostic_class not in the closed set" % cls))
    # LF-10
    if ev.get("cefr_level_min") in _BEGINNER:
        for label, h in _hints(ev):
            if isinstance(h, dict) and _IRAB_META_RE.search(h.get("text") or ""):
                errors.append(("LF-10", "%s.%s exposes iʿrāb metalanguage at a beginner band" % (cls, label)))
    return errors


def validate_file(path):
    n, errs = 0, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            errs.extend(validate_event(json.loads(line)))
    return n, errs


def _good_event():
    from tools import fusha_text_check as TC
    _kcs, by_class = LF.load_kc_catalog()
    rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "وبالكتابِ"})
    evs = LF.build_events(rec["diagnostics"], by_class)
    return evs[0]


def _bad_events():
    g = _good_event()
    out = []
    b = json.loads(json.dumps(g)); b["bottom_out_hint"] = {"text": "the answer", "references_cause": True, "source_clean": True}
    out.append(("LF-1", b))  # gate is two_vote, bottom_out present
    b = json.loads(json.dumps(g)); b["when_not_to_give_answer"]["gate"] = "auto_safe"; b["decision_status"] = "pending"
    b["bottom_out_hint"] = {"text": "the answer", "references_cause": True, "source_clean": True}
    out.append(("LF-2", b))  # auto_safe but pending + bottom_out
    b = json.loads(json.dumps(g)); b["point_hint"]["text"] = "see the QAC tagset"
    out.append(("LF-3", b))
    b = json.loads(json.dumps(g)); b["drill_route"] = "curriculum/drills/does-not-exist.md"
    out.append(("LF-4", b))
    b = json.loads(json.dumps(g)); b["diagnostic_class"] = "weak_irab_reasoning"; b["teach_hint"]["references_cause"] = False
    out.append(("LF-5", b))
    b = json.loads(json.dumps(g)); b["when_not_to_give_answer"]["gate"] = "auto_publish"
    out.append(("LF-6", b))
    b = json.loads(json.dumps(g)); b["knowledge_component"] = "kc-nope"
    out.append(("LF-7", b))
    b = json.loads(json.dumps(g)); b["examples"] = [{"en": "x", "public_boundary": {"public_gloss_src": "qamus", "public_gloss_kind": "authored", "public_gloss_lang": "en", "external_source_names_public": True}}]
    out.append(("LF-8", b))
    b = json.loads(json.dumps(g)); b["diagnostic_class"] = "totally_invented_class"
    out.append(("LF-9", b))
    b = json.loads(json.dumps(g)); b["cefr_level_min"] = "A1"; b["teach_hint"]["text"] = "name the governor and the genitive case"
    out.append(("LF-10", b))
    return out


def _self_test():
    from tools import fusha_text_check as TC
    _kcs, by_class = LF.load_kc_catalog()
    failures = []
    for raw in ["وبالكتابِ", "علم نور", "كتابُهم جديدٌ", "من يقرأ"]:
        rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": raw})
        for ev in LF.build_events(rec["diagnostics"], by_class):
            errs = validate_event(ev)
            if errs:
                failures.append("good event (%s) should validate clean but: %s" % (raw, errs[:2]))
    for cond, ev in _bad_events():
        conds = {c for c, _ in validate_event(ev)}
        if cond not in conds:
            failures.append("bad event should trip %s but tripped %s" % (cond, sorted(conds)))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_learner_feedback self-test: events clean; LF-1..10 reject (bottom-out gating, leak, routes, cause, KC, CEFR beginner-safety)")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate learner-feedback hint-ladder events.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.path:
        ap.error("need a path or --self-test")
    n, errs = validate_file(a.path)
    for cond, msg in errs:
        print("FAIL [%s] %s" % (cond, msg))
    print("checked %d event(s), %d violation(s)" % (n, len(errs)))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
