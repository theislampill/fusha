#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_conflicts — cross-builder conflict detector + precedence resolver (P2 deliverable F).

The five builders (arbitrary-typing checker, source-addressed parser/checker, rich-hover flywheel, certification
validator, curriculum/tutor route) can disagree on the same token. This module turns a disagreement into an explicit
cross-builder CONFLICT record (qamus/schemas/cross-builder-conflict.schema.json). It SURFACES the conflict and routes
it — it NEVER silently picks a side. The winning_source_of_truth is chosen by a fixed precedence order:

  source-addressed certainty > heuristic ;  cert-validator gate > candidate gate ;  deterministic verdict > suggestion ;
  qg-palette enum > segment-role ;  source-clean public_boundary > internal evidence.

gate_required is the MAX of the two readings' gates (and the conflict-type floor); the conflict routes to two-vote /
human / scholar review (or, for a public-gloss-vs-internal-lattice conflict, the public gloss stands and the lattice
merely flags an internal review). Dry-run: live_writes==0; all public text scanned via leak_sot.
CLI: --self-test | --emit-fixture <path> | --in <specs.jsonl> --out <-|path>.
See parserplans/general-fusha-grammar-checker-p2/006-cross-builder-conflict-resolution.md.
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
from tools.validate_linguistic_decisions import _GATE_RANK  # noqa: E402

SCHEMA = "fusha/cross-builder-conflict@1"
_PUBLIC_BOUNDARY = {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                    "public_gloss_lang": "en", "external_source_names_public": False}
_RANK_TO_GATE = {v: k for k, v in _GATE_RANK.items()}

# conflict_type -> resolution per the master precedence order (winning SoT + floor gate + next action + route)
CONFLICT_RESOLUTION = {
    "C1_sarf_pos_vs_nahw_irab": dict(winning="sarf_reanalysis", floor="never_auto_resolve", next="return_to_sarf",
                                     lane="sarf", proc="sarf/procedures/homograph-risk.md", sev="block", block="blocking"),
    "C2_morphology_vs_governor": dict(winning="source_addressed_checker", floor="two_vote_required", next="route_to_two_vote",
                                      lane="nahw", proc="nahw/procedures/irab-case-mood.md", sev="warn", block="non_blocking"),
    "C3_nahw_vote_a_vs_b": dict(winning="neither", floor="two_vote_required", next="hold_pending_both_readings",
                                lane="scholar_irab_review", proc="nahw/procedures/grammar-risk-gate.md", sev="warn", block="blocking"),
    "C4_candidate_gate_vs_cert_gate": dict(winning="cert_validator", floor="two_vote_required", next="downgrade_gate_to_max",
                                           lane="validator", proc="qamus/reports/general-checker-rich-hover-flywheel.md", sev="warn", block="blocking"),
    "C5_verdict_vs_suggestion": dict(winning="deterministic_verdict", floor="two_vote_required", next="suppress_unsafe_suggestion",
                                     lane="validator", proc="nahw/procedures/irab-case-mood.md", sev="warn", block="blocking"),
    "C6_segment_role_vs_qg_palette": dict(winning="qg_palette", floor="two_vote_required", next="map_role_to_nearest_qg_class",
                                          lane="curriculum", proc="curriculum/qamus-hover-parse-key-and-color.md", sev="info", block="non_blocking"),
    "C7_homograph_unresolved": dict(winning="neither", floor="two_vote_required", next="hold_pending_both_readings",
                                    lane="sarf", proc="sarf/procedures/homograph-risk.md", sev="warn", block="blocking"),
    "C8_idafa_vs_jar_majrur": dict(winning="neither", floor="two_vote_required", next="hold_pending_both_readings",
                                   lane="nahw", proc="nahw/procedures/idafa-jar-majrur.md", sev="warn", block="blocking"),
    "C9_public_gloss_vs_internal_lattice": dict(winning="public_gloss", floor="two_vote_required",
                                                next="public_gloss_stands_lattice_flags_internal_review",
                                                lane="validator", proc="provenance/source-boundaries.md", sev="info", block="non_blocking"),
    "C10_suggestion_vs_suggestion": dict(winning="neither", floor="two_vote_required", next="hold_pending_both_readings",
                                         lane="nahw", proc="nahw/procedures/pp-attachment-review.md", sev="warn", block="non_blocking"),
}


def _max_gate(gates):
    ranks = []
    for g in gates:
        if g is None:
            continue
        # an UNKNOWN/misspelled gate fails SAFE to the strictest tier (never silently coerce to auto_safe / rank 0,
        # which would let a typo'd human_source_review_required escalation drop to the two-vote floor).
        ranks.append(_GATE_RANK[g] if g in _GATE_RANK else _GATE_RANK["never_auto_resolve"])
    return _RANK_TO_GATE[max(ranks, default=0)]


def _clean(s):
    return leak_sot.redact(s) if isinstance(s, str) else s


def make_conflict(conflict_loc, conflict_type, involved_builders, reason, readings, raww=False):
    """Build a well-formed conflict record. readings = [{builder, reading, gate}, ...] (>=2). Surfaces, never picks."""
    res = CONFLICT_RESOLUTION[conflict_type]
    gate = _max_gate([res["floor"]] + [r.get("gate") for r in readings])
    # a right-answer-wrong-reason conflict ESCALATES to scholar/iʿrāb review (overrides the type's default route/next/gate
    # floor); a correct ending with a wrong reason is the GP-WR case that must reach a scholar, not stop at two-vote.
    if raww:
        lane, proc, nxt = "scholar_irab_review", "nahw/procedures/irab-case-mood.md", "route_to_scholar_irab_review"
        gate = _max_gate([gate, "two_vote_required"])
    else:
        lane, proc, nxt = res["lane"], res["proc"], res["next"]
    clean_readings = [{"builder": r.get("builder"), "reading": _clean(r.get("reading")), "gate": r.get("gate")} for r in readings]
    # winner_evidence_index: index of the reading the precedence selects (so a UI can dereference winner→reading), or
    # null when no single reading wins (winning_source_of_truth in {neither} or the winner is a process, not a builder).
    win = res["winning"]
    winner_evidence_index = next((i for i, r in enumerate(readings) if r.get("builder") == win), None)
    rec = {
        "schema": SCHEMA, "conflict_loc": conflict_loc, "conflict_type": conflict_type,
        "involved_builders": involved_builders, "severity": res["sev"], "blocking_status": res["block"],
        "reason_for_disagreement": _clean(reason), "winning_source_of_truth": win,
        "winner_evidence_index": winner_evidence_index,
        "gate_required": gate, "next_action": nxt,
        "route_to": {"lane": lane, "procedure": proc},
        "resolution_path": ["surface the disagreement (never auto-pick)",
                            "apply precedence: %s" % win,
                            "gate at max(%s) and %s" % (gate, nxt)],
        "right_answer_wrong_reason_marker": raww,
        "evidence_from_both_sides": clean_readings,
        "public_boundary": dict(_PUBLIC_BOUNDARY), "live_writes": 0,
    }
    assert rec["live_writes"] == 0, "dry-run"
    return rec


# ---------------------------------------------------------------------------
# real detectors (a few concrete cases; the rest are surfaced by callers via make_conflict)
# ---------------------------------------------------------------------------
def detect_verdict_vs_suggestion(loc, verdict, suggestion):
    """C5: a deterministic verdict says contradicted/unsafe but a suggestion claims safe_inline -> verdict wins."""
    if verdict.get("status") in {"contradicted", "unsafe_reasoning"} and suggestion.get("safe_to_show_inline"):
        return make_conflict(loc, "C5_verdict_vs_suggestion", ["source_addressed_checker", "suggestion_engine"],
                             "The deterministic verdict is %s, but a suggestion proposes a safe inline edit; the verdict wins and the suggestion is suppressed." % verdict.get("status"),
                             [{"builder": "source_addressed_checker", "reading": verdict.get("status"), "gate": verdict.get("gate")},
                              {"builder": "suggestion_engine", "reading": "safe_inline edit", "gate": suggestion.get("gate")}])
    return None


def detect_candidate_vs_cert_gate(loc, candidate_gate, cert_gate):
    """C4: a rich-hover candidate gate is weaker than the cert validator's gate -> cert wins, downgrade to max."""
    if candidate_gate and cert_gate and _GATE_RANK.get(candidate_gate, 0) < _GATE_RANK.get(cert_gate, 0):
        return make_conflict(loc, "C4_candidate_gate_vs_cert_gate", ["rich_hover_flywheel", "cert_validator"],
                             "The candidate gate (%s) is weaker than the certification gate (%s); the cert validator wins and the row is held at the stricter gate." % (candidate_gate, cert_gate),
                             [{"builder": "rich_hover_flywheel", "reading": "gate=%s" % candidate_gate, "gate": candidate_gate},
                              {"builder": "cert_validator", "reading": "gate=%s" % cert_gate, "gate": cert_gate}])
    return None


def detect_governor_vs_grounded(loc, gov_edge, verdict):
    """C2: a governor edge flags right-answer-wrong-reason but a verdict says grounded -> source-addressed > heuristic."""
    if gov_edge.get("right_answer_wrong_reason_marker") and verdict.get("status") == "grounded":
        return make_conflict(loc, "C2_morphology_vs_governor", ["governor_lattice", "source_addressed_checker"],
                             "The governor lattice flags an unjustified governor (right answer, wrong reason) while the source-addressed verdict reports grounded; surface for two-vote review.",
                             [{"builder": "governor_lattice", "reading": "governor_not_justified", "gate": gov_edge.get("gate")},
                              {"builder": "source_addressed_checker", "reading": "grounded", "gate": verdict.get("gate")}],
                             raww=True)
    return None


# ---------------------------------------------------------------------------
# regression specs (one per conflict type) + self-test
# ---------------------------------------------------------------------------
def regression_records():
    R = lambda b, r, g: {"builder": b, "reading": r, "gate": g}  # noqa: E731
    out = [
        make_conflict("tok:1", "C1_sarf_pos_vs_nahw_irab", ["sarf", "nahw"],
                      "sarf reads the token as a noun on the wazn fiʿl, but the iʿrāb implies an active participle; return to sarf.",
                      [R("sarf", "noun (wazn fiʿl)", "two_vote_required"), R("nahw", "active participle role", "two_vote_required")]),
        make_conflict("tok:1", "C2_morphology_vs_governor", ["morphology_lattice", "governor_lattice"],
                      "A passive-voice morphology candidate competes with a governor that expects an active reading; source-addressed certainty would decide, else two-vote.",
                      [R("morphology_lattice", "passive candidate", "two_vote_required"), R("governor_lattice", "active expected", "two_vote_required")]),
        make_conflict("28:82:7", "C3_nahw_vote_a_vs_b", ["nahw", "nahw"],
                      "Two independent nahw checks agree the verb is past but disagree on WHY (mood vs verb-form); neither wins until conclusion AND reasoning align.",
                      [R("nahw", "past via mood", "two_vote_required"), R("nahw", "past via verb form", "two_vote_required")]),
        make_conflict("3:123:4", "C4_candidate_gate_vs_cert_gate", ["rich_hover_flywheel", "cert_validator"],
                      "The candidate gate is auto_safe but the certification gate requires two-vote; the cert validator wins.",
                      [R("rich_hover_flywheel", "gate=auto_safe", "auto_safe"), R("cert_validator", "gate=two_vote_required", "two_vote_required")]),
        make_conflict("33:63:1", "C5_verdict_vs_suggestion", ["source_addressed_checker", "suggestion_engine"],
                      "The verdict is contradicted, but a suggestion proposes a safe inline edit; the verdict wins and the suggestion is suppressed.",
                      [R("source_addressed_checker", "contradicted", "two_vote_required"), R("suggestion_engine", "safe_inline", "auto_safe")]),
        make_conflict("1:2:4", "C6_segment_role_vs_qg_palette", ["governor_lattice", "qg_palette"],
                      "A segment role has no exact qg-palette class; the palette enum wins — map to the nearest supported class and keep the role in parse_key.summary.",
                      [R("governor_lattice", "role=adverbial", "two_vote_required"), R("qg_palette", "nearest=qg-particle", "two_vote_required")]),
        make_conflict("tok:2", "C7_homograph_unresolved", ["sarf", "morphology_lattice"],
                      "A norm_strict collision yields two morphology candidates with the diacritic absent; pending, route to sarf.",
                      [R("sarf", "reading A", "two_vote_required"), R("morphology_lattice", "reading B", "two_vote_required")]),
        make_conflict("tok:3", "C8_idafa_vs_jar_majrur", ["governor_lattice", "nahw"],
                      "A noun-noun sequence is ambiguous between iḍāfa and a ṣifa reading; hold pending with both readings.",
                      [R("governor_lattice", "iḍāfa", "two_vote_required"), R("nahw", "ṣifa", "two_vote_required")]),
        make_conflict("16:16:2", "C9_public_gloss_vs_internal_lattice", ["curriculum_route", "governor_lattice"],
                      "The shipped public gloss is resolved, but the internal lattice finds an unresolved attachment; the public gloss stands and the lattice flags an internal review.",
                      [R("curriculum_route", "public gloss resolved", "auto_safe"), R("governor_lattice", "attachment unresolved", "two_vote_required")]),
        make_conflict("tok:4", "C10_suggestion_vs_suggestion", ["suggestion_engine", "suggestion_engine"],
                      "Two suggestions overlap on one token (split-clitic vs keep-merged); both plausible -> pending, no auto-pick (NMS unresolved).",
                      [R("suggestion_engine", "split clitic", "two_vote_required"), R("suggestion_engine", "keep merged", "two_vote_required")]),
    ]
    return out


def _self_test():
    failures = []
    recs = regression_records()
    types_seen = {r["conflict_type"] for r in recs}
    if types_seen != set(CONFLICT_RESOLUTION):
        failures.append("fixture does not cover all 10 conflict types: missing %s" % (set(CONFLICT_RESOLUTION) - types_seen))
    for r in recs:
        if not r.get("winning_source_of_truth") or not r.get("next_action") or not r.get("gate_required"):
            failures.append("%s missing winning/next/gate" % r["conflict_type"])
        if len(r.get("evidence_from_both_sides") or []) < 2:
            failures.append("%s < 2 readings" % r["conflict_type"])
        # gate_required must be the max of the readings' gates and the floor
        gates = [CONFLICT_RESOLUTION[r["conflict_type"]]["floor"]] + [e.get("gate") for e in r["evidence_from_both_sides"]]
        if r["gate_required"] != _max_gate(gates):
            failures.append("%s gate_required is not max(readings)" % r["conflict_type"])
        for f in ("reason_for_disagreement",):
            if leak_sot.is_leak(r.get(f) or ""):
                failures.append("%s leak in %s" % (r["conflict_type"], f))
    # precedence guarantees
    c4 = next(r for r in recs if r["conflict_type"] == "C4_candidate_gate_vs_cert_gate")
    if c4["winning_source_of_truth"] != "cert_validator" or c4["gate_required"] != "two_vote_required":
        failures.append("C4 must select cert_validator + downgrade to the stricter gate")
    c5 = next(r for r in recs if r["conflict_type"] == "C5_verdict_vs_suggestion")
    if c5["winning_source_of_truth"] != "deterministic_verdict":
        failures.append("C5 must select the deterministic verdict over the suggestion")
    # real detectors
    if not detect_verdict_vs_suggestion("x", {"status": "contradicted", "gate": "two_vote_required"}, {"safe_to_show_inline": True, "gate": "auto_safe"}):
        failures.append("detect_verdict_vs_suggestion should fire")
    if detect_verdict_vs_suggestion("x", {"status": "grounded", "gate": "auto_safe"}, {"safe_to_show_inline": True, "gate": "auto_safe"}):
        failures.append("detect_verdict_vs_suggestion must NOT fire when verdict grounded")
    if not detect_candidate_vs_cert_gate("x", "auto_safe", "two_vote_required"):
        failures.append("detect_candidate_vs_cert_gate should fire (candidate weaker)")
    if detect_candidate_vs_cert_gate("x", "two_vote_required", "auto_safe"):
        failures.append("detect_candidate_vs_cert_gate must NOT fire when candidate already stricter")
    # H: an unknown/typo'd gate fails SAFE to the strictest tier (never silently auto_safe / rank 0)
    if _max_gate(["two_vote_required", "human_source_review_requiredX"]) != "never_auto_resolve":
        failures.append("H: an unknown gate must coerce to the strictest tier (fail-safe)")
    # Q: a right-answer-wrong-reason conflict ESCALATES to scholar/iʿrāb review
    _rw = make_conflict("x", "C2_morphology_vs_governor", ["governor_lattice", "source_addressed_checker"], "r",
                        [{"builder": "governor_lattice", "reading": "a", "gate": "two_vote_required"},
                         {"builder": "source_addressed_checker", "reading": "b", "gate": "two_vote_required"}], raww=True)
    if _rw["route_to"]["lane"] != "scholar_irab_review" or _rw["next_action"] != "route_to_scholar_irab_review":
        failures.append("Q: a raww conflict must escalate to scholar_irab_review")
    # L: winner_evidence_index points at the winning reading
    _c4 = next(r for r in recs if r["conflict_type"] == "C4_candidate_gate_vs_cert_gate")
    if _c4["winner_evidence_index"] is None or _c4["evidence_from_both_sides"][_c4["winner_evidence_index"]]["builder"] != _c4["winning_source_of_truth"]:
        failures.append("L: winner_evidence_index must point at the winning reading")
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_conflicts self-test: all 10 conflict types; gate=max(readings); precedence (cert>candidate, verdict>suggestion); detectors; source-clean")
    return 0 if not failures else 1


def emit_fixture(path):
    rows = regression_records()
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {
        "schema": SCHEMA, "generator": "tools/fusha_conflicts.py --emit-fixture", "count": len(rows),
        "conflict_types": sorted({r["conflict_type"] for r in rows}),
        "note": "Cross-builder conflict records (C1-C10). P2 SURFACES conflicts and routes them; it never picks sides. "
                "Precedence: source-addressed>heuristic; cert-gate>candidate-gate; verdict>suggestion; qg-palette>role; "
                "source-clean>internal. gate_required=max. Authored; source-clean; live_writes==0. parserplans p2/006.",
    }
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d conflict records -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Fusha cross-builder conflict detector/resolver (dry-run; surfaces, never picks).")
    ap.add_argument("--in", dest="infile")
    ap.add_argument("--out", dest="outfile", default="-")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    if not a.infile:
        ap.error("need --in, --self-test, or --emit-fixture")
    rows = []
    with open(a.infile, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                s = json.loads(line)
                rows.append(make_conflict(s["conflict_loc"], s["conflict_type"], s["involved_builders"],
                                          s.get("reason", ""), s.get("readings", []), s.get("raww", False)))
    sink = sys.stdout if a.outfile == "-" else open(a.outfile, "w", encoding="utf-8")
    for r in rows:
        sink.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
