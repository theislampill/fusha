# Governing Particle Mood Review

Before approving an imperfect verb hover, check whether a governing particle
sets mood, force, or clause role.

Subjunctive governors include:

- `لن`;
- `أن`;
- `كي`;
- `حتى`;
- purpose lām;
- denial lām;
- causal fā';
- comitative wāw.

Jussive governors include:

- `لم`;
- imperative lām;
- prohibition `لا`;
- conditional particles;
- result of imperative contexts.

The hover must reflect the token contribution when the governor changes force:
`let`, `do not`, `so that`, `will never`, `did not`, or condition/result scope.
If the row only has the bare verb lemma, route it for repair.

For parse-key/color output, include both the governor and the governed verb:

- `parse_key.key`: `NEG:LAM+V:JUSS`, `LAN+V:SUBJ`, `PURP_LAM+V:SUBJ`,
  `FA:CAUSE+V:SUBJ`, or similar compact form;
- display classes: governor as `qg-particle` or `qg-result`, verb as `qg-verb`,
  attached pronouns as `qg-pronoun`;
- blocker: if the mood/governor relation is uncertain, emit
  `governing_particle_mood_uncertified` instead of a rich-hover parse key.
