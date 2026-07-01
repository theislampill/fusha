# Qamustyping3 Implementation Handoff

Qamustyping3 implements a safe parser/checker substrate for Fusha and Qamus
Mode A work. It is not live Qamus, not arbitrary-text, and not a trained
dependency parser.

The implementation exists to keep future workers from confusing planning,
boards, packets, or selected-word closure with actual all-qword visual closure.

## Implemented Now

- canonical source ledger and freshness policy
- local CLI contract, not an HTTP endpoint
- P0.5 thin end-to-end Mode A fixture
- morphology smoke database and generator/reinflection tools
- rule-ranked disambiguation, dependency, and i'rab smoke tools
- all-qword fixture rows for known Qamus ANDON families
- eval and claim-boundary gates
- qamustyping3 acceptance validator

## Not Implemented Yet

- live Qamus deployment
- VN tranche closure
- broad Classical Arabic lexicon
- broad morphology generator
- statistical disambiguator
- trained dependency parser
- arbitrary-text certification
- runtime API endpoint

## Why This Matters For Qamus

The rollout target is every visible word on every cited Qamus example card, not
only the selected dictionary token and not only the draft-gloss counter. The
all-qword fixture makes that denominator explicit before live deployment.

Each candidate must preserve both directions:

```text
entry/card/source -> visible qword -> canonical loc/crosswalk -> public hover
public hover -> canonical loc/crosswalk -> visible qword -> entry/card/source
```

Rows that cannot preserve this graph must route to an exact packet:

- owner
- scholar/i'rab
- source-crosswalk
- compiler/template
- renderer/qg
- validator/schema

## Screenshot-Derived Regression Families

The current smoke surfaces encode these recurring failures:

- n0005: every visible qword on one card must be represented.
- v100: function particles and clusters such as `أَمْ لَهُمْ` are grammar-bearing.
- p011: finite verbs expose prefix, stem, and subject marker.
- p018: participles expose article, derivative prefix, stem, and plural suffix.
- p050: "complete" pages can still fail if vocalization/readback drifts.

## Use In Future Executor Threads

Before authoring broad rows or opening broad residual threads, run:

```bash
python tools/validate_qamustyping3_acceptance.py --self-test
python tools/validate_qamus_mode_a_adoption.py --self-test
python tools/validate_fusha_morph_db.py --self-test
python tools/validate_fusha_parser_baseline.py --self-test
python tools/validate_parser_claims.py --self-test
```

Then consume the CLI contract in `docs/parser/fusha-cli-contract.md`.

Do not treat these checks as live coverage. They prove only that the repo can
produce and validate source-clean fixture artifacts for safe downstream use.
