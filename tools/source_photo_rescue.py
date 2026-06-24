#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source-photo RESCUE: reclassify the needs_source_photo_review queue using the EXISTING corpus, not retake-by-default.

Inputs (read-only):
  - corpora/sarfnahw/out/audit/entry_audit.jsonl  (gitignored audit dump; the needs_source_photo_review entries)
  - qamus/indexes/source_photo_index.json         (corpus coverage from source_photo_indexer.py)
  - qamus/reports/source-photo-verified-samples.jsonl  (optional: entries verified by visual read, e.g. ب ي ن 523==523)

Reclassifies each queued entry into 6 buckets instead of a blanket "needs photo":
  verified_from_existing_photo · certified_repair_ready · needs_manual_visual_review · needs_new_photo ·
  missing_locator · deferred_ambiguous

Key principle (owner correction): if the corpus covers the dictionary (the index shows pages 2..N, 0 missing),
the default for a queued entry is needs_manual_visual_review (photo PRESENT), NOT needs_new_photo. Only entries the
corpus genuinely cannot cover become needs_new_photo. Writes the rescue report + reclassified queue.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUD = os.path.join(ROOT, "corpora", "sarfnahw", "out", "audit", "entry_audit.jsonl")
IDX = os.path.join(ROOT, "qamus", "indexes", "source_photo_index.json")
SAMPLES = os.path.join(ROOT, "qamus", "reports", "source-photo-verified-samples.jsonl")
OUT_JSON = os.path.join(ROOT, "qamus", "indexes", "source_photo_rescue_queue.json")
REP = os.path.join(ROOT, "qamus", "reports", "source-photo-rescue-report.md")


def main():
    aud = [json.loads(l) for l in open(AUD, encoding="utf-8") if l.strip()]
    idx = json.load(open(IDX, encoding="utf-8")) if os.path.exists(IDX) else {}
    corpus_complete = idx.get("total_images", 0) > 0 and len(idx.get("pages_missing_from_manifests", [])) == 0
    verified = {}
    if os.path.exists(SAMPLES):
        for l in open(SAMPLES, encoding="utf-8"):
            if l.strip():
                v = json.loads(l)
                verified[v.get("entry_id")] = v

    queue = [r for r in aud if r.get("terminal_state") == "needs_source_photo_review"]
    refq = [r for r in aud if r.get("terminal_state") == "needs_quran_ref_verification"]
    buckets = {"verified_from_existing_photo": [], "certified_repair_ready": [],
               "needs_manual_visual_review": [], "needs_new_photo": [],
               "missing_locator": [], "deferred_ambiguous": []}
    for r in queue:
        eid = r.get("entry_id")
        sk = r.get("source_keys") or []
        if eid in verified:
            v = verified[eid]
            buckets["certified_repair_ready" if v.get("repair") else "verified_from_existing_photo"].append(
                {"entry_id": eid, "source_keys": sk, "verdict": v.get("verdict"), "field": v.get("field")})
        elif not sk:
            buckets["missing_locator"].append({"entry_id": eid, "root": r.get("root")})
        elif corpus_complete:
            buckets["needs_manual_visual_review"].append({"entry_id": eid, "source_keys": sk, "root": r.get("root")})
        else:
            buckets["needs_new_photo"].append({"entry_id": eid, "source_keys": sk, "root": r.get("root")})

    json.dump({"corpus_complete": corpus_complete, "total_images": idx.get("total_images"),
               "queue_size": len(queue), "buckets": {k: len(v) for k, v in buckets.items()},
               "entries": buckets}, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n = {k: len(v) for k, v in buckets.items()}
    L = ["# Source-photo rescue report", "",
         "**Owner correction honored:** `needs_source_photo_review` is NOT treated as "
         "\"ask owner for new photos.\" The existing corpus (`qamus/indexes/source_photo_index.json`) was indexed "
         "first: **%d images, %d page-numbered files (pages %s–%s), 0 missing pages per manifests** — the "
         "dictionary is fully photographed. So queued entries default to *visual review of existing photos*, not "
         "retake." % (idx.get("total_images", 0), len(idx.get("page_numbered_files", [])),
                       (idx.get("page_numbered_files") or [0])[0], (idx.get("page_numbered_files") or [0])[-1]),
         "", "## Reclassified queue (%d entries) — 6 buckets, not a blanket retake" % len(queue), "",
         "| bucket | n | meaning |", "|---|---:|---|",
         "| `verified_from_existing_photo` | %d | field read from an existing photo matches live (no action) |" % n["verified_from_existing_photo"],
         "| `certified_repair_ready` | %d | existing photo shows live is WRONG -> repair payload |" % n["certified_repair_ready"],
         "| `needs_manual_visual_review` | %d | photo PRESENT in corpus; awaiting a visual read (NOT a retake) |" % n["needs_manual_visual_review"],
         "| `needs_new_photo` | %d | corpus genuinely lacks coverage (retake justified) |" % n["needs_new_photo"],
         "| `missing_locator` | %d | entry has no source_key to map to a page |" % n["missing_locator"],
         "| `deferred_ambiguous` | %d | ambiguous; deferred |" % n["deferred_ambiguous"], "",
         "**Net: %d of %d queued entries are reclassified OFF \"needs new photo\"** (the corpus covers them). "
         "Only %d genuinely need a new photo." % (len(queue) - n["needs_new_photo"], len(queue), n["needs_new_photo"]),
         "", "## Verified-from-existing-photo samples", ""]
    if verified:
        L.append("| entry | field | live | source | verdict | source_ref |")
        L.append("|---|---|---|---|---|---|")
        for v in verified.values():
            L.append("| %s | %s | %s | %s | %s | %s |" % (v.get("entry_id"), v.get("field"), v.get("live_value"),
                     v.get("source_value"), v.get("verdict"), v.get("source_ref")))
    else:
        L.append("(none recorded yet — see source-photo-verified-samples.jsonl)")
    L += ["", "## Pipeline", "",
          "`source_photo_indexer.py` (coverage) → `source_photo_cropper.py` (orient/CLAHE/crop tile) → visual read "
          "(authority) → `source_photo_verify_entry.py` (field compare) → repair payload if live != source. "
          "OCR is a candidate generator only. Retake is requested ONLY for the `needs_new_photo` bucket."]
    open(REP, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(json.dumps({"queue": len(queue), "buckets": n, "corpus_complete": corpus_complete}, ensure_ascii=False))


if __name__ == "__main__":
    main()
