#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install the Fusha sarf + nahw skills for Claude (Claude Code skill convention: ~/.claude/skills/<name>/SKILL.md).

Each manifest (skills/<name>/manifest.json) lists the canonical engine tree to copy so the installed skill is
SELF-CONTAINED (SKILL.md + procedures/ + rules/ + evals/ + curriculum/ + references/). The installed SKILL.md is the
canonical engine's SKILL.md (full procedures), with frontmatter name set to fusha-<name>. MCP-free by construction.

Usage:
  python scripts/install_claude_skills.py --dry-run         # show what would be copied
  python scripts/install_claude_skills.py                   # install to ~/.claude/skills
  python scripts/install_claude_skills.py --target DIR      # install to a custom skills dir
"""
import argparse
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src_skill_md(name):
    return os.path.join(ROOT, name, "SKILL.md")


def plan(name):
    man = json.load(open(os.path.join(ROOT, "skills", name, "manifest.json"), encoding="utf-8"))
    items = []
    for inc in man["includes"]:
        p = os.path.join(ROOT, inc.rstrip("/"))
        if os.path.exists(p):
            items.append(inc.rstrip("/"))
    return man, items


def install(name, target_dir, dry):
    man, items = plan(name)
    dest = os.path.join(target_dir, "fusha-" + name)
    actions = []
    for inc in items:
        src = os.path.join(ROOT, inc)
        rel = inc.split("/", 1)[1] if "/" in inc else os.path.basename(inc)
        dst = os.path.join(dest, rel)
        actions.append((src, dst, os.path.isdir(src)))
    if not dry:
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        os.makedirs(dest, exist_ok=True)
        for src, dst, isdir in actions:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if isdir:
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        # ensure the installed SKILL.md frontmatter name is fusha-<name> (canonical sarf/SKILL.md is named <name>)
        sm = os.path.join(dest, "SKILL.md")
        if os.path.exists(sm):
            t = open(sm, encoding="utf-8").read()
            t = t.replace("\nname: %s\n" % name, "\nname: fusha-%s\n" % name, 1)
            open(sm, "w", encoding="utf-8").write(t)
    return {"skill": "fusha-" + name, "dest": dest, "items": [a[0].replace(ROOT, ".") for a in actions]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--target", default=os.path.expanduser("~/.claude/skills"))
    a = ap.parse_args()
    out = []
    for name in ("sarf", "nahw"):
        out.append(install(name, a.target, a.dry_run))
    print(json.dumps({"mode": "dry-run" if a.dry_run else "installed", "target": a.target, "skills": out},
                     ensure_ascii=False, indent=1))
    if a.dry_run:
        print("\nDRY-RUN: no files written. Re-run without --dry-run to install.")


if __name__ == "__main__":
    main()
