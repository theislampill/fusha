# Repair batch 001 — source-corpus certified repair (terminal classification)

**0 certified fields applied — correctly.** Per the P6 contract, when no class yields a certified *error* field,
the class is terminally classified with exact blockers. `repair_batch_001.jsonl` (the certified payload) is
therefore **empty**. The apply path (`edit_entry_record` → versioned snapshot + `backup_store`, owner-gated
DawahAgent) is verified ready for the day an owner-confirmed error class exists.

## Classes assessed (live, read-only)
| class | live count | terminal state | blocker / evidence |
|---|---:|---|---|
| count_mismatch | **0** | resolved | `sum(sense.count)==total_uses` holds for all current entries |
| all-zero total_uses | **0** | resolved | no entry has `total_uses==0` |
| **impossible_root / word-in-root** | 126 | **deferred — curator noun-keying STYLE, not an error** | 69 *clean* nouns share the tashkeel-word-root format (5 Whys); mutating imposes my scheme on curator data |
| held-back 19 | — | closed (prior tranche; v044 applied in S2) | — |

## Owner-gated candidates (NOT applied — `repair_batch_001.evidence.jsonl`)
**102 of 126** impossible_root entries have a **QAC-derivable radical root** for their headword
(خَبَالًا→خبل، رِفْد→رفد، عَتِيق→عتق، حَرَسًا→حرس…). Each is recorded as `live-entry:<id>#field=root` with the
`qac_derived_root` and the blocker. **24** have no clean QAC match (rare/weak forms → would need source-page
visual certification). A few derivations are morphologically debatable (مَكَانَكُمْ→كون via the مَفْعَل prefix) →
flagged for human judgement, never auto-applied.

## Why no field was applied (5 Whys, evidence not hand-waving)
1. Flagged because the `root` field holds a tashkeel'd word-form, not radicals.
2. That is how the curator keys many **noun** entries.
3. **69 clean (un-flagged) nouns share the exact format** → it is an established pattern, not an isolated defect.
4. The S5 "impossible_root" heuristic was verb-centric (assumed 3–4 radicals) — a false positive.
5. It does **not** break the hover (the QAC backlink uses QAC's per-token root, not the entry's root field).

So auto-mutating 100+ scripture-adjacent entries to impose radical roots would override the curator's own
scheme on my inference — a boundary violation, not a repair. **Deferred to owner**, with the QAC roots ready as
a certified candidate batch if the owner decides nouns should carry radical roots.

## Next step (owner-gated)
If approved: for each candidate, app-helper dry-run → `backup_store` → `edit_entry_record` (root field) as
DawahAgent → exact-match verify → `/healthz` 200 → entry count → `qamus_wbw/rebuild.sh` → hover coverage delta.
**No blind OCR; no invented roots/forms/counts.**
