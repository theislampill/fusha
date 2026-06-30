#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_cefr_gate — CEFR diagnostic gating + abstention projection (P2b deliverable 005).

A pure, side-effect-free projection from a CALLER-supplied CEFR level onto a fusha/text-check record and learner-feedback
events. CEFR gates DISPLAY, not linguistics: the projection can only REMOVE detail or DOWNGRADE a suggestion to a hint —
it never adds certainty, lowers a safety gate, forces a parse, reveals a withheld Bottom-out, or asserts a learner's
level. It returns a COPY/view; it never mutates the source. Invariants (enforced in --self-test):
  * subset visibility   — filtered diagnostics are a subset of the originals;
  * monotonic gates     — no surviving item's gate is weaker than the original;
  * ambiguity preserved — a >1-candidate token keeps n_candidates and all_unvoweled_kept (only the RENDERED count shrinks);
  * no reveal           — a Bottom-out that was withheld (null) stays absent at every level.
See parserplans/general-fusha-grammar-checker-p2b-learning-cefr/005.
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

SCHEMA = "fusha/cefr-projection@1"
LEVELS_PATH = os.path.join(_REPO, "curriculum", "cefr-fusha-levels.json")
DEFAULT_LEVEL = "B1"
_BEGINNER = {"pre_A1", "A1", "A2"}


def load_levels(path=LEVELS_PATH):
    return {r["level"]: r for r in json.load(open(path, encoding="utf-8"))}


def visible_for(level, levels=None):
    levels = levels or load_levels()
    return set((levels.get(level) or {}).get("diagnostic_visibility", []))


def hint_depth_for(level, levels=None):
    levels = levels or load_levels()
    return (levels.get(level) or {}).get("hint_depth", "point")


def cefr_filter(record, level, levels=None):
    """Project a fusha/text-check record for a caller-supplied level. Returns a view (never mutates `record`)."""
    levels = levels or load_levels()
    lvl = levels.get(level) or levels.get(DEFAULT_LEVEL)
    allow = set(lvl.get("diagnostic_visibility", []))
    beginner = level in _BEGINNER
    diags = [d for d in record.get("diagnostics") or [] if d.get("issue_class") in allow]
    hidden = len(record.get("diagnostics") or []) - len(diags)
    # morphology: at beginner levels render only the top candidate, but KEEP n_candidates + all_unvoweled_kept (ambiguity).
    morph = []
    for lat in record.get("morphology_candidates") or []:
        cands = lat.get("candidates") or []
        rendered = [c for c in cands if c.get("rank") == 1] if (beginner and len(cands) > 1) else cands
        morph.append({"token_ref": lat.get("token_ref"), "rendered_candidates": rendered,
                      "n_candidates": lat.get("n_candidates", len(cands)), "all_unvoweled_kept": lat.get("all_unvoweled_kept", True)})
    # suggestions: downgrade to hints at non-explicit levels; NEVER raise safe_to_show_inline beyond the original.
    explicit = lvl.get("correction_aggressiveness") == "explicit"
    suggs = []
    for s in record.get("suggestions") or []:
        s2 = json.loads(json.dumps(s))
        if not explicit and s2.get("safe_to_show_inline"):
            s2["safe_to_show_inline"] = False  # downgrade only
        suggs.append(s2)
    return {
        "schema": SCHEMA, "level": level, "metalanguage_exposure": lvl.get("metalanguage_exposure"),
        "hint_depth": lvl.get("hint_depth"), "correction_aggressiveness": lvl.get("correction_aggressiveness"),
        "diagnostics": diags, "hidden_diagnostic_count": hidden,
        "morphology_candidates": morph, "suggestions": suggs,
    }


def gate_event(event, level, levels=None):
    """Project a learner-feedback event to a level's hint depth. NEVER reveals a withheld Bottom-out."""
    depth = hint_depth_for(level, levels)
    point = event.get("point_hint")
    teach = event.get("teach_hint") if depth in ("point_teach", "full_ladder") else None
    # Bottom-out shows only at full_ladder AND only if it was not withheld upstream (no reveal).
    bottom = event.get("bottom_out_hint") if (depth == "full_ladder" and event.get("bottom_out_hint") is not None) else None
    return {"schema": "fusha/cefr-hint-view@1", "level": level, "hint_depth": depth,
            "point_hint": point, "teach_hint": teach, "bottom_out_hint": bottom,
            "when_not_to_give_answer": event.get("when_not_to_give_answer")}


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def _self_test():
    from tools import fusha_text_check as TC  # lazy
    from tools import fusha_learner_feedback as LF
    levels = load_levels()
    failures = []
    if set(levels) != {"pre_A1", "A1", "A2", "B1", "B2", "C1", "C2"}:
        failures.append("level set is not the 7 CEFR bands")
    rec = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "وبالكتابِ علم نور"})
    orig_classes = {d["issue_class"] for d in rec["diagnostics"]}
    orig_gate = {d["issue_class"]: d["gate"] for d in rec["diagnostics"]}
    orig_ncand = {l["token_ref"]: l["n_candidates"] for l in rec["morphology_candidates"]}
    _kcs, by_class = LF.load_kc_catalog()
    events = LF.build_events(rec["diagnostics"], by_class)
    for level in levels:
        proj = cefr_filter(rec, level, levels)
        shown = {d["issue_class"] for d in proj["diagnostics"]}
        # subset visibility
        if not shown <= orig_classes:
            failures.append("%s: projection added a diagnostic (not a subset)" % level)
        # monotonic gates
        for d in proj["diagnostics"]:
            if _GATE_RANK[d["gate"]] < _GATE_RANK[orig_gate[d["issue_class"]]]:
                failures.append("%s: projection lowered a gate" % level)
        # beginner bands never surface an iʿrāb-sensitive class
        if level in _BEGINNER:
            from tools.fusha_check import IRAB_SENSITIVE_ISSUE_CLASSES
            if shown & IRAB_SENSITIVE_ISSUE_CLASSES:
                failures.append("%s: beginner band surfaced an iʿrāb-sensitive diagnostic" % level)
        # ambiguity preserved
        for l in proj["morphology_candidates"]:
            if l["n_candidates"] != orig_ncand.get(l["token_ref"]):
                failures.append("%s: projection dropped n_candidates (ambiguity)" % level)
            if l["all_unvoweled_kept"] is not True:
                failures.append("%s: projection dropped all_unvoweled_kept" % level)
        # suggestions never raised toward inline
        for s in proj["suggestions"]:
            if s.get("safe_to_show_inline") and level not in ("B2", "C1", "C2"):
                failures.append("%s: projection raised safe_to_show_inline" % level)
        # events: no withheld Bottom-out revealed; rungs respect depth
        for ev in events:
            view = gate_event(ev, level, levels)
            if ev.get("bottom_out_hint") is None and view["bottom_out_hint"] is not None:
                failures.append("%s: projection revealed a withheld Bottom-out" % level)
            if hint_depth_for(level, levels) == "point" and view["teach_hint"] is not None:
                failures.append("%s: point-depth view exposed a Teach rung" % level)
    # leak-clean projection
    for level in levels:
        proj = cefr_filter(rec, level, levels)
        if leak_sot.is_leak(json.dumps(proj, ensure_ascii=False)):
            failures.append("%s: projection leaks" % level)
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_cefr_gate self-test: subset-visible; monotonic gates; ambiguity preserved; no Bottom-out reveal; beginner-safe; source-clean")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="CEFR diagnostic-gating projection (scaffold, not certification; dry-run).")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    ap.error("need --self-test")


if __name__ == "__main__":
    sys.exit(main())
