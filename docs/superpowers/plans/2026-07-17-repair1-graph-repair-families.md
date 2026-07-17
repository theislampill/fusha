# Repair1 Graph Repair Families Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the first reusable graph-repair families over the EDGES debt classification: guarded deterministic entry/form overlays, occurrence-appearance resolver closure, and bounded duplicate-surface crosswalk packets.

**Architecture:** Keep the EDGES typed graph and occurrence-appearance index as the source graph. A stdlib-only Repair1 builder consumes those artifacts plus explicit read-only corpora, emits a candidate-mode graph overlay and forward/reverse projections, and writes all large outputs lane-side. Deterministic edges are merged into the validator input; context-resolved duplicate rows remain candidate packets and never become `deterministic_exact`.

**Tech Stack:** Python 3 standard library, JSONL/pretty JSON, existing `qamus.graph_edge.v1` builder and ten-check validator, `unittest`.

## Global Constraints

- Read-only inputs remain `../../data/entries.jsonl`, `../../data/rh_live_01_beta_whitelist.jsonl`, and `../EDGES/full-artifacts/`.
- All repair output is candidate-mode except guarded exact form edges with status `deterministic_exact`; no live mutation, whitelist append, push, publication, or release.
- Orthography guards preserve hamza seats, `ة`/`ه`, and defective spellings; failed guards emit typed reclassification records and no edge.
- Duplicate context resolution emits status `candidate`, never `deterministic_exact`; unresolved rows route to `owner_or_scholar_required` with required evidence.
- Large JSONL stays lane-side; the repository receives only tools, committed fixture subsets, tests, and this plan.
- Fresh-clone validation uses committed fixtures/defaults and explicit CLI paths for external corpora; no lane path is a default.
- Every committed text artifact ends with a newline; no `*.png`; RM-09 needles are constructed by concatenation.

---

### Task 1: Establish Repair1 fixtures and test seams

**Files:**
- Create: `qamus/examples/repair1/deterministic-debt.fixture.jsonl`
- Create: `qamus/examples/repair1/source-key-resolver.fixture.jsonl`
- Create: `qamus/examples/repair1/duplicate-crosswalk.fixture.jsonl`
- Create: `tools/test_repair1_graph_families.py`

**Interfaces:**
- Tests consume the existing edge fixtures and the new compact Repair1 rows.
- Tests produce the required red-first evidence for guarded matching, resolver canonicalization, candidate-vs-deterministic status, divine-name policy, and exact unresolved routing.

- [ ] Write failing tests for a URL carrying a source-key alias, an orthography mismatch, a context candidate, and an unresolved duplicate.
- [ ] Run `python -m unittest tools.test_repair1_graph_families -v` and record the expected missing-implementation failures.
- [ ] Add the six source-key locations as a compact fixture subset and assert their typed ids are the rebuilt relationship target.

### Task 2: Implement guarded deterministic repair overlay

**Files:**
- Create: `tools/build_repair1_graph_families.py`
- Modify: `tools/test_repair1_graph_families.py`

**Interfaces:**
- `build_deterministic_repairs(debt_rows, entries, base_edges)` returns repair records, deterministic edges, typed reclassifications, and metrics.
- `merge_repair_edges(base_edges, repair_edges)` returns a stable edge stream without dropping base evidence.
- `project_repair_reverse(forward, edges, entries)` returns the Repair1 reverse projection.

- [ ] Implement `bare()`-based exact matching with an entry/form address, candidate collision check, and explicit hamza/ta-marbuta/defective mismatch reasons.
- [ ] Emit `form_entry_edge` and `lexeme_entry_edge` with full evidence, guards, producer id/version, and `deterministic_exact` status only for one guarded match.
- [ ] Emit typed reclassification records for every execution-time guard failure and keep failed rows out of the edge overlay.
- [ ] Merge the overlay and regenerate forward/reverse projections; measure new overlay edges, owner rows advanced, cards, entries, and forward/reverse trace counts.

### Task 3: Harden and prove occurrence-appearance source-key resolution

**Files:**
- Modify: `tools/build_occurrence_appearance_index.py`
- Modify: `tools/test_occurrence_appearance_index.py`

**Interfaces:**
- `resolve_entry_id(row, by_id, by_source)` canonicalizes direct ids, source-key aliases, and `e/<source-key>` URL paths through the same resolver.

- [ ] Run the source-key fixture against the pre-fix resolver from the EDGES parent and capture the red misresolution.
- [ ] Implement one canonical source-key resolver path, including `entry_url` values whose `e/` payload is an alias.
- [ ] Regenerate the affected index subset from the explicit entries/whitelist inputs and assert all six locations reciprocate to typed entry ids.

### Task 4: Implement bounded duplicate-surface crosswalk review

**Files:**
- Modify: `tools/build_repair1_graph_families.py`
- Modify: `tools/test_repair1_graph_families.py`

**Interfaces:**
- `build_duplicate_crosswalk_packets(rows, entries, whitelist, appearances)` returns one resolution record per input row.

- [ ] Build occurrence candidates only from the supplied card ayah, entry example refs, sense/form identity, and orthography-aware surface keys.
- [ ] Emit `resolved` packets with an evidence chain, proposed candidate edge set, collision set, and learner-projection path.
- [ ] Emit `still_ambiguous` packets with the full collision set, exact missing discriminator, and `owner_or_scholar_required` route.
- [ ] Keep divine-name rows root-silent and non-promotable even when context identifies a single occurrence.

### Task 5: Add Repair1 CLI, validator integration, report, and lane artifacts

**Files:**
- Modify: `tools/build_repair1_graph_families.py`
- Create: `REPAIR1-REPORT.md` (lane-side)
- Create: `artifacts/` outputs (lane-side, gitignored or outside the checkout)

**Interfaces:**
- CLI accepts every corpus and EDGES artifact by explicit argument and writes a lane-side output directory.
- The report includes task-by-task yield, before/after bidirectionality, all ten validator results, six resolver rows, three typed packet repairs, duplicate dispositions, and Compounding Impact metrics over all 16 channels.

- [ ] Run the full input builder with explicit paths and write JSONL outputs beside the lane.
- [ ] Run `validate_typed_edge_graph.py` over the enlarged deterministic graph and existing inputs; require all ten checks to pass.
- [ ] Run the complete repository harness, artifact ergonomics, `git diff --check`, and a fresh-clone-style fixture invocation.
- [ ] Read back report/metrics, stage explicit repo paths, and commit with a `repair1:` message; never push.
