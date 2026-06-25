#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a token-addressed hover-decision JSONL: schema, loc format, public-record invariant, precedence-safety.

Fails closed if:
  - a record lacks loc/gloss, or loc is not S:A:W;
  - src != "qamus" or kind != "authored" (public record must be clean);
  - --require-lang-en is set and lang != "en" (required for public/runtime export);
  - the gloss text contains an external source name (Tafsir/QAC/Quran.com/Tanzil) — that would leak publicly;
  - duplicate loc (a token must have exactly one decision — the override is unambiguous).
internal_provenance MAY cite external sources (it never ships); the public fields may not.

Usage: python tools/validate_token_hover_decisions.py [--require-lang-en] <decisions.jsonl>
"""
import argparse
import json
import re
import sys
from pathlib import Path

LOC = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK = ("tafsir", "qac", "quran.com", "quran-corpus", "tanzil", "corpus.quran")
GATES = {"auto_safe", "two_vote_required", "human_source_review_required", "never_auto_resolve"}
REVIEW_FIELDS = {"gate", "reasoning", "internal_provenance"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("decisions", help="token-addressed hover-decision JSONL")
    ap.add_argument(
        "--require-lang-en",
        action="store_true",
        help="enforce lang='en' for public/runtime export; legacy internal mirrors may omit it",
    )
    a = ap.parse_args()
    path = a.decisions
    strict_linguistic = "andon_hover_regression_repairs" in Path(path).name
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
        if a.require_lang_en and d.get("lang") != "en":
            errors.append("%s: public/runtime export record must set lang=en" % loc)
        has_review_fields = bool(REVIEW_FIELDS & set(d))
        if strict_linguistic:
            for field in ("surface", "decision_state", "gate", "reasoning"):
                if not d.get(field):
                    errors.append("%s: linguistic decision missing %s" % (loc, field))
        if strict_linguistic or has_review_fields:
            if d.get("gate") and d.get("gate") not in GATES:
                errors.append("%s: unknown gate %r" % (loc, d.get("gate")))
            if strict_linguistic and "internal_provenance" in d and not isinstance(d.get("internal_provenance"), list):
                errors.append("%s: internal_provenance must be a list when present" % loc)
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
