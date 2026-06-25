#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a form-variant (or any hover) batch + its provenance sidecar as a hard contract.

Public batch rows:  loc, non-empty authored gloss, src=="qamus", kind=="authored", no external source
                    name in the gloss, no `informed_by` in the PUBLIC row.
Provenance sidecar (when --provenance given): same loc set, same row count, review_status==
                    "two_vote_certified", votes>=2.
Banned regression families: hard-fail if any row glosses a known-unsafe family (فاستقيموا/نعف/جاءني/
                    أرجه/بالبنين/كذبوا/ويقتلون/ظمأ) unless --allow lists that family with per-loc reasoning.

Read-only. Exit non-zero on any defect.
"""
import argparse, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A

EXTERNAL = re.compile(r"\b(tafsir|mcp|qac|qul|tanzil|quranwbw)\b|quran\.com|corpus\.quran|sunnah\.com", re.I)
BANNED = {A.norm_strict(x) for x in ["فاستقيموا", "نعف", "جاءني", "أرجه", "بالبنين", "كذبوا", "ويقتلون", "ظمأ"]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--allow", nargs="*", default=[])
    a = ap.parse_args()
    allow = {A.norm_strict(x) for x in a.allow}
    errors = []
    pub = [json.loads(l) for l in open(a.batch, encoding="utf-8") if l.strip()]
    locs = []
    for d in pub:
        loc = d.get("loc"); g = (d.get("gloss") or "").strip()
        locs.append(loc)
        if not loc or not re.match(r"^\d+:\d+:\d+$", str(loc)):
            errors.append("bad loc %r" % loc)
        if not g:
            errors.append("%s: empty gloss" % loc)
        if d.get("src") != "qamus" or d.get("kind") != "authored":
            errors.append("%s: public record not {src:qamus,kind:authored}" % loc)
        if "informed_by" in d:
            errors.append("%s: informed_by present in PUBLIC row" % loc)
        if EXTERNAL.search(g):
            errors.append("%s: external source name in public gloss %r" % (loc, g))
        nk = A.norm_strict(d.get("surface") or d.get("key") or "")
        if nk in BANNED and nk not in allow:
            errors.append("%s: banned regression family %r (surface %s) — needs --allow with per-loc reasoning"
                          % (loc, g, d.get("surface")))
    if len(locs) != len(set(locs)):
        errors.append("duplicate locs in public batch")

    if a.provenance:
        if not os.path.exists(a.provenance):
            errors.append("provenance sidecar missing: %s" % a.provenance)
        else:
            prov = [json.loads(l) for l in open(a.provenance, encoding="utf-8") if l.strip()]
            if len(prov) != len(pub):
                errors.append("provenance row count %d != public %d" % (len(prov), len(pub)))
            if {p.get("loc") for p in prov} != set(locs):
                errors.append("provenance loc set != public loc set")
            for p in prov:
                if p.get("review_status") != "two_vote_certified":
                    errors.append("%s: review_status != two_vote_certified" % p.get("loc"))
                if (p.get("votes") or 0) < 2:
                    errors.append("%s: votes < 2" % p.get("loc"))

    if errors:
        print("FORM-VARIANT BATCH FAIL (%s):" % os.path.basename(a.batch))
        for e in errors[:30]:
            print("  -", e)
        sys.exit(1)
    print("FORM-VARIANT BATCH OK — %d rows, public-clean%s" %
          (len(pub), " + provenance parity (2-vote)" if a.provenance else ""))

if __name__ == "__main__":
    main()
