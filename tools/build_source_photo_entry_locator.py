#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C0 — entry -> candidate source-photo page locator (from committed dataset + pages.md ranges).

The dictionary (Vocabulary of the Holy Qurʾān) is ordered verbs -> nouns -> particles; the
photographed corpus covers pages ~19-471 (0 missing). There is no committed exact entry->page index
(the draft JSONs live on the author's machine), so this emits a CANDIDATE page band per entry by
linear interpolation of the entry's global rank over the photographed page span, refined by section.
CONFIRMED locations (read off the photo) override the candidate. Output is honest: `confidence`
= verified | candidate. Lets C0 process every entry into a real bucket instead of "needs review".

Output: qamus/indexes/source_photo_entry_locator.json (pretty).
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
OUT = os.path.join(ROOT, "qamus", "indexes", "source_photo_entry_locator.json")
PAGE_MIN, PAGE_MAX = 19, 471

# CONFIRMED from direct photo reads (see source-photo-verified-samples.jsonl)
CONFIRMED = {
    "v008": {"page_image": "intake_13/IMG_7784.jpeg", "headword": "بَيَّنَ", "total_uses": 523},
    "v027": {"page_image": "intake_13/IMG_7790.jpeg", "headword": "عَبَدَ", "total_uses": 275},
}

def rank(sk):
    m = re.match(r"([vnp])(\d+)", sk or "")
    if not m: return None
    sec, n = m.group(1), int(m.group(2))
    base = {"v": 0, "n": 947, "p": 947 + 1045}[sec]
    return base + n

def main():
    ents = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    total = 2092
    loc = {}
    for e in ents:
        sk = (e.get("source_keys") or ["?"])[0]
        r = rank(sk)
        rec = {"entry_id": e["id"], "source_key": sk, "section": e.get("section"),
               "headword": e.get("headword"), "root": e.get("root"),
               "total_uses": e.get("total_uses")}
        if sk in CONFIRMED:
            rec.update({"confidence": "verified", **CONFIRMED[sk]})
        elif r:
            frac = (r - 1) / (total - 1)
            page = int(round(PAGE_MIN + frac * (PAGE_MAX - PAGE_MIN)))
            rec.update({"confidence": "candidate", "candidate_page": page,
                        "candidate_page_band": [max(PAGE_MIN, page - 6), min(PAGE_MAX, page + 6)],
                        "candidate_page_image": "pg%03d.jpeg" % page})
        else:
            rec["confidence"] = "unlocatable"
        loc[sk] = rec
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": "fusha/source-photo-entry-locator@1",
                   "note": "candidate page band by global rank over photographed span 19-471; "
                           "verified entries override. NOT an exact index (draft JSONs not committed).",
                   "page_span": [PAGE_MIN, PAGE_MAX], "entry_count": len(loc),
                   "verified": sum(1 for v in loc.values() if v["confidence"] == "verified"),
                   "locator": loc}, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    print("wrote locator: %d entries, %d verified, %d candidate" % (
        len(loc), sum(1 for v in loc.values() if v["confidence"] == "verified"),
        sum(1 for v in loc.values() if v["confidence"] == "candidate")))

if __name__ == "__main__":
    main()
