# Index-Miss Reindex Plan

Owner-gated, not applied. This is resolver/index work, not new hover authoring.

| metric | value |
|---|---:|
| candidate rows | 846 |
| exact-form index misses | 638 |
| existing-entry family review | 208 |

## Live Access Status

`live-ssh-verified-post-deterministic-apply-20260625`

## Required Dry-Run

1. Run the live resolver against each candidate without changing entry data.
2. Split candidates into safe-relaxable vs correctly quarantined homograph/multi-root rows.
3. Apply only owner-approved resolver changes with diff `+N / -0 / ~0`.
4. Rebuild, health-check, and regenerate the hover audit before claiming coverage.

Public provenance remains unchanged: `src=qamus`, `kind=authored`.
