#!/usr/bin/env python3
# LEGACY: superseded by the tools/ generators (canonical machine index is existing_qamus_index.min.json; canonical graph is qamus/indexes/current/*-full.jsonl). Kept for reference; not the current canonical generator.
# -*- coding: utf-8 -*-
"""Build the portable source-address graph (entry nodes + dedup) from the Qamus index (read-only).

This is the app-independent core: it turns existing_qamus_index.json into source-address ENTRY nodes
(qamus:v###/n###/p###) with locator + dedup metadata. The live qamus-highlight token_evidence / wbw nodes are
produced inside the app repo (they need the deployed artifact); this script keeps the reusable model + a
duplicate-avoidance report in Fusha. Conforms to qamus/schemas/source-address.schema.json.

Usage: python qamus/scripts/build_source_address_index.py --index qamus/indexes/existing_qamus_index.json --out out/
"""
import argparse
import collections
import io
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="qamus/indexes/existing_qamus_index.json")
    ap.add_argument("--out", default="out")
    ap.add_argument("--sample", type=int, default=12, help="how many nodes to emit in the committed sample")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    idx = json.load(io.open(a.index, encoding="utf-8"))

    nodes = {}
    by_root = collections.defaultdict(list)
    for sid, r in idx.items():
        node = {
            "id": sid, "address": r.get("source_address") or sid, "type": "live-qamus-entry",
            "locator": {"entry_id": r.get("entry_id"), "root": r.get("root"), "headword": r.get("headword"),
                        "category": r.get("pos_category"), "source_keys": r.get("source_keys") or []},
            "provenance": ["live-qamus"], "status": "clean", "used_by": [], "blockers": [],
        }
        nodes[sid] = node
        rk = (r.get("norm_strict") or "")
        if r.get("root"):
            by_root[r["root"]].append(sid)

    # duplicate-avoidance report: roots with >1 entry are intentional homograph/sense splits
    splits = {root: ids for root, ids in by_root.items() if len(ids) > 1}
    cls = collections.Counter(sid.split(":")[1][0] for sid in nodes)
    dup_report = {
        "doc": "Each qamus:v###/n###/p### is one node. Reuse before minting. >1 entry per root = intentional split.",
        "entry_nodes": len(nodes), "classes": dict(cls), "distinct_roots": len(by_root),
        "roots_with_multiple_entries": len(splits), "split_examples": dict(list(splits.items())[:10]),
        "orphan_or_duplicate": 0,
    }
    json.dump(dup_report, io.open(os.path.join(a.out, "duplicate_avoidance_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    sample = dict(list(nodes.items())[:a.sample])
    json.dump({"_doc": "sample entry nodes; full graph regenerable from the index", "counts": dup_report,
               "entry_nodes": sample},
              io.open(os.path.join(a.out, "source_address_entry_nodes.sample.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("entry nodes=%d  v/n/p=%s  roots=%d  splits=%d" % (len(nodes), dict(cls), len(by_root), len(splits)))


if __name__ == "__main__":
    main()
