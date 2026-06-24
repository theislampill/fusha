#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the per-token completion manifest (canonical: hover-token-audit-full.jsonl). Phase 4 gate.

The full hover-token audit IS the completion manifest: every one of the 49,900 tokens has a terminal
state with an exact blocker (no generic pending) and a risk level. Fails closed.
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "qamus", "reports", "hover-token-audit-full.jsonl")
BLOCKERS = {"stem_base_unknown","source_entry_unverified","same_surface_polysemy_requires_i3rab","proper_noun_no_qamus_entry"}
RISK = {"LOW","MEDIUM","HIGH","SCHOLAR"}

def main():
    rows = [json.loads(l) for l in open(MAN, encoding="utf-8") if l.strip()]
    errs = []
    if len(rows) != 49900: errs.append(f"manifest has {len(rows)} tokens (need 49,900)")
    res = pend = 0
    for r in rows:
        if "quran_loc" not in r or "decision_state" not in r:
            errs.append(f"row missing anchor: {r.get('quran_loc')}"); continue
        if r.get("risk") not in RISK: errs.append(f"{r['quran_loc']}: bad/absent risk {r.get('risk')}")
        st = r["decision_state"]
        if st == "resolved":
            res += 1
            if not r.get("public_gloss"): errs.append(f"{r['quran_loc']}: resolved without gloss")
        elif st == "pending":
            pend += 1
            if r.get("blocker") not in BLOCKERS:
                errs.append(f"{r['quran_loc']}: generic/unknown pending blocker {r.get('blocker')!r}")
        else:
            errs.append(f"{r['quran_loc']}: non-terminal state {st}")
        if len(errs) > 40: break
    print(f"manifest tokens={len(rows)} resolved={res} pending={pend}")
    if errs:
        print(f"FAIL ({len(errs)}):"); [print("  -", e) for e in errs[:30]]; sys.exit(1)
    print("VALIDATE OK — per-token completion manifest complete (49,900 terminal, exact blockers, risk-tagged)")

if __name__ == "__main__":
    main()
