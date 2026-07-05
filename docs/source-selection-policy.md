# Qamus transclusion source-selection policy

**Status:** adopted 2026-07-04. Machine-enforced by
`qamus/schemas/source-selection-decision.schema.json` +
`tools/validate_source_selection.py` (self-test + accept/reject fixtures wired into
`tools/check_regressions.py`). This doc is the human statement of what those files enforce.

## 0. What this governs — and what it does not

Transclusion reuses an already-authored per-word analysis (a "source" whitelist row for a
surface form) at a **different** Qurʾān location that has the **same exact surface**. This policy
governs **which** authored candidate becomes the source. It does **not** authorize fanout by
itself — the certified-lemma gates (`docs/certification-policy.md`) and the transclusion
semantic/naḥw review gate still apply. Selection is a *pre-condition*, not a licence.

**Target-fitness is out of scope for this gate.** Source-selection decides whether a *source*
analysis is well-formed and canonical for its surface. Whether that source may be applied to a
given *target* occurrence — whether the grammar fits *that* āyah — is the job of the downstream
transclusion semantic/naḥw review gate (`gen_transclusion_review.py`, the L49 gate). A passing
source-selection decision never licenses fanout to an arbitrary `target_loc`.

## 1. The bug this closes (the L15 canary lesson)

The first live transclusion canary held three rows out for qg-class defects. Root cause: the
ad-hoc selector scored candidates by **(fallback-free, then MAXIMUM segment count)** — it
maximised segmentation. For an indivisible word an over-segmented **minority** analysis then
out-ranked the correct single-segment **majority** that already existed in the whitelist:

| Surface | Bad (minority) analysis | Correct (majority) analysis | Majority evidence |
|---|---|---|---|
| مُوسَىٰ (7:127:7) | `[qg-derivative-prefix, qg-noun-stem]` (a false مُـ prefix) | `[qg-proper-noun]` | 9 / 15 occurrences |
| ٱلَّذِى (43:83:7) | `[qg-article, qg-noun-stem]` (a false definite article) | `[qg-relative]` | 34 / 48 occurrences |
| نِسَآءَهُمْ (7:127:18) | `[qg-segment, qg-possessive-pronoun]` (generic fallback on the noun) | `[qg-noun-stem, qg-possessive-pronoun]` | — |

Mechanical structural gates (segment-concat, boundary, qg-class-present) passed all three; only
the sarf/naḥw review caught them. **Maximising segment count is not a safety property.**

## 2. The corrected selector (`choose_source`)

Given a surface and its authored candidate analyses (each an ordered qg-class *signature* with an
occurrence count), choose in this order:

1. **Exact source-address** — if a specific authored occurrence of the surface is requested and
   present, that occurrence is authoritative (`source_address_exact`).
2. **Closed-class allow-list** — relative pronouns (ٱلَّذِى / ٱلَّتِى / ٱلَّذِينَ / …) resolve to a single
   `[qg-relative]`; they never decompose into article + noun (`canonical_allowlist`).
3. **Majority class-signature by OCCURRENCE COUNT** — the modal fallback-free signature across
   candidates wins. **Never** the longest signature (`majority_class_signature`).

And it **blocks** (does not fan out — author instead) when:
- only a generic `qg-segment` fallback exists (`only_generic_fallback`);
- the surface is a genuine **homograph** — fallback-free candidates carry more than one distinct
  analysis and a function-word family (relative/pronoun/particle) is involved, or the analyses
  span more than one grammatical family (`ambiguous_homograph_surface`). e.g. مَا (relative vs
  negative vs maṣdariyya) or a noun-vs-verb homograph. These are authored per-occurrence, never
  majority-voted. (A single content family with several *segmentation* variants — مُوسَىٰ — is not
  a homograph and is safely resolved by majority.)
- two fallback-free signatures tie with no majority (`ambiguous_no_majority`);
- a required closed-class canonical is absent (`relative_canonical_absent`).

**Raw-surface disambiguation (norm-collision homographs).** Some distinct words *collide under
normalization* — e.g. أَمْ ("or", interrogative particle) and أُمّ ("mother", noun) both fold to `ام`,
while أَوْ ("or", disjunction → `qg-alternative`) stays distinct as `او`. For these, source selection
and homograph detection must key on the **raw written surface**, never the normalized form: the
normalized key manufactures a particle-vs-noun homograph that the raw surfaces already keep apart.
Locked by `tools/check_regressions.py` (أُمّ/أَمْ norm_strict collision → pending, never one key-gloss).

## 3. Forbidden (each is a validator FAIL, not a guideline)

- **Over-segmented minority beats the majority** — `majority_class_signature` where the chosen
  signature is not the unique modal fallback-free signature by count (the canary bug).
- **Generic fallback chosen where determinable** — choosing a signature containing `qg-segment`
  while a fallback-free candidate exists. (`qg-segment` is deliberately absent from the canonical
  `qamus-grammar-v1` class enum — it is a runtime fallback only.)
- **Relative pronoun as article + noun** — a closed-class relative resolved to anything but one
  `[qg-relative]`.
- **`qg-article` not wrapping a stem** — an article segment must be immediately followed by a real
  noun/adjective stem (`qg-noun-stem`/`qg-noun`/`qg-adjective`/`qg-proper-noun`), never a frozen
  pronoun or a verb.
- **Invented analysis** — `chosen_signature` that is not one of the candidates.
- **Majority-voting a homograph** — a `majority_class_signature` decision on a surface that is a
  genuine homograph (see §2). Function-word homographs may never be canonicalized by plurality.
- **Laundering through `source_address_exact`** — a decision whose `chosen_signature` does not
  match the candidate authored at the cited `chosen_source_loc` (self-inconsistent), or that cites
  a non-majority over-segmented minority while a clear non-homograph majority exists. The exact-
  cite basis is for genuinely per-occurrence reuse, not a side door around the majority rule.
- **Public-source leakage** — public fields (`surface`, `surface_norm`, `note`) are
  `FORBIDDEN_LABELS`-clean (QAC/MCP/Quran.com/tafsir/OCR/server-path labels never appear).

## 4. What "majority by occurrence count" is — and is NOT

Majority-by-occurrence is a **segment-count tiebreak *within* a set that is already one word** — a
data-grounded way to prefer the correct *segmentation* over a rare over-segmentation of the **same
lexical/grammatical unit**. For مُوسَىٰ the fallback-free candidates are all the nominal proper noun
(`[qg-proper-noun]` 9× vs the false `[qg-derivative-prefix, qg-noun-stem]` 1×), so the modal
signature is the right one; a genuinely segmented verb-with-clitics keeps its real multi-segment
structure because *that* is its majority. In this scoped role it would have auto-corrected the two
canary defects with no scholar in the loop.

It is **NOT** a cross-homograph canonicaliser. Where a surface has genuinely different grammatical
analyses — a function-word homograph (مَا relative vs negative vs maṣdariyya) or a noun-vs-verb
homograph — the plurality parse is not "the answer": forcing it onto every occurrence would
mis-class every minority-but-correct occurrence, re-introducing exactly the "structural gate
passed, grammar was wrong" failure the L15 lesson is about, displaced from over-segmentation to
occurrence-majority. That is why the selector **blocks** homograph surfaces (§2) and defers them
to per-occurrence authoring, and why the closed-class relative allow-list takes precedence over
majority for frozen function words. Majority is a tiebreak inside an already-disambiguated set,
never a substitute for disambiguation.

## 5. Relationship to the existing SoT compiler

`tools/build_canonical_hover_payload_table.py` already keys transclusion identity on
`(surface_norm, root, pos, pattern)` so conflicting analyses become **separate** payloads rather
than competing sources — the architecturally-correct home. This policy adds the *within-surface*
selection discipline (majority, not most-segmented) and the closed-class/fallback guards on top,
and provides the decision-row schema that future canary packets validate against before deploy.
