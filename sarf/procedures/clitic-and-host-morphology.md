# Clitic And Host Morphology

Before accepting a host gloss, segment the written token into visible pieces:

- proclitics such as `و`, `ف`, `ب`, `ل`, `ك`, article `ال`;
- the host stem and its root/form/POS;
- suffix pronouns and inflectional endings;
- false-clitic traps such as tanwin-alif, long vowels, and lexical final letters.

An exact host match does not certify the whole written token. The public hover
must account for visible clitics when they affect the token contribution.
For rich-hover readiness, also emit a compact `parse_key.key` and one
`qamus-grammar-v1` display class per segment, following
[`../../curriculum/qamus-hover-parse-key-and-color.md`](../../curriculum/qamus-hover-parse-key-and-color.md).

Examples:

- `بِسَلَامٍ` cannot be only `peace`;
- `بِبَدْرٍ` cannot be only `Badr`;
- `جَادَلُوكَ` cannot be only `to argue/dispute`;
- `وَلْيَعْفُوا` cannot be only `pardon`.

## Dogfood finding: plus-sign hovers are not learner explanations

The 2026-06-27 full-corpus dogfood batch found populated hovers that were
string-correct enough to be readable, but not rich-certified enough to teach the
token. Treat `and + the stars`-style text as a fallback symptom, not completion.

For tokens such as `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`,
`وَٱلْجِبَالُ`, and `وَٱلشَّجَرُ`:

- segment the written token as `وَ` + `ٱل` + host noun;
- keep the visible Arabic token intact in any renderer handoff;
- emit component roles for the renderer and learner breakdown;
- do not count the row rich-certified merely because the visible gloss says
  `and + the ...`;
- send the `وَ` function to nahw before allowing any parse-family propagation.

For tokens such as `بِٱلْمَعْرُوفِ`, record bā' + article + host. A generic
"by what is right/customary" gloss can be understandable, but it is not a
complete rich-hover certification unless the preposition, article, host, and PP
role are visible in the breakdown.

If the clitic function is syntactic rather than purely morphological, sarf
records the segmentation and defers to nahw. Do not invent a color/parse-key
explanation for a segment whose function is still unknown; use an exact blocker
such as `particle_function_uncertified` or `preposition_role_uncertified`.

## Dogfood finding: lexical yā is not automatically vocative

The vocative dogfood packet also exposed the opposite failure: rows such as
`يَابِسٍ` and `يَابِسَٰتٍ` were pulled into the vocative lane by surface shape.
Sarf must not split a lexical stem merely because the raw surface begins with a
yā-like sequence.

Before routing to the vocative procedure, prove a real vocative piece:

- an independent or prefixed call particle `يَا`;
- a vocative support form such as `أَيُّهَا` / `أَيَّتُهَا`;
- a following addressee or a fused munāda form;
- corpus/morphology evidence that the initial letters are not part of the host
  noun/adjective/verb.

If the token is a lexical word such as `يَابِسٍ` ("dry") or `يَابِسَٰتٍ`
("dry [feminine plural]"), keep the whole stem as the host and record
`not_vocative_surface_prefix`. Do not send it to nahw as a vocative merely from
`startswith("يا")`.

## Dogfood finding: lexical initial letters are not clitics

The particle-first dogfood tranche found the same false-positive shape outside
vocatives. A raw token can begin with bā', lām, fā', or kāf without containing a
real attached particle. Examples include `بُكْمٌ`, `بِكْرٌ`, `بِطَانَةً`,
`لِسَانِ`, and `فَالِقُ`.

Before routing a row to preposition/oath/result/clitic review, require positive
segmentation evidence:

- a corpus/morphology segment for the particle;
- a governed majrūr host for `بِـ` / `لِـ` / `كَـ`;
- a clause/function trigger for `فَـ` or `وَ`;
- a token-internal segment record from a trusted parser or rich WBW layer.

If only the raw first letter matches a particle, keep the written token as one
lexical host and record `not_clitic_surface_prefix`. Do not let component-level
candidate evidence from a particle-like initial letter create a whole-token
Qamus entry candidate, propagation-safe parse family, or closure-coverage claim.

## Dogfood finding: component candidates stay below the whole token

The remaining-particle dogfood tranche found rows where component candidates are
real and useful, but still unsafe as whole-token entry evidence:

- `فَأَهْلَكْنَاهُمْ`: result/sequence `فَـ` + Form IV verb host + object
  pronoun `هُمْ`;
- `يَسْـَٔلُكَ`: imperfect verb host + object suffix `كَ`;
- `لَيْتَنِي`: wishing particle host + first-person suffix `نِي`;
- `لِكَيْلَا`: purpose lām + `كَيْ` + negation `لا`.

These pieces may feed a rich renderer or learner breakdown. They must not create
a whole-token particle/pronoun candidate, an `auto_safe` parse family, or a
surface-family hover. If a suffix or composite particle is visible, the
token-addressed hover must account for it or remain pending.

## Dogfood finding: preposition and oath hosts need their governors

The 2026-06-27 preposition/oath dogfood batch found host-only hovers on tokens
whose visible governor is part of the written word.

Sarf must preserve these pieces before nahw chooses the contextual function:

- `بِذُنُوبِهِمْ`: `بِـ` + plural noun host + possessive suffix `هِمْ`.
- `بِذُنُوبِكُم`: `بِـ` + plural noun host + possessive suffix `كُم`.
- `بِرُوحِ` / `بِرُوحٍ`: `بِـ` + host noun; referent and relation stay gated.
- `بِبَابِلَ`: `بِـ` + proper place host.
- `وَطُورِ`: oath/coordinating `وَ` + governed host.
- `وَهَٰذَا`: oath/coordinating `وَ` + demonstrative host.

Do not let an article, preposition, oath particle, or suffix pronoun become
component-only metadata while the public hover reads like the bare host. If the
host is known but the governor/function is not, emit the segmentation and route
to nahw with `preposition_role_uncertified`, `oath_function_uncertified`, or
`pp_attachment_uncertified`.
