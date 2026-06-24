#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""closure-2092 — build the apply batch from the form-variant 2-vote workflow result.

Reads the certified `approved` list ({nk, gloss}) + the candidate file (nk -> locs) + the live verses
(per-loc surface), and emits per-loc token decisions in the live schema. Surface-wide: one certified
family gloss -> a decision for every collision-free occurrence of that surface.

Outputs:
  qamus/candidates/qamus_2092/form_variant_batch_001.jsonl            (git provenance)
  qamus/candidates/qamus_2092/form_variant_batch_001.provenance.jsonl
  out/hover_stage/form_variant_apply.jsonl                           (lines to append to live)
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT, "out", "hover_stage"))
CAND = os.path.join(STAGE, "form_variant_cand.jsonl")
CDIR = os.path.join(ROOT, "qamus", "candidates", "qamus_2092")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved", required=True, help="JSON with {approved:[{nk,gloss}]}")
    ap.add_argument("--name", default="form_variant_batch_001")
    a = ap.parse_args()
    res = json.load(open(a.approved, encoding="utf-8"))
    approved = {d["nk"]: d["gloss"].strip() for d in res.get("approved", []) if d.get("gloss", "").strip()}
    cand = {}
    for ln in open(CAND, encoding="utf-8"):
        ln = ln.strip()
        if ln:
            r = json.loads(ln); cand[r["nk"]] = r
    wbw = json.load(open(os.path.join(STAGE, "wbw-lookup.json"), encoding="utf-8"))
    verses, words = wbw["verses"], wbw["words"]

    def surface_at(loc):
        sa = ":".join(loc.split(":")[:2]); i = int(loc.split(":")[2])
        wl = verses.get(sa, [])
        return wl[i - 1] if 0 < i <= len(wl) else ""

    batch, prov = [], []
    skipped_already = 0
    for nk, gloss in approved.items():
        fam = cand.get(nk)
        if not fam:
            continue
        for loc in fam["locs"]:
            if loc in words:          # already resolved by another lane meanwhile -> skip
                skipped_already += 1
                continue
            surf = surface_at(loc) or fam["surface"]
            batch.append({
                "loc": loc, "gloss": gloss, "surface": surf, "key": nk,
                "state_id": "state:tok:%s" % loc, "src": "qamus", "kind": "authored", "lang": "en",
                "decision_state": "form_variant_decision",
                "internal_provenance": {"informed_by": ["qac", "qamus-dataset"],
                                        "method": "root-known form-variant (entry-seeded), sarf+nahw 2-vote"},
            })
            prov.append({"loc": loc, "gloss": gloss, "surface": surf, "nk": nk,
                         "entry_id": fam.get("entry_id"), "qac_root": fam.get("qac_root"),
                         "tier": fam.get("tier"), "review_status": "two_vote_certified", "votes": 2})
    base = os.path.join(CDIR, a.name)
    with open(base + ".jsonl", "w", encoding="utf-8", newline="\n") as f:
        for b in batch: f.write(json.dumps(b, ensure_ascii=False) + "\n")
    with open(base + ".provenance.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for p in prov: f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with open(os.path.join(STAGE, "form_variant_apply.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for b in batch: f.write(json.dumps(b, ensure_ascii=False) + "\n")
    print("APPLY BATCH: families=%d -> token decisions=%d (skipped already-resolved=%d)" %
          (len(approved), len(batch), skipped_already))
    print("families:", ", ".join("%s=%s" % (k, v) for k, v in list(approved.items())[:12]))

if __name__ == "__main__":
    main()
