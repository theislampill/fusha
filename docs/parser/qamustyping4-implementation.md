# qamustyping4 implementation closure

This document records the qamustyping4 implementation boundary for the Fusha
repo. It is intentionally stricter than the qamustyping3 smoke substrate.

## Current claim

Fusha now has a source-controlled qamustyping4 acceptance layer over the existing
Mode A fixtures, morphology smoke database, rule-ranked disambiguation baseline,
dependency/i'rab smoke baseline, all-qword regression fixtures, and claim
validators.

This is not live Qamus progress. It does not mutate the live site. It is not an
HTTP endpoint. It is not yet a CAMeL Tools, MADAMIRA, Stanza, or Grammarly
equivalent.

## Why the stronger claim is gated

The qamustyping4 plan asks for a genuine Classical/Fusha NLP stack. That stack
requires evidence beyond smoke fixtures:

- source-ledgered corpora and license decisions;
- train/dev/test splits;
- broad morphology coverage and generation metrics;
- disambiguation accuracy and calibration;
- dependency/i'rab gold data and wrong-reason metrics;
- arbitrary-text overcorrection and abstention metrics;
- model or rule cards for each component.

The repo can implement deterministic rule baselines and validators now. It
cannot truthfully claim a trained statistical disambiguator or broad dependency
parser until those artifacts exist.

## What changed for qamustyping4

- Added a qamustyping4 implementation ledger:
  `qamus/reports/qamustyping4-implementation-ledger.json`.
- Added all-qword regression fixtures for the observed sparse-page and missing
  color/hover families:
  `qamus/examples/mode_a_all_qword/qamustyping4-regression-worklist.sample.jsonl`
  and `qamus/examples/mode_a_all_qword/qamustyping4-visual-readback.fixture.jsonl`.
- Added a qamustyping4 evaluation matrix:
  `fusha/parser/eval/qamustyping4-eval-matrix.json`.
- Added a qamustyping4 acceptance validator:
  `tools/validate_qamustyping4_acceptance.py`.
- Extended the claim validator so qamustyping4 docs and reports are checked.

## All-qword regression families

The qamustyping4 fixture layer explicitly covers:

- `p011`: verb prefix/stem/subject-marker coloring and governed imperfects;
- `p014`: noun/proper form review where a hidden segment or POS error is
  suspected;
- `p016`: imperfect prefix plus plural subject marker;
- `p018`: article + participle prefix + stem + plural suffix;
- `p050`: missing-diacritic completion bug;
- `n0005`: draft-gloss count confused with rich hover/color completion;
- `n0100`: proper-name/no-fake-root rows;
- `v033`: sparse page rows involving preposition + host/pronoun;
- `v100`: function-token cluster and attached object-pronoun rows.

These are fixture checks, not live readbacks. They are meant to prevent future
agents from saying a page is complete because selected rows or packets exist
while visible qwords remain uncolored or hoverless.

## ANDON closure

The apparent blocker was the phrase "deliver all plans completely." Under
implementaudit, the blocker is not a reason to give up; it is routed into exact
terminal outcomes:

- implemented now: claim gates, source ledger checks, smoke morphology,
  rule-ranked disambiguation, dependency/i'rab smoke baseline, all-qword
  regression fixture, release/handoff validator;
- deferred with gate: broad morphology database, statistical disambiguator,
  trained dependency parser, arbitrary-text Grammarly equivalence;
- executor-owned: live Qamus deployment and public readback.

## Required verification

Run:

```powershell
python tools/validate_qamustyping4_acceptance.py --self-test
python tools/validate_qamustyping3_acceptance.py --self-test
python tools/validate_source_artifact_ledger.py --self-test
python tools/validate_fusha_morph_db.py --self-test
python tools/validate_fusha_parser_baseline.py --self-test
python tools/validate_fusha_evaluation.py --self-test
python tools/validate_parser_claims.py --self-test
python tools/validate_fusha_standalone_parse.py --self-test
git diff --check
```

## Qamus executor handoff

The Qamus executor should consume qamustyping4 as local Fusha tooling only:

1. Pull the Fusha branch or merge result after owner approval.
2. Run the qamustyping4 acceptance validator before using the artifacts.
3. Use the all-qword regression fixture as a minimum page-closure sanity set.
4. Do not treat fixture pass as live coverage.
5. Do not deploy any row that fails public/private boundary, qg class,
   segment-concat, source-address, clitic/function-token, or visual closure
   gates.
6. Route unresolved rows to exact owner, scholar/i'rab, source-crosswalk,
   compiler/template, renderer/qg, or validator/schema packets.
