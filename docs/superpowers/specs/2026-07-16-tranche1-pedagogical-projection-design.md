# Tranche 1 Pedagogical Projection Design

## Goal

Build the Q7 eight-canary, fixture-only proof that connects typed source observations to registered morphology or syntax projectors, normalized learner-safe payload candidates, typed unresolved queues, deterministic validation, and a non-authorizing apply-readiness gate.

## Boundaries

- Work only in the `andon-tranche1` worktree.
- Treat `../../data/rh_live_01_beta_whitelist.jsonl` and `../../data/entries.jsonl` as read-only inputs.
- Do not edit whitelist data, `wbw.js`, `wbw.css`, renderer code, or the pristine Fusha checkout.
- Do not create an applier, use SSH, push, deploy, publish, restart, or claim live behavior.
- All linguistic rows remain candidates or typed unresolved records. No generated artifact certifies a root, lemma, pattern, plural derivation, case, mood, governor, attachment, or referent.
- Learner-facing fields are English-first. `Ṣarf` and `Naḥw` may appear only as concise grammar labels.

## Architecture

The compiler reads the current whitelist snapshot and selects the eight Q7 token addresses. It verifies each exact surface, captures a content hash of the raw source row, and projects only the four Q7-positive rows. The four adversarial or incomplete rows are emitted without learner payloads as typed queue records with an exact blocker and route.

The output is split into four reviewable planes:

1. `source-canaries.jsonl` records exact addresses, surfaces, raw-row hashes, and only the source fields needed by the fixture compiler.
2. `normalized-public-payload.jsonl` is the eight-row compiler envelope: four `candidate_projection` records and four `typed_queue_record` records.
3. `public-hover-projections.jsonl` and `unresolved-queue.jsonl` are deterministic filtered views for public-schema and queue validation.
4. `projection-crosswalk.jsonl` binds every source observation fact ID to producer, projector ID, semantic version, status, target artifact/field, output hash, and exact `gloss`/`qg_class` to `gloss_contribution`/`class` mappings.

DOM behavior is represented only by `dom-consumption.expectations.jsonl`. Candidate rows assert the payload and exact segment reconstruction a renderer would consume; queue rows assert that no learner payload or hover should be consumed. Every row explicitly says `live_readback: false` and `live_mutation_allowed: false`.

## Schema Strategy

Add the optional lineage carrier fields `fact_ids`, `status`, `source_address`, `materialization_target`, `producer`, `projector_id`, and `version` to each Q7-named schema. Existing required sets and enums remain unchanged, so historical fixtures continue to validate.

The new `tranche1-projection-crosswalk.schema.json` requires those fields and closes the record shape. It defines two variants:

- `candidate_projection`: requires a public projection reference, materialization mappings, and output hash.
- `typed_queue_record`: requires a typed blocker, route, and an explicit absence of public materialization.

The Phase 4 manifest schema gains an optional closed `source_corpus` object carrying basename, row count, SHA-256, Fusha checkout commit, commit scope, and verification status. Historical manifests remain valid.

## Registered Projectors

Add one fixture projector contract per family:

- `sarf.tranche1_fixture_projection.v1`
- `nahw.tranche1_fixture_projection.v1`

Both appear in `fact_projectors.py` and `qamus/lattice/registered-projectors.json`; their named predicates, guards, and fixture projection entry point live in `lattice_projectors.py`. They emit candidates or abstentions only. Every produced tranche record carries `producer`, `projector_id`, and `version`.

The morphology path handles `3:141:4`, `24:31:76`, `39:63:3`, `22:18:9`, `2:13:12`, and `7:54:23`. The syntax path handles `2:34:5` and `5:2:12`.

## Canary Outcomes

| Location | Outcome | Rule |
| --- | --- | --- |
| `3:141:4` | candidate | typed positive; preserve stem and subject marker |
| `24:31:76` | candidate | preserve exact `ART + DER + STEM + PL` segmentation |
| `2:34:5` | candidate | preserve lām + proper name and explicit no-root status |
| `39:63:3` | candidate | preserve exact segmented surface parity |
| `22:18:9` | unresolved | fused/segmented same-surface compatibility is not typed |
| `2:13:12` | source gap | omit singular, template, root certification, and case claim |
| `7:54:23` | producer pending | generic whole-token segment cannot authorize a split |
| `5:2:12` | syntax pending | omit role/case because governor evidence is absent |

## Validation and Failure Handling

`tools/validate_tranche1_projection.py` validates all tranche schemas and artifacts, exact source surfaces, exact segment concatenation, 4+4 counts, producer/projector/version lineage, canonical/public segment field mappings, deterministic row hashes, and reverse source-to-output round trips. Any incomplete canary must appear in the typed queue; an omitted or accidentally projected blocker is a hard failure.

The generated fixtures are also checked by the five Q7 validators:

- `validate_morphosyntax_token_metadata.py`
- `validate_dependency_lattice.py`
- `validate_renderer_completeness_gate.py`
- `check_rich_hover_norm.py`
- `validate_schema_coherence.py`

The apply plan feeds `build_phase4_apply_readiness_manifest.py`. The resulting manifest is schema-validated, checked against the plan and read-only corpus snapshot, and remains `pre_apply_not_authorized`. The four unresolved records form a bounded human-review packet checked by `validate_human_review_packet.py`.

## Source Snapshot Truth

The observed read-only corpus contains 34,323 rows with SHA-256 `5805cc9f3b3c98f5e2b6209871f106d708dc42848b135e780531cc8b2e38ac6e`. The source checkout commit at design time is `f706698a9f682de1731b1913221538c7a4289870`. The data directory is not itself a Git repository, so the manifest identifies that commit as the Fusha checkout scope, not as a data-repository commit.

The older rich-seg debt metadata records 34,322 rows and a different hash. This is reported as stale comparison metadata; it does not replace the freshly verified read-only snapshot.

## Done When

- The compiler reproducibly emits exactly four candidate projections and four typed queue records.
- All named schemas preserve their existing validation behavior and the tranche schema closes the new carrier.
- Both registered projector paths are exercised and every produced row has complete lineage.
- The five named validators, parity/hash validator, phase-4 validator, human-review validator, tests, and artifact ergonomics checks pass, or an incomplete linguistic row is represented by the expected typed queue rather than a guessed projection.
- `docs/reports/history/2026-07-16-QAMUS-FIXTURE-TRANCHE1-REPORT.md` records verbatim command output, the 4+4 table, `git log --stat`, risks, and exact nonclaims.
- All commits are local to `andon-tranche1`, prefixed `tranche1:`, with no push.
