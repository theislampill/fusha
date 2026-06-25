#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a suffix/pronoun decision JSONL: loc format, possessor in gloss, enclitic present, public-record clean.

Fails closed if: bad loc; gloss does not begin with the declared possessor; missing stem/suffix; src/kind not
qamus/authored; external source name leaks into the public gloss; duplicate loc. (POS-gating against verbs happens
in the generator; this validator enforces the public/shape invariants.)

Usage: python tools/validate_suffix_pronoun_decisions.py <decisions.jsonl>
"""
import json
import re
import sys

LOC = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK = ("tafsir", "qac", "quran.com", "tanzil", "corpus.quran")


def main():
    if len(sys.argv) < 2:
        print("usage: validate_suffix_pronoun_decisions.py <jsonl>"); sys.exit(2)
    errors, n, seen = [], 0, set()
    for ln_no, ln in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
        ln = ln.strip()
        if not ln:
            continue
        n += 1
        try:
            d = json.loads(ln)
        except Exception as e:
            errors.append("line %d: bad JSON (%s)" % (ln_no, e)); continue
        loc, g = d.get("loc"), (d.get("gloss") or "")
        if not loc or not LOC.match(str(loc)):
            errors.append("line %d: bad loc %r" % (ln_no, loc))
        poss = d.get("possessor")
        # allow a tightly controlled leading conjunction/preposition before the possessor (and/for/with/
        # by/to/so/then), case-insensitively; still require the possessor word present at the head (F13).
        gl = g.lower().strip()
        for _pre in ("and ", "for ", "with ", "by ", "to ", "so ", "then "):
            if gl.startswith(_pre):
                gl = gl[len(_pre):]; break
        if not poss or not gl.startswith(poss.lower()):
            errors.append("%s: gloss %r must begin with possessor %r (after an optional and/for/with/by/to/so/then)" % (loc, g, poss))
        if not d.get("stem") or not d.get("suffix"):
            errors.append("%s: missing stem/suffix" % loc)
        if d.get("src") != "qamus" or d.get("kind") != "authored":
            errors.append("%s: public record must be src=qamus kind=authored" % loc)
        if any(x in g.lower() for x in LEAK):
            errors.append("%s: gloss leaks an external source name" % loc)
        if loc in seen:
            errors.append("%s: duplicate loc" % loc)
        seen.add(loc)
    print("checked %d suffix/pronoun decisions" % n)
    if errors:
        print("FAIL:")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    print("PASS — loc + possessor-in-gloss + stem/suffix + public-record + no-leak + uniqueness OK")


if __name__ == "__main__":
    main()
