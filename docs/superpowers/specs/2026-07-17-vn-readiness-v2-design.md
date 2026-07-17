# VN Readiness v2 Design

## Goal

Regenerate the VN-00 through VN-20 readiness ledger from the recovered VNREC
scope and the EDGES typed crosswalk, while preserving historical authority,
making both provisional namespaces explicit, and keeping every output
candidate-only.

## Boundaries

- `vn_tranche` remains the scalar VNREC field. A single historical claim emits
  `VN-00`, `VN-01`, or `VN-02`; multiple historical claims emit `null` with
  `historical_conflict`; a row without historical claims emits the partition
  proposal as `proposed:vn-partition-proposal.v1:<label>`.
- Every row also carries `vn_tranche_claims`, `vn_tranche_evidence`, generic
  `evidence`, `vn00_staging_member`, and both
  `vn_tranche_partition_proposal` and `vn_tranche_plan_table_proposal`.
  Provisional fields are populated only for rows with no historical claim.
- The documented windows remain separate 92-entry scopes and are marked
  CLOSED-FROZEN from recorded milestone evidence. Staging-only rows are
  counted under `VN-00-STAGING`; they are never merged into the documented
  VN-00 matrix row. Dual-claim rows remain in their documented scope's
  conflict count while their scalar field stays null.
- The plan-table namespace covers VN-00 through VN-23 and exposes particles as
  `UNPLANNED_PARTICLES`. The partition namespace covers VN-00 through VN-20.
- Crosswalk status comes from the EDGES forward artifact. Only
  `deterministic_exact` and `candidate` are usable; `ambiguous` is not.
  Source certification remains exactly zero. The named sufaha, fattabini, and
  ma proofs add three candidate deploy-shaped fully-rich rows, with their
  names retained in the matrix.

## Components

1. `tools/build_vn_readiness_v2.py` reads all data through explicit CLI paths,
   reuses the existing entry/card/word ledger for the canonical D1-D4 joins,
   joins VNREC claims, plan ranges, EDGES crosswalk/debt rows, FAMWIDE rows,
   and the committed proof descriptor fixture, then emits a pretty JSON matrix,
   newline-terminated JSONL ledger, and report.
2. `tools/validate_vn_readiness_v2.py` validates schema, denominator
   conservation, the 164 null historical conflicts, staging separation, both
   proposal namespaces, crosswalk status accounting, proof-name accounting,
   debt-family totals, and artifact ergonomics. Its self-test uses only the
   committed fixture subset and includes red-first mutations.
3. `tools/test_vn_readiness_v2.py` exercises the builder with the same fixture
   subset and asserts the owner rules before the validator runs.
4. `qamus/examples/vnmap-v2/` contains small JSON/JSONL fixture inputs and
   generated fixture outputs so a fresh clone can run the builder and validator
   without lane or corpus paths.
5. `tools/check_regressions.py` invokes the focused v2 tests, validator
   self-test, and committed fixture artifact validation.

## Matrix shape

The matrix has `views.authoritative_partition` and `views.plan_table`. Each
row reports entries, cards, displayed selected words, unique canonical
occurrences, usable graph rows split by deterministic/candidate status, source
certification, fully-rich proof rows, recorded already-live/no-op scope,
owner/scholar and source/crosswalk debt breakdowns, and an exact next action.
The matrix also carries denominator totals, a separate staging namespace,
historical-conflict totals, the stable pre-crosswalk delta, source evidence,
and a Compounding Impact section.

## Testing and failure behavior

- The fixture builder must pass before full-corpus generation is attempted.
- Missing or malformed explicit inputs fail closed with a non-zero exit code.
- The builder never writes an input path, performs network access, mutates live
  state, or depends on a lane-relative default.
- Reports and JSON artifacts end with a newline; JSON is pretty-printed and
  JSONL is one record per line. No PNG is created or tracked.
