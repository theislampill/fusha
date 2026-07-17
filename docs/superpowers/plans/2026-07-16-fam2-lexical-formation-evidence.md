# FAM2 Lexical Formation-Evidence Producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a bounded candidate-only FAM2 formation-evidence producer and shared-compiler calibration packet for the 121-row lexical noun/adjective family.

**Architecture:** Add one stdlib-only producer that emits F-A typed formation facts or typed unresolved records, register its projector and named pattern rules in the existing registries, and extend `tools/fd_compiler.py` with a FAM2 compilation entry point that reuses its existing exact-span and fact-derived learner machinery. A fixture-only validator and harness gate prove the committed packet without requiring external corpus files.

**Tech Stack:** Python 3 standard library, JSON/JSONL, existing F-A contract helpers, existing registered projector registry, `unittest`, and `tools/check_regressions.py`.

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

**Interfaces:** Tests call `produce_record(row, entries=entries)`, `match_registered_pattern(...)`, `build_formation_fact(...)`, `build_unresolved_record(...)`, `validate_formation_record(...)`, and `classify_sub_shape(...)`. Fixture rows use only exact surfaces, source addresses, explicit entry-form evidence, and named pattern IDs.

- [ ] **Step 1: Write failing tests.** Cover six positive formation shapes, canary label-only abstention, sound-plural-not-broken, missing-singular route, noun/adjective ambiguity, hamza-seat mismatch, and exact surface reconstruction.
- [ ] **Step 2: Run the focused test module.** Run `python -m unittest tools.test_fam2_lexical_producer -v`. Expected result is a red import/interface failure because the FAM2 producer does not yet exist.
- [ ] **Step 3: Commit the red-first fixtures and tests.** Run `git diff --check`, then commit the fixture/test/doc set with `fam2: add red-first lexical formation fixtures`.

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

- [ ] **Step 1: Implement exact Unicode/base-letter helpers and registry loading.** Preserve hamza seats, `ة`, `ى`, and all written marks; permit only an explicitly documented case-ending normalization for entry-form lookup and reject every other spelling difference.
- [ ] **Step 2: Implement entry lookup.** Scan caller-supplied entry headwords and usage forms by exact surface/address. Never consult gloss, meaning, or morphline text. Require a unique entry-backed singular for broken plural and route duplicates to `entry_lookup_missing` or `pattern_unresolved`.
- [ ] **Step 3: Implement the six bounded sub-shape routes.** Broken plural requires a registered pair; sound masculine/feminine plural, dual, nisba, and elative require explicit pair/base evidence and exact registry matches. Unsupported or ambiguous shapes abstain.
- [ ] **Step 4: Build the closed F-A envelope.** Include exact spans, ownership, source addresses, evidence mode, rule/projector metadata, guards, defeaters, dependencies, and reconstruction proof. Positive facts bind to a candidate claim; unresolved records carry no claim and the mapped learner statement.
- [ ] **Step 5: Run the focused tests.** Run `python -m unittest tools.test_fam2_lexical_producer -v`; expected result is green for the producer contract and all adversarial routes.
- [ ] **Step 6: Commit.** Run `git diff --check` and commit with `fam2: implement strict lexical formation producer`.

### Task 3: Register the FAM2 projector and extend the shared compiler

**Files:**
- Modify: `tools/fact_projectors.py`
- Modify: `tools/fd_compiler.py`
- Create: `tools/test_fam2_compiler.py`
- Create: `qamus/schemas/fam2-calibration-report.schema.json`

**Interfaces:**
- Registered projector ID: `sarf.fam2_lexical_formation.v1`.
- Shared compiler entry point: `compile_fam2_rows(strat_rows, verdict_rows, source_rows, entries, *, selected_locs, records_by_loc, occurrence_index) -> tuple[list[dict], dict]`.
- Shared view helper: `build_fam2_fact_derived_views(surface, record, source_segments=None) -> dict`.

- [ ] **Step 1: Write failing compiler tests.** Assert positive facts generate both exact learner labels and compact/expanded identity; unresolved records never generate a candidate view; source surfaces reconstruct exactly; the canary cannot project; and per-subshape counts recompute.
- [ ] **Step 2: Verify the tests fail.** Run `python -m unittest tools.test_fam2_compiler -v`; expected result is missing shared FAM2 compiler interfaces.
- [ ] **Step 3: Add the registered projector contract.** Register the named FAM2 projector with a two-vote gate and explicit defeater callables. The projector delegates to the FAM2 producer and remains candidate-only.
- [ ] **Step 4: Extend `fd_compiler.py`.** Reuse existing exact segment, payload ID, N-LANG, and no-live helpers. Derive formation learner text only from typed fact fields, and represent unresolved routes as typed blockers rather than source prose.
- [ ] **Step 5: Run compiler tests and the neighboring compiler tests.** Run `python -m unittest tools.test_fam2_compiler tools.test_fd_compiler tools.test_fd2_rerun -q`; expected result is green.
- [ ] **Step 6: Commit.** Run `git diff --check` and commit with `fam2: register lexical projector in shared compiler`.

### Task 4: Add explicit calibration CLI, fixtures, proof chain, and validator

**Files:**
- Modify: `tools/fam2_lexical_producer.py`
- Create: `tools/validate_fam2_lexical.py`
- Create: `qamus/examples/fam2-lexical/calibration-sample.jsonl`
- Create: `qamus/examples/fam2-lexical/calibration-unresolved.jsonl`
- Create: `qamus/examples/fam2-lexical/calibration.meta.json`
- Create: `qamus/examples/fam2-lexical/sufaha-proof.json`
- Create: `qamus/examples/fam2-lexical/sufaha-proof.meta.json`
- Create: `FAM2-REPORT.md`

**Interfaces:** The operational CLI requires `--strat-455`, `--v575-verdicts`, `--whitelist`, `--entries`, and `--output-dir`. The fixture-only validator supports `--self-test` and `--fixtures qamus/examples/fam2-lexical`.

- [ ] **Step 1: Implement stable family selection.** Join exact locations, select at least 40 rows stratified across the six sub-shape routes and unresolved classes, and store only basenames/scope metadata in artifacts.
- [ ] **Step 2: Generate calibration records.** Run the producer over the selected rows and write one typed fact or typed unresolved record per row; do not write the external corpus or whitelist.
- [ ] **Step 3: Generate the first worked Ṣufahā proof.** Use the exact `2:13:12` occurrence fixture, entry-backed `سَفِيهًا`/`سُفَهَاء`, pattern `فَعِيل→فُعَلَاء`, the full fact dependency chain, and compiler-generated Ṣarf/Naḥw learner copy. Keep the real label-only canary fixture unresolved beside it.
- [ ] **Step 4: Implement validator checks.** Validate schema, exact record counts, selected locations, positive/unresolved accounting, pattern witnesses, canary abstention, N-LANG fields, compact/expanded identity, no paths, no live flags, no corpus-wide claim, and report recomputation.
- [ ] **Step 5: Write `FAM2-REPORT.md`.** Include per-row outcomes, precision and abstention by sub-shape, zero-false-projection basis, exact nonclaims, and Compounding Impact §9 covering reusable registry entries, unlocks beyond 121, fast paths, and Ṣarf skill-increment candidates.
- [ ] **Step 6: Run the validator.** Run `python tools/validate_fam2_lexical.py --self-test` and `python tools/validate_fam2_lexical.py --fixtures qamus/examples/fam2-lexical`; expected markers are `FAM2 LEXICAL SELF-TEST PASS` and `FAM2 LEXICAL FIXTURES PASS`.
- [ ] **Step 7: Commit the bounded packet.** Run `git diff --check` and commit with `fam2: add lexical calibration and sufaha proof packet`.

### Task 5: Wire the gate and run the explicit calibration

**Files:**
- Modify: `tools/check_regressions.py`
- Modify: `FAM2-REPORT.md`
- Modify: `qamus/examples/fam2-lexical/*` generated packet artifacts

- [ ] **Step 1: Add the fixture-only harness block.** Run the FAM2 self-test, focused unit test module, and committed fixture validation using only repository paths; do not add external defaults.
- [ ] **Step 2: Run the explicit-input calibration.** Pass the lane’s stratification/verdict files and caller-supplied read-only corpus/entries paths to the CLI; write only the repository packet artifacts and read back the report counts.
- [ ] **Step 3: Run targeted checks.** Run `python -m unittest tools.test_fam2_lexical_producer tools.test_fam2_compiler -q`, both FAM2 validator commands, and `python tools/check_artifact_ergonomics.py`.
- [ ] **Step 4: Run the full harness and hygiene checks.** Run `python tools/check_regressions.py` and `git diff --check`; expected final marker is `ALL REGRESSION CHECKS PASS`.
- [ ] **Step 5: Review staged scope.** Confirm only FAM2 code, registry, fixtures, docs, report, and harness files are changed; confirm no `*.png`, external corpus, whitelist, renderer, or production path/identifier is staged.
- [ ] **Step 6: Commit without pushing.** Commit remaining changes with `fam2: wire lexical producer calibration gate`.
