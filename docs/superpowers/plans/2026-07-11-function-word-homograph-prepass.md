# Function-Word Homograph Pre-Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, exact-diacritic candidate pre-pass that emits a v2 function-word queue and an evidence-rich calibration report without mutating the v1 queue.

**Architecture:** A tracked JSON rule table declares literal fully vocalized surfaces for the three approved homograph families. A Python builder joins every v1 queue row to the canonical loc-surface index, applies at most one exact rule, records before/after audit fields, adds the fused-divine-name route, and emits JSONL plus a pretty JSON report. Context-sensitive subfunctions remain family-level classes for later naḥw review.

**Tech Stack:** Python 3 standard library, JSON/JSONL artifacts, `unittest`, existing repository artifact validators.

## Global Constraints

- Match only literal exact-diacritic patterns from the tracked rule table.
- Leave out-of-table and ambiguous rows' particle class unchanged with `prepass_rule: null`.
- Emit only `funcword-queue.v2.jsonl` and a pre-pass report; do not alter the v1 queue or canonical data.
- Reproduce at least 28 of 31 calibration homograph corrections and cite every calibration row.
- Set `boundary_route: divine_name_entry` on exactly the 11 `lillahi_fused_divine_name` rows.
- Do not edit `tools/check_regressions.py`; do not push.

---

### Task 1: Exact-Diacritic Rule Contract and Red Tests

**Files:**
- Create: `nahw/rules/funcword-homograph-prepass-rules.json`
- Create: `tools/test_funcword_homograph_prepass.py`

**Interfaces:**
- Consumes: v1 queue rows, loc-surface rows, and the 200-row calibration JSONL.
- Produces: failing tests for `load_rules()`, `apply_prepass()`, and `build_report()` in `tools.funcword_homograph_prepass`.

- [ ] Add literal pattern rows for `man_fatha_not_min`, `in_light_not_inna`, and `an_light_not_anna`; reject wildcards, duplicate patterns, and duplicate rule ids.
- [ ] Add one red test per family using the calibration's real locations and canonical loc-surface bytes.
- [ ] Add red abstention tests for out-of-table surfaces and false-positive normalization collisions.
- [ ] Add red tests for 31 calibration citations, at least 28 reproduced corrections, and exactly 11 divine-name routes.
- [ ] Run `python tools/test_funcword_homograph_prepass.py` and confirm failure because the builder module is absent.

### Task 2: Deterministic Builder and Candidate Artifacts

**Files:**
- Create: `tools/funcword_homograph_prepass.py`
- Create: `qamus/indexes/largelexicon/append-queue/class2/funcword-queue.v2.jsonl`
- Create: `qamus/reports/funcword-homograph-prepass.report.json`

**Interfaces:**
- Consumes: `--queue`, `--loc-surface`, `--rules`, optional `--calibration`.
- Produces: v2 JSONL rows with `schema`, `prepass_rule`, `particle_class_before`, `particle_class_after`, and optional `boundary_route`; a pretty deterministic report with per-rule counts and calibration citations.

- [ ] Implement strict loaders, literal rule validation, exact location-to-surface joining, and one-rule-only matching.
- [ ] Preserve every v1 row field except the intentional v2 schema/class/audit additions; never alter target scripture surface bytes.
- [ ] Emit family-level classes where diacritics settle the lexeme family but not the contextual subfunction.
- [ ] Emit honest residual calibration rows for non-family wrong-entry, false-positive, and uncovered cases.
- [ ] Run the focused test suite until all tests pass.
- [ ] Generate the committed v2 queue and report from repository defaults.

### Task 3: Closure Verification and Commit

**Files:**
- Verify all files above; do not modify other tracked paths.

**Interfaces:**
- Consumes: generated artifacts and repository harness.
- Produces: byte-identical double-run evidence, workspace/fresh-clone harness evidence, and the exact requested commit.

- [ ] Generate twice into separate temporary directories and compare hashes/bytes.
- [ ] Run focused tests, artifact ergonomics, artifact classification, and `git diff --check`.
- [ ] Run the complete regression harness in the workspace with the unrelated calibration-only `.inputs/` trigger safely hidden and restored.
- [ ] Clone the resulting branch locally, run focused checks and the complete regression harness there, and confirm no owner-only inputs are required.
- [ ] Review `git diff`, stage only explicit requested paths, verify the staged set, and commit as `feat(qamus): function-word homograph pre-pass (diacritic-deterministic)`.
