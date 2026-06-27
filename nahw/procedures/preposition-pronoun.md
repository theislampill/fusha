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

## Dogfood finding: VN-11 lām/kāf relation rows stay exact-addressed

VN-11 added relation rows that look English-readable but remain grammar gated:

- `لِفُرُوجِهِمْ` is lām + governed host + `هِمْ`; the preposition relation,
  host noun, suffix, and attachment all need review.
- `لَٱنفَضُّوا۟`, `لَنَاكِبُونَ`, and similar initial-lām rows cannot be
  assumed to be purpose/preposition lām without trusted segmentation and mood
  or POS context.
- `كَسَادَهَا`, `كَبَدٍ`, and `كَالِحُونَ` show that raw kāf/initial-kāf
  shape can be lexical or comparison-like by context. Do not route a raw
  initial letter as a preposition without segmentation evidence.

Rule: relation/function rows require exact function and attachment proof. If
the row is component-only, it stays `component_only_blocker`; if whole-token but
grammar-sensitive, it stays `two_vote_exact_address_review`.

## Dogfood finding: VN-12 comparison and mood-governing relations

VN-12 added rows whose visible strings can look plausible while the function
piece is still uncertified:

- `كَزَرْعٍ` contains a comparison/preposition-like kāf plus governed host.
  The host noun candidate is not whole-token proof.
- `فَلْيُؤَدِّ` combines fā' plus imperative/purpose-like lām on a finite
  host. The lām function and mood/governor must be reviewed before wording is
  trusted.
- `لِّيُوَاطِـُٔوا۟` and similar lām-on-verb rows require function, mood, and
  clause relation review.
- `وَفُرُشٍۢ` has wāw plus a nominal host; a component host candidate does not
  decide whether the public hover should include the conjunction.

Use `comparison_attachment_uncertified`, `lam_function_uncertified`,
`mood_governor_uncertified`, or `component_only_blocker` rather than
propagating from host text.

## Dogfood finding: VN-13 prefixed relation rows stay grammar-gated

VN-13 repeated function/attachment boundaries:

- `وَٱلشَّمْسُ` and `وَٱلْقَمَرُ` are wāw + article + nominal host rows. A
  component host candidate does not certify the whole token or the wāw
  function.
- `وَخَابَ`, `وَزَهَقَ`, `فَصَبَّ`, `وَصَدَفَ`, and `وَقَدَّتْ`
  have prefixed sequence/function pieces plus a finite host; component
  evidence remains a blocker until the whole token is reviewed.
- `بِمُصْرِخِكُمْ`, `بِطَارِدِ`, and similar rows need preposition,
  governed host, suffix or object where present, and attachment proof.

Use `component_only_blocker`, `wa_function_uncertified`,
`fa_function_uncertified`, `preposition_role_uncertified`, or
`pp_attachment_uncertified`; do not convert these rows into safe propagation
from a host gloss.

## Dogfood finding: VN-14 bā', lām, and kāf relation rows stay exact-addressed

VN-14 added relation rows whose host-family prose can look useful while the
function is still uncertified:

- `بِجَهَازِهِمْ` is bā' + governed host + `هِمْ`; the preposition relation,
  noun host, suffix, and attachment all need review before wording can
  propagate.
- `بِدْعًا` and `كَهَيْـَٔةِ` require relation/function and attachment review;
  raw entry prose such as "to invent" or "to shape/form" is not a token hover.
- `لِيُدْحِضُوا۟`, `لِيَمِيزَ`, and similar lām-on-verb rows require lām
  function, mood/governor, and clause relation proof before any public wording
  is trusted.

Use `preposition_role_uncertified`, `comparison_attachment_uncertified`,
`lam_function_uncertified`, `mood_governor_uncertified`, or
`component_only_blocker`. A relation row needs two compatible reasons when the
function affects i'rab, mood, attachment, or English wording.

## Dogfood finding: VN-15 false-prefix and true relation rows

VN-15 added a mixed preposition/function detector warning:

- True relation rows such as `كَالصَّرِيمِ`, `بِٱلْعُرْوَةِ`,
  `بِالْعَرَاءِ`, `بِٱلْعَرَآءِ`, and `بِقَبَسٍ` need preposition or
  comparison function, governed host, and attachment proof.
- False-prefix or ordinary nominal rows such as `أَعْنَٰبٍۢ`, `كَافُورًا`,
  and `بِيضٌۭ` must not enter a PP/function lane merely because a detector saw
  an initial bā/kāf-looking shape.
- Component-only function evidence can route review but cannot certify the
  whole token or relax the two-vote gate.

Use `not_clitic_surface_prefix` when segmentation does not prove a real
preposition/comparison particle. Use `preposition_role_uncertified` or
`pp_attachment_uncertified` when the particle is real but relation or
attachment is not certified.

## Dogfood finding: VN-16 lexical bā' and lām are not particles

VN-16 shows why raw first-letter detectors must stay subordinate to strict
segmentation:

- `لِتَلْفِتَنَا` is a real lām-on-verb candidate and needs lām function,
  mood/governor, finite host, and `نَا` object review.
- `لِبَاسٌۭ` is a lexical noun, not a lām governor merely because it begins
  with lām and kasrah.
- `بِضَٰعَةًۭ`, `بِضَاعَتَهُمْ`, `بِضَٰعَتُنَا`, and
  `بِضَٰعَتَهُمْ` are merchandise/possession rows whose initial bā' belongs
  to the host unless segmentation proves a separate preposition.

Rule: mark false positives as `not_clitic_surface_prefix`. Only a segmented
particle can enter preposition/comparison/lām-function review.
