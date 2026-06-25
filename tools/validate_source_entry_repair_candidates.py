#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate source-entry repair candidates (Phase 4C): field-level repair, gated, no blind add_form,
no live mutation, no copied external text. Read-only. Usage: <jsonl>."""
import json, os, re, sys
EXTERNAL = re.compile(r"\b(tafsir|mcp|qac:gloss|qul|tanzil|quranwbw)\b|quran\.com|sunnah\.com", re.I)
def main():
    if len(sys.argv) < 2:
        print("usage: validate_source_entry_repair_candidates.py <jsonl>"); sys.exit(2)
    p = sys.argv[1]
    if not os.path.exists(p):
        print("SOURCE-ENTRY REPAIR FAIL: missing", p); sys.exit(1)
    errors = 0; n = 0
    for l in open(p, encoding="utf-8"):
        l = l.strip()
        if not l: continue
        d = json.loads(l); n += 1
        if not d.get("target_entry"):
            print("  missing target_entry"); errors += 1
        if d.get("gate") not in ("two_vote", "source", "owner"):
            print("  %s: bad gate %r" % (d.get("target_entry"), d.get("gate"))); errors += 1
        if d.get("public_provenance_clean") is not True:
            print("  %s: public_provenance_clean != true" % d.get("target_entry")); errors += 1
        if EXTERNAL.search(json.dumps(d, ensure_ascii=False)):
            print("  %s: external source reference present" % d.get("target_entry")); errors += 1
        # no authored gloss field allowed in a repair candidate (repair != gloss authoring)
        if "gloss" in d or "public_gloss" in d:
            print("  %s: repair candidate must not carry a gloss (no blind add_form)" % d.get("target_entry")); errors += 1
    if errors:
        print("SOURCE-ENTRY REPAIR FAIL — %d error(s)/%d" % (errors, n)); sys.exit(1)
    print("SOURCE-ENTRY REPAIR OK — %d field-level repair candidates, gated, no blind add_form, no leak" % n)
if __name__ == "__main__":
    main()
