# The transclusion graph — canonical nodes, edges, and identity rules

Status: adopted 2026-07-29 (canonical architecture doc, precedence tier 4).
Machine sources of truth (tier 1, always win):
`qamus/schemas/particle-edge-ontology.schema.json`,
`tools/build_typed_edge_crosswalk.py`,
`tools/test_entry_transclusion_invariants.py`,
`tools/validate_particle_projection_parity.py`.

Everything the Qamus teaches is a **projection of a graph**, never a copy of
text. A solved fact lives once, at a canonical address, and every page that
shows it *transcludes* it. This doc names the graph's node types, its typed
edge vocabulary (the real, greppable identifiers), the identity rules that
keep it honest, and four worked examples from committed artifacts.

## 1. Node types

Schema enum (`particle-edge-ontology.schema.json`, `node_type`):

`entry` · `sense` · `card` · `selected-word` · `occurrence` ·
`morpheme-occurrence` · `appearance` · `source` · `decision`

Node-id formats (from `tools/build_typed_edge_crosswalk.py`):

| Node | Id format | Meaning |
|---|---|---|
| entry | `entry:<entry_id>` | one of the 2,092 public Qamus entries (p/v/n) |
| sense | `sense:<entry_id>:s<n>` | a numbered sense of an entry |
| card | `card:<entry_id>:u<n>:x<n>` | an example card (usage × example index) on an entry page |
| selected-word | `selected-word:<entry_id>:s<n>:u<n>:f<n>[...]` | the highlighted word a card selects |
| occurrence | `occurrence:<loc>` / canonical `quran:S:A:W` | one canonical Qurʾānic token occurrence |
| morpheme-occurrence | `mocc:<source_key>:S:A:W` (pilot idiom) | one **sub-token** morpheme at an occurrence (e.g. the لِ of لِقَوْمِهِ) |
| appearance | `appearance:<loc>:<index>` / `<page-hash>:u<n>:x<n>:w<n>` | one rendering of an occurrence on one page |
| source | (address-formed) | an evidence source record |
| decision | `decision:<state_id>` | a recorded review/decision artifact |

**Token vs morpheme occurrences.** A *token occurrence* is the whole written
word at `quran:S:A:W`. A *morpheme occurrence* is an identity node for one
piece of it (schema `qamus.particle_morpheme_occurrence.v1`, with
`base_letter_span` + `component_surface`). They are distinct node kinds with
distinct appearances; the 8-object model (owner-ruled 2026-07-29) forbids
conflating token occurrence/appearance with morpheme occurrence/appearance or
candidate with certified edges. Classifier output ("candidate particle
entry/sense links") is never called "particle occurrences".

**Selected vs context words.** A card *selects* exactly one word
(`selected_example_edge` to the selected-word node); every other word in the
card's āyah is a *context word*. Context words get `page_context_entry_edge`
with guards `entry_id_is_verse_context` + `never_lexeme_edge` — page context
is **never** a lexical claim about the entry. The particle denominator is the
full example-āyah universe (particles as context words across all 2,092
entries' cards), not just particle-page spans.

## 2. Typed edge vocabulary

All edges are rows of schema `qamus.graph_edge.v1`. One graph — the particle
kinds are appended to the same `EDGE_TYPES` list, "NOT a parallel graph"
(`tools/build_typed_edge_crosswalk.py`).

### 2.1 Base edge family (13)

`page_context_entry_edge` · `selected_example_edge` · `lexeme_entry_edge` ·
`form_entry_edge` · `sense_entry_edge` · `root_family_edge` ·
`canonical_occurrence_edge` · `display_local_to_canonical_crosswalk_edge` ·
`source_card_edge` · `source_photo_edge` · `rendered_appearance_edge` ·
`decision_evidence_edge` · `citation_form_display_edge`

### 2.2 Particle edge family (18)

`particle_entry_candidate_edge` · `particle_entry_certified_edge` ·
`particle_sense_candidate_edge` · `particle_sense_certified_edge` ·
`particle_function_edge` · `clitic_host_edge` · `governor_edge` ·
`governed_expression_edge` · `scope_edge` · `coordination_edge` ·
`condition_edge` · `negation_scope_edge` · `relative_antecedent_edge` ·
`pronoun_referent_edge` · `particle_occurrence_appearance_edge` ·
`particle_entry_reverse_occurrence_edge` · `source_evidence_edge` ·
`decision_or_two_vote_edge`

The **iʿrāb-bearing subset** (each requires a two-vote artifact to certify):
`particle_function_edge`, `governor_edge`, `governed_expression_edge`,
`scope_edge`, `condition_edge`, `negation_scope_edge`,
`relative_antecedent_edge`, `pronoun_referent_edge`.
`coordination_edge` is deliberately excluded — it is a relation edge, not an
iʿrāb class (owner §8 flag decision).

### 2.3 Edge statuses

`certified` · `deterministic_exact` · `candidate` · `ambiguous` ·
`source_gap` · `owner_or_scholar_required` · `rejected`

### 2.4 Owner-name → repo-idiom crosswalk

The owner's relation vocabulary maps onto the edge types above (full mapping
in the docstring of `tools/test_entry_transclusion_invariants.py`; extract):

| Owner relation | Repo edge |
|---|---|
| entry_has_lexeme / occurrence_instantiates_lexeme | `lexeme_entry_edge` |
| entry_has_sense / occurrence_instantiates_entry_sense | `sense_entry_edge` |
| entry_documents_form / occurrence_realizes_form_of_entry | `form_entry_edge` |
| entry_root_family / occurrence_shares_root_with_entry | `root_family_edge` |
| entry_has_example_card | `source_card_edge` (+ card node) |
| card_selects_occurrence | `selected_example_edge` |
| card_displays_context_occurrence | `display_local_to_canonical_crosswalk_edge` |
| occurrence_contains_morpheme | `clitic_host_edge` + morpheme-occurrence node |
| morpheme_occurrence_instantiates_particle_entry | `particle_entry_{candidate,certified}_edge` |
| morpheme_occurrence_instantiates_particle_sense | `particle_sense_{candidate,certified}_edge` |
| occurrence_has_public_appearance | `rendered_appearance_edge` / `particle_occurrence_appearance_edge` |
| appearance_consumes_projection | `details.projection_hash` |
| projection_derived_from_certified_facts | `decision_evidence_edge` |
| certified_fact_supported_by_evidence | `source_evidence_edge` |
| entry_reverse_lists_occurrence | `particle_entry_reverse_occurrence_edge` |

These are **different edges, never interchangeable**: instantiating a lexeme,
realizing a form, instantiating a sense, and sharing a root are four distinct
claims with distinct evidence requirements.

## 3. Identity and integrity rules

**Source-address identity.** The canonical occurrence address is
`corpus:surah:ayah:token` (regex `^[a-z]+:[0-9]+:[0-9]+:[0-9]+$`, e.g.
`quran:61:5:4`), asserted by the particle-edge ontology schema. The wider
address grammar (entry fields, WBW artifacts, decisions, repairs, source
photos) is documented in `tools/build_full_source_address_graph.py`. The
older whitelist/ledger layer uses bare `S:A:W` locs — crosswalked, never
merged. Reuse is **loc-first**: surface-only keys are diagnostic labels, not
reuse authority (`docs/parser/TRANSCLUSION.md`).

**Reverse indexing.** Every entry must be able to list its certified
occurrences (`particle_entry_reverse_occurrence_edge`, guard
`reverse_index_closure`). Implementations:
`tools/build_typed_edge_crosswalk.py` (reverse crosswalk records),
`tools/build_occurrence_appearance_index.py`,
`tools/build_full_source_address_graph.py` (+
`tools/query_source_address_graph.py`), `tools/build_p007_li_pilot.py`
(pilot `entry-reverse-index.json`).

**Appearance parity.** Every appearance of one canonical occurrence carries
the SAME projection hash — one occurrence, one analysis, everywhere. Enforced
by `tools/validate_appearance_parity.py` and
`tools/validate_particle_projection_parity.py`; a cross-page fork is a defect
by construction. See `docs/architecture/two-surface-contract.md`.

**Reciprocity.** Forward and reverse views must agree: if an occurrence
instantiates an entry, the entry's reverse index lists the occurrence, and
the appearance sets match (`tools/test_entry_transclusion_invariants.py`; the
2026-07-29 graph repair drove reciprocity failures 3 → 0).

**Revocation propagation.** Certification is fact-level and revocable; when a
fact loses certification, `dependent_fact_ids` / `dependent_projection_ids`
are mechanically flagged and derived facts cascade to de-certified
(`tools/certify_typed_fact.py`; rules in
`docs/certification-authority.md` §5). Edges citing a revoked fact revert to
non-certified statuses.

**Citation-form displays.** Cards often display a citation form rather than a
canonical inflected occurrence. That is a `citation_form_display_edge`
(producer `citation_form_display.v1`) — it *retires* the debt families
`display_local_to_canonical_crosswalk_missing`, `missing_quran_wbw_edge`,
`canonical_occurrence_appearance_missing` as satisfied-by-design, with guard
`no_canonical_loc_guard` (regression-gated). It never fabricates a canonical
loc for a display-only form.

**Page-context vs lexical edges.** A verse quoted on an entry page creates
page-context edges to that page only; lexical claims require
`lexeme_entry_edge`/`form_entry_edge`/`sense_entry_edge` with their own
evidence. Guard: `never_lexeme_edge`.

**Root-family is relation, never identity.** `root_family_edge` carries guard
`root_agreement_never_lexeme_edge` and evidence method `root_agreement_only`.
Root-sharing NEVER implies entry identity; function words may not receive a
root-family edge at all (`tools/proofp_harness.py`).

**Entry completion ladder.** Entry state is measured on the 12-state ladder in
`tools/build_entry_completion_state.py`: `entry_registered` →
`entry_membership_known` → `forms_documented` → `senses_enumerated` →
`root_family_mapped` → `occurrences_discovered` →
`occurrence_links_candidate` → `occurrence_links_certified` →
`appearances_projected` → `reverse_index_published` →
`teaching_assets_derived` → `fully_transcluded`.

## 4. Worked examples (all from committed artifacts)

### 4.1 p007 — the لِـ noun-host pilot (`qamus/examples/p007-li-pilot/`)

The flagship end-to-end slice: entry `b10a1ee04666` sense 2 (لِـ), 12
canonical occurrences, 78 entry-page appearances, 49 typed facts.
`transclusion-edges.jsonl` holds 72 certified `qamus.graph_edge.v1` rows —
exactly six edge types × 12 occurrences: `particle_entry_certified_edge`
(mocc → entry), `particle_sense_certified_edge` (mocc → sense),
`clitic_host_edge` (mocc → host occurrence), `governor_edge`,
`governed_expression_edge` (both two-vote-backed), and
`particle_entry_reverse_occurrence_edge` (entry → occurrence). A generic
"preposition" colour class without the entry+sense edges does **not** satisfy
transclusion. Gate: `tools/validate_p007_pilot.py`, wired into
`tools/check_regressions.py` (P007PILOT block).

### 4.2 Multi-entry token — لِقَوْمِهِ at `quran:61:5:4`

`qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json`
(the vn-entry-canaries multi-entry sample, schema_version 1.1.0). One written
token, three segments (لِ + قَوْمِ + هِ), known to **three entry graphs at
once** with three distinct relation kinds in `entry_links`:

- `clitic_component_of_entry` → the particle entry (p007's لِـ) for segment 0;
- `candidate_entry` → the noun entry (n225 lane, قَوْم headword candidate);
- `root_family_of_entry` → the verb entry (v005 قَامَ) for segment 1 — root
  ق و م shared, **no** lexeme identity.

One projection hash serves all pages; the cross-axis proof is that the same
occurrence sits in the p007 morpheme graph, the v005 root-family graph, and
the n-entry form graph without any claim leaking between axes.

### 4.3 A root-family-only relation — v005 قَامَ ↔ قَوْمِ

The `root_family_of_entry` link in the 61:5:4 payload above (and the
`root_family_edge` vocabulary behind it) is the canonical demonstration that
root relation ≠ dictionary identity: the segment's own `sarf_note` teaches
"the same root also builds the verb qama — a root-family relation, not a
shared dictionary entry." Machine guards: `root_agreement_never_lexeme_edge`;
evidence method `root_agreement_only`. A separate `vn-entry-canaries` lane
store once claimed root/lexeme attachment certified for the v005/n225
canaries, but that lane store is not one of the two committed certification
stores `tools/website_evidence_resolver.py` consults, so those payloads
(`verb_qamu_2_20_13` / `noun_rajulayni_2_282_59`) currently carry
`certification.status: unresolved`, `plane.root: review_required` /
`plane.lexeme_attachment: review_required`, and
`public_projection_eligible: false` (see
`docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`
§12) pending re-certification against currently authoritative repository
evidence — neither row is currently certified payload authority.

### 4.4 An unresolved lattice — مَا at `quran:2:284:2`

`qamus/examples/website-payloads/unresolved_ma_2_284_2.payload.json`. The
particle-function lattice (`qamus.particle_function_lattice.v1`) holds
mutually exclusive candidates (`nafiya`, `mawsula`, `istifhamiyya`, … — at
most ONE may be certified, schema-enforced by `maxContains: 1`). Here none
is: `semantic_class: unresolved`, renderer class `qg-unresolved` (neutral
colour, never colour-guessed), gloss "reading not yet adjudicated",
candidates shown in the hover, `certification.status: unresolved`. Honest
unresolved is a first-class state — never render one rival as the winner.
Same-surface distinctness: the مَا at `2:284:2` and the مَا at `2:284:10`
(PROOF-P, `qamus/examples/proof-particle/`) are distinct artifacts —
sharing is per-occurrence, never per-surface.

---
Verified against: commit 637d7da (origin/main, 2026-07-29). Artifacts:
`qamus/schemas/particle-edge-ontology.schema.json`,
`tools/build_typed_edge_crosswalk.py`,
`tools/test_entry_transclusion_invariants.py`,
`tools/build_entry_completion_state.py`,
`qamus/examples/p007-li-pilot/{README.md,transclusion-edges.jsonl,morpheme-occurrences.jsonl,entry-reverse-index.json}`,
`qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json`,
`qamus/examples/website-payloads/unresolved_ma_2_284_2.payload.json`,
`qamus/examples/proof-particle/particle-graph-edges.jsonl`;
`tools/check_regressions.py` ALL REGRESSION CHECKS PASS.
