# Function Token Hover Review

Function tokens must be classified before they are glossed. The same surface or
prefix can mark different grammar roles.

Review:

- `ما`: negative, relative, interrogative, masdariyya/source, conditional,
  negative acting like laysa, or preventive/kāffa.
- `و`: conjunction, oath, comitative, resumption, or circumstantial.
- `ف`: resumption, coordination, result, supplement, or cause.
- `ل`: genitive preposition, purpose, imperative, denial, or emphasis.
- `أ`: interrogative or equalization.
- `لا`: simple negation, prohibition, or negation of genus.
- `إلا`: exception structure with polarity and case effects.

If function controls meaning and evidence is insufficient, route to two-vote or
scholar review. Do not use a default one-gloss particle policy.

## Dogfood finding: readable text is not rich certification

The 2026-06-27 full-corpus dogfood batch exposed rows whose fallback text was
readable but whose grammar was still not learner-ready. Classify these before
repair-preview:

- `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`, `وَٱلْجِبَالُ`,
  `وَٱلشَّجَرُ`: decide whether `وَ` is ordinary coordination, resumption, oath,
  or another role in context. The learner breakdown must teach `وَ` + article +
  host; the public wording must not be treated as sufficient merely because it
  contains `and + the`.
- `وَخُلِقَ`: keep the wāw/resumption or coordination role separate from the
  passive perfect verb. A correct phrase still needs parse-role proof.
- `بِٱلْمَعْرُوفِ`: bā' governs a definite nominal and the resulting PP needs an
  attachment or a precise blocker. Do not certify from host meaning alone.
- `فَأَهْلَكْنَاهُمْ`: decide the fā' role before treating the finite verb and
  object suffix as a reusable family.

If the function role is known enough for a fallback phrase but not enough for a
rich row, classify the row as `string_correct_but_not_rich`,
`needs_renderer_segments`, or `needs_nahw_review`; do not mark it
`rich_certified`.

Rich-hover readiness:

- emit a compact `parse_key.key`, e.g. `OATH+ART+N:GEN:DEF`,
  `FA:CAUSE+V:SUBJ`, `MA:LAYSALIKE`, or `HAMZA:EQUALIZATION`;
- assign display classes by function, not surface: `qg-oath` for oath wāw,
  `qg-comitative` for comitative wāw, `qg-result` for causal/result fā',
  `qg-relative` for a relative pronoun, and `qg-particle` for ordinary
  particles;
- if the function cannot be certified, do not choose a color or parse key as if
  it were resolved. Route to `particle_function_uncertified`,
  `ma_function_uncertified`, `waw_function_uncertified`, or a more exact blocker.
