#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4A — verb-clitic object/subject candidate generator (review-only).

Reads `verb_clitic_object_or_subject_candidate` rows from the root-cause ledger (a verb + an attached
object/subject pronoun — NEVER a possessed-noun host) and emits review-only candidates with the verb
stem, enclitic, and pronoun person/gender/number. Per the nahw skill, a verb's enclitic is object/
subject, not possessive. NO public gloss is authored here (`gloss_draft` stays blank until a 2-vote
certifies). Rejects tanwīn-alif / particle bundles. Read-only. Owner/2-vote gate downstream.
"""
import argparse, json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A
LED = os.path.join(ROOT, "qamus", "reports", "closure-2092", "blocker-root-cause-ledger.jsonl")

# enclitic pronoun -> (person, gender, number); longest-first match on the bare surface
ENCL = [("كما", ("2", "m/f", "dual")), ("هما", ("3", "m/f", "dual")), ("كنّ", ("2", "f", "plural")),
        ("هنّ", ("3", "f", "plural")), ("كم", ("2", "m", "plural")), ("هم", ("3", "m", "plural")),
        ("نا", ("1", "m/f", "plural")), ("ها", ("3", "f", "singular")), ("هن", ("3", "f", "plural")),
        ("كن", ("2", "f", "plural")), ("ني", ("1", "m/f", "singular")), ("ه", ("3", "m", "singular")),
        ("ك", ("2", "m/f", "singular")), ("ي", ("1", "m/f", "singular"))]
PARTICLE_PREFIX = ("وإن", "وأن", "فإن", "وأنا", "فإنما", "وله", "فله", "بكم", "فهل")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "hover_stage", "verb_clitic_cand.jsonl"))
    ap.add_argument("--max", type=int, default=0)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(LED, encoding="utf-8") if l.strip() and '"loc"' in l]
    cands, skipped = [], collections.Counter()
    for r in rows:
        if r["root_cause"] != "verb_clitic_object_or_subject_candidate":
            continue
        surf = r["surface"]; nk = r["nk"]
        if A.ends_tanwin_alef(surf) if hasattr(A, "ends_tanwin_alef") else nk.endswith("ا"):
            skipped["tanwin_alef"] += 1; continue
        if any(nk.startswith(p) for p in PARTICLE_PREFIX):
            skipped["particle_bundle"] += 1; continue
        bare = A.norm_lenient(surf)
        pgn = None; enc = None
        for e, meta in ENCL:
            be = A.norm_lenient(e)
            if be and bare.endswith(be) and len(bare) > len(be) + 1:
                enc = e; pgn = meta; break
        if not enc:
            skipped["no_enclitic"] += 1; continue
        stem = surf  # display stem is the surface minus the enclitic glyphs (kept vocalized for review)
        cands.append({
            "loc": r["loc"], "surface": surf, "verb_stem": stem,
            "root": r.get("qac_root"), "lemma_candidate": None, "qac_pos": "V",
            "enclitic": enc, "pronoun_person": pgn[0], "pronoun_gender": pgn[1], "pronoun_number": pgn[2],
            "clitic_role": "object", "gloss_draft": "", "sarf_procedure": "verb-form",
            "nahw_procedure": "preposition-pronoun", "risk": "MEDIUM", "gate": "two_vote",
            "public_provenance_clean": True})
    if a.max:
        cands = cands[:a.max]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for c in cands:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print("VERB-CLITIC CANDIDATES: %d review-only (no gloss authored); skipped %s -> %s"
          % (len(cands), dict(skipped), a.out))

if __name__ == "__main__":
    main()
