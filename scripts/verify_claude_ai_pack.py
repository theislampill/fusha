#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the claude.ai pack: required files present, no banned/oversize files, manifest agrees, no
stale canonical refs, and fusha-project-instructions.md exists. Builds the pack first if absent.
Read-only. Exit non-zero on any defect.
"""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "claude-ai")
PACK = os.path.join(DIST, "pack")
INCLUDE = os.path.join(DIST, "pack.include.txt")
MAX_FILE = 500 * 1024
MAX_TOTAL = 5 * 1024 * 1024
BANNED = ("entries.jsonl", "indexes/current/", "candidates/", ".provenance.", "out/", "source_photo")
STALE = re.compile(r"existing_qamus_index\.json|qamus-2092-scoreboard\.md|hover-gloss-scoreboard\.md")

def main():
    errors = []
    if not os.path.exists(os.path.join(DIST, "fusha-project-instructions.md")):
        errors.append("missing dist/claude-ai/fusha-project-instructions.md")
    if not os.path.isdir(PACK):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_claude_ai_project_pack.py")])
    want = [l.strip() for l in open(INCLUDE, encoding="utf-8")
            if l.strip() and not l.lstrip().startswith("#")]
    total, nfiles = 0, 0
    for dp, _, fs in os.walk(PACK):
        for f in fs:
            p = os.path.join(dp, f); rel = os.path.relpath(p, PACK).replace("\\", "/")
            nfiles += 1; sz = os.path.getsize(p); total += sz
            if any(b in rel for b in BANNED):
                errors.append("banned file in pack: %s" % rel)
            if sz > MAX_FILE:
                errors.append("file > 500KB: %s" % rel)
            if f.endswith(".md") and STALE.search(open(p, encoding="utf-8", errors="replace").read()):
                if "historical" not in open(p, encoding="utf-8", errors="replace").read().lower():
                    errors.append("stale canonical ref inside pack: %s" % rel)
    for rel in want:
        if not os.path.exists(os.path.join(PACK, rel)):
            errors.append("required file missing from pack: %s" % rel)
    if total > MAX_TOTAL:
        errors.append("pack total %d > 5MB" % total)
    if errors:
        print("VERIFY CLAUDE-AI PACK FAIL:")
        for e in errors[:30]:
            print("  -", e)
        sys.exit(1)
    print("CLAUDE-AI PACK OK — %d files, %d bytes (< 5MB, no file > 500KB, no banned/stale, instructions present)"
          % (nfiles, total))

if __name__ == "__main__":
    main()
