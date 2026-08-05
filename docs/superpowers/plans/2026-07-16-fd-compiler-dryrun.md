# F-D Compiler Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the F-A typed-claim contract with evidence modes and build a shared F-D compiler that generates the Ṣufahāʾ proof surfaces and the 455-row candidate dry-run with truthful gates.

**Architecture:** Keep the existing F-A and tranche-1 contracts backward-compatible where possible. Add a strict evidence/provenance extension, a registered stdlib-only `tools/fd_compiler.py`, F-D fixture schemas and validators, and generated artifacts under `qamus/examples/fd/` plus the two required root reports. The compiler owns all projection fields; the HTML reads one embedded normalized payload for both views.

**Tech Stack:** Python 3 stdlib, JSON Schema checked by the repository’s `fact_ledger`, unittest, JSONL, generated HTML/CSS/JS, optional local Playwright.

## Global constraints

- Work only in the specified isolated worktree; never push.
- Prefix commits with `fd:`.
- Read-only corpus inputs; never modify `data/` or live/runtime files.
- No public source quotations or external-source prose in the learner payload.
- Preserve `live_mutation_allowed=false` everywhere.
- Do not invent missing morphology, naḥw, entry, or learner-language claims.
- Use `apply_patch` for authored text/source and generated compiler output for generated artifacts.

## Tasks

### 1. Record design and establish the red baseline

- [x] Write the pre-approved design/spec and commit it as `fd: record compiler dry-run design`.
- [ ] Add F-D tests before production implementation. Cover schema-required evidence fields, enum closure, source quotation/structured fact exclusivity, derivation requirements, dependency references, unresolved tension isolation, the Ṣufahāʾ fixture modes, spans, entry reciprocity, same-payload HTML views, and the exact twelve report keys.
- [ ] Run the new focused tests and capture the expected red failure before implementation.

### 2. Extend the typed-claim contract

- [ ] Extend `qamus/schemas/typed-claim-contract.schema.json` with the evidence-mode enum, source evidence, derivation, dependencies, contradiction records, and top-level tension records.
- [ ] Extend `tools/typed_claim_contract.py` with semantic checks for source evidence exclusivity, evidence-mode derivation rules, dependency/tension references, and unresolved-status honesty.
- [ ] Update the F-A valid fixture with the additive fields and add evidence-extension fixtures (valid certified, valid unresolved tension, invalid mode, invalid derived chain, invalid unknown dependency).
- [ ] Keep the original F-A self-test and fixtures passing.

### 3. Implement the shared compiler and Ṣufahāʾ contract

- [ ] Add `tools/fd_compiler.py` with stable functions for evidence conversion, contract validation, at-rest span assignment, public payload generation, HTML generation, family search, entry reciprocity, and 455-row candidate compilation.
- [ ] Add the F-D projector registration and F-D JSON schemas.
- [ ] Generate `qamus/examples/fd/sufaha-contract.json`, the normalized public payload, parity fixture, and a README explaining the fixture-only boundary.
- [ ] Verify owner-mandated evidence modes and that the jām id/mushtaq tension is not a certified claim binding.

### 4. Generate the HTML proof

- [ ] Generate the compact/expanded Ṣufahāʾ HTML from the normalized payload, including all 22 owner witnesses, accessible non-colour equivalents, visible provenance/projector footer, exact reconstruction witness, and visible unresolved tension.
- [ ] Copy the supplied local Kawkab Mono Qamus woff2 into the F-D proof asset directory and inject a visible `document.fonts.check` assertion using the prior-board protocol.
- [ ] Run `npx playwright --version`; render through the local browser when available, otherwise emit `RENDER-INSTRUCTIONS.md` and report the absence without a fake screenshot.

### 5. Run the 455-row candidate dry-run

- [ ] Load only v575 rows with verdict `verified`, join against the read-only whitelist and entries corpus, and compile every row without certifying or mutating it.
- [ ] Emit root `fd-455-verdicts.jsonl` and `fd-455-report.json` with exactly the twelve metrics, per-row flags, and primary blockers.
- [ ] Assert the report’s totals and matrix are reproducible from the source snapshots and that repeated page coverage is not inferred.

### 6. Wire gates and report

- [ ] Add `tools/validate_fd_compiler.py` and `tools/test_fd_compiler.py`; make the validator check the checked-in generated artifacts and the red/green invariants.
- [ ] Add the F-D gate to `tools/check_regressions.py` without broadening it into live or corpus mutation.
- [ ] Write root `docs/reports/history/2026-07-16-FD-REPORT.md` with the built artifacts, the 22-point checklist and witnesses, exact 12-metric table, verbatim harness output, and exact nonclaims.

### 7. Verify and commit

- [ ] Run focused unit tests, F-A tests, F-D fixture validation, the full regression harness, render verification if available, and `git diff --check`.
- [ ] Re-read generated artifacts and `git status --short`; confirm only F-D files plus the intentional registry/harness/schema changes are present.
- [ ] Commit implementation/generated artifacts with `fd:` prefixes. Do not push.

## Done when

The F-D contract extension validates its fixtures; the compiler generates a single-payload Ṣufahāʾ card and honest 455-row dry-run; all requested reports/docs exist; the full harness prints `ALL REGRESSION CHECKS PASS`; the render is either freshly verified by Playwright or explicitly handed off with render instructions; and no live/read-only corpus state was mutated.
