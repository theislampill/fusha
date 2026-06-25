# Post-hygiene closure — baseline (2026-06-24)

Every prior-tranche claim **re-verified, not trusted**. Companion: `.json`.

## Git

- HEAD `a0f596b` = origin/main `a0f596b`, **clean (0 dirty)**. `a0f596b` is current.

## Gates (14, all PASS)

artifact-ergonomics · report-ergonomics · report-reconciliation · canonical-paths · surface-index-covers-usage-forms ·
open-stem-lane-sanity · blocker-root-cause-ledger · completion-manifest · entry-rollup · current-dataset ·
bidirectional-links · grammar-evals · regressions · verify-claude-ai-pack.

## Coverage — repo-local AND live-verified (they match exactly)

| source | resolved | pending | coverage |
|---|---:|---:|---:|
| repo-local staged artifact | 42,849 | 7,051 | **85.87%** |
| live (read-only) | 42,849 | 7,051 | **85.87%** |

The staged artifact equals live exactly, so the numbers below are **both repo-local and live-verified**. **No
live mutation this phase.** Live context (SSH + scoped deploy loop) is present and verified read-only.

## Public Qamus (read-only)

- home HTTP **200**; **2,092 entries** visible. Committed dataset split: **947 verb / 1,045 noun / 100 particle**.

## Prior claims independently re-verified

| claim | check | verdict |
|---|---|---|
| surface index includes `usage[].forms` | `by_norm` keys = 7,125 | **TRUE** |
| host-lexeme noun-only | qac_pos==V in host_lexeme = 0 | **TRUE** |
| verb-clitics split out | verb_clitic lane = 822 | **TRUE** |
| أتي/رأي rerouted by flattened root | missing_entry أتي/رأي residual = 0 | **TRUE** |
| batch/provenance validators wired | form_variant_family_batches + 7 batch gates green | **TRUE** |
| claude.ai pack + corpus fixture | both verifiers PASS | **TRUE** |

## Claim provenance labelling

All current claims are **repo-verified**; coverage + entry count are additionally **live-verified read-only**.
`out/` is gitignored; the staged artifact is the audit input only and does not influence committed results.

**Verdict:** baseline reconciles; the prior tranche's claims are all TRUE. Proceed to the deep-research
finding-by-finding reattempt proof (Phase 1).
