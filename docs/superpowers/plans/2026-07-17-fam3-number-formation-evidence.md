# FAM3 Number-Word Formation-Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a candidate-only number-word producer and all-57-row calibration packet for the `number_words` family.

**Architecture:** Add one FAM3 producer that imports FAM2 exact-surface and F-A carrier helpers, uses VNMAP `WhitelistIndex` for the verse-context edge, and consumes a FAM3 JSONL number-pattern registry. Register the FAM3 projector in `tools/fact_projectors.py`, compile learner copy through the existing formation-view contract, and keep every unsupported or weakly joined row as a typed unresolved record.

**Tech Stack:** Python 3 standard library, JSON/JSONL, existing typed-claim contract, FAM2 producer helpers, VNMAP ledger index, `unittest`, and `tools/check_regressions.py`.

## Global Constraints

- External stratified rows, verdicts, whitelist, and entries are read-only and accepted only through explicit CLI arguments.
- The calibration packet includes all 57 family rows; no sampling or external corpus copy is allowed.
- A formation label is never evidence by itself; positive output requires an entry-backed base, a registered number rule, evidence mode, source addresses, and reconstruction proof.
- FAM2 orthography guards and exact written spans are reused; hamza-seat, tāʾ/هāʾ, defective, and unsupported near-miss forms abstain.
- Learner copy uses `Ṣarf — how this piece forms the word` and `Naḥw — what this piece does here` and passes N-LANG validation.
- Every output is candidate-only with `pre_apply_not_authorized`, false public/live mutation flags, and no application path.
- Tracked files contain no absolute/private/production paths or identifiers, no secrets, and no PNG files.
- Commits use the `fam3:` prefix and no push is performed.

---

### Task 1: Add red-first number registry, fixtures, and tests

**Files:**
- Create: `qamus/examples/fam3-numbers/pattern-registry.jsonl`
- Create: `qamus/examples/fam3-numbers/entry-fixtures.jsonl`
- Create: `qamus/examples/fam3-numbers/producer-fixtures.jsonl`
- Create: `qamus/examples/fam3-numbers/README.md`
- Create: `tools/test_fam3_number_producer.py`

**Interfaces:** Tests call `produce_record(row, entries=..., whitelist_rows=..., pattern_registry=...)`, `match_registered_number_pattern(...)`, and `validate_number_record(...)`. Fixtures remain repository-only and contain logical addresses, not input paths.

- [ ] Write at least six positive fixtures covering bare cardinal, gender-polarity, ordinal, compound 11–19, tens, and pairwise/other-number formation.
- [ ] Write at least six adversarial fixtures covering label-only ordinal, wrong gender, `سبع` number/noun ambiguity, context-only entry join, hamza/orthography mismatch, missing counted-noun evidence, and unsupported surface.
- [ ] Run `python -m unittest tools.test_fam3_number_producer -v` and confirm the new tests fail because the producer module is absent.
- [ ] Commit the red-first fixture/test boundary with `fam3: add red-first number formation fixtures`.

### Task 2: Implement strict number formation and unresolved records

**Files:**
- Create: `tools/fam3_number_producer.py`

**Interfaces:**
- `load_pattern_registry(path=None) -> list[dict]` validates unique named FAM3 rules.
- `classify_sub_shape(row) -> str` uses written form and source-addressed local context, never a label as evidence.
- `match_registered_number_pattern(base_surface, observed_surface, pattern_id, context, registry) -> dict | None` returns an exact witness or no match.
- `produce_record(row, *, entries, whitelist_rows=None, pattern_registry=None) -> dict` emits one F-A candidate or typed unresolved envelope.
- `validate_number_record(record) -> list[str]` combines the shared contract and FAM3 semantic gates.
- `build_calibration_packet(...)` and `write_calibration_packet(...)` operate on all 57 selected rows.

- [ ] Import FAM2 `_surface_relation`, `_strip_case`, `_letters`, `_form_rows`, `_entry_map`, `_sha256`, and fact-carrier helpers rather than duplicating a second contract pipeline.
- [ ] Build the whitelist join through VNMAP `WhitelistIndex`; retain only safe logical fields and treat `entry_id` as context unless the observed surface matches the joined entry.
- [ ] Require exact headword/sense/form evidence for the base, distinguish orthographic near-misses, and route missing/context-only/formless joins to typed blockers.
- [ ] Implement only registry-backed routes for the surveyed number shapes, including counted-noun and homograph guards.
- [ ] Emit the base fact, dependent formation fact, source-address set, registered rule ID, guards/defeaters, and proof for candidates; emit no claim for unresolved rows.
- [ ] Generate shared-shape learner copy with the two public labels and exact reconstruction.
- [ ] Run the focused tests through red-green cycles and commit `fam3: implement guarded number formation producer`.

### Task 3: Register the FAM3 projector and learner contract

**Files:**
- Modify: `tools/fact_projectors.py`
- Modify: `tools/fd_compiler.py` only if the shared number labels require an additive shape mapping.
- Modify: `tools/test_fact_projectors.py`

**Interfaces:** Projector ID is `sarf.fam3.number_formation.v1`; its output fact type is `formation_evidence`, its input fact type is `entry_base_attestation`, and it is `two_vote_required` with a named orthography guard.

- [ ] Add the FAM3 guard, projector adapter, contract, and registry registration without changing FAM2 behavior.
- [ ] Add the FAM3 projector ID to the existing registry test set and prove a matching and nonmatching pattern result.
- [ ] Keep learner text fact-derived, English-led, and free of route/source/process wording.
- [ ] Run `python -m unittest tools.test_fact_projectors tools.test_fd_compiler -q` and commit `fam3: register number formation projector`.

### Task 4: Add fixture validator, calibration artifacts, and report

**Files:**
- Create: `tools/validate_fam3_numbers.py`
- Create: `FAM3-REPORT.md`
- Create: `qamus/examples/fam3-numbers/generated/calibration-sample.jsonl`
- Create: `qamus/examples/fam3-numbers/generated/formation-facts.jsonl`
- Create: `qamus/examples/fam3-numbers/generated/unresolved-records.jsonl`
- Create: `qamus/examples/fam3-numbers/generated/calibration-summary.json`
- Create: `qamus/examples/fam3-numbers/generated/fixture-formation-facts.jsonl`
- Create: `qamus/examples/fam3-numbers/generated/fixture-unresolved-records.jsonl`

**Interfaces:** `python tools/validate_fam3_numbers.py --self-test` validates fixtures only; the same validator with `--fixtures qamus/examples/fam3-numbers` validates the committed packet. The producer CLI requires `--stratified`, `--verdicts`, `--whitelist`, `--entries`, and `--output-dir`.

- [ ] Validate fixture counts, required adversarial routes, candidate-only flags, fact dependencies, reconstruction proofs, N-LANG labels, and no external-path/image leakage.
- [ ] Run the explicit calibration against the lane inputs and read-only corpus, with output limited to the FAM3 example directory.
- [ ] Confirm exactly 57 packet records and split records by projection status.
- [ ] Compute sub-shape populations, candidate counts, contract-bounded precision, abstention counts/rates, and a per-row outcome table.
- [ ] Write `FAM3-REPORT.md` with the survey, precision/abstention table, zero-false-projection attestation basis, exact nonclaims, and finite-verbs/F-C compounding impact.
- [ ] Commit `fam3: add number calibration packet and report`.

### Task 5: Wire the full harness and close the branch

**Files:**
- Modify: `tools/check_regressions.py`
- Modify: `FAM3-REPORT.md` if verification results change the report.

- [ ] Add fixture-only FAM3 self-test, focused unit test, and packet validator checks beside FAM2/VNMAP gates.
- [ ] Run `git diff --check`, the FAM3 self-test, focused tests, FAM2/VNMAP neighbors, and the full `python tools/check_regressions.py` harness.
- [ ] Run RM-09/no-image checks over tracked files and inspect the final diff and staged file list.
- [ ] If a usage limit interrupts execution, commit the verified WIP with `fam3:` and add `PAUSED-STATE.md`; otherwise do not add a pause substitute.
- [ ] Commit the final harness/report adjustment with `fam3: wire number producer harness` and leave the branch unpushed.
