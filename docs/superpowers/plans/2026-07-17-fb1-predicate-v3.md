# FB1 Predicate v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the candidate-only `pred_fb1_clitic_pronoun_v3` predicate beside unchanged v1/v2 owners, measure its strict-subset population, and deliver the requested evidence artifacts.

**Architecture:** Keep v1 and v2 functions, fixtures, and behavior intact. Add v3 as a named predicate using exact previous `(role, class)` registries: attached-role/v2 admissions first, then generic-role admission only after an empirical governor/host. Add a separate v3 measurement CLI that takes corpus and STRAT inputs explicitly and writes lane artifacts without copying or mutating the corpus.

**Tech Stack:** Python 3 standard library, JSONL fixtures/artifacts, existing lattice registry and unittest/check_regressions harness.

## Global Constraints

- Preserve `pred_fb1_clitic_pronoun` and `pred_fb1_clitic_pronoun_v2`; do not remove or mutate either owner.
- Use exact numeric `segment_index` ordering and fail closed for leading, explicit non-attached, conjunction-only, and ambiguous predecessor shapes.
- Keep corpus input read-only and available only through required measurement CLI arguments.
- Keep all outputs candidate-mode; do not mutate whitelist/live surfaces, push, deploy, or select an owner boundary.
- Commit locally with a `predv3:` message and do not push.
- Stop and write `PAUSED-STATE.md` plus a WIP commit only if usage/time limits prevent completion.

---

### Task 1: Add red-first v3 fixtures and tests

**Files:**
- Create: `qamus/examples/fb1-predicate-v3/predicate-fixtures.jsonl`
- Modify: `tools/test_lattice_projectors.py:19,39-77`

**Interfaces:**
- Consumes: existing v1/v2 predicates and `FB1_ATTACHED_ROLE_REGISTRY`.
- Produces: four committed fixture rows with `expected_v1`, `expected_v2`, and `expected_v3`, plus a test that calls the not-yet-existing v3 predicate.

- [ ] **Step 1: Write the failing v3 fixture matrix.**

Create four rows covering:

```json
{"fixture_id":"generic_preposition_minha","expected_v1":true,"expected_v2":false,"expected_v3":true}
{"fixture_id":"generic_emphatic_particle_innahu","expected_v1":true,"expected_v2":false,"expected_v3":true}
{"fixture_id":"generic_prefix_conjunction_wahuwa","expected_v1":true,"expected_v2":false,"expected_v3":false}
{"fixture_id":"generic_wish_particle_laytani","expected_v1":true,"expected_v2":false,"expected_v3":true}
```

Use full segment objects matching the supplied corpus shapes: `qg-preposition` + `referential_pronoun`, `qg-particle` + generic `pronoun`, `qg-conjunction` + `independent_pronoun_3ms`, and `qg-particle` + `subject_pronoun` respectively.

- [ ] **Step 2: Add the test before implementing v3.**

Add a `PREDV3_FIXTURES` path and a test that loads the four rows and asserts all three predicate results. Keep the existing 12-row v2 test unchanged. Also extend the registry ID list with `sarf.fb1_clitic_pronoun_composition.v3` so the registration test fails until the registry entry exists.

- [ ] **Step 3: Run the focused test and verify the expected red failure.**

Run:

```powershell
python -m unittest tools.test_lattice_projectors.ClassPredicateTests.test_fb1_predicate_v3_red_first_fixtures -q
```

Expected: a failure caused by the missing v3 predicate/registry entry, not a fixture parse error.

### Task 2: Implement the v3 predicate and registration contract

**Files:**
- Modify: `tools/lattice_projectors.py:51-280, 2090-2110`
- Modify: `qamus/lattice/registered-projectors.json` immediately after the v2 FB1 entry
- Modify: `tools/test_lattice_projectors.py` only as needed to assert registry metadata

**Interfaces:**
- Consumes: existing `FB1_ATTACHED_ROLE_REGISTRY`, `_FB1_TYPED_SUBJECT_PREDECESSOR_CLASSES`, and the v3 fixture matrix.
- Produces: `FB1_GENERIC_NON_ATTACHED_ROLE_MARKERS`, `FB1_GENERIC_GOVERNOR_HOST_REGISTRY`, `FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY`, `FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY`, `pred_fb1_clitic_pronoun_v3(row)`, and `NAMED_PREDICATES["pred_fb1_clitic_pronoun_v3"]`.

- [ ] **Step 1: Implement only the exact registries and predicate.**

Use the reviewed exact pairs:

```python
FB1_GENERIC_GOVERNOR_HOST_REGISTRY = frozenset({
    ("an", "qg-preposition"), ("ba", "qg-preposition"),
    ("bound_preposition_ala", "qg-preposition"), ("fi", "qg-preposition"),
    ("prefix_preposition", "qg-preposition"),
    ("prefix_preposition_ba", "qg-preposition"),
    ("prefix_preposition_bi", "qg-preposition"),
    ("preposition", "qg-preposition"),
    ("preposition_ba", "qg-preposition"),
    ("preposition_fi", "qg-preposition"),
    ("relation_adverb", "qg-preposition"),
    ("relation_preposition", "qg-preposition"), ("with", "qg-preposition"),
    ("lam", "qg-lam"), ("lam_relation", "qg-lam"),
    ("prefix_lam", "qg-lam"), ("prefix_lam_preposition", "qg-lam"),
    ("prefix_preposition", "qg-lam"), ("prepositional_lam", "qg-lam"),
    ("emphasis_particle", "qg-emphasis"),
    ("emphatic_particle", "qg-emphasis"), ("particle", "qg-emphasis"),
    ("subordinating_particle", "qg-emphasis"),
    ("emphatic_particle", "qg-particle"), ("inna", "qg-particle"),
    ("wish_particle", "qg-particle"),
    ("nominal_host", "qg-noun-stem"), ("noun_stem", "qg-noun-stem"),
    ("relation_word", "qg-noun-stem"), ("verb_stem", "qg-verb-stem"),
    ("stem", "qg-segment"), ("token", "qg-segment"),
})
```

Keep the three class registries exported so F-C dependency producers can reuse the evidence boundary. The predicate must check explicit family override, then v2 admissions, then the generic-role marker exclusion and exact predecessor pair. Do not use substring matching on predecessor roles.

- [ ] **Step 2: Register v3 as a separate candidate-only projector.**

Add the same guards and two-vote gate as v2, with:

```json
"projector_id":"sarf.fb1_clitic_pronoun_composition.v3",
"class_predicate":"pred_fb1_clitic_pronoun_v3",
"version":"3.0.0",
"resolution_method":"fa_typed_fact_byte_exact_clitic_calibration_v3",
```

Use a target-population note that names the empirical generic-role governor/host fallback and says v1/v2 remain runnable.

- [ ] **Step 3: Wire lattice self-test and run the focused red/green test.**

Add the v3 fixture check to `tools/lattice_projectors.py` with result key `t25_fb1_predicate_v3_fixture_matrix`, then run:

```powershell
python -m unittest tools.test_lattice_projectors -q
python tools/lattice_projectors.py self-test
```

Expected: both commands pass, including the unchanged v2 matrix.

### Task 3: Build the v3 measurement CLI

**Files:**
- Create: `tools/measure_fb1_predicate_v3.py`
- Modify: `tools/check_regressions.py` in the FB1 harness block

**Interfaces:**
- Consumes: `--corpus`, `--strat`, `--out-dropped`, `--out-readmitted`, `--out-fp-sample`, `--report`, `--seed`, `--expected-v1`, and optional hand-check JSONL paths.
- Produces: v1/v2/v3 population counts, exact v1−v3 drop rows, exact v2→v3 re-admission rows, 40-row outside-STRAT sample, 12-row new-admission sample, and the report.

- [ ] **Step 1: Add CLI loaders and deterministic helpers.**

Reuse the v2 JSONL and segment-ordering conventions, but keep the corpus path required and never embed a repository corpus default. Add deterministic `loc_key`, SHA-256 reporting, JSONL read/write, and hand-check validation that rejects missing/duplicate locations or non-boolean verdicts.

- [ ] **Step 2: Add three-way classification and exact drop reasons.**

Compute sets with all three named predicates and stop with a clear `STOP` error if `v3 - v1` is non-empty. For every `v1 - v3` row, classify the first decisive v1 role hit as `leading`, `named_non_attached`, `conjunction_prev`, or `ambiguous_prev`, recording segment role/class evidence and the previous role/class pair. Write the complete list to `predv3-dropped.jsonl`.

- [ ] **Step 3: Add exact re-admission evidence.**

For every `v3 - v2` row, record v1/v2/v3 booleans, the v3 match reason, generic role, previous role/class, and compact ordered segments. Write `predv3-readmitted.jsonl`.

- [ ] **Step 4: Add governor/host inventory and both deterministic samples.**

Enumerate all 39 previous role+class shapes across generic v2 drops with counts, classifications, and at least one corpus location/surface example each. Sample 40 rows from `v3 - strat_all_locs` and 12 rows from `v3 - v2` using `random.Random(20260718)`, sorted by location for stable artifacts. Require hand-check inputs to match exactly and write `predv3-fp-sample.jsonl` with verdicts and reasons.

- [ ] **Step 5: Render the complete PREDV3 report.**

Include source hashes, baseline v1/v2/v3 table, strict-subset proof, governor/host/conjunction/ambiguous registry table, exact remaining-drop decomposition and machine artifact pointers, STRAT-234 and all-455 overlap for all three owners, fixture matrix, both hand-checks with FP estimates, exact nonclaims, and Compounding Impact for F-C dependency producers.

- [ ] **Step 6: Wire the v3 measurement self-test into the harness.**

Add `tools/measure_fb1_predicate_v3.py --self-test` to `tools/check_regressions.py` and require the exact `FB1 PREDICATE V3 MEASUREMENT SELF-TEST PASS` marker. Leave the v2 measurement gate intact.

### Task 4: Generate lane artifacts and verify completion

**Files:**
- Create outside the repo lane: `PREDV3-REPORT.md`, `predv3-dropped.jsonl`, `predv3-readmitted.jsonl`, `predv3-fp-sample.jsonl`
- Modify: no corpus or whitelist files

**Interfaces:**
- Consumes: `../../data/rh_live_01_beta_whitelist.jsonl`, `../PREDV2/predv2-dropped.jsonl`, and the existing STRAT packet selected from the repository inputs/CLI contract.
- Produces: the four requested candidate artifacts in the PREDV3 lane.

- [ ] **Step 1: Identify the supplied STRAT packet without copying the corpus.**

Use the existing repository/path conventions from the PREDV2 measurement invocation and verify its row count and SHA-256 before measuring. If no explicit STRAT input can be located, report the exact blocker instead of fabricating overlap data.

- [ ] **Step 2: Run the v3 measurement with seed 20260718.**

Run the CLI with the read-only corpus and explicit STRAT path, output paths in the PREDV3 lane, `--expected-v1 4865`, `--sample-size 40`, and hand-check files containing the deterministic 40 and 12 verdicts. Confirm v3 is 4,621, v3−v1 is empty, and the 12 new-admission verdicts are all true.

- [ ] **Step 3: Run artifact and source checks.**

Run `git diff --check`, the v3 self-test, focused unittest, `python tools/check_artifact_ergonomics.py`, and the full `python tools/check_regressions.py` with a timeout sufficient for the repository. Inspect JSONL counts, report section presence, unchanged corpus hash, and git status.

- [ ] **Step 4: Commit the implementation and report the evidence.**

Stage only the v3 code, fixtures, registry, harness, design/plan docs, and any intended repo artifacts. Verify the staged file list, commit with a message beginning `predv3:`, confirm no push occurred, and report any checks that remain unverified.
