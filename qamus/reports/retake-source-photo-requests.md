# Source-photo retake requests — RESCUED (retake is no longer the default)

> **Reclassified by the source-photo rescue pass** (`qamus/reports/source-photo-rescue-report.md`). The existing
> corpus was indexed first: **1,205 images, pages 2–471, 0 missing**. The dictionary is fully photographed, so the
> 240 `needs_source_photo_review` entries do **NOT** need new photos — they need a *visual read of existing pages*.

## Reclassified queue (240 entries)
| bucket | n | action |
|---|---:|---|
| `needs_manual_visual_review` | **240** | read the existing page tile (`source_photo_cropper.py`) + verify fields — **no retake** |
| `verified_from_existing_photo` | (sample) | ب ي ن total_uses 523 = live 523 (no action) |
| `certified_repair_ready` | 0 | none certified yet |
| **`needs_new_photo`** | **0** | corpus covers every page — **no retakes requested** |
| `missing_locator` | 0 | every queued entry has a source_key |
| `deferred_ambiguous` | 0 | — |

## Retake instructions (only if a genuine gap appears later)
A retake is requested ONLY for an entry that lands in `needs_new_photo` after a visual-review attempt fails (e.g.
the page tile is illegible at that block). For such a case record: entry_id · source_key · expected page (the
corpus is page-indexed 2–471) · exact crop · field needing verification · why the existing photo is insufficient.
**As of this pass, that list is empty.**

## Next tier (the actual remaining work)
Per-entry visual verification of the 240: for each, map source_key → page → tile (`source_photo_cropper.py`),
read the entry block, compare headword/forms/senses/sense-counts/total_uses/refs against live
(`source_photo_verify_entry.py`), and emit a repair payload only on a real discrepancy. The pipeline is built and
calibrated; this is a bounded reading task over an already-complete photo set, not a retake campaign.

## Ref-verification queue (separate, 10 entries)
Bad/range āyah refs (unchanged): see the audit; these are ref fixes, not photo retakes.
