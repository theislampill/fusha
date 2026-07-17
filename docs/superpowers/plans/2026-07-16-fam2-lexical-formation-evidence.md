# FAM2 Lexical Formation-Evidence Producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a bounded candidate-only FAM2 formation-evidence producer and shared-compiler calibration packet for the 121-row lexical noun/adjective family.

**Architecture:** Add one stdlib-only producer that emits F-A typed formation facts or typed unresolved records, register its projector and named pattern rules in the existing registries, and extend `tools/fd_compiler.py` with a FAM2 compilation entry point that reuses its existing exact-span and fact-derived learner machinery. A fixture-only validator and harness gate prove the committed packet without requiring external corpus files.

**Tech Stack:** Python 3 standard library, JSON/JSONL, existing F-A contract helpers, existing registered projector registry, `unittest`, and `tools/check_regressions.py`.

**Execution status:** Complete in the FAM2 checkout. The external calibration used explicit caller-supplied inputs; no external corpus file is tracked and no public/live surface was mutated.

## Global Constraints

- External corpus and entry files are read-only and supplied through explicit CLI arguments.
- No tracked file may contain a lane-workspace path, production path/identifier, absolute path, secret, or PNG.
- Formation facts must carry exact occurrence/span, ownership, evidence mode, source address, producer/projector, guards, defeaters, dependencies, and reconstruction proof.
- Broken plural requires entry-backed singular plus a named pattern pair; label-only claims abstain typed and never project.
- Diacritic and orthography mismatches are defeaters, never fuzzy matches.
- Generated text must pass the N-LANG gate and use the public Ṣarf/Naḥw labels.
- All outputs are candidate-only with `pre_apply_not_authorized`, `public_materialization_allowed=false`, and `live_mutation_allowed=false`.
- Commits use the `fam2:` prefix and nothing is pushed.

---

### Task 1: Add red-first FAM2 fixtures and producer tests

**Files:**
- Create: `tools/test_fam2_lexical_producer.py`
- Create: `qamus/examples/fam2-lexical/pattern-registry.jsonl`
- Create: `qamus/examples/fam2-lexical/producer-fixtures.jsonl`
- Create: `qamus/examples/fam2-lexical/README.md`
- Modify: `tools/fam2_lexical_producer.py` only after the tests fail

**Interfaces:** Tests call `produce_record(row, entries=entries)`, `match_registered_pattern(...)`, and `validate_formation_record(...)`. Fixture rows use only exact surfaces, source addresses, explicit entry-form evidence, and named pattern IDs.

- [x] **Step 1: Write failing tests.** Cover six positive formation shapes, canary label-only abstention, sound-plural-not-broken, missing-singular route, noun/adjective ambiguity, hamza-seat mismatch, and exact surface reconstruction.
- [x] **Step 2: Run the focused test module.** The initial run failed at the absent producer import; the focused module passes after implementation.
- [x] **Step 3: Commit the red-first fixtures and tests.** `fam2: add red-first lexical formation fixtures`.

### Task 2: Implement strict pattern matching and F-A formation/unresolved records

**Files:**
- Create: `tools/fam2_lexical_producer.py`
- Modify: `tools/test_fam2_lexical_producer.py`
- Modify: `qamus/examples/fam2-lexical/pattern-registry.jsonl`

**Interfaces:**
- `match_registered_pattern(singular_surface, plural_surface, pattern_id, registry) -> dict | None` returns an exact pair witness or `None` with no orthographic repair.
- `build_formation_fact(input_row, evidence, *, projection_id, pattern_registry) -> dict` returns one F-A governed fact.
- `build_unresolved_record(input_row, *, blocker, reason, source_record_id) -> dict` returns an F-A unresolved envelope with `claim=null`.
- `produce_record(input_row, *, entries=(), pattern_registry=None) -> dict` runs only the family producer and validates the result before returning.
- `validate_formation_record(record) -> list[str]` combines F-A and producer semantic checks.

- [x] **Step 1: Implement exact Unicode/base-letter helpers and registry loading.** Written variants remain hard defeaters except named structural article/case routes.
- [x] **Step 2: Implement entry lookup.** Headwords and usage forms are scanned by exact address; glosses and morphlines never create formation evidence.
- [x] **Step 3: Implement the six bounded sub-shape routes.** Broken plural requires a registered pair; sound masculine/feminine plural, dual, nisba, and elative use named exact routes.
- [x] **Step 4: Build the closed F-A envelope.** Positive records carry pair and dependent formation facts; unresolved records carry no claim.
- [x] **Step 5: Run the focused tests.** `python -m unittest tools.test_fam2_lexical_producer -v` passes.
- [x] **Step 6: Implemented in the scoped FAM2 diff; final commit follows verification.**

### Task 3: Register the FAM2 projector and extend the shared compiler

**Files:**
- Modify: `tools/fact_projectors.py`
- Modify: `tools/fd_compiler.py`

**Interfaces:** Registered projector ID: `sarf.fam2.lexical_formation.v1`. Shared compiler helper: `build_formation_learner_view(record) -> dict`.

- [x] **Step 1: Exercise the shared compiler through the focused producer tests and validator.** Positive labels, reconstruction, and unresolved no-claim behavior pass.
- [x] **Step 2: Add the registered projector contract.** The central registry uses a two-vote gate and explicit orthography guard.
- [x] **Step 3: Extend `fd_compiler.py`.** Formation learner copy is derived only from typed facts and exact canonical surface.
- [x] **Step 4: Run compiler and registry neighbors.** `tools.test_fact_projectors` and `tools.test_fd_compiler` pass.
- [x] **Step 5: Implemented in the scoped FAM2 diff; final commit follows verification.**

### Task 4: Add explicit calibration CLI, fixtures, proof chain, and validator

**Files:**
- Modify: `tools/fam2_lexical_producer.py`
- Create: `tools/validate_fam2_lexical.py`
- Create: `qamus/examples/fam2-lexical/generated/*`
- Create: `FAM2-REPORT.md` in the lane workspace

**Interfaces:** The operational CLI requires `--stratified`, `--verdicts`, `--whitelist`, `--entries`, and `--output-dir`. The fixture-only validator supports `--self-test` and `--fixtures qamus/examples/fam2-lexical`.

- [x] **Step 1: Implement stable family selection.** Exact locations are joined; 40 rows are selected from the 121-row family, while all six sub-shapes remain in fixture controls.
- [x] **Step 2: Generate calibration records.** The packet contains one typed candidate or unresolved record per selected row; external files are not written.
- [x] **Step 3: Generate the first worked Ṣufahā proof.** The proof and real label-only abstention are separate generated artifacts.
- [x] **Step 4: Implement validator checks.** Schema, counts, routes, proof, N-LANG, no-live flags, and no external tokens are checked.
- [x] **Step 5: Write `FAM2-REPORT.md`.** The lane report includes per-row outcomes, stratified metrics, nonclaims, and §9 impact.
- [x] **Step 6: Run the validator.** Both FAM2 validator commands pass.
- [x] **Step 7: Commit the bounded packet.** Included in the final scoped FAM2 commits.

### Task 5: Wire the gate and run the explicit calibration

**Files:**
- Modify: `tools/check_regressions.py`
- Modify: `FAM2-REPORT.md`
- Modify: `qamus/examples/fam2-lexical/*` generated packet artifacts

- [x] **Step 1: Add the fixture-only harness block.** The harness runs the FAM2 self-test, focused unit tests, and packet validation with repo contents only.
- [x] **Step 2: Run the explicit-input calibration.** The caller-supplied read-only corpus and entries paths were passed explicitly; only packet artifacts were written.
- [x] **Step 3: Run targeted checks.** FAM2, projector, shared compiler, and packet checks pass.
- [x] **Step 4: Run the full harness and hygiene checks.** `python tools/check_regressions.py` returned `ALL REGRESSION CHECKS PASS`; `git diff --check` is clean.
- [x] **Step 5: Review staged scope.** The target checkout contains only FAM2 code, registry, fixtures, packet artifacts, docs, tests, and the harness hook; no PNG, external corpus, whitelist, renderer, or production path is staged.
- [x] **Step 6: Commit without pushing.** Completed with `fam2:` commits; branch remains local and unpushed.
