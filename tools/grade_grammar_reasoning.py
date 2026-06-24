#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grade a grammar answer on BOTH final answer and reasoning — the GrammarProblems lesson made executable.

The paper's core finding: a model can give the right final answer for the WRONG reason (or a confident wrong
answer). For our pipeline that is unsafe — a correct-looking grammar answer with bad reasoning must NOT export to
a hover gloss or an entry repair. So a grammar-affecting decision passes only when ALL hold:

    final_ok       final answer matches expected
    reasoning_ok   reasoning cites the correct rule/iʿrāb path (not a wrong path that happens to land right)
    evidence_ok    an evidence rung + source-address is cited
    gate_ok        two-vote present when the case requires it

grade() is deterministic over supplied judgments (the model/verifier supplies final/reasoning judgments; this
module enforces the AND-gate). The CLI runs a self-test proving the load-bearing case — right answer + wrong
reasoning => FAIL — and exits non-zero if that property ever breaks.
"""
import sys


def grade(case, judgment):
    """case: an eval case dict (has required_gate). judgment: {final_ok, reasoning_ok, evidence_cited,
    source_address, two_vote_done}. Returns {..., 'pass': bool, 'block_reason': str|None}."""
    final_ok = bool(judgment.get("final_ok"))
    reasoning_ok = bool(judgment.get("reasoning_ok"))
    evidence_ok = bool(judgment.get("evidence_cited")) and bool(judgment.get("source_address"))
    needs_two_vote = case.get("required_gate") in ("two_vote_required", "human_source_review_required")
    gate_ok = (not needs_two_vote) or bool(judgment.get("two_vote_done"))
    never_auto = case.get("required_gate") == "never_auto"
    ok = final_ok and reasoning_ok and evidence_ok and gate_ok and not never_auto
    reason = None
    if not ok:
        if never_auto:
            reason = "never_auto: human source review required"
        elif not final_ok:
            reason = "final answer wrong"
        elif not reasoning_ok:
            reason = "reasoning wrong (right answer, wrong path => unsafe)"
        elif not evidence_ok:
            reason = "missing evidence rung or source-address"
        elif not gate_ok:
            reason = "two-vote gate required but not done"
    return {"final_ok": final_ok, "reasoning_ok": reasoning_ok, "evidence_ok": evidence_ok,
            "gate_ok": gate_ok, "pass": ok, "block_reason": reason}


def _selftest():
    case_tv = {"id": "t1", "required_gate": "two_vote_required"}
    case_auto = {"id": "t2", "required_gate": "auto_safe"}
    cases = [
        # (case, judgment, expected_pass)
        (case_auto, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x"}, True),
        # THE load-bearing case: right final answer, WRONG reasoning -> must FAIL
        (case_auto, {"final_ok": True, "reasoning_ok": False, "evidence_cited": True, "source_address": "x"}, False),
        # confident wrong answer -> FAIL
        (case_auto, {"final_ok": False, "reasoning_ok": True, "evidence_cited": True, "source_address": "x"}, False),
        # two-vote required but not done -> FAIL even if everything else right
        (case_tv, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x",
                   "two_vote_done": False}, False),
        (case_tv, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x",
                   "two_vote_done": True}, True),
        # missing source-address -> FAIL
        (case_auto, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": ""}, False),
    ]
    bad = 0
    for i, (c, j, exp) in enumerate(cases, 1):
        r = grade(c, j)
        if r["pass"] != exp:
            bad += 1
            print("  self-test %d FAIL: expected pass=%s got %s (%s)" % (i, exp, r["pass"], r["block_reason"]))
    if bad:
        print("FAIL: %d self-test case(s) broke the AND-gate" % bad); sys.exit(1)
    print("PASS — grade() AND-gate holds (right answer + wrong reasoning correctly FAILS; %d cases)" % len(cases))


if __name__ == "__main__":
    _selftest()
