# Verbs proofing matrix (canonical, from qamus-2092-entry-matrix)

Per-entry audit of the **947** verb entries (public `section` split — authoritative 947 verb / 1045 noun / 100 particle). **0 unknown buckets.** Regenerate: `tools/build_proofing_matrices.py` (from `qamus-2092-entry-matrix.jsonl`). Reconciles to `hover-gloss-terminal-scoreboard.md` (82.49% overall) and `qamus-2092-terminal-scoreboard.md`.

| metric | value |
|---|---:|
| verb entries | **947** |
| entries fully hover-complete | 56 |
| entries with ≥1 pending hover token | 886 |
| resolved example tokens (per-entry, overlapping) | 84,850 |
| pending example tokens (per-entry, overlapping) | 18,016 |
| per-section example coverage | **82.5%** |

> Per-entry token counts overlap (a token in a shared āyah counts for each citing entry); the canonical de-duplicated total is the P3 audit (41,164 resolved / 8,736 pending / 49,900).

## Pending by blocker (this section)

| blocker | count |
|---|---:|
| `stem_base_unknown` | 14,216 |
| `source_entry_unverified` | 2,656 |
| `same_surface_polysemy_requires_i3rab` | 1,030 |
| `proper_noun_no_qamus_entry` | 3 |
