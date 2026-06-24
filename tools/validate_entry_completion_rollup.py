#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the per-entry completion rollup (canonical: qamus-2092-entry-matrix.jsonl). Phase 4 gate.

The 2,092-entry matrix IS the entry rollup: every entry has a terminal source-photo status, per-field
status (no 'unknown'), hover status, repair status, and an exact next_action. Fails closed.
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RU = os.path.join(ROOT, "qamus", "reports", "qamus-2092-entry-matrix.jsonl")
SP_OK = {"verified","photo_present_needs_visual","repair_ready","missing_locator","deferred","needs_retake"}

def main():
    rows = [json.loads(l) for l in open(RU, encoding="utf-8") if l.strip()]
    errs = []
    if len(rows) != 2092: errs.append(f"rollup has {len(rows)} entries (need 2,092)")
    sec = {}
    for r in rows:
        sec[r.get("section")] = sec.get(r.get("section"),0)+1
        for k in ("entry_id","source_photo_status","field_status","hover_status","repair_status","next_action"):
            if k not in r: errs.append(f"{r.get('entry_id')}: missing {k}")
        if r.get("source_photo_status") not in SP_OK:
            errs.append(f"{r.get('entry_id')}: unknown source_photo_status {r.get('source_photo_status')!r}")
        for fld, st in (r.get("field_status") or {}).items():
            if st == "unknown" or st == "":
                errs.append(f"{r.get('entry_id')}: field {fld} has unknown status")
        if not r.get("next_action"): errs.append(f"{r.get('entry_id')}: empty next_action")
        if len(errs) > 40: break
    if sec != {"verb":947,"noun":1045,"particle":100}:
        errs.append(f"section split {sec} != 947/1045/100")
    print(f"rollup entries={len(rows)} sections={sec}")
    if errs:
        print(f"FAIL ({len(errs)}):"); [print("  -", e) for e in errs[:30]]; sys.exit(1)
    print("VALIDATE OK — entry completion rollup complete (2,092 terminal, 0 unknown, next_action per entry)")

if __name__ == "__main__":
    main()
