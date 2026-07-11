# Nouns proofing matrix (canonical, from qamus-2092-entry-matrix)

Per-entry audit of the **1045** noun entries (public `section` split — authoritative 947 verb / 1045 noun / 100 particle). **0 unknown buckets.** Regenerate: `tools/build_proofing_matrices.py` (from `qamus-2092-entry-matrix.jsonl`). Reconciles to `hover-gloss-terminal-scoreboard.md` (HISTORICAL snapshot; 98.71% of example tokens resolved at matrix build time — current live coverage lives ONLY in `docs/STATUS.md`) and `qamus-2092-terminal-scoreboard.md`.

| metric | value |
|---|---:|
| noun entries | **1045** |
| entries fully hover-complete | 219 |
| entries with ≥1 pending hover token | 824 |
| resolved example tokens (per-entry, overlapping) | 27,836 |
| pending example tokens (per-entry, overlapping) | 4,275 |
| per-section example coverage | **86.7%** |

> Per-entry token counts overlap (a token in a shared āyah counts for each citing entry); the canonical de-duplicated total is the P3 audit (49,255 resolved / 645 pending / 49,900).

## Pending by blocker (this section)

| blocker | count |
|---|---:|
| `stem_base_unknown` | 2,268 |
| `source_entry_unverified` | 959 |
| `same_surface_polysemy_requires_i3rab` | 256 |
