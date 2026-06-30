#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_cross_builder_conflict — conformance gate for cross-builder conflict records (P2 deliverable F).

Validates each record against qamus/schemas/cross-builder-conflict.schema.json, then enforces the FAIL conditions
(parserplans/general-fusha-grammar-checker-p2/{006,008}). A record FAILS if:

  1. it lacks a winning_source_of_truth OR next_action OR gate_required OR route_to(lane+procedure).
  2. gate_required is not the MAX of the readings' gates and the conflict-type floor.
  3. the winning_source_of_truth does not match the precedence table for its conflict_type (e.g. C4 must select
     cert_validator, C5 must select the deterministic_verdict, C2 must select source_addressed_checker — a HEURISTIC
     reading may never win over a source-addressed one).
  4. gate_required is auto_safe (a surfaced conflict is never auto-resolvable).
  5. evidence_from_both_sides has fewer than 2 readings.
  6. a public field (reason_for_disagreement / a reading) leaks a source/provenance/path string (leak_sot).
  7. live_writes != 0.

CLI:
  python3 tools/validate_cross_builder_conflict.py <records.jsonl>
  python3 tools/validate_cross_builder_conflict.py --self-test
Stdlib only. Exit non-zero on any violation.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools.validate_linguistic_decisions import validate_schema  # noqa: E402
from tools import leak_sot  # noqa: E402
from tools import fusha_conflicts as CF  # noqa: E402  (the precedence table is the source of truth)

SCHEMA_PATH = os.path.join(_REPO, "qamus", "schemas", "cross-builder-conflict.schema.json")
_SCHEMA = json.load(open(SCHEMA_PATH, encoding="utf-8"))
_LANES = {"sarf", "nahw", "curriculum", "validator", "owner_review", "scholar_irab_review"}
_GATES = {"auto_safe", "two_vote_required", "human_source_review_required", "never_auto_resolve"}


def validate_record(rec):
    errors = []
    cid = rec.get("conflict_loc", "?")
    for e in validate_schema(rec, _SCHEMA):
        errors.append(("schema", "%s: %s" % (cid, e)))
    ct = rec.get("conflict_type")

    # FAIL 1: required resolution fields
    rt = rec.get("route_to") or {}
    if not rec.get("winning_source_of_truth") or not rec.get("next_action") or not rec.get("gate_required") \
            or rt.get("lane") not in _LANES or not (rt.get("procedure") or "").strip():
        errors.append(("1", "%s: conflict lacks winning_source_of_truth / next_action / gate_required / route" % cid))

    readings = rec.get("evidence_from_both_sides") or []
    # FAIL 5: >= 2 readings
    if len(readings) < 2:
        errors.append(("5", "%s: fewer than 2 readings in evidence_from_both_sides" % cid))
    # FAIL 1: resolution_path must be non-empty (schema minItems:1 is not enforced by the mini-validator)
    if len(rec.get("resolution_path") or []) < 1:
        errors.append(("1", "%s: resolution_path is empty" % cid))
    # FAIL 8: every reading.gate must be in the 4-tier enum (an unknown/typo'd gate would silently under-gate via _max_gate)
    for r in readings:
        if r.get("gate") not in _GATES:
            errors.append(("8", "%s: a reading.gate %r is not in the 4-tier enum" % (cid, r.get("gate"))))

    # FAIL 2: gate_required == max(readings + floor)
    if ct in CF.CONFLICT_RESOLUTION:
        floor = CF.CONFLICT_RESOLUTION[ct]["floor"]
        expect_gate = CF._max_gate([floor] + [r.get("gate") for r in readings])
        if rec.get("gate_required") != expect_gate:
            errors.append(("2", "%s: gate_required %r != max(readings,floor)=%r" % (cid, rec.get("gate_required"), expect_gate)))
        # FAIL 3: winner matches the precedence table (a heuristic may never win over a source-addressed reading)
        expect_win = CF.CONFLICT_RESOLUTION[ct]["winning"]
        if rec.get("winning_source_of_truth") != expect_win:
            errors.append(("3", "%s: winning_source_of_truth %r != precedence %r for %s" % (cid, rec.get("winning_source_of_truth"), expect_win, ct)))
        # FAIL 9: severity / blocking_status must match the precedence table (metadata drift)
        if rec.get("severity") != CF.CONFLICT_RESOLUTION[ct]["sev"]:
            errors.append(("9", "%s: severity %r != table %r for %s" % (cid, rec.get("severity"), CF.CONFLICT_RESOLUTION[ct]["sev"], ct)))
        if rec.get("blocking_status") != CF.CONFLICT_RESOLUTION[ct]["block"]:
            errors.append(("9", "%s: blocking_status %r != table %r for %s" % (cid, rec.get("blocking_status"), CF.CONFLICT_RESOLUTION[ct]["block"], ct)))

    # FAIL 4: never auto_safe
    if rec.get("gate_required") == "auto_safe":
        errors.append(("4", "%s: gate_required=auto_safe (a surfaced conflict is never auto-resolvable)" % cid))

    # FAIL 9: a right-answer-wrong-reason conflict must ESCALATE to scholar/iʿrāb review
    if rec.get("right_answer_wrong_reason_marker") and rt.get("lane") != "scholar_irab_review":
        errors.append(("9", "%s: right_answer_wrong_reason conflict must route to scholar_irab_review" % cid))
    # FAIL 9: winner_evidence_index (if non-null) must point at the winning reading
    wei = rec.get("winner_evidence_index")
    if wei is not None and not (isinstance(wei, int) and 0 <= wei < len(readings)
                                and readings[wei].get("builder") == rec.get("winning_source_of_truth")):
        errors.append(("9", "%s: winner_evidence_index does not point to the winning reading" % cid))

    # FAIL 6: public leak
    if leak_sot.is_leak(rec.get("reason_for_disagreement") or ""):
        errors.append(("6", "%s: reason_for_disagreement leaks a source/provenance/path string" % cid))
    for r in readings:
        if leak_sot.is_leak(r.get("reading") or ""):
            errors.append(("6", "%s: a reading leaks a source/provenance/path string" % cid))

    # FAIL 7: dry-run
    if rec.get("live_writes") != 0:
        errors.append(("7", "%s: live_writes != 0" % cid))
    return errors


def validate_file(path):
    n, errs = 0, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            errs.extend(validate_record(json.loads(line)))
    return n, errs


def _bad_records():
    good = next(r for r in CF.regression_records() if r["conflict_type"] == "C4_candidate_gate_vs_cert_gate")
    out = []

    b = json.loads(json.dumps(good)); b["winning_source_of_truth"] = ""
    out.append(("1", b))

    b = json.loads(json.dumps(good)); b["gate_required"] = "never_auto_resolve"  # not the max of the readings/floor (two_vote)
    out.append(("2", b))

    b = json.loads(json.dumps(good)); b["winning_source_of_truth"] = "rich_hover_flywheel"  # heuristic/candidate winning over cert
    out.append(("3", b))

    # C5 winner must be deterministic_verdict
    b = next(json.loads(json.dumps(r)) for r in CF.regression_records() if r["conflict_type"] == "C5_verdict_vs_suggestion")
    b["winning_source_of_truth"] = "suggestion_engine"
    out.append(("3", b))

    b = json.loads(json.dumps(good)); b["gate_required"] = "auto_safe"; b["evidence_from_both_sides"][0]["gate"] = "auto_safe"; b["evidence_from_both_sides"][1]["gate"] = "auto_safe"
    out.append(("4", b))

    b = json.loads(json.dumps(good)); b["evidence_from_both_sides"] = [b["evidence_from_both_sides"][0]]
    out.append(("5", b))

    b = json.loads(json.dumps(good)); b["reason_for_disagreement"] = "the cert gate per the QAC tagset"
    out.append(("6", b))

    b = json.loads(json.dumps(good)); b["live_writes"] = 1
    out.append(("7", b))

    # 8: a reading with an out-of-enum gate (would silently under-gate via _max_gate)
    b = json.loads(json.dumps(good)); b["evidence_from_both_sides"][0]["gate"] = "auto_publish"
    out.append(("8", b))
    # 9: severity drift vs the precedence table (C4 table severity is 'warn')
    b = json.loads(json.dumps(good)); b["severity"] = "info"
    out.append(("9", b))
    # 9: a right-answer-wrong-reason conflict NOT escalated to scholar review
    b = json.loads(json.dumps(good)); b["right_answer_wrong_reason_marker"] = True; b["route_to"] = {"lane": "nahw", "procedure": "x.md"}
    out.append(("9", b))
    # 9: winner_evidence_index points at the wrong (losing) reading (good is C4: winner=cert_validator at index 1)
    b = json.loads(json.dumps(good)); b["winner_evidence_index"] = 0
    out.append(("9", b))
    # 1: empty resolution_path
    b = json.loads(json.dumps(good)); b["resolution_path"] = []
    out.append(("1", b))
    return out


def _self_test():
    failures = []
    for r in CF.regression_records():
        errs = validate_record(r)
        if errs:
            failures.append("good record %s should validate clean but: %s" % (r["conflict_type"], errs[:2]))
    for cond, rec in _bad_records():
        conds = {c for c, _ in validate_record(rec)}
        if cond not in conds:
            failures.append("bad record should trip FAIL %s but tripped %s" % (cond, sorted(conds)))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_cross_builder_conflict self-test: conflict records clean; all FAIL conditions reject (incl. precedence + gate=max)")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate cross-builder conflict records.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.path:
        ap.error("need a path or --self-test")
    n, errs = validate_file(a.path)
    for cond, msg in errs:
        print("FAIL [cond %s] %s" % (cond, msg))
    print("checked %d record(s), %d violation(s)" % (n, len(errs)))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
