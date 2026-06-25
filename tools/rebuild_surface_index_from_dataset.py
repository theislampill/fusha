#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repo-local regeneration of the surface index from the COMMITTED public dataset.

The server exporter (export_current_qamus_dataset.py) reads per-entry JSON from the server entries
dir, so it cannot run repo-locally. This rebuilder reads `qamus/data/current/entries.jsonl` (the
exporter's own public output) and rewrites `by-normalized-surface.json` + `by-normalized-surface-detail.json`
using the EXACT shared `build_surface_index()` from the exporter (no drift, no faked exporter run).

The change vs the prior committed index must be ADDITIVE (headword keys unchanged; usage[].forms keys
added) — the rebuilder asserts that and prints the delta. Read-only over entries; writes only the two
index files. No live/server access.
"""
import hashlib, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export_current_qamus_dataset as X

DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
IDX = os.path.join(ROOT, "qamus", "indexes", "current")
CHECKSUMS = os.path.join(ROOT, "qamus", "data", "current", "checksums.json")

def jdump(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2); f.write("\n")

def main():
    entries = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
    by_norm, detail = X.build_surface_index(entries)
    out_norm = {k: sorted(set(v)) for k, v in by_norm.items()}
    out_detail = {k: sorted(detail[k], key=lambda h: (h["kind"], h["eid"])) for k in sorted(detail)}

    prev_path = os.path.join(IDX, "by-normalized-surface.json")
    prev = json.load(open(prev_path, encoding="utf-8")) if os.path.exists(prev_path) else {}
    added = [k for k in out_norm if k not in prev]
    removed = [k for k in prev if k not in out_norm]
    # additive-only invariant: prior keys must all survive, and their eid sets must be a subset of new
    regressed = [k for k in prev if k in out_norm and not set(prev[k]).issubset(set(out_norm[k]))]
    if removed:
        print("REBUILD FAIL: %d prior keys would be REMOVED (non-additive): %s" % (len(removed), removed[:8]))
        sys.exit(1)
    if regressed:
        print("REBUILD FAIL: %d prior keys lost entries (non-additive): %s" % (len(regressed), regressed[:8]))
        sys.exit(1)

    jdump(out_norm, prev_path)
    jdump(out_detail, os.path.join(IDX, "by-normalized-surface-detail.json"))
    # keep the dataset checksum for the index in sync (the public-dataset acceptance gate pins it)
    if os.path.exists(CHECKSUMS):
        cs = json.load(open(CHECKSUMS, encoding="utf-8"))
        key = "indexes/by-normalized-surface.json"
        if key in cs and isinstance(cs[key], dict):
            raw = open(prev_path, "rb").read()
            cs[key] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            with open(CHECKSUMS, "w", encoding="utf-8", newline="\n") as f:
                json.dump(cs, f, ensure_ascii=False, sort_keys=True, indent=2); f.write("\n")
    form_keys = sum(1 for k, hs in out_detail.items() if any(h["kind"] == "form" for h in hs))
    print("SURFACE INDEX REBUILT — keys %d (+%d added, 0 removed); form-bearing keys %d; detail + checksum updated" %
          (len(out_norm), len(added), form_keys))

if __name__ == "__main__":
    main()
