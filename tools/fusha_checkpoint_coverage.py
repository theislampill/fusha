#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_checkpoint_coverage — REPORT (never fabricate) the coverage of a checkpoint answer-key bank (criticism 3).

The criticism is that the assessment bank is "too small and uneven". The honest response is to MEASURE it, not to
mass-generate filler rows (templated auto-generation = fake coverage; deep-research anti-pattern). This tool:
  * counts rows by roadmap level, by hard-grammar vs objective, and by remediation-route presence;
  * names the roadmap levels (1-12, from curriculum/mastery-checkpoints.md) that have ZERO checkpoint rows;
  * flags over-/under-weighted bands;
  * REFERENTIAL CHECK: every cited sarf_procedure / nahw_procedure / remediation_route path must exist on disk
    (a dangling citation is a real defect — the only thing that FAILs by default).

It authors NOTHING. Filling empty bands is owner-reviewable authoring (scripture-adjacent), tracked as P1 — see
parserplans/fusha-data-runtime-completion-pass/004. Stdlib only; dry-run. CLI: <bank.jsonl> [--strict-bands] | --self-test.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ROADMAP_LEVELS = list(range(1, 13))  # mastery-checkpoints.md defines pass bars for levels 1..12


def _levels(value):
    return [int(m) for m in re.findall(r"\d+", str(value))]


def coverage(rows, repo_root=_REPO):
    by_level = Counter()
    hard = 0
    with_route = 0
    missing_paths = []
    for r in rows:
        for L in _levels(r.get("level", "")):
            by_level[L] += 1
        if r.get("two_vote_required"):
            hard += 1
        if r.get("remediation_route"):
            with_route += 1
        for field in ("sarf_procedure", "nahw_procedure", "remediation_route"):
            p = r.get(field)
            if p and not os.path.exists(os.path.join(repo_root, p)):
                missing_paths.append({"id": r.get("id"), "field": field, "path": p})
    empty_bands = [L for L in ROADMAP_LEVELS if by_level.get(L, 0) == 0]
    total = len(rows)
    # a band is "thin" if a covered level has only 1 row; "heavy" if it holds >35% of all rows.
    # ALL band lists iterate ROADMAP_LEVELS so an out-of-roadmap level (e.g. 99) can never leak into a band.
    thin = [L for L in ROADMAP_LEVELS if by_level.get(L, 0) == 1]
    heavy = [L for L in ROADMAP_LEVELS if total and by_level.get(L, 0) / total > 0.35]
    # rows whose level is missing or entirely outside 1-12 are counted in total but binned in NO roadmap band;
    # surface them so the report reconciles (band presence + out_of_roadmap accounts for every row).
    out_of_roadmap = sum(1 for r in rows if not any(1 <= L <= 12 for L in _levels(r.get("level", ""))))
    return {"total": total, "by_level": {L: by_level.get(L, 0) for L in ROADMAP_LEVELS},
            "hard_grammar_rows": hard, "objective_rows": total - hard, "rows_with_remediation_route": with_route,
            "empty_bands": empty_bands, "thin_bands": thin, "heavy_bands": heavy,
            "out_of_roadmap": out_of_roadmap, "missing_paths": missing_paths}


def render(cov):
    lines = ["checkpoint coverage report", "  total rows: %d (hard-grammar %d / objective %d)"
             % (cov["total"], cov["hard_grammar_rows"], cov["objective_rows"]),
             "  by level (1-12): " + ", ".join("L%d=%d" % (L, cov["by_level"][L]) for L in ROADMAP_LEVELS),
             "  empty bands: %s" % (cov["empty_bands"] or "none"),
             "  thin bands (1 row): %s" % (cov["thin_bands"] or "none"),
             "  heavy bands (>35%% of rows): %s" % (cov["heavy_bands"] or "none"),
             "  rows outside roadmap levels 1-12: %d" % cov.get("out_of_roadmap", 0),
             "  rows with a remediation route: %d/%d" % (cov["rows_with_remediation_route"], cov["total"]),
             "  dangling cited paths: %d" % len(cov["missing_paths"])]
    for m in cov["missing_paths"]:
        lines.append("    MISSING %s.%s -> %s" % (m["id"], m["field"], m["path"]))
    lines.append("  note: counts are item PRESENCE, not difficulty-equivalence; fill empty bands by AUTHORING +"
                 " human review, never by templated generation (isomorphic variants drift in difficulty — AIG evidence).")
    return "\n".join(lines)


def _load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _self_test():
    failures = []
    # clean bank: covers L1 + L7 hard, cites only existing paths -> 0 missing, L7 covered, others empty
    clean = [
        {"id": "c1", "level": "1", "two_vote_required": False, "remediation_route": "README.md",
         "sarf_procedure": None, "nahw_procedure": None},
        {"id": "c2", "level": "7", "two_vote_required": True, "remediation_route": "README.md",
         "sarf_procedure": None, "nahw_procedure": "AGENTS.md"},
    ]
    cov = coverage(clean)
    if cov["missing_paths"]:
        failures.append("clean bank reported missing paths: %s" % cov["missing_paths"])
    if 1 in cov["empty_bands"] or 7 in cov["empty_bands"]:
        failures.append("covered levels 1/7 wrongly flagged empty")
    if 6 not in cov["empty_bands"] or 12 not in cov["empty_bands"]:
        failures.append("uncovered levels 6/12 not flagged empty")
    if cov["hard_grammar_rows"] != 1:
        failures.append("hard-grammar count wrong: %s" % cov["hard_grammar_rows"])

    # dangling-path bank: a cited route that does not exist must be caught
    dangling = [{"id": "d1", "level": "3", "two_vote_required": False,
                 "remediation_route": "curriculum/does/not/exist.md", "sarf_procedure": None, "nahw_procedure": None}]
    if not coverage(dangling)["missing_paths"]:
        failures.append("a dangling cited path was not caught")

    # out-of-roadmap / malformed input: heavy_bands must NEVER leak a non-roadmap level, and out_of_roadmap must
    # count rows that have no roadmap-1-12 level (so the report reconciles with total instead of silently dropping them)
    odd = [{"id": "NOLVL"}, {"id": "L99", "level": "99"}, {"id": "ok", "level": "3"}]
    ocov = coverage(odd)
    if any(L not in ROADMAP_LEVELS for L in ocov["heavy_bands"]):
        failures.append("heavy_bands leaked an out-of-roadmap level: %s" % ocov["heavy_bands"])
    if ocov["out_of_roadmap"] != 2:
        failures.append("out_of_roadmap should count the 2 unbinned rows, got %s" % ocov["out_of_roadmap"])

    # the SHIPPED sample must have 0 dangling paths (a real regression guard)
    sample = os.path.join(_REPO, "curriculum", "assessment", "level-checkpoints.sample.jsonl")
    if os.path.exists(sample):
        scov = coverage(_load(sample))
        if scov["missing_paths"]:
            failures.append("shipped sample cites missing paths: %s" % scov["missing_paths"][:3])

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_checkpoint_coverage self-test: counts by level/hardness/route; empty+thin+heavy bands "
              "(in-roadmap only); out_of_roadmap reconciles; dangling-citation detection; shipped sample 0 dangling")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Report checkpoint bank coverage + cited-path integrity (no generation).")
    ap.add_argument("bank", nargs="?", help="checkpoint JSONL")
    ap.add_argument("--strict-bands", action="store_true", help="also exit non-zero if any roadmap level is empty")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.bank:
        ap.error("provide a checkpoint JSONL path or --self-test")
    cov = coverage(_load(a.bank))
    print(render(cov))
    rc = 1 if cov["missing_paths"] else 0           # a dangling citation always fails
    if a.strict_bands and cov["empty_bands"]:
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
