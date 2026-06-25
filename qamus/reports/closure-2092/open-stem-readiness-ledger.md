# Open-stem readiness — run ledger (implementaudit audit object)

Repo-local queue-hygiene tranche. NO live server / NO rebuild.sh / NO authoring. States:
`done` · `in_progress` · `blocked_exact` · `deferred_owner` · `deferred_source` · `deferred_scholar` ·
`no_action_false_positive`. Companion: `open-stem-readiness-baseline.{md,json}`, deep-research index.

| phase | item | state | note |
|---|---|---|---|
| 0 | baseline + ledger + verify claims | done | all 5 audit claims CONFIRMED against current code+data (see baseline.json) |
| 1 | surface-index covers usage.forms | in_progress | exporter builds by_norm from headwords only (confirmed); 1,100 pending tokens index-recoverable |
| 2 | ledger lane pollution split | in_progress | 780 verb-clitics in host_lexeme; 494 function-words in forms_array; 89 أتي/رأي root-flatten reroutes |
| 3 | family-batch / sidecar validators + wiring | open | |
| 4 | stale path / status / graph truthfulness | open | incl. build_decision_backlinks entry_nodes:0 fail-closed |
| 5 | 2,092-entry status-vocabulary honesty | open | |
| 6 | regression fixtures for scar families | open | كذبوا/يقتلون/بنين/ظمأ/clitic/particle |
| 7 | claude.ai / tutor runtime skeleton | open | dist/claude-ai pack + verifier |
| 8 | corpus-to-Qamus read-only fixture validator | open | Nawawī40 only; Ṣaḥīḥayn plan-only |
| 9 | regenerate repo-local artifacts | open | |
| 10 | review-only casebook outputs | open | structural reroute / noun-host / verb-clitic / particle / new-entry / source / token / photo / scholar |
| 11 | next-batch resume plan = BLOCKED on hygiene | open | |
| 12 | commits (6 chunks) | open | explicit paths only |
| 13 | final response | open | repo-local; GO/NO-GO with exact next |

## Hard constraints honored

- No live server access; no `rebuild.sh`; no append to `qamus-service/ref/*`; no new authored glosses; no new
  entries; no corpus mass-import; public invariant `{src:"qamus",kind:"authored"}` unchanged.
- The exporter (`export_current_qamus_dataset.py`) reads per-entry JSON from the **server** entries dir, so it
  cannot run repo-locally; the index regeneration uses a repo-local rebuilder over the committed
  `entries.jsonl` that shares the exporter's surface-index logic (no faked exporter run).
