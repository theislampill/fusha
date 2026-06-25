#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the host-lexeme apply batch from the 2-vote result (per-loc).

Reads {approved:[{loc,gloss}]} + the candidate file (loc -> surface/stem/suffix/possessor/...),
emits suffix_pronoun_decision rows in the live schema. Enforces the validator invariant: the gloss
MUST begin with the possessor (optionally after and/for/with/by/to/so/then) — rows that don't are
dropped (reported), never forced.

Outputs:
  qamus/candidates/qamus_2092/<name>.jsonl + .provenance.jsonl
  out/hover_stage/host_lexeme_apply.jsonl  (append to live)
"""
import argparse, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "out", "hover_stage")
CAND = os.path.join(STAGE, "host_lexeme_next.jsonl")
CDIR = os.path.join(ROOT, "qamus", "candidates", "qamus_2092")
LEAD = re.compile(r"^(and|for|with|by|to|so|then)\s+", re.I)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved", required=True)
    ap.add_argument("--name", default="host_lexeme_batch_002")
    a = ap.parse_args()
    approved = {d["loc"]: d["gloss"].strip() for d in json.load(open(a.approved, encoding="utf-8"))["approved"] if d.get("gloss", "").strip()}
    cand = {}
    for ln in open(CAND, encoding="utf-8"):
        ln = ln.strip()
        if ln:
            r = json.loads(ln); cand[r["loc"]] = r
    batch, prov = [], []
    dropped = []
    for loc, gloss in approved.items():
        c = cand.get(loc)
        if not c:
            continue
        poss = (c.get("possessor") or "").strip().lower()
        g2 = LEAD.sub("", gloss.lower())
        if poss and not g2.startswith(poss):
            dropped.append((loc, gloss, poss)); continue   # validator would reject — drop, don't force
        batch.append({
            "loc": loc, "gloss": gloss, "surface": c.get("surface"),
            "state_id": "state:tok:%s" % loc, "src": "qamus", "kind": "authored", "lang": "en",
            "stem": c.get("host_stem"), "suffix": c.get("suffix"), "possessor": c.get("possessor"),
            "person": str(c.get("person") or ""), "number": c.get("number"),
            "decision_state": "suffix_pronoun_decision",
            "internal_provenance": {"informed_by": ["qac", "qamus-dataset"],
                                    "method": "host-lexeme authored (sarf suffix-pronoun + noun) + nahw pronoun-attachment; 2-vote certified"},
        })
        prov.append({"loc": loc, "gloss": gloss, "surface": c.get("surface"),
                     "stem": c.get("host_stem"), "qac_root": c.get("root"),
                     "review_status": "two_vote_certified", "votes": 2})
    base = os.path.join(CDIR, a.name)
    with open(base + ".jsonl", "w", encoding="utf-8", newline="\n") as f:
        for b in batch: f.write(json.dumps(b, ensure_ascii=False) + "\n")
    with open(base + ".provenance.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for p in prov: f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with open(os.path.join(STAGE, "host_lexeme_apply.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for b in batch: f.write(json.dumps(b, ensure_ascii=False) + "\n")
    print("HOST-LEXEME APPLY: approved=%d -> rows=%d dropped_not_possessor_lead=%d" % (len(approved), len(batch), len(dropped)))
    for loc, g, p in dropped[:6]:
        print("  drop", loc, repr(g), "expected lead", repr(p))

if __name__ == "__main__":
    main()
