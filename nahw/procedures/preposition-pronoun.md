# Procedure — preposition + pronoun (jar-majrūr wording)

**Invoke when:** surface is a preposition, or preposition+attached pronoun.

**Input:** surface, referent context.

**Checks:**
1. Render by referent: بِهِ "in it / in him / by it"; لَهُ "for him / belongs to him"; إِلَيْنَا "to us";
   فِيهِ "in it"; عَلَيْهِمْ "upon them"; بِإِذْنِهِ "by His permission" ([`../rules/preposition-pronoun-rules.json`](../rules/preposition-pronoun-rules.json)).
2. The attached pronoun (ـه/ـها/ـهم/ـكم/ـنا) changes wording, not the head sense, and never invents a stem.
3. **Hard guard:** إِلَيْنَا = إِلَى + نا (root أ‑ل‑ي), **NOT** root ل‑ي‑ن; a final ـًا is tanwīn‑alef
   (قُرْءَانًا), not the pronoun نا (`ends_tanwin_alef`).

**Output:** the phrase-role gloss; pending(referent_unresolved) if the referent is out of range.

**Forbidden:** glossing the preposition as a content word; reading إِلَيْنَا as ل‑ي‑ن; `norm()` certification.

**Test:** `examples/function-word-decisions.jsonl` (بِهِ, إِلَيْنَا, عَلَيْهِمْ, فِيهِ); regression إِلَيْنَا≠لين.

## Dogfood finding: bā' plus host plus suffix is not a host gloss

The 2026-06-27 full-corpus dogfood pass exposed populated hovers where the
visible bā' relation, governed host, and possessive suffix were not all
learner-visible.

Route these as preposition phrase rows, not host-only rows:

- `بِذُنُوبِهِمْ`: bā' + plural host + `هِمْ`; a hover such as `Sin.` drops both
  the causal/prepositional relation and "their".
- `بِذُنُوبِكُم`: bā' + plural host + `كُم`; do not leave this as a generic
  suffix pending when the row needs bā' + possessed host review.
- `بِرُوحِ` / `بِرُوحٍ`: bā' + host noun; host-only "spirit" is incomplete until
  the bā' relation and referent are certified.
- `بِٱلْغَيْبِ`: bā' + article + host; a host gloss for "unseen" is not the PP
  contribution unless the "in/by/with" relation is visible.
- `بِبَابِلَ`: bā' + proper place name; host-only "Babylon" loses the locative
  contribution.

If the prepositional relation is clear enough for an authored token hover, the
best public gloss must include it. If the relation or attachment is not
certified, use an exact blocker such as `preposition_role_uncertified`,
`pp_attachment_uncertified`, or `referent_unresolved`; do not mark the row
rich-certified from the host noun alone.

## Dogfood finding: lām plus Allah is not a suffix-pronoun row

VN-08 found high-volume `لِلَّهِ` rows linked near the phrase `حَاشَ لِلَّه`.
These are lām + the proper name Allah in a jar-majrūr construction. Do not
classify the final `هِ` shape as an attached pronoun, and do not certify a
host-only "Allah" hover when the lām relation contributes "to/for/belongs to"
by context.

Route `لِلَّهِ` as:

- lām/preposition or ownership/relation review;
- proper-name governed host review;
- PP attachment / predicate relation review;
- two-vote when the English contribution depends on attachment or phrase
  context.

False suffix guards also matter: `لَهُوَ` contains lām/emphasis + pronoun, and
`لِلَّهِ` contains lām + proper noun, not a noun host plus possessor suffix.

## Dogfood finding: VN-09 true prepositions and false raw-prefix routes

VN-09 added two guards:

- True attached relations such as `كَلَمْحِ`, `بِعِصَمِ`,
  `بِٱلْبُخْلِ`, `كَٱلْجَوَابِ`, `بِسِيمَٰهُمْ`, `بِسَبَبٍ`, and
  `بِٱلشَّفَقِ` need preposition/comparison plus host and attachment review.
  Do not certify from a bare host or from component-only evidence.
- Raw initial letters are not enough. Lexical rows such as `كَادِحٌ`,
  `لِبَدًا`, `لُغُوبٌۭ`, `بَاخِعٌ`, `بَازِغًا`, and `بَاسِقَاتٍ` should not
  enter a preposition lane unless segmentation evidence proves a real
  preposition.

Use `not_clitic_surface_prefix` for lexical initial-letter false positives and
`component_only_blocker` when the preposition/host evidence is below the whole
written token.

## Dogfood finding: VN-10 bā' and lām rows need relation proof

VN-10 added fresh relation rows:

- `بِغَيْظِكُمْ` is bā' + host noun + `كُمْ`; a verb-family hover such as
  "to enrage" hides the preposition, host, suffix, and PP attachment.
- `لِيَغِيظَ` and `لِيُضِيعَ` are lām-on-finite-verb rows. They require lām
  function, governed mood, and clause relation before any public wording is
  trusted.
- `لَزُلْفَىٰ`, `لَمَعْزُولُونَ`, `كِفْلٌۭ`, and `كِفْلَيْنِ` show that raw
  initial letters can trigger false preposition lanes. Use exact segmentation
  evidence before routing to a PP/function decision.

If the relation is not certified, emit `preposition_role_uncertified`,
`lam_function_uncertified`, `mood_governor_uncertified`, or
`pp_attachment_uncertified`. Do not let component evidence from a host family
become a whole-token hover.
