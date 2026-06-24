#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F9 — DRY-RUN applier for linguistic decisions (sarf+nahw).

Reads a JSONL of linguistic-decision objects, checks them against an optional source-address index for
duplicate avoidance, classifies each into a target payload, and writes candidate payloads + a report.
**Dry-run only: never writes live Qamus, never strips a public artifact's provenance because it never ships
one.** Public export is gated: a decision may be exported only if decision.type=='authored_gloss' AND no
internal provenance would leak.

Usage:
  python tools/apply_linguistic_decision.py --decisions <in.jsonl> [--graph source_address_index.json] --out out/
"""
import argparse
import io
import json
import os


def load_addresses(graph_path):
    if not graph_path or not os.path.exists(graph_path):
        return set()
    g = json.load(io.open(graph_path, encoding="utf-8"))
    addrs = set()
    for n in (g.get("entry_nodes") or {}).values():
        if n.get("address"):
            addrs.add(n["address"])
    addrs |= set((g.get("token_evidence") or {}).keys())
    return addrs


def public_record(d):
    """Build the EXACTLY-shaped public record, or None if export is not allowed."""
    if d.get("decision", {}).get("type") != "authored_gloss":
        return None
    gloss = d["decision"].get("gloss_en_authored")
    if not gloss or not d.get("public_export_allowed", False):
        return None
    return {"text": gloss, "src": "qamus", "kind": "authored", "lang": "en"}  # nothing else ever ships


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--graph", default=None)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    known = load_addresses(a.graph)

    buckets = {"qamus_entry_candidate": [], "qamus_repair_candidate": [], "hover_authored_gloss": [],
               "pending_update": [], "quarantine": []}
    dup = 0
    seen = set()
    report = []
    for line in io.open(a.decisions, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        sa = d.get("source_address")
        if sa in seen:
            dup += 1
            continue                                    # duplicate-avoidance within the batch
        seen.add(sa)
        t = d.get("decision", {}).get("type")
        pub = public_record(d)
        leak = any(d.get("internal_provenance", {}).get(k) for k in ("external_informed_by",)) and pub and \
            ("informed_by" in json.dumps(pub) or any(s in json.dumps(pub).lower() for s in ("qac", "quran.com", "tanzil")))
        if t == "authored_gloss":
            buckets["hover_authored_gloss"].append({"source_address": sa, "public_record": pub,
                                                    "exported": bool(pub), "in_graph": sa in known})
        elif t == "pending":
            buckets["pending_update"].append({"source_address": sa, "pending_reason": d["decision"].get("pending_reason")})
        elif t == "quarantine":
            buckets["quarantine"].append({"source_address": sa, "surface_ar": d.get("surface_ar")})
        elif t == "repair_candidate":
            buckets["qamus_repair_candidate"].append({"source_address": sa, "surface_ar": d.get("surface_ar")})
        report.append({"id": d.get("decision_id"), "address": sa, "type": t, "public_exported": bool(pub),
                       "leak_detected": bool(leak)})

    for k, v in buckets.items():
        with io.open(os.path.join(a.out, k + ".candidate.jsonl"), "w", encoding="utf-8") as f:
            for r in v:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    leaks = sum(1 for r in report if r["leak_detected"])
    summary = {"dry_run": True, "live_writes": 0, "decisions": len(report), "duplicates_skipped": dup,
               "by_bucket": {k: len(v) for k, v in buckets.items()}, "provenance_leaks": leaks}
    json.dump(summary, io.open(os.path.join(a.out, "apply_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))
    assert leaks == 0, "ABORT: a public record would leak internal provenance"


if __name__ == "__main__":
    main()
