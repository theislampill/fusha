# Rich-Hover Normalization Contract — `norm@1`

Status: **DRAFT — authored, not yet enforced.** Version tag: `norm@1`.
Scope: every row in the live rich-hover whitelist (`rh_live_01_beta_whitelist.jsonl`,
schema `qamus.rh_live_01.public_beta.v1`), 34,322 rows as of 2026-07-12.
Complement to: the C1–C5 defect classifier (`tools/validate_segment_completeness.py`) +
`qamus/reports/rich-seg-known-debt.jsonl`.

## Why this exists

The defect classes answer *"what is broken?"* one failure mode at a time. They do **not**
answer *"what does a correct row look like?"* — so same-page rows of the same root family
drift wildly. Concrete live evidence, all root **ح ق ق**, all on 2026-07-12:

| loc | surface | shape | what's wrong |
| --- | --- | --- | --- |
| `39:71:30` | حَقَّتْ | **norm target** — `root ح ق ق · Form I perfect active`, STEM+SUBJ split, English gloss | (conformant) |
| `38:14:6` | فَحَقَّ | `no public root asserted · FA:فَ + TOK:حَقَّ`, `qg-segment`/`TOK` | root hedged though the sibling asserts ح ق ق; non-canonical colour class; segment-label notation leaked into learner text |
| `7:105:1` | حَقِيقٌ | `adjectival token … no unsupported root added`, sarf `visible piece accounted; no unsupported public source label` | validator meta-language rendered to the learner; root hedged |
| `14:24:7` | كَلِمَةًۭ | `root ك ل م` but segments split كَ as a preposition "like/as" | segmentation steals the first radical; morphline root ↔ segmentation incoherent |

`norm@1` defines CORRECT once, positively, and every row is measured against it.

## Conformance model

Two clause tiers:

- **MUST** clauses are hard: a row is **`norm@1`-conformant** iff it violates zero MUST clauses.
  The headline conformance number counts MUST-conformant rows.
- **SHOULD** clauses are normalization targets tracked as advisory debt (they mostly require a
  new field or a corpus projector that is not yet deployed); they are reported but do not
  subtract from the headline.

Each clause has an ID, a normative statement, a **detector** (how the scanner decides), and a
**mapping** to existing enforcement or a NEW gate/projector.

---

## N-ROOT — root assertion & typed rootless rationale

**N-ROOT-01 (MUST).** A row MUST NOT decline its root with hedge prose. If a row carries a
content segment (`qg-verb-stem`, `qg-noun-stem`, `qg-noun`, `qg-adjective`, `qg-verb`,
`qg-proper-noun`, or the generic `qg-segment`) and does not assert a root, its morphline/notes
MUST NOT contain a hedge such as *"no public root asserted"*, *"no unsupported root added"*,
*"root not certified"*, *"no lexical root"*. A root is **asserted** when it is discoverable via
an evidence tier — certified Qamus entry ownership (**including the entry the row renders on**),
exact source-addressed analysis, or a documented lemma/form relation — and MUST then appear as
spaced Arabic radicals in the root field (top-level `root`, `morphline` as `root ح ق ق …`, or a
segment `sarf_note`).
*Detector:* content-segment row where `_root_asserted()` is false AND a hedge phrase is present.
*Maps to:* partial overlap with **C2** (`whole_token_root`, derived-form single-segment only).
N-ROOT-01 additionally catches the multi-segment hedge shapes C2 skips (فَحَقَّ, حَقِيقٌ).
**NEW gate** for the multi-segment hedge case.

**N-ROOT-02 (SHOULD).** A genuinely rootless row MUST carry an **explicit typed** rootless
rationale drawn from a closed vocabulary — `function-word` / `proper-name` / `jamid-contested`
/ `pending` — in a dedicated field (`no_root_reason` / `not_clitic_reason` /
`rootless_rationale`). Never silent, never hedge prose, never a free-text morphline description
standing in for the typed value.
*Detector:* row asserts no root, no hedge, and carries no recognized typed-rationale field value.
*Maps to:* **NEW field + gate.** Today almost no rows carry the typed field; this is the largest
single normalization gap and is reported as advisory debt.

---

## N-LANG — language discipline in rendered fields

Rendered fields = `learner_explanation`, `token_contribution_gloss`,
`contextual_phrase_gloss`, every segment `gloss_contribution`, `sarf_note`, `nahw_note`, and
`morphline` (learner-visible in the hover plaque).

**N-LANG-01 (MUST).** No internal meta-/process-language in any rendered field. Forbidden
substrings (validator/process vocabulary): *"no unsupported public source label"*, *"no
unsupported root"*, *"no public root asserted"*, *"visible piece accounted"*, *"accounted for"*,
*"retained and accounted"*, *"preserved where relevant"*, *"exposes the visible"*, *"not
separately asserted"*, *"root not certified"*, *"frozen row"*, *"candidate for … certification"*,
*"no unsupported public source"*. Also forbidden: leaked **segment-label notation** — an
uppercase label glued to a form with a colon, e.g. `FA:فَ`, `TOK:حَقَّ`, `ADJ:حَقِيقٌ`,
`N:…` — rendered inside `learner_explanation`.
*Detector:* case-insensitive blocklist over rendered fields + regex `\b[A-Z]{1,6}:\S` in
`learner_explanation`.
*Maps to:* **C4** covers exactly three of these phrases (`as context requires`,
`not separately asserted`, `exposes the visible`). N-LANG-01 is the **superset gate**;
`leak_sot.py` / `validate_public_private_boundary.py` cover provenance labels, not learner prose.

**N-LANG-02 (MUST).** Learner-facing fields MUST be English. Arabic script is permitted only as
short **quoted forms** (surface/root/quoted-form slots). `learner_explanation` MUST NOT be an
Arabic-prose dump: it MUST contain substantive English and MUST NOT be dominated by Arabic
running text.
*Detector:* over `learner_explanation`, count Arabic-script words vs Latin words; flag when
`arabic_words >= 6`, or (`arabic_words >= 4` and `arabic_ratio >= 0.6`), or (`latin_words < 3`
and `arabic_words >= 3`). (Short quoted forms inside an English sentence stay clean.)
*Maps to:* **NEW gate** (no existing class inspects learner-text language balance).

**N-LANG-03 (SHOULD).** `sarf_note` / `nahw_note` MAY use Arabic grammatical terms but MUST lead
with English. *Maps to:* NEW gate (advisory).

---

## N-SEG — segmentation completeness & colour coverage

**N-SEG-01 (MUST).** The concatenation of segment surfaces MUST reconstruct the token surface
(every proclitic / prefix / suffix / pronoun is its own segment at the project's coarse tier;
derivational augments stay stem-internal).
*Detector:* diacritic-folded concatenation of `segments[].surface` equals folded `surface`.
*Maps to:* **existing** completeness gate (`validate_segment_completeness.run_gates`, C1/C5 split
defects). Live corpus already satisfies concat at 100%; kept as a guard.

**N-SEG-02 (MUST) = N-COLOUR-01.** Every segment `class` MUST be a canonical `qg-*` role from
the released scheme (`docs/parser/qamus-grammar-v1-class-map.md`). The generic fallback
`qg-segment` and any non-enum class are forbidden.
*Detector:* `class ∈ CANONICAL_QG` (40 classes); `qg-negative` is a SHOULD (legacy alias);
`qg-segment` / anything else is a MUST violation.
*Maps to:* **existing** `validate_schema_coherence.py` enum; surfaced here as a per-row count.

---

## N-PEDAGOGY — every piece teaches; features are committed

**N-PED-01 (MUST).** Every segment MUST carry a non-empty `gloss_contribution`.
*Detector:* no segment has blank `gloss_contribution`.
*Maps to:* **NEW gate** (schema allows empty today).

**N-PED-02 (MUST).** The morphline MUST commit person/number/voice/mood when knowable at the
exact address — it MUST NOT hedge with *"as context requires"* / *"as the context requires"*.
*Detector:* hedge phrase absent from `morphline`.
*Maps to:* **C4** fallback-leak overlap (the completeness sentence must render only when true).

---

## N-CONSISTENCY — same-surface & entry coherence

**N-CONS-01 (MUST).** Same-surface rows MUST have compatible analyses or a recorded homograph
rationale. In particular, if one occurrence of a bare surface asserts a root and another content
occurrence of the **same bare surface** declines it (hedge / silent), the declining row is
nonconforming.
*Detector:* group by diacritic-folded bare surface; within a group where ≥1 content row asserts
a root, any content row that hedges/omits the root is flagged.
*Maps to:* **NEW gate.**

**N-CONS-02 (SHOULD) — entry-root inheritance.** A row rendered on a Qamus entry page MUST
cohere with that entry's own root/lemma assertion: a content row on entry *E* SHOULD inherit
*E*'s root rather than hedge it. Same-lexeme siblings SHOULD share stem segmentation shape.
*Detector:* requires joining rows to entry root (via `entry_id`) — **NEW PROJECTOR**
(`entry_root_inheritance`), the highest-leverage new build, directly repairs فَحَقَّ / حَقِيقٌ
by inheriting ح ق ق from the entry they render on.

---

## N-COLOUR — one colour language

**N-COLOUR-01 (MUST).** = N-SEG-02. Colours are the **released pre-tier** qg scheme only. The
experimental RM-42 / RM-43 tiered scheme stays parked; no row may emit a tier class.
*Detector:* same canonical-enum check; no `qg-*-t1/t2/tier*` classes.
*Maps to:* existing enum guard + the parked-tier note.

---

## Clause → enforcement map (summary)

| Clause | Tier | Existing enforcement | New gate/projector needed |
| --- | --- | --- | --- |
| N-ROOT-01 hedge | MUST | C2 (subset) | NEW gate (multi-seg hedge) |
| N-ROOT-02 typed rationale | SHOULD | — | NEW field + gate |
| N-LANG-01 meta-language | MUST | C4 (3 phrases) | NEW gate (superset) |
| N-LANG-02 English-only | MUST | — | NEW gate |
| N-LANG-03 note-leads-English | SHOULD | — | NEW gate |
| N-SEG-01 concat completeness | MUST | C1/C5 completeness | (guard) |
| N-SEG-02 / N-COLOUR-01 canonical class | MUST | schema-coherence enum | (per-row surfacing) |
| N-PED-01 gloss present | MUST | — | NEW gate |
| N-PED-02 committed features | MUST | C4 | (shared) |
| N-CONS-01 same-surface root | MUST | — | NEW gate |
| N-CONS-02 entry-root inheritance | SHOULD | — | **NEW PROJECTOR** |

## Conformance measurement

`tools/check_rich_hover_norm.py` scans a whitelist snapshot, reports MUST/SHOULD violations per
clause ID with counts and samples, computes the **fully-conformant** headline (zero MUST
violations), and cross-references each nonconforming row against
`qamus/reports/rich-seg-known-debt.jsonl` (by `loc`, and by `loc`+`row_hash`) to separate
**KNOWN** debt (the C1–C5 classes already saw it) from **NEW** debt (only `norm@1` sees it).
`--self-test` proves each MUST clause red-first against the four drift shapes above plus a clean
`حَقَّتْ`-style row.
