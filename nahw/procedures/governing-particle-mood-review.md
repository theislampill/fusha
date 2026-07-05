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

## Maʿṭūf subjunctive (mood propagated by ʿaṭf)

A subjunctive/jussive governor's force **carries across a coordinating wāw/فاء/ثم/أو** onto the
conjoined verb: in `... حَتَّىٰ تَأْتِيَنَا آيَةٌ` / `أَن يَغْفِرَ ... وَ(أَن) تَأْتِيَ`, the second
verb تَأْتِيَ is **manṣūb as maʿṭūf** on the first منصوب verb, NOT indicative marfūʿ — even though
no naṣb particle sits immediately before it. Record `governor: maʿṭūf ʿalā <first verb> (via أَن/حتّى)`
and mood `naṣb`. Rejecting the ʿaṭf and reading تَأْتِيَ as indicative is a mood error that flips
the tense/aspect of the gloss. Two-vote: the second checker must confirm the ʿaṭf link, not just the
surface fatḥa. (VN-00: تَأْتِيَ was mislabeled indicative.)

For parse-key/color output, include both the governor and the governed verb:

- `parse_key.key`: `NEG:LAM+V:JUSS`, `LAN+V:SUBJ`, `PURP_LAM+V:SUBJ`,
  `FA:CAUSE+V:SUBJ`, or similar compact form;
- display classes: governor as `qg-particle` or `qg-result`, verb as `qg-verb`,
  attached pronouns as `qg-pronoun`;
- blocker: if the mood/governor relation is uncertain, emit
  `governing_particle_mood_uncertified` instead of a rich-hover parse key.
