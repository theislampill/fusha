# Particles proofing matrix (canonical, from qamus-2092-entry-matrix)

Per-entry audit of the **100** particle entries (public `section` split — authoritative 947 verb / 1045 noun / 100 particle). **0 unknown buckets.** Regenerate: `tools/build_proofing_matrices.py` (from `qamus-2092-entry-matrix.jsonl`). Reconciles to `hover-gloss-terminal-scoreboard.md` (85.87% overall) and `qamus-2092-terminal-scoreboard.md`.

| metric | value |
|---|---:|
| particle entries | **100** |
| entries fully hover-complete | 29 |
| entries with ≥1 pending hover token | 71 |
| resolved example tokens (per-entry, overlapping) | 3,526 |
| pending example tokens (per-entry, overlapping) | 231 |
| per-section example coverage | **93.9%** |

> Per-entry token counts overlap (a token in a shared āyah counts for each citing entry); the canonical de-duplicated total is the P3 audit (42,849 resolved / 7,051 pending / 49,900).

## Pending by blocker (this section)

| blocker | count |
|---|---:|
| `stem_base_unknown` | 124 |
| `source_entry_unverified` | 67 |
| `same_surface_polysemy_requires_i3rab` | 16 |
| `proper_noun_no_qamus_entry` | 1 |
