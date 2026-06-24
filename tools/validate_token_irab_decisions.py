#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 — validate per-loc iʿrāb token decisions before apply (fail-closed, public-safe).

Each decision must: have a valid quran loc (S:A:W), a non-empty authored gloss, public record
exactly {src:qamus, kind:authored}, NO public provenance leak (no source name / informed_by in the
PUBLIC fields), and a recorded internal provenance (separate). Usage:
  python3 tools/validate_token_irab_decisions.py <decisions.jsonl>
"""
import json, re, sys

LOC = re.compile(r"^\d+:\d+:\d+$")
LEAK = re.compile(r"(tafsir|mcp|quran\.?com|tanzil|qac|informed_by|/srv/|/tmp/)", re.I)
PUBLIC_FIELDS = ("loc", "gloss", "surface", "key", "state_id", "src", "kind", "lang", "decision_state")

def main():
    path = sys.argv[1]
    errs = []; n = 0
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line: continue
        n += 1
        d = json.loads(line)
        if not LOC.match(d.get("loc", "")): errs.append(f"{i}: bad loc {d.get('loc')!r}")
        if not (d.get("gloss") or "").strip(): errs.append(f"{i}: empty gloss")
        if d.get("src") != "qamus" or d.get("kind") != "authored":
            errs.append(f"{i}: public record not {{src:qamus,kind:authored}}")
        # public fields must not leak source/provenance
        pub_blob = json.dumps({k: d.get(k) for k in PUBLIC_FIELDS if k in d}, ensure_ascii=False)
        if LEAK.search(pub_blob): errs.append(f"{i}: provenance leak in public fields")
        ip = d.get("internal_provenance")
        if not isinstance(ip, dict): errs.append(f"{i}: missing internal_provenance")
    print(f"checked {n} iʿrāb decisions")
    if errs:
        print(f"FAIL ({len(errs)}):"); [print("  -", e) for e in errs[:20]]; sys.exit(1)
    print("VALIDATE OK — iʿrāb token decisions public-safe")

if __name__ == "__main__":
    main()
