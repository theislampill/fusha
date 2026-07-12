# Transclusion (Meta-Transclusive Lattice Projection)

> ## ⚠ Defect / validation-posture box (read first)
>
> Transclusion "accepted" is **support evidence, not visual closure.**
> - The largelexicon tables ship in a **schema-migration validation posture**: `RELEASE.json`
>   reports every table `validation.pass_rows: 0` with `violation_rows == row_count`
>   (`#tables.*.validation`). This is expected for the v1→v2 migration, but it means a table being
>   "present" is NOT a claim that its rows passed the target-schema gate.
> - An accepted crosswalk row (`canonical_crosswalk_accepted`) is **internal support evidence only**.
>   It does not make a page visually complete and does not authorize a public hover by itself.
> - Closure is owned by the executor (hover payload generation, qg colour projection, sarf/nahw
>   validation, source/runtime deploy, desktop/mobile readback, rollback). See the False-Closure Rule.

Fusha/Qamus transclusion has two layers.

1. **Source-address transclusion** — the same visible Qurʾānic qword occurrence is identified by
   stable entry/card/qword handles and, when available, canonical `quran:S:A:W` / `wbw:S:A:W`
   addresses. Reuse must be **loc-first**: `qword_row_id` and accepted canonical locs are binding
   keys. Surface-only keys (`missing-loc|...`, `sarf:surface:...`) are diagnostic labels, not reuse
   authority.
2. **Meta-transclusive lattice projection** — sarf, nahw, typed-edge, source-edge, and renderer facts
   form a reusable lattice. If one occurrence has a richer source-clean fact (root, prefix, suffix,
   particle function, case/tanwīn explanation, peer payload), every equivalent occurrence must either
   project that fact into public hover/colour or carry an exact exception.

This is not optional ornament. It is the anti-false-closure contract for rollout work.

## Accepted crosswalk rows (current counts)

`qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json` is a source-clean support table.
Rows with both canonical locs are `canonical_crosswalk_accepted`; rows without canonical locs remain
`source_crosswalk_packet_ready`.

- Accepted:
  `qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json#status_counts.canonical_crosswalk_accepted` (read live — moves per promotion wave; not transcribed here)
- Demoted:
  37
- Source-crosswalk packet-ready:
  `qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json#status_counts.source_crosswalk_packet_ready` (read live — moves per promotion wave; not transcribed here)

<!-- Historical: the 2026-07-03 ADOPTION snapshot was 85,877 accepted / 31,240 packet
     (`…#adoption.evidence_counts`). The live status_counts above supersede it after the two-vote/lane-A wave-3 promotions (generated 2026-07-11). Raw executor paths and external source names are never committed. -->

## Projection queue shape

Plan18 queue rows come in two valid shapes:

- **exact rows** — include `qword_row_id`, `exact_transclusion_group_key`, or `public_payload_hash`;
- **family-summary rows** — include `loc=multiple`, `example_pages`, `proposed_file_or_queue`; an
  index to recurring failure classes only.

Family summaries are **not** closure packets. Required recurring families:
`source_clean_fact_available_but_not_projected`, `function_token_flat`,
`peer_payload_richer_than_current`, `object_or_possessive_suffix_hidden`, `root_known_but_hidden`,
`finite_prefix_hidden`.

```powershell
python tools\validate_meta_transclusion_projection.py --self-test
python tools\validate_largelexicon_transclusion.py
```

Use `--require-exact-rows` only when claiming row-level closure readiness; it fails if a required
family is represented only by a family-summary row.

## False-closure rule

A page is **not** visually complete when any public qword has: a known root/stem not shown where the
hover claims morphology; a hidden finite prefix, derivative prefix, suffix pronoun, subject suffix, or
sound-plural ending; a function token still flat/uncoloured despite a known nahw role; a richer
same-address/same-lattice peer payload not projected; or a source-clean fact available internally but
absent from public hover/colour. The executor may deploy small batches serially, but the
learning/flywheel layer must convert every repeated miss into a sarf/nahw/validator/parser/curriculum/
drill or exact source-crosswalk packet.
