# Plan: FB1 clitic-pronoun composition calibration

## Goal

Deliver the pre-approved FB1 calibration packet on `andon-fb-clitic-producers`
with a registered, abstention-first producer, governed F-A records, red-first
fixtures, a >=40-row calibrated sample, an exact report, and a full harness
pass. No push or corpus mutation.

## Constraints and done-when

- Work only in the assigned checkout; preserve unrelated changes.
- Commits, if made, use the `fb1:` prefix and are not pushed.
- Repository tools never name lane-workspace or external-corpus paths.
- Done means the producer self-test, fixture validator, registry checks,
  artifact ergonomics checks, focused tests, and `tools/check_regressions.py`
  all pass; `git diff --check` is clean; the report separates candidate,
  unresolved, and nonclaims.

## Execution steps

1. Add the design and this plan; inspect F-A, lattice-registry, and harness
   contracts. Record the baseline branch and clean state.
2. Add red-first unit/fixture tests for exact span reconstruction, ordinary
   clitic compositions, protective-nūn typing, idghām A/B acceptance and C/D
   abstention, the closed-class guard, spurious-root rejection, and `لا`/`إلا`
   ambiguity. Run them before the producer exists and retain the failing
   evidence.
3. Implement the producer with pure row processing, typed unresolved records,
   deterministic fact IDs, explicit evidence modes, registered predicate and
   guards, and a `--self-test` command. Add the small fixture corpus and F-A
   output validation.
4. Select and run the real >=40-row family sample from explicit STRAT/verdict/
   corpus CLI paths. Commit only the bounded fixture input and the resulting
   typed calibration output, never the external corpus.
5. Write `docs/reports/history/2026-07-16-FB1-REPORT.md` with the per-row table, abstention arithmetic,
   zero-false-projection attestation basis, and exact nonclaims. Wire the FB1
   self-test/fixture gate into the regression harness.
6. Run focused tests, F-A validation, registry and ergonomics validators, then
   the full regression harness. Review the diff, check path hygiene and
   whitespace, and commit the coherent change with an `fb1:` message.

## Rollback / escape hatch

All generated packet files are bounded and reversible. If a guard or sample
selection is wrong, regenerate the committed fixture/output/report from the
explicit CLI inputs; do not widen to corpus-wide output or edit public data.
