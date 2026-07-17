# EDGES lane implementation plan

## Goal

Add a canonical typed-edge graph beside the existing VNMAP ledger and
occurrence-appearance index, build a bidirectional lexeme-to-entry crosswalk,
reclassify only graph-plumbing false `source_gap` rows, classify the complete
crosswalk debt set, and close the result with fixture-only regression proof
plus lane-side full-input measurement.

## Constraints and done-when

- Work only on the existing `andon-lexeme-crosswalk` checkout.
- Treat whitelist `entry_id` as page context; never use it for a lexeme edge.
- Do not rewrite producer packet history, push, publish, or mutate read-only
  inputs.
- Use the existing occurrence-appearance index; do not create a second
  occurrence graph.
- Keep tracked fixtures and tools self-contained and free of production paths,
  identifiers, secrets, and image files.
- Done when the named validators pass in the full repository harness, the
  explicit full-input run emits the report and lane-side artifacts, the debt
  total is exactly 6,677, all nine reciprocity failures have an evidence-backed
  diagnosis, and a local `edges:` commit exists.

## Work sequence

### 1. Contract and fixtures

Files:

- `docs/superpowers/specs/2026-07-17-typed-edge-lexeme-crosswalk-design.md`
- `qamus/examples/edges/*.jsonl`
- `tools/test_typed_edge_graph.py`

Create the smallest fixture that contains a page-context edge, an exact
lexeme/form/sense chain, a root-only candidate, a duplicate surface, a
repeated appearance, a display-local correction, and an orphaned fact. Add
red-first tests for each named validator, especially the page-context-to-
lexeme promotion rejection. Run only the new test module and record the red
failures before writing implementation code.

### 2. Typed edge and crosswalk core

Files:

- `tools/build_typed_edge_crosswalk.py`
- `tools/test_typed_edge_graph.py`

Implement schema validation, typed node IDs, stable edge IDs, orthography
guards, candidate collection, fail-closed status assignment, page-context
materialization, forward/reverse projection generation, and exact
reconstruction. Use the ledger and appearance index as inputs, preserving
their source fields. Add focused tests and run them green.

### 3. Validators and lane analyses

Files:

- `tools/validate_typed_edge_graph.py`
- `tools/test_typed_edge_graph.py`

Implement the ten named checks, reclassification delta generation, debt
family classifier, duplicate ambiguity split, and nine-row reciprocity report.
Every output is deterministic JSON/JSONL. Add fixture assertions for each
failure and its repaired counterpart, then run the focused suite.

### 4. Harness and full-input run

Files:

- `tools/check_regressions.py`
- `tools/validate_typed_edge_graph.py` (self-test entry point if needed)

Wire a fixture-only typed-edge gate into the regression harness. Run the
validator self-test, committed fixture validation, existing VNMAP and
appearance checks, and then the full harness. Separately run the builder with
explicit corpus and producer arguments, predicate-v3 boundary input for any
clitic analysis, and a lane-side output directory. Do not copy large generated
JSONL outputs into the repo.

### 5. Audit and handoff

Files:

- lane-side `EDGES-REPORT.md`
- lane-side edge/crosswalk/reclassification/debt artifacts
- `PAUSED-STATE.md` only if execution is interrupted by the usage limit

Read back the report and metrics, verify all required totals and sections,
run `git diff --check`, inspect the final diff against the base, and rerun the
full harness after the final edit. Commit only the intended files with an
`edges:` message. No push.

## Verification commands

Focused red/green loop:

```text
python -m unittest tools.test_typed_edge_graph -v
python tools/validate_typed_edge_graph.py --self-test
```

Repository gate:

```text
python tools/check_regressions.py
git diff --check
git status --short --branch --untracked-files=all
```

The explicit full-input command is recorded in the lane report with its
argument values redacted to repository-relative placeholders where necessary.
