#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a token-addressed hover-decision JSONL: schema, loc format, public-record invariant, precedence-safety.

Fails closed if:
  - a record lacks loc/gloss, or loc is not S:A:W;
  - src != "qamus" or kind != "authored" (public record must be clean);
  - the gloss text contains an external source name (Tafsir/QAC/Quran.com/Tanzil) — that would leak publicly;
  - duplicate loc (a token must have exactly one decision — the override is unambiguous).
internal_provenance MAY cite external sources (it never ships); the public fields may not.

Usage: python tools/validate_token_hover_decisions.py <decisions.jsonl>
"""
import json
import re
import sys

LOC = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK = ("tafsir", "qac", "quran.com", "quran-corpus", "tanzil", "corpus.quran")


def main():
    if len(sys.argv) < 2:
        print("usage: validate_token_hover_decisions.py <decisions.jsonl>"); sys.exit(2)
    path = sys.argv[1]
    errors, n, seen = [], 0, {}
    for ln_no, ln in enumerate(open(path, encoding="utf-8"), 1):
        ln = ln.strip()
        if not ln:
            continue
        n += 1
        try:
            d = json.loads(ln)
        except Exception as e:
            errors.append("line %d: bad JSON (%s)" % (ln_no, e)); continue
        loc = d.get("loc")
        if not loc or not LOC.match(str(loc)):
            errors.append("line %d: bad/missing loc %r" % (ln_no, loc))
        if not d.get("gloss"):
            errors.append("%s: missing gloss" % loc)
        if d.get("src") != "qamus" or d.get("kind") != "authored":
            errors.append("%s: public record must be src=qamus kind=authored" % loc)
        g = (d.get("gloss") or "").lower()
        if any(x in g for x in LEAK):
            errors.append("%s: gloss leaks an external source name" % loc)
        if loc in seen:
            errors.append("%s: duplicate loc (token override must be unique)" % loc)
        seen[loc] = True
    print("checked %d token decisions" % n)
    if errors:
        print("FAIL:")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    print("PASS — schema + loc format + public-record invariant + uniqueness OK")


if __name__ == "__main__":
    main()
