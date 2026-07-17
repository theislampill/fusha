# VNMAP entry-card word ledger design

## Goal

Add a deterministic, candidate-mode NorthStar addendum that joins Qamus entry
senses and usage forms to the existing whitelist and canonical
occurrence-to-appearance index. The output must expose the four denominators,
the owner missing-edge vocabulary, bidirectional trace metrics, a labelled VN
proposal when no authoritative per-entry assignment exists, and the clitic
family's impact on each denominator.

## Verified inputs and denominator meanings

- `entries.jsonl` contains 2,092 entries with exactly 100 particle source keys
  (`p001`-`p100`), 947 verb keys (`v001`-`v947`), and 1,045 noun keys in the
  requested numeric `n0001`-`n1045` space. The observed raw noun keys are
  `n001`-`n1045`: three-digit padding below 1,000 and four digits thereafter.
- `rh_live_01_beta_whitelist.jsonl` contains 34,323 canonical `loc` rows.
- `occurrence-appearances.jsonl` contains one record per canonical location,
  34,323 unique occurrences, 56,117 total appearances, and 21,794 repeated
  appearances beyond the reader occurrence.
- `famwide-strat.jsonl` contains 4,865 verified clitic-family producer rows.
- D1 counts entries.
- D2 counts every non-empty `usage.examples[]` object as one listed Qurʾānic
  example card; the containing usage objects are retained as sense-card
  context.
- D3 counts every `usage.forms[]` value once per usage object, producing one
  ledger row per displayed selected-word record. Forms are not multiplied by
  the number of examples in the same usage object.
- D4 is joined from the existing occurrence/appearance records: unique
  canonical occurrences, total appearances, and repeated appearances.

## Architecture and identity joins

`tools/build_entry_card_word_ledger.py` is stdlib-only and has no implicit
lane or workstation paths. Its required arguments name the entries and
whitelist files; the occurrence index and clitic-family files are explicit
arguments too. The builder imports the existing occurrence builder's
projection hash only for parity comparison and reads its emitted JSONL as the
canonical occurrence/appearance source. It never creates a second occurrence
graph or copies finished renderings.

For each entry, the builder walks `usage` in source order, preserves the
numeric `sense` value, counts each example card, and emits each form as a D3
row. A form is joined conservatively to whitelist rows sharing the entry's
source-key identity (prefix plus numeric value, so `n518` and `n0518`
crosswalk), entry ID, and the example's ayah reference. Exact surface match
is preferred; strict normalized surface match is allowed only when unique.
Multiple candidates produce `duplicate_surface_edge_ambiguous`; no candidate
produces the precise selected-word and display-address missing edges. A
unique candidate supplies the whitelist `loc`, quran/wbw addresses, quality
state, and the existing occurrence-index record. No entry URL or production
identifier is persisted in the new artifacts.

Each row carries recoverable identity fields and a sorted `missing_edges` list.
Only the owner enum is used for missing edges:

`missing_entry_url_edge`, `missing_source_photo_edge`,
`missing_source_card_edge`, `missing_displayed_fragment_edge`,
`missing_selected_word_edge`, `missing_quran_wbw_edge`,
`duplicate_surface_edge_ambiguous`,
`display_local_to_canonical_crosswalk_missing`,
`rendered_span_edge_missing`, `decision_backlink_missing`, and
`canonical_occurrence_appearance_missing`.

Source-photo absence is reported from the entry store rather than inferred
from a whitelist locator. Rendered-span/readback and decision-backlink edges
are explicitly unmeasurable in this pre-deploy offline lane and therefore are
counted with their exact enum names, not hidden behind a generic blocker.

## VN proposal and readiness

The builder searches repository documentation, Qamus records, and prior VN
reports for a data-backed per-entry `VN-00` through `VN-20` assignment. If no
such assignment exists, every ledger row has `vn_tranche: null`. The report
then presents a `DERIVED PROPOSAL — REQUIRES OWNER CONFIRMATION` matrix using
the documented source-key order (verbs, nouns, particles), preserving the
documented VN-00/VN-01 boundaries and splitting the remaining ordered entries
into 19 balanced contiguous groups. Proposal labels never become ledger
assignments.

The readiness matrix groups D1-D3 and linked D4 rows by proposal tranche. It
also joins verified clitic-family rows by canonical `loc` and entry/source-key
identity. Producer verification unlocks candidate rows only; source-certified
count remains zero pending owner certification. Expected deployable counts and
coverage gains are projections, never deployment or rich-hover claims.

## Metrics, validation, and artifacts

`vn-graph-metrics.json` records the required forward/reverse trace metrics,
typed-fact/payload orphan counts, reciprocity failures, appearance parity
failures, exact missing-edge counts, input-space counts, and zero manual-probe
status with reasons. `vn-readiness-matrix.json` records denominator totals,
proposal labels, tranche rows, clitic-family mapping, and projection limits.
`VNMAP-REPORT.md` is generated from the same deterministic result and includes
the denominator tables, metrics, proposal caveat, clitic-family NorthStar
mapping, Compounding Impact, and honest pre-deploy limits.

`tools/validate_vn_ledger.py` validates row shape, owner-enum closure,
denominator sums, canonical reverse reciprocity, and fixture integrity. The
existing regression harness invokes its repo-only structure gate and
self-test. A small committed fixture subset exercises the joins without
requiring external input files; the full deliverables are regenerated by the
explicit-input builder command.
