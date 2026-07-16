# F-A Typed-Claim Contract Report

## Outcome

F-A is implemented as an additive, versioned authoring boundary for projection
inputs. The governed contract is `qamus.typed_claim_contract.v1` at contract
version `1.0.0`. A learner-visible candidate claim must bind to one or more
governed facts; the validator emits the exact failure text:

`learner-visible claim lacks backing typed fact: a prose assertion is not itself a typed fact`

The tranche-1 canary remains candidate-only and reuses its existing source-row
and fact lineage. No linguistic certification transition was performed.

## Built

- Added the closed governed contract schema in
  `qamus/schemas/typed-claim-contract.schema.json`. Each governed fact requires
  occurrence identity, typed fact value, exact surface spans, primary and
  secondary ownership, source/address, certification, evidence/confidence,
  producer/version, rule/projector/version, guards, defeaters, unresolved
  blockers, and dependent fact/projection ids. The projection envelope requires
  typed fact bindings for learner-visible candidate claims.
- Added additive `governed_contract_ref` carriers to the seven tranche-1
  schema surfaces without changing their existing required fields.
- Added `tools/typed_claim_contract.py` and
  `tools/validate_typed_claim_contract.py` for schema, join, span, lineage,
  alias, legacy, and unresolved-language validation.
- Added red/green fixtures under `qamus/examples/fa-contract/`: the real
  prose-only row shape rejects, the tranche-1 `3:141:4` canary passes, the
  alias fixture normalizes `qg-negative` to `qg-negation`, the Q6-4 legacy
  record is internal-only, and the five Q6-7 unresolved statuses map to typed
  English learner statements.
- Added `qamus/schemas/legacy-valid-record.schema.json` and
  `qamus/schemas/unresolved-language-map.schema.json`.
- Added the F-A self-test and fixture checks to `tools/check_regressions.py`
  following the gate-14 subprocess/check pattern.
- Recorded the implementation design and execution plan in
  `docs/superpowers/specs/2026-07-16-fa-typed-claim-contract-design.md` and
  `docs/superpowers/plans/2026-07-16-fa-typed-claim-contract.md`.

## Verbatim validator results

Command:

```text
python tools/validate_typed_claim_contract.py --self-test
FA TYPED-CLAIM CONTRACT SELF-TEST PASS (1 governed, 1 prose rejected, 1 legacy internal, 1 aliases normalized, 5 unresolved mappings)

python tools/validate_typed_claim_contract.py --fixtures qamus/examples/fa-contract
FA TYPED-CLAIM CONTRACT FIXTURES PASS (1 governed, 1 prose rejected, 1 legacy internal, 1 aliases normalized, 5 unresolved mappings)
```

The tranche-1 precedent validator also returned:

```text
TRANCHE1 VALIDATION PASS
PASS - schema validation: all typed fixture rows conform
PASS - exact source surface and segment parity: 8/8
PASS - exact gloss_contribution/class to gloss/qg_class mapping: 4/4 candidates
PASS - row/hash round trip: 8/8 source and output hashes recompute
PASS - routing: 4 candidate projections + 4 typed queue records
PASS - DOM consumption expectations: 4 consume + 4 abstain; live assertions 0
PASS - same-surface adversary: segmented candidate + fused unresolved
PASS - live mutation authorization: 0
SUMMARY canonical=8 candidates=4 queued=4 errors=0
```

## Verbatim full-harness result

Command:

```text
python tools/check_regressions.py
```

Exit code: `0`. The final full run completed in `238 seconds`; its final F-A and
terminal lines were:

```text
ok   F-A typed-claim contract self-test and red-first fixtures pass
ok   F-A typed-claim contract fixture boundary passes

ALL REGRESSION CHECKS PASS
```

The focused F-A suite returned:

```text
Ran 9 tests in 0.008s

OK
```

Additional completed checks: `python tools/check_artifact_ergonomics.py`
returned `ARTIFACT ERGONOMICS OK — all committed artifacts reviewable/diffable`;
`git diff --check` returned no output; Python compilation returned exit code 0;
and schema coherence returned `ALL SCHEMA COHERENCE CHECKS PASS`.

## Diff summary

- New: three governed schemas, three validator/test modules, six F-A fixture
  artifacts, and this report.
- Modified additively: seven existing qamus schemas and
  `tools/check_regressions.py`.
- No changes to whitelist data, renderer code, DOM fixtures, deployment
  surfaces, or live-site artifacts.
- The working branch is `andon-fa-contract`; commits are prefixed `fa:` and no
  push was performed.

## EXACT NONCLAIMS

- This lane does not claim that the tranche-1 canary is linguistically
  certified. It remains a candidate with low/source-addressed-candidate
  evidence.
- This lane does not claim a complete QG alias registry reconciliation. The
  alias table is intentionally minimal and currently covers only
  `qg-negative` -> `qg-negation`.
- This lane does not claim that legacy records are learner-visible,
  public-materializable, or equivalent to governed facts. `legacy_valid` is an
  internal upgrade record only.
- This lane does not claim whitelist append, renderer integration, DOM/live
  readback, SSH, deployment, publication, approval, or production mutation.
- This lane does not fabricate Arabic morphology, syntax, glosses, source
  evidence, owner decisions, or producer output. It validates supplied typed
  facts and routes missing evidence to explicit unresolved language.
