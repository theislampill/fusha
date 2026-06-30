#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_suggest — the edit-level suggestion / correction engine (P2b deliverable C).

Turns the diagnostics already produced by `fusha_text_check.check_text` into edit-level suggestions WITHOUT ever
overcorrecting. Abstain-first (deep-research R-GEC-F05/R-GEC-OVERCORRECT: M2/F0.5 favours precision; valid edits recur,
spurious ones don't): the default posture is `abstain`. iʿrāb-sensitive suggestions are never `auto_safe` without a
governor justification; structural edits (insert/delete/replace/merge/split) are never `auto_safe`. Edit-op taxonomy
(R-GEC-OPS, keep/delete/merge-before/replace/insert/append): INSERT/DELETE/REPLACE/MERGE/SPLIT/RETAIN/REJECT/ABSTAIN —
`retain`=leave-unchanged-acceptable, `reject`=tempting-but-unsafe, `abstain`=defer; these carry no replacement and (for
reject/abstain) a closed `reject_reason`. Overlapping applicable edits are resolved by 1D-span NMS — the loser is
surfaced as a C10 conflict (`conflicts_for`), never silently dropped.

Pure, dry-run (`live_writes`-free; never applies an edit). Source-clean: every text field passes `leak_sot.scan()`.
See parserplans/general-fusha-grammar-checker-p2b-learning-cefr/002.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import normalize_ar as N  # noqa: E402
from tools import leak_sot  # noqa: E402
from tools import fusha_conflicts as CF  # noqa: E402
from tools.fusha_check import IRAB_SENSITIVE_ISSUE_CLASSES, GATE_ALIAS  # noqa: E402
from tools.validate_linguistic_decisions import _GATE_RANK  # noqa: E402

SCHEMA = "fusha/suggestion@1"
STRUCTURAL_OPS = {"insert", "delete", "replace", "merge", "split"}
NONAPPLY_OPS = {"retain", "reject", "abstain", "none"}
_CONF_RANK = {"high": 3, "medium": 2, "low": 1}
_PROCLITIC_LETTERS = {"و", "ف", "ب", "ك", "ل"}
_IRAB_ROUTE = {"lane": "scholar_irab_review", "procedure": "nahw/procedures/irab-case-mood.md"}


def _has_harakat(s):
    return any(0x064B <= ord(c) <= 0x0652 for c in (s or ""))


def _gate(g, op):
    g = GATE_ALIAS.get(g, g)
    # structural / arbitrary suggestions can never be auto_safe.
    if op in STRUCTURAL_OPS and _GATE_RANK[g] < _GATE_RANK["two_vote_required"]:
        g = "two_vote_required"
    return g


def _mk(op, target, replacement, *, diagnostic_id, confidence, gate, explanation,
        reject_reason=None, route=None, span=None, source_locus=None):
    gate = _gate(gate, op)
    structural = op in STRUCTURAL_OPS
    safe_inline = (gate == "auto_safe") and not structural
    needs_review = (_GATE_RANK[gate] >= _GATE_RANK["human_source_review_required"]) or structural
    return {
        "diagnostic_id": diagnostic_id,
        "edit": {"op": op, "target": target, "replacement": replacement, "target_span": span, "source_locus": source_locus},
        "explanation": leak_sot.redact(explanation) if (explanation and leak_sot.is_leak(explanation)) else explanation,
        "confidence": confidence, "gate": gate,
        "safe_to_show_inline": safe_inline, "needs_review": needs_review,
        "reject_reason": reject_reason, "nms_group": None,
        "learner_level_min": None, "learner_level_max": None, "route_to": route,
    }


def _span(t):
    if t.get("start") is None or t.get("end") is None:
        return None
    return {"start": int(t["start"]), "end": int(t["end"]), "unit": "char"}


def _token_suggestions(t, td, mode):
    """Candidate suggestions for one token. Abstain-first; iʿrāb-sensitive → reject (no governor justification here)."""
    ref = "tok:%d" % t.get("index", 0)
    surface = t.get("surface", "")
    voweled = _has_harakat(surface)
    span = _span(t)
    out = []
    for d in td:
        cls = d.get("issue_class")
        did = "%s@%s" % (cls, ref)
        seg_split = _split_replacement(t)
        if cls in IRAB_SENSITIVE_ISSUE_CLASSES:
            out.append(_mk("reject", ref, None, diagnostic_id=did, confidence="medium",
                           gate="human_source_review_required", reject_reason="governor_not_justified", route=_IRAB_ROUTE,
                           span=span, explanation="A case/iʿrāb change is tempting here, but without a justified governing "
                           "element it is unsafe; routed for review rather than applied."))
        elif cls == "ambiguous_unvoweled_token":
            out.append(_mk("abstain", ref, None, diagnostic_id=did, confidence="low", gate="two_vote_required",
                           reject_reason="ambiguous_unvoweled", span=span,
                           explanation="Unvoweled — several readings compete; no correction is offered, the reading stays a candidate."))
        elif cls in ("possible_particle_function", "possible_preposition_host"):
            out.append(_mk("abstain", ref, None, diagnostic_id=did, confidence="low", gate="two_vote_required",
                           reject_reason="needs_context", span=span,
                           explanation="This depends on context that is not present; no correction is offered."))
        elif cls == "possible_clitic_segmentation" and seg_split:
            out.append(_mk("split", ref, seg_split, diagnostic_id=did, confidence="medium", gate="two_vote_required",
                           span=span, explanation="The written token appears to carry a prefixed particle; a suggested "
                           "split is shown for review, not applied."))
        elif cls == "possible_attached_pronoun":
            single = any(len(N.bare(s.get("surface", ""))) == 1 for c in (t.get("segment_candidates") or [])
                         for s in c.get("segments", []) if s.get("role") == "object_pronoun")
            if single or not seg_split:
                out.append(_mk("abstain", ref, None, diagnostic_id=did, confidence="low", gate="two_vote_required",
                               reject_reason="ambiguous_unvoweled", span=span,
                               explanation="A single-letter ending could be an attached pronoun or part of the stem; left as a candidate."))
            else:
                out.append(_mk("split", ref, seg_split, diagnostic_id=did, confidence="medium", gate="two_vote_required",
                               span=span, explanation="An attached pronoun may be present; a suggested split is shown for review."))
        elif cls == "orthography_normalization_warning":
            norm = N.norm_strict(surface)
            if norm and norm != surface:
                out.append(_mk("replace", ref, norm, diagnostic_id=did, confidence="medium", gate="two_vote_required",
                               span=span, explanation="An orthographic variant could be normalized; shown as a review hint, "
                               "the original spelling is preserved."))
    # RETAIN: a voweled token with no token-specific diagnostics reads acceptably as written.
    if not td and voweled:
        out.append(_mk("retain", ref, None, diagnostic_id=None, confidence="high", gate="two_vote_required", span=span,
                       explanation="The token reads acceptably as written; no change suggested."))
    return out


def _split_replacement(t):
    """The suggested whitespace-separated split for the first legal multi-piece segmentation, or None."""
    for c in t.get("segment_candidates") or []:
        segs = c.get("segments") or []
        if len(segs) >= 2 and not c.get("single_letter_clitic") and c.get("legal", True):
            return " ".join(s.get("surface", "") for s in segs)
    return None


def _merge_suggestions(tokens, diags_by_target):
    """A lone proclitic letter (و/ف/ب/ك/ل) immediately followed by an Arabic token → a MERGE spacing-fix hint.
    Only emitted when the lone token already carries a diagnostic (so diagnostic_id resolves in-record)."""
    out = []
    for i, t in enumerate(tokens[:-1]):
        if N.bare(t.get("surface", "")) in _PROCLITIC_LETTERS and len(N.bare(t.get("surface", ""))) == 1:
            nxt = tokens[i + 1]
            ref = "tok:%d" % t.get("index", i)
            td = diags_by_target.get(ref, [])
            if not td or not nxt.get("is_arabic"):
                continue
            joined = t.get("surface", "") + nxt.get("surface", "")
            out.append(_mk("merge", ref, joined, diagnostic_id="%s@%s" % (td[0].get("issue_class"), ref),
                           confidence="medium", gate="two_vote_required", span=_span(t),
                           explanation="These two pieces may belong to one written word; a spacing-fix is suggested for review."))
    return out


def _nms(suggestions):
    """1D-span NMS over APPLICABLE (structural) suggestions sharing a target: keep the highest-confidence, demote the
    rest to `reject`/`nms_suppressed_conflict` with a shared `nms_group`. Non-applicable suggestions pass through."""
    by_target = {}
    for s in suggestions:
        if s["edit"]["op"] in STRUCTURAL_OPS:
            by_target.setdefault(s["edit"]["target"], []).append(s)
    for target, group in by_target.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda s: -_CONF_RANK.get(s["confidence"], 0))
        gid = "nms:%s" % target
        for k, s in enumerate(group):
            s["nms_group"] = gid
            if k > 0:  # losers
                s["edit"]["op"] = "reject"
                s["edit"]["replacement"] = None
                s["reject_reason"] = "nms_suppressed_conflict"
                s["needs_review"] = True
                s["safe_to_show_inline"] = False
    return suggestions


def build_suggestions(analysis_tokens, diagnostics, input_mode):
    """Return suggestions[] for a fusha/text-check@1 record (assigned to rec['suggestions'] by check_text)."""
    diags_by_target = {}
    for d in diagnostics or []:
        diags_by_target.setdefault(d.get("target"), []).append(d)
    suggestions = []
    for t in analysis_tokens or []:
        ref = "tok:%d" % t.get("index", 0)
        suggestions.extend(_token_suggestions(t, diags_by_target.get(ref, []), input_mode))
    suggestions.extend(_merge_suggestions(analysis_tokens or [], diags_by_target))
    suggestions = _nms(suggestions)
    # final leak scrub of every text-bearing field
    for s in suggestions:
        for f in ("explanation",):
            if leak_sot.is_leak(s.get(f) or ""):
                s[f] = leak_sot.redact(s[f]); s["reject_reason"] = "leak_tripwire"; s["safe_to_show_inline"] = False
        if leak_sot.is_leak((s["edit"].get("replacement") or "")):
            s["edit"]["replacement"] = None; s["edit"]["op"] = "reject"; s["reject_reason"] = "leak_tripwire"; s["safe_to_show_inline"] = False
    return suggestions


def conflicts_for(suggestions):
    """C10 conflict records for each NMS-suppressed group (surfaces the tie; never silently dropped)."""
    groups = {}
    for s in suggestions:
        if s.get("nms_group"):
            groups.setdefault(s["nms_group"], []).append(s)
    out = []
    for gid, group in groups.items():
        if len(group) < 2:
            continue
        target = group[0]["edit"]["target"]
        readings = [{"builder": "suggestion_engine",
                     "reading": "%s edit (confidence %s)" % (s["edit"]["op"], s["confidence"]),
                     "gate": s["gate"]} for s in group]
        out.append(CF.make_conflict(target, "C10_suggestion_vs_suggestion", ["suggestion_engine"],
                                    "two overlapping edits target the same span; NMS keeps one and surfaces the rest", readings))
    return out


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def _records():
    from tools import fusha_text_check as TC  # lazy (avoids the check_text -> fusha_suggest import cycle)
    return {
        "abstain-unvoweled": TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "علم نور"}),
        "split-proclitic": TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "وبالكتابِ"}),
        "merge-lone-proclitic": TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "و الكتابُ"}),
        # tok:1 (مفيدٌ) is voweled with no token-specific diagnostic → a RETAIN (reads acceptably as written)
        "retain-clean": TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "الكتابُ مفيدٌ"}),
        # both a proclitic (و+ال → split) and an orthographic variant (آ/ة → replace) on one token → NMS surfaces a C10
        "nms-pair": TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "والآخرة"}),
    }


def _self_test():
    failures = []
    recs = _records()
    seen_ops = set()
    for name, rec in recs.items():
        sugg = build_suggestions(rec["analysis_tokens"], rec["diagnostics"], rec["input_mode"])
        for s in sugg:
            op = s["edit"]["op"]
            seen_ops.add(op)
            # never auto_safe in arbitrary mode
            if s["gate"] == "auto_safe":
                failures.append("%s: suggestion auto_safe in arbitrary mode" % name)
            # iʿrāb-sensitive / structural never auto_safe (redundant with above but explicit)
            if op in STRUCTURAL_OPS and s["gate"] == "auto_safe":
                failures.append("%s: structural suggestion auto_safe" % name)
            # retain/reject/abstain/none carry no replacement
            if op in NONAPPLY_OPS and s["edit"]["replacement"] is not None:
                failures.append("%s: %s carries a replacement" % (name, op))
            # reject/abstain/none require a reject_reason
            if op in ("reject", "abstain", "none") and not s.get("reject_reason"):
                failures.append("%s: %s lacks a reject_reason" % (name, op))
            # diagnostic_id resolves for non-retain ops
            if op != "retain":
                if not s.get("diagnostic_id"):
                    failures.append("%s: non-retain suggestion lacks diagnostic_id" % name)
            # leak-free
            if leak_sot.is_leak(s.get("explanation") or "") or leak_sot.is_leak(s["edit"].get("replacement") or ""):
                failures.append("%s: suggestion leaks" % name)
        # conflicts for NMS groups validate-shaped
        for c in conflicts_for(sugg):
            if c.get("gate_required") == "auto_safe" or c.get("live_writes") != 0:
                failures.append("%s: NMS conflict malformed" % name)
    # coverage: the engine exercises abstain, split, merge, retain, reject across the fixtures
    need_ops = {"abstain", "split", "merge", "retain", "reject"}
    missing = need_ops - seen_ops
    if missing:
        failures.append("fixtures do not exercise ops: %s" % sorted(missing))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_suggest self-test: abstain-first; never auto_safe; retain/reject/abstain no-replacement; NMS surfaces C10; source-clean")
    return 0 if not failures else 1


def emit_fixture(path):
    recs = _records()
    rows = []
    for name, rec in recs.items():
        sugg = build_suggestions(rec["analysis_tokens"], rec["diagnostics"], rec["input_mode"])
        rows.append({"case": name, "input_mode": rec["input_mode"], "suggestions": sugg,
                     "conflicts": conflicts_for(sugg)})
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {"schema": SCHEMA, "generator": "tools/fusha_suggest.py --emit-fixture", "count": len(rows),
            "note": "Edit-level suggestion fixtures (authored arbitrary inputs). Abstain-first; never auto_safe; "
                    "retain/reject/abstain carry no replacement; NMS surfaces a C10 conflict. Source-clean; dry-run.",
            "row_schema": ["case", "input_mode", "suggestions", "conflicts"]}
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d suggestion cases -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Edit-level suggestion engine (abstain-first, dry-run).")
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
