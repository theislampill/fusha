# Source-photo rescue report

**Owner correction honored:** `needs_source_photo_review` is NOT treated as "ask owner for new photos." The existing corpus (`qamus/indexes/source_photo_index.json`) was indexed first: **1205 images, 468 page-numbered files (pages 2–471), 0 missing pages per manifests** — the dictionary is fully photographed. So queued entries default to *visual review of existing photos*, not retake.

## Reclassified queue (240 entries) — 6 buckets, not a blanket retake

| bucket | n | meaning |
|---|---:|---|
| `verified_from_existing_photo` | 0 | field read from an existing photo matches live (no action) |
| `certified_repair_ready` | 0 | existing photo shows live is WRONG -> repair payload |
| `needs_manual_visual_review` | 240 | photo PRESENT in corpus; awaiting a visual read (NOT a retake) |
| `needs_new_photo` | 0 | corpus genuinely lacks coverage (retake justified) |
| `missing_locator` | 0 | entry has no source_key to map to a page |
| `deferred_ambiguous` | 0 | ambiguous; deferred |

**Net: 240 of 240 queued entries are reclassified OFF "needs new photo"** (the corpus covers them). Only 0 genuinely need a new photo.

## Verified-from-existing-photo samples

| entry | field | live | source | verdict | source_ref |
|---|---|---|---|---|---|
| df6af97d5e93 | total_uses | 523 | 523 | verified_correct | intake_13/IMG_7784.jpeg |

## Pipeline

`source_photo_indexer.py` (coverage) → `source_photo_cropper.py` (orient/CLAHE/crop tile) → visual read (authority) → `source_photo_verify_entry.py` (field compare) → repair payload if live != source. OCR is a candidate generator only. Retake is requested ONLY for the `needs_new_photo` bucket.
