# VNMAP Entry-Card Word Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the candidate-mode VNMAP NorthStar ledger, readiness matrix, graph metrics, report, and repo-only validation gate from the existing entry, whitelist, clitic-family, and occurrence/appearance contracts.

**Architecture:** A single stdlib builder walks entry `usage` objects, counts nested example cards and form rows, conservatively joins each form to whitelist evidence, and joins canonical locations to the existing occurrence/appearance JSONL. It emits the ledger plus deterministic metrics, proposal-tranche matrix, and report; a validator checks those artifacts without needing external inputs. A small fixture subset exercises all joins in the regression harness.

**Tech Stack:** Python 3 standard library, JSONL, pretty JSON, `unittest`, existing `tools/check_regressions.py`, and existing `tools/build_occurrence_appearance_index.py` / `tools/validate_appearance_parity.py` outputs.

## Global Constraints

- Use only the requested `vnmap-wt` checkout on branch `andon-vn-ledger`; do not push.
- Commit messages use the `vnmap:` prefix.
- Keep entries, whitelist, FAMWIDE strategy, and occurrence/appearance inputs read-only.
- The rollout unit is entry → sense → example card → selected word → address → canonical occurrence; whitelist rows are evidence, not rollout units.
- Do not create a second occurrence graph or ontology; join the existing occurrence/appearance output.
- Use only the exact owner missing-edge enum; never emit a generic blocker.
- Keep every ledger row and artifact in candidate mode; source-certified counts are zero pending owner certification.
- Do not persist production URLs, private paths, secrets, or images; no `*.png` files.
- Use `vn_tranche: null` unless a repository data file proves an authoritative per-entry assignment.
- Full-input output is reproducible with explicit CLI paths; committed fixtures keep the harness repo-self-contained.

---

### Task 1: Red-first fixture contracts

**Files:**
- Create: `tools/test_entry_card_word_ledger.py`
- Create: `qamus/examples/vnmap/entries.fixture.jsonl`
- Create: `qamus/examples/vnmap/whitelist.fixture.jsonl`
- Create: `qamus/examples/vnmap/occurrence-appearances.fixture.jsonl`
- Create: `qamus/examples/vnmap/famwide-strat.fixture.jsonl`

**Interfaces:**
- Tests import `build_entry_card_word_ledger.build_ledger` and the validator after implementation.
- Fixtures contain two entries, two example cards, two selected forms, one exact join, one strict unique join, one missing join, one repeated appearance, and one verified clitic-family row.

- [ ] **Step 1: Write failing tests**

```python
def test_build_ledger_preserves_four_denominators_and_exact_missing_edges():
    result = build_ledger(entries, whitelist, appearances, family)
    assert result.metrics["denominators"]["D1_entries"] == 2
    assert result.metrics["denominators"]["D2_listed_quran_example_cards"] == 2
    assert result.metrics["denominators"]["D3_displayed_selected_word_rows"] == 2
    assert result.metrics["denominators"]["D4_unique_canonical_occurrences"] == 2
    assert any("missing_selected_word_edge" in row["missing_edges"] for row in result.ledger)
    assert all("blocker" not in row for row in result.ledger)

def test_build_ledger_reciprocity_and_fixture_validator_contract():
    result = build_ledger(entries, whitelist, appearances, family)
    assert result.metrics["edge_join_rows_total"] == 2
    assert result.metrics["entry_occurrence_reciprocity_failures"] == 0
    assert validate_artifacts(result.ledger, result.metrics, result.matrix).ok
```

- [ ] **Step 2: Run the focused test and verify the expected missing-module failure**

Run: `python -m unittest tools.test_entry_card_word_ledger -v`

Expected: FAIL because `tools.build_entry_card_word_ledger` has not been written.

- [ ] **Step 3: Add only the fixture input rows**

Use relative fixture records with canonical locations, quran/wbw locators,
entry/source-key identity, one `appearances` record with an extra entry
appearance, and no private or production URL values.

- [ ] **Step 4: Re-run the focused test and confirm it still fails for the missing builder**

Run: `python -m unittest tools.test_entry_card_word_ledger -v`

Expected: FAIL at the import/implementation boundary, not because the fixture JSONL is malformed.

### Task 2: Deterministic builder and owner-edge ledger

**Files:**
- Create: `tools/build_entry_card_word_ledger.py`
- Modify: `tools/test_entry_card_word_ledger.py`

**Interfaces:**
- `build_ledger(entries, whitelist, appearance_records, family_rows) -> BuildResult`.
- `BuildResult.ledger`, `.metrics`, `.matrix`, and `.report` are deterministic Python values.
- CLI requires `--entries`, `--whitelist`, `--appearance-index`, `--family`, `--ledger-output`, `--metrics-output`, `--matrix-output`, and `--report-output`.

- [ ] **Step 1: Implement JSONL readers and strict deterministic helpers**

Preserve source order for usage/sense traversal, sort output rows by source
key, sense index, example index, and form index, use NFC plus the repository
strict surface normalization only for unique matching, and serialize JSON with
UTF-8, sorted keys, and trailing newlines. Do not add implicit external paths.

- [ ] **Step 2: Implement D1-D3 traversal**

Count entries by `section`/source-key space, count each non-empty
`usage.examples[]` as D2, and emit one D3 row per `usage.forms[]` value. Keep
usage index, example index, sense, ref, source example text, and form surface
even when downstream joins are missing.

- [ ] **Step 3: Implement conservative whitelist and occurrence joins**

Index whitelist rows by source key, entry ID, ayah ref, and canonical `loc`.
Prefer exact form/surface matches, accept a strict normalized match only when
unique, mark ambiguity with `duplicate_surface_edge_ambiguous`, and attach
quran/wbw locators, display-local address, quality-state source/value,
occurrence ID, appearance count, and reverse entry relationships from the
existing index.

- [ ] **Step 4: Implement exact missing-edge assignment**

Add only the owner enum values for absent entry URL, source photo, source card,
displayed fragment, selected word, quran/wbw address, display-to-canonical
crosswalk, decision backlink, rendered span/readback, and occurrence/appearance
edges. Count source-photo absence from the entry schema, and count pre-deploy
render/readback as unmeasured exact edges. Never add `blocker` or a free-form
replacement.

- [ ] **Step 5: Run the focused test and verify green**

Run: `python -m unittest tools.test_entry_card_word_ledger -v`

Expected: all builder fixture tests PASS.

### Task 3: Proposal VN matrix and clitic NorthStar mapping

**Files:**
- Modify: `tools/build_entry_card_word_ledger.py`
- Modify: `tools/test_entry_card_word_ledger.py`

**Interfaces:**
- `proposal_tranche_map(entries) -> dict[entry_id, str]` is internal and never populates `vn_tranche`.
- Matrix rows expose `proposal_vn_tranche`, D1-D4 counts, quality counts, clitic candidate counts, certification/unresolved/gap counts, affected appearances, and projected coverage gains.

- [ ] **Step 1: Add a test proving absent authoritative mapping stays null**

Assert every fixture ledger row has `vn_tranche is None`, while the matrix is
labelled `derived_proposal_requires_owner_confirmation` and has 21 proposal
tranche labels.

- [ ] **Step 2: Implement repository mapping search and proposal partition**

Search only repository docs/Qamus/prior records for a per-entry data mapping.
If none is found, use source-key order `v`, `n`, `p`, preserve the documented
VN-00/VN-01 boundary rule, and split the remaining entries into 19 balanced
contiguous groups. Report the rule and source-file search scope without
claiming an authoritative assignment.

- [ ] **Step 3: Join family rows onto all denominators**

Resolve family rows by canonical `loc`, whitelist source/entry identity, and
ledger selected-word rows. Count affected entries, example cards, selected
word rows, unique occurrences, and repeated appearances. Count producer
statuses separately and keep source-certified count at zero.

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tools.test_entry_card_word_ledger -v`

Expected: all proposal, clitic mapping, and denominator tests PASS.

### Task 4: Validator and repo-only fixture artifacts

**Files:**
- Create: `tools/validate_vn_ledger.py`
- Create: `qamus/examples/vnmap/vn-ledger.fixture.jsonl`
- Create: `qamus/examples/vnmap/vn-graph-metrics.fixture.json`
- Create: `qamus/examples/vnmap/vn-readiness-matrix.fixture.json`
- Modify: `tools/test_entry_card_word_ledger.py`

**Interfaces:**
- `validate_artifacts(ledger, metrics, matrix) -> ValidationReport`.
- CLI supports `--ledger`, `--metrics`, `--matrix`, and `--self-test`.

- [ ] **Step 1: Write validator red tests**

Mutate a fixture row to remove its reverse relationship, alter a denominator,
and add a non-enum edge; assert each mutation fails with a specific message.

- [ ] **Step 2: Implement structure, sums, enum, and reciprocity checks**

Require JSONL row uniqueness, valid canonical IDs, `vn_tranche` null in
candidate mode, sorted owner-edge values, D1-D4 sum checks, matrix totals, and
reverse entry/occurrence relationships. The self-test includes an expected
reciprocity failure and a passing fixture.

- [ ] **Step 3: Generate fixture artifacts from committed fixture inputs**

Run the builder with the fixture input paths and write the three fixture
outputs under `qamus/examples/vnmap/`. The fixture validator must not read any
external path.

- [ ] **Step 4: Run validator tests**

Run: `python -m unittest tools.test_entry_card_word_ledger -v`; `python tools/validate_vn_ledger.py --self-test`

Expected: focused suite and self-test both exit 0.

### Task 5: Full-input deliverables and harness gate

**Files:**
- Create: `vn-ledger.jsonl`
- Create: `vn-graph-metrics.json`
- Create: `vn-readiness-matrix.json`
- Create: `docs/reports/history/2026-07-29-VNMAP-REPORT.md`
- Modify: `tools/check_regressions.py`

**Interfaces:**
- Full artifacts are regenerated by the builder with explicit input paths;
  the harness uses the committed artifacts in structure-only mode.
- Harness output includes stable `ok   vnmap ...` markers and ends with the existing all-pass marker.

- [ ] **Step 1: Wire the repo-only harness gate**

Invoke `validate_vn_ledger.py --self-test` and a structure-only validation of
the committed four deliverables. Fail closed on missing files, malformed JSON,
or validator nonzero status.

- [ ] **Step 2: Generate full deliverables from the four read-only inputs**

Run the builder with explicit relative paths from the checkout's parent data
and sibling FAMWIDE lanes, writing only the requested root artifacts. Never
write to the input paths.

- [ ] **Step 3: Verify report content and RM-09 hygiene**

Require denominator tables, exact input counts, graph metrics, the labelled
derived proposal, clitic-family mapping, Compounding Impact, candidate-only
limits, exact missing-edge classes, and no absolute/private/production paths or
images in tracked lines.

- [ ] **Step 4: Run full verification**

Run: `python -m unittest tools.test_entry_card_word_ledger -v`; `python tools/validate_vn_ledger.py --self-test`; `python tools/validate_vn_ledger.py --ledger vn-ledger.jsonl --metrics vn-graph-metrics.json --matrix vn-readiness-matrix.json`; `python tools/check_regressions.py`; `python tools/check_artifact_ergonomics.py`; `git diff --check`.

Expected: focused tests, validator, artifact checks, and full harness exit 0; no `*.png` tracked; no RM-09 violations.

- [ ] **Step 5: Commit the bounded lane**

Stage only the VNMAP design/plan, builder, validator, tests, fixture subset,
full deliverables, report, and harness change. Commit:

```text
vnmap: add entry card word ledger and readiness matrix
```

