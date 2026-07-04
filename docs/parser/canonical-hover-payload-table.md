# Canonical Hover Payload Table Contract

This is the Fusha-side contract for replacing copy-per-occurrence RH-LIVE hover
rows with a transclusive, source-addressed payload layer. It is not a live
Qamus deployment format yet.

## Purpose

The public Qamus whitelist currently stores full authored payloads per
occurrence. That is safe but slow: when a shared token family is repaired, every
occurrence must be found and rewritten. The canonical table splits the model:

- canonical payload: the authored hover body;
- occurrence binding: the source-addressed place where that payload is used;
- exception: an explicit page-local override with a recorded reason.

This keeps Project-Xanadu-style transclusion honest: a repair to a canonical
payload can propagate to all bound occurrences, while true contextual exceptions
stay visible and auditable.

## Canonical Payload Row

Required fields:

- `canonical_payload_id`: sha256-truncated hash over the canonical public body.
- `schema`: `qamus/canonical-hover-payload@1`.
- `public_boundary`: exactly `{ "src": "qamus", "kind": "authored", "lang": "en" }`.
- `token_contribution_gloss`.
- `morphline`.
- `segments`.
- `learner_explanation`.
- `source_clean_fact_hash`: hash over the source-clean Fusha facts used to
  author the payload.
- `lemma_status`: one of `exact`, `inferred`, `candidate`, `missing`,
  `conflict`, `blocked`.

The hash input must exclude private evidence labels, MCP names, local paths,
source-photo paths, and process prose.

## Occurrence Binding Row

Required fields:

- `occurrence_id`: stable source-address binding id.
- `source_key`.
- `entry_id`.
- `card_id`.
- `quran_loc`.
- `wbw_loc`.
- `visible_surface`.
- `visible_surface_norm_strict`.
- `exact_transclusion_group_key`: `quran:S:A:W|normalized-surface`.
- `canonical_payload_id`.
- `public_payload_hash`: hash of the rendered public payload for readback.
- `source_sha`: lookup/denominator source hash used by the compile.

Forbidden identity fields:

- raw `qword_index` as a binding key;
- loc-free `missing-loc|...` binding keys;
- surface-only `sarf:surface:...` binding keys.

## Exception Row

An occurrence may override the canonical payload only when it carries:

- `exception_reason`: `contextual_function`, `homograph`, `different_lemma`,
  `different_governor`, `phrase_context`, `owner_override`,
  `scholar_irab_override`, or `source_repair_pending`;
- `review_route`: `sarf`, `nahw`, `owner`, `scholar_irab`, `source_crosswalk`,
  or `validator`;
- `evidence_backlink`: private/internal pointer, never rendered publicly.

## Whitelist Compile Step

The future live compile step sits between WBW artifact build and runtime deploy:

1. read denominator/crosswalk rows;
2. read canonical payload rows;
3. read occurrence bindings and exception rows;
4. validate loc-first joins with `tools/validate_largelexicon_denominator_join.py`;
5. render the current public whitelist;
6. stamp the whitelist with the same `source_sha` family as `wbw-lookup.json`;
7. verify byte-identical output for identical inputs.

Same source tables plus same canonical payload table must produce byte-identical
whitelist output.

## Gates

Minimum gates before adopting this as a live compiler:

- `tools/validate_largelexicon_qword_crosswalk.py`.
- `tools/validate_largelexicon_denominator_join.py`.
- `tools/validate_largelexicon_transclusion.py`.
- `tools/validate_meta_transclusion_projection.py`.
- source-clean public leak scan.
- duplicate same-loc conflict check.
- public DOM readback after any live deployment.

## Machine-checkable schemas (added 2026-07-04, compiler Task 1-2)

The row types above are now formalized as JSON schemas and enforced by a validator
wired into the regression gate (validator-BEFORE-builder — the safety property):

- `qamus/schemas/canonical-hover-payload.schema.json`
- `qamus/schemas/canonical-hover-occurrence-binding.schema.json`
- `qamus/schemas/canonical-hover-exception.schema.json`
- `tools/validate_canonical_hover_payload_table.py` (`--self-test` + sample) — enforces
  content-addressed `canonical_payload_id`/`binding_id`/`exception_id`, the source-clean
  leak scan, exact segment-surface concat, the accepted-binding loc requirement, the
  `certified_lemma` gate, and referential integrity. Samples:
  `qamus/examples/canonical_hover_payload.sample.jsonl`.

The builder (`build_canonical_hover_payload_table.py`) and compiler
(`compile_canonical_hover_whitelist_packet.py`) — Tasks 3-4 — are NOT yet implemented;
this substrate is what they will validate against. See CANONICAL_HOVER_PAYLOAD_COMPILER_PLAN
(fablehardening) for the remaining tasks and the Qamus-executor canary (Task 6).

## Claim Boundary

This document defines a contract and compile target. It does not claim that live
Qamus currently uses canonical payload ids. Until the live compiler exists,
runtime whitelist rows remain copy-per-occurrence and must be audited as such.
