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
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092", "pending-source-triangulation-table.jsonl")

def flat(s):
    return (s or "").replace(" ", "").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ء", "").replace("ؤ", "و").replace("ئ", "ي").replace("ى", "ي")

def ascii_safe(s):
    return str(s).encode("ascii", "backslashreplace").decode("ascii")

def read_rows(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip() and '"loc"' in line]

def family_from_ledger(rows, root_flat):
    fam = collections.defaultdict(lambda: {"locs": [], "surfaces": set(), "sarf": set(), "nahw": set()})
    for r in rows:
        if r["root_cause"] != "missing_qamus_entry_candidate":
            continue
        rt = r.get("qac_root")
        if not rt or flat(rt) in root_flat:   # safety: never propose for a root that already has an entry
            continue
        f = fam[rt]
        f["locs"].append(r["loc"])
        f["surfaces"].add(r.get("surface") or r.get("surface_ar") or "")
        f["sarf"].add(r.get("sarf_procedure") or "qamus-entry-authoring")
        f["nahw"].add(r.get("nahw_procedure") or "qamus-entry-authoring")
    return fam

def family_from_table(rows, root_flat):
    fam = collections.defaultdict(lambda: {"locs": [], "surfaces": set(), "sarf": set(), "nahw": set()})
    for r in rows:
        if r.get("suggested_lane") != "new_entry_proposal":
            continue
        if r.get("gate") != "owner":
            continue
        if r.get("root_cause") != "missing_qamus_entry_candidate":
            continue
        rt = r.get("qac_root")
        if not rt or flat(rt) in root_flat:
            continue
        f = fam[rt]
        f["locs"].append(r["loc"])
        f["surfaces"].add(r.get("surface_ar") or r.get("surface") or "")
        f["sarf"].add(r.get("sarf_procedure") or "procedures/qamus-entry-authoring.md")
        f["nahw"].add(r.get("nahw_procedure") or "")
    return fam

def build_proposals(fam, min_occ):
    props = []
    for rt, f in sorted(fam.items(), key=lambda kv: -len(kv[1]["locs"])):
        if len(f["locs"]) < min_occ:
            continue
        surfaces = [s for s in sorted(f["surfaces"]) if s]
        sarf = sorted(s for s in f["sarf"] if s)
        nahw = sorted(s for s in f["nahw"] if s)
        props.append({
            "proposed_entry_id": "PROPOSE:" + flat(rt),
            "root": rt,
            "headword_candidate": surfaces[0] if surfaces else "",
            "pos": "review_required",
            "lemma_candidate": None,
            "forms_observed": surfaces[:6],
            "example_locs": f["locs"][:6],
            "occurrences": len(f["locs"]),
            "affected_token_count": len(f["locs"]),
            "expected_coverage_unlock": len(f["locs"]),
            "definition_draft": "",
            "suggested_hover_glosses": [],
            "why_existing_insufficient": "no Qamus entry for this QAC root after flattened-root reroute",
            "source_evidence_ids": ["qac:root"],
            "sarf_procedure": sarf[0] if sarf else "qamus-entry-authoring",
            "nahw_procedure": nahw[0] if nahw else "qamus-entry-authoring",
            "gate": "owner",
            "public_provenance_clean": True,
        })
    return props

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_table", default=None,
                    help="pending-source-triangulation-table.jsonl input")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "hover_stage", "new_entry_proposals.jsonl"))
    ap.add_argument("--min-occ", type=int, default=2)
    a = ap.parse_args()
    by_root = json.load(open(os.path.join(ROOT, "qamus", "indexes", "current", "by-root.json"), encoding="utf-8"))
    root_flat = {flat(r) for r in by_root}
    if a.from_table:
        fam = family_from_table(read_rows(a.from_table), root_flat)
    else:
        fam = family_from_ledger(read_rows(LED), root_flat)
    props = build_proposals(fam, a.min_occ)
    if a.min_occ:
        pass
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fo:
        for p in props:
            fo.write(json.dumps(p, ensure_ascii=False) + "\n")
    tok = sum(p["occurrences"] for p in props)
    print("NEW-ENTRY PROPOSALS: %d roots (owner-gated, review-only), covering %d tokens -> %s"
          % (len(props), tok, a.out))
    print("top:", ", ".join("%s(%d)" % (ascii_safe(p["root"]), p["occurrences"]) for p in props[:10]))

if __name__ == "__main__":
    main()
