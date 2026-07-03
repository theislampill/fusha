# Meta-Transclusive Lattice Projection

Fusha/Qamus transclusion has two layers.

1. **Source-address transclusion**: the same visible Qur'anic qword occurrence is
   identified by stable entry/card/qword handles and, when available, by
   canonical `quran:S:A:W` / `wbw:S:A:W` addresses. Reuse must be loc-first:
   `qword_row_id` and accepted canonical locs are binding keys. Surface-only
   keys such as `missing-loc|...` or `sarf:surface:...` are diagnostic labels,
   not reuse authority.
2. **Meta-transclusive lattice projection**: sarf, nahw, typed-edge,
   source-edge, and renderer facts form a reusable lattice. If one occurrence
   has a richer source-clean fact for root, prefix, suffix, particle function,
   case/tanwin explanation, or peer payload, every equivalent occurrence should
   either project that fact into public hover/color or carry an exact exception.

This is not optional ornament. It is the anti-false-closure contract for
rollout work.

## Accepted Crosswalk Rows

`qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json` is a
source-clean support table. Rows with both canonical locs must be
`canonical_crosswalk_accepted`; rows without canonical locs remain
`source_crosswalk_packet_ready`.

Accepted rows are internal support evidence only. They are not live Qamus
progress and not sufficient for visual closure. The executor still owns public
hover payload generation, qg class/color projection, sarf/nahw validation,
source/runtime whitelist deployment, desktop/mobile readback, and rollback.

The 2026-07-03 adoption projected the reviewed crosswalk packet into the
committed shards:

- `85877` rows accepted as canonical crosswalk support;
- `31240` rows retained as exact source-crosswalk packets;
- raw executor paths and external source names are not committed.

## Projection Queue Shape

Plan18 queue rows come in two valid shapes:

- exact rows: include `qword_row_id`, `exact_transclusion_group_key`, or
  `public_payload_hash`;
- family-summary rows: include `loc=multiple`, `example_pages`, and
  `proposed_file_or_queue`, and serve only as an index to recurring failure
  classes.

Family summaries are not closure packets. An executor may use them to spawn
page workers or build fixtures, but cannot call a page complete from a summary.

Required recurring families include:

- `source_clean_fact_available_but_not_projected`;
- `function_token_flat`;
- `peer_payload_richer_than_current`;
- `object_or_possessive_suffix_hidden`;
- `root_known_but_hidden`;
- `finite_prefix_hidden`.

Run:

```powershell
python tools\validate_meta_transclusion_projection.py --self-test
python tools\validate_meta_transclusion_projection.py `
  --queue qamus\reports\vn00-public-andon-20260703\plan18-meta-lattice-projection-queue.jsonl `
  --typed-edge-queue qamus\reports\vn00-public-andon-20260703\plan18-typed-edge-transclusion-queue.jsonl
```

Use `--require-exact-rows` only when an executor is claiming row-level closure
readiness; it intentionally fails if a required family is represented only by a
family-summary row.

## False Closure Rule

A page is not visually complete when any public qword has:

- known root/stem not shown where the hover claims morphology;
- hidden finite prefix, derivative prefix, suffix pronoun, subject suffix, or
  sound plural ending;
- function token that remains flat/uncolored despite a known nahw role;
- richer same-address or same-lattice peer payload not projected;
- source-clean fact available internally but absent from public hover/color.

The executor may deploy small batches serially, but the learning/flywheel layer
must convert every repeated miss into a sarf, nahw, validator, parser,
curriculum, drill, or exact source-crosswalk packet.
