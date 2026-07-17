# FD2 Producer-Aware Rerun Design

Status: pre-approved by the FD2 execution brief. This document records the bounded rerun design; it does not authorize scholarly certification, publication, live mutation, or a corpus write.

## Goal

Re-run the shared F-D compiler over the 455 stratified, v575-verified rows with the calibrated F-B clitic-pronoun producer and F-C naḥw dependency producer active only within their existing guards. Emit fact-derived learner projections, the owner’s thirteen FD2 metrics, before-to-after movement from the prior F-D baseline, per-row verdicts, and an exact nonclaims report.

## Boundary

- F-B is invoked only for `morphology_family == "clitic_pronoun_compositions"`; its positive and unresolved contract records remain candidate-only.
- F-C is invoked only when its source-addressed evidence selector returns a positive input and its strict contract builder accepts it; a withheld row remains prior state.
- All other families retain the previous source row and are not reclassified by a new producer.
- The read-only corpus and entries files are explicit CLI inputs. Their absolute paths are never serialized into repo artifacts.
- The existing `fd-455-*` baseline artifacts and the Ṣufahāʾ proof fixture remain unchanged.

## Data flow

`fd2_rerun.py` loads `strat-455.jsonl`, `v575-verdicts.jsonl`, the explicitly supplied whitelist and entries, then builds the occurrence-to-appearance index in memory with `build_occurrence_appearance_index.build_index`. The shared compiler joins rows by exact location, calls the guarded producer contracts, and keeps each producer’s typed envelope separate. A deterministic adapter composes the available facts into source-safe row views; it never copies corpus learner prose into generated fields.

The adapter emits one candidate verdict per stratified location. Existing structural checks remain in force: exact source segmentation, entry linkage, source/scholar routing, byte/code-point reconstruction, and immutable `live_mutation_allowed=false`. Producer exceptions, cross-producer surface disagreement, and non-source-addressed outputs are recorded as defects or conflicts instead of being silently counted as facts.

## Fact-derived learner contract

For a positive F-B record, the adapter derives component glosses and morphology notes from each typed component fact (`typed_kind`, `role`, `class`, and exact span), then derives the composition statement from those component outputs. For a positive F-C record, it derives the naḥw statement from the typed role, relationship, governor, governed occurrence, case/mood, and ending state. The literal labels are:

- `Ṣarf — how this piece forms the word`
- `Naḥw — what this piece does here`

Generated fields are plain English, contain no segment-label notation, source/evidence prose, absolute paths, or producer process language, and preserve the canonical Arabic surface exactly. Compact and expanded views consume the same generated payload identity.

## Report contract

`fd2-455-report.json` contains the report schema, producer lineage, explicit calibration scope, the thirteen owner metrics, baseline movement, exact blocker/queue maps, conflict/defect evidence, and the repo-relative `fd2-455-verdicts.jsonl` artifact name. The verdict JSONL contains one deterministic row record per location. A small metadata sidecar records the JSONL count and generator without embedding external paths.

The metrics are:

1. rows with complete morphology facts;
2. rows with complete naḥw facts;
3. rows with both;
4. rows generating an at-rest projection;
5. rows generating rich Ṣarf;
6. rows generating rich Naḥw;
7. rows generating both compact and expanded views;
8. rows with repeated-appearance parity;
9. unresolved rows by exact blocker;
10. source/scholar queues;
11. reconstruction failures;
12. projection conflicts; and
13. newly discovered producer defects.

Movement records the four prior values exactly (`437`, `437`, `383`, `0`) and the computed FD2 values, with signed deltas and a note that producer scope—not corpus-wide completion—is being measured.

## Validation and rollback

Red-first unit tests cover producer scope, fact-only generation, surface preservation, compact/expanded payload identity, occurrence-index parity, exact blockers, baseline movement, and defect/conflict detection. `validate_fd2_rerun.py --self-test` validates committed FD2 fixtures without external inputs; `check_regressions.py` invokes that validator. The operational rerun command takes all four external paths explicitly and writes only the requested FD2 artifacts.

Rollback is limited to removing FD2-only code, schemas, fixtures, reports, and the harness hook. No corpus, source whitelist, Qamus entry, live renderer, or deployment surface is changed.

## Exact nonclaims

- Candidate facts are not scholarly certification.
- Calibration-scope reach is not corpus-wide producer accuracy or coverage.
- A generated learner view is not permission to publish or materialize a public hover.
- Repeated-appearance parity proves the merged index’s canonical occurrence reuse only; it is not live page/render coverage.
- No live effect, whitelist append, restart, push, release, or publication is performed.
