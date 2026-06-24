#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the Fusha skills are installable + sound: files exist, procedures/fixtures accessible, no raw-source leak,
no MCP dependency in the skill. Works on the repo (default) or an installed dir (--dir).

Usage:
  python scripts/verify_skill_install.py                 # verify the repo is install-ready
  python scripts/verify_skill_install.py --dir ~/.claude/skills/fusha-sarf   # verify an installed skill
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAK = ("/srv/", "157.245.", "id_ed25519", "root.txt", "C:\\\\workspace")


def check(label, cond, fails):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        fails.append(label)


def verify_repo(fails):
    for name in ("sarf", "nahw"):
        check("manifest: skills/%s/manifest.json" % name, os.path.exists(os.path.join(ROOT, "skills", name, "manifest.json")), fails)
        check("wrapper: skills/%s/SKILL.md" % name, os.path.exists(os.path.join(ROOT, "skills", name, "SKILL.md")), fails)
        check("engine SKILL.md: %s/SKILL.md" % name, os.path.exists(os.path.join(ROOT, name, "SKILL.md")), fails)
        procd = os.path.join(ROOT, name, "procedures")
        nproc = len([f for f in os.listdir(procd)]) if os.path.isdir(procd) else 0
        check("%s procedures accessible (%d)" % (name, nproc), nproc >= 5, fails)
        # MCP-free skill
        t = open(os.path.join(ROOT, name, "SKILL.md"), encoding="utf-8").read().lower()
        check("%s/SKILL.md is MCP-free" % name, "tafsir" not in t and "mcp" not in t, fails)
    # regression fixtures accessible
    for fx in ("sarf/examples/qamus-regressions.jsonl", "nahw/evals/suffix-pronoun-eval.jsonl"):
        check("fixture accessible: %s" % fx, os.path.exists(os.path.join(ROOT, fx)), fails)
    # no raw-source leak in the skill trees
    leaked = []
    for name in ("sarf", "nahw", "skills"):
        for dp, _, fs in os.walk(os.path.join(ROOT, name)):
            for f in fs:
                if f.endswith((".md", ".json", ".jsonl")):
                    try:
                        c = open(os.path.join(dp, f), encoding="utf-8").read()
                    except Exception:
                        continue
                    if any(x in c for x in LEAK):
                        leaked.append(os.path.join(dp, f))
    check("no raw-source/secret leak in skill trees", not leaked, fails)
    if leaked:
        for l in leaked[:5]:
            print("   leak:", l)


def verify_installed(d, fails):
    check("installed SKILL.md", os.path.exists(os.path.join(d, "SKILL.md")), fails)
    check("installed procedures/", os.path.isdir(os.path.join(d, "procedures")), fails)
    if os.path.exists(os.path.join(d, "SKILL.md")):
        t = open(os.path.join(d, "SKILL.md"), encoding="utf-8").read().lower()
        check("installed SKILL.md MCP-free", "tafsir" not in t and "mcp" not in t, fails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    a = ap.parse_args()
    fails = []
    if a.dir:
        verify_installed(os.path.expanduser(a.dir), fails)
    else:
        verify_repo(fails)
    if fails:
        print("\n%d CHECK(S) FAILED" % len(fails)); sys.exit(1)
    print("\nALL SKILL-INSTALL CHECKS PASS")


if __name__ == "__main__":
    main()
