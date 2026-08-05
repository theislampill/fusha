# PROOF-V Real Verb Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one candidate-only, repo-self-contained end-to-end verb proof whose typed facts, graph chain, shared compiler payload, uncertainty display, manifest, render attestation, report, and harness gate all agree.

**Architecture:** Keep the owner-preferred `فَٱتَّبِعْنِىٓ` occurrence at `19:43:10` because it is the sole surface match and its nearest same-lexeme card-selected occurrence (`28:50:12`) has a deterministic crosswalk with documented-form evidence and a canonical occurrence backlink. A small PROOF-V producer consumes that bounded source packet, reuses FAM4 tokenization/affix and weak-root gates plus FAM5 Treatment-C conventions, emits candidate typed facts and explicit source-gap facts, and passes those facts to a shared compiler adapter that creates compact/expanded learner views, hover metadata, per-appearance parity, and readback descriptors. The build command reads the live corpus and EDGES lane only through explicit arguments; committed fixture artifacts make the validator and full regression harness self-contained.

**Tech Stack:** Python 3 standard library, existing F-A typed-claim envelope, FAM4/FAM5 registries and helpers, typed-edge graph schema, JSON/JSONL fixtures, `unittest`, repository regression harness.

## Global Constraints

- Candidate mode only: `pre_apply_not_authorized`; all materialization and live mutation flags are false.
- Scripture text is preserved exactly; normalized keys are match-only and never replace display text.
- Use only facts already present in repo or lane packets; absent exact source facts become typed `source_gap` / unresolved records with a scholar-packet route.
- The chosen whitelist surface is matched by surface key, never by an index; all seven `تَوَكَّلْتُ` alternatives are recorded only as the comparison survey.
- The target occurrence is reader-only and has no direct lexeme, card, or selected-word edge; the report must say this and show the nearest real same-lexeme chain.
- Every written base letter receives exactly one primary Ṣarf display class; diacritics remain hover metadata, and Naḥw colors never repaint letters.
- Public learner labels are exactly `Ṣarf — how this piece forms the word` and `Naḥw — what this piece does here`.
- Protective nūn is `sarf.protective_nun` / `qg-protective-nun`, never a particle; the attached final pronoun is a 1cs object pronoun.
- Form-VIII shared-letter gemination uses Treatment-C and an explicit A–D idghām classification; no naive split is emitted.
- Do not modify `data/entries.jsonl`, `rh_live_01_beta_whitelist.jsonl`, or EDGES artifacts; do not add PNGs, external source text, private paths, secrets, pushes, or deployment changes.
- Commit messages begin with `proofv:` and no push is performed.

---

### Task 1: Lock the red-first contract

**Files:**

- Create: `tools/test_proofv_verb.py`
- Create: `qamus/examples/proof-verb/producer-fixtures.jsonl`

- [ ] Write failing tests for exact surface preservation, one-class-per-base-letter ownership, Form-VIII infix/root shared-letter Treatment-C metadata, hamzat al-waṣl class, protective-nūn typing, 1cs object-pronoun typing, unresolved Naḥw governor/object relation, candidate-only flags, N-LANG labels, and payload parity.
- [ ] Add adversarial fixtures for a particle-labelled protective nūn, naive gemination splitting, missing source crosswalk, and a surface-only template claim.
- [ ] Run `python -m unittest tools.test_proofv_verb -v` and capture the expected red result before implementation.

### Task 2: Implement the bounded typed-fact producer

**Files:**

- Create: `tools/proofv_verb_producer.py`
- Create: `qamus/examples/proof-verb/proofv-form-registry.jsonl`
- Modify: `tools/fact_projectors.py`

- [ ] Implement explicit target selection/survey parsing from caller-supplied rows and surface keys.
- [ ] Reuse FAM4 tokenization, affix registry, weak-root defeater registry, and FAM5 carrier conventions; do not infer root from normalization or gloss.
- [ ] Build candidate typed facts for the source-addressed Form-VIII structure and typed unresolved facts for missing exact Naḥw or source certification.
- [ ] Record each written base letter once, with the shared `تّ` span carrying root radical 1 plus the Form-VIII infix as internal roles while retaining one display owner.
- [ ] Register an abstention-first `sarf.proofv.verb.v1` projector contract whose materialization result is always disabled.
- [ ] Run the focused tests and make them green.

### Task 3: Build the graph-backed shared compiler packet

**Files:**

- Create: `tools/proofv_shared_compiler.py`
- Create: `tools/build_proofv_verb.py`
- Create: `qamus/examples/proof-verb/source-selection.json`
- Create: `qamus/examples/proof-verb/source-occurrence.json`
- Create: `qamus/examples/proof-verb/canonical-facts.json`
- Create: `qamus/examples/proof-verb/typed-edge-graph.jsonl`
- Create: `qamus/examples/proof-verb/crosswalk-forward.json`
- Create: `qamus/examples/proof-verb/crosswalk-reverse.json`
- Create: `qamus/examples/proof-verb/shared-compiler-payload.json`
- Create: `qamus/examples/proof-verb/render-proof.json`
- Create: `qamus/examples/proof-verb/PROOFV-MANIFEST.json`
- Create: `qamus/examples/proof-verb/README.md`

- [ ] Extract only the bounded target appearance edge and the complete nearest same-lexeme entry→sense→card→selected-word→crosswalk→occurrence evidence from EDGES.
- [ ] Compile at-rest spans, compact and expanded Ṣarf/Naḥw views, hover records, per-appearance descriptors, readback descriptors, uncertainty display, and exact reconstruction from canonical facts rather than hand-authored output.
- [ ] Preserve source scripture surface and expose `PENDING`/source-gap state where exact evidence is absent.
- [ ] Emit the manifest chain enumeration, artifact owners, input boundaries, generator commands, candidate status, and no-PNG policy.

### Task 4: Validator, report, and full harness gate

**Files:**

- Create: `tools/validate_proofv_verb.py`
- Create: `docs/reports/history/2026-07-17-PROOFV-REPORT.md`
- Modify: `tools/check_regressions.py`

- [ ] Validate all committed proof artifacts without corpus, network, or lane dependencies.
- [ ] Validate graph edge schemas/statuses, crosswalk reciprocity, fact-to-payload bindings, letter ownership, Treatment-C metadata, Naḥw uncertainty, hover provenance, readback parity, manifest closure, candidate-only flags, RM-09, and no tracked PNGs.
- [ ] Wire a named PROOF-V self-test/fixture gate into the full harness and require an `ALL PASS` marker.
- [ ] Run focused tests, validator, artifact ergonomics/classification, RM-09/image scans, and the complete `python tools/check_regressions.py` harness.

### Task 5: Final audit and commit

- [ ] Re-read the final report and manifest against the owner acceptance checklist, including the target-vs-fallback selection reasoning and §13 pre-deploy limits.
- [ ] Run `git diff --check`, inspect status and the staged file list, and confirm read-only inputs are unchanged.
- [ ] Commit only the intended PROOF-V files with a `proofv:` message; leave the branch unpushed.
- [ ] Report exact done, owner-gated, artifact-gated, partial, deferred, and unverified state from fresh command output.
