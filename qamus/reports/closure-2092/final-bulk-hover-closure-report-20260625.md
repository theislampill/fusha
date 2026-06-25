# Bulk hover closure report - 2026-06-25

**AUDIT_HANDOFF_9443_REACHED_NOT_100_COMPLETE.** This continuation mutated only the Qamus hover layer through the dry-run -> backup -> append -> rebuild -> health -> readback gate. The 90% milestone remains reached; 100% is not complete.

- Coverage moved from **43,589 / 49,900 = 87.35%** to **47,121 / 49,900 = 94.43%**.
- Newly resolved this continuation: **3,532** tokens.
- Remaining pending: **2,779** exact-blocked tokens.
- Public lookup provenance: **47,121** resolved word records, **47,260** gloss records, all `src=qamus`, all `kind=authored`, **0** public source/private leaks.
- Fresh full public crawl after batch016: **2,092/2,092** pages crawled, **2,092** HTTP 200, **0** render errors, **0** hover mismatches at that checkpoint. Against the batch017-synced lookup, the same checkpoint now reports **7** hover mismatches, expected because batch017 added exactly 7 hovers; batch017 has targeted live row readback, not a fresh full crawl.
- Generated lookup emitted pending markers: **2,167**; exact blocker ledger pending: **2,779**.
- No commits, pushes, tags, or releases were created.

## Latest Live Apply Evidence

- Batch017: **7** rows; dry-run had **0** decision overlap and **0** currently-glossed locs.
- Batch017 SHA-256: `73dbc956a31631a4194832fc791312b3db1fce5ed91aa81e43d85ef8aea35c7f`.
- Rebuild diff: **+7 / -0 / ~0**.
- Health gates: local `/` **200**, `/healthz` **200**, public root **200**.
- Row readback: **7/7** expected glosses matched. Sample: 3:162:2 incurred; 4:9:15 sound; 9:66:2 We pardon; 19:43:4 came to me; 72:3:2 Majesty.

## Applied Coverage Lift
- Batch 004: +592, coverage **90.09%**.
- Batch 005: +383, coverage **90.85%**.
- Batch 006: +200, coverage **91.25%**.
- Batch 007: +187, coverage **91.63%**.
- Batch 008: +191, coverage **92.01%**.
- Batch 009: +201, coverage **92.41%**.
- Batch 010: +186, coverage **92.79%**.
- Batch 011: +108, coverage **93.00%**.
- Batch 012: +13, coverage **93.03%**.
- Batch 013: +108, coverage **93.25%**.
- Batch 014: +276, coverage **93.80%**.
- Batch 015: +264, coverage **94.33%**.
- Batch 016: +44, coverage **94.42%**.
- Batch 017: +7, coverage **94.43%**.

## Current Remaining Work
- `form_variant`: 842 rows remain.
- `verb_clitic`: 728 rows remain.
- `token_irab`: 482 rows remain.
- `new_entry_proposal`: 274 rows remain.
- `scholar_review`: 196 rows remain.
- `host_lexeme`: 179 rows remain.
- `source_entry_repair`: 73 rows remain.
- `source_photo`: 4 rows remain.
- `reject_unsafe`: 1 rows remain.
- Gates remaining: two-vote 2,231, owner 274, scholar 197, source 77.
- Deterministic auto-rule rows remaining: **0**.

## Verification
- python -X utf8 tools/validate_token_hover_decisions.py qamus/candidates/qamus_2092/bulk_certified_apply_batch_20260625_017.jsonl: PASS
- python -X utf8 tools/validate_pending_source_triangulation_table.py: PASS, 2,779 rows, 0 deterministic rows remaining
- live dry-run batch017: PASS, 7 rows, 0 decision overlap, 0 currently glossed locs, expected +7
- live apply batch017: PASS, +7 / -0 / ~0, rebuild rc 0, health 200/200/public 200, readback 7/7
- python -X utf8 tools/audit_all_hover_tokens.py: PASS, 47,121/49,900=94.43%
- python -X utf8 tools/build_blocker_root_cause_ledger.py: PASS, 2,779 pending
- public hover gloss invariant: PASS, 47,260 gloss records, 0 public source/private leaks
- `python -X utf8 tools/validate_qamus_public_crawl.py`: checkpoint still covers 2,092/2,092 pages, but now reports 7 hover mismatches because the full crawl predates batch017; batch017 targeted live readback is current.
- `python -X utf8 tools/check_regressions.py`: FAIL, 5 broader project-completion checks remain outside batch017 hover apply (P4 suffix/pronoun, Phase3 nahw engine, source-graph integrity, bidirectional links runnable, corpus fixture); Windows subprocess UnicodeDecodeError noise also observed.
