#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4C — source-entry repair candidate generator (review-only; source/owner-gated).

Modes:
  --mode forms_array   : forms_array_missing_surface -> propose adding the inflected form to forms[]
  --mode quran_refs    : quran_refs_missing_or_incomplete -> propose adding the āyah ref to the entry
  --mode source_photo  : source_photo_visual_needed -> queue for source-photo visual verification

Emits field-level before/after repair candidates with affected locs. NO blind add_form (every row keeps
gate=two_vote/source/owner and an authored gloss is NOT produced here). NO live mutation. Read-only.
"""
import argparse, json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A
LED = os.path.join(ROOT, "qamus", "reports", "closure-2092", "blocker-root-cause-ledger.jsonl")
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
MODE_RC = {"forms_array": "forms_array_missing_surface", "quran_refs": "quran_refs_missing_or_incomplete",
           "source_photo": "source_photo_visual_needed"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=list(MODE_RC))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(ROOT, "out", "hover_stage", "source_entry_repair_%s.jsonl" % a.mode)
    ent = {json.loads(l)["id"]: json.loads(l) for l in open(DATA, encoding="utf-8")}
    rows = [json.loads(l) for l in open(LED, encoding="utf-8") if l.strip() and '"loc"' in l]
    rc = MODE_RC[a.mode]
    by_entry = collections.defaultdict(lambda: {"locs": [], "surfaces": set()})
    for r in rows:
        if r["root_cause"] != rc:
            continue
        tgt = r.get("host_entry") or r.get("root_entry")
        if not tgt:
            continue
        d = by_entry[tgt]; d["locs"].append(r["loc"]); d["surfaces"].add(r["surface"])
    cands = []
    for eid, d in sorted(by_entry.items(), key=lambda kv: -len(kv[1]["locs"])):
        e = ent.get(eid, {})
        rec = {"target_entry": eid, "root": e.get("root"), "headword": e.get("headword"),
               "affected_locs": d["locs"][:8], "occurrences": len(d["locs"]),
               "repair_type": a.mode, "public_provenance_clean": True}
        if a.mode == "forms_array":
            rec.update({"field": "usage[].forms", "before": "(surface absent)",
                        "after_proposed": sorted(d["surfaces"])[:6],
                        "gate": "two_vote", "note": "POS-correct authored gloss still required at 2-vote; not a blind add_form"})
        elif a.mode == "quran_refs":
            rec.update({"field": "usage[].examples[].ref", "before": "(ref absent)",
                        "after_proposed_refs": sorted({":".join(l.split(":")[:2]) for l in d["locs"]})[:8],
                        "gate": "source", "note": "entry-completeness; verify against source before adding"})
        else:
            rec.update({"field": "source_photo", "status": "needs_visual",
                        "gate": "source", "note": "head-on crop visual verification; never infer unreadable digits"})
        cands.append(rec)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fo:
        for c in cands:
            fo.write(json.dumps(c, ensure_ascii=False) + "\n")
    print("SOURCE-ENTRY REPAIR (%s): %d entry candidates, %d tokens -> %s"
          % (a.mode, len(cands), sum(c["occurrences"] for c in cands), out))

if __name__ == "__main__":
    main()
