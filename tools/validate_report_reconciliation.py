#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate: current reports must agree with the canonical scoreboards (no stale-as-current drift).

Canonical current artifacts:
  qamus/reports/hover-gloss-terminal-scoreboard.md   (coverage %, resolved/total)
  qamus/reports/qamus-2092-terminal-scoreboard.md    (section split 947/1045/100)

Any report NOT marked historical (containing the token `<!-- HISTORICAL`) must NOT carry a stale
current-claim. Stale tokens are coverage/section values from superseded tranches.
Fails closed so a future stale report can't masquerade as current.
"""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "qamus", "reports")

# genuinely-superseded scoreboard values that must not appear in a CURRENT (unmarked) report.
# (Intermediate-current values like 81.41/81.77/81.91 are allowed — they appear in legitimate
#  coverage-trail narratives that lead to the current 82.49%.)
STALE = [r"80\.68", r"79\.93", r"40,?260", r"40,?805",
         r"970 ?verbs?\b", r"970 ?v\b", r"1,?022 ?nouns?\b"]
STALE_RE = re.compile("|".join(STALE))

def main():
    # confirm canonical scoreboard shows the CURRENT numbers
    canon = open(os.path.join(REP, "hover-gloss-terminal-scoreboard.md"), encoding="utf-8").read()
    canonical_pcts = [float(m.group(1)) for m in re.finditer(r"(\d{2,3}\.\d\d)%", canon)]
    if not canonical_pcts or max(canonical_pcts) < 82.49:
        print("FAIL: canonical hover-gloss-terminal-scoreboard.md missing current coverage"); sys.exit(1)
    tracked = subprocess.run(["git", "ls-files", "qamus/reports/*.md", "qamus/reports/*.json"],
                             cwd=ROOT, capture_output=True, text=True).stdout.split()
    if not tracked:  # F14 no-git fallback: filesystem walk so a ZIP checkout is not scanned vacuously
        for dp, _, fs in os.walk(os.path.join(ROOT, "qamus", "reports")):
            if "__pycache__" in dp:
                continue
            for f in fs:
                if f.endswith((".md", ".json")):
                    tracked.append(os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/"))
    fails = []
    for rel in tracked:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p): continue
        txt = open(p, encoding="utf-8").read()
        if "<!-- HISTORICAL" in txt or "HISTORICAL —" in txt or "(historical" in txt.lower():
            continue  # explicitly labeled historical -> exempt
        if rel.endswith(".json") and ('"_status":"historical"' in txt.replace(" ", "")
                                       or '"_historical":true' in txt.replace(" ", "")):
            continue  # JSON marked historical -> exempt
        m = STALE_RE.search(txt)
        if m:
            fails.append(f"{os.path.basename(rel)}: stale current-claim {m.group(0)!r} (mark <!-- HISTORICAL --> or regenerate)")
    if fails:
        print(f"FAIL — {len(fails)} report(s) carry stale current-claims:")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("REPORT RECONCILIATION OK — no stale current-claims; canonical scoreboard current")

if __name__ == "__main__":
    main()
