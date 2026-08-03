# Website-agent handoff record — delivery of `qamus.website_projection_payload.v1`

**Date:** 2026-07-29 (owner steer §10, WEBSITE-BOUNDARY delivery lane).
**Parties:** the Fusha/Qamus agent ("Fable") → the separate website agent.
**Contract:** `docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`
(prose spec) with executable twin `tools/validate_website_payload.py`
(red-first self-test, gated in `tools/check_regressions.py`).

This file is the §10 delivery record and the standing coordination point
between the two agents.

---

## 1. What is delivered

### 1.1 Schema

- Payload schema: `qamus.website_projection_payload.v1`.
- Current `schema_version`: **1.1.0**. The 1.0.x → 1.1.0 change is additive
  only (contract §9): one new closed-vocabulary value
  `entry_links[*].relation_kind = "root_family_of_entry"` — a root-agreement
  relation ONLY, never a lexeme/entry-membership claim. Payloads emitted at
  `1.0.0` remain valid; the renderer MUST ignore unknown enum values in
  non-load-bearing slots per §9 (neutral render + report).
- The validator accepts major 1 only; hash semantics are unchanged.

### 1.2 Sample inventory (11 payloads, all green under the executable twin)

All in `qamus/examples/website-payloads/`. `cert status` and `public
eligible` are the payload's actual `projection.certification.status` and
`projection.public_projection_eligible` today, as enforced by
`tools/website_evidence_resolver.py` +
`tools/validate_website_payload.py`'s evidence-resolution check — **none of
the 11 is currently publicly deliverable**:

| # | file | shows | provenance_class | cert status | public eligible |
|---|---|---|---|---|---|
| 1 | `p007_li_adam_clean.payload.json` | clean لِـ + noun (quran:2:34:5), segmentation/function/governor-identity/case certified from the p007-li-pilot certification store; governor relation + entry sense unresolved | certified | unresolved | `false` |
| 2 | `p007_lillahi_fused.payload.json` | fused لِلَّهِ (quran:12:31:24), clitic + assimilated host boundary, same p007 certified/unresolved split | certified | unresolved | `false` |
| 3 | `verb_ituni_12_59_5.payload.json` | verb word ٱئْتُونِى: stem + protective nūn + object pronoun | illustrative-from-live | candidate | `false` |
| 4 | `noun_libuulatihinna_24_31_23.payload.json` | noun word لِبُعُولَتِهِنَّ: clitic + rooted stem + possessive pronoun | illustrative-from-live | candidate | `false` |
| 5 | `unresolved_ma_2_284_2.payload.json` | honest unresolved state, neutral `qg-unresolved`, live alternatives | illustrative-constructed | unresolved | `false` |
| 6 | `no_entry_link_17_78_3.payload.json` | `entry_link_state: none_yet` — first-class no-entry state | illustrative-from-live | candidate | `false` |
| 7 | `multi_entry_liqawmihi_61_5_4.payload.json` | **multi-entry token** لِقَوْمِهِ (quran:61:5:4): THREE entry-link rows with distinct relation kinds — clitic → p007 `b10a1ee04666` (`clitic_component_of_entry`), written form → n912 `65d3d5c51f24` (`candidate_entry`), shared root → v005 `3041d6f44a27` (`root_family_of_entry`); `schema_version` 1.1.0; `1.2.0` neutral candidate-plane binding | illustrative-from-live | unresolved | `false` |
| 8 | `verb_qamu_2_20_13.payload.json` | verb word قَامُوا (quran:2:20:13): hollow-root stem + built-in subject suffix; a `vn-entry-canaries` lane store once claimed root/lexeme attachment certified, but that lane store is outside the two committed certification stores this repository's evidence resolver consults, so those facts resolve non-authoritative | illustrative-from-live | unresolved | `false` |
| 9 | `noun_rajulayni_2_282_59.payload.json` | noun word رَجُلَيْنِ (quran:2:282:59): stem + dual ending; same lane-store-claimed-but-repo-non-authoritative history; root was already honestly candidate | illustrative-from-live | unresolved | `false` |
| 10 | `ma_relative_2_284_10.payload.json` | **same-surface pair, leg 1**: مَا (quran:2:284:10) candidate RELATIVE function (`qg-relative`) — cites PROOF-P candidate-contract fact `sha256:c5e69dac…`, which is candidate-only evidence and never certification authority | illustrative-from-live | unresolved | `false` |
| 11 | `ma_nafiya_93_3_1.payload.json` | **same-surface pair, leg 2**: مَا (quran:93:3:1) candidate NAFIYA function (`qg-negation`) — cites two-vote bundle `two-vote-artifact:quran_93_3_1:v11`, valid review evidence (`review_verified`) but not currently bound by any certification-event trail | illustrative-from-live | unresolved | `false` |

Provenance honesty notes:

- Samples 3–4 re-express already-rich live/candidate rows and are kept
  alongside the canary-derived samples 8–9 deliberately: the renderer must
  handle both provenance classes.
- Samples 10–11 are the **same-surface / different-analysis** requirement
  (steer §19): one entry (`b8e480aebafe`), one written surface مَا, two
  occurrences with two DIFFERENT occurrence-specific candidate analyses,
  neither currently certified, each carrying its own occurrence-level
  evidence ref (fact id / two-vote artifact id in `evidence_refs`,
  provenance-marked). The renderer must key everything on `occurrence_id` +
  `projection_hash` — never on surface text — and the two payloads must
  never share a cache entry. Sample 5 (`unresolved_ma_2_284_2`) is the
  honest third leg of the same surface: unresolved, neutral render.
- Sample 7 is honest about its rungs: the p007 morpheme row is a rung-1
  deterministic **candidate** (attachment geometry), the jarr governor fact
  was engine-REFUSED pending a two-vote bundle, and no plane key is
  certified — the `1.2.0` neutral candidate-plane binding keeps the whole
  primary plane unresolved (root/governor/meaning/translation stay `null`).
- Samples 8–9 and 10–11 were downgraded by
  `tools/migrate_website_evidence_fail_closed.py` from a formerly claimed
  `certified` status once `tools/website_evidence_resolver.py` could not
  resolve their cited evidence as current repository certification
  authority. This is a committed, deterministic, byte-preserving repair
  (hashes recomputed, every other field untouched) — never a hand edit.
  Nothing in these payloads creates or upgrades certification; an
  `evidence_refs` entry's mere presence never certifies by itself.

### 1.3 Expected rendering (per the projection contract)

- **At rest:** colour, boundary, and segmentation only — segments are
  coloured by `renderer_class` (`qg-*` vocabulary), sliced by the §3.1
  spans; `whole_word_gloss` appears where the page class shows glosses.
  Hover facts NEVER render at rest.
- **Hover, compact set:** `component_surface`, `contextual_gloss`,
  `contextual_function`, `entry_link`, plus `unresolved` when non-null.
- **Hover, expanded set:** all card fields in §3.2 order, plus
  `rootless_pedagogy` when present. `unresolved` may never be dropped from
  either set when non-null.
- **Rootless particles** (`root: null`, particle kind) show
  `rootless_pedagogy` in the expanded ṣarf plane — never an empty field or
  a dash (§10.1).
- **Unresolved** segments render the neutral `qg-unresolved` style only —
  no colour guessing; candidates render in the alternatives plane, never in
  `contextual_function` (§10.2).
- **Multi-entry tokens** (sample 7): each `entry_links` row renders in its
  own register — clitic link on the clitic segment, form link as the word's
  entry link, `root_family_of_entry` as a "same root" cross-reference. The
  renderer never collapses distinct relation kinds into one "belongs to"
  presentation.
- **`entry_link_state: none_yet`** renders an honest no-entry state: no
  dead link, no invented target (§4).

### 1.4 Test obligations carried across the boundary

1. **Parity (contract §5):** every appearance of one `occurrence_id` must
   carry the same `projection_hash`; `projection_hash` is the cache/dedupe
   key; a mismatch between two appearances is a defect REPORT back to
   Fable, never a renderer-side pick. The renderer must never mutate a
   `projection` field (re-serialization that changes the hash included).
2. **Readback:** for each consumed payload the website agent should be able
   to read back, byte-identically, the `projection` object it renders from
   (slice-by-span and join-segments must reconstruct the same surface,
   §3.1). Recommended: run `tools/validate_website_payload.py` against any
   payload before first render — it is the executable contract twin and
   validates the committed samples green in
   `tools/check_regressions.py` (WEBHANDOFF gates, 11 samples).
3. **Forward compatibility (§9):** unknown keys are ignored; unknown enum
   values in non-load-bearing slots get a neutral render plus a report.

## 2. Delivery channel

The website agent reads this repository. Standing locations:

- Contract (spec): `docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`
- Executable twin: `tools/validate_website_payload.py`
- Sample payloads: `qamus/examples/website-payloads/*.payload.json`
- Response format: `docs/qamus/website-handoff/RESPONSE-TEMPLATE.md`
  (supported fields / unsupported fields / renderer assumptions / parity
  results / open questions / adoption blockers — one response per adoption
  round, filed into §3 below).
- Coordination point: **this file** (`docs/qamus/website-handoff/HANDOFF-RECORD.md`).
  Questions, defect reports, and contract-change requests from the website
  agent are recorded in §3 below; Fable answers here and, where needed,
  revises the contract + validator + samples in one change.

A copy of this record is handed to the owner for direct delivery to the
website agent as `packets/WEBSITE-HANDOFF-DELIVERY-2026-07-29.md`
(dawahwiki packets tree).

## 3. Open questions (website agent)

*None yet — awaiting website-agent questions. Append here; each item gets
an answer recorded in place.*

## 4. Boundary restatement

- Fable owns the graph, schemas, typed facts, certification, payloads, and
  validators (`qamus/**`, `docs/qamus/**`, `tools/validate_*.py`). Fable
  never edits renderer files — no template, CSS, JS, or live-page change is
  ever authored from the Fusha/Qamus side.
- The website agent owns templates, renderer, CSS, JS, and live pages. It
  CONSUMES payloads only: it may not add, edit, infer, translate,
  re-segment, re-gloss, re-colour, or "fix" any linguistic fact — including
  apparently trivial ones. A payload defect is reported back across the
  boundary (§3 above), never repaired renderer-side.
- The `qg-*` renderer class names are the interface: Fable assigns classes,
  the website agent styles them; neither side crosses.
- All refs are opaque internal ids. No source prose, no private corpus
  names (FORBIDDEN_LABELS), and no server filesystem paths cross the
  boundary in either direction (RM-09).
- Nothing in a website payload can create, upgrade, or imply certification
  (`docs/certification-authority.md`).
