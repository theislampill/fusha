#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED-FIRST harness for the QAMUS-RICH-SEG-001 skill fixtures (candidate @2).

Companion to test_skill_fixtures.py, kept SEPARATE so it does not collide with the in-flight
skill-fixtures integration. Merges alongside it at release.

For every fixture in skill_fixtures_richseg.jsonl we run BOTH the corrected candidate rule and the
superseded rule it replaces (skill_rules_richseg.py):

  GREEN     : corrected_rule(case) == correct_label                      (the fix holds)
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label
              (the pre-fix behaviour reproduces the documented defect, so a test asserting the
               correct label FAILS against the superseded behaviour and PASSES against the corrected one)

Also asserts: every candidate @2 rule_id is covered by >=1 red-first fixture, and BOTH
over-segmentation boundary negatives (4:144:17 مبينا, 102:3:3 تعلمون) are present.

No server, no MCP, no network. Deterministic. Fails closed (exit 1) on any violation.
"""
import io
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skill_rules_richseg as R  # noqa: E402

FIXTURES = os.path.join(HERE, "skill_fixtures_richseg.jsonl")

# The 9 candidate @2 rule_ids that MUST each be covered by at least one red-first fixture.
REQUIRED_RULE_IDS = {
    "sarf-richseg-mudari-prefix-own-segment",
    "sarf-richseg-derived-nominal-exposes-root",
    "sarf-richseg-attached-pronoun-subject-marker-own-segment",
    "sarf-richseg-occurrence-voice-mood-aspect-form-committed",
    "sarf-richseg-no-oversegmentation-boundary",
    "nahw-richseg-imperative-lam-governor-jussive-segment",
    "nahw-richseg-negation-owned-by-particle",
    "nahw-richseg-verb-shaped-triliteral-is-content",
    "nahw-richseg-attached-pronoun-irab-role-per-occurrence",
}
# The two over-segmentation boundary negatives that must be present.
REQUIRED_BOUNDARY_LOCS = {"4:144:17", "102:3:3"}


def main():
    fixtures = [json.loads(l) for l in io.open(FIXTURES, encoding="utf-8") if l.strip()]
    fails = []
    seen_rule_ids = set()
    seen_boundary_locs = set()
    redfirst_count = 0

    for fx in fixtures:
        fid = fx["fixture_id"]
        rule = fx["rule"]
        case = fx["case"]
        seen_rule_ids.add(fx.get("rule_id"))
        for loc in fx.get("canonical_locations", []):
            if loc in REQUIRED_BOUNDARY_LOCS:
                seen_boundary_locs.add(loc)

        if not fx.get("example_id"):
            fails.append("%s: missing example_id citation" % fid)
        if not fx.get("rule_id"):
            fails.append("%s: missing rule_id citation" % fid)

        if rule not in R.CORRECTED or rule not in R.SUPERSEDED:
            fails.append("%s: no corrected/superseded rule registered for '%s'" % (fid, rule))
            continue

        corrected = R.CORRECTED[rule](case)
        superseded = R.SUPERSEDED[rule](case)

        # GREEN: the corrected candidate rule yields the correct label.
        if corrected != fx["correct_label"]:
            fails.append("%s: corrected rule -> %r, expected %r (GREEN failed)"
                         % (fid, corrected, fx["correct_label"]))

        if fx.get("redfirst"):
            redfirst_count += 1
            if superseded != fx["wrong_label"]:
                fails.append("%s: superseded rule -> %r, expected wrong_label %r (defect not reproduced)"
                             % (fid, superseded, fx["wrong_label"]))
            if superseded == fx["correct_label"]:
                fails.append("%s: superseded label == correct label -> NOT red-first" % fid)
            print("  RED-FIRST %-34s superseded=%-32r -> corrected=%-28r [%s / %s]"
                  % (fid, superseded, corrected, fx["example_id"], fx["rule_id"]))
        else:
            print("  GREEN-CTRL %-34s corrected=%r [%s / %s]"
                  % (fid, corrected, fx["example_id"], fx["rule_id"]))

    missing_rules = REQUIRED_RULE_IDS - seen_rule_ids
    for m in sorted(missing_rules):
        fails.append("MISSING red-first fixture for candidate @2 rule: %s" % m)

    missing_boundary = REQUIRED_BOUNDARY_LOCS - seen_boundary_locs
    for m in sorted(missing_boundary):
        fails.append("MISSING over-segmentation boundary negative for loc: %s" % m)

    print("\nrichseg skill fixtures: %d total, %d red-first, %d rule_ids covered, %d/2 boundary negatives"
          % (len(fixtures), redfirst_count, len(seen_rule_ids & REQUIRED_RULE_IDS), len(seen_boundary_locs)))
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS - every fixture is green on the corrected candidate rule and red-first against the "
          "superseded rule; all 9 candidate @2 rules covered; both boundary negatives present.")


if __name__ == "__main__":
    main()
