# Qamus Mode A Parser Stack Report

Date: 2026-07-01

Status: dependency-free fixture smoke implementation.

This report is not live Qamus progress, not arbitrary-text certification, and not a trained NLP model claim.

## Implemented Layers

- P0/P0.5: source-addressed Mode A thin slice, public/private projection, edge manifest, rendered/readback fixture, and flywheel artifact.
- P1: small repo-authored morphology database with analyzer, generator, reinflector facade, validator, and smoke eval.
- P2: transparent rule-ranked disambiguation and dependency/iʿrāb candidate baseline with abstention on unknown surfaces.
- P3: Mode A adoption procedure and curriculum regression fixture.
- P4: source/eval ledger extension, frozen split manifests, model card, eval report, and claim-boundary validator.

## Claim Boundary

Allowed claim:

The repo now has a runnable, source-clean, dependency-free smoke substrate for Qamus Mode A parser/checker work.

Forbidden claim:

It is not a full Classical Arabic Grammarly, not a trained dependency parser, not a broad morphological generator, and not evidence of live qamus.dawah.wiki coverage.

## Executor Use

Qamus rollout workers can consume this as a local contract:

```powershell
python tools\validate_qamus_mode_a_adoption.py --self-test
python tools\validate_fusha_morph_db.py --self-test
python tools\eval_fusha_morphology.py --self-test
python tools\validate_fusha_parser_baseline.py --self-test
python tools\validate_fusha_evaluation.py --self-test
python tools\validate_parser_claims.py --self-test
```

Passing these checks proves only the local fixture substrate. Live deployment still requires the rollout executor's source/runtime, DOM/readback, health, and owner/scholar gates.
