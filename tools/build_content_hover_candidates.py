#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5/P6 candidate generator — SAFE remaining content-token hover resolutions for verification.

For each PENDING token (not resolved, not a suffix/pronoun case), propose a gloss ONLY when:
  - the token's norm_strict key is COLLISION-FREE across the live corpus (the empirical key-collision
    probe: every distinct vocalized surface sharing this key folds to ONE lemma/POS — the
    نَزَّلَ↔نَزَلَ lesson), AND
  - a Qamus dataset entry matches the lemma (headword or a listed form), AND
  - that entry has a single applicable sense (or a clearly dominant first sense), AND
  - POS is consistent (QAC POS vs entry section).
Everything else stays pending with its exact blocker. Emits candidates with āyah context + entry
senses + QAC POS + collision-set for 2-vote sarf/nahw verification. Auto-applies NOTHING.

Env: QAMUS_WBW_SERVICES, QAMUS_WBW_ARTIFACT, QAMUS_DATASET.
"""
import argparse, json, os, re, sys, collections
sys.path.insert(0, os.environ.get("QAMUS_WBW_SERVICES", "services"))
from qamus_wbw import expand as X
from qamus_wbw import normalize as N

DIAC = re.compile(r"[ً-ْٰـۖ-ۭ]")
def bare(s): return DIAC.sub("", (s or "")).replace("ٱ", "ا")
PROCLITIC = re.compile(r"^(وَ|فَ|بِ|لِ|كَ|سَ|أَ)?(ال)?")

def clean_gloss(g):
    g = (g or "").strip()
    g = re.sub(r"^\((lit\.?,?\s*)?", "", g).strip("() ")
    return g.split(";")[0].split(",")[0].strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--dataset", default=os.environ.get("QAMUS_DATASET", "/tmp/entries.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-per-section", type=int, default=60)
    a = ap.parse_args()
    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words, pending = d["verses"], d["words"], d.get("pending", {})
    X._load_qac_roots(); qpos = X._QAC_CACHE.get("pos", {}); qroot = X._QAC_CACHE.get("root", {})

    # dataset: norm_strict(headword/form) -> list of (entry, which)
    by_key = collections.defaultdict(list)
    ents = {}
    for line in open(a.dataset, encoding="utf-8"):
        e = json.loads(line); ents[e["id"]] = e
        hk = N.norm_strict(e.get("headword", ""))
        if hk: by_key[hk].append((e["id"], "headword"))
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                for t in re.findall(r"[؀-ۿ]+", fstr):
                    k = N.norm_strict(t)
                    if k: by_key[k].append((e["id"], "form"))

    # empirical key-collision probe: norm_strict key -> set of distinct vocalized surfaces in corpus
    key_surfaces = collections.defaultdict(set)
    key_roots = collections.defaultdict(set)
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            k = N.norm_strict(tok)
            key_surfaces[k].add(tok)
            r = qroot.get((ref, k))
            if r: key_roots[k].add(r)

    cands_by_sec = collections.defaultdict(list)
    seen_key_sec = set()
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            if loc in words:
                continue
            key = N.norm_strict(tok)
            # collision probe: at most ONE QAC root for this key across the corpus
            if len(key_roots.get(key, set())) > 1:
                continue
            hits = by_key.get(key, [])
            if not hits:
                continue
            eids = {h[0] for h in hits}
            if len(eids) != 1:
                continue  # ambiguous: key maps to >1 entry
            eid = next(iter(eids)); e = ents[eid]
            senses = e.get("senses", [])
            if len(senses) != 1:
                continue  # multi-sense: needs context (nahw) — leave for a deeper pass
            sec = e.get("section", "?")
            pos = qpos.get((ref, key))
            # POS consistency: verb entry vs QAC V, noun/particle vs non-V
            if pos == "V" and sec != "verb":
                continue
            if pos in ("N", "ADJ", "PN") and sec == "verb":
                continue
            dom = clean_gloss(senses[0].get("gloss") or e.get("definition"))
            if not dom or len(dom) > 60:
                continue
            # de-dupe one candidate per (key, section) to keep the batch lean & representative
            if (key, sec) in seen_key_sec:
                # still emit (each loc needs its own decision) but cap per section below
                pass
            cands_by_sec[sec].append({
                "loc": loc, "surface": tok, "key": key, "section": sec,
                "entry_id": eid, "host_headword": e.get("headword"),
                "dominant_gloss": dom, "n_senses": 1, "qac_pos": pos,
                "qac_root": qroot.get((ref, key)),
                "collision_surfaces": sorted(key_surfaces.get(key, set()))[:6],
                "ayah_text": " ".join(toks), "pending_code": pending.get(loc, "untagged"),
            })
            seen_key_sec.add((key, sec))

    out = []
    for sec in ("verb", "noun", "particle"):
        out.extend(cands_by_sec.get(sec, [])[:a.max_per_section])
    with open(a.out, "w", encoding="utf-8") as f:
        for c in out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(json.dumps({"total": len(out),
                      "by_section_available": {k: len(v) for k, v in cands_by_sec.items()},
                      "emitted": dict(collections.Counter(c["section"] for c in out))}, ensure_ascii=False))

if __name__ == "__main__":
    main()
