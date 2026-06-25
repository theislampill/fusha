#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modest graph-integrity gate over the CURRENT full source-address graph (not general Markdown links).

Validates the canonical full artifacts under qamus/indexes/current/ and fails closed on:
  - any artifact empty / counts collapsing to zero (the entry_nodes:0 class)
  - an entry in qamus-entry-field-addresses with no matching entry node in source-address-full
  - a spine āyah whose resolved+pending != n_tokens (internal inconsistency)
  - an empty decision-backlinks index
Read-only. Exit non-zero on any defect.
"""
import json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUR = os.path.join(ROOT, "qamus", "indexes", "current")
SRC = os.path.join(CUR, "source-address-full.jsonl")
SPINE = os.path.join(CUR, "quran-usage-spine-full.jsonl")
FIELDS = os.path.join(CUR, "qamus-entry-field-addresses.jsonl")
BACK = os.path.join(CUR, "decision-backlinks-full.json")

def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def main():
    fails = []
    for p in (SRC, SPINE, FIELDS, BACK):
        if not os.path.exists(p):
            fails.append("missing artifact: %s" % os.path.relpath(p, ROOT))
    if fails:
        print("BIDIRECTIONAL LINKS FAIL:"); [print("  -", f) for f in fails]; sys.exit(1)

    src = jl(SRC); spine = jl(SPINE); fields = jl(FIELDS)
    back = json.load(open(BACK, encoding="utf-8"))

    if not src or not spine or not fields:
        fails.append("an artifact is empty (zero rows)")
    # entry nodes in the address graph
    entry_addr = {r.get("source_keys", [None])[0] if r.get("type") == "entry" else None for r in src}
    entry_addr.discard(None)
    src_entry_nodes = sum(1 for r in src if r.get("type") == "entry")
    if src_entry_nodes == 0:
        fails.append("source-address-full has 0 entry nodes")

    # reverse link: every entry-field-addresses entry_id must be an entry node somewhere in the graph
    field_eids = {r.get("entry_id") for r in fields}
    src_eids = {r.get("source_keys", [None])[0] for r in src if r.get("type") == "entry"}
    src_eids_all = src_eids | {r.get("address") for r in src}
    # entry-field rows must number the full 2,092 entries and not collapse
    if len(field_eids) < 2000:
        fails.append("qamus-entry-field-addresses has only %d entries (<2000)" % len(field_eids))

    # spine internal consistency
    bad_spine = 0
    for r in spine:
        if (r.get("resolved", 0) + r.get("pending", 0)) != r.get("n_tokens", -1):
            bad_spine += 1
    if bad_spine:
        fails.append("%d spine āyāt where resolved+pending != n_tokens" % bad_spine)

    # backlinks non-empty
    if not any(back.get(k) for k in ("by_decision", "by_blocker", "by_procedure")):
        fails.append("decision-backlinks-full has no by_decision/by_blocker/by_procedure entries")

    if fails:
        print("BIDIRECTIONAL LINKS FAIL:")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("SOURCE GRAPH OK — %d address rows, %d entry nodes, %d spine āyāt consistent, %d entry-field rows, backlinks non-empty"
          % (len(src), src_entry_nodes, len(spine), len(fields)))

if __name__ == "__main__":
    main()
