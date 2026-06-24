# Particles proofing matrix (canonical, from qamus-2092-entry-matrix)

Per-entry audit of the **100** particle entries (public `section` split — authoritative 947 verb / 1045 noun / 100 particle). **0 unknown buckets.** Regenerate: `tools/build_proofing_matrices.py` (from `qamus-2092-entry-matrix.jsonl`). Reconciles to `hover-gloss-terminal-scoreboard.md` (82.49% overall) and `qamus-2092-terminal-scoreboard.md`.

| metric | value |
|---|---:|
| particle entries | **100** |
| entries fully hover-complete | 26 |
| entries with ≥1 pending hover token | 74 |
| resolved example tokens (per-entry, overlapping) | 3,479 |
| pending example tokens (per-entry, overlapping) | 278 |
| per-section example coverage | **92.6%** |

> Per-entry token counts overlap (a token in a shared āyah counts for each citing entry); the canonical de-duplicated total is the P3 audit (41,164 resolved / 8,736 pending / 49,900).

## Pending by blocker (this section)

| blocker | count |
|---|---:|
| `stem_base_unknown` | 155 |
| `source_entry_unverified` | 94 |
| `same_surface_polysemy_requires_i3rab` | 28 |
| `proper_noun_no_qamus_entry` | 1 |
