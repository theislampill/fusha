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
- `qamus/lattice/particle-occurrence-matrix.jsonl` — candidate particle fact/function
  lattice; the closest committed proxy for Nahw/colour/hover fact identity.

## What it writes

- Full manifest JSONL (one row per displayed-token appearance): an explicit,
  user-supplied `--output` path, normally under the gitignored `out/` tree. Never
  committed. Deterministic: same committed inputs -> byte-identical output.
- `qamus/reports/corpus-projection-baseline.json` (committed): compact aggregate —
  entry/universe count verification, per-disposition status counts, letter-ownership
  and page-local-fork counts, the P009/P099 canary report, the colour/hover identity
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
entry/canonical-occurrence counts, an eleven-part `dispositions` object
(`exact_binding`, `surface`, `letter_ownership`, `sarf`, `nahw`, `colour`,
`hover`, `reverse_trace`, `revocation_dependency`, `payload`, `next_action`),
and a `page_local_fork` flag for canonical occurrences selected by more than one
distinct entry.

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
- `sarf`/`nahw` dispositions are `authority_not_joined_in_closed_inputs` for the
  large majority of rows: no committed per-token sarf/nahw fact source is joined
  in this manifest's closed authority yet.
- `colour`/`hover` are `not_available` or `candidate_available_uncertified` for
  the large majority of rows — this is exactly the backlog this manifest hands
  to the later rich-colour/rich-hover batches on this Train D branch. It always
  cites the same `fact_id` for `colour` and `hover` (enforced by construction and
  checked by `colour_hover_identity_invariant` in the baseline).
- `page_local_fork` (105 canonical occurrences, 210 affected rows at last build):
  canonical occurrences selected by more than one distinct entry, needing owner
  adjudication rather than a silent merge.

## Consumers

Train A/B fact projectors and the Train D projector/compiler regenerate affected
corpus batches from this manifest's `next_action` field and the baseline's
disposition-count deficits; they should re-run the generator against their own
`--output` path and diff against the committed `full_output.sha256` /
`sample_sha256` in the baseline/sample-meta to confirm they are working from the
same population spine.
