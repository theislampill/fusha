# Qamus Mode A Thin Slice Report

Date: 2026-07-01

Branch: `feature/fusha-standalone-parser-qamus-kernel`

Scope: repository fixture and tooling only. No live Qamus mutation, SSH deployment, whitelist append, service restart, commit, push, or live coverage claim.

## Result

The P0.5 Mode A slice is implemented as a local CLI/JSONL contract and fixture validator.

It proves this narrow loop:

`visible qword -> source-address row -> minimal morphology/syntax -> public hover projection -> private trace -> bidirectional edge manifest -> rendered/readback fixture -> flywheel artifact -> claim validator`.

It does not prove arbitrary-text parsing, full Classical Arabic NLP, or live Qamus closure.

## Implemented Tools

- `tools/fusha_mode_a.py`: materializes Mode A fixture artifacts from source-address rows.
- `tools/fusha_analyze_token.py`: analyzes one source-addressed token row.
- `tools/fusha_analyze_card.py`: analyzes a JSONL card/worklist.
- `tools/fusha_project_hover.py`: projects analysis rows into public-safe hover rows.
- `tools/validate_qamus_mode_a_adoption.py`: validates the P0.5 bundle.
- `tools/validate_source_artifact_ledger.py`: validates the canonical ledger.
- `tools/validate_artifact_freshness.py`: validates freshness/retirement metadata.
- `tools/validate_human_review_packet.py`: validates owner/scholar packet shape.

## Implemented Fixture

The fixture source rows live in:

`qamus/examples/mode_a_thin_slice/source-address-rows.jsonl`

Smoke families:

- `n0005_all_qword_card`: 12 rows, every visible qword on the 2:98 card.
- `v100_am_lahum_particle_cluster`: 2 rows for `أَمْ لَهُمْ`.
- `p011_verb_prefix_stem_subject`: 1 row for `تَعْبُدُوا۟`.
- `p018_participle_prefix_plural_suffix`: 1 row for `ٱلْمُبْطِلُونَ`.
- `p050_vocalized_interrogative_particle`: 1 row for `أَيَّانَ`.

Generated fixture artifacts:

- `analysis.jsonl`
- `public-hover-projection.jsonl`
- `private-trace.jsonl`
- `source-edge-manifest.jsonl`
- `rendered-readback.fixture.jsonl`
- `flywheel-artifacts.jsonl`
- `claim-validation-report.json`

## Validated Guarantees

The Mode A validator checks:

- public boundary is source-clean;
- no public source/path/process leakage;
- segment surfaces concatenate to the visible qword;
- qg classes are allowlisted;
- full-card denominators are honored when declared;
- vocalization-required rows/cards contain Arabic diacritics;
- each row has private trace, decision backlink, forward trace, reverse trace, rendered fixture, and flywheel route;
- rendered fixture text equals the visible qword;
- the report remains fixture-only and cannot be mistaken for a live coverage claim.

## Claim Boundary

This is a local candidate/validation substrate.

Allowed claims:

- fixture-level Mode A vertical slice exists;
- five ANDON families are represented by source rows and validator checks;
- local CLI/JSONL consumer contract exists for future Qamus workers.

Forbidden claims:

- live Qamus progress;
- VN tranche closure;
- arbitrary-text grammatical correction;
- CAMeL/MADAMIRA/Stanza-equivalent morphology, disambiguation, or dependency parsing;
- source-address certainty for arbitrary text.

## Why This Matters For The Rollout

The prior rollout failure mode was treating deploy packets, selected-row counts, and boards as page closure while visible words remained sparse or uncolored.

This slice makes the denominator explicit:

- a visible qword must have a source-address row;
- a public hover must have a private trace and reverse edge;
- qg segments must preserve morphology rather than hiding pieces in the host;
- a card declared all-qword must account for every visible qword;
- missing vocalization is a visual-closure defect, not a cosmetic afterthought.

## Next Gates

Before broad P1/P2 parser work:

1. Add more all-qword cards from VN-00/VN-01/VN-02 to the same contract.
2. Add source-crosswalk rows where display-local and canonical locs differ.
3. Convert repeated owner/scholar decisions into fixtures and validators.
4. Extend the minimal morphology table only after new cases pass the Mode A validator.
5. Keep live deployment serial in the rollout executor; this repo produces candidates and gates only.
