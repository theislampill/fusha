#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED-FIRST + NON-CONSTANT-DISCRIMINATOR harness for the INCREMENT-24 skill fixtures
(candidate sarf@2.4 / nahw@2.4 — the P00-vertical-slice pilot dogfood increment, 2026-07-29).

For every fixture in skill_fixtures_increment24.jsonl we run BOTH the corrected candidate rule and
the superseded rule it replaces (skill_rules_increment24.py):

  GREEN     : corrected_rule(case) == correct_label                      (the fix holds)
  RED-FIRST : superseded_rule(case) == wrong_label  AND  wrong_label != correct_label
              (the pre-pilot defect — blanket لِ carve over lexical-lam/pronoun/verb hosts,
               per-page article fold, NFC-order false boundary fork, governor-null iʿrāb claim,
               notation-variant false disagreement, tajarrud canary false-FAIL — is reproduced)

NON-CONSTANT-DISCRIMINATOR guard: for EACH rule, the CORRECTED discriminator must return >=2
DISTINCT labels across that rule's fixtures — i.e. the rule genuinely branches on its input.
Every rule therefore ships >=1 positive (red-first) fixture AND a boundary/control fixture the
same corrected rule maps to a different label.

Also asserts: every candidate @2.4 rule_id in rule-registry-increment-24.jsonl is covered by >=1
red-first fixture; the increment builder is regeneration-clean; every fixture's domain tag agrees
with the registry; and the NFC fixtures are REAL canonical-equivalence pairs (raw bytes differ,
NFC keys agree) so the red-first case cannot silently degenerate into byte equality.

No server, no MCP, no network. Deterministic. Fails closed (exit 1) on any violation.
"""
import io
import json
import os
import subprocess
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import skill_rules_increment24 as R  # noqa: E402

FIXTURES = os.path.join(HERE, "skill_fixtures_increment24.jsonl")
REGISTRY_INC = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-24.jsonl")
BUILDER = os.path.join(HERE, "_build_increment24.py")


def main():
    fixtures = [json.loads(l) for l in io.open(FIXTURES, encoding="utf-8") if l.strip()]
    reg_rows = [json.loads(l) for l in io.open(REGISTRY_INC, encoding="utf-8") if l.strip()]
    reg_ids = {r["skill_rule_id"] for r in reg_rows}
    reg_domain = {r["skill_rule_id"]: r["provenance"].get("domain") for r in reg_rows}
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

        # registry/fixture domain tags must agree.
        if fx.get("rule_id") in reg_domain and fx.get("domain") != reg_domain[fx["rule_id"]]:
            fails.append("%s: fixture domain %r != registry domain %r"
                         % (fid, fx.get("domain"), reg_domain[fx["rule_id"]]))

        if rule not in R.CORRECTED or rule not in R.SUPERSEDED:
            fails.append("%s: no corrected/superseded rule registered for '%s'" % (fid, rule))
            continue

        # NFC-parity fixtures must be REAL canonical-equivalence material: the red-first pairs must
        # differ in raw bytes yet agree under NFC; the control fork must survive NFC.
        if rule == "nfc_span_parity":
            a, b = case.get("side_a", ""), case.get("side_b", "")
            nfc_eq = unicodedata.normalize("NFC", a) == unicodedata.normalize("NFC", b)
            if fx.get("redfirst") and (a == b or not nfc_eq):
                fails.append("%s: NFC red-first pair must be raw-distinct and NFC-equivalent" % fid)
            if not fx.get("redfirst") and nfc_eq:
                fails.append("%s: NFC control fork must survive NFC" % fid)

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

        print("  %-10s %-56s corrected=%-42r [%s]" % (tag, fid, corrected, fx.get("rule_id")))

    # NON-CONSTANT guard: every rule's corrected discriminator returns >=2 distinct labels.
    for rule, labels in sorted(corrected_labels_by_rule.items()):
        if len(labels) < 2:
            fails.append("CONSTANT DISCRIMINATOR (send-back class): rule '%s' corrected returns only %r"
                         % (rule, sorted(labels)))

    # coverage: every registry @2.4 rule_id has a red-first fixture.
    for rid in sorted(reg_ids - redfirst_rule_ids):
        fails.append("MISSING red-first fixture for candidate @2.4 rule: %s" % rid)
    for rid in sorted(redfirst_rule_ids - reg_ids):
        fails.append("fixture rule_id %s not present in rule-registry-increment-24.jsonl" % rid)

    # builder is regeneration-clean (committed artifacts == regenerated).
    chk = subprocess.run([sys.executable, BUILDER, "--check"], capture_output=True, text=True)
    if chk.returncode != 0:
        fails.append("increment-24 builder --check FAILED: %s" % (chk.stdout.strip() or chk.stderr.strip()))

    n_sarf = sum(1 for r in reg_rows if r["skill"] == "sarf")
    n_nahw = sum(1 for r in reg_rows if r["skill"] == "nahw")
    print("\nincrement-24 fixtures: %d total, %d red-first, %d rules, %d registry ids covered"
          % (len(fixtures), redfirst_count, len(corrected_labels_by_rule), len(redfirst_rule_ids & reg_ids)))
    print("increment-24 registry: %d rows (%d sarf, %d nahw)" % (len(reg_rows), n_sarf, n_nahw))
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS - every fixture green on the corrected @2.4 rule + red-first against the superseded rule; "
          "every corrected discriminator branches (non-constant); all %d @2.4 registry rules covered; "
          "NFC pairs verified raw-distinct/canonically-equivalent; domain tags agree; "
          "builder regeneration-clean." % len(reg_ids))


if __name__ == "__main__":
    main()
