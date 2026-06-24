# Batch-3 (B3) — continued noun + verb sweep (APPLIED LIVE)

Third production sweep (continuation rule: don't stop while green). Same four-gate pipeline; the 71 known B2
rejects were **excluded** from selection so this tier processed genuinely new lower-frequency surfaces.

## Result
- **230 candidates** (next pending tier, post-B2, top occ = 7) → **186 certified, 44 rejected**.
- Applied to the live tsv: **377 → 563 lines**, backup `*.bak-b3`.
- Rebuild: **coverage 75.28% → 77.31%** (matched 37,567 → 38,580, **+1,013 occ, ~0 changed, −0 removed**),
  validate PASS, health 200, smoke OK (40 glossed on a covered page). Light + dark screenshots verified.

## Certified (186) — examples
Plurals/content nouns (faces, gods/false-deities, the eyes, the matters, your houses, the evil deeds), proper
nouns (Lot, Midian), participles/adjectives (the clear, confirming, most grateful, the criminals, the believing
women), and finite verbs with person/voice (they are promised, We gave them, they were arrogant, and establish,
He gives life, they entered).

## Rejected (44) — the gate still biting on the harder tail
- **form_voice_collision**: يتبعون, ذكروا, دعوا, بلغ (Form I/II/IV or active/passive mixes under one key).
- **lemma_collision**: مثله, الذكر (remembrance/the Reminder/males), حكما (judgment/wisdom/ruling), بشرا
  (human/glad-tidings).

Recorded as forbidden transitions in the state-transition rules.

## Cumulative this tranche
72.14% (start) → 75.28% (B2, +159) → **77.31% (B3, +186)** — **+345 glosses, +2,584 occ, −0 removed**.
Provenance public-clean (`src:"qamus"`). Mirror: `hover_batch_005_b3.*`. Rollback: `*.bak-b3` + `wbw-lookup.prev.json`.
