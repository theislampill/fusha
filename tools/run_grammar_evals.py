#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the GrammarProblems-derived eval bank — structure + gate-consistency gate, and a coverage scoreboard.

GrammarProblems.pdf showed that general-model naḥw answers can look confident while failing, especially at
intermediate/advanced/deep levels. We do NOT copy its questions; we encode its DIMENSIONS as executable gates.
This runner fails closed if:
  - any case is missing a required field or uses an out-of-vocabulary level/bloom/format/depth;
  - a grammar-AFFECTING topic does not declare a strict enough required_gate
    (such cases must be two_vote_required or never_auto — never auto_safe);
  - hover_safety and required_gate disagree.

A failing eval BLOCKS export: tools/check_regressions.py asserts this runner is green, and
validate_linguistic_decisions enforces the same gate vocabulary on real decisions.

Writes nahw/evals/grammar-problems-scoreboard.md. Exit 0 = all pass.
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(ROOT, "nahw", "evals", "grammar-problems-derived-eval.jsonl")
SCORE = os.path.join(ROOT, "nahw", "evals", "grammar-problems-scoreboard.md")

LEVELS = {"ajurrumiyyah", "qatr_al_nada", "awdah_al_masalik"}
BLOOM = {"recall", "understanding", "application", "analysis", "evaluation", "generation"}
FORMAT = {"objective", "essay"}
DEPTH = {"direct", "deep"}
GATES = {"auto_safe", "two_vote_required", "human_source_review_required", "never_auto"}
REQUIRED = {"id", "level", "bloom", "format", "depth", "topic", "question_ar", "question_en",
            "expected_answer", "expected_reasoning", "hover_safety", "required_gate"}
# grammar-affecting topics: a wrong call here changes a gloss/iʿrāb -> may NEVER be auto_safe
GRAMMAR_AFFECTING = {
    "building_present_verb", "signs_of_irab", "mubtada_khabar", "zanna_and_sisters", "maful_li_ajlih",
    "maful_mutlaq", "la_nafiyah_lil_jins", "kana_and_sisters", "istithna", "passive_agent_transformation",
    "mamnu_min_al_sarf", "hal", "badal", "tamyiz", "idafa", "jar_majrur", "tanazu", "ism_fail_maful_operation",
    "nima_bisa", "ikhtisas",
}


def main():
    if not os.path.exists(EVAL):
        print("MISSING eval bank:", os.path.relpath(EVAL, ROOT)); sys.exit(2)
    cases = []
    errors = []
    for n, ln in enumerate(open(EVAL, encoding="utf-8"), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            c = json.loads(ln)
        except Exception as e:
            errors.append("line %d: bad JSON (%s)" % (n, e)); continue
        cases.append(c)
        miss = REQUIRED - set(c)
        if miss:
            errors.append("%s: missing %s" % (c.get("id", "line%d" % n), sorted(miss))); continue
        if c["level"] not in LEVELS: errors.append("%s: bad level %s" % (c["id"], c["level"]))
        if c["bloom"] not in BLOOM: errors.append("%s: bad bloom %s" % (c["id"], c["bloom"]))
        if c["format"] not in FORMAT: errors.append("%s: bad format %s" % (c["id"], c["format"]))
        if c["depth"] not in DEPTH: errors.append("%s: bad depth %s" % (c["id"], c["depth"]))
        if c["required_gate"] not in GATES: errors.append("%s: bad gate %s" % (c["id"], c["required_gate"]))
        if c["hover_safety"] not in {"auto_safe", "two_vote_required", "never_auto"}:
            errors.append("%s: bad hover_safety %s" % (c["id"], c["hover_safety"]))
        # the core principle (aligned with nahw/rules/two-vote-required-rules.json): a grammar-affecting decision
        # at analysis+ / deep / essay forces two-vote and may NEVER be auto_safe. Recall/understanding/application
        # direct-objective knowledge facts may be auto_safe.
        strict = (c.get("bloom") in {"analysis", "evaluation", "generation"}
                  or c.get("depth") == "deep" or c.get("format") == "essay")
        if c.get("topic") in GRAMMAR_AFFECTING and strict and c.get("required_gate") == "auto_safe":
            errors.append("%s: grammar-affecting topic %s at %s/%s/%s requires >= two_vote (got auto_safe)"
                          % (c["id"], c["topic"], c["bloom"], c["depth"], c["format"]))
        if c.get("hover_safety") == "auto_safe" and c.get("required_gate") != "auto_safe":
            errors.append("%s: hover_safety auto_safe but required_gate=%s (disagree)"
                          % (c["id"], c["required_gate"]))

    ids = [c.get("id") for c in cases if c.get("id")]
    if len(set(ids)) != len(ids):
        dup = [i for i, n in collections.Counter(ids).items() if n > 1]
        errors.append("duplicate ids: %s" % dup)

    # GrammarProblems load-bearing property, exercised on REAL content: every case carrying a
    # wrong_reasoning_trap (a plausible path that lands on the right final answer for the wrong reason)
    # MUST be blocked by the grader when reasoning_ok is False — a right answer with wrong reasoning is unsafe.
    from grade_grammar_reasoning import grade
    wr_cases = [c for c in cases if c.get("wrong_reasoning_trap")]
    for c in wr_cases:
        # simulate the failure mode: final answer correct, reasoning is the trap (wrong), evidence + 2-vote present
        r = grade(c, {"final_ok": True, "reasoning_ok": False, "evidence_cited": True,
                      "source_address": "quran:demo", "two_vote_done": True})
        if r["pass"]:
            errors.append("%s: wrong_reasoning_trap NOT blocked (right answer + wrong reasoning passed!)" % c["id"])
        # and the honest version (correct reasoning) must pass the gate
        r2 = grade(c, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True,
                       "source_address": "quran:demo", "two_vote_done": True})
        if not r2["pass"]:
            errors.append("%s: correct-reasoning version unexpectedly blocked (%s)" % (c["id"], r2["block_reason"]))
    print("wrong_reasoning_trap cases exercised: %d (each must FAIL on wrong reasoning, PASS on right)" % len(wr_cases))

    # scoreboard
    by_level = collections.Counter(c.get("level") for c in cases)
    by_bloom = collections.Counter(c.get("bloom") for c in cases)
    by_topic = collections.Counter(c.get("topic") for c in cases)
    by_gate = collections.Counter(c.get("required_gate") for c in cases)
    by_depth = collections.Counter(c.get("depth") for c in cases)
    L = ["# GrammarProblems-derived eval — scoreboard", "",
         "Original/isomorphic cases (NOT copied). Generator/gate: `tools/run_grammar_evals.py`. "
         "A grammar-affecting decision is unsafe unless final answer AND reasoning AND evidence-ladder AND "
         "source-address AND two-vote(when required) all pass (`tools/grade_grammar_reasoning.py`).", "",
         "| metric | value |", "|---|---:|",
         "| total cases | **%d** | (target >= 72)" % len(cases),
         "| structure/gate errors | **%d** |" % len(errors), "",
         "## By level", "", "| level | n |", "|---|---:|"]
    for k in sorted(by_level): L.append("| %s | %d |" % (k, by_level[k]))
    L += ["", "## By Bloom level", "", "| bloom | n |", "|---|---:|"]
    for k in sorted(by_bloom): L.append("| %s | %d |" % (k, by_bloom[k]))
    L += ["", "## By depth / gate", "", "| dim | n |", "|---|---:|"]
    for k in sorted(by_depth): L.append("| depth:%s | %d |" % (k, by_depth[k]))
    for k in sorted(by_gate): L.append("| gate:%s | %d |" % (k, by_gate[k]))
    L += ["", "## Topic coverage", "", "| topic | n | grammar-affecting |", "|---|---:|:--:|"]
    for k in sorted(by_topic):
        L.append("| %s | %d | %s |" % (k, by_topic[k], "yes" if k in GRAMMAR_AFFECTING else ""))
    missing_topics = sorted(GRAMMAR_AFFECTING - set(by_topic))
    L += ["", "## Uncovered grammar-affecting topics", "",
          ("none — all %d covered" % len(GRAMMAR_AFFECTING)) if not missing_topics else ", ".join(missing_topics)]
    os.makedirs(os.path.dirname(SCORE), exist_ok=True)
    open(SCORE, "w", encoding="utf-8").write("\n".join(L) + "\n")

    print("cases=%d errors=%d levels=%s gates=%s" % (len(cases), len(errors), dict(by_level), dict(by_gate)))
    if errors:
        print("FAIL:")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    if len(cases) < 72:
        print("FAIL: only %d cases (need >= 72)" % len(cases)); sys.exit(1)
    print("PASS — %d cases, structure + gate-consistency OK; scoreboard -> %s"
          % (len(cases), os.path.relpath(SCORE, ROOT)))


if __name__ == "__main__":
    main()
