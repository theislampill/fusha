# VN Readiness v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a deterministic candidate-only VN-00→VN-23 readiness matrix and full selected-word ledger that preserves VNREC authority, staging separation, both planning namespaces, EDGES crosswalk yield, and the three named proof rows.

**Architecture:** Add a standalone builder that reuses the existing canonical entry/card/word ledger for D1-D4 joins, then joins explicit VNREC, EDGES, FAMWIDE, baseline, and proof inputs. Add a focused v2 validator and fixture test suite, and register those checks in the repository regression harness. Generate full lane outputs only after the repo-self-contained fixture gate passes.

**Tech Stack:** Python 3 stdlib, JSON/JSONL, `unittest`, existing repo ledger and appearance-index helpers, PowerShell for explicit Windows CLI invocation.

## Global Constraints

- Preserve documented VN-00 `v001–v047+n0001–n0045`, VN-01 `v048–v094+n0046–n0090`, and VN-02 `v095–v141+n0091–n0135`; all are recorded `CLOSED-FROZEN` and are never live-reverified.
- Preserve the 1,302-key staging namespace as `vn00_staging_member` and `VN-00-STAGING`; never merge staging-only keys into the documented VN-00 window.
- Keep 164 historical-conflict scalars null with every historical claim retained.
- Populate provisional strings only for keys without historical claims, as `proposed:<proposal_id>:<label>`, with partition and plan-table proposals side-by-side.
- Use only EDGES `deterministic_exact` and `candidate` as usable crosswalk statuses; ambiguous rows remain incomplete.
- Report source-certified rows as zero and count only `sufaha 2:13:12`, `fattabini 19:43:10`, and `ma 2:284:10` as candidate deploy-shaped fully-rich proof rows.
- Use explicit CLI input paths; no lane path, network, live mutation, commit push, PNG, or input rewrite may be present in repo code.
- Pretty JSON and newline-terminated JSONL are required; `git diff --check` and the full harness must pass before completion claims.

---

### Task 1: Create the red fixture contract and failing v2 tests

**Files:**
- Create: `qamus/examples/vnmap-v2/entries.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/whitelist.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/occurrence-appearances.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/famwide-strat.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/membership.fixture.json`
- Create: `qamus/examples/vnmap-v2/conflicts.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/edge-summary.fixture.json`
- Create: `qamus/examples/vnmap-v2/crosswalk-forward.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/debt-classification.fixture.jsonl`
- Create: `qamus/examples/vnmap-v2/baseline-matrix.fixture.json`
- Create: `qamus/examples/vnmap-v2/proofs.fixture.json`
- Create: `tools/test_vn_readiness_v2.py`

**Interfaces:**
- Fixtures provide four entries: one documented VN-00 key, one dual-claim VN-01/staging key, one partition-only future key, and one unplanned particle. Their crosswalk rows include one `deterministic_exact`, one `candidate`, and one `ambiguous` status. The debt fixture includes one source/scholar, one divine-name, one proper-noun, and one deterministic source/crosswalk row.
- `tools.test_vn_readiness_v2` imports `build_v2` from the not-yet-created builder and asserts the desired public shape.

- [ ] **Step 1: Write the failing test**

```python
def test_owner_schema_keeps_conflict_null_and_staging_separate(self):
    result = build_v2(*self.inputs)
    conflict = next(row for row in result.ledger if row["source_key"] == "v002")
    self.assertIsNone(conflict["vn_tranche"])
    self.assertEqual(conflict["vn_tranche_status"], "historical_conflict")
    self.assertEqual(conflict["vn_tranche_claims"], ["VN-00", "VN-01"])
    self.assertTrue(conflict["vn00_staging_member"])
    self.assertEqual(result.matrix["views"]["authoritative_partition"]["tranches"][1]["historical_conflict_entries"], 1)

def test_both_proposal_namespaces_and_graph_status_split_are_explicit(self):
    result = build_v2(*self.inputs)
    proposed = next(row for row in result.ledger if row["source_key"] == "v003")
    self.assertEqual(proposed["vn_tranche"], "proposed:vn-partition-proposal.v1:VN-02")
    self.assertEqual(proposed["vn_tranche_plan_table_proposal"], "proposed:vn-plan-table.v1:VN-03")
    row = result.matrix["views"]["authoritative_partition"]["tranches"][2]
    self.assertEqual(row["graph_complete_deterministic_exact_rows"], 1)
    self.assertEqual(row["graph_complete_candidate_rows"], 1)
```

- [ ] **Step 2: Run the focused test to verify the expected missing-builder failure**

Run: `python -m unittest tools.test_vn_readiness_v2 -v`

Expected: FAIL with an import error for `tools.build_vn_readiness_v2`.

- [ ] **Step 3: Commit fixture and red test**

```text
git add qamus/examples/vnmap-v2 tools/test_vn_readiness_v2.py
git commit -m "vnregen: add v2 fixture contract and red tests"
```

### Task 2: Implement the deterministic v2 builder

**Files:**
- Create: `tools/build_vn_readiness_v2.py`

**Interfaces:**
- `build_v2(entries, whitelist, appearances, family_rows, membership, conflicts, edge_summary, crosswalk_rows, debt_rows, baseline_matrix, proof_rows) -> BuildResultV2`.
- CLI requires `--entries`, `--whitelist`, `--appearance-index`, `--family`, `--membership`, `--conflicts`, `--edge-summary`, `--crosswalk-forward`, `--debt-classification`, `--baseline-matrix`, `--proofs`, `--matrix-output`, `--ledger-output`, and `--report-output`.
- The builder writes only the three output arguments and serializes JSON with `indent=2`, `sort_keys=True`, `ensure_ascii=False`, and a final newline; JSONL uses one sorted-key object per line plus a final newline.

- [ ] **Step 1: Implement input readers, canonical source-key normalization, and proposal maps**

Implement these exact helpers: `_read_json`, `_read_jsonl`, `_write_json`, `_write_jsonl`, `_canonical_source_key`, `_historical_claims`, `_partition_map`, `_plan_table_map`, and `_proposal_string`. Normalize `n773` and `n0773` to `n0773`; do not use lenient Arabic normalization for VN identity.

- [ ] **Step 2: Implement the VNREC scalar assignment contract**

For each ledger row, emit:

```python
{
    "vn_tranche": historical_label_or_partition_proposal_or_none,
    "vn_tranche_status": "authoritative" | "historical_conflict" | "proposed" | "unassigned",
    "vn_tranche_claims": sorted_historical_labels,
    "vn_tranche_evidence": evidence_strings,
    "evidence": evidence_strings,
    "vn00_staging_member": source_key in staging_set,
    "vn_tranche_partition_proposal": proposed_partition_or_none,
    "vn_tranche_plan_table_proposal": proposed_plan_or_none,
    "vn_matrix_view_authoritative_partition": documented_label_or_staging_or_partition_label,
    "vn_matrix_view_plan_table": documented_label_or_staging_or_plan_label_or_unplanned_particle,
}
```

Historical conflicts never receive either proposal string. A staging-only historical `VN-00` claim uses `VN-00-STAGING` in the matrix view while retaining scalar `VN-00` and `vn00_staging_member=true`.

- [ ] **Step 3: Reuse the existing D1-D4 ledger and join EDGES statuses/debt**

Call the existing `build_ledger` with explicit input lists. Reconstruct each EDGES selected-word ID with the same stable coordinates used by `tools.build_typed_edge_crosswalk`; join the forward crosswalk status and debt family by ID. Count only `deterministic_exact` and `candidate` as graph-complete. Use the existing ledger occurrence IDs and exact entry usage/example coordinates for card and occurrence denominators.

- [ ] **Step 4: Build both matrix views and deltas**

Emit rows for VN-00 through VN-20 in both views, VN-21 through VN-23 in the plan-table view (and explicit zero rows in the other view), plus `VN-00-STAGING`, `HISTORICAL_CONFLICT`, and `UNPLANNED_PARTICLES` sidecars. Each tranche row contains the requested yield units, `graph_complete_rows`, deterministic/candidate split, `source_certified_rows=0`, named proof rows, recorded frozen no-op scope, the debt-family breakdown, and a deterministic `next_action`.

Calculate the material delta on the stable v1 partition identity: baseline complete rows are `displayed_selected_words - graph_crosswalk_gap_rows`; after rows use EDGES usable statuses. Also report cards with all selected-word rows usable and entries with any usable edge before/after, clearly separating the three proof rows from the 7,740-row corpus denominator.

- [ ] **Step 5: Render the report with evidence and Compounding Impact**

The report must name `VNREC/VNREC-REPORT.md`, `VNREC/vnrec-authoritative-membership.json`, `VNREC/vnrec-conflicts.jsonl`, `EDGES/edge-closure-summary.json`, `EDGES/full-artifacts/lexeme-entry-crosswalk.forward.jsonl`, `EDGES/full-artifacts/debt-classification.jsonl`, `FAMWIDE/famwide-strat.jsonl`, the v1 baseline, and the three proof artifacts. State that CLOSED-FROZEN is recorded evidence and was not live-reverified; state that proofs are candidate deploy-shaped only.

- [ ] **Step 6: Run the focused test to verify green**

Run: `python -m unittest tools.test_vn_readiness_v2 -v`

Expected: all fixture behavior tests pass.

- [ ] **Step 7: Commit the builder**

```text
git add tools/build_vn_readiness_v2.py
git commit -m "vnregen: build v2 readiness matrix and ledger"
```

### Task 3: Add the validator and fixture outputs

**Files:**
- Create: `tools/validate_vn_readiness_v2.py`
- Create: `qamus/examples/vnmap-v2/vn-readiness-v2.fixture.json`
- Create: `qamus/examples/vnmap-v2/vn-ledger-v2.fixture.jsonl`

**Interfaces:**
- `validate_artifacts(ledger, matrix) -> ValidationReport`.
- CLI accepts `--ledger`, `--matrix`, or `--self-test`.

- [ ] **Step 1: Add validator assertions**

Validate schema version, candidate-only state, row identity uniqueness, status enum, proposal-string grammar, scalar/conflict rules, staging separation, exact D1-D4 totals, 21 primary rows plus plan rows, graph status conservation, zero source certification, exactly three named proof rows, debt family conservation, newline/pretty-output ergonomics, and no forbidden `blocker` field.

- [ ] **Step 2: Add red-first mutations to `--self-test`**

Start from fixture outputs, then mutate one conflict scalar to `VN-01`, remove one claim, fold one staging row into `VN-00`, change one proposal prefix, mark an ambiguous row usable, and remove one proof name. Each mutation must be rejected for its intended reason.

- [ ] **Step 3: Generate fixture outputs and run validator**

Run the builder against `qamus/examples/vnmap-v2/*fixture*` inputs, then run:

```text
python tools/validate_vn_readiness_v2.py --self-test
python tools/validate_vn_readiness_v2.py --ledger qamus/examples/vnmap-v2/vn-ledger-v2.fixture.jsonl --matrix qamus/examples/vnmap-v2/vn-readiness-v2.fixture.json
```

Expected: `VN READINESS V2 SELF-TEST PASS` and `VN READINESS V2 VALIDATION PASS`.

- [ ] **Step 4: Commit validator and fixture outputs**

```text
git add tools/validate_vn_readiness_v2.py qamus/examples/vnmap-v2/vn-readiness-v2.fixture.json qamus/examples/vnmap-v2/vn-ledger-v2.fixture.jsonl
git commit -m "vnregen: validate v2 readiness artifacts"
```

### Task 4: Add unit coverage and the full harness gate

**Files:**
- Modify: `tools/test_vn_readiness_v2.py`
- Modify: `tools/check_regressions.py` near the existing VNMAP gate

- [ ] **Step 1: Add tests for fixture regeneration, deterministic ordering, and report ergonomics**

Assert two builder runs serialize byte-identical outputs, every JSONL row ends in the expected schema, the report ends with a newline and contains `Compounding Impact`, and no input file changes after a run.

- [ ] **Step 2: Add harness invocations**

Run the v2 focused unittest module, validator self-test, and validator against the committed v2 fixture outputs from `tools/check_regressions.py`, each with a named `check(...)` and a fail-closed return-code/output assertion.

- [ ] **Step 3: Run the focused harness subset**

Run: `python tools/check_regressions.py`

Expected: all existing checks plus the three named VN readiness v2 checks pass and the final line is `ALL REGRESSION CHECKS PASS`.

- [ ] **Step 4: Commit harness integration**

```text
git add tools/test_vn_readiness_v2.py tools/check_regressions.py
git commit -m "vnregen: gate v2 readiness in the harness"
```

### Task 5: Generate full lane outputs and close verification

**Files:**
- Create outside the repo: `<lane-output-dir>/VNREGEN-REPORT.md`
- Create outside the repo: `<lane-output-dir>/vn-readiness-v2.json`
- Create outside the repo: `<lane-output-dir>/vn-ledger-v2.jsonl`

- [ ] **Step 1: Run the explicit full-corpus builder**

Use the supplied read-only inputs and the repository appearance index/proof fixture. Write only to the lane output paths. Verify the generated totals are D1=2,092, D2=7,700, D3=7,740, D4 unique=34,323, D4 appearances=56,117, and the EDGES usable split is deterministic_exact=7,017 and candidate=0 for the full forward crosswalk, with three proof rows separately named.

- [ ] **Step 2: Validate the full lane outputs**

Run the v2 validator on the generated lane artifacts, `git diff --check`, and a read-only Python schema/count audit that confirms 164 historical-conflict rows have `vn_tranche=null` and claims preserved, staging-only view rows are separate, and all report citations/limits are present.

- [ ] **Step 3: Run the complete repo harness and artifact gates**

Run:

```text
python tools/check_regressions.py
python tools/check_artifact_ergonomics.py
python tools/classify_artifacts.py
git diff --check
git status --short --branch
```

Expected: full harness `ALL REGRESSION CHECKS PASS`, artifact ergonomics pass, no tracked PNG, and only intended repo changes plus the lane output files outside the repo.

- [ ] **Step 4: Commit final repo changes**

```text
git add tools/build_vn_readiness_v2.py tools/validate_vn_readiness_v2.py tools/test_vn_readiness_v2.py tools/check_regressions.py qamus/examples/vnmap-v2
git commit -m "vnregen: close readiness matrix regeneration"
```

- [ ] **Step 5: Re-read final state and hand off**

Confirm branch `andon-vn-regen`, no push performed, the final commit messages all start with `vnregen:`, lane outputs exist, and the final response separates implemented, owner-gated, artifact-gated, partial, and deferred facts.
