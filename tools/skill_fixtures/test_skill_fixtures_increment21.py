#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED-FIRST + NON-CONSTANT-DISCRIMINATOR harness for the INCREMENT-21 skill fixtures
(candidate sarf@2.1 / nahw@2.1).

For every fixture in skill_fixtures_increment21.jsonl we run BOTH the corrected candidate rule and
the superseded rule it replaces (skill_rules_increment21.py):

  GREEN     : corrected_rule(case) == correct_label                      (the fix holds)
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label
              (the pre-fix calibration defect is reproduced)

NON-CONSTANT-DISCRIMINATOR guard (the known SEND-BACK class): for EACH rule, the CORRECTED
discriminator must return >=2 DISTINCT labels across that rule's fixtures — i.e. the rule genuinely
branches on its input rather than returning a constant that happens to match. Every rule therefore
ships a positive (red-first) fixture AND a boundary/control fixture that the same corrected rule maps
to a different label.

Also asserts: every candidate @2.1 rule_id in rule-registry-increment-21.jsonl is covered by >=1
red-first fixture; the increment builder is regeneration-clean; and the loc-integrity family carries
both a mismatch find and the impossible-address find.

No server, no MCP, no network. Deterministic. Fails closed (exit 1) on any violation.
"""
import io
import json
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import skill_rules_increment21 as R  # noqa: E402

FIXTURES = os.path.join(HERE, "skill_fixtures_increment21.jsonl")
REGISTRY_INC = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-21.jsonl")
BUILDER = os.path.join(HERE, "_build_increment21.py")

# The loc-integrity family must carry both a mismatch and the impossible-address find.
REQUIRED_LOC_LABELS = {"fail_closed_reroute_addressing", "fail_closed_impossible_address"}


def main():
    fixtures = [json.loads(l) for l in io.open(FIXTURES, encoding="utf-8") if l.strip()]
    reg_ids = {json.loads(l)["skill_rule_id"]
               for l in io.open(REGISTRY_INC, encoding="utf-8") if l.strip()}
    fails = []
    redfirst_count = 0
    corrected_labels_by_rule = {}     # rule_key -> set(labels) for the non-constant guard
    redfirst_rule_ids = set()
    loc_labels = set()

    for fx in fixtures:
        fid = fx["fixture_id"]
        rule = fx["rule"]
        case = fx["case"]

        if not fx.get("example_id"):
            fails.append("%s: missing example_id" % fid)
        if not fx.get("rule_id"):
            fails.append("%s: missing rule_id" % fid)

        if rule not in R.CORRECTED or rule not in R.SUPERSEDED:
            fails.append("%s: no corrected/superseded rule registered for '%s'" % (fid, rule))
            continue

        corrected = R.CORRECTED[rule](case)
        superseded = R.SUPERSEDED[rule](case)
        corrected_labels_by_rule.setdefault(rule, set()).add(corrected)

        # GREEN: the corrected candidate rule yields the correct label.
        if corrected != fx["correct_label"]:
            fails.append("%s: corrected -> %r, expected %r (GREEN failed)"
                         % (fid, corrected, fx["correct_label"]))

        if fx.get("redfirst"):
            redfirst_count += 1
            redfirst_rule_ids.add(fx.get("rule_id"))
            if superseded != fx.get("wrong_label"):
                fails.append("%s: superseded -> %r, expected wrong_label %r (defect not reproduced)"
                             % (fid, superseded, fx.get("wrong_label")))
            if superseded == fx["correct_label"]:
                fails.append("%s: superseded label == correct label -> NOT red-first" % fid)
            tag = "RED-FIRST"
        else:
            tag = "BRANCH-CTL"

        if fx.get("rule_id", "").startswith("sarf-loc-integrity"):
            loc_labels.add(corrected)

        print("  %-10s %-40s corrected=%-40r [%s]" % (tag, fid, corrected, fx.get("rule_id")))

    # NON-CONSTANT guard: every rule's corrected discriminator returns >=2 distinct labels.
    for rule, labels in sorted(corrected_labels_by_rule.items()):
        if len(labels) < 2:
            fails.append("CONSTANT DISCRIMINATOR (send-back class): rule '%s' corrected returns only %r"
                         % (rule, sorted(labels)))

    # coverage: every registry @2.1 rule_id has a red-first fixture.
    for rid in sorted(reg_ids - redfirst_rule_ids):
        fails.append("MISSING red-first fixture for candidate @2.1 rule: %s" % rid)
    for rid in sorted(redfirst_rule_ids - reg_ids):
        fails.append("fixture rule_id %s not present in rule-registry-increment-21.jsonl" % rid)

    # loc-integrity family carries mismatch + impossible finds.
    for lbl in sorted(REQUIRED_LOC_LABELS - loc_labels):
        fails.append("loc-integrity family missing required find label: %s" % lbl)

    # builder is regeneration-clean (committed artifacts == regenerated).
    chk = subprocess.run([sys.executable, BUILDER, "--check"], capture_output=True, text=True)
    if chk.returncode != 0:
        fails.append("increment-21 builder --check FAILED: %s" % (chk.stdout.strip() or chk.stderr.strip()))

    print("\nincrement-21 fixtures: %d total, %d red-first, %d rules, %d registry ids covered"
          % (len(fixtures), redfirst_count, len(corrected_labels_by_rule), len(redfirst_rule_ids & reg_ids)))
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS - every fixture green on the corrected @2.1 rule + red-first against the superseded rule; "
          "every corrected discriminator branches (non-constant); all %d @2.1 registry rules covered; "
          "loc-integrity mismatch+impossible finds present; builder regeneration-clean." % len(reg_ids))


if __name__ == "__main__":
    main()
