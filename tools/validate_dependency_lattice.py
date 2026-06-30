#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_dependency_lattice — conformance gate for governor/iʿrāb dependency lattices (P2 deliverable B).

Validates each lattice against qamus/schemas/dependency-candidate-lattice.schema.json, then enforces the FAIL
conditions (parserplans/general-fusha-grammar-checker-p2/{002,008}). A lattice FAILS if:

  1. an iʿrāb edge asserts a case/mood (assigned_case_mood) or right_answer_wrong_reason WITHOUT a governor_justification.
  2. an AMBIGUOUS edge (unresolved_alternatives non-empty) is marked decision_status=resolved (a forced single parse).
  3. an arbitrary/corpus-mode edge is decision_status=resolved (the ending is not visible → cannot confirm), or
     claims evidence_class=source_addressed in a non-source mode.
  4. a resolved edge has no candidate_head and is not headless (single-governor spine: at most one head, but a
     resolved governed token needs one).
  5. any edge gate is auto_safe (governor/iʿrāb edges are never auto_safe).
  6. a right_answer_wrong_reason edge is gated below two_vote_required, or does not route to scholar/iʿrāb (nahw) review.
  7. a HEURISTIC edge is decision_status=resolved (heuristic surface rules never confirm; they propose candidates),
     or source_boundary.heuristic_never_overrides_source is not true.
  8. a public-facing field (governor_justification / rel_label_ar) leaks a source/provenance/path string (leak_sot).
  9. summary.live_writes != 0.

CLI:
  python3 tools/validate_dependency_lattice.py <lattices.jsonl>
  python3 tools/validate_dependency_lattice.py --self-test
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
from tools.validate_linguistic_decisions import validate_schema, _GATE_RANK  # noqa: E402
from tools import leak_sot  # noqa: E402

SCHEMA_PATH = os.path.join(_REPO, "qamus", "schemas", "dependency-candidate-lattice.schema.json")
_SCHEMA = json.load(open(SCHEMA_PATH, encoding="utf-8"))
# The edges[] items sit behind {"$ref":"#/$defs/edge"} and the repo mini-validator does NOT resolve $ref, so the whole
# edge subtree (required keys, enums, additionalProperties) would be UNCHECKED. Validate each edge against the $defs
# subschema explicitly so a forged edge (garbage enum / missing required key / dropped unresolved_alternatives) is caught.
_EDGE_SCHEMA = _SCHEMA["$defs"]["edge"]
_NONCERT_MODES = {"arbitrary_typing", "corpus_backed"}
_SCHOLAR_LANES = {"scholar_irab_review", "nahw"}


def validate_lattice(lat):
    errors = []
    lid = (lat.get("source_unit") or {}).get("address") or lat.get("input_mode") or "?"
    for e in validate_schema(lat, _SCHEMA):
        errors.append(("schema", "%s: %s" % (lid, e)))
    mode = lat.get("input_mode")
    for idx, edge in enumerate(lat.get("edges") or []):
        tag = "%s edge[%s]" % (lid, edge.get("edge_id", idx))
        for se in validate_schema(edge, _EDGE_SCHEMA):   # enforce the $defs.edge subtree (required keys + enums)
            errors.append(("schema", "%s: %s" % (tag, se)))
        just = (edge.get("governor_justification") or "").strip()
        cm = edge.get("assigned_case_mood")
        raww = edge.get("right_answer_wrong_reason_marker")
        dec = edge.get("decision_status")
        gate = edge.get("gate")
        ev = edge.get("evidence_class")

        # FAIL 1: a case/mood or right-answer-wrong-reason edge needs a justification
        if (cm or raww) and not just:
            errors.append(("1", "%s asserts a case/iʿrāb without a governor_justification" % tag))
        # FAIL 2: ambiguous edge must not be resolved
        if (edge.get("unresolved_alternatives") or []) and dec == "resolved":
            errors.append(("2", "%s has unresolved_alternatives but decision_status=resolved (forced single parse)" % tag))
        # FAIL 3: arbitrary/corpus cannot CONFIRM a case ending (a no-case structural edge, e.g. headless coordination,
        # may still resolve — only a case/mood CLAIM needs a visible ending).
        if mode in _NONCERT_MODES:
            if dec == "resolved" and cm:
                errors.append(("3", "%s decision_status=resolved with a case/mood in %s mode (ending not visible)" % (tag, mode)))
            if ev == "source_addressed":
                errors.append(("3", "%s evidence_class=source_addressed in %s mode" % (tag, mode)))
        # FAIL 4: a resolved edge needs a head or headless; and headless ⇒ no candidate_head (else a self-contradiction)
        if dec == "resolved" and not (edge.get("candidate_head") or edge.get("headless")):
            errors.append(("4", "%s resolved without a candidate_head and not headless" % tag))
        if edge.get("headless") and edge.get("candidate_head"):
            errors.append(("4", "%s headless edge must not carry a candidate_head (contradiction)" % tag))
        # FAIL 5: never auto_safe
        if gate == "auto_safe":
            errors.append(("5", "%s gate=auto_safe (governor/iʿrāb edge may never be auto_safe)" % tag))
        # FAIL 6: right-answer-wrong-reason must be >= two_vote AND route to scholar/nahw
        if raww:
            if gate not in _GATE_RANK or _GATE_RANK.get(gate, 0) < _GATE_RANK["two_vote_required"]:
                errors.append(("6", "%s right_answer_wrong_reason gated below two_vote_required" % tag))
            if (edge.get("route_to") or {}).get("lane") not in _SCHOLAR_LANES:
                errors.append(("6", "%s right_answer_wrong_reason not routed to scholar/iʿrāb review" % tag))
        # FAIL 7: a heuristic edge may resolve ONLY when headless (the coordination wāw). Any NON-headless heuristic
        # edge that resolves is forcing a single governor — heuristic proposes a candidate, it never confirms.
        if ev == "heuristic" and dec == "resolved" and not edge.get("headless"):
            errors.append(("7", "%s heuristic edge resolves with a forced governor (heuristic proposes, never confirms)" % tag))
        # FAIL 8: public leak
        for f in ("governor_justification", "rel_label_ar"):
            if leak_sot.is_leak(edge.get(f) or ""):
                errors.append(("8", "%s %s leaks a source/provenance/path string" % (tag, f)))

    # FAIL 7 (boundary): heuristic never overrides source
    sb = lat.get("source_boundary") or {}
    if sb.get("heuristic_never_overrides_source") is not True:
        errors.append(("7", "%s source_boundary.heuristic_never_overrides_source must be true" % lid))
    # FAIL 9: dry-run
    if (lat.get("summary") or {}).get("live_writes") != 0:
        errors.append(("9", "%s summary.live_writes != 0" % lid))
    return errors


def validate_file(path):
    n, errs = 0, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            errs.extend(validate_lattice(json.loads(line)))
    return n, errs


def _bad_lattices():
    from tools import fusha_governor as G
    good = G.build_dependency_lattice(next(u for u in G.regression_units() if u["name"] == "prep-majrur-known"))
    out = []

    b = json.loads(json.dumps(good))
    b["edges"][0]["governor_justification"] = ""  # case asserted, no justification
    out.append(("1", b))

    b = json.loads(json.dumps(good))
    e = b["edges"][1]  # the pp_attachment edge has unresolved_alternatives
    e["decision_status"] = "resolved"
    out.append(("2", b))

    b = G.build_dependency_lattice(next(u for u in G.regression_units() if u["name"] == "prep-majrur-arbitrary"))
    b["edges"][0]["decision_status"] = "resolved"  # arbitrary cannot resolve
    out.append(("3", b))

    b = json.loads(json.dumps(good))
    b["edges"][0]["decision_status"] = "resolved"; b["edges"][0]["candidate_head"] = None; b["edges"][0]["headless"] = False
    out.append(("4", b))

    b = json.loads(json.dumps(good)); b["edges"][0]["gate"] = "auto_safe"
    out.append(("5", b))

    b = G.build_dependency_lattice(next(u for u in G.regression_units() if u["name"] == "weak-governor-claim"))
    for e in b["edges"]:
        if e["right_answer_wrong_reason_marker"]:
            e["route_to"] = {"lane": "curriculum", "procedure": "x.md"}  # not scholar/nahw
    out.append(("6", b))

    b = json.loads(json.dumps(good))
    b["edges"][0]["evidence_class"] = "heuristic"; b["edges"][0]["decision_status"] = "resolved"
    out.append(("7", b))

    b = json.loads(json.dumps(good)); b["edges"][0]["governor_justification"] = "genitive per the QAC tagset"
    out.append(("8", b))

    b = json.loads(json.dumps(good)); b["summary"]["live_writes"] = 1
    out.append(("9", b))

    # A (edge $ref enforcement): a forged edge with an out-of-enum value must be caught (was a no-op before).
    b = json.loads(json.dumps(good)); b["edges"][0]["governor_type"] = "banana"
    out.append(("schema", b))
    # A/B: a forged edge missing a required key (unresolved_alternatives dropped) — the ambiguity-bypass vector.
    b = json.loads(json.dumps(good)); del b["edges"][0]["unresolved_alternatives"]
    out.append(("schema", b))
    # O: a headless edge that also carries a candidate_head (self-contradiction).
    b = json.loads(json.dumps(good)); b["edges"][0]["headless"] = True; b["edges"][0]["candidate_head"] = "tok:9"
    out.append(("4", b))
    # C: a NON-headless heuristic edge that resolves with a forced governor and NO case/mood (the loophole).
    b = json.loads(json.dumps(good))
    b["edges"][0].update({"evidence_class": "heuristic", "decision_status": "resolved", "assigned_case_mood": None,
                          "headless": False, "candidate_head": "tok:9", "unresolved_alternatives": []})
    out.append(("7", b))
    return out


def _self_test():
    from tools import fusha_governor as G
    failures = []
    for u in G.regression_units():
        lat = G.build_dependency_lattice(u)
        errs = validate_lattice(lat)
        if errs:
            failures.append("good lattice %s should validate clean but: %s" % (u["name"], errs[:2]))
    for cond, lat in _bad_lattices():
        conds = {c for c, _ in validate_lattice(lat)}
        if cond not in conds:
            failures.append("bad lattice should trip FAIL %s but tripped %s" % (cond, sorted(conds)))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_dependency_lattice self-test: governor lattices clean; all 9 FAIL conditions reject")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate governor/iʿrāb dependency lattices.")
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
    print("checked %d lattice(s), %d violation(s)" % (n, len(errs)))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
