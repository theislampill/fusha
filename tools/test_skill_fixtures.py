#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Permanent RED-FIRST skill fixtures from the 141-example bank (gate 9).

Each fixture in tools/skill_fixtures/skill_fixtures.jsonl cites its example_id + rule_id and carries a
deterministic `case`. For every fixture we run BOTH the corrected rule and the superseded rule it replaced
(tools/skill_fixtures/skill_rules.py):

  GREEN     : corrected_rule(case) == correct_label                      (the fix holds)
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label
              (the pre-fix behaviour reproduces the bug, so a test asserting the correct label FAILS
               against the superseded behaviour and PASSES against the corrected behaviour)

No server, no MCP, no network. Deterministic. Fails closed (exit 1) on any violation.
"""
import io
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.skill_fixtures import skill_rules as R  # noqa: E402

FIXTURES = os.path.join(ROOT, "tools", "skill_fixtures", "skill_fixtures.jsonl")

# The phenomena the gate REQUIRES to be covered by a permanent red-first fixture.
REQUIRED_PHENOMENA = {
    "adjacency-not-ownership",          # adjacent-token ownership misbinding
    "affirm-live",                      # affirm_live as a valid disposition
    "rootless-noun-convention",         # root-less noun ownership boundary
    "function-word-routing",            # function-word vs content-root routing
    "diacritic-homograph",              # harakah conflict + مِنْ/مَنْ + أنْ/أنَّ
    "ma-lam-family-subfunction",        # لا/ما function alternatives (family-label-not-a-resolution)
    "governor-locality",                # qg-lam blocked-for-insufficient-exemplars
    "morphline-authoring",              # morphline no-placeholder
    "mabni-fi-mahall",                  # case/maḥall abstention
    "source-address-ref-fidelity",      # source-address reference fidelity
    "ma-family-relative-vs-negation",   # 5:116:33 relative مَا not negation
    "dependent-binding-reeval",         # correction/supersedes propagation
    "certified-retain-both",            # أنْ المخففة vs conditional/maṣdariyya (retain-both alternatives)
    "idafa-mabni-fi-mahall",            # iḍāfa mabnī fi maḥall abstention
}


def main():
    fixtures = [json.loads(l) for l in io.open(FIXTURES, encoding="utf-8") if l.strip()]
    fails = []
    seen_phenomena = set()
    seen_rules = set()
    redfirst_count = 0
    ma5116_proven = False

    for fx in fixtures:
        fid = fx["fixture_id"]
        rule = fx["rule"]
        case = fx["case"]
        seen_phenomena.add(fx["phenomenon"])
        seen_rules.add(rule)

        # provenance: every fixture must cite a real example_id + rule_id
        if not fx.get("example_id"):
            fails.append("%s: missing example_id citation" % fid)
        if not fx.get("rule_id"):
            fails.append("%s: missing rule_id citation" % fid)

        if rule not in R.CORRECTED or rule not in R.SUPERSEDED:
            fails.append("%s: no corrected/superseded rule registered for '%s'" % (fid, rule))
            continue

        corrected = R.CORRECTED[rule](case)
        superseded = R.SUPERSEDED[rule](case)

        # GREEN: the corrected rule yields the correct label.
        if corrected != fx["correct_label"]:
            fails.append("%s: corrected rule -> %r, expected %r (GREEN failed)"
                         % (fid, corrected, fx["correct_label"]))

        if fx.get("redfirst"):
            redfirst_count += 1
            # RED-FIRST arm 1: the superseded rule faithfully reproduces the documented wrong label.
            if superseded != fx["wrong_label"]:
                fails.append("%s: superseded rule -> %r, expected wrong_label %r (bug not reproduced)"
                             % (fid, superseded, fx["wrong_label"]))
            # RED-FIRST arm 2: that wrong label diverges from the correct one, so a correct-asserting
            # test is genuinely RED under the superseded behaviour.
            if superseded == fx["correct_label"]:
                fails.append("%s: superseded label == correct label -> NOT red-first" % fid)
            proof = "  RED-FIRST %-40s superseded=%r  ->  corrected=%r  [%s / %s]" % (
                fid, superseded, corrected, fx["example_id"], fx["rule_id"])
            print(proof)
            if fid == "test_ma_family_relative_not_negation":
                # the mandated 5:116:33 fixture must be red against 'not'/qg-negation, green on 'what'/qg-ma-particle
                if (superseded == "qg-negation" and corrected == "qg-ma-particle"
                        and fx["correct_label"] == "qg-ma-particle"):
                    ma5116_proven = True
        else:
            # green-only control (e.g. genuine-negation / correct-ref): corrected must still hold.
            print("  GREEN-CTRL %-40s corrected=%r  [%s / %s]" % (
                fid, corrected, fx["example_id"], fx["rule_id"]))

    # coverage: every required phenomenon has at least one fixture.
    missing = REQUIRED_PHENOMENA - seen_phenomena
    for m in sorted(missing):
        fails.append("MISSING required phenomenon fixture: %s" % m)

    if not ma5116_proven:
        fails.append("5:116:33 fixture (test_ma_family_relative_not_negation) not red-first-proven "
                     "(must fail on qg-negation/'not', pass on qg-ma-particle/'what')")

    print("\nskill fixtures: %d total, %d red-first, %d phenomena, %d discriminators"
          % (len(fixtures), redfirst_count, len(seen_phenomena), len(seen_rules)))
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS - every fixture is green on the corrected rule and red-first against the superseded rule; "
          "5:116:33 relative-مَا-not-negation proven; all required phenomena covered.")


if __name__ == "__main__":
    main()
