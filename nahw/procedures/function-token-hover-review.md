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
