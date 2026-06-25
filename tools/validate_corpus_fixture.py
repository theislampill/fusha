#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F16 — validate a corpus-to-Qamus fixture run is read-only and translation-clean, and that Ṣaḥīḥayn
stays plan-only. Read-only. Usage: validate_corpus_fixture.py <out_dir>. Exit non-zero on any defect.
"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND_REQ = ["source_address", "surface_ar", "norm_strict", "classification", "candidate_action", "live_write"]
HOVER_REQ = ["norm_key", "surfaces", "occurrences", "status", "recommended_gate", "live_write"]
BANNED_FIELDS = {"en", "translation", "tafsir", "meaning", "notes_public", "gloss_en_authored"}

def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def main():
    if len(sys.argv) < 2:
        print("usage: validate_corpus_fixture.py <out_dir>"); sys.exit(2)
    d = sys.argv[1]
    errors = []
    cand_p = os.path.join(d, "corpus_to_qamus_candidates.jsonl")
    hov_p = os.path.join(d, "corpus_hover_decisions_worklist.jsonl")
    for p in (cand_p, hov_p):
        if not os.path.exists(p):
            errors.append("missing fixture output: %s" % p)
    if errors:
        print("CORPUS FIXTURE FAIL:"); [print("  -", e) for e in errors]; sys.exit(1)

    for p, req in ((cand_p, CAND_REQ), (hov_p, HOVER_REQ)):
        for i, r in enumerate(jl(p), 1):
            if r.get("live_write") is not False:
                errors.append("%s:%d live_write != false" % (os.path.basename(p), i))
            for k in req:
                if k not in r:
                    errors.append("%s:%d missing field %s" % (os.path.basename(p), i, k)); break
            for bad in BANNED_FIELDS & set(r.keys()):
                errors.append("%s:%d translation-like field %r present" % (os.path.basename(p), i, bad))
            sa = str(r.get("source_address", ""))
            if "source_address" in r and not re.match(r"^corpus:", sa):
                errors.append("%s:%d source_address %r not corpus:* scoped" % (os.path.basename(p), i, sa))

    # Ṣaḥīḥayn stays plan-only
    sah = os.path.join(ROOT, "corpora", "sahihayn")
    if os.path.isdir(sah):
        non_plan = [f for f in os.listdir(sah) if f not in ("PLAN.md",) and not f.startswith(".")]
        if non_plan:
            errors.append("corpora/sahihayn contains non-PLAN files (must stay plan-only): %s" % non_plan)

    if errors:
        print("CORPUS FIXTURE FAIL:")
        for e in errors[:30]:
            print("  -", e)
        sys.exit(1)
    print("CORPUS FIXTURE OK — read-only (0 live writes), schema valid, no translation leakage, Ṣaḥīḥayn plan-only")

if __name__ == "__main__":
    main()
