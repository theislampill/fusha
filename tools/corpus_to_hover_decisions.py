#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corpus -> hover-decision WORKLIST (key-safety aware). READ-ONLY, never live.

Produces the list of hover-gloss decisions a corpus implies, each with a key-safety verdict and the gate that
must be cleared before it can ship. It does NOT author glosses (that is the certified author + key-aware 2-vote
pipeline) — it surfaces, per distinct norm_strict key:
    resolved              already authored (key present in an optional decisions tsv)
    quarantine_homograph  the key carries >1 distinct surface skeleton in this corpus -> NO single gloss
    pending_needs_authoring  one apparent owner, safe to send to the author+2-vote pipeline
    particle_or_construction needs nahw context, route to the particle/relative/conditional procedures

Usage:
  python tools/corpus_to_hover_decisions.py --corpus corpora/nawawi40/nawawi40.matn.jsonl --out out/
  python tools/corpus_to_hover_decisions.py --corpus ... --decisions path/to/hover-decisions.tsv --out out/
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import normalize_ar as NA  # noqa: E402

PARTICLES = set("في من عن الى على مع او ثم بل لا ما ان اذا قد هل لم لن كي اذ".split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--decisions", help="optional existing hover-decisions tsv (key<TAB>gloss) to mark resolved")
    ap.add_argument("--out", default="out")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    resolved = {}
    if a.decisions and os.path.exists(a.decisions):
        for ln in open(a.decisions, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 2:
                resolved[p[0]] = p[1]

    rows = []
    if a.plain:
        for i, ln in enumerate(open(a.corpus, encoding="utf-8")):
            if ln.strip():
                rows.append({"ref": "line:%d" % (i + 1), "ar": ln.strip()})
    else:
        for ln in open(a.corpus, encoding="utf-8"):
            if ln.strip():
                rows.append(json.loads(ln))
    if a.limit:
        rows = rows[:a.limit]

    surfaces = collections.defaultdict(collections.Counter)   # key -> {surface: n}
    locs = collections.defaultdict(list)
    for row in rows:
        ref = row.get("ref") or "?"
        for idx, tok in enumerate((row.get("ar") or "").split()):
            k = NA.norm_strict(tok)
            if not k:
                continue
            surfaces[k][tok] += 1
            if len(locs[k]) < 4:
                locs[k].append("corpus:%s:%d" % (ref, idx + 1))

    out = []
    cc = collections.Counter()
    for k in sorted(surfaces):
        surf = dict(surfaces[k])
        bare = NA.bare(next(iter(surf)))
        occ = sum(surf.values())
        if k in resolved:
            status, gate = "resolved", "auto_safe"
        elif bare in PARTICLES or k in PARTICLES:
            status, gate = "particle_or_construction", "two_vote_required"
        elif len(surf) > 1:
            # >1 distinct vocalized surface under one key -> potential homograph; the 2-vote arbitrates
            status, gate = "quarantine_homograph", "two_vote_required"
        else:
            status, gate = "pending_needs_authoring", "two_vote_required"
        cc[status] += 1
        out.append({"norm_key": k, "surfaces": surf, "occurrences": occ, "status": status,
                    "recommended_gate": gate, "proposed_gloss": resolved.get(k),
                    "used_by": locs[k], "live_write": False})

    with open(os.path.join(a.out, "corpus_hover_decisions_worklist.jsonl"), "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"corpus": os.path.basename(a.corpus), "rows": len(rows), "distinct_keys": len(out),
               "by_status": dict(cc), "live_writes": 0}
    json.dump(summary, open(os.path.join(a.out, "corpus_hover_decisions_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
