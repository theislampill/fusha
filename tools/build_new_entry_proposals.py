#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4B — missing-entry proposal generator (OWNER-GATED, review-only).

Reads `missing_qamus_entry_candidate` rows (recurring QAC roots with no Qamus entry, AFTER the
flattened-root reroute), groups by root, and emits owner-gated entry proposals. NEVER applies, NEVER
creates a live entry, NEVER authors a public gloss for live use. أتي/رأي are excluded (they have
entries). The dr05 recurring families (سوء/رضو/جيأ/زكو/صلو/أخو/ربب…) surface here only if the current
ledger still supports them. Read-only.
"""
import argparse, json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A
LED = os.path.join(ROOT, "qamus", "reports", "closure-2092", "blocker-root-cause-ledger.jsonl")
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")

def flat(s):
    return (s or "").replace(" ", "").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ء", "").replace("ؤ", "و").replace("ئ", "ي").replace("ى", "ي")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "hover_stage", "new_entry_proposals.jsonl"))
    ap.add_argument("--min-occ", type=int, default=2)
    a = ap.parse_args()
    by_root = json.load(open(os.path.join(ROOT, "qamus", "indexes", "current", "by-root.json"), encoding="utf-8"))
    root_flat = {flat(r) for r in by_root}
    rows = [json.loads(l) for l in open(LED, encoding="utf-8") if l.strip() and '"loc"' in l]
    fam = collections.defaultdict(lambda: {"locs": [], "surfaces": set()})
    for r in rows:
        if r["root_cause"] != "missing_qamus_entry_candidate":
            continue
        rt = r.get("qac_root")
        if not rt or flat(rt) in root_flat:   # safety: never propose for a root that already has an entry
            continue
        f = fam[rt]; f["locs"].append(r["loc"]); f["surfaces"].add(r["surface"])
    props = []
    for rt, f in sorted(fam.items(), key=lambda kv: -len(kv[1]["locs"])):
        if len(f["locs"]) < a.min_occ:
            continue
        props.append({
            "proposed_entry_id": "PROPOSE:" + flat(rt),
            "root": rt, "headword_candidate": sorted(f["surfaces"])[0], "pos": "review_required",
            "lemma_candidate": None, "forms_observed": sorted(f["surfaces"])[:6],
            "example_locs": f["locs"][:6], "occurrences": len(f["locs"]),
            "definition_draft": "", "why_existing_insufficient": "no Qamus entry for this QAC root after flattened-root reroute",
            "source_evidence_ids": ["qac:root"], "sarf_procedure": "qamus-entry-authoring",
            "nahw_procedure": "qamus-entry-authoring", "gate": "owner", "public_provenance_clean": True})
    if a.min_occ:
        pass
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fo:
        for p in props:
            fo.write(json.dumps(p, ensure_ascii=False) + "\n")
    tok = sum(p["occurrences"] for p in props)
    print("NEW-ENTRY PROPOSALS: %d roots (owner-gated, review-only), covering %d tokens -> %s"
          % (len(props), tok, a.out))
    print("top:", ", ".join("%s(%d)" % (p["root"], p["occurrences"]) for p in props[:10]))

if __name__ == "__main__":
    main()
