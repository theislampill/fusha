# Procedure — particle decision

**Invoke when:** the surface is a closed-set particle / function word.

**Input:** surface (with diacritics), surrounding tokens.

**Checks:**
1. Read the harakah on the **content letter** (after any و/ف proclitic), never the first letter:
   مَن(fatḥa "who") vs مِن(kasra "from", incl. وَمِنَ); لَمْ vs لِمَ; لِمَا vs لَمَّا(shadda); كُلّ vs كَلَّا;
   نِعْمَ vs نَعَمْ; أَنِّي vs أَنَّى ([`../rules/particle-context-rules.json`](../rules/particle-context-rules.json)).
   Use `normalize_ar.haraka_on/shadda_on/is_man_who`.
2. مَا is multi-function (negation / relative / interrogative / maṣdariyyah) — no default; needs context.
3. أَنْ vs إِنَّ by hamza seat (kept by `norm_strict`) + shadda.

**Output:** the function gloss (مَن→"whoever", وَمِنَ→"and from", قَدْ+past→"indeed/already") or pending.

**Forbidden:** deciding on the first letter or on `norm()`; a surface key when undiacritized input collapses the
pair → pending(homograph_haraka). A particle never takes a content-verb/noun gloss.

**Test:** `examples/function-word-decisions.jsonl`; `tools/check_regressions.py` (مَن/مِن، لَمْ/لِمَ، لِمَا/لَمَّا).

## Dogfood finding: particle entries are instance functions

The 2026-06-27 particle-first dogfood tranche audited the highest-impact
particle entries against live WBW rows and confirmed that a populated particle
hover is not certification. Every occurrence needs a function decision, not a
surface-family gloss.

Route repeated classes as follows:

- `مَا` / `وَمَا` / `فَمَا`: use
  [`ma-function-decision.md`](ma-function-decision.md). Record the fired rung
  (negative, relative, interrogative, maṣdariyya, preventive, etc.) or
  `ma_function_uncertain`.
- `مِن` / `مَنْ`: split by content-letter harakah before review. Kasra `مِن`
  belongs to preposition/PP review; fatḥa `مَنْ` belongs to
  relative/interrogative/conditional review.
- `لَا`, `لَمْ`, `لَنْ`, `لِمَ`: record the governed word and mood/case. Reject
  generic dictionary hovers such as "did not or do not" as rich certification.
- `إِنْ`, `إِنَّ`, `أَنْ`, `أَنَّ`, `أَلَّا`: record seat, shadda, and clause
  role before selecting conditional, emphatic, subordinating, or `أن+لا`.
- `ثُمَّ`: record sequential transition and clause scope; a plain "then" hover
  remains string-populated until the scope is attached.
- `هَلْ` and interrogative/equalization hamza: record whether the particle is a
  yes/no question, equalization, or another interrogative frame before accepting
  the hover.
- `إِذْ` / `إِذَا`: route to temporal/conditional clause review, preserving any
  leading wāw separately.
- `إِذَا` / `إِذًا`: split the final alif/tanwīn surface before review.
  `إِذَا` is temporal/conditional or fujāʾiyya; `إِذًا` is inferential/result.
  They cannot share one rich parse key or one entry inventory.
- `ثُمَّ` / `ثَمَّ`: split the sequence particle from the locative/demonstrative
  adverb. A `ثَمَّ` row must not inherit a `ثُمَّ` "then" hover by shared
  consonant shape.
- `هَلْ`: classify as a yes/no interrogative frame and attach the following
  clause. A bundled English list such as "has/have/is/are/will/can?" is not a
  rich-certified hover.
- `مَاذَا`: classify the `ما` function and `ذا` contribution in context. Do not
  certify a blended default such as "what/whatever/that/who".
- `أَنَا` / `أَنَّا`: split independent pronoun from subordinator+pronoun by
  shadda, surface, and clause role.
- `كَيْ` / `لِكَيْلَا`: record purpose-governor scope, negation, and governed
  subjunctive before rich certification.
- `إِلَّا`: route to exception review with polarity, omitted/mentioned
  mustathnā minhu, exception type, and case behavior.

When sarf reports that a token only has component-level particle candidates
(for example `وَ`, `بِـ`, or `ال` inside a richer written token), do not treat
that evidence as a whole-token particle entry resolution. Component candidates
may explain the renderer and learner breakdown; they do not make a parse family
`auto_safe` and do not authorize propagation.
