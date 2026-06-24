#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build qamus/indexes/existing_qamus_index.json from the COMMITTED public dataset (P0).

This makes the corpus->Qamus pipeline (corpus_to_qamus_candidates.py) dedupe against the committed
2,092-entry dataset — NOT a hidden live dependency. Reproducible from qamus/data/current/entries.jsonl.
Public-safe: no status/visibility/author fields. Keyed by qamus:<section><n> address.
"""
import json, os, re, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
# compact-machine index (named .min.json per A1 ergonomics — internal corpus dedup lookup)
OUT = os.path.join(ROOT, "qamus", "indexes", "existing_qamus_index.min.json")

def _norm(s, strict):
    if not s: return ""
    s = unicodedata.normalize("NFC", s).replace("ىٰ", "ى")
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0652: continue
        if o == 0x0670: out.append("ا"); continue
        if o == 0x0640: continue
        if 0x0653 <= o <= 0x0655: continue
        if 0x06D6 <= o <= 0x06ED: continue
        out.append(ch)
    s = "".join(out).replace("آ", "ا").replace("ٱ", "ا")
    if not strict:
        s = s.replace("أ", "").replace("إ", "").replace("ء", "").replace("ؤ", "و").replace("ئ", "ي")
    return s.replace("ى", "ي").replace("ة", "ه").replace(" ", "")

def bare(s):
    return re.sub(r"[ً-ْٰـۖ-ۭ]", "", s or "").replace("ٱ", "ا")

def main():
    idx = {}
    for line in open(DATA, encoding="utf-8"):
        e = json.loads(line)
        sk = (e.get("source_keys") or ["?"])[0]
        addr = "qamus:%s" % sk
        forms = []
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                forms += re.findall(r"[؀-ۿ]+", fstr)
        hw = e.get("headword", "")
        idx[addr] = {
            "source_address": "%s#root=%s" % (addr, e.get("root", "")),
            "entry_id": e["id"], "source_keys": e.get("source_keys", []),
            "surface_ar": hw, "norm": _norm(hw, False), "norm_strict": _norm(hw, True),
            "bare": bare(hw), "root": e.get("root", ""), "headword": hw,
            "lemma_candidate": hw, "pos_category": e.get("category", ""),
            "section": e.get("section", ""), "class": e.get("section", ""),
            "forms": sorted(set(forms)), "n_senses": len(e.get("senses", [])),
            "glosses": [s.get("gloss") for s in e.get("senses", [])],
            "total_uses": e.get("total_uses"), "tags": e.get("tags", []),
            "usage_refs": sorted({str(ex.get("ref")) for u in e.get("usage", []) for ex in u.get("examples", []) if ex.get("ref")}),
        }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(idx, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        f.write("\n")
    print("wrote %s with %d entries from committed dataset" % (os.path.relpath(OUT, ROOT), len(idx)))

if __name__ == "__main__":
    main()
