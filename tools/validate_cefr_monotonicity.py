#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_cefr_monotonicity — a PROPERTY test that the CEFR display-depth ladder is MONOTONIC (P2-11).

`fusha_cefr_gate` projects a caller-supplied CEFR level onto a fusha record: it can only REMOVE detail or DOWNGRADE a
suggestion to a hint. The intended discipline is that the seven bands (pre_A1 < A1 < A2 < B1 < B2 < C1 < C2) form a
NON-DECREASING ladder of display depth — a higher band never shows LESS than a lower one. This is a contract on the
GATE, so the test imports `fusha_cefr_gate` and CALLS it (visible_for / hint_depth_for / cefr_filter / gate_event)
rather than re-reading the JSON; it measures behaviour, not the data file.

MONOTONICITY (each measured per pair lower < higher on the canonical ladder):
  * diagnostic visibility  — visible_for(higher) ⊇ visible_for(lower)  (the rendered diagnostic set is a growing chain);
  * metalanguage exposure  — exposure_rank(higher) >= exposure_rank(lower)  (none<=minimal<=moderate<=full);
  * correction aggressiveness — aggr_rank(higher) >= aggr_rank(lower)  (hint_only<=gentle<=standard<=explicit);
  * hint depth             — depth_rank(higher) >= depth_rank(lower)  (point<=point_teach<=full_ladder).

SAFETY (asserted at EVERY level, via the gate's own projection of a real record):
  * never forces a parse        — ambiguity is preserved (n_candidates kept; >1-candidate token keeps all candidates);
  * never reveals a withheld Bottom-out — a null bottom_out_hint stays null at every level;
  * never certifies/asserts a learner level — no projection output contains a certification/assertion claim.

--self-test: a SYNTHETIC monotonic ladder PASSES; a tampered non-monotonic ladder is CAUGHT on every dimension; the
REAL levels (fusha_cefr_gate is already monotonic-safe) PASS. Stdlib only; dry-run; no CEFR certification claim emitted.
See parserplans/fusha-data-runtime-completion-pass (P2-11).
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import leak_sot          # noqa: E402
from tools import fusha_cefr_gate as G  # noqa: E402

# the canonical zero-to-fluency ladder; index = rank (lowest display depth first).
LADDER = ("pre_A1", "A1", "A2", "B1", "B2", "C1", "C2")
# ordinal scales the gate's own string knobs map onto (lower display depth -> smaller rank).
METALANG_RANK = {"none": 0, "minimal": 1, "moderate": 2, "full": 3}
AGGR_RANK = {"hint_only": 0, "gentle": 1, "standard": 2, "explicit": 3}
DEPTH_RANK = {"point": 0, "point_teach": 1, "full_ladder": 2}
# phrases that would amount to ASSERTING/certifying a learner's level — must never appear in a projection's output.
# (Intentionally assertion-shaped, not the bare stem "certif", so neutral safety prose like "not a certification"
# never trips them; the gate emits structured display fields, so a real certification claim is an injected sentence.)
_CERT_MARKERS = ("you are at level", "your level is", "your cefr level", "assessed as level", "attained level",
                 "qualifies as level", "certified at level", "you are certified", "officially at level")


def _meta_rank(level, levels):
    return METALANG_RANK.get((levels.get(level) or {}).get("metalanguage_exposure"), -1)


def _aggr_rank(level, levels):
    return AGGR_RANK.get((levels.get(level) or {}).get("correction_aggressiveness"), -1)


def _depth_rank(level, levels):
    # read depth THROUGH the gate (its public accessor), not the raw row.
    return DEPTH_RANK.get(G.hint_depth_for(level, levels), -1)


def check_ladder(levels, ladder=LADDER, record=None):
    """Return a list of violation strings (empty == monotonic + safe). `levels` is {level: row} as the gate loads them.

    Monotonicity is checked on adjacent pairs of `ladder`; the safety invariants are checked by projecting `record`
    (a fusha/text-check-shaped dict) at every level through the gate.
    """
    errs = []
    present = [lv for lv in ladder if lv in levels]
    if len(present) < 2:
        return ["ladder has fewer than 2 known levels: %s" % present]
    if set(levels) != set(ladder):
        errs.append("level set %s is not the canonical ladder %s" % (sorted(levels), list(ladder)))

    # ---- monotonicity on adjacent pairs (lower -> higher) -------------------
    for lo, hi in zip(present, present[1:]):
        vlo, vhi = G.visible_for(lo, levels), G.visible_for(hi, levels)
        if not vlo <= vhi:                                   # visibility must be a growing chain
            errs.append("visibility not monotonic: %s shows %s NOT subset of %s's %s"
                        % (lo, sorted(vlo - vhi), hi, sorted(vhi)))
        if _meta_rank(hi, levels) < _meta_rank(lo, levels):
            errs.append("metalanguage_exposure drops from %s to %s" % (lo, hi))
        if _aggr_rank(hi, levels) < _aggr_rank(lo, levels):
            errs.append("correction_aggressiveness drops from %s to %s" % (lo, hi))
        if _depth_rank(hi, levels) < _depth_rank(lo, levels):
            errs.append("hint_depth drops from %s to %s" % (lo, hi))

    # ---- safety, asserted at EVERY level via a real projection --------------
    if record is not None:
        orig_ncand = {l.get("token_ref"): l.get("n_candidates")
                      for l in record.get("morphology_candidates") or []}
        for lv in present:
            proj = G.cefr_filter(record, lv, levels)
            # never forces a parse: ambiguity (candidate count) is preserved verbatim.
            for l in proj.get("morphology_candidates") or []:
                if l.get("n_candidates") != orig_ncand.get(l.get("token_ref")):
                    errs.append("%s: projection altered n_candidates (forced a parse)" % lv)
                if l.get("all_unvoweled_kept") is not True:
                    errs.append("%s: projection dropped all_unvoweled_kept (forced a parse)" % lv)
            # never reveals a withheld Bottom-out: a null bottom-out stays null through the gate at this depth.
            view = G.gate_event({"point_hint": "p", "teach_hint": "t", "bottom_out_hint": None}, lv, levels)
            if view.get("bottom_out_hint") is not None:
                errs.append("%s: gate revealed a withheld Bottom-out" % lv)
            # never certifies/asserts a learner level: no certification language in the projection's output.
            blob = json.dumps(proj, ensure_ascii=False).lower()
            for mark in _CERT_MARKERS:
                if mark in blob:
                    errs.append("%s: projection emits a learner-level certification/assertion claim (%r)" % (lv, mark))
            # leak-clean projection (no QAC/tafsir/external gloss/path/secret).
            if leak_sot.is_leak(json.dumps(proj, ensure_ascii=False)):
                errs.append("%s: projection leaks a forbidden token" % lv)
    return errs


def _real_record(levels):
    """Build a real fusha/text-check record to project. Falls back to a tiny synthetic record if the live checker
    is unavailable, so this property test stays runnable in a public clone."""
    try:
        from tools import fusha_text_check as TC
        return TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "وبالكتابِ علم نور"})
    except Exception:
        # minimal record exercising ambiguity + a withheld bottom-out path, gate-shaped.
        return {"diagnostics": [], "suggestions": [],
                "morphology_candidates": [{"token_ref": "t1", "candidates": [{"rank": 1}, {"rank": 2}],
                                           "n_candidates": 2, "all_unvoweled_kept": True}]}


def _self_test():
    failures = []
    levels = G.load_levels()
    record = _real_record(levels)

    # 1. SYNTHETIC monotonic ladder -> passes (built so each dimension only ever climbs).
    def row(level, vis, meta, aggr, depth):
        return {"level": level, "diagnostic_visibility": vis, "metalanguage_exposure": meta,
                "correction_aggressiveness": aggr, "hint_depth": depth}
    synth = {r["level"]: r for r in [
        row("pre_A1", [], "none", "hint_only", "point"),
        row("A1", ["a"], "none", "hint_only", "point"),
        row("A2", ["a", "b"], "minimal", "gentle", "point_teach"),
        row("B1", ["a", "b", "c"], "moderate", "standard", "point_teach"),
        row("B2", ["a", "b", "c", "d"], "moderate", "explicit", "full_ladder"),
        row("C1", ["a", "b", "c", "d", "e"], "full", "explicit", "full_ladder"),
        row("C2", ["a", "b", "c", "d", "e", "f"], "full", "explicit", "full_ladder"),
    ]}
    if check_ladder(synth):
        failures.append("synthetic monotonic ladder wrongly flagged: %s" % check_ladder(synth))

    # 2. each tamper must be CAUGHT on its own dimension --------------------
    # 2a. visibility regression: C2 shows LESS than C1.
    t = json.loads(json.dumps(synth))
    t["C2"]["diagnostic_visibility"] = ["a"]
    if not any("visibility not monotonic" in e for e in check_ladder(t)):
        failures.append("a visibility regression was not caught")
    # 2b. metalanguage regression: B2 drops to 'none' after A2/B1 were higher.
    t = json.loads(json.dumps(synth))
    t["B2"]["metalanguage_exposure"] = "none"
    if not any("metalanguage_exposure drops" in e for e in check_ladder(t)):
        failures.append("a metalanguage regression was not caught")
    # 2c. aggressiveness regression: C1 drops to hint_only.
    t = json.loads(json.dumps(synth))
    t["C1"]["correction_aggressiveness"] = "hint_only"
    if not any("correction_aggressiveness drops" in e for e in check_ladder(t)):
        failures.append("an aggressiveness regression was not caught")
    # 2d. hint-depth regression: C2 drops to point.
    t = json.loads(json.dumps(synth))
    t["C2"]["hint_depth"] = "point"
    if not any("hint_depth drops" in e for e in check_ladder(t)):
        failures.append("a hint_depth regression was not caught")

    # 3. SAFETY tampers caught through the gate's own projection -----------
    # 3a. a record whose projection certifies a level (inject a certification-claim diagnostic) must be caught.
    cert_rec = {"diagnostics": [{"issue_class": "orthography_normalization_warning", "gate": "auto_safe",
                                 "message": "you are at level C1 now"}],
                "suggestions": [], "morphology_candidates": []}
    # only B1+ render this class; project the real levels and confirm certification language is flagged at a level
    # that surfaces it.
    if not any("certification/assertion" in e for e in check_ladder(levels, record=cert_rec)):
        failures.append("a certification/assertion claim in a projection was not caught")
    # 3b. a record whose morphology n_candidates would change cannot (the gate preserves it) — sanity that the safety
    #     check is actually exercised: a record with >1 candidate must report n_candidates unchanged at all levels.
    amb_rec = {"diagnostics": [], "suggestions": [],
               "morphology_candidates": [{"token_ref": "z", "candidates": [{"rank": 1}, {"rank": 2}],
                                          "n_candidates": 2, "all_unvoweled_kept": True}]}
    if check_ladder(levels, record=amb_rec):
        failures.append("ambiguity-preserving record wrongly flagged: %s" % check_ladder(levels, record=amb_rec))

    # 4. the REAL levels must be monotonic + safe (fusha_cefr_gate is already monotonic-safe).
    real = check_ladder(levels, record=record)
    if real:
        failures.append("REAL CEFR levels are NOT monotonic/safe: %s" % real[:4])

    # 5. this tool's OWN output is certification-free (no learner-level claim).
    summary = ("ok   validate_cefr_monotonicity self-test: synthetic monotonic ladder passes; visibility/"
               "metalanguage/aggressiveness/hint-depth regressions caught; never forces a parse, reveals a withheld "
               "Bottom-out, or certifies a learner level; REAL levels monotonic + leak-clean (scaffold, not certification)")
    if any(m in summary.lower() for m in _CERT_MARKERS) or leak_sot.is_leak(summary):
        failures.append("self-test summary itself certifies/leaks")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print(summary)
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(
        description="Property test: the CEFR display-depth ladder is monotonic + safe (no parse-force/Bottom-out "
                    "reveal/learner certification). Scaffold, not certification; dry-run.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    # default run: assert the REAL repo levels are monotonic + safe.
    levels = G.load_levels()
    errs = check_ladder(levels, record=_real_record(levels))
    for e in errs:
        print("FAIL " + e)
    print("cefr monotonicity: %d violation(s) over %d levels" % (len(errs), len(levels)))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
