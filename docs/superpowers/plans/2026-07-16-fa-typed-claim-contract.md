# F-A Typed-Claim Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the additive, versioned F-A typed-claim contract, its fail-closed authoring validator, alias normalization, internal legacy record, unresolved-language table, fixtures, harness gate, and FA report.

**Architecture:** Keep the historical tranche-1 schemas and projectors compatible while adding optional governed-contract references. Put the stricter closed contract, semantic checks, alias normalization, and unresolved-language lookup in a stdlib-only Python module and CLI. Validate a governed envelope whose projection claims bind to fact IDs and exact fact fields; keep legacy records internal and unresolved statements English-first.

**Tech Stack:** Python 3.11 standard library, repository mini-schema validator, JSON/JSONL, `unittest`, Git.

## Global Constraints

- Additive only; existing validators and tranche-1 fixtures must remain valid.
- Every typed fact used for projection must carry or resolve to occurrence identity, fact type, exact span, ownership, source/address, certification/evidence, producer/version, rule/projector, guards/defeaters, blockers, and dependencies.
- A prose assertion is not itself a typed fact; learner-visible claims require explicit fact-field bindings.
- Accept `qg-negative` only on input, normalize it to `qg-negation`, and never emit the deprecated alias.
- `legacy_valid` is internal-only and must never be learner-visible or live-materialized.
- Unresolved-language output is plain English and does not resolve missing linguistic facts.
- Do not change whitelist data, renderer files, CSS, live/apply paths, or production data; do not push.
- Commits are prefixed `fa:`.

---

### Task 1: Record and validate the approved contract design

**Files:**
- Create: `docs/superpowers/specs/2026-07-16-fa-typed-claim-contract-design.md`
- Create: `docs/superpowers/plans/2026-07-16-fa-typed-claim-contract.md`

- [x] **Step 1: Capture the approved design boundary**

The design document records the closed contract, compatibility carriers, normalization rule, legacy boundary, unresolved mapping, validator behavior, harness gate, verification, and nonclaims from the pre-approved brief.

- [x] **Step 2: Self-review the documents**

Check that there are no placeholders, no renderer/whitelist scope expansion, and every requested Q6-1/Q6-4/Q6-7 surface has an implementation task below.

- [ ] **Step 3: Commit the durable design and plan**

Run:

```powershell
git diff --check
git add docs/superpowers/specs/2026-07-16-fa-typed-claim-contract-design.md docs/superpowers/plans/2026-07-16-fa-typed-claim-contract.md
git commit -m "fa: record typed-claim contract design"
```

Expected: only the two new planning documents are staged and the commit succeeds without a push.

### Task 2: Write red-first contract tests and fixtures

**Files:**
- Create: `tools/test_typed_claim_contract.py`
- Create: `qamus/examples/fa-contract/prose-only.invalid.jsonl`
- Create: `qamus/examples/fa-contract/tranche1-canary.valid.jsonl`
- Create: `qamus/examples/fa-contract/alias-normalization.jsonl`
- Create: `qamus/examples/fa-contract/legacy-valid.jsonl`
- Create: `qamus/examples/fa-contract/unresolved-language-map.json`
- Create: `qamus/examples/fa-contract/README.md`

- [ ] **Step 1: Write tests for the wished-for APIs**

Test that `validate_contract_record` rejects learner text with no governed fact binding, accepts the tranche-1 `3:141:4` candidate-derived envelope, normalizes `qg-negative` in nested input, rejects deprecated aliases in generated output, validates the legacy record as internal-only, resolves every public unresolved status to an English statement, and rejects a legacy record with `learner_visible: true`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tools.test_typed_claim_contract -v
```

Expected: import/API failures because the contract module and schema do not yet exist.

### Task 3: Add the versioned governed schemas and additive tranche-1 references

**Files:**
- Create: `qamus/schemas/typed-claim-contract.schema.json`
- Create: `qamus/schemas/legacy-valid-record.schema.json`
- Create: `qamus/schemas/unresolved-language-map.schema.json`
- Modify: `qamus/schemas/fact-ledger-row.schema.json`
- Modify: `qamus/schemas/morphology-candidate-lattice.schema.json`
- Modify: `qamus/schemas/dependency-candidate-lattice.schema.json`
- Modify: `qamus/schemas/morphosyntax-token.schema.json`
- Modify: `qamus/schemas/canonical-hover-payload.schema.json`
- Modify: `qamus/schemas/public-hover-projection.schema.json`
- Modify: `qamus/schemas/tranche1-projection-crosswalk.schema.json`

- [ ] **Step 1: Define the closed governed contract**

Use `qamus.typed_claim_contract.v1`, `contract_version: 1.0.0`, required canonical occurrence, `facts`, and `projection` fields. Require exact Unicode spans, primary/secondary ownership, source/address, status/evidence, producer/projector, guards/defeaters, blockers, dependency IDs, and explicit claim bindings.

- [ ] **Step 2: Define legacy and unresolved schemas**

Require the six Q6-4 legacy fields plus `learner_visible: false` and `public_materialization_allowed: false`. Require one unique English-first mapping row per public unresolved status and exclude `legacy_valid` from public mapping.

- [ ] **Step 3: Add optional `governed_contract_ref` carriers**

Add the same optional object shape—`contract_id`, `contract_version`, and nonempty `fact_ids`—without changing existing required arrays or old constants.

- [ ] **Step 4: Run schema-focused tests**

Run:

```powershell
python -m unittest tools.test_typed_claim_contract -v
```

Expected: schema tests proceed to module/API failures, while no tranche-1 schema regression is introduced.

### Task 4: Implement alias normalization, semantic validation, and projection helpers

**Files:**
- Create: `tools/typed_claim_contract.py`
- Create: `tools/validate_typed_claim_contract.py`
- Modify: `tools/test_typed_claim_contract.py`

- [ ] **Step 1: Implement the minimal immutable alias table and normalizer**

Expose `DEPRECATED_QG_ALIASES = {"qg-negative": "qg-negation"}` and `normalize_aliases(value)`. Normalize recognized class fields recursively on input, preserve unrelated values, and expose `assert_no_deprecated_aliases`.

- [ ] **Step 2: Implement contract schema and semantic checks**

Load the local schema, validate closed structure through `fact_ledger._validate_node`, then enforce fact-ID joins, exact span bounds and text, claim bindings, status/blocker consistency, ownership, source/address, and internal-only legacy rules. Reject raw projection-shaped learner claims with the explicit prose-only error.

- [ ] **Step 3: Implement unresolved-language consumption**

Load `unresolved-language-map.json`, validate unique status coverage and plain-English statements, and expose `learner_statement_for(status)`. Public unresolved projections must use the table; `legacy_valid` has no public statement.

- [ ] **Step 4: Run the red/green focused suite**

Run:

```powershell
python -m unittest tools.test_typed_claim_contract -v
python tools/validate_typed_claim_contract.py --self-test
```

Expected: all focused tests and the self-test pass, including the preserved red prose-only fixture.

### Task 5: Wire the authoring gate into the full harness

**Files:**
- Modify: `tools/check_regressions.py`
- Modify: `tools/test_typed_claim_contract.py`

- [ ] **Step 1: Add the gate-14-shaped self-test invocation**

Run the contract validator self-test with a bounded timeout and require its exact PASS marker. Keep exception handling and failure reporting consistent with the surrounding gate-14 block.

- [ ] **Step 2: Add a real committed-fixture invocation**

Run the validator against `qamus/examples/fa-contract/tranche1-canary.valid.jsonl`, the legacy fixture, alias fixture, and unresolved map; require zero errors and a stable PASS marker.

- [ ] **Step 3: Run focused harness checks**

Run:

```powershell
python tools/validate_typed_claim_contract.py --fixtures qamus/examples/fa-contract
python tools/check_regressions.py
```

Expected: the new gate is green; the full harness output ends with `ALL REGRESSION CHECKS PASS`.

### Task 6: Final verification, report, and commit

**Files:**
- Create: `FA-REPORT.md`

- [ ] **Step 1: Run fresh verification commands**

Run the focused unit suite, contract self-test, fixture validator, tranche-1 validator/self-tests, artifact ergonomics, `git diff --check`, and the full `python tools/check_regressions.py` command again after all edits.

- [ ] **Step 2: Review scope and exact diff**

Run:

```powershell
git status --short --branch
git diff --stat
git diff --check
git diff --name-only
```

Confirm no whitelist, renderer, CSS, live/apply, or unrelated files changed.

- [ ] **Step 3: Write `FA-REPORT.md`**

Include what was built, the exact fixture counts, verbatim validator/harness outputs, diff summary, and an `EXACT NONCLAIMS` section stating no linguistic certification, no renderer/whitelist/live mutation, no deploy, no push, no full-corpus projection claim, and no unresolved-fact invention.

- [ ] **Step 4: Verify report and commit**

Run `rg` for the mandatory headings and `git diff --check`, then stage only the implementation/report paths and commit with a `fa:` prefix. Do not push.

- [ ] **Step 5: Re-run the final smoke after the commit**

Run the contract validator, focused tests, `python tools/check_regressions.py`, `git diff --check`, and status. Only claim completion if all fresh outputs support it; otherwise report the exact remaining gate.
