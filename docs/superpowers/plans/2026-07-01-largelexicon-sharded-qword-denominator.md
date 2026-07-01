# Largelexicon Sharded Qword Denominator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the oversized committed qword denominator monolith with a manifest-backed, bidirectional, shard-addressable table that remains easy for Qamus rollout and future lexicon workers to extend.

**Architecture:** Keep one logical Project-Xanadu-style table, but store it as small JSONL shards with a manifest, SHA-256/count checks, an entry-shard reverse index, and a source-card repair packet for entries that exist in the 2,092-entry Qamus target but lack tokenizable examples in the current export. Consumers use `tools/largelexicon_table_reader.py` instead of hard-coding file paths.

**Tech Stack:** Python stdlib, JSON/JSONL, existing `tools/largelexicon_common.py` builders and largelexicon validators.

---

### Task 1: Add Red Gates

**Files:**
- Create: `tools/validate_largelexicon_table_manifest.py`
- Create: `tools/validate_largelexicon_table_reader.py`

- [x] Add a manifest validator that fails while `qamus/indexes/largelexicon/qamus-qword-denominator.full.jsonl` exists and the manifest is absent.
- [x] Add a reader contract validator that fails until `tools/largelexicon_table_reader.py` exists.
- [x] Run both validators and confirm they fail for the expected reasons before implementation.

### Task 2: Generate The Sharded Logical Table

**Files:**
- Modify: `tools/largelexicon_common.py`
- Modify: `tools/build_largelexicon_source_inventory.py`
- Create generated artifacts under `qamus/indexes/largelexicon/`

- [x] Add constants for `qamus-qword-denominator.manifest.json`, `qamus-qword-denominator.entry-shard-index.json`, `qamus-qword-denominator.source-card-repair.json`, and `qword-denominator/*.jsonl`.
- [x] Generate qword denominator shards by Qamus source-key ranges so the table remains tranche-friendly and reviewable.
- [x] Remove the committed monolithic qword denominator from the source-clean full-table path.
- [x] Record `qamus_entry_count`, `entries_with_qword_rows`, and `entries_without_qword_rows` so the 2,092-entry target is not confused with rows currently tokenizable from `entries.jsonl`.

### Task 3: Preserve Bidirectionality

**Files:**
- Create: `tools/largelexicon_table_reader.py`
- Modify generated manifest/index artifacts.

- [x] Preserve forward keys: `entry_id`, `source_keys`, `card_id`, usage/example/qword indexes, visible surface, and `quran_ref`.
- [x] Preserve reverse keys: `row_id`, `entry_id`, `card_id`, and `card_text_sha256`.
- [x] Add entry-shard lookup so `row_id -> entry -> shard -> row` works without scanning all shards.
- [x] Add a manifest `bidirectional_contract` section for future validators and executor workers.

### Task 4: Surface Source-Card Repair Gaps

**Files:**
- Modify: `tools/largelexicon_common.py`
- Create generated: `qamus/indexes/largelexicon/qamus-qword-denominator.source-card-repair.json`

- [x] Emit a repair packet for entries present in Qamus but absent from the qword denominator because the current export lacks example rows.
- [x] Preserve the known `n993` / `مَلْجَأ` repair hint with `pg443.jpeg` and candidate Qur'an reference `42:47`.
- [x] Keep the repair packet internal/source-clean and non-live-mutating.

### Task 5: Update Consumers And Docs

**Files:**
- Modify: `tools/validate_largelexicon_source_ledger.py`
- Modify: `tools/check_regressions.py`
- Add: `qamus/schemas/largelexicon-table-manifest.schema.json`
- Modify: `docs/parser/largelexicon-source-ledger.md`
- Modify: `docs/parser/largelexicon-implementation.md`
- Modify: `qamus/procedures/largelexicon-rollout-consumption.md`
- Modify: `curriculum/largelexicon-tutor-routing.md`
- Modify claim/report JSON surfaces.

- [x] Update source-ledger validation to verify the logical table through the manifest and shards.
- [x] Update regression harness to run manifest and reader self-tests.
- [x] Document the manifest-backed table as the only supported qword denominator surface.
- [x] Document source-card repair packets as repair gaps, not learner grammar failures or live coverage.

### Task 6: Verify, Commit, Push

**Files:**
- All changed files in this plan.

- [x] Run focused validators.
- [x] Run broader regression checks and `git diff --check`.
- [x] Commit the scoped change.
- [ ] Push `largelexicon`.
