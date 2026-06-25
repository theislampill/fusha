#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate verb-clitic candidates (Phase 4A): every row is a verb (qac_pos==V) with an enclitic
object/subject pronoun, NEVER a possessed-noun host; no public gloss authored (gloss_draft blank);
gate=two_vote; public_provenance_clean. Read-only. Usage: validate_verb_clitic_candidates.py <jsonl>.
"""
import json, os, re, sys
def main():
    if len(sys.argv) < 2:
        print("usage: validate_verb_clitic_candidates.py <jsonl>"); sys.exit(2)
    p = sys.argv[1]
    if not os.path.exists(p):
        print("VERB-CLITIC FAIL: file missing", p); sys.exit(1)
    errors = 0; n = 0
    for ln, line in enumerate(open(p, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line); n += 1
        loc = d.get("loc")
        if not re.match(r"^\d+:\d+:\d+$", str(loc)):
            print("  bad loc", loc); errors += 1
        if d.get("qac_pos") != "V":
            print("  %s: qac_pos != V (verb-clitic lane is verbs only)" % loc); errors += 1
        if not d.get("enclitic"):
            print("  %s: missing enclitic" % loc); errors += 1
        if not d.get("pronoun_person"):
            print("  %s: missing pronoun_person" % loc); errors += 1
        if d.get("clitic_role") == "possessive" or d.get("root_cause") == "host_lexeme_possessive_candidate":
            print("  %s: routed to possessive lane (forbidden — verb enclitic is object/subject)" % loc); errors += 1
        if (d.get("gloss_draft") or "").strip():
            print("  %s: gloss_draft must be blank (no authoring in this lane)" % loc); errors += 1
        if d.get("gate") != "two_vote":
            print("  %s: gate != two_vote" % loc); errors += 1
        if d.get("public_provenance_clean") is not True:
            print("  %s: public_provenance_clean != true" % loc); errors += 1
    if errors:
        print("VERB-CLITIC CANDIDATES FAIL — %d error(s) in %d rows" % (errors, n)); sys.exit(1)
    print("VERB-CLITIC CANDIDATES OK — %d review-only rows, verb-only, no gloss authored, 2-vote gated" % n)

if __name__ == "__main__":
    main()
