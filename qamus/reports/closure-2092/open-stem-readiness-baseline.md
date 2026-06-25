# Open-stem readiness — baseline (2026-06-24)

Repo-local queue-hygiene tranche. NO live server / NO rebuild.sh / NO authoring. Companion:
`open-stem-readiness-baseline.json`; run ledger: `open-stem-readiness-ledger.md`.

## Git + gates

- HEAD `74607a9` = origin/main, clean.
- 8 gates green at baseline: artifact-ergonomics, report-ergonomics, report-reconciliation, dataset,
  completion-manifest, entry-rollup, grammar-evals, regressions.

## Repo-local state (staged artifact; NOT live-verified)

- coverage 85.87% · resolved 42,849 · pending 7,051 · total 49,900.
- coarse blockers: `stem_base_unknown` 5,595 · `source_entry_unverified` 1,076 ·
  `same_surface_polysemy_requires_i3rab` 379 · `proper_noun_no_qamus_entry` 1.

## Audit claims — all 5 verified against current code+data (not trusted)

| claim | verdict | evidence |
|---|---|---|
| surface index headword-only | **confirmed** | 5,075/6,659 form keys absent; 1,100 pending index-recoverable |
| host_lexeme verb-clitic pollution | **confirmed** | 780/1,210 rows `qac_pos==V` |
| أتي/رأي missing-entry misroute | **confirmed** | 89 flatten-reroute (أتي 55, رأي 34) |
| forms_array function-word pollution | **confirmed** | 494/633 rows `qac_pos==P` |
| decision_backlinks entry_nodes:0 | to verify | (Phase 4) |

## Verdict

Queues are polluted; **hygiene-first** before any authoring. The revised safe-realizable pool is
**provisional** until the lane-sanity validators pass. This tranche reshapes classification only —
no coverage gain is claimed, and nothing live is touched.
