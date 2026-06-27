# Procedure: particle-function decision

**Input:** a particle surface + `quran_loc` + surrounding tokens (+ sarf output if any).
**Goal:** pick the particle's **function in context** (and its gloss), or `pending` with the exact
ambiguity. The function — not the surface — is the meaning.

## Steps
1. **Read the content-letter harakah first** (it is the whole distinction for homographs):
   مَن(fatḥa)/مِن(kasra), لِمَ/لَمْ, أَمْ/أُمّ, أَنَّ/أَنْ. If the diacritic is absent and undecidable → pending.
2. **Resolve any proclitic** (فـ/وـ/لـ/بـ) separately, then the core particle (فَمَا = فـ rābiṭa + مَا).
3. **Select the function** from `references/particle-functions.md` using the clause:
   - مَا: is a verb/noun negated (negation) · a relative antecedent (relative) · a question (interrogative)
     · "the fact that" (maṣdariyya) · exclamatory · zāʾida.
   - إِنْ: jawāb present (conditional) · paired with إلا (negation) · before a nominal (lightened إنّ).
   - لَا: jussive after (prohibition) · mabnī mufrad ism after (lā of genus) · else simple negation.
   - أَلَا (opener "behold") vs أَلَّا (أن+لا, subjunctive "that not").
   - أَمْ (interrogative-or, often after hamza) vs أَوْ (disjunction).
   - فاء/واو/لام: pick ʿāṭifa/sababiyya/istiʾnāf/jawāb · ʿāṭifa/istiʾnāf/qasam/ḥāl · jarr/amr/taʿlīl/tawkīd.
4. **Apply negation scope** (`negation`): لَمْ+jussive → past "did not"; لَنْ → future "will never".
5. **Emit** the function + concise authored gloss (e.g. مَن→"whoever", وَمِنَ→"and from", أَلَّا→"that not"),
   or `pending: particle function ambiguous (needs iʿrāb)` with the candidates.

## Two-vote gate
Particle-function decisions are grammar-affecting → require the two-vote gate when iʿrāb-dependent;
a right gloss with wrong function/reasoning is **rejected** (`grammar-risk-gate`).

## Forbidden
- A surface-key gloss that ignores the content-letter harakah (وَمَن inheriting وَمِنَ's "from").
- Glossing مَا as a single fixed word regardless of clause.

## Test
`evals/particle-function-eval.jsonl` + `evals/irab-polysemy-eval.jsonl` — each row's `context_function`
/ `reading` must hold; 3:7:27 وَمَا = "and not", أَلَّا = "that not", فَمَا = "so not".

## Particle-tranche dogfood routing

For high-frequency particle entries, distinguish "string looks acceptable" from
"function is certified." The dogfood controller should emit the exact next gate:

- `function_word_hover_not_learner_ready` when the hover is readable but lacks a
  function, scope, parse key, or learner breakdown;
- `negation_scope_or_particle_function_uncertified` when the particle governs a
  verb/noun mood or case that has not been recorded;
- `exception_structure_uncertified` for `إِلَّا` until the exception polarity,
  type, and case behavior are known;
- `temporal_clause_role_uncertified` for `إِذْ` / `إِذَا` until the temporal or
  conditional clause relation is attached;
- `question_frame_uncertified` for `هَلْ` and hamza until yes/no,
  equalization, or other interrogative function is known.

If the current row only proves a component candidate (`وَ`, `فَ`, `بِـ`, `لِـ`,
`ال`) inside a larger token, keep it out of whole-token entry resolution. It may
feed renderer segmentation, but it must not make the token propagation-safe.
