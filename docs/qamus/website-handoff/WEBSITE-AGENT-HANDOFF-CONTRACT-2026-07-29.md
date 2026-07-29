# Website-agent handoff contract — `qamus.website_projection_payload.v1`

**Status:** proposed 2026-07-29 (owner steer §11, WEBSITE-BOUNDARY lane).
**Parties:** the Fusha/Qamus agent ("Fable") and the separate website agent.
**Executable twin:** `tools/validate_website_payload.py` (red-first self-test,
gated in `tools/check_regressions.py`). Where this prose and the validator
disagree, the validator is the bug and this doc is the spec.
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

Sample payloads: `qamus/examples/website-payloads/*.payload.json` (six
committed samples, all validated green by the executable twin).

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
   (FORBIDDEN_LABELS discipline), and no server filesystem paths ever cross
   the boundary in either direction.

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
| `appearance` | yes | where this payload renders: `appearance_id`, `page_id`, `page_kind` (`reader` \| `entry` \| `example_card` \| `wbw_hover` \| `dogfood_review`), `page_local` (§6) |
| `projection` | yes | the fact plane (§3) — the ONLY hashed region |
| `projection_hash` | yes | sha256 hex over the canonical serialization of `projection` (§5) |
| `reverse_links` | yes | §7 |
| `provenance` | yes | §8 |

Appearance identity (`appearance_id`, `page_id`, `page_kind`) and
`page_local` metadata live OUTSIDE `projection` and are never hashed.

## 3. The projection object (fact plane)

Everything inside `projection` is a linguistic fact owned by Fable. Keys:

| key | req | meaning |
|---|---|---|
| `occurrence_id` | yes | repeats the envelope address (self-containment) |
| `surface` | yes | the exact rendered surface, diacritics intact, **NFC-normalized** |
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
| `certification` | yes | `{status, plane}` — `status`: `certified` \| `candidate` \| `unresolved`; `plane`: per-fact map (e.g. `segmentation`, `function`, `governor`, `case`) |
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
  entry).
- `segment_index` — which segment carries the link, or `null` for the whole
  word.

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
same projection everywhere; ONLY `appearance.page_local` (§6) may differ
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

## 7. Reverse-link targets (§10 reverse knowledge views)

`reverse_links` gives the renderer both directions without a graph query:

- `occurrence_to_appearances` — every page appearance of THIS occurrence:
  array of `{appearance_id, page_id, page_kind}`. The renderer uses it for
  "this word also appears on…" affordances and for parity auditing (§5).
- `entry_to_occurrences` — for each linked entry, the occurrence-list shape
  the entry page's reverse knowledge view consumes: array of
  `{entry_id, occurrences: [{occurrence_id, surface, loc, page_refs}]}`.
  `page_refs` is an array of `page_id`s. This is the §10 reverse view: an
  entry knows every occurrence that cites it, and each occurrence row is
  enough to render a linked example line without fetching the full payload.

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
- The validator pins the accepted major; `check_regressions` fails on drift
  between this doc's version rules and the validator.

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

## 11. Teaching-plane language discipline

All learner fields — `whole_word_gloss`, `learner_explanation`, segment
`gloss`/`sarf_note`/`nahw_note`, hover `contextual_gloss`/`sarf_note`/
`nahw_note`/`reason`, `rootless_pedagogy`, `unresolved.message` — are
learner-register English. Arabic technical iʿrāb formulas (e.g.
"مبتدأ مرفوع وعلامة رفعه", "في محل جر", "مفعول به منصوب") are private-side
analysis prose and may not appear (particle contract §1.4, `norm@1`
N-LANG-01/02). Arabic in these fields is limited to short quoted
object-language forms (surfaces, hosts, governed expressions). The validator
carries the forbidden-formula scan; a leak is a payload defect, and the
website agent must not "translate around" one.

## 12. Committed samples

All in `qamus/examples/website-payloads/`, all green under
`tools/validate_website_payload.py`:

| file | shows | provenance |
|---|---|---|
| `p007_li_adam_clean.payload.json` | clean لِـ + noun (quran:2:34:5 لِءَادَمَ), certified pilot analysis | certified |
| `p007_lillahi_fused.payload.json` | fused لِلَّهِ (quran:12:31:24), clitic + assimilated host boundary | certified |
| `verb_ituni_12_59_5.payload.json` | verb word ٱئْتُونِى: stem + protective nūn + object pronoun | illustrative-from-live |
| `noun_libuulatihinna_24_31_23.payload.json` | noun word لِبُعُولَتِهِنَّ: clitic + rooted stem + possessive pronoun | illustrative-from-live |
| `unresolved_ma_2_284_2.payload.json` | honest unresolved state, neutral colour, live alternatives | illustrative-constructed |
| `no_entry_link_17_78_3.payload.json` | `entry_link_state: none_yet` (§7 W5 board requirement 6) | illustrative-from-live |

The pilot-derived samples re-express `packets/p00-vertical-slice/`
projection artifacts in this contract's shape; their fact content is
unchanged (segment spans corrected to the §3.1 tiling rule, which the pilot
shape predates).
