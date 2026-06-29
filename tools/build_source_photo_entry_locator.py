#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C0 — entry -> candidate source-photo page locator (from committed dataset + pages.md ranges).

The dictionary (Vocabulary of the Holy Qurʾān) is ordered verbs -> nouns -> particles; the
photographed corpus covers pages 002-471 (0 missing). There is no committed exact entry->page index
(the draft JSONs live on the author's machine), so this emits a CANDIDATE page band per entry by
linear interpolation of the entry's rank over its photographed section span.
CONFIRMED locations (read off the photo) override the candidate. Output is honest: `confidence`
= verified | candidate. Lets C0 process every entry into a real bucket instead of "needs review".

Output: qamus/indexes/source_photo_entry_locator.json (pretty).
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
OUT = os.path.join(ROOT, "qamus", "indexes", "source_photo_entry_locator.json")
SAMPLES = os.path.join(ROOT, "qamus", "reports", "source-photo-verified-samples.jsonl")

# The source photos are dictionary page numbers, not a global interpolation
# surface. The section starts are visible in the photographed corpus:
# v001/v002 on pg002, n001 on pg224, and p001 on pg453.
SECTION_SPANS = {
    "v": {"count": 947, "page_min": 2, "page_max": 223},
    "n": {"count": 1045, "page_min": 224, "page_max": 452},
    "p": {"count": 100, "page_min": 453, "page_max": 471},
}
PAGE_MIN = min(v["page_min"] for v in SECTION_SPANS.values())
PAGE_MAX = max(v["page_max"] for v in SECTION_SPANS.values())

# CONFIRMED from direct photo reads (see source-photo-verified-samples.jsonl)
CONFIRMED = {
    "v008": {"page_image": "intake_13/IMG_7784.jpeg", "headword": "بَيَّنَ", "total_uses": 523},
    "v027": {"page_image": "intake_13/IMG_7790.jpeg", "headword": "عَبَدَ", "total_uses": 275},
}

def load_confirmed():
    confirmed = {k: dict(v) for k, v in CONFIRMED.items()}
    if os.path.exists(OUT):
        try:
            prior = json.load(open(OUT, encoding="utf-8")).get("locator", {})
        except Exception:
            prior = {}
        for sk, rec in prior.items():
            if rec.get("confidence") in {"verified", "photo_verified"}:
                confirmed.setdefault(sk, {}).update(rec)
    if not os.path.exists(SAMPLES):
        return confirmed
    for line in open(SAMPLES, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("verdict") not in {"verified_correct", "verified"}:
            continue
        for sk in rec.get("source_keys") or []:
            cur = confirmed.setdefault(sk, {})
            if rec.get("page") is not None:
                cur["page"] = rec.get("page")
            if rec.get("page_image"):
                cur["page_image"] = rec.get("page_image")
            elif rec.get("source_ref") and ";" not in str(rec.get("source_ref")):
                cur.setdefault("page_image", rec.get("source_ref"))
            if rec.get("headword"):
                cur["headword"] = rec.get("headword")
            if rec.get("live_value") is not None:
                cur.setdefault("verified_value", rec.get("live_value"))
    return confirmed

def rank(sk):
    m = re.match(r"([vnp])(\d+)", sk or "")
    if not m: return None
    sec, n = m.group(1), int(m.group(2))
    base = {"v": 0, "n": 947, "p": 947 + 1045}[sec]
    return base + n

def section_page_candidate(sk):
    m = re.match(r"([vnp])(\d+)", sk or "")
    if not m:
        return None
    sec, n = m.group(1), int(m.group(2))
    span = SECTION_SPANS[sec]
    if n < 1 or n > span["count"]:
        return None
    if span["count"] == 1:
        return span["page_min"]
    frac = (n - 1) / (span["count"] - 1)
    return int(round(span["page_min"] + frac * (span["page_max"] - span["page_min"])))

def main():
    ents = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    confirmed = load_confirmed()
    total = 2092
    loc = {}
    for e in ents:
        sk = (e.get("source_keys") or ["?"])[0]
        r = rank(sk)
        rec = {"entry_id": e["id"], "source_key": sk, "section": e.get("section"),
               "headword": e.get("headword"), "root": e.get("root"),
               "total_uses": e.get("total_uses")}
        if sk in confirmed:
            rec.update({"confidence": "verified", **confirmed[sk]})
        else:
            page = section_page_candidate(sk)
            if page is None and r:
                frac = (r - 1) / (total - 1)
                page = int(round(PAGE_MIN + frac * (PAGE_MAX - PAGE_MIN)))
        if rec.get("confidence") != "verified" and page is not None:
            rec.update({"confidence": "candidate", "candidate_page": page,
                        "candidate_page_band": [max(PAGE_MIN, page - 6), min(PAGE_MAX, page + 6)],
                        "candidate_page_image": "pg%03d.jpeg" % page})
        elif rec.get("confidence") != "verified":
            rec["confidence"] = "unlocatable"
        loc[sk] = rec
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": "fusha/source-photo-entry-locator@1",
                   "note": "candidate page band by source-key rank over photographed section spans: "
                           "verbs pg002-223, nouns pg224-452, particles pg453-471; verified entries override. "
                           "NOT an exact index (draft JSONs not committed).",
                   "page_span": [PAGE_MIN, PAGE_MAX], "entry_count": len(loc),
                   "verified": sum(1 for v in loc.values() if v["confidence"] == "verified"),
                   "locator": loc}, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    print("wrote locator: %d entries, %d verified, %d candidate" % (
        len(loc), sum(1 for v in loc.values() if v["confidence"] == "verified"),
        sum(1 for v in loc.values() if v["confidence"] == "candidate")))

if __name__ == "__main__":
    main()
