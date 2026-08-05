# D-11 attic

These scripts were unreferenced and absent from the regression harness at `446a536a`. They are preserved for history and must not be used from production paths. Restore any file with `git revert` of the D-11 move commit, then reclassify it before reuse.

| File | Prior role | Evidence |
|---|---|---|
| `qamus/scripts/build_qamus_terminal_matrix.py` | P2 — assign every one of the 2,092 Qamus entries a single TERMINAL state (read-only). | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `qamus/scripts/build_retake_requests.py` | Regenerate qamus/reports/retake-source-photo-requests.md from the entry audit dump (read-only). | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/build_dr_reattempt_reports.py` | Phase 1/4 — emit the five deep-research approach reattempt reports + the three Phase-4 lane-readiness | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/build_engine_completion_audit.py` | Phase 9 — sarf/nahw engine completion audit. Maps each named failure mode to its repo assets | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/build_index_miss_reindex_plan.py` | Build index-miss reindex candidate list and owner-gated plan. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/build_my_dr_reattempt.py` | Phase 1 — MY re-attempt of the five deep-research approaches against the CURRENT tree. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/build_sarfnahw_knowledge_base.py` | SN3 — normalize the APKG + PDF extraction into a deduped sarf/nahw concept base. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/eval_fusha_dependency.py` | Evaluate the smoke dependency/i'rab baseline. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/ingest_apkg.py` | SN1 — extract AMAU / Anki .apkg decks into normalized JSONL. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/ingest_pdf_sarfnahw.py` | SN2 — extract the verb-chart PDFs + verb-tables DOCX (structure + English only). | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_blocker_root_cause_ledger.py` | Regression tests for blocker-root-cause safe-tier classification. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_bulk_followup_certified_batch.py` | Self-test for follow-up review conversion into certified hover decisions. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_bulk_two_vote_reconciliation.py` | Self-test for two-vote reconciliation into certified/unresolved packets. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_index_miss_reindex_plan.py` | Self-test for index-miss reindex candidate/plan generation. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_new_entry_owner_review_packet.py` | Self-test for the new-entry owner review packet builder. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_new_entry_proposals_from_table.py` | Self-test for building new-entry proposals from the triangulation table. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_public_hover_crawl_details.py` | Self-test for public Qamus hover-detail extraction. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/test_qamustyping3_acceptance.py` | Regression test for the qamustyping3 acceptance gate. | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |
| `tools/text_extract.py` | Shared text helpers for the sarf/nahw corpus ingest (SN1/SN2). | No literal references, Python importers, or `tools/check_regressions.py` execution at `446a536a`. |

## 2026-08-05 sweep

Second application of the D-11 pattern, from the repository-organization audit on `fable/doc-hygiene`.
Every entry below was verified zero-consumer by `git grep` of its basename/module name across the
whole tree immediately before the move; none is invoked by `tools/check_regressions.py`. Restore the
same way: `git revert` the sweep commit, then reclassify before reuse.

| File | Prior role | Evidence |
|---|---|---|
| `tools/assemble_calibration.py` | One-shot assembly of a calibration input bundle. | `git grep assemble_calibration` returns no hit outside the file itself; not harness-invoked. |
| `tools/build_morphline_author_packets.py` | Built morphline authoring packets for a closed authoring wave. | `git grep build_morphline_author_packets` returns no hit outside the file itself; not harness-invoked. |
| `tools/build_richseg_debt_manifest.py` | Built the rich-segmentation debt manifest for a closed debt wave. | `git grep build_richseg_debt_manifest` returns no hit outside the file itself; not harness-invoked. |
| `tools/check_richseg_debt.py` | Checked the rich-segmentation debt manifest produced by the builder above. | `git grep check_richseg_debt` returns no hit outside the file itself; not harness-invoked. |
| `tools/test_certify_funcword_wave.py` | Self-test for a completed function-word certification wave. | `git grep test_certify_funcword_wave` returns no hit outside the file itself; not harness-invoked. |
| `tools/test_certify_rebind_wave.py` | Self-test for a completed rebind certification wave. | `git grep test_certify_rebind_wave` returns no hit outside the file itself; not harness-invoked. |
| `tools/test_rich_seg_83_26_5.py` | Single-location rich-segmentation regression fixture (83:26:5). | `git grep test_rich_seg_83_26_5` returns no hit outside the file itself; not harness-invoked. |
| `tools/test_tier_due_process.py` | Self-test for a retired tier due-process rule. | `git grep test_tier_due_process` returns no hit outside the file itself; not harness-invoked. |
| `prep/` (5 files: `morphline-apply-plan.md`, `nft101-apply.py`, `nft101-manifest.txt`, `nft101-plan.md`, `test_nft101_apply.py`) | Closed one-shot migration staging (morphline apply + NFT-101 apply). | `git grep -E "prep/(morphline\|nft101)"` and `git grep nft101` return no hit outside `prep/` itself; the full harness is green without them. **`prep/morphline-approved-manifest.json` was NOT retired** — it is live input to `tools/apply_rm20_morphline.py`, `tools/build_crosswalk_gap_queue.py` and `tools/test_shadow_canonical_repair_overlay.py`, which address it as `ROOT / "prep" / ...` (a joined path the basename grep missed; caught by the harness and reverted). |
| `IMPLEMENTAUDIT-runs/*-STATE.md` (3 files, from `.IMPLEMENTAUDIT/runs/`) | Committed agent run state for three closed audit runs (`fusha-parser-substrate-001`, `qamustyping4-closure-001`, `qamustypingfin-closure-001`). | `git grep IMPLEMENTAUDIT` finds only two prose strings naming an out-of-repo operator-workspace path, never these files. `.IMPLEMENTAUDIT/` is now gitignored. |
| `rm22-row-accounting.jsonl` (from `qamus/reports/rm22-regeneration-rehearsal/row-accounting.jsonl`) | Bulk per-row accounting dump for the RM-22 regeneration rehearsal (owner ruling 2026-08-05: evidence dump, not reviewable report surface). | Its only consumer was `tools/rehearse_largelexicon_regeneration.py`, which now takes `--accounting-path` defaulting here. The summary `migration-report.json` and the sha256-pinning `row-accounting.meta.json` deliberately STAY in `qamus/reports/rm22-regeneration-rehearsal/`; `--check` stays green. |
