# PROOF-N noun proof for سُفَهَاءُ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a candidate-only, compiler-generated end-to-end proof for `السُّفَهَاءُ` at `quran:2:13:12` that closes the actual entry/card/source/fact/projection/appearance/reverse chain.

**Architecture:** Add one proofn generator and one proofn validator. The generator calls the existing F-D shared compiler and FAM2 producer, materializes the EDGES repair path as typed graph records, and writes all deploy-shaped artifacts under one fixture directory. The validator recomputes the proof from the committed artifacts and runs the existing ten typed-edge checks plus proofn-specific acceptance checks.

**Tech Stack:** Python 3.11 stdlib, existing `tools.fd_compiler`, `tools.fam2_lexical_producer`, `tools.build_typed_edge_crosswalk`, JSON/JSONL, generated HTML, optional Playwright render witness.

## Global Constraints

- Use writable checkout `../../proofn-wt` on branch `andon-proof-noun`; no push.
- Read-only inputs are `../../data/entries.jsonl`, `../../data/rh_live_01_beta_whitelist.jsonl`, `../../canary-sufaha/sufaha-evidence.jsonl`, `../EDGES/EDGES-REPORT.md`, `../EDGES/edge-closure-summary.json`, and `../EDGES/full-artifacts/` from the lane root.
- Scripture facts come only from the supplied 11/11 certified evidence packet; no facts are invented.
- Candidate mode only; every generated projection and edge is `candidate` or `deterministic_exact` as justified, with `authorization_state=pre_apply_not_authorized` and all live mutation flags false.
- Whitelist `c59a0161fac8` remains page context; lexical entry `1ffcc554ec44` is selected from documented-form evidence and is the only lexeme edge target.
- The final `ُ` is a Naḥw case overlay, never plural-forming; governor `آمَنَ` and subject relation remain explicit.
- The جامد/مشتق MCP-internal tension remains unresolved and cannot contaminate certified facts.
- No `*.png` is tracked; a render screenshot may exist only as a local ignored file.
- Public learner fields are compiler-generated, N-LANG-clean, and contain no source quotation, evidence verbatim, internal route, or external-source name.

---

### Task 1: Add red-first proofn acceptance tests

**Files:**
- Create: `tools/test_proofn_noun_sufaha.py`
- Create: `qamus/examples/proof-noun-sufaha/fixture-input.json`

**Interfaces:**
- Consumes: the committed proofn generator/validator interfaces defined in Task 2.
- Produces: failing tests for identity split, 11/11 facts, exact spans, edge-chain closure, payload/view parity, all appearance parity, reverse trace, N-LANG, candidate boundary, tension retention, and PNG policy.

- [ ] **Step 1: Write the failing test module**

  Assert the requested constants and artifact paths, then call `build_proof()` and `validate_proof()`. Include red-first mutations that remove the lexical edge, replace the page-context target with the lexical entry, remove one appearance edge, alter the final case span, leak `MCP` into learner text, and change candidate authorization.

- [ ] **Step 2: Run the focused test and record the expected missing-interface failures**

  Run:

  ```text
  python -m unittest tools.test_proofn_noun_sufaha -v
  ```

  Expected: failure because `tools.proofn_noun_sufaha` and its proof validator do not yet exist.

- [ ] **Step 3: Commit the red test fixture**

  Run `git diff --check`, stage only the new test/fixture, and commit with `proofn: add red noun proof acceptance tests`.

### Task 2: Implement the canonical proofn generator

**Files:**
- Create: `tools/proofn_noun_sufaha.py`
- Modify: `tools/fd_compiler.py` only where a shared helper is required for exact public labels or the proof bundle.

**Interfaces:**
- Consumes: `build_sufaha_contract`, `build_sufaha_payload`, FAM2 `produce_record`, `make_edge`, the named read-only inputs, and the occurrence-appearance index.
- Produces: `load_inputs() -> dict`, `build_proof(inputs) -> dict`, `write_artifacts(proof, output_dir) -> dict[str, Path]`, `render_proof_html(payload) -> str`, and CLI `python tools/proofn_noun_sufaha.py --output-dir ...`.

- [ ] **Step 1: Implement input resolution and read-only guards**

  Require explicit paths for all external inputs; resolve the lexical entry by exact documented `usage[0].forms[1] == سُفَهَاء`, retain whitelist entry `c59a0161fac8` as page context, select whitelist location `2:13:12`, load exactly facts `1..11` with every status `certified`, and load the two appearance records for `2:13:12` from `qamus/indexes/occurrence-appearances.jsonl`.

- [ ] **Step 2: Run the FAM2 producer and shared F-D compiler**

  Pass the real occurrence and lexical entry to `tools.fam2_lexical_producer.produce_record`; preserve its candidate formation fact. Build the 11-fact F-D contract from the supplied evidence, call `build_sufaha_payload`, and derive compact, expanded Ṣarf, expanded Naḥw, rich-hover, at-rest, and readback-target descriptors from the typed contract/payload rather than hand-authored HTML fields.

- [ ] **Step 3: Materialize the complete typed graph**

  Emit the page-context edge to `entry:c59a0161fac8` separately from the candidate form/lexeme edge to `entry:1ffcc554ec44`. Emit candidate source-card, selected-example, form, lexeme, root, projection-input, and certified-fact-attachment edges; deterministic exact canonical/display crosswalk, sense, and reverse edges; candidate rendered-appearance edges for every appearance index; and candidate rich-projection/hover/readback descriptors with exact artifact addresses.

- [ ] **Step 4: Generate the proof HTML from one payload**

  Use the shared compiler’s HTML path or a shared helper that embeds one normalized JSON payload. Render compact and expanded views from that payload, include the exact public Ṣarf/Naḥw labels, visible brackets/badges, exact reconstruction hook, `document.fonts.check`, and a declared-not-measured public readback target. Copy the existing Kawkab Mono asset; never create or stage a PNG.

- [ ] **Step 5: Write deterministic artifacts**

  Write pretty JSON, JSONL, and Markdown artifacts under `qamus/examples/proof-noun-sufaha/`: contract, typed edges, payload, compact/expanded projections, hover structure, appearance parity, FAM2 candidate fact, parity fixture, render witness placeholder/updated witness, graph-validator report, and `PROOFN-MANIFEST.json`/`PROOFN-REPORT.md` at repo root.

### Task 3: Implement proofn validation and harness wiring

**Files:**
- Create: `tools/validate_proofn_noun_sufaha.py`
- Modify: `tools/check_regressions.py`

**Interfaces:**
- Consumes: committed proofn artifacts and the existing typed-edge validator.
- Produces: `validate_proofn_artifacts(...) -> list[str]`, `--self-test`, and a harness line containing `PROOFN NOUN PROOF PASS`.

- [ ] **Step 1: Validate the ten existing typed-graph checks**

  Load the proofn graph and self-contained fixture inputs, invoke all ten named checks, and require every check name to be present and `ok=true`.

- [ ] **Step 2: Validate proofn-specific chain closure**

  Require actual identity split, entry sense/card/example addresses, 11/11 evidence backlinks, exact lexical/form/root edges, `سَفِيه`/`سُفَهَاء`, both patterns, radicals, removed/introduction facts, lexical-body/case separation, `آمَنَ` subject relation, shared compiler lineage, at-rest/compact/expanded/hover parity, every appearance edge, reverse entry/card/source links, declared-not-measured readback, candidate boundary, N-LANG, unresolved tension, and no tracked PNG.

- [ ] **Step 3: Add the fixture-only harness gate**

  Invoke `python tools/validate_proofn_noun_sufaha.py --self-test` from `tools/check_regressions.py` without reading external inputs. Keep the gate bounded to committed proofn artifacts.

- [ ] **Step 4: Run the focused red/green cycle**

  Run `python -m unittest tools.test_proofn_noun_sufaha -v` and `python tools/validate_proofn_noun_sufaha.py --self-test`; expected result after implementation is all proofn tests and validator checks passing.

### Task 4: Generate and render the deploy-shaped proof packet

**Files:**
- Create/modify: `qamus/examples/proof-noun-sufaha/*`
- Create/modify: `PROOFN-MANIFEST.json`
- Create/modify: `PROOFN-REPORT.md`
- Create: `tools/render_proofn_sufaha.js`

**Interfaces:**
- Consumes: the generator and committed Kawkab asset.
- Produces: checked-in proof artifacts and `render-proof.json`; any `proofn-card.png` remains ignored/local-only.

- [ ] **Step 1: Run the generator with explicit repository-relative input paths**

  Run the generator from the repo root with the five named input arguments and `--output-dir qamus/examples/proof-noun-sufaha`. Verify read-only input mtimes and hashes are unchanged.

- [ ] **Step 2: Run the local render proof when Playwright is available**

  Run `node tools/render_proofn_sufaha.js`; require font readiness, exact reconstruction, compact/expanded presence, same normalized payload identity, all appearance parity, and `live_mutation_allowed=false`. Write only `render-proof.json` durably.

- [ ] **Step 3: Rebuild the manifest and report from artifact addresses**

  Ensure the report walks entry → sense → card → selected word → source/card evidence → display-local/canonical crosswalk → occurrence → typed facts → compiler → projections → hover → appearances → readback declaration → reverse trace, with each link pointing to a file and JSON/JSONL selector.

### Task 5: Full verification and handoff

**Files:**
- Modify only generated proofn artifacts and reports if verification finds deterministic drift.

- [ ] **Step 1: Run all focused validators and neighboring gates**

  ```text
  python -m unittest tools.test_proofn_noun_sufaha tools.test_fd_compiler tools.test_typed_edge_graph tools.test_fam2_lexical_producer -v
  python tools/validate_proofn_noun_sufaha.py --self-test
  python tools/validate_fd_compiler.py --self-test
  python tools/validate_typed_edge_graph.py --self-test
  python tools/validate_fam2_lexical.py --self-test
  ```

- [ ] **Step 2: Run repository artifact and regression checks**

  ```text
  python tools/check_artifact_ergonomics.py
  python tools/classify_artifacts.py
  python tools/check_regressions.py
  git diff --check
  ```

- [ ] **Step 3: Inspect the final diff and forbidden files**

  Run `git status --short --branch --untracked-files=all`, `git diff --stat`, `git diff --name-only --diff-filter=ACM`, and `rg --files -g '*.png'`. Confirm no read-only input path, secret, private path, external gloss, or PNG is staged.

- [ ] **Step 4: Commit only after fresh verification**

  Stage explicit proofn source, tests, harness, artifacts, manifest, and report paths; verify `git diff --cached --check` and the staged file list; commit `proofn: close real noun proof for sufaha`; do not push.
