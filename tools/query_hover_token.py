#!/usr/bin/env python3
"""Inspect any hover token's terminal audit state — offline, from the committed repo.

Loads qamus/reports/hover-token-audit-full.jsonl (lazy, line scan) + by-quran-ref to join
the āyah-level entry_contexts, and resolves next_action from the blocker map.

  python3 tools/query_hover_token.py 2:139:2
  python3 tools/query_hover_token.py 1:4:1
  python3 tools/query_hover_token.py --blocker stem_base_unknown --limit 10
  python3 tools/query_hover_token.py --ayah 9:69          # all tokens of one āyah
"""
import argparse, json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT,"qamus","reports","hover-token-audit-full.jsonl")
IDX = os.path.join(ROOT,"qamus","indexes","current")

NEXT_ACTION = {
    "stem_base_unknown": "author the host stem/lexeme in Qamus, then re-run the resolver",
    "source_entry_unverified": "add the inflected form to the entry forms[] (or verify from source photo) and re-run",
    "same_surface_polysemy_requires_i3rab": "author a per-loc token-addressed decision (iʿrāb) selecting the sense",
    "proper_noun_no_qamus_entry": "create a proper-noun entry or token-address as a proper noun (no gloss)",
}

def by_ref(sa):
    d = json.load(open(os.path.join(IDX,"by-quran-ref.json"),encoding="utf-8"))
    return d.get(sa, [])

def enrich(row):
    sa = ":".join(row["quran_loc"].split(":")[:2])
    row["entry_contexts"] = by_ref(sa)
    if row.get("blocker"):
        row["next_action"] = NEXT_ACTION.get(row["blocker"])
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("loc", nargs="?")
    ap.add_argument("--blocker"); ap.add_argument("--ayah"); ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    out = []
    with open(AUDIT, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if a.loc and r["quran_loc"] == a.loc:
                print(json.dumps(enrich(r), ensure_ascii=False, indent=1)); return
            if a.ayah and ":".join(r["quran_loc"].split(":")[:2]) == a.ayah:
                out.append(r)
            elif a.blocker and r.get("blocker") == a.blocker:
                out.append(r)
                if len(out) >= a.limit: break
    if a.ayah:
        print(json.dumps({"ayah": a.ayah, "entry_contexts": by_ref(a.ayah),
                          "tokens": out}, ensure_ascii=False, indent=1)); return
    if a.blocker:
        print(json.dumps({"blocker": a.blocker, "next_action": NEXT_ACTION.get(a.blocker),
                          "sample": out}, ensure_ascii=False, indent=1)); return
    if a.loc:
        print(json.dumps({"loc": a.loc, "error": "not found"})); sys.exit(1)
    ap.print_help()

if __name__ == "__main__":
    main()
