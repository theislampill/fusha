# Website-agent handoff contract — `qamus.website_projection_payload.v1`

**Status:** proposed 2026-07-29; additive `1.2.0` pilot-safety extension
specified 2026-07-30. This is a Fusha-side candidate contract, not evidence
that any website renderer accepts the extension.
**Parties:** the Fusha/Qamus agent ("Fable") and the separate website agent.
**Executable twin:** `tools/validate_website_payload.py` (red-first self-test).
Repository-harness registration of the 2026-07-30 re-anchor suite is owned by
`TP-PVN-REANCHOR-HARNESS-INTEGRATION-W1`; this pilot contract is not
merge-ready until that serialized packet runs. Where this prose and the
validator disagree, the validator is the bug and this doc is the spec.
**Extends, never forks:**

- `docs/qamus/particle-projection-contract.md` — the two-surface projection
  and the cross-page parity invariant (§2 there). This doc re-expresses the
  same invariants as a RENDERER-FACING payload contract; it introduces no new
  linguistic authority.
- `docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md` — language discipline in
  rendered fields (`norm@1` N-LANG): learner fields are English; Arabic only
  as short quoted object-language forms.
- `docs/certification-authority.md` — evidence modes and the sufficiency
  ladder. Nothing in a website payload can create, upgrade, or imply
  certification.

Sample payloads: `qamus/examples/website-payloads/*.payload.json`, all
validated by the executable twin.

---

## 1. Boundary statement — who owns what

| plane | owner | files |
|---|---|---|
| Graph, schemas, typed facts, certification, payloads, validators | **Fable (Fusha/Qamus agent)** | `qamus/**`, `docs/qamus/**`, `tools/validate_*.py` |
| Templates, renderer, CSS, JS, live pages | **Website agent** | renderer/template/CSS/JS trees and deployed pages |

Hard rules, both directions:

1. **Fable never edits renderer files.** No template, CSS, JS, or live-page
   change is ever authored from the Fusha/Qamus side. If a payload cannot be
   rendered, the payload contract is revised here — the renderer is never
   patched around from this side.
2. **The website agent never authors linguistic payloads.** It CONSUMES
   payloads only. It may not add, edit, infer, translate, re-segment,
   re-gloss, re-colour, or "fix" any linguistic fact — including apparently
   trivial ones (a missing gloss, an empty root, an odd segmentation). A
   payload defect is reported back across the boundary, never repaired
   renderer-side.
3. **The renderer class names are the interface.** Fable emits
   `renderer_class` values (the `qg-*` vocabulary); the website agent owns
   what those classes look like (colours, spacing, hover chrome). Fable never
   dictates pixels; the website agent never reassigns a token to a different
   class.
4. **All refs are internal ids.** Payloads carry evidence and provenance as
   opaque internal identifiers only (fact ids, two-vote artifact ids,
   occurrence addresses). No source prose, no private corpus names
   (FORBIDDEN_LABELS discipline), private review material, home or server
   filesystem paths, UNC paths, private network addresses, build-host keys,
   or machine topology ever cross the boundary in either direction.

## 2. Canonical payload envelope

One payload file = one appearance of one canonical occurrence. Top-level
object (`schema`: `qamus.website_projection_payload.v1`):

| key | req | meaning |
|---|---|---|
| `schema` | yes | `qamus.website_projection_payload.v1` |
| `schema_version` | yes | semver string, see §9 |
| `payload_kind` | yes | `occurrence_projection` |
| `occurrence_id` | yes | canonical occurrence address, e.g. `quran:2:34:5` |
| `artifact_id` | yes | internal typed-fact artifact id owning this occurrence |
| `appearance` | yes | where this payload renders: `appearance_id`, `page_id`, `page_kind` (`reader` \| `entry` \| `example_card` \| `wbw_hover` \| `dogfood_review`), `page_local` (§6), and the conditional `1.2.0` binding fields (§6.1) |
| `projection` | yes | the canonical fact plane (§3), hashed by `projection_hash` |
| `projection_hash` | yes | sha256 hex over the canonical serialization of `projection` (§5) |
| `appearance_binding_hash` | `1.2.0` | separate sha256 over stable appearance identity, local geometry, binding state, and the shared `projection_hash` (§6.1) |
| `reverse_links` | yes | §7 |
| `provenance` | yes | §8 |

Appearance identity and appearance-local geometry live OUTSIDE `projection`.
`page_local` is never hashed. In `1.2.0`, the closed appearance-binding basis
has its own hash so local orthographic geometry cannot mutate silently or
fork canonical occurrence truth.

## 3. The projection object (fact plane)

Everything inside `projection` is a linguistic fact owned by Fable. Keys:

| key | req | meaning |
|---|---|---|
| `occurrence_id` | yes | repeats the envelope address (self-containment) |
| `surface` | yes | canonical occurrence surface, diacritics intact and **NFC-normalized**; for `1.0.x` and `1.1.x` this is also the rendered surface, while `1.2.0` binds the exact local rendering separately (§6.1) |
| `normalization` | yes | literally `"NFC"` — the renderer must not re-normalize |
| `kind` | yes | `particle_clitic_word` \| `noun_word` \| `verb_word` |
| `segments` | yes | ordered array, §3.1 |
| `whole_word_gloss` | yes | the contextual gloss of the whole word *in this āyah* |
| `learner_explanation` | yes | one-to-two sentence learner-register English explanation |
| `entry_links` | yes | array of `{entry_id, sense_id, relation_kind, segment_index}` (§4) |
| `entry_link_state` | yes | `linked` \| `none_yet` (§4) |
| `morpheme_spans` | yes | array of `{morpheme_occurrence_id, segment_index, char_start, char_end}` — morpheme-occurrence identity per particle-contract flag D |
| `root` | yes | spaced Arabic radicals (`"ب ع ل"`) or `null` |
| `rootless_pedagogy` | cond | non-empty string REQUIRED when `kind` is `particle_clitic_word` and `root` is null (rootlessness is taught, §10.1) |
| `hover_cards` | yes | ordered array, §3.2 — the hover-only teaching plane |
| `unresolved` | yes | `null` or the honest unresolved object (§10) |
| `certification` | yes | `{status, plane}` — `status`: `certified` \| `candidate` \| `unresolved` \| `review_required`; `plane`: per-fact map (e.g. `segmentation`, `function`, `governor`, `case`), values include `certified` \| `candidate` \| `unresolved` \| `review_required` \| `candidate_pending` \| `none_yet`; this per-fact vocabulary is non-exhaustive and additive-only within a major (§9) — the renderer must render an unrecognised value neutrally, never fail |
| `public_projection_eligible` | yes (fail-closed) | boolean; REQUIRED and explicit on every non-certified payload — never omitted, `null`, or non-boolean when `certification.status` is `candidate` \| `unresolved` \| `review_required`. `certified` MAY carry `false` (or omit-as-not-yet-eligible in the `1.2.0` candidate handoff shape, §6.1) and MAY carry `true` ONLY when every cited `evidence_refs` entry resolves as `authoritative_for_certification` against the committed repository evidence (`tools/website_evidence_resolver.py`) — a certified `status` field is never itself sufficient. `tools/validate_website_payload.py`'s evidence-resolution check enforces this against the actual resolver, not against the string in `certification.status` |
| `evidence_refs` | yes | array of opaque internal ids (fact ids, two-vote artifact ids, bundle refs) |

### 3.1 Segments

Each segment: `segment_index` (0-based, contiguous), `surface` (exact NFC
substring), `char_start` / `char_end` (base-letter span: Python-style
code-point offsets into `projection.surface`, half-open), `semantic_class`
(Fable's typed role, e.g. `jarr_clitic_lam`, `noun_stem`,
`object_pronoun_1s`, or `unresolved`), `renderer_class` (the `qg-*` class the
renderer styles), `gloss` (this segment's contribution), `sarf_note`,
`nahw_note` (both learner-register English; may be `null` on non-teaching
segments, never on particle/clitic segments).

**Reconstruction invariant:** the concatenation of `segments[*].surface` in
order MUST equal `projection.surface` exactly (NFC to NFC), and the spans
MUST tile `[0, len(surface))` contiguously in order. A renderer may therefore
slice the surface by spans OR join the segment surfaces — both must give the
same string. Failure is a validator FAIL, never a renderer workaround.

Every morpheme ownership row has a unique, non-empty
`morpheme_occurrence_id`, a valid `segment_index`, and a non-empty half-open
span equal to that segment's canonical span. A primary span boundary may not
split a combining-mark sequence. `1.2.0` permits a segment to have no backed
primary morpheme identity; that absence is expressed as `null` in the
appearance map and hover identity. It never permits an invented identity.

The committed `quran:61:5:4` safety pilot deliberately exposes only the
evidence-backed opening span `[0,2)` and host remainder `[2,11)` in the
neutral primary plane. The available geometry facts do not support the
candidate inner boundary at 8, so the possible stem and attached-pronoun
analysis remains in `alternatives` and `public_projection_eligible` remains
`false`.

### 3.2 Hover cards, compact vs expanded

Hover facts are **hover-only**: they never render at rest. At rest the
renderer shows colour, boundary, and segmentation only (particle contract
§1.1) — plus the `whole_word_gloss` where the page class shows glosses.

Each hover card: `component_surface`, `contextual_gloss`,
`particle_identity` (`{headword, entry_id, sense}` or `null`),
`contextual_function`, `sarf_note`, `nahw_note`, `governor`
(`{loc, surface, relation}` or `null`), `governed_expression`, `scope`,
`attachment` (`{host, boundary}` or `null`), `alternatives` (array),
`reason`, `unresolved` (`null` or message), `entry_link` (path or `null`).
For `1.2.0`, each card also carries `segment_index` and
`morpheme_occurrence_id` (string or `null`). The ordered card, visible
segment, morpheme ownership row, and appearance span-map row MUST agree on
segment identity, morpheme identity, surface, and canonical span. A
position-only match is insufficient.

Two renderer field sets over ONE card object (the renderer selects fields; it
never receives two divergent fact sets):

- **Compact hover** (small viewport / first plaque):
  `component_surface`, `contextual_gloss`, `contextual_function`,
  `entry_link`, and — when non-null — `unresolved`.
- **Expanded hover** (full plaque): all card fields, in the order listed
  above, plus `rootless_pedagogy` when present.

The `unresolved` field may never be dropped from either set when non-null:
honesty is not an expanded-only luxury.

## 4. Entry-link fields

`entry_links[*]`:

- `entry_id` — Qamus entry id (e.g. `b10a1ee04666`, `n0231`). Required,
  non-empty.
- `sense_id` — the sense within the entry, or `null` when the entry has no
  adjudicated sense split yet. The key itself is always present.
- `relation_kind` — closed vocabulary:
  `certified_sense` (certified occurrence→sense link),
  `certified_entry` (certified to the entry, sense pending),
  `candidate_entry` (candidate link; renderer must present as tentative),
  `clitic_component_of_entry` (a sub-token component links to a particle
  entry),
  `root_family_of_entry` (added `1.1.0`, additive per §9: the occurrence
  shares the entry's root family — a root-agreement relation ONLY, never a
  lexeme/entry-membership claim; guard `root_agreement_never_lexeme_edge`.
  The renderer presents it as a "same root" cross-reference, not as "this
  word belongs to this entry").

One occurrence may carry SEVERAL entry-link rows with distinct
`relation_kind`s when each edge has its own evidence and state. Page context,
surface resemblance, and root family never create entry membership. The
`quran:61:5:4` safety sample therefore keeps both retained links explicitly
`candidate_entry`, omits its former root-family claim, and does not convert
the bound v489 appearance page into occurrence entry identity.
- `segment_index` — which segment carries the link, or `null` for the whole
  word.

For a `1.2.0` appearance-bound payload, every link additionally carries:

- `link_state` — `candidate` or `certified`. It must agree with
  `relation_kind`; in particular, `candidate_entry` can never carry a
  certified-looking state.
- `sense_state` — `candidate`, `certified`, `unresolved`, or
  `not_applicable`. A null `sense_id` on `candidate_entry` is
  `unresolved`, not an implicit whole-entry sense.
- `evidence_refs` — a non-empty, unique array of opaque repository evidence
  ids for this edge. A global projection evidence list does not replace
  edge-local evidence.

The `1.2.0` row is closed over
`{entry_id, sense_id, relation_kind, segment_index, link_state, sense_state,
evidence_refs}`. The same typed fields are copied into the corresponding
reverse row and validated byte-semantically through canonical JSON. Thus a
candidate edge cannot become settled-looking reverse membership.

`entry_link_state`:

- `linked` — `entry_links` MUST be non-empty and each row complete.
- `none_yet` — `entry_links` MUST be empty, and the renderer renders an
  honest no-entry state (no dead link, no invented target). §7 W5 board
  requirement 6: the no-entry-link payload is a first-class state, not an
  error.

A payload with empty `entry_links` and state `linked` (or a missing state) is
a validator FAIL ("missing entry links").

## 5. Projection hash — basis and parity

`projection_hash = sha256(utf8(json.dumps(projection, ensure_ascii=False,
sort_keys=True, separators=(",", ":"))))` hex digest.

The hash basis is the ENTIRE `projection` object — page-local metadata is
structurally outside it (§2), so no key-exclusion step is needed. This is the
same canonical-serialization rule as particle contract §2.1; the two hashes
agree whenever the same fact plane is expressed in both shapes.

**Appearance-parity invariant (renderer obligation).** Every appearance of
one canonical `occurrence_id` — reader page, entry card, example card, WBW
hover, dogfood review — carries the SAME `projection_hash`. Same occurrence =
same canonical projection everywhere. `appearance.page_local` (§6) and, in
`1.2.0`, the separately hashed local surface and span map (§6.1) may differ
between appearances. The renderer:

1. MUST treat `projection_hash` as the cache/dedupe key for the fact plane;
2. MUST NOT mutate any `projection` field (a re-serialization that changes
   the hash is a boundary violation, not a formatting choice);
3. MUST surface a hash mismatch between two appearances of one occurrence as
   a defect report back to Fable — never pick a winner renderer-side.

Two occurrences with the same surface (two مَا on one card) are DISTINCT
occurrences with distinct artifacts and hashes; the renderer keys by
`occurrence_id`, never by surface (particle contract §2.3).

## 6. Page-local metadata whitelist (closed, 4 keys)

`appearance.page_local` may carry EXACTLY these keys, nothing else:

| key | meaning |
|---|---|
| `selected_highlight` | whether this appearance is the page's selected/highlighted instance |
| `entry_relationship` | how this page relates to the occurrence (own-entry example, cross-reference, reader context) |
| `focus` | page focus/emphasis state |
| `navigation` | page-local navigation affordances |

The whitelist is closed and owner-decided (particle contract §2.2, flag A).
Any other key under `page_local` — and any page-presentation key smuggled
into `projection` — is a validator FAIL. Extending the whitelist is an owner
decision recorded in the particle contract, never a renderer convenience.

### 6.1 Appearance-local orthography binding (`1.2.0`)

`1.2.0` adds an appearance-local geometry binding without changing
`projection_hash` semantics:

- `appearance.displayed_surface`: exact NFC string from the authoritative
  row selected by `appearance.appearance_id` in
  `qamus/lattice/example-ayah-universe.jsonl`.
- `appearance.canonical_to_appearance_span_map`: one ordered row for every
  canonical segment. Each closed row contains `segment_index`,
  `morpheme_occurrence_id` (string or `null`),
  `canonical_char_start`, `canonical_char_end`,
  `appearance_char_start`, and `appearance_char_end`.
- `appearance.binding_state`: exactly
  `candidate_requires_renderer_capability_acceptance`.
- top-level `appearance_binding_hash`: the separate binding digest below.

Canonical spans equal the referenced `projection.segments` spans. Local spans
are integer, non-empty, ordered, gap-free, combining-mark safe, and tile
`[0, len(appearance.displayed_surface))`. If canonical and displayed surfaces
are equal, the map is an identity map. If they differ, the map preserves
canonical segment and morpheme identity while reconstructing the local
surface. It never copies canonical offsets blindly onto a shorter local
spelling.

The validator joins the envelope `appearance_id` to exactly one authoritative
appearance row and requires exact `canonical_loc`, `page_id`, `page_kind`,
and `displayed_surface` agreement. For an occurrence with a committed
appearance universe, reverse entry-appearance ids must equal that exact set.
A context row with `appearance_index_entry_linked: false` cannot become an
entry-identity edge.

The binding hash basis is this closed object:

```json
{
  "appearance_id": "...",
  "artifact_id": "...",
  "binding_state": "candidate_requires_renderer_capability_acceptance",
  "canonical_to_appearance_span_map": [],
  "displayed_surface": "...",
  "normalization": "NFC",
  "occurrence_id": "quran:S:A:W",
  "page_id": "...",
  "page_kind": "entry",
  "projection_hash": "..."
}
```

`appearance_binding_hash = sha256(utf8(json.dumps(binding_basis,
ensure_ascii=False, sort_keys=True, separators=(",", ":"))))`.

The binding and hash are Fusha-side candidate artifacts. They do not prove
that the website renderer supports orthographic variants, neutral unresolved
classes, or this envelope version. Until the website agent records capability
acceptance under its separate owner boundary, the envelope remains a
non-deployed candidate and `projection.public_projection_eligible` stays
`false`.

## 7. Reverse-link targets (§10 reverse knowledge views)

`reverse_links` gives the renderer both directions without a graph query:

- `occurrence_to_appearances` — every page appearance of THIS occurrence:
  array of `{appearance_id, page_id, page_kind, projection_hash}`. The
  shared hash is required on every row. The renderer uses it for
  "this word also appears on…" affordances and for parity auditing (§5).
- `entry_to_occurrences` — for each linked entry, the occurrence-list shape
  the entry page's reverse knowledge view consumes: array of
  `{entry_id, sense_id, relation_kind, segment_index, link_state,
  sense_state, evidence_refs, occurrences: [{occurrence_id, surface, loc,
  page_refs, projection_hash}]}` in `1.2.0`. `page_refs` is the exact unique
  set of `page_id`s declared in `occurrence_to_appearances`. Each reverse
  typed edge must match exactly one forward `entry_links` edge, and each
  reverse occurrence must bind this payload's occurrence id, canonical
  surface, location, projection hash, and appearance pages. Extra, duplicate,
  phantom, or state-losing rows are validator failures. This is the §10
  reverse view: an entry knows every occurrence that cites it, and each
  occurrence row is enough to render a linked example line without fetching
  the full payload while preserving candidate state.

Reverse links are derived data (Fable-computed from the graph); they are NOT
part of the hashed fact plane, because appearance inventories legitimately
grow as pages are added while the analysis stays fixed.

## 8. Provenance

`provenance`:

- `provenance_class` — closed vocabulary:
  `certified` (renders from certified typed facts),
  `illustrative-from-live` (re-expressed from an already-rich live/candidate
  row; facts not yet certified),
  `illustrative-constructed` (authored to demonstrate a contract state).
  Only `certified` payloads may claim `certification.status: "certified"`.
- `built_by` — producing tool id + version.
- `source_refs` — opaque internal ids/addresses (e.g.
  `corpus:fb1-fixtures#loc=9:46:11`, `two-vote-artifact:quran_2_34_5:...`).
  Internal ids only: no source prose, no private corpus display names, no
  server paths (RM-09).

## 9. Versioning & compatibility

- `schema_version` is semver `MAJOR.MINOR.PATCH`, starting `1.0.0`.
- `1.1.0` adds `root_family_of_entry` without changing the envelope.
- `1.2.0` adds the conditional appearance-local binding and separate binding
  hash in §6.1, plus explicit colour-hover identity and
  `public_projection_eligible`. Legacy `1.0.x` and `1.1.x` payloads remain
  valid without those fields. If any `1.2.0` binding field is emitted, the
  complete shape and all `1.2.0` safety checks apply.
- **Additive-only within a major:** within major 1, Fable may ADD keys and
  ADD closed-vocabulary values; it may never remove keys, rename keys, change
  a key's type, or change hash semantics. The renderer MUST ignore unknown
  keys (forward compatibility) and MUST NOT fail on new enum values in
  non-load-bearing slots (it may fall back to a neutral render and report).
- **Breaking changes bump the major** and require a recorded owner decision
  plus a migration window in which Fable emits both majors side by side.
- **Deprecation policy:** a key is deprecated by marking it in this doc and
  keeping it emitted (with correct values) for at least one full minor
  version before the next major removes it. The validator warns on
  deprecated-key use by producers; the renderer never depends on a key this
  doc marks deprecated.
- The validator pins the accepted major. The focused self-test is executable
  now; repository-harness registration is an explicit dependency of
  `TP-PVN-REANCHOR-HARNESS-INTEGRATION-W1`.

## 10. Unresolved & rootless rendering rules

### 10.1 Rootlessness is taught, never blank

A rootless particle (`root: null`, `kind: particle_clitic_word`) MUST carry a
non-empty `rootless_pedagogy` and the renderer MUST show it in the expanded
hover's ṣarf plane. A null root never renders as an empty field, a dash, or a
missing row. A particle is *differently complete*, never incomplete.

### 10.2 Unresolved is honest, never colour-guessed

When an occurrence's function is not yet adjudicated:

- `projection.unresolved` is
  `{state: "function_unresolved", message, candidate_count, candidates}` —
  `message` is learner-register English ("function not yet adjudicated; N
  candidate analyses"), and the hover presents the candidates as live
  alternatives, not noise.
- Any segment whose analysis is unresolved carries
  `semantic_class: "unresolved"` and `renderer_class: "qg-unresolved"`. The
  renderer styles `qg-unresolved` as an explicitly NEUTRAL state — it MUST
  NOT guess a semantic colour, and Fable MUST NOT emit a semantic `qg-*`
  class for an unresolved segment (validator FAIL either way).
- A candidate analysis renders only in the alternatives/unresolved plane —
  never in the `contextual_function` slot as if certified.
- `certification.status` MUST be `unresolved`; an unresolved evidence state
  can never certify.

For a `1.2.0` capability-gated candidate, `certification.plane` is a closed
map with exactly `attachment_head`, `contextual_meaning`, `entry_links`,
`function`, `governor`, `referent`, `root`, `segmentation`, and
`translation`. Every value is exactly `candidate` or `unresolved`; a missing,
extra, misspelled, or differently valued state is a validator failure. The
primary public plane is strictly neutral regardless of which of those two
open states each fact carries:

- every segment uses `semantic_class: "unresolved"` and
  `renderer_class: "qg-unresolved"`;
- `whole_word_gloss`, segment glosses, and hover contextual glosses are
  `"unresolved"`;
- primary `particle_identity`, `contextual_function`, `governor`,
  `governed_expression`, `scope`, `attachment`, and `entry_link` fields are
  `null`;
- candidate statements occur only in non-empty alternatives whose text begins
  `Candidate only:`;
- `root` remains `null`, `public_projection_eligible` remains `false`, and no
  unresolved dictionary or surface gloss becomes a contextual translation.

This neutral plane is not a universal rendering policy for already-certified
legacy payloads. It is the fail-closed `1.2.0` contract for an appearance
binding that has not passed both linguistic eligibility and renderer
capability acceptance.

## 11. Teaching-plane language discipline

All learner fields — `whole_word_gloss`, `learner_explanation`, segment
`gloss`/`sarf_note`/`nahw_note`, every hover learner value including
`contextual_gloss`, `contextual_function`, identity labels, governor and
attachment labels, alternatives, `sarf_note`, `nahw_note`, `reason`, and
`unresolved`, plus `rootless_pedagogy` and the complete unresolved object — are
learner-register English. Arabic technical iʿrāb formulas (e.g.
"مبتدأ مرفوع وعلامة رفعه", "في محل جر", "مفعول به منصوب") are private-side
analysis prose and may not appear (particle contract §1.4, `norm@1`
N-LANG-01/02). Arabic in these fields is limited to short quoted
object-language forms (surfaces, hosts, governed expressions). The validator
carries the forbidden-formula scan; a leak is a payload defect, and the
website agent must not "translate around" one.

The validator scans both keys and values. External source names,
`informed_by`, private reviewer or workflow prose, build-host metadata,
Windows paths using either slash direction, UNC paths, home paths, private
network addresses, and machine topology are all validator failures. Opaque
internal fact ids remain legal, but source prose does not.

## 12. Committed samples

All in `qamus/examples/website-payloads/`, all green under
`tools/validate_website_payload.py`. `cert status` and `public eligible` are
the payload's actual `projection.certification.status` and
`projection.public_projection_eligible` — the fail-closed values
`tools/website_evidence_resolver.py` and `tools/validate_website_payload.py`
currently require, not a description of what a lane store elsewhere once
claimed:

| file | shows | provenance_class | cert status | public eligible |
|---|---|---|---|---|
| `p007_li_adam_clean.payload.json` | clean لِـ + noun (quran:2:34:5 لِءَادَمَ), segmentation/function/governor-identity/case certified from `qamus/examples/p007-li-pilot/certification`; governor relation + entry sense still unresolved | certified | unresolved | `false` |
| `p007_lillahi_fused.payload.json` | fused لِلَّهِ (quran:12:31:24), clitic + assimilated host boundary, same p007 pilot certification/unresolved split as above | certified | unresolved | `false` |
| `verb_ituni_12_59_5.payload.json` | verb word ٱئْتُونِى: stem + protective nūn + object pronoun | illustrative-from-live | candidate | `false` |
| `noun_libuulatihinna_24_31_23.payload.json` | noun word لِبُعُولَتِهِنَّ: clitic + rooted stem + possessive pronoun | illustrative-from-live | candidate | `false` |
| `unresolved_ma_2_284_2.payload.json` | honest unresolved state, neutral colour, live alternatives | illustrative-constructed | unresolved | `false` |
| `ma_nafiya_93_3_1.payload.json` | occurrence-specific negative `مَا` candidate analysis; its two-vote artifact is valid review evidence (`review_verified`) but is not currently bound by a committed certification-event trail, so `function` sits `review_required` | illustrative-from-live | unresolved | `false` |
| `ma_relative_2_284_10.payload.json` | distinct occurrence-specific relative `مَا` candidate analysis; its evidence ref is a PROOF-P candidate contract fact, which is candidate-only and never certification authority, so `function` sits `review_required` | illustrative-from-live | unresolved | `false` |
| `no_entry_link_17_78_3.payload.json` | `entry_link_state: none_yet` (§7 W5 board requirement 6) | illustrative-from-live | candidate | `false` |
| `multi_entry_liqawmihi_61_5_4.payload.json` | `1.2.0` candidate safety canary: exact `01133eb5431b:u0:x1:w3` appearance join, separate binding hash, geometry-supported neutral opening/host boundary, candidate links and alternatives, no root/governor/meaning/translation promotion, and explicit renderer-capability ineligibility | illustrative-from-live | unresolved | `false` |
| `verb_qamu_2_20_13.payload.json` | verb word قَامُوا (quran:2:20:13): hollow-root stem + built-in subject suffix; a `vn-entry-canaries` lane store once claimed root + lexeme attachment certified, but that lane store is not one of the two committed certification stores this repository's evidence resolver consults, so those facts resolve as non-authoritative and the payload was migrated (`tools/migrate_website_evidence_fail_closed.py`) to honest `unresolved`/`review_required` pending re-certification against currently authoritative repository evidence | illustrative-from-live | unresolved | `false` |
| `noun_rajulayni_2_282_59.payload.json` | noun word رَجُلَيْنِ (quran:2:282:59): stem + dual ending; same lane-store-claimed-but-repo-non-authoritative history and the same fail-closed migration as `verb_qamu_2_20_13`; root was already honestly candidate | illustrative-from-live | unresolved | `false` |

**None of these 11 samples is currently publicly deliverable** —
`public_projection_eligible` is explicit `false` on every one. Only a
`certified` payload whose every `evidence_refs` entry resolves as
`authoritative_for_certification` under `tools/website_evidence_resolver.py`
may ever set it `true`; no sample in this repository currently meets that bar.

The pilot-derived samples re-express `packets/p00-vertical-slice/`
projection artifacts in this contract's shape; their fact content is
unchanged (segment spans corrected to the §3.1 tiling rule, which the pilot
shape predates). Their `provenance_class: certified` describes where the
segmentation/function/governor-identity/case facts render from
(`qamus/examples/p007-li-pilot/certification`); it does not claim the whole
payload is certified — `certification.status` is the honest per-payload
summary, and it is `unresolved` here because the governor-relation and
entry-sense facts are not yet certified.

The `ma_nafiya_93_3_1.payload.json` / `ma_relative_2_284_10.payload.json`
pair and the `verb_qamu_2_20_13.payload.json` /
`noun_rajulayni_2_282_59.payload.json` pair were downgraded from a formerly
claimed `certified` status by `tools/migrate_website_evidence_fail_closed.py`
once the repository evidence resolver could not resolve their cited evidence
as current certification authority (a lane store's own posture claim, an
unbound two-vote artifact, or a candidate-only contract fact are all
non-authoritative). The migration is deterministic, byte-preserves every
other field, and recomputes `projection_hash` and every reverse-appearance
hash — never a hand edit. `docs/qamus/website-handoff/HANDOFF-RECORD.md` §1.2
carries the same corrected inventory.

The `quran:61:5:4` sample is intentionally narrower than the former canary
projection. It binds only the exact `01133eb5431b:u0:x1:w3` appearance
envelope and keeps
the authoritative four-appearance set in reverse declarations. It does not
prove that four concrete envelopes consume the projection, that the website
renderer accepts `1.2.0`, that revocation propagates across those envelopes,
or that the unsupported inner host boundary has acquired a producer. Those
remain A4 and website-capability acceptance gaps.
