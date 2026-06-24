# Repair batch 006 — source-photo rescue (NOT retake-by-default)

Honors the owner correction: do not demand 240 new photos before trying the **existing** corpus.

## What was done
1. **Indexed the existing corpus** (`tools/source_photo_indexer.py` on the owner's photo set):
   **1,205 images, 468 page-numbered files (pages 2–471), 0 missing pages** per the frontmatter manifests — the
   dictionary is fully photographed. Index: `qamus/indexes/source_photo_index.json`.
2. **Calibrated** on a sample page (`intake_13/IMG_7784.jpeg`): the entry blocks are clearly readable — red
   headword band, root (ب ي ن), definition "(lit., to be clear)", 3 senses with forms, **"Total uses: 523"**, and
   Qurʾānic usage with refs. (S8A calibration.)
3. **Reclassified the 240** `needs_source_photo_review` queue (`tools/source_photo_rescue.py`):
   - `needs_manual_visual_review`: **240** (photo PRESENT in corpus — awaiting a visual read, NOT a retake)
   - `needs_new_photo`: **0** · `missing_locator`: **0** · `deferred_ambiguous`: **0**
   - **Net: all 240 are off "needs new photo."**
4. **Field verification sample** (`tools/source_photo_verify_entry.py`): ب ي ن (df6af97d5e93, source_key v008) —
   live `total_uses` = 523 read from `intake_13/IMG_7784.jpeg` shows **523** → **verified_correct, no repair**.

## Certified repairs this pass: **0**
The sampled entry was already correct (523 = 523). No live mutation. Per-entry visual verification of the 240
(reading each entry's page tile and comparing headword/forms/senses/counts) is the next tier — the pipeline +
tools are in place (`source_photo_cropper.py` → visual read → `source_photo_verify_entry.py` → payload).

## If/when a discrepancy is certified
Apply via the proven owner-gated path: dry-run → `backup_store` → DawahAgent `edit_entry_record` → verify
(versioned) → `/healthz` + entry-count + offline tests → `qamus_wbw/rebuild.sh` → hover before/after.

## Retake requests
**Reduced to 0** by the rescue (the corpus covers every page). See `qamus/reports/retake-source-photo-requests.md`
(now: 0 `needs_new_photo`; 240 `needs_manual_visual_review`) and `source-photo-verification-progress.md`.
