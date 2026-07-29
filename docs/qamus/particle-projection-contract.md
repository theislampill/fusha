# Particle two-surface projection & pedagogy contract

**Status:** proposed 2026-07-29 (owner steer §6, PARTICLE-CONTRACTS lane);
design flags A–E owner-decided 2026-07-29 (steer decision §8) — recorded in §5.
**Scope:** every rendered appearance of a particle/clitic occurrence, on every
page class (reader, entry card, example card, WBW hover, dogfood review).
**Extends, never forks:**

- `docs/certification-authority.md` — evidence modes and the sufficiency
  ladder are reused verbatim; nothing here introduces a new certification path.
- `qamus/schemas/particle-edge-ontology.schema.json` — the particle edge kinds
  (an extension of the one canonical `qamus.graph_edge.v1` vocabulary in
  `tools/build_typed_edge_crosswalk.py`) plus the homograph function lattice.
- `docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md` — hover-payload
  normalization; this doc adds the particle-specific pedagogy plane and the
  cross-page parity invariant.

**Executable twin:** `tools/validate_particle_projection_parity.py`
(red-first self-test, gated in `tools/check_regressions.py`). Where this prose
and the validator disagree, the validator is the bug and this doc is the spec —
fix the validator, never quietly re-read the doc.

## 1. The two surfaces

A particle occurrence teaches on exactly two surfaces. Both are projections of
the SAME canonical typed-fact artifact for that occurrence; neither may carry
a fact the artifact does not carry.

### 1.1 Rich-at-rest (no interaction)

At rest, wherever the semantic class instantiates, the reader must see — with
zero hovering:

1. **Stable colour class.** The particle/clitic colour class is a function of
   the certified (or, pre-certification, the single deterministic) semantic
   class of the component — never of the page it happens to render on. The
   same occurrence renders the same colour class on the reader page, the entry
   card, and every example card.
2. **Host boundary.** When the particle is a clitic on a host token
   (بِـ، فَـ، وَ، لَـ، الْ…), the boundary between clitic and host is visible at
   rest (segment boundary in the span markup), so a learner never mistakes
   بِسْمِ for one morpheme.
3. **Attached pronoun.** An attached pronoun component (ـهُ، ـكَ، ـنَا…) is its
   own visible segment with its own colour class, not absorbed into the host.

Rich-at-rest carries NO analysis prose. It is colour, boundary, and segmentation
only — the invitation to hover, not the lesson.

### 1.2 Rich-hover (the teaching plane)

The hover for a particle/clitic component presents, in order:

1. **Exact component** — the precise sub-token surface being explained
   (`component_surface`), diacritics intact.
2. **Contextual gloss** — the gloss that is true *in this āyah*, not the
   headword's gloss list.
3. **Particle identity** — which particle this is (headword + entry identity).
4. **Contextual function** — what it is doing here (nafiya, mawsula,
   istifhamiyya, masdariyya, shartiyya, jarr, ʿaṭf, …), from the certified
   winner of the function lattice, or an honest unresolved state (§1.3).
5. **"Ṣarf — how this piece forms or attaches"** — formation/attachment
   pedagogy: indeclinable form, clitic attachment to the host, assimilation,
   the pronoun's attachment.
6. **"Naḥw — what this piece does here"** — the sentence-level work: what it
   governs, what governs it, what it scopes over.
7. **Governor / governed** — from `governor_edge` / `governed_expression_edge`.
8. **Scope** — from `scope_edge` / `negation_scope_edge` / `condition_edge` /
   `coordination_edge` as applicable.
9. **Attachment** — host token and boundary (from `clitic_host_edge`).
   Rung-1 certification of `clitic_host_edge` certifies ATTACHMENT GEOMETRY
   ONLY (§5, flag C) — never the clitic's lexical identity, function,
   governor, or scope.
10. **Alternatives** — the surviving non-winning candidates from the function
    lattice, each with its guards, presented as live alternatives, not noise.
11. **Reason** — why the winning analysis wins (the discriminating guard /
    defeater that eliminated the alternatives).
12. **Unresolved state** — if no candidate is certified, the hover says so
    explicitly ("function not yet adjudicated; N candidate analyses") rather
    than silently picking one.
13. **Entry link** — navigation to the particle's entry page.

### 1.3 Rootlessness is taught, never blank

A particle has no triliteral root. A ROOTLESS particle's hover MUST explicitly
teach rootlessness in the Ṣarf plane (e.g. "This particle is not built from a
root — it is an indeclinable tool word") — a null root may never render as an
empty field, a dash, or a missing row. The projection carries a non-empty
`rootless_pedagogy` string whenever `root` is null; the validator fails a
rootless particle projection without it. A particle must never look
*incomplete*; it is *differently complete*.

### 1.4 No Arabic iʿrāb prose in the teaching plane

The teaching plane (gloss, ṣarf note, naḥw note, reason) is learner-register
English. Arabic technical iʿrāb formulas (e.g. "مبتدأ مرفوع وعلامة رفعه…",
"في محل جر", "مفعول به منصوب") are private-side analysis language and may not
appear in any public teaching field. Arabic in the teaching plane is limited to
object-language material: the surfaces, hosts, governed expressions, and
antecedents being taught. The validator carries a forbidden-formula scan.

## 2. Projection-hash invariant (cross-page parity)

**Invariant:** every appearance of one canonical occurrence has the SAME
projection hash, on every page, except for the permitted page-presentation
metadata below. One occurrence, one analysis, everywhere — a gloss, function,
or segmentation that forks across pages is a defect by construction, not a
style choice.

### 2.1 Hash basis

The hash is computed over the **canonical typed-fact artifact serialization**
of the appearance's projection object:

1. remove the permitted presentation keys (§2.2) from the projection object
   (top level only — presentation metadata may not be smuggled into nested
   fact fields);
2. serialize with `json.dumps(obj, ensure_ascii=False, sort_keys=True,
   separators=(",", ":"))`;
3. `projection_hash = sha256(utf-8 bytes)` hex digest.

The canonical occurrence projection (the typed-fact artifact's own projection)
is hashed the same way; every appearance hash must equal it.

### 2.2 Permitted presentation-metadata whitelist

Exactly these top-level projection keys are presentation, not fact, and are
excluded from the hash:

| key | meaning |
|---|---|
| `selected_highlight` | whether this appearance is the page's selected/highlighted instance |
| `entry_relationship` | how this page relates to the occurrence (own-entry example, cross-reference, reader context) |
| `focus` | page focus/emphasis state |
| `navigation` | page-local navigation affordances (breadcrumbs, links rendered) |

Appearance identity fields (`appearance_id`, `page_id`, `occurrence_id`,
`artifact_id`) live OUTSIDE the projection object and are never hashed. Any
other key that differs between appearances of one occurrence — segmentation,
gloss, function, colour class, governor, scope, ṣarf/naḥw notes, root,
rootless pedagogy, alternatives, reason, unresolved state, entry link — is a
hash fork and a validator FAIL. The whitelist is closed: extending it is an
owner decision recorded here, not a validator-side convenience.

### 2.3 Artifact sharing is per-occurrence, never per-surface

Two occurrences with the SAME surface (two مَا in one āyah, or on one card) are
distinct canonical occurrences with distinct artifacts. An appearance may only
reference the artifact of its own `occurrence_id`; same-surface artifact
sharing across occurrences is a FAIL (this is the PROOF-P `2:284:2` vs
`2:284:10` lesson — the card with two identical مَا surfaces keeps them
distinct or keeps the gap explicit).

## 3. Candidate vs certified on the two surfaces

- A **candidate** function analysis may render only inside the alternatives /
  unresolved plane of the hover; it may never occupy the contextual-function
  slot as if certified.
- The contextual-function slot is fed by the certified winner of the
  `qamus.particle_function_lattice.v1` lattice; certification of that winner
  requires the evidence bundle + two-vote artifact per
  `docs/certification-authority.md` §2 rung 4 (structural in
  `particle-edge-ontology.schema.json`).
- The lattice's single-winner rule is scoped to MUTUALLY EXCLUSIVE candidate
  analyses (§5, flag E): at most one member of `mutually_exclusive_candidates`
  may ever be certified, unconditionally. Genuine layered functions —
  zero-or-more compatible typed function facts WITHIN the winning analysis —
  live in `compatible_functions`, and each certifies only with (a) explicit
  source support for coexistence (`coexistence_source_support`), (b) an
  independent review (`review_ref`), and (c) no contradiction in the typed
  relation set (a layered function may never duplicate an exclusive-candidate
  label). Then, and only then, may the hover teach a layered function.
- An `unresolved` evidence mode can never certify, so an unresolved occurrence
  always renders §1.2's item 12 honestly.

## 4. What this contract does NOT govern

- Which occurrences get authored first (lane sequencing).
- Private-side triangulation corpora and their names (FORBIDDEN_LABELS
  discipline applies; internal source names never reach the projection).
- Non-particle tokens (nouns/verbs have their own richer ṣarf plane; the
  parity invariant §2 is written per-occurrence and is expected to generalize,
  but only the particle plane is normative here).

## 5. Owner-decided design flags (2026-07-29 steer, decision §8)

The five PR #115 design flags are OWNER-DECIDED. Reversing any of them is an
owner decision recorded here — never a schema- or validator-side convenience.

- **Flag A — presentation whitelist (OWNER-DECIDED).** The permitted
  presentation-metadata whitelist is exactly the four keys of §2.2
  (`selected_highlight`, `entry_relationship`, `focus`, `navigation`).
  Extension of the whitelist is an owner decision recorded in this doc.
- **Flag B — coordination reclassification (OWNER-DECIDED).** Coordination is
  a typed Naḥw RELATION edge, not itself an iʿrāb class. `coordination_edge`
  is removed from the iʿrāb-bearing set (schema
  `$defs/irab_bearing_edge_type` + validator `IRAB_BEARING_EDGE_TYPES`): a
  certified coordination edge requires the evidence bundle (bundle rung) but
  NOT a token-layer two-vote artifact. The COORDINATED ELEMENTS'
  case/mood/agreement/attachment facts remain iʿrāb-bearing through their own
  edges (governor / governed-expression / scope …), which keep the two-vote
  requirement. The vocabulary-drift gate fails if `coordination_edge`
  re-enters either iʿrāb-bearing set.
- **Flag C — clitic-host scope (OWNER-DECIDED).** Rung-1 certification of
  `clitic_host_edge` certifies ATTACHMENT GEOMETRY ONLY: which sub-token
  component attaches to which host, at which boundary. It does NOT certify
  the clitic's lexical identity, contextual function, governor, or scope —
  those travel on their own edges with their own evidence.
- **Flag D — node-type guidance (OWNER-DECIDED).** Nodes exist only for
  identity-bearing objects: token occurrence, morpheme occurrence, entry,
  sense analysis, evidence artifact, public appearance. Relations are typed
  edges, never nodes. Per owner model §7 the ontology carries
  morpheme-occurrence-level identity: the `morpheme-occurrence` node type and
  the minimal `qamus.particle_morpheme_occurrence.v1` object
  (`morpheme_occurrence_id` + base-letter span + host token occurrence) in
  `particle-edge-ontology.schema.json`.
- **Flag E — dual-function allowance (OWNER-DECIDED).** The lattice's
  `maxContains: 1` applies only ACROSS MUTUALLY EXCLUSIVE candidate analyses
  (`mutually_exclusive_candidates`), unconditionally — the former
  `overlap.supported` escape hatch is removed. Zero-or-more compatible typed
  function/relation facts WITHIN the winning analysis live in
  `compatible_functions`; a certified layered function requires (a) explicit
  source support for coexistence, (b) independent review, (c) no
  contradiction in the typed relation set (§3).

