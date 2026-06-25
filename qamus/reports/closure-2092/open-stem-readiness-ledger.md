# Open-stem readiness — run ledger (implementaudit audit object)

Repo-local queue-hygiene tranche. NO live server / NO rebuild.sh / NO authoring. States:
`done` · `in_progress` · `blocked_exact` · `deferred_owner` · `deferred_source` · `deferred_scholar` ·
`no_action_false_positive`. Companion: `open-stem-readiness-baseline.{md,json}`, deep-research index.

| phase | item | state | note |
|---|---|---|---|
| 0 | baseline + ledger + verify claims | done | all 5 audit claims CONFIRMED against current code+data |
| 1 | surface-index covers usage.forms | done | shared build_surface_index() (+5,075 keys, additive); validator; 721 tokens reclassified |
| 2 | ledger lane pollution split | done | verb_clitic 822 split; host_lexeme noun-only 255; أتي/رأي rerouted; function_word 550; index_miss 1,050; lane-sanity green |
| 3 | family-batch / sidecar validators + wiring | done | validate_form_variant_family_batches.py + provenance parity; suffix-pronoun loosened (F13); 7 batch gates wired |
| 4 | stale path / status / graph truthfulness | done | validate_canonical_paths (0 stale); build_decision_backlinks fail-closed (F5); proofing dynamic; banners |
| 5 | 2,092-entry status-vocabulary honesty | done | audit-completion + manifest-summary + final-closure-report use mechanically-classified vocabulary |
| 6 | regression fixtures for scar families | done | qamus/examples/form_variant_rejections.jsonl (20 fixtures) wired into check_regressions |
| 7 | claude.ai / tutor runtime skeleton | done | dist/claude-ai pack + build/verify scripts + tutor-routing appendix |
| 8 | corpus-to-Qamus read-only fixture validator | done | validate_corpus_fixture.py + Nawawī40 fixture; Ṣaḥīḥayn plan-only |
| 9 | regenerate repo-local artifacts | done | audit/graph/matrix/ledgers/quality/proofing all reconcile post-hygiene; gates green |
| 10 | review-only casebook outputs | done | review-only-casebook + next-authoring-go-nogo (1,606 families, 9 buckets; NO apply payloads) |
| 11 | next-batch resume plan = BLOCKED on hygiene | done | banner = hygiene complete; GO lanes only; live-apply marked private-context-only |
| 12 | commits (6 chunks) | done | explicit paths; chunks landed ae898a7…(this) |
| 13 | final response | done | repo-local; GO/NO-GO with exact next |

## Hard constraints honored

- No live server access; no `rebuild.sh`; no append to `qamus-service/ref/*`; no new authored glosses; no new
  entries; no corpus mass-import; public invariant `{src:"qamus",kind:"authored",lang:"en"}` unchanged.
- The exporter (`export_current_qamus_dataset.py`) reads per-entry JSON from the **server** entries dir, so it
  cannot run repo-locally; the index regeneration uses a repo-local rebuilder over the committed
  `entries.jsonl` that shares the exporter's surface-index logic (no faked exporter run).
