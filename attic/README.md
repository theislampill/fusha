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
