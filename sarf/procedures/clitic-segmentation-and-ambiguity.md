# Procedure — clitic segmentation + ambiguity (arbitrary typing)

Recognise proclitics, enclitics, and attached pronouns as **candidates**, not certainties, for typed/arbitrary Arabic where there is
no source address. This is the arbitrary-typing companion to [`clitic-and-host-morphology.md`](clitic-and-host-morphology.md) (which
governs the source-addressed hover path). Source of truth: [`tools/fusha_text_check.py`](../../tools/fusha_text_check.py)
`segment_candidates`.

## Input
A typed token (often unvoweled), no `quran_loc`.

## Checks
1. **Keep the whole-token reading.** A leading `بـ/كـ/لـ/وـ/فـ` or `ال` may be a real prefix **or** a radical — keep both the
   peeled and the un-peeled segmentation as candidates.
2. **Single-letter peel = low confidence.** A lone single-letter clitic (`كـ`, a final `ه/ك/ي`) is usually part of the stem; mark it
   low confidence, never assert it.
3. **Tanwīn-alif ≠ نا.** A final tanwīn-alif (ـًا, e.g. `قُرْءَانًا`) is **not** the pronoun نا (`ends_tanwin_alef`).
4. **Surfaces concatenate exactly.** Every candidate segmentation's surfaces must concatenate to the token surface (the renderer
   invariant); the engine asserts this.
5. **Route unresolved to pending.** If the segmentation cannot be decided from the surface, keep the candidate set and stay pending —
   never guess a split.

## Output
The token's `segment_candidates` (kept, ranked, never collapsed) feeding the morphology candidate lattice
([`morphology-candidate-lattice.md`](morphology-candidate-lattice.md)). An attached-pronoun or preposition candidate routes to
[`suffix-pronoun-state.md`](suffix-pronoun-state.md) / nahw.

## Forbidden
Inventing a split the lattice did not produce; asserting a single-letter clitic as a pronoun without evidence; treating a tanwīn-alif
as نا; forcing one segmentation for an unvoweled token.

## Test
`sarf/evals/morphology-candidate-lattice.jsonl` (proclitic+host, attached-pronoun candidate, tanwīn-alif guard) +
`tools/validate_sarf_nahw_skill_backprop.py`.
