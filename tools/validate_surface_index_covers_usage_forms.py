#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F1 gate — every usage[].forms token (and every headword) must be present in the surface index.

A headword-only surface index miscounts inflected forms already stored in an entry as unresolved.
This validator fails closed if any usage[].forms token's norm_strict key is absent from
by-normalized-surface.json, or present only via an unrelated entry collision without the owning entry.
Read-only. Exit non-zero on any miss.
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export_current_qamus_dataset as X   # canonical norm_strict (the hover-key join)
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
IDX = os.path.join(ROOT, "qamus", "indexes", "current", "by-normalized-surface.json")

def main():
    entries = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
    by_norm = json.load(open(IDX, encoding="utf-8"))
    missing = []
    miss_owner = []
    checked = 0
    for e in entries:
        eid = e.get("id")
        toks = [e.get("headword", "")]
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                toks += str(fstr).split()
        for tok in toks:
            nk = X.norm_strict(tok)
            if not nk:
                continue
            checked += 1
            ids = by_norm.get(nk)
            if not ids:
                missing.append((eid, e.get("headword", ""), tok, nk))
            elif eid not in ids:
                miss_owner.append((eid, e.get("headword", ""), tok, nk))
    if missing:
        print("SURFACE INDEX FAIL — %d form/headword tokens absent from by-normalized-surface.json:" % len(missing))
        for r in missing[:20]:
            print("  ", r)
        sys.exit(1)
    if miss_owner:
        print("SURFACE INDEX FAIL — %d form tokens present only via an unrelated entry (owning entry missing):" % len(miss_owner))
        for r in miss_owner[:20]:
            print("  ", r)
        sys.exit(1)
    print("SURFACE INDEX OK — usage.forms covered (%d form/headword tokens, all in index with owning entry)" % checked)

if __name__ == "__main__":
    main()
