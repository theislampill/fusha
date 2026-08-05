# FAM4 finite-verb producer calibration implementation plan

> **Execution note:** This plan is executed in the existing linked checkout
> `andon-fam4-finite-verbs`; the user pre-approved the design and requested
> completion without an approval pause.

## Goal

Build and verify a candidate-only, abstention-first finite-verb producer for
all 12 `finite_verbs` rows, with source-addressed typed facts, typed routes,
RED-first fixtures, a committed packet/report, and a full harness gate.

## Constraints

- Work only in this linked checkout; do not push, publish, or mutate the
  read-only corpus.
- Keep `derived_verbs` owner-gated and do not analyze derived forms.
- Reuse F-A/FAM2 carriers; do not add a parallel pipeline.
- Treat labels and whitelist entry IDs as non-evidence until exact entry-form
  and letter-level checks pass.
- Keep all public/live materialization flags false and preserve exact N-LANG
  labels.

## Tasks

### 1. Add RED-first fixtures and focused tests

Files: `qamus/examples/fam4-finite-verbs/entry-fixtures.jsonl`,
`producer-fixtures.jsonl`, `verb-affix-registry.jsonl`,
`weak-root-defeater-registry.jsonl`, and
`tools/test_fam4_finite_verb_producer.py`.

Write tests that initially fail because the producer module and validator do
not yet exist. Cover six sound Form-I candidates, a subject suffix and an
object suffix, and the required adversarial routes.

Run:

```text
python -m unittest tools.test_fam4_finite_verb_producer -v
```

Expected first state: import/fixture failure (RED), captured before the
implementation is added.

### 2. Implement the producer and typed contract validator

Files: `tools/fam4_finite_verb_producer.py`,
`tools/validate_fam4_finite_verbs.py`, and `tools/fact_projectors.py`.

Implement caller-supplied JSONL loading, exact entry-form indexing,
annotation-only matching, Form-I registry matching, radical/affix span
reconstruction, weak-root and derived-form defeaters, typed pending records,
candidate-only learner payloads, packet construction, and record validation.

Run the focused tests and fixture self-test after implementation. Expected
result: GREEN with all required blockers and no candidate claims on negative
fixtures.

### 3. Build the 12-row packet and report

Files: `tools/build_fam4_report.py`,
`qamus/examples/fam4-finite-verbs/generated/*`,
`qamus/examples/fam4-finite-verbs/README.md`, and `docs/reports/history/2026-07-17-FAM4-REPORT.md`.

Run the producer with explicit lane inputs and read-only corpus paths. Commit
only typed packet outputs, the per-row survey, precision/abstention summary,
and the rendered report. The packet must retain all 12 rows in location order.

### 4. Wire repo-local gates

File: `tools/check_regressions.py`.

Add FAM4 self-test, focused unit-test, and committed-packet checks beside the
existing family gates. Keep the harness independent of external corpus paths
so a repo-only run validates the fixtures and packet.

### 5. Verify and close

Run focused tests, fixture self-test, packet validation, report generation,
`git diff --check`, tracked-image/RM-09 scans, and the full regression harness
with a bounded long timeout. Re-run any failed check after repair, inspect the
final diff and status, then commit with a `fam4:` subject. No push.

## Done when

All 12 production rows have a typed candidate or typed route; the required
fixtures and report are committed; all FAM4 gates and the full harness pass;
all outputs remain candidate-only; and the final commit is present on
`andon-fam4-finite-verbs`.
