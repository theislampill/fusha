# Typed Edge Graph and Lexeme-to-Entry Crosswalk

## Binding boundary

This design implements the owner directive for the EDGES lane. The whitelist
`entry_id` is a page-context fact. It is represented by
`page_context_entry_edge` and is never used as a lexeme-entry assertion. The
new graph is additive: existing VNMAP ledger fields and the occurrence-
appearance index remain intact and remain the only occurrence graph.

All outputs are candidate-mode unless an input fact explicitly supplies a
certified morphology record. A root match alone can create only a
`root_family_edge`; it can never promote a `lexeme_entry_edge`.

## Ontology

The graph uses the exact minimum edge vocabulary:

`page_context_entry_edge`, `selected_example_edge`, `lexeme_entry_edge`,
`form_entry_edge`, `sense_entry_edge`, `root_family_edge`,
`canonical_occurrence_edge`, `display_local_to_canonical_crosswalk_edge`,
`source_card_edge`, `source_photo_edge`, `rendered_appearance_edge`, and
`decision_evidence_edge`.

Each JSONL record has schema `qamus.graph_edge.v1` and these required fields:

```json
{
  "schema": "qamus.graph_edge.v1",
  "edge_id": "edge:<stable-digest>",
  "edge_type": "lexeme_entry_edge",
  "from_node_id": "selected-word:<stable-id>",
  "from_node_type": "selected-word",
  "to_node_id": "entry:<stable-id>",
  "to_node_type": "entry",
  "status": "deterministic_exact",
  "evidence": [{"address": "<source address>", "method": "<method>"}],
  "producer": {"id": "<producer>", "version": "<version>"},
  "guards": ["orthography_guard_v1"]
}
```

Permitted statuses are `certified`, `deterministic_exact`, `candidate`,
`ambiguous`, `source_gap`, `owner_or_scholar_required`, and `rejected`.
Node identifiers are typed and use the prefixes `entry`, `sense`, `card`,
`selected-word`, `occurrence`, and `appearance`. Stable edge IDs are derived
from the complete identity tuple, so reruns do not duplicate edges.

## Construction

`tools/build_typed_edge_crosswalk.py` consumes the entries, whitelist, VNMAP
ledger, and the existing occurrence-appearance index. Optional producer fact
packets and predicate-v3 boundary data are supplied explicitly on the command
line. It emits one canonical edge stream and two projections:

- forward selected-word records, containing every candidate and its edge IDs;
- reverse entry records, containing every selected-word link and canonical
  occurrence backlink.

The builder also emits a delta stream for source-gap reclassification and a
debt stream for every crosswalk-missing selected-word row. The projections are
derived from the canonical edge stream in the same run; no independent
occurrence relationship is created.

Surface matching has two stages. Exact matching uses a base-letter key that
preserves hamza seats, `ة` versus `ه`, and defective spellings. Strict or
lenient normalization is recall-only. A unique exact, guarded match is
`deterministic_exact`. A certified status additionally requires an attached
certified morphology fact. Any collision records the complete collision set
and abstains. Root, POS, lemma, context, source key, and card identity are
candidate evidence only unless an explicit source fact closes the required
chain.

The builder materializes page-context, selected-example, card, occurrence,
appearance, display-local, and source evidence edges even when the lexeme
crosswalk is absent. This makes plumbing gaps visible without laundering them
into linguistic certainty.

## Validators and harness contract

`tools/validate_typed_edge_graph.py` contains ten named checks. Every check
has a failing red-first fixture and a passing fixture assertion:

1. page-context edges cannot be consumed as lexeme edges;
2. every selected word has an exact card backlink;
3. certified occurrence links have reverse entry-to-occurrence links;
4. form edges cite documented form or source evidence;
5. sense edges cite a sense identity;
6. duplicate-surface ambiguity abstains;
7. display-local addresses map to exact canonical surfaces;
8. canonical corrections reach every repeated appearance;
9. typed facts and projections have no orphan;
10. exact reconstruction remains valid.

The committed fixture mode is self-contained and is the harness gate. Full
corpus measurement is an explicit CLI run and writes lane-side artifacts only.
The harness never depends on an external corpus, network, private path, or
untracked generated file.

## Reclassification and debt

Reclassification is a delta, never an edit to producer history. A source-gap
row remains `source_gap` unless a linguistic/source fact is present and the
only failure is one of the exact graph blockers:

`lexeme_entry_crosswalk_missing`, `certified_fact_attachment_missing`,
`selected_word_edge_missing`, `canonical_occurrence_edge_missing`,
`display_local_crosswalk_missing`, `projection_input_edge_missing`, and
`appearance_backlink_missing`.

The special `سفهاء` location is handled by the same chain: page-context
relationship, canonical occurrence, repeated appearance, source card/local
selected-word bridge, fact attachment, then form/sense/lexeme edges. The
repair records remain candidate or deterministic-exact; no scripture fact is
created by the graph tool.

All 6,677 missing rows receive one primary owner repair family from the exact
thirteen-family vocabulary in the directive. The report includes counts,
worked rows, secondary evidence, and a reusable repair-lane recipe per family.
The nine reciprocity failures are reported individually with their observed
relationship values and a decision about ledger defect versus typed packet
repair. Duplicate-surface ambiguities are split into context-resolvable,
crosswalk-needed, and genuinely ambiguous.

## Measurement and completion

The report measures selected-word rows gaining lexeme/form edges by status,
cards whose complete selected-word set has an edge, entries with at least one
edge, and the classic entry/card/selected-word/occurrence/appearance totals.
Any clitic-family measurement is explicitly bounded by predicate v3 input.

Completion requires the committed tools, fixtures, tests, and harness hook to
pass from repository contents alone; the lane-side full-input artifacts and
`EDGES-REPORT.md` to contain the measured counts and blocker classifications;
`git diff --check` to pass; and a local `edges:` commit with no push.

## Extension (2026-07-28): `citation_form_display_edge`

Per GRAPH-BACKLINK-REPAIR-PREP-2026-07-29 §1: 4,930 of the 6,677 crosswalk-missing
selected-word rows are dictionary **citation forms rendered display-locally** — the entry
page shows a lemma that is *not a token of the cited āyah*. Forcing a
`display_local_to_canonical_crosswalk_edge` for them would assert a false canonical loc.
One new `edge_type` is added to `qamus.graph_edge.v1` (schema string unchanged; the
edge-type vocabulary is extended, statuses/nodes are reused, never extended):

- `edge_type: citation_form_display_edge`, `from: selected-word`, `to: entry` (or `sense`).
- `display_basis`: `corpus_witness_elsewhere` (surface IS a Qurʾān token, just not in the
  cited āyah — witness locs recorded as **evidence only**, methods
  `surface_match_strict_witness_only` / `surface_match_lenient_witness_only`),
  `never_a_corpus_token`, or `multiword_phrase`.
- Guards: `no_canonical_loc_guard` (the edge may not carry, and the builder may not
  co-emit, any canonical-loc assertion for the same selected-word node; enforced by
  `citation_guard_violations`) + `orthography_guard_v1`.
- Status vocabulary reused: `deterministic_exact` (display surface byte-matches its own
  entry's headword/usage-form/sense surface), `ambiguous` (surface collides across >1
  entry — existing collision-abstain), `candidate` otherwise.
- Debt semantics: a row carrying this edge retires
  `display_local_to_canonical_crosswalk_missing`, `missing_quran_wbw_edge`, and
  `canonical_occurrence_appearance_missing` **as satisfied-by-design**
  (`details.retires_as_satisfied_by_design`).
- Builder mode: `tools/build_typed_edge_crosswalk.py --emit-citation-display` →
  `qamus/lattice/citation-display-edges.jsonl` (Queue B, 4,930) and
  `qamus/lattice/crosswalk-attach-queue.jsonl` (Queue A, 1,747 attachable rows —
  deterministic pre-fill, `two_vote_disambiguation` for the 83 multi-position ambiguous).
- All candidate-plane; nothing touches certification or the live site.
