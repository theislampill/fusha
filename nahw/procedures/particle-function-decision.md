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
- `entry_pair_collision` for pairs such as `إِذَا`/`إِذًا` and
  `ثُمَّ`/`ثَمَّ` when one inventory contains both functions. Split by strict
  vocalized surface and clause role before any rich certification.
- `composite_particle_uncertified` for `لِكَيْلَا`, `لَيْتَنِي`, and similar
  fused forms until every visible piece and its governor/suffix contribution is
  recorded.
- `pronoun_subordinator_collision` for `أَنَا` versus `أَنَّا`; the former is
  an independent pronoun and the latter introduces a clause with pronoun
  contribution.

If the current row only proves a component candidate (`وَ`, `فَ`, `بِـ`, `لِـ`,
`ال`) inside a larger token, keep it out of whole-token entry resolution. It may
feed renderer segmentation, but it must not make the token propagation-safe.

## VN-06 dogfood: function tokens misfiled through verb-entry candidates

The VN-06 verb/noun tranche found many `م ن ن` entry-family rows where the
surface was actually `مِن`, `مِّن`, `مِنَ`, `مَنْ`, or `ٱلْمَنَّ`.

Route these by function and strict surface, not by the verb-entry source key:

- `مِن` / `مِّن` / `مِنَ` -> preposition and jar-majrūr attachment review.
- `مَنْ` -> relative/interrogative/conditional review by context.
- `ٱلْمَنَّ` -> lexical noun/entry review, not the `مَنَّ` verb.
- Any row whose current English gloss contains a slash or family list
  (`who / whoever`, `sell, buy, or trade depending on form`) remains
  `two_vote_required` until context selects the function or form.

This is not a live-apply instruction. It is a dogfood gate: if a particle or
function token enters a verb/noun tranche through component evidence, keep the
row out of `rich_certified` and out of parse-family propagation.

## VN-07 dogfood: preposition plus pronoun vs verb-family candidate

VN-07 found `مِنِّى` / `مِّنِّى` rows while reviewing the `تَمَنَّى` verb
entry. These are not wish-verb tokens. They are the preposition `مِن` with an
attached first-person pronoun, so the hover lane depends on jar-majrūr
attachment, speaker/referent context, and public wording such as "from me" or
"from Me" by exact address.

Do not certify these from:

- stripped-surface similarity to `تَمَنَّى`;
- source-key or component candidate evidence alone;
- a generic "from" string that hides the attached pronoun.

If the row cannot show the preposition relation and suffix pronoun visibly,
route it to `needs_nahw_review` or `needs_renderer_segments`, not
`rich_certified`.
