#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED-FIRST + NON-CONSTANT-DISCRIMINATOR harness for the INCREMENT-23 skill fixtures
(candidate sarf@2.3 / nahw@2.3 — the Window-1-2026-07-16 measured flywheel increment).

For every fixture in skill_fixtures_increment23.jsonl we run BOTH the corrected candidate rule and the
superseded rule it replaces (skill_rules_increment23.py):

  GREEN     : corrected_rule(case) == correct_label                      (the fix holds)
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label
              (the pre-fix Window-1 defect — wrong join root / false hold / index-skew smear /
               empty segment gloss / asymmetric no_match — is reproduced)

NON-CONSTANT-DISCRIMINATOR guard (the SEND-BACK class, now a harness gate): for EACH rule, the
CORRECTED discriminator must return >=2 DISTINCT labels across that rule's fixtures — i.e. the rule
genuinely branches on its input rather than returning a constant that happens to match. Every rule
therefore ships >=1 positive (red-first) fixture AND a boundary/control fixture the same corrected rule
maps to a different label.

Also asserts: every candidate @2.3 rule_id in rule-registry-increment-23.jsonl is covered by >=1
red-first fixture; the increment builder is regeneration-clean; the norm-domain fixtures' domain tag
agrees with the registry; and the two norm@1 clauses inc-23 covers (N-ROOT-03, N-PED-01) are present.

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
import skill_rules_increment23 as R  # noqa: E402

FIXTURES = os.path.join(HERE, "skill_fixtures_increment23.jsonl")
REGISTRY_INC = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-23.jsonl")
BUILDER = os.path.join(HERE, "_build_increment23.py")

# The norm@1 contract clauses inc-23 actually carries (only the norm-domain rows). inc-23 does NOT
# re-cover the full N-ROOT/N-LANG/N-PED/N-CONS set — it adds N-ROOT-03 (display consistency) and closes
# the N-PED-01 seam at segment granularity — so demand exactly those two, not the whole @2.2 set.
REQUIRED_NORM_CLAUSES = {"N-ROOT-03", "N-PED-01"}


def main():
    fixtures = [json.loads(l) for l in io.open(FIXTURES, encoding="utf-8") if l.strip()]
    reg_rows = [json.loads(l) for l in io.open(REGISTRY_INC, encoding="utf-8") if l.strip()]
    reg_ids = {r["skill_rule_id"] for r in reg_rows}
    reg_domain = {r["skill_rule_id"]: r["provenance"].get("domain") for r in reg_rows}
    reg_clauses = {r["provenance"].get("clause") for r in reg_rows}
    fails = []
    redfirst_count = 0
    corrected_labels_by_rule = {}     # rule_key -> set(labels) for the non-constant guard
    redfirst_rule_ids = set()

    for fx in fixtures:
        fid = fx["fixture_id"]
        rule = fx["rule"]
        case = fx["case"]

        if not fx.get("example_id"):
            fails.append("%s: missing example_id" % fid)
        if not fx.get("rule_id"):
            fails.append("%s: missing rule_id" % fid)

        # registry/fixture domain tags must agree WHEN the fixture carries one (only norm-domain rows do).
        if fx.get("domain") is not None and fx.get("rule_id") in reg_domain \
                and fx.get("domain") != reg_domain[fx["rule_id"]]:
            fails.append("%s: fixture domain %r != registry domain %r"
                         % (fid, fx.get("domain"), reg_domain[fx["rule_id"]]))

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

        print("  %-10s %-52s corrected=%-38r [%s]" % (tag, fid, corrected, fx.get("rule_id")))

    # NON-CONSTANT guard: every rule's corrected discriminator returns >=2 distinct labels.
    for rule, labels in sorted(corrected_labels_by_rule.items()):
        if len(labels) < 2:
            fails.append("CONSTANT DISCRIMINATOR (send-back class): rule '%s' corrected returns only %r"
                         % (rule, sorted(labels)))

    # coverage: every registry @2.3 rule_id has a red-first fixture.
    for rid in sorted(reg_ids - redfirst_rule_ids):
        fails.append("MISSING red-first fixture for candidate @2.3 rule: %s" % rid)
    for rid in sorted(redfirst_rule_ids - reg_ids):
        fails.append("fixture rule_id %s not present in rule-registry-increment-23.jsonl" % rid)

    # norm@1 contract clause coverage (only the two clauses inc-23 carries).
    for cl in sorted(REQUIRED_NORM_CLAUSES - reg_clauses):
        fails.append("norm@1 contract clause not represented in @2.3 rows: %s" % cl)

    # builder is regeneration-clean (committed artifacts == regenerated).
    chk = subprocess.run([sys.executable, BUILDER, "--check"], capture_output=True, text=True)
    if chk.returncode != 0:
        fails.append("increment-23 builder --check FAILED: %s" % (chk.stdout.strip() or chk.stderr.strip()))

    n_sarf = sum(1 for r in reg_rows if r["skill"] == "sarf")
    n_nahw = sum(1 for r in reg_rows if r["skill"] == "nahw")
    n_norm = sum(1 for rid in reg_domain if reg_domain[rid] == "norm")
    print("\nincrement-23 fixtures: %d total, %d red-first, %d rules, %d registry ids covered"
          % (len(fixtures), redfirst_count, len(corrected_labels_by_rule), len(redfirst_rule_ids & reg_ids)))
    print("increment-23 registry: %d rows (%d sarf, %d nahw; %d norm-domain)"
          % (len(reg_rows), n_sarf, n_nahw, n_norm))
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS - every fixture green on the corrected @2.3 rule + red-first against the superseded rule; "
          "every corrected discriminator branches (non-constant); all %d @2.3 registry rules covered; "
          "norm@1 clauses (N-ROOT-03, N-PED-01) present; domain tags agree; builder regeneration-clean." % len(reg_ids))


if __name__ == "__main__":
    main()
