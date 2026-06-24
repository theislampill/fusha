# Source-photo verification — progress (RESCUE pass)

> **2026-06-24b update:** entry→page locator built for all 2,092 (`source_photo_entry_locator.json`); 3 head-on verified (v008 بين 523, v027 عبد 275, v028 أخذ 273); circled entry number = v-number confirmed; 0 retakes (corpus complete). Read-quality (angle/glare) limits bulk digit reads — see `source-photo-verification-batch-002.md`.


Status of the **entry-data** verification lane. **Owner correction applied:** `needs_source_photo_review` is no
longer treated as "ask owner for new photos." The existing photographed corpus was indexed and used FIRST.

## Corpus inventory (existing photos — `tools/source_photo_indexer.py`)
| metric | value |
|---|---|
| total images | **1,205** |
| page-numbered files | **468** (pages **2–471**) |
| missing pages (per manifests) | **0** |
| folders | 21 (intake_2…intake_13, alternates, legacy, …) |
| verdict | **dictionary fully photographed** → retakes are not the default |

Index: `qamus/indexes/source_photo_index.json`. Calibration page `intake_13/IMG_7784.jpeg` confirmed entry blocks
are legible (headword/root/definition/senses/total-uses/Qurʾānic-usage).

## Reclassified queue (240 → 6 buckets, `tools/source_photo_rescue.py`)
| bucket | n |
|---|---:|
| `needs_manual_visual_review` (photo PRESENT) | **240** |
| `needs_new_photo` (retake justified) | **0** |
| `verified_from_existing_photo` | 1 sample (ب ي ن) |
| `certified_repair_ready` | 0 |
| `missing_locator` | 0 |
| `deferred_ambiguous` | 0 |

**All 240 reclassified off "needs new photo."** Only entries the corpus genuinely cannot cover would become
`needs_new_photo`; there are none (0 missing pages).

## Field-verification sample (proof the method works)
ب ي ن (df6af97d5e93, source_key v008): live `total_uses` = 523; the photo `intake_13/IMG_7784.jpeg` reads
**"Total uses in the Quran: 523"** → **verified_correct**, no repair, no mutation
(`tools/source_photo_verify_entry.py`).

## What remains (next tier — bounded reading, not retakes)
Per-entry visual verification of the 240 against existing page tiles: crop (`source_photo_cropper.py`) → read →
compare headword/forms/senses/sense-counts/total_uses/refs (`source_photo_verify_entry.py`) → repair payload only
on a real discrepancy → owner-gated `edit_entry_record`. The pipeline is built, calibrated, and the corpus is
complete; this is a reading task over an already-complete photo set.

## Lane status: **RESCUED** — 0 retakes required; 240 awaiting visual review of existing photos.
