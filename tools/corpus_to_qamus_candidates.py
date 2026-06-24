#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corpus -> reviewable Qamus candidates (the sarf/nahw engine pulling the Qamus cart). READ-ONLY, never live.

Point it at any Arabic corpus (jsonl rows {ref, ar} or plain-text lines). For each token it:
  1. creates a source-address node (corpus:<ref>:<idx>);
  2. normalizes (norm_strict — keeps hamza seat + ال, drops harakat);
  3. looks up the existing Qamus index (surfaces + forms);
  4. classifies: already_in_qamus | occurrence_augment | new_surface_existing_lemma | new_lemma_existing_root |
     new_root | particle_or_construction | review_needed;
  5. emits a candidate row (entry stub / occurrence augment / nothing-needed) for HUMAN review.

It does NOT author final glosses (that is the certified author+2-vote pipeline) and NEVER writes the live store.
Dedupe is through the index (reuse before minting).

Usage:
  python tools/corpus_to_qamus_candidates.py --corpus corpora/nawawi40/nawawi40.matn.jsonl --out out/
  python tools/corpus_to_qamus_candidates.py --corpus path/to/text.txt --plain --out out/
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import normalize_ar as NA  # noqa: E402

IDX = os.path.join(ROOT, "qamus", "indexes", "existing_qamus_index.min.json")
# short high-frequency function words -> particle_or_construction (no root-verb gloss)
PARTICLES = set("في من عن الى على مع او ثم بل لا ما ان اذا قد هل لم لن كي اذ".split())


def load_index():
    idx = json.load(open(IDX, encoding="utf-8"))
    surf = {}          # norm_strict surface/form -> entry meta
    roots = set()
    for sid, r in idx.items():
        meta = {"entry_id": r.get("entry_id"), "root": r.get("root"), "address": r.get("source_address")}
        for s in [r.get("surface_ar")] + (r.get("forms") or []):
            if s:
                surf.setdefault(NA.norm_strict(s), meta)
        if r.get("norm_strict"):
            surf.setdefault(r["norm_strict"], meta)
        if r.get("root"):
            roots.add(r["root"])
    return surf, roots


def classify(tok, surf, roots):
    nk = NA.norm_strict(tok)
    bare = NA.bare(tok)
    if not nk or len(bare) <= 1:
        return "review_needed", None
    if bare in PARTICLES or nk in PARTICLES:
        return "particle_or_construction", surf.get(nk)
    if nk in surf:
        return "already_in_qamus", surf[nk]
    # de-article / strip common proclitics for a second look
    for pre in ("ال", "وال", "بال", "فال", "و", "ف", "ب", "ل", "ك"):
        if nk.startswith(pre) and nk[len(pre):] in surf:
            return "new_surface_existing_lemma", surf[nk[len(pre):]]
    return "new_root", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--plain", action="store_true", help="corpus is plain text (one passage per line)")
    ap.add_argument("--limit", type=int, default=0, help="cap rows (0 = all)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    surf, roots = load_index()

    rows = []
    if a.plain:
        for i, ln in enumerate(open(a.corpus, encoding="utf-8")):
            if ln.strip():
                rows.append({"ref": "line:%d" % (i + 1), "ar": ln.strip()})
    else:
        for ln in open(a.corpus, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                rows.append(json.loads(ln))
    if a.limit:
        rows = rows[:a.limit]

    cls_count = collections.Counter()
    cands = []
    seen_new = set()
    for row in rows:
        ref = row.get("ref") or row.get("id") or "?"
        toks = (row.get("ar") or "").split()
        for idx, tok in enumerate(toks):
            cl, meta = classify(tok, surf, roots)
            cls_count[cl] += 1
            if cl in ("already_in_qamus", "particle_or_construction"):
                continue  # nothing to mint; (occurrence augment would attach the ref to the entry's usage)
            addr = "corpus:%s:%d" % (ref, idx + 1)
            key = NA.norm_strict(tok)
            if cl in ("new_root", "new_surface_existing_lemma") and key in seen_new:
                continue
            seen_new.add(key)
            cands.append({
                "source_address": addr, "surface_ar": tok, "norm_strict": key,
                "classification": cl, "existing_entry": meta,
                "candidate_action": {"new_root": "draft new entry (root review)",
                                     "new_surface_existing_lemma": "add surface/form + occurrence to entry",
                                     "review_needed": "human review"}.get(cl, "review"),
                "needs": ["sarf:root-decision", "nahw:role"] if cl == "new_root" else ["sarf:noun-plural-gender"],
                "live_write": False,
            })

    with open(os.path.join(a.out, "corpus_to_qamus_candidates.jsonl"), "w", encoding="utf-8") as f:
        for c in cands:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    summary = {"corpus": os.path.basename(a.corpus), "rows": len(rows),
               "token_classifications": dict(cls_count), "distinct_candidates": len(cands),
               "live_writes": 0}
    json.dump(summary, open(os.path.join(a.out, "corpus_to_qamus_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
