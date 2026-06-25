#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F6 gate — fail closed on stale canonical-path / stale-current-status references in docs, reports,
generators and curriculum, so future agents/learners do not follow superseded artifacts.

Forbidden (in non-historical, non-legacy files):
  - `existing_qamus_index.json`   (current canonical machine index is `existing_qamus_index.min.json`)
  - `qamus-2092-scoreboard.md`    (current is `qamus-2092-terminal-scoreboard.md`)
  - `hover-gloss-scoreboard.md`   (current is `hover-gloss-terminal-scoreboard.md`)
  - stale-current coverage `82.49%` / `41,164` presented as CURRENT (not under a historical marker)

Exemptions: a file (or the line) carrying `HISTORICAL`, `LEGACY`, or `SUPERSEDED`; the deep-research
findings index and this validator (they name the stale strings on purpose). Works with or without git
(filesystem walk — F14 no-git fallback). Read-only. Exit non-zero on any unmarked stale reference.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["curriculum", "corpora", "qamus", "tools"]
SCAN_ROOT_FILES = ["README.md", "INSTALL.md"]

FORBIDDEN = [
    (re.compile(r"existing_qamus_index\.json"), "existing_qamus_index.json -> existing_qamus_index.min.json"),
    (re.compile(r"qamus-2092-scoreboard\.md"), "qamus-2092-scoreboard.md -> qamus-2092-terminal-scoreboard.md"),
    (re.compile(r"hover-gloss-scoreboard\.md"), "hover-gloss-scoreboard.md -> hover-gloss-terminal-scoreboard.md"),
    (re.compile(r"\b82\.49\s*%|41,164"), "stale-current coverage 82.49% / 41,164 (mark HISTORICAL or update)"),
]
EXEMPT_MARKERS = ("historical", "legacy", "superseded", "deprecated")
EXEMPT_FILES = {"qamus/reports/closure-2092/deep-research-findings-index.md",
                "qamus/reports/closure-2092/deep-research-findings-index.json",
                "tools/validate_canonical_paths.py"}

def discover():
    files = []
    for rf in SCAN_ROOT_FILES:
        p = os.path.join(ROOT, rf)
        if os.path.exists(p): files.append(rf)
    for d in SCAN_DIRS:
        for dp, _, fs in os.walk(os.path.join(ROOT, d)):
            if os.sep + "out" + os.sep in dp + os.sep or os.sep + "__pycache__" in dp:
                continue
            for f in fs:
                if f.endswith((".md", ".py", ".json", ".jsonl")):
                    files.append(os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/"))
    return files

def main():
    fails = []
    files = discover()
    for rel in files:
        if rel in EXEMPT_FILES:
            continue
        txt = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        low = txt.lower()
        file_exempt = any(m in low for m in EXEMPT_MARKERS)
        for i, line in enumerate(txt.splitlines(), 1):
            llow = line.lower()
            if any(m in llow for m in EXEMPT_MARKERS):
                continue
            for pat, msg in FORBIDDEN:
                if pat.search(line):
                    # a whole-file historical/legacy marker exempts the file's stale refs
                    if file_exempt:
                        continue
                    fails.append(f"{rel}:{i}: {msg}")
    if fails:
        print("CANONICAL PATHS FAIL — stale references (mark HISTORICAL/LEGACY or update):")
        for f in fails[:60]:
            print("  -", f)
        print(f"  ... {len(fails)} total" if len(fails) > 60 else "")
        sys.exit(1)
    print(f"CANONICAL PATHS OK — {len(files)} files scanned, 0 stale current-path references")

if __name__ == "__main__":
    main()
