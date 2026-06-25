#!/usr/bin/env python3
# LEGACY: superseded by the tools/ generators (canonical machine index is existing_qamus_index.min.json; canonical graph is qamus/indexes/current/*-full.jsonl). Kept for reference; not the current canonical generator.
# -*- coding: utf-8 -*-
"""Build the canonical index of the existing Qamus 2,092 entries (read-only).

Reads entry JSON files from --entries (a local export or a server mirror dir) and writes
  qamus/indexes/existing_qamus_index.json   — one record per entry, indexed by the fields F1 requires
  qamus/reports/qamus-2092-scoreboard.md    — counts by class / status

NO live writes. Reusable: point --entries at any directory of Qamus entry JSON files.
Requires tools/normalize_ar.py on the path.
"""
import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools import normalize_ar as N


def category_class(cat):
    c = (cat or "").lower()
    if "verb" in c:
        return "v"
    if any(k in c for k in ("particle", "preposition", "question", "letters with meaning", "interrogativ",
                            "demonstrativ", "relative", "negation", "pronoun", "conjunction", "vocative",
                            "definite article", "response", "urging")):
        return "p"
    return "n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", required=True, help="dir of Qamus entry *.json files")
    ap.add_argument("--out-index", default="qamus/indexes/existing_qamus_index.json")
    ap.add_argument("--out-report", default="qamus/reports/qamus-2092-scoreboard.md")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.entries, "*.json")))
    entries = [json.load(open(f, encoding="utf-8")) for f in files]

    # frequency-ordered v###/n###/p### ids within class (verbs match the printed book order)
    by_class = collections.defaultdict(list)
    for e in entries:
        by_class[category_class(e.get("category") or e.get("section"))].append(e)
    for cls in by_class:
        by_class[cls].sort(key=lambda e: (-(e.get("total_uses") or 0), e.get("root") or ""))
    sid = {}
    for cls, lst in by_class.items():
        for i, e in enumerate(lst, 1):
            sid[e["id"]] = "qamus:%s%03d" % (cls, i)

    index = {}
    refs_total = 0
    for e in entries:
        hw = (e.get("headword") or "")
        surf = hw.split("/")[0]
        senses = e.get("senses") or []
        glosses = []
        forms = []
        refs = []
        for blk in e.get("usage") or []:
            forms += [f for f in (blk.get("forms") or []) if f]
            for ex in blk.get("examples") or []:
                if ex.get("ref"):
                    refs.append(ex["ref"])
        for s in senses:
            if isinstance(s, dict) and s.get("gloss"):
                glosses.append(s["gloss"])
        refs_total += len(refs)
        index[sid[e["id"]]] = {
            "source_address": "%s#root=%s" % (sid[e["id"]], e.get("root") or ""),
            "entry_id": e["id"],
            "source_keys": e.get("source_keys") or [],
            "surface_ar": surf,
            "norm": N.norm(surf),
            "norm_strict": N.norm_strict(surf),
            "bare": N.bare(surf),
            "root": e.get("root"),
            "headword": hw,
            "lemma_candidate": (e.get("root") or "").replace(" ", "") or surf,
            "pos_category": e.get("category"),
            "section": e.get("section"),
            "class": sid[e["id"]].split(":")[1][0],
            "forms": sorted(set(forms)),
            "n_senses": len(senses),
            "glosses": glosses[:8],
            "total_uses": e.get("total_uses"),
            "tags": e.get("tags") or [],
            "usage_refs": sorted(set(refs))[:40],
            "status": e.get("status"),
            "visibility": e.get("visibility"),
        }

    json.dump(index, open(a.out_index, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    cls = collections.Counter(r["class"] for r in index.values())
    cats = collections.Counter(r["pos_category"] for r in index.values())
    rep = ["# Qamus 2,092 scoreboard (Fusha index export, read-only)", "",
           "Source: existing Qamus entries (live mirror). No live writes. Regenerate: `build_existing_qamus_index.py`.",
           "", "| metric | n |", "|---|---:|",
           "| total entries | %d |" % len(index),
           "| verbs (v) | %d |" % cls["v"],
           "| nouns (n) | %d |" % cls["n"],
           "| particles (p) | %d |" % cls["p"],
           "| distinct roots | %d |" % len({r["root"] for r in index.values() if r["root"]}),
           "| total usage refs | %d |" % refs_total, "",
           "## By category (top 20)", "", "| category | n |", "|---|---:|"]
    for c, n in cats.most_common(20):
        rep.append("| %s | %d |" % (c or "—", n))
    open(a.out_report, "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("wrote %d index records; v=%d n=%d p=%d; refs=%d" % (len(index), cls["v"], cls["n"], cls["p"], refs_total))


if __name__ == "__main__":
    main()
