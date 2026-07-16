# F-A Typed-Claim Contract Design

## Goal

Add an additive, versioned contract that makes every typed fact used by a learner-facing projection source-addressed, span-bound, owned, evidence-qualified, producer/projector-bound, and fail-closed at the authoring boundary.

## Scope and boundaries

- The contract is fixture/compiler infrastructure only; it does not certify Arabic facts.
- Existing tranche-1 schemas and validators remain valid. New contract references are optional carriers in existing schemas; the new governed schema is stricter than the historical schemas.
- A learner-visible claim must bind to one or more governed typed fact IDs and named fact fields. Prose, morphline, labels, and notes are explanatory output, never fact identity.
- Alias normalization happens on ingestion. The minimal extensible table maps `qg-negative` to `qg-negation`; deprecated aliases are forbidden in normalized/generated output.
- `legacy_valid` records are internal compatibility records and are never learner-visible or live-materialized.
- Unresolved statuses use a versioned, typed internal-to-English mapping consumed by the validator/projection helper. The mapping does not resolve a linguistic fact.
- No whitelist, renderer, CSS, live app, applier, source corpus, or production data is changed.

## Contract shape

`qamus.typed_claim_contract.v1` is a closed JSON object with `contract_version: 1.0.0`, a canonical occurrence identity, an array of governed typed facts, and an optional projection envelope.

Each governed fact requires:

1. a stable `fact_id` and `fact_type`;
2. exact whitespace-free surface spans using Unicode code-point offsets plus the original span text;
3. required primary ownership and an explicit secondary-owner array;
4. source identity and an exact source address;
5. certification status and confidence/evidence status;
6. producer ID/version and a rule/projector ID/version;
7. explicit guards, defeaters, unresolved blockers, dependent fact IDs, and dependent projection IDs.

The projection envelope records status, materialization target, learner visibility, and either a learner claim with fact-field bindings or an unresolved-language statement. A learner claim is invalid when it has no fact binding, references an absent fact, references an absent field, or uses a span not covered by the fact.

## Compatibility and normalization

The tranche-1 carrier schemas gain optional `governed_contract_ref` objects with contract version and fact IDs; their existing required arrays are unchanged. The validator accepts governed contract envelopes and gives a specific prose-only error for a historical projection-shaped object that has learner text without governed fact bindings.

`tools/typed_claim_contract.py` owns the alias table, recursive input normalization, JSONL helpers, unresolved language lookup, and semantic checks. It never mutates input objects in place. Output builders call the same normalizer before writing, and a final scan rejects deprecated IDs.

## Internal compatibility and learner language

`qamus.legacy_valid_record.v1` requires `projection_status`, `legacy_reason`, `unresolved_fact_ids`, `blocked_spans`, `upgrade_route`, `evidence_status`, `learner_visible: false`, and `public_materialization_allowed: false`. The validator rejects any learner claim attached to this record.

`qamus.unresolved_language_map.v1` maps `unresolved`, `source_gap`, `producer_pending`, `syntax_pending`, and `blocked` to plain-English learner statements. It rejects duplicate statuses, internal jargon in statements, and missing coverage for a public unresolved status. `legacy_valid` is intentionally excluded from public mapping because it is internal-only.

## Validation and harness

`tools/validate_typed_claim_contract.py` exposes a reusable `validate_contract_record()` function and a CLI. Its self-test is red-first: the prose-only fixture must fail, the tranche-1 canary-derived governed fixture must pass, alias output must be canonical, the legacy fixture must remain internal, and every unresolved status must map to an English statement. A dedicated harness block follows the gate-14 pattern with a self-test and a real fixture validation invocation.

## Verification

The focused unit tests run before implementation and after each contract component. Final verification includes the contract self-test, fixture validation, relevant tranche-1 validators, artifact ergonomics, `git diff --check`, and a fresh `python tools/check_regressions.py` invocation. Any timeout or pre-existing failure is reported as unverified rather than reclassified as a pass.

## Exact nonclaims

This design does not certify roots, lemmas, forms, plural relations, case, mood, governors, attachments, referents, colors, public rendering, live behavior, deployment readiness, whitelist correctness, or any corpus-wide coverage percentage.
