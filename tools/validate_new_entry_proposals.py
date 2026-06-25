#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate new-entry proposals (Phase 4B): owner-gated, review-only; no live apply; no proposal for a
root that already has an entry; no copied external text; no public gloss authored. Read-only."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def flat(s):
    return (s or "").replace(" ", "").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ء", "").replace("ؤ", "و").replace("ئ", "ي").replace("ى", "ي")
def main():
    if len(sys.argv) < 2:
        print("usage: validate_new_entry_proposals.py <jsonl>"); sys.exit(2)
    p = sys.argv[1]
    if not os.path.exists(p):
        print("NEW-ENTRY FAIL: missing", p); sys.exit(1)
    by_root = json.load(open(os.path.join(ROOT, "qamus", "indexes", "current", "by-root.json"), encoding="utf-8"))
    rootflat = {flat(r) for r in by_root}
    errors = 0; n = 0
    for l in open(p, encoding="utf-8"):
        l = l.strip()
        if not l: continue
        d = json.loads(l); n += 1
        if d.get("gate") != "owner":
            print("  %s: gate != owner" % d.get("root")); errors += 1
        if d.get("public_provenance_clean") is not True:
            print("  %s: public_provenance_clean != true" % d.get("root")); errors += 1
        if (d.get("definition_draft") or "").strip():
            print("  %s: definition_draft must be blank (owner authors)" % d.get("root")); errors += 1
        if d.get("root") and flat(d["root"]) in rootflat:
            print("  %s: proposes a root that ALREADY has an entry (must not)" % d.get("root")); errors += 1
        if not str(d.get("proposed_entry_id", "")).startswith("PROPOSE:"):
            print("  %s: proposed_entry_id must be PROPOSE:* (not a live id)" % d.get("root")); errors += 1
    if errors:
        print("NEW-ENTRY PROPOSALS FAIL — %d error(s)/%d" % (errors, n)); sys.exit(1)
    print("NEW-ENTRY PROPOSALS OK — %d owner-gated review-only proposals (no live id, no draft gloss, root-clean)" % n)
if __name__ == "__main__":
    main()
