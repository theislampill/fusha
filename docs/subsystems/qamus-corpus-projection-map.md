# Corpus occurrence/appearance/projection manifest — consumer/command map

Train D atomic component 1: `tools/build_corpus_projection_manifest.py` builds the
deterministic population spine consumed by later rich-colour/rich-hover batches on
this train. It is a coverage manifest, not a linguistic engine: it grounds every row
in committed repo authority and reports an explicit reason wherever a disposition
cannot be measured from that authority, rather than fabricating closure.

## What it reads (closed authority, read-only)

- `qamus/data/current/entries.jsonl` — 2,092 P/N/V entries.
- `qamus/lattice/example-ayah-universe.jsonl` — 117,117 displayed-token appearances
  (109,471 displayed words + 7,646 pause marks).
- `qamus/lattice/example-ayah-universe.occurrences.jsonl` — 50,041 unique canonical
  occurrences (the appearance-vs-occurrence denominators are never collapsed).
- `qamus/indexes/occurrence-appearances.jsonl` — reader/entry_example surface index;
  the closest committed proxy for live payload/revocation posture.
- `qamus/lattice/particle-occurrence-matrix.jsonl` — candidate particle-function
  relations only. Its matrix IDs are not occurrence-bound Naḥw, colour or hover
  fact identities and never populate those planes.

## What it writes

- Full manifest JSONL (one row per displayed-token appearance): an explicit,
  user-supplied `--output` path, normally under the gitignored `out/` tree. Never
  committed. Deterministic: same committed inputs -> byte-identical output.
- `qamus/reports/corpus-projection-baseline.json` (committed): compact aggregate —
  entry/universe count verification, per-disposition status counts, orthographic
  shape-recall and multi-entry fanout counts, the P009/P099 canary report, the colour/hover identity
  invariant check, and the full output's row count + sha256 (so downstream consumers
  can verify a locally rebuilt `out/` file without the large file being committed).
- `qamus/examples/corpus-projection-manifest.sample.jsonl` +
  `.sample.meta.json` (committed): a deterministic, bounded, order-preserving sample
  (see `sample_selection_rule` in the meta file for the exact selection order).

## Row schema (summary)

Each row carries: entry/page/card/token identity, `canonical_loc` /
`occurrence_id` (or `null` with an explicit alignment `blockers` list), the
`crosswalk`/`match_basis` alignment tier, `selected` vs context scope (never
merged across entries — same surface/root/citation form never creates entry,
sense, or occurrence identity), a `denominators` block preserving the distinct
entry/canonical-occurrence counts, a `particle_function_candidate_refs` nonclaim
list, and a 21-plane `dispositions` object: `appearance_identity`,
`card_owner_binding`, `token_lexeme_binding`, `surface`, `surface_conflict`,
`orthographic_shape_recall`, `morpheme_ownership`, `sarf`, `nahw`,
`particle_function_candidates_at_loc`, `contextual_meaning`, `translation`,
`colour`, `hover`, `cross_plane_conflict`, `reverse_trace`,
`revocation_dependency`, `certification`, `payload`, `live_state`, and
`pending_actions`. `multi_entry_transclusion_fanout` reports shared canonical
locations without calling fanout a page-local factual fork.

Every disposition sub-object always carries `status` + `reason`; there is no
silent `null`/omission — absence of authority is itself an explicit reason
(e.g. `sarf: authority_not_joined_in_closed_inputs` — the whitelist that would
carry per-token sarf/nahw segmentation is not a repo artifact at this stage).

## Commands

```
# Full manifest (ignored, not committed) + committed baseline/sample:
python tools/build_corpus_projection_manifest.py --output out/corpus-projection-manifest.jsonl

# Deterministic rebuild check against an existing --output:
python tools/build_corpus_projection_manifest.py --output out/corpus-projection-manifest.jsonl --check

# Regenerate only the committed baseline/sample (no full output write):
python tools/build_corpus_projection_manifest.py

# Tests:
python tools/test_corpus_projection_manifest.py
```

## Known deficits this manifest surfaces (not fabricated closure)

- `ma_function_disambiguation_deficit` (baseline `canaries`): every P099 (`مَا`)
  occurrence in `particle-occurrence-matrix.jsonl` currently carries the same
  undifferentiated homograph `function_candidates` list — occurrence-bound
  function/hover disambiguation is not yet provable from committed authority.
- `sarf` is `token_class_not_determined` for 105,062 context rows and
  `authority_not_joined_in_closed_inputs` for 4,409 selected-token rows; `nahw`
  is `occurrence_bound_nahw_not_joined_in_closed_inputs` for all 109,471 word
  rows. The particle matrix remains a separate candidate plane.
- `colour` and `hover` are both `not_available` for all 109,471 word rows. Their
  fact IDs are null because no authoritative facts are joined; null/null is not
  parity. The baseline therefore reports 0 `both_present_compared`, 41,739
  `both_absent_not_compared`, 75,378 `candidate_only_not_compared`, and 0
  violations rather than claiming that any word received a rich projection.
- `multi_entry_transclusion_fanout` covers 105 canonical locations / 210 rows at
  the current build. It reports `no_divergent_projection_identity_in_closed_inputs`;
  it neither proves rich projection parity nor invents a page-local fork.

## Consumers

Train A/B fact projectors and the Train D projector/compiler regenerate affected
corpus batches from this manifest's `pending_actions` list and the baseline's
disposition-count deficits; they should re-run the generator against their own
`--output` path and diff against the committed `full_output.sha256` /
`sample_sha256` in the baseline/sample-meta to confirm they are working from the
same population spine.

## Train D component 2 — certified P007 geometry disposition batch

`tools/build_corpus_fact_projection_batch.py` is the first real certified-fact
consumer of this manifest. It selects only the 454
`deterministic-attachment-geometry` rows in
`qamus/lattice/p007-reverse-universe.jsonl`, validates the latest effective state
of all 1,362 facts through the 4,086-event hash-chained certification trail, and
joins the selected locations to the component-1 manifest by exact
`canonical_loc`. The join is appearance-complete: 985 manifest appearances must
equal the reverse-universe appearance sets exactly.

Certification validity and effective state are owned exclusively by
`TypedFactCertificationStore`: the batch calls its `validate_trail()`, `state()`,
and `status_by_id()` APIs. The batch separately checks register-event payload/set
equality against committed `typed-facts.jsonl`; it does not carry a second
transition vocabulary or certification state machine.

The component projects only three fact types:
`attachment_geometry`, `surface_reconstruction_nfc`, and
`token_host_boundary`. Its certification boundary is
`partial_certified_geometry_only`. The component/token span is represented
separately from the whole token and the NFC component + host reconstruction is
rechecked before any row is emitted.

Surface readiness is occurrence-wide, never appearance-local:

- 385 occurrences / 820 appearances are `geometry_projection_ready` because
  every appearance is NFC-identical to the certified reference surface.
- 69 occurrences / 165 appearances are
  `appearance_surface_variant_mapping_required`: 15/50 are mixed-surface and
  54/115 are variant-only. An exact-looking appearance from a mixed occurrence
  remains held with every other appearance of that occurrence.

Every appearance of one occurrence carries one identical geometry projection
hash. The batch does not promote corpus candidate refs into Naḥw, and a card
owner is never treated as the displayed token's lexeme. Its explicit output
boundaries are `boundary_available_no_semantic_colour`,
`not_available_missing_full_token_facts`, zero website payloads, and zero live
outputs. Semantic rich-colour and hover gains therefore remain zero.

Artifacts and commands:

```
# Generate the committed baseline/sample and an ignored full batch.
python tools/build_corpus_fact_projection_batch.py \
  --output out/p007-geometry-corpus-projection.jsonl

# Verify the committed baseline/sample are fresh (and the full batch too when
# --output is supplied).
python tools/build_corpus_fact_projection_batch.py --check

# Focused tests.
python tools/test_corpus_fact_projection_batch.py
```

Committed review surfaces:
`qamus/reports/p007-geometry-corpus-projection-baseline.json`,
`qamus/examples/p007-geometry-corpus-projection.sample.jsonl` + `.meta.json`,
and `qamus/schemas/corpus-fact-projection-disposition.schema.json`. The full
985-row batch is regenerable and belongs under ignored `out/`.
