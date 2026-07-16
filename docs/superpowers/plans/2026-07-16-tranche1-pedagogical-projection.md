# Tranche 1 Pedagogical Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the eight-canary fixture-only Q7 projection chain with four public candidates, four typed unresolved records, deterministic lineage, and a non-authorizing apply manifest.

**Architecture:** A deterministic Python compiler selects the eight exact source rows from a caller-supplied read-only whitelist, routes each through one registered Ṣarf or Naḥw fixture projector, and emits closed schema-backed fixture planes. A tranche validator checks schema conformance, exact surfaces and segment composition, 4+4 routing, field crosswalks, and row/hash round trips; existing validators consume dedicated compatible views.

**Tech Stack:** Python 3.11 standard library, `unittest`, JSON/JSONL, repository mini-schema validators, Git.

## Global Constraints

- Work only on branch `andon-tranche1` in `../../tranche1-wt`.
- Every commit message starts with `tranche1:`; do not push.
- Treat `../../data/` and `../../fusha/` as read-only.
- Do not edit a whitelist, `wbw.js`, `wbw.css`, or renderer code.
- Do not create an applier, use SSH, deploy, publish, restart, or claim live readback.
- Emit learner text in English first; `Ṣarf` and `Naḥw` are labels only.
- Do not certify linguistic facts. `2:13:12` has no guessed singular/template/root/case; `7:54:23` has no automatic split; `5:2:12` has no case/role without a governor.
- Existing validators and fixtures must remain valid after additive schema changes.

---

### Task 1: Additive lineage and crosswalk schemas

**Files:**
- Create: `qamus/schemas/tranche1-projection-crosswalk.schema.json`
- Modify: `qamus/schemas/fact-ledger-row.schema.json`
- Modify: `qamus/schemas/morphology-candidate-lattice.schema.json`
- Modify: `qamus/schemas/dependency-candidate-lattice.schema.json`
- Modify: `qamus/schemas/morphosyntax-token.schema.json`
- Modify: `qamus/schemas/canonical-hover-payload.schema.json`
- Modify: `qamus/schemas/public-hover-projection.schema.json`
- Modify: `qamus/schemas/projector-record.schema.json`
- Modify: `qamus/schemas/phase4-apply-readiness-manifest.schema.json`
- Test: `tools/test_tranche1_projection.py`

**Interfaces:**
- Produces: optional `fact_ids`, `status`, `source_address`, `materialization_target`, `producer`, `projector_id`, and `version` carriers in the named schemas.
- Produces: a closed `qamus.tranche1_projection_crosswalk.v1` schema that requires those carriers and distinguishes candidate from queue materialization.

- [ ] **Step 1: Write the failing schema tests**

```python
class TrancheSchemaTests(unittest.TestCase):
    def test_crosswalk_schema_requires_lineage(self):
        errors = validate_crosswalk({"schema": "qamus.tranche1_projection_crosswalk.v1"})
        self.assertTrue(any("fact_ids" in error for error in errors))

    def test_named_schemas_accept_additive_lineage(self):
        for fixture in lineage_augmented_named_schema_fixtures():
            self.assertEqual([], validate_fixture(fixture))
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m unittest tools.test_tranche1_projection.TrancheSchemaTests -v`

Expected: failure because `tranche1-projection-crosswalk.schema.json` and its helper API do not exist.

- [ ] **Step 3: Add the closed crosswalk schema and optional carriers**

Define candidate rows with `status: candidate`, a projection target and output hash; define queue rows with one of `unresolved`, `source_gap`, `producer_pending`, or `syntax_pending`, plus `blocker`, `route`, and `materialization_target.live_mutation_allowed: false`. Keep all existing schema `required` arrays unchanged.

- [ ] **Step 4: Run schema tests and existing schema gates**

Run:

```powershell
python -m unittest tools.test_tranche1_projection.TrancheSchemaTests -v
python tools/validate_schema_coherence.py --self-test
python tools/validate_morphosyntax_token_metadata.py --self-test
python tools/validate_dependency_lattice.py --self-test
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```powershell
git add qamus/schemas tools/test_tranche1_projection.py
git commit -m "tranche1: add projection lineage schemas"
```

### Task 2: Register fixture morphology and syntax paths

**Files:**
- Modify: `tools/fact_projectors.py`
- Modify: `tools/lattice_projectors.py`
- Modify: `qamus/lattice/registered-projectors.json`
- Modify: `tools/test_fact_projectors.py`
- Modify: `tools/test_lattice_projectors.py`
- Modify: `tools/test_tranche1_projection.py`

**Interfaces:**
- Produces: `TRANCHE1_SARF_PROJECTOR_ID = "sarf.tranche1_fixture_projection.v1"`.
- Produces: `TRANCHE1_NAHW_PROJECTOR_ID = "nahw.tranche1_fixture_projection.v1"`.
- Produces: `run_tranche1_fixture_projector(projector, source_row, policy) -> dict` with producer, projector ID, version, status, fact IDs, and either candidate materialization or typed queue routing.

- [ ] **Step 1: Write failing registration and routing tests**

```python
def test_tranche_projector_contracts_are_registered(self):
    ids = {row["projector_id"] for row in fact_projectors.REGISTRY.list_contracts()}
    self.assertIn("sarf.tranche1_fixture_projection.v1", ids)
    self.assertIn("nahw.tranche1_fixture_projection.v1", ids)

def test_source_gap_abstains_without_root_or_segments(self):
    result = lattice_projectors.run_tranche1_fixture_projector(projector, source_row, policy)
    self.assertEqual("source_gap", result["status"])
    self.assertNotIn("public_payload", result)
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tools.test_fact_projectors tools.test_lattice_projectors tools.test_tranche1_projection.TrancheProjectorTests -v`

Expected: failures for missing contracts, registry rows, and runner.

- [ ] **Step 3: Implement minimal registered paths**

Add callable predicates/guards for the fixture policy, append the two registry records, and emit only `candidate`, `unresolved`, `source_gap`, `producer_pending`, or `syntax_pending`. Version is read from the registry entry and copied to every output.

- [ ] **Step 4: Run projector tests and registry self-test**

Run:

```powershell
python -m unittest tools.test_fact_projectors tools.test_lattice_projectors tools.test_tranche1_projection.TrancheProjectorTests -v
python tools/lattice_projectors.py self-test
python tools/fact_projectors.py list --json
```

Expected: tests and self-test exit 0; list contains both tranche projector IDs at version `1.0.0`.

- [ ] **Step 5: Commit**

```powershell
git add tools/fact_projectors.py tools/lattice_projectors.py tools/test_fact_projectors.py tools/test_lattice_projectors.py tools/test_tranche1_projection.py qamus/lattice/registered-projectors.json
git commit -m "tranche1: register fixture projectors"
```

### Task 3: Implement the eight-canary compiler

**Files:**
- Create: `tools/tranche1_projection.py`
- Create: `qamus/examples/tranche1/canary-policy.json`
- Create/generated: `qamus/examples/tranche1/source-canaries.jsonl`
- Create/generated: `qamus/examples/tranche1/fact-ledger.jsonl`
- Create/generated: `qamus/examples/tranche1/morphology-lattice.jsonl`
- Create/generated: `qamus/examples/tranche1/dependency-lattice.jsonl`
- Create/generated: `qamus/examples/tranche1/morphosyntax-token.jsonl`
- Create/generated: `qamus/examples/tranche1/canonical-hover-payload.jsonl`
- Create/generated: `qamus/examples/tranche1/normalized-public-payload.jsonl`
- Create/generated: `qamus/examples/tranche1/public-hover-projections.jsonl`
- Create/generated: `qamus/examples/tranche1/unresolved-queue.jsonl`
- Create/generated: `qamus/examples/tranche1/projection-crosswalk.jsonl`
- Create/generated: `qamus/examples/tranche1/dom-consumption.expectations.jsonl`
- Create/generated: `qamus/examples/tranche1/renderer-completeness.jsonl`
- Create/generated: `qamus/examples/tranche1/rich-hover-norm.jsonl`
- Test: `tools/test_tranche1_projection.py`

**Interfaces:**
- Produces: `compile_tranche(whitelist_path: Path, policy_path: Path, out_dir: Path, source_commit: str) -> dict`.
- Produces: deterministic JSON/JSONL using sorted keys and UTF-8 LF endings.
- Consumes: exact raw source rows selected only by the eight policy locations.

- [ ] **Step 1: Write failing compiler outcome tests**

```python
def test_compiler_emits_exact_four_plus_four(self):
    summary = compile_fixture(self.temp_dir)
    self.assertEqual(4, summary["candidate_count"])
    self.assertEqual(4, summary["queue_count"])

def test_source_gap_omits_guessed_facts(self):
    row = queue_by_loc(self.temp_dir)["2:13:12"]
    blob = json.dumps(row, ensure_ascii=False).lower()
    self.assertNotIn("candidate_root", blob)
    self.assertNotIn("template", blob)
    self.assertNotIn("singular", blob)

def test_positive_segments_reconstruct_exact_surface(self):
    for row in candidate_rows(self.temp_dir):
        self.assertEqual(row["surface"], "".join(s["surface"] for s in row["segments"]))
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tools.test_tranche1_projection.TrancheCompilerTests -v`

Expected: failure because compiler and policy are absent.

- [ ] **Step 3: Implement the minimal compiler and policy**

Map source segment `gloss_contribution` to public `gloss` and source `class` to public `qg_class` without changing values. Use English-first authored candidate explanations. For blocked rows, retain only identity, source hash, observation fact ID, lineage, blocker, route, and non-materialization state.

- [ ] **Step 4: Generate fixtures from the read-only corpus**

Run:

```powershell
python tools/tranche1_projection.py compile --whitelist ..\data\rh_live_01_beta_whitelist.jsonl --policy qamus/examples/tranche1/canary-policy.json --out-dir qamus/examples/tranche1 --source-commit f706698a9f682de1731b1913221538c7a4289870
```

Expected: JSON summary with `candidate_count: 4`, `queue_count: 4`, `live_mutations: 0`.

- [ ] **Step 5: Run compiler tests and artifact checks**

Run:

```powershell
python -m unittest tools.test_tranche1_projection.TrancheCompilerTests -v
python tools/check_artifact_ergonomics.py
git diff --check
```

Expected: all exit 0.

- [ ] **Step 6: Commit**

```powershell
git add tools/tranche1_projection.py tools/test_tranche1_projection.py qamus/examples/tranche1
git commit -m "tranche1: compile eight canary fixtures"
```

### Task 4: Add parity and round-trip validation

**Files:**
- Create: `tools/validate_tranche1_projection.py`
- Modify: `tools/test_tranche1_projection.py`
- Create: `qamus/examples/tranche1/README.md`

**Interfaces:**
- Produces: `validate_tranche(fixture_dir: Path, whitelist_path: Path | None, source_commit: str | None) -> list[str]`.
- Checks: all schema rows, exact source address/surface, exact segment parity, exact field mapping, producer/projector/version, row hashes, reverse crosswalk, 4+4 counts, and typed blockers/routes.

- [ ] **Step 1: Write failing mutation tests**

```python
def test_validator_rejects_segment_parity_drift(self):
    mutate_candidate_segment_surface(self.fixture_dir)
    self.assertContains(validate_tranche(self.fixture_dir), "segment parity")

def test_validator_rejects_round_trip_hash_drift(self):
    mutate_crosswalk_output_hash(self.fixture_dir)
    self.assertContains(validate_tranche(self.fixture_dir), "output hash")
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tools.test_tranche1_projection.TrancheValidatorTests -v`

Expected: failure because validator does not exist.

- [ ] **Step 3: Implement validation and fail-closed messages**

Return concrete errors tagged by location and artifact. The CLI prints counts and explicit PASS lines for schema, surface/segment parity, row/hash round trip, 4+4 routing, and zero live mutation.

- [ ] **Step 4: Run tranche and named validators**

Run:

```powershell
python tools/validate_tranche1_projection.py qamus/examples/tranche1 --whitelist ..\data\rh_live_01_beta_whitelist.jsonl --source-commit f706698a9f682de1731b1913221538c7a4289870
python tools/validate_morphosyntax_token_metadata.py qamus/examples/tranche1/morphosyntax-token.jsonl
python tools/validate_dependency_lattice.py qamus/examples/tranche1/dependency-lattice.jsonl
python tools/validate_renderer_completeness_gate.py qamus/examples/tranche1/renderer-completeness.jsonl
python tools/check_rich_hover_norm.py --whitelist qamus/examples/tranche1/rich-hover-norm.jsonl
python tools/validate_schema_coherence.py --self-test
```

Expected: all commands exit 0 with four candidates and four typed queue records.

- [ ] **Step 5: Commit**

```powershell
git add tools/validate_tranche1_projection.py tools/test_tranche1_projection.py qamus/examples/tranche1/README.md
git commit -m "tranche1: validate projection parity and lineage"
```

### Task 5: Build the bounded non-authorizing gate

**Files:**
- Modify: `tools/build_phase4_apply_readiness_manifest.py`
- Modify: `tools/validate_phase4_apply_readiness_manifest.py`
- Modify: `tools/test_tranche1_projection.py`
- Create/generated: `qamus/examples/tranche1/apply-plan.jsonl`
- Create/generated: `qamus/examples/tranche1/apply-readiness-manifest.json`
- Create/generated: `qamus/examples/tranche1/human-review-packet.json`

**Interfaces:**
- Manifest `source_corpus` carries exact corpus basename, row count, SHA-256, source commit, commit scope, and `verified_read_only_snapshot`.
- Validator accepts `--source-corpus` and `--source-commit` and rejects count/hash/commit drift.
- Human packet contains exactly the four unresolved rows and stays within the 25-row cap.

- [ ] **Step 1: Write failing manifest verification tests**

```python
def test_manifest_records_and_verifies_corpus_snapshot(self):
    manifest = build_fixture_manifest(self.temp_dir)
    self.assertEqual(34323, manifest["source_corpus"]["row_count"])
    self.assertEqual([], validate_manifest_with_source(manifest))

def test_manifest_rejects_source_commit_drift(self):
    errors = validate_manifest_with_source_commit("0" * 40)
    self.assertTrue(any("source_commit" in error for error in errors))
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tools.test_tranche1_projection.TrancheApplyGateTests -v`

Expected: failure because source corpus fields and CLI verification are absent.

- [ ] **Step 3: Extend builder/validator and generate gate artifacts**

The builder receives optional corpus path and source commit. The compiler writes a four-row `planned_not_applied` plan and four-row owner review packet. The manifest remains `pre_apply_not_authorized`; all future apply gates remain `not_run`.

- [ ] **Step 4: Run gate validators**

Run:

```powershell
python tools/validate_phase4_apply_readiness_manifest.py qamus/examples/tranche1/apply-readiness-manifest.json --plan-jsonl qamus/examples/tranche1/apply-plan.jsonl --source-corpus ..\data\rh_live_01_beta_whitelist.jsonl --source-commit f706698a9f682de1731b1913221538c7a4289870
python tools/validate_human_review_packet.py qamus/examples/tranche1/human-review-packet.json
```

Expected: both commands exit 0; manifest output says source-only/non-mutating; packet output says `{"ok": true, "rows": 4}`.

- [ ] **Step 5: Commit**

```powershell
git add tools/build_phase4_apply_readiness_manifest.py tools/validate_phase4_apply_readiness_manifest.py tools/test_tranche1_projection.py qamus/examples/tranche1
git commit -m "tranche1: add non-authorizing apply gate"
```

### Task 6: Final verification and report

**Files:**
- Create: `TRANCHE1-REPORT.md`

**Interfaces:**
- Report contains built surfaces, verbatim validator outputs, 4+4 table, exact `git log --stat`, risks, and exact nonclaims.

- [ ] **Step 1: Run the full fresh verification set**

Run all Task 4 and Task 5 commands plus:

```powershell
python -m unittest tools.test_tranche1_projection tools.test_fact_projectors tools.test_lattice_projectors -v
python tools/fact_ledger.py --self-test
python tools/lattice_projectors.py self-test
python tools/validate_phase4_apply_readiness_manifest.py --self-test
python tools/check_artifact_ergonomics.py
git diff --check
```

Expected: zero failures. Any incomplete linguistic row remains one of the four typed queue records.

- [ ] **Step 2: Capture exact Git evidence**

Run:

```powershell
git status --short --branch
git log --stat --oneline f706698..HEAD
git diff --stat f706698..HEAD
```

Expected: local `andon-tranche1` commits only; no push or remote mutation.

- [ ] **Step 3: Write `TRANCHE1-REPORT.md`**

Include the validator stdout verbatim in fenced text blocks, the exact 4+4 table, current corpus/hash/commit evidence, stale metadata mismatch risk, and these nonclaims: fixture-only; no linguistic certification; no root/template/singular/case guess for source gaps; no live/browser/DOM readback; no whitelist or renderer mutation; no applier; no SSH; no deploy/publication/release; no push; no corpus-wide correctness or coverage claim.

- [ ] **Step 4: Verify report and repository state**

Run:

```powershell
rg -n "EXACT NONCLAIMS|fixture-only|no linguistic certification|no live deployment|pre_apply_not_authorized" TRANCHE1-REPORT.md
git diff --check
git status --short
```

Expected: report contains all mandatory headings and only the report is uncommitted.

- [ ] **Step 5: Commit report**

```powershell
git add TRANCHE1-REPORT.md
git commit -m "tranche1: report fixture projection proof"
```

- [ ] **Step 6: Re-run final smoke after the report commit**

Run the tranche validator, all five named validators, phase-4 validator, human-review validator, unit tests, artifact ergonomics, `git diff --check`, and `git status --short --branch` again.

Expected: all gates exit 0 and the worktree is clean on `andon-tranche1`.
