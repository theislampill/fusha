# FAM5 derived-verb producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a candidate-only, source-grounded derived-verb typed-fact producer for the exact seven-row FAM5 working set.

**Architecture:** Extend the FAM4 producer carrier and F-A contract in one FAM5 module. A closed, fixture-backed registry contains only the Form-II, Form-IV, Form-VIII, and quadriliteral shapes attested by the surveyed rows; exact entry-form evidence gates every candidate, while missing evidence becomes a typed unresolved record. The same module builds the seven-row packet; a small report builder renders the survey and precision/abstention summary.

**Tech Stack:** Python standard library, JSONL review artifacts, existing F-A typed-claim contract, existing FAM4 helpers/registries, `unittest`, repository regression harness.

## Global Constraints

- Reuse the FAM4 finite-verb producer + verb-affix registry + weak-root defeater registry + F-A contract + evidence modes; never create a parallel pipeline.
- Derived-form producers must preserve root; template; derivational additions; inflectional prefixes/suffixes; weak-letter operations; assimilation and gemination; hamzat al-waṣl; voice; person/number/gender; mood; exact guards and defeaters.
- Ambiguous cases ABSTAIN.
- Every typed fact letter-level: each written base letter is owned by exactly one class; Form-V/VI ت is `derivative_prefix`; Form-VIII ت is `derivative_infix`; gemination uses Treatment-C and idghām A–D metadata; hamzat al-waṣl is a governed class.
- Implement template rules only for forms the seven rows attest and evidence certifies.
- No corpus-wide projection from surface templates alone; corpus data remains read-only.
- N-LANG public labels are exactly `Ṣarf — how this piece forms the word` and `Naḥw — what this piece does here`.
- Candidate mode only: `pre_apply_not_authorized`; no `*.png` tracked; RM-09 and repo self-containment remain gates.
- Commits use the `fam5:` prefix; no pushes.

---

### Task 1: Add RED-first FAM5 fixture matrix and focused tests

**Files:**
- Create: `qamus/examples/fam5-derived-verbs/entry-fixtures.jsonl`
- Create: `qamus/examples/fam5-derived-verbs/derived-form-registry.jsonl`
- Create: `qamus/examples/fam5-derived-verbs/producer-fixtures.jsonl`
- Create: `tools/test_fam5_derived_verb_producer.py`

**Interfaces:**
- Tests import `tools.fam5_derived_verb_producer` and call `produce_record(row, entries=..., registry=...)`.
- Fixture rows carry `expected_status`, optional `expected_pattern`, and an exact `expected_blocker` for abstentions.

- [ ] **Step 1: Write the failing fixture matrix and tests**

  Add six positive entry-backed rows covering Form-II active/energic, Form-IV active/passive, Form-VIII passive/geminate with hamzat al-waṣl, and quadriliteral; add at least eight adversarial rows covering the required owner cases. Assert exact status, blocker, typed field preservation, one-class-per-base-letter ownership, and reconstruction behavior.

- [ ] **Step 2: Run the focused test to verify RED**

  Run `python -m unittest tools.test_fam5_derived_verb_producer -v` from the writable checkout. Expected: import failure because `tools.fam5_derived_verb_producer` does not yet exist.

### Task 2: Implement the evidence-gated producer and FAM5 projector registration

**Files:**
- Create: `tools/fam5_derived_verb_producer.py`
- Modify: `tools/fact_projectors.py`
- Modify: `tools/test_fact_projectors.py`

**Interfaces:**
- `load_registry(path=None) -> list[dict]` validates the closed attested-form registry.
- `produce_record(row, *, entries, registry=None, weak_root_registry=None) -> dict` returns one F-A contract record.
- `build_calibration_packet(strat_rows, verdict_rows, fam4_rows, entries, ...) -> dict` returns seven ordered records plus survey/metrics.
- The registered projector `sarf.fam5.derived_verb.v1` returns a candidate only for a caller-supplied exact entry form + named supported pattern; otherwise it returns an abstention with `materialization_allowed: false`.

- [ ] **Step 1: Implement FAM4-carrier adapters and exact source join**

  Reuse FAM4 token/span/hash/entry-match/base-fact functions. Validate `v575=verified`, exact or Quran-annotation-only entry-form equality, and verb/quadriliteral section. Keep STRAT root claims as non-certifying hints when no source form joins.

- [ ] **Step 2: Implement the closed derived-form matchers**

  Match only registry patterns for Form-II gemination/energic, Form-IV active/passive, Form-VIII infix/hamzat-al-waṣl/passive/gemination, and quadriliteral perfect. Treat shadda as one written token; keep internal gemination/Treatment-C metadata and idghām A–D classification without splitting it. Match every base letter to exactly one internal owner class and preserve all morphology fields.

- [ ] **Step 3: Implement typed candidate and typed abstention records**

  Candidate records contain one entry attestation plus one `derived_verb_evidence` fact, exact reconstruction proof, source addresses, guard/defeater lists, N-LANG labels, and disabled materialization. Non-candidates contain exactly one `derived_verb_pending` fact, no claim, the exact route, and disabled materialization.

- [ ] **Step 4: Register and test the FAM5 projector**

  Add the contract, callable guard, registry entry, and focused registry assertions. Run `python -m unittest tools.test_fam5_derived_verb_producer tools.test_fact_projectors -v`; expected: PASS after the implementation satisfies the RED matrix.

### Task 3: Build the seven-row packet and report

**Files:**
- Create: `tools/build_fam5_report.py`
- Create: `qamus/examples/fam5-derived-verbs/README.md`
- Create: `qamus/examples/fam5-derived-verbs/generated/calibration-sample.jsonl`
- Create: `qamus/examples/fam5-derived-verbs/generated/derived-verb-facts.jsonl`
- Create: `qamus/examples/fam5-derived-verbs/generated/unresolved-records.jsonl`
- Create: `qamus/examples/fam5-derived-verbs/generated/calibration-summary.json`
- Create: `FAM5-REPORT.md`

**Interfaces:**
- `tools/build_fam5_report.py` accepts the lane STRAT/v575 inputs, read-only corpus entries/whitelist, and the committed FAM4 packet; it writes only the FAM5 generated directory and report.

- [ ] **Step 1: Run the producer over the seven-row working set**

  Use `strat-455.jsonl`, `v575-verdicts.jsonl`, `../../data/entries.jsonl`, `../../data/rh_live_01_beta_whitelist.jsonl`, and the four named FAM4 packet rows. Preserve the source survey and do not copy the corpus into the repo.

- [ ] **Step 2: Render the report and packet metadata**

  Record the three exact-entry candidates, two STRAT source gaps, one duplicated Form-IV source gap, and one FAM4 owner-gated Form-II/energic row; include precision and abstention by form class, zero-false-projection basis, exact nonclaims, compounding impact, and candidate Ṣarf skill increments.

- [ ] **Step 3: Validate committed artifacts**

  Run the FAM5 fixture/packet validator, JSON artifact ergonomics checks, `git diff --check`, tracked-image scan, and forbidden external path/source scan.

### Task 4: Wire the repo self-test and full harness

**Files:**
- Modify: `tools/check_regressions.py`
- Create: `tools/validate_fam5_derived_verbs.py`

**Interfaces:**
- `validate_fam5_derived_verbs.py --self-test` validates fixtures and projector registration without external inputs.
- The default validator validates the committed seven-row packet and all generated JSONL artifacts from repo contents alone.

- [ ] **Step 1: Add FAM5 self-test and packet checks**

  Require at least six positive and eight adversarial fixtures, all seven packet rows, exact one-class ownership, candidate-only flags, no candidate for surface-template-only input, and no images.

- [ ] **Step 2: Add the FAM5 gates beside the FAM4 harness block**

  Run the FAM5 self-test, focused unit tests, and committed packet validator with no external corpus dependency; fail closed on any nonzero command or missing pass marker.

- [ ] **Step 3: Run the full harness**

  Run `python tools/check_regressions.py` with a bounded long timeout and retain the complete pass/fail output for handoff.

### Task 5: Final verification and commit

- [ ] **Step 1: Re-read the requirements against the final packet**
- [ ] **Step 2: Run the focused tests, validators, full harness, `git diff --check`, RM-09/image scans, and status/diff inspection**
- [ ] **Step 3: Commit the explicit FAM5 paths with `fam5: derived-verb producer calibration packet`**
- [ ] **Step 4: Report exact done, gated, unverified, and nonclaims state; do not push**
