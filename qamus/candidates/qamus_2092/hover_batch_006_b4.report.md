# Batch-4 (B4) — deep-tail noun + verb sweep (APPLIED LIVE)

Fourth production sweep. Top pending occurrence is now 5 (the deep tail). Same four-gate pipeline; B2+B3 rejects
excluded from selection.

## Result
- **230 candidates** → **181 certified, 49 rejected**. tsv **563 → 744 lines**, backup `*.bak-b4`.
- Rebuild: **coverage 77.31% → 78.78%** (matched 38,580 → 39,312, **+732 occ, ~0 changed, −0 removed**), validate
  PASS, health 200, smoke OK. Dark screenshot verified.

## Safety note — the نَزَّلَ / كَذَّبَ landmines, empirically cleared
Three certified keys touched the historically-dangerous نزل/كذب roots: نزلنا, كذبت, كذبا. Before applying, their
ACTUAL corpus surface sets were checked: نزلنا = {نَزَّلْنَا, نَزَّلْنَآ} (Form II only — no Form I نَزَلْنَا present),
كذبت = {كَذَّبَتْ} (Form II only — no كَذَبَتْ), كذبا = {كَذِبًا} (noun "a lie" only). Because the live gloss fires
only over tokens actually in the corpus, and these suffixed keys carry a single form there, the glosses are safe.
The bare key نزل (which DOES mix نَزَّلَ/نَزَلَ) remains quarantined.

## Rejected (49) — gate still biting
Form/voice and lemma collisions in the deeper tail, now forbidden transitions.

## Cumulative this tranche (B2+B3+B4)
72.14% → 75.28% → 77.31% → **78.78%** — **+526 glosses, +3,316 occ, −0 removed**. Per-batch gain shrinking
(+1,571 → +1,013 → +732) as the tail becomes homograph-dense. Mirror: `hover_batch_006_b4.*`; rollback `*.bak-b4`.
