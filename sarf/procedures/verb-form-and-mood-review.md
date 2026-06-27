# Verb Form And Mood Review

For a verb token, record:

- root and derived form;
- perfect/imperfect/imperative;
- active/passive voice;
- person, number, and gender;
- subject marker or hidden subject;
- object or possessive suffixes;
- visible proclitics before the verb;
- any governing particle that may affect mood or force.

Sarf may certify form and voice. Nahw decides contextual mood and force when a
governor is present: `لم`, `لن`, `لا` of prohibition, imperative lām, purpose
lām, causal fā', comitative wāw, `أن`, `كي`, `حتى`, or conditional particles.

Bare infinitive hovers are unsafe for finite verbs when person, number, suffix,
imperative force, passive voice, or context materially changes the visible
token contribution.

## Dogfood finding: finite verbs need internal composition

The 2026-06-27 dogfood batch promoted two verb defects into permanent checks:

- `يَسْـَٔلُكَ`: record `يَـ` imperfect prefix, `سْـَٔلُ` host stem/root, and
  `كَ` attached object pronoun. The hover may be concise, but the breakdown must
  preserve `OBJ.2MS`; a lemma-style "to ask, question" or a hidden-only suffix is
  not rich-certified.
- `فَأَهْلَكْنَاهُمْ`: record `فَ` separately, then the Form IV perfect active
  1st-person plural verb with attached 3rd-person masculine plural object. A
  fluent phrase such as "so We destroyed them" still needs a parse key and
  component table before it can be used as a model row.

When the subject is supplied by a following explicit noun, the verb form still
keeps its own person/number/gender. Do not replace the finite morphology with a
dictionary entry gloss.

## Dogfood finding: form resolution is not enough for populated verb hovers

The next full-corpus dogfood packet found populated verb hovers that still
behave like dictionary entries. `ثَقِفْتُمُوهُمْ`,
`تُخَالِطُوهُمْ`, `لَأَعْنَتَكُمْ`, `تُمْسِكُوهُنَّ`,
`سَرِّحُوهُنَّ`, `تَمَسُّوهُنَّ`, and `تَكْتُبُوهَا` must preserve the
finite verb shape and attached object, not only the root/lemma meaning.

For these rows, the sarf decision must include:

- aspect and form where known;
- subject agreement or subject suffix;
- visible object suffix and person/number/gender;
- proclitic or governing particle that may change mood or force.

A hover such as "to find/come upon", "partners", "to hold", or "to write" is a
populated string, not a token hover, when the suffix object is missing. Keep the
row in the dogfood queue until the suffix is visible to the learner or an exact
blocker explains why it cannot yet be shown.

Rich-hover readiness:

- include form/voice/aspect/person/number in `parse_key.key`, e.g.
  `V:IV:PERF:ACT:1P+OBJ.3MS`;
- assign `qg-verb` to the stem and `qg-pronoun` to visible subject/object
  suffixes;
- hand any governing particle, mood, prohibition, cause/result, or condition
  relation to nahw before finalizing the parse key;
- leave the row pending if the verb can only be described by a root-family or
  infinitive gloss.

## Dogfood finding: VN-00 finite-verb leakage

The VN-00 verb+noun calibration tranche found that common populated verb hovers
still leak dictionary prose onto exact finite tokens. Treat these as
`finite_verb_dictionary_gloss_leakage` until the parse key and visible
breakdown are present:

- `قَالُوا`: not a spread definition of saying; record perfect active 3mp.
- `قُلْنَا`: not a bare root; record the imperative/perfect shape and first
  plural subject where applicable.
- `ظَلَمُونَا`: record 3mp subject plus `نا` object; a bare "wronged" or
  infinitive hides the attached pronoun.
- `وَيُرِيكُمْ`: record waw function, Form IV causative sense, and `كم`
  object suffix.
- `وَيُعَلِّمُكُمُ`: record Form II teaching sense and `كم` object suffix;
  do not reuse an omnibus "know/teach/learn" entry gloss.

Passive voice, hamzated/madd-sensitive roots, and derived form are part of the
token, not polish. `قِيلَ`, `ءَاتَيْنَا`, `وَأْتُوا`, and `يُبَيِّن` stay
review-gated until voice/form/root are certified at the exact address.

## Dogfood finding: VN-02 voice, root, and suffix blockers

The VN-02 tranche added more finite-verb blockers:

- `وَفَضَّلْنَٰهُمْ`: Form II perfect active 1cp with `هُمْ` object. Reject
  broad فضل entry prose until the learner can see the subject and object.
- `فُضِّلُوا۟`: passive Form II perfect 3mp. Reject active "to favor" prose.
- `يُولَدْ`: weak-root passive imperfect/jussive under negation. Reject active
  "to have children / beget" family prose.
- `أَصْبَرَهُمْ`: Form IV/exclamatory-looking shape plus `هُمْ`; do not
  inherit a plain Form I صبر infinitive.
- `وَٱصْطَبِرْ`: Form VIII imperative plus `وَ`; do not flatten to "to be
  patient".
- `ٱسْتَـْٔذَنَكَ`: hamzated Form X perfect with `كَ` object; record the suffix
  before any "sought permission from you" hover.
- `فَشُدُّوا۟`: doubled-root imperative 2mp plus `فَ`; do not certify from a
  generic "strong" family entry.

When the exact token has passive voice, imperative force, derived form, or an
attached object, any dictionary infinitive is a blocker, not a fallback.

## Dogfood finding: VN-03 component evidence and finite suffixes

The VN-03 tranche found the same finite-verb failure in new families:

- `عَقَلُوهُ`: perfect plural verb plus `هُ` object. Reject a bare "to
  reason; understand" hover until the suffix and referent are visible.
- `أَعْجَلَكَ` and `وَيَسْتَعْجِلُونَكَ`: derived/finite verb forms with
  attached `كَ`. Reject a bare "to hasten" hover.
- `فَأَهْلَكْنَاهُمْ`: component evidence is useful, but it is not a
  whole-token certificate. Preserve `فَ`, Form IV perfect active 1cp, and
  `هُمْ` object before treating "so We destroyed them" as rich-certified.
- `ذُوقُوا۟`, `كَسَبَ`, `تَحْمِلْ`, `يَجْرِى`, and `بَعَثَ` rows show that
  even unsuffixed finite verbs can inherit dictionary infinitives. They still
  need aspect, voice, person/number/gender, and derived-form review.

Subagent review also flagged passive and weak-root rows (`وَقُضِىَ`,
`تُوَفَّىٰ`, `يَجْرِى`) and doubled-root rows (`تَمَسُّوهُنَّ`, `مَسَّ`).
For these, `norm_strict()` is not enough: expand weak/doubled morphology and
record passive/active voice before authoring a hover.

## Dogfood finding: VN-04 weak roots, shadda, and component-only verbs

The VN-04 tranche repeated the finite-verb leakage pattern in weak, hamzated,
and shadda-bearing forms:

- `فَأَنسَىٰهُ`, `أَنسَىٰنِيهُ`, `نَنسَىٰهُمْ`, and `فَنَسِيَهُمْ`
  come from the defective/hamzated-looking `ن س ي` family. They must preserve
  the finite form, causative or base reading, subject, and object suffix.
- `ذَرْهُمْ`, `فَذَرْهُمْ`, and `وَيَذَرَكَ` are not the dictionary entry
  `to leave someone or something`. They need imperative/imperfect review,
  weak-root recovery, and visible object suffixes.
- `بَدِّلْهُ`, `أُبَدِّلَهُ`, `يُبْدِلَهُمَا`, `وَلَيُبَدِّلَنَّهُم`,
  and `بَدَّلْنَٰهُمْ` need form, voice, subject, object, and emphatic-nun
  handling before the English can be trusted.
- `تُنسَىٰ`, `تُبَدَّلُ`, `يُتْرَكُوا`, and `ٱسْتُحْفِظُوا` are passive or
  governed finite surfaces. Reject active/root infinitives.
- `يَصُدُّونَ`, `يَصِدُّونَ`, `تَصَدَّىٰ`, `أَسَرَّ`, and `تَسُرُّ` need
  shadda/geminate and form evidence; stripped skeletons collapse unsafe rows.

Component-only evidence may explain a host or suffix, but it does not certify
the written token. A VN-04 row with visible proclitic, form marker, passive
vowels, object suffix, or emphatic nun remains `component_only_blocker`,
`token_only_review`, or `two_vote_required` until whole-token evidence exists.

## Dogfood finding: VN-05 finite verbs, voice, and verb-entry nouns

The VN-05 tranche repeated the same defect in new verb families:

- `لِيَسْتَخْفُوا۟`, `يُخْفِينَ`, and `أَخْفَيْتُمْ` are finite derived forms
  in the خ ف ي family. They cannot be certified from a broad "to hide" entry
  gloss without form, voice, person/number, and governor/mood review.
- `فَسَيَكْفِيكَهُمُ`, `كَفَيْنَٰكَ`, `وَقَاسَمَهُمَآ`, and
  `تَبَرُّوهُمْ` preserve visible object suffixes. A learner-facing hover must
  account for `كَ`, `هُم`, `هُمُ`, or `هُمَا`; hidden suffix metadata is not
  enough.
- `ٱسْتُهْزِئَ`, `وَيُسْتَهْزَأُ`, `وَسَيُجَنَّبُهَا`, and `فَعُمِّيَتْ`
  are passive-looking or voice-sensitive rows. Reject active infinitive
  shortcuts such as "to mock" or "to set aside" until passive voice is visible.
- `مُسْتَخْفٍۭ`, `هُزُوًۭا`, `ٱلْوُثْقَىٰ`, `مَّقْسُومٌ`, and
  `لَقَسَمٌۭ` are nominal/adjectival rows inside verb-entry families. Entry
  class does not decide token POS.

For VN-05 rows, a populated English string moves only to
`needs_sarf_review`, `needs_nahw_review`, or `needs_renderer_segments` until
the exact token has form/voice/aspect/person/number, visible suffixes, and any
governing particle recorded. Component-only host evidence remains below the
whole token and cannot create a parse-family hover.

## Dogfood finding: VN-06 verb-entry candidate leakage

The VN-06 tranche exposed a different failure mode: a verb entry can collect
component or family evidence that is useful for search, while the exact token is
not a verb at all.

- `مِن`, `مِّن`, `مِنَ`, `مَنْ`, and `ٱلْمَنَّ` appeared in the `م ن ن`
  verb-entry tranche. These rows must not inherit a `مَنَّ` verb lane: they are
  prepositions, relative/interrogative/conditional particles, or a lexical noun
  by strict surface and context.
- `ثَمَرَةٍ`, `ثَمَرِهِۦ`, and related fruit rows appeared in a verb-entry
  family. They are nominal hosts with number/state/case and sometimes suffix
  morphology, not finite `أَثْمَرَ` hovers.
- `مَرَضٌ`, `مَرَضًا`, and adjectival/health rows appeared beside finite
  `مَرِضْتُ`. Treat the noun/state token separately from the verb.
- `غَضَبٍ`, `خِزْيٌ`, `حَوْلَهُۥ`, `بَيْنَ`, and `مُصَلًّى` show the same
  problem: nominal, adverbial, or place/derived rows can live near verb roots
  but still need their own POS and syntax review.
- `ٱشْتَرَوُا`, `يَوَدُّ`, `ٱسْتَسْقَىٰ`, and `تَلْبِسُوا` are finite verbs
  whose entry glosses contain slash/omnibus prose. Pick the exact form,
  transitivity, voice, and object relation; do not ship "sell/buy/trade
  depending on form" or a bare infinitive as a token hover.

For VN-06, a Qamus entry candidate discovered from a rich component or source
key is not whole-token proof. Before any propagation, classify the token as
function particle, finite verb, lexical noun, nominal derivative, or
component-only evidence. Anything else remains `two_vote_required`,
`needs_sarf_review`, or `needs_nahw_review`.

## Dogfood finding: VN-07 strict surface before verb-family reuse

VN-07 repeated the same rule with different shapes:

- `مِنِّى` / `مِّنِّى` entered the `تَمَنَّى` tranche. The row is a
  preposition plus first-person suffix pronoun, not a Form V wish verb.
- `يَتَمَنَّوْهُ` is a finite Form V imperfect verb with an attached `هُ`
  object. The hover cannot be the entry prose "to desire or wish" unless the
  object contribution is visible.
- `مَوَازِينُهُۥ`, `ٱلْمَوَازِينَ`, `ٱلْمِيزَان`, and `وَزْنًا` entered the
  `وَزَنُوهُمْ` family. They are scales/balance/weight nouns or masdar rows
  with number/state/case and sometimes suffix morphology, not finite "to
  weigh" hovers.
- `فَرِيضَةً`, `مَّفْرُوضًا`, and `فَارِضٌ` are obligation/ordained/old
  nominal rows near `فَرَضَ`. Treat the token POS and derivative shape before
  reusing a verb-entry gloss.

For VN-07 rows, a readable English phrase such as "from", "his scales",
"to desire or wish", or "to ordain" is only a starting clue. The finite verb
form, suffix pronoun, nominal derivative, or particle+pronoun composition
decides the dogfood lane.

## Dogfood finding: VN-08 passive/finite rows and component-only verbs

VN-08 repeated the finite-verb leakage pattern:

- `يُخَفَّفُ` is a passive/imperfect-looking verb surface; do not certify it
  from a broad "to be light or make easy" entry gloss without voice, aspect,
  person/number/gender, and governor/context review.
- `يُبَايِعُونَكَ`, `كَالُوهُمْ`, and `رَكَّبَكَ` carry visible object
  suffixes. The suffix contribution must be present in the learner breakdown.
- `تَرَبُّصُ` is a nominal/masdar-like row in a verb family; it cannot inherit
  finite "to wait" prose.
- `فَتَرَبَّصُوا۟` appeared as component-only evidence. It may guide review,
  but the fā' function and finite plural form keep the row below whole-token
  certification.

Rule: a VN-08 row may be populated and still remain `needs_sarf_review` or
`needs_renderer_segments` until the exact token carries form, voice, suffix,
and component-vs-whole-token proof.

## Dogfood finding: VN-09 finite verb lemma leakage

VN-09 found more populated hovers where the live string was only an entry
infinitive:

- `يَشْتَهُونَ` was shown as `to desire`. The token is an imperfect plural
  finite verb; record aspect, person/number, and context before a hover such
  as "they desire" is reviewable.
- `يَعْصِمُكَ` and `يَجْتَبِيكَ` were shown with entry-family prose while the
  attached `كَ` object was not learner-visible. Preserve the finite verb host
  plus `2ms` object suffix.
- `وَفَدَيْنَٰهُ` is not certified by a ransom-family infinitive. The written
  token contains wāw, a finite/perfect host, and `هُ` object.
- `لِتُضَيِّقُوا۟` is component-only evidence until lām function/mood, finite
  form, and plural subject are reviewed.
- `لِّيَطْمَئِنَّ` needs lām/governor and form/mood review before any
  tranquility-family hover is trusted.

Rule: a VN-09 finite row can be useful evidence and still stay
`component_only_blocker`, `needs_sarf_review`, or `two_vote_required`. Do not
let an entry/root gloss become a public token hover unless the exact written
token exposes form, voice/aspect/mood, person/number/gender, and suffixes.

Weak, hamzated, and doubled roots remain load-bearing: `تَشْتَهِيهِ`,
`ٱسْتَيْـَٔسُوا۟`, `خَرَّ`, and `مُطْمَئِنٌّۢ` need root-class handling before
surface-family reuse.

## Dogfood finding: VN-10 finite form before entry prose

VN-10 repeated finite-verb leakage in a fresh entry range:

- `طَبَعَ`, `ٱسْتَعِينُوا۟`, `تَعَاوَنُوا۟`, `دَمَّرْنَا`, and
  `تَرْهَقُهُمْ` were string-populated from entry prose such as "to seal",
  "to assist", "to destroy", or "to cover". They still need exact aspect,
  voice, person/number/gender, form, and object/suffix review before a token
  hover is learner-safe.
- `فَأَعِينُونِى`, `وَأَعَانَهُۥ`, `فَدَمَّرْنَٰهُمْ`,
  `فَفِرُّوٓا۟`, and `وَمُقَصِّرِينَ` are component-only rows. Their host
  family helps route review, but the whole token still contains fā'/wāw,
  finite or nominal form, and sometimes an object suffix.
- `لِيَغِيظَ` and `لِيُضِيعَ` are lām-on-verb rows. Sarf records the finite
  host; nahw must certify the lām function, mood/governor, and clause
  relation.

Rule: VN-10 candidates may populate English strings without satisfying the
finite-form contract. Do not mark them rich-certified or propagation-safe
until the exact written token exposes the finite host and every visible
clitic/suffix/function piece.

## Dogfood finding: VN-11 finite rows and pronoun collisions

VN-11 repeated finite-form leakage and added a fresh collision class:

- `غَنِمْتُم` / `غَنِمْتُمْ`, `تَسْتَغِيثُونَ`, `يَسْتَغِيثُوا۟`,
  `يُغَاثُوا۟`, and `يُغَاثُ` were populated from entry prose such as
  "to take war gains" or "to cry for aid". They are finite or voice-sensitive
  token rows, not dictionary infinitives.
- `قَبَضْنَٰهُ`, `ٱقْذِفِيهِ`, and `فَقَذَفْنَٰهَا` require the verb host,
  person/number/voice or mood, and the attached suffix/object contribution
  before public wording can be reviewed.
- `فَأَهْلَكْنَاهُمْ` appeared as a known defect but only component evidence in
  this tranche. Keep it blocked until fā' function, finite host, and `هُمْ`
  object agree under exact-address review.
- Standalone pronoun rows such as `هُمْ` / `هُمُ` can collide with a verb-entry
  family. Do not route them as finite verbs; hand them to nahw as pronoun or
  function-token rows.

Rule: VN-11 rows may have a useful Qamus candidate and still remain
`component_only_blocker`, `two_vote_exact_address_review`, or
`needs_nahw_review`. A finite verb candidate never certifies a standalone
pronoun, and component evidence never certifies the whole written token.

## Dogfood finding: VN-12 finite rows and object suffixes

VN-12 repeated the same finite-form failure in a new source-key range:

- `أَضَآءَ`, `تُثِيرُ`, `أَفْرِغْ`, `تَحُسُّونَهُم`, and
  `يُضَيِّفُوهُمَا` were populated from entry prose such as "to light/shine",
  "to stir up/plough", or "to host guests". These are exact finite or
  command-like tokens, not dictionary infinitives.
- `يُحَرِّفُونَهُۥ`, `ثَقِفْتُمُوهُمْ`, `جَاوَزَهُۥ`,
  `فَرَشْنَٰهَا`, and `أَسْرَهُمْ` require the host action plus the attached
  object or possessor/reference contribution before a learner can trust the
  hover.
- `فَلْيُؤَدِّ`, `فَٱصْطَادُوا۟`, `وَجَٰوَزْنَا`, and
  `لِّيُوَاطِـُٔوا۟` are component-only routing evidence. Lām/fā'/wāw
  function, mood, finite form, and suffix roles keep them below whole-token
  certification.
- `تُخَالِطُوهُمْ` surfaced a nominal leak: "partners" is not a finite verb
  hover for the exact written token.

Rule: VN-12 rows may be string-populated, source-linked, or component-linked
and still fail the finite-form contract. Before certification, expose form,
voice/aspect/mood, person/number/gender, subject/object or suffix role, and
whether evidence is whole-token or component-only.

## Dogfood finding: VN-13 finite rows stay below token decisions

VN-13 repeated finite-form and component-boundary defects in a fresh source-key
range:

- `أَحْرَصَ`, `حَرَصْتَ`, `يَحْسُدُونَ`, `يُخَٰدِعُونَ`,
  `صَبَبْنَا`, and `فَاتَكُمْ` are finite or form-sensitive tokens. Entry
  prose such as "to be keen", "to envy", "to deceive", or "to pour" is only a
  routing hint until aspect, form, subject/agreement, and object or suffix
  contribution are visible.
- `لَأَعْنَتَكُمْ`, `ٱقْتَرَفْتُمُوهَا`, `يَسْتَصْرِخُهُۥ`,
  and `فَتَطْرُدَهُمْ` need the finite host plus visible object or suffix
  accounting. Some also carry a function particle that belongs to nahw.
- `وَخَابَ`, `وَزَهَقَ`, `فَصَبَّ`, and `وَقَدَّتْ` are component-only or
  prefixed rows. The host/root family may route review, but the whole written
  token is still blocked until the prefixed function, finite host, and exact
  context are certified.

Rule: VN-13 repair candidates are not live decisions. A row may be useful for
sarf training and still require `rich_metadata_plus_exact_address_review`,
`two_vote_exact_address_review`, or `component_only_blocker`.

## Dogfood finding: VN-14 finite rows split from nominal/POS rows

VN-14 corrected an over-broad detector that initially treated every verb-entry
row as finite. After the correction, the tranche separates finite hosts from
nominal or lexical rows inside the same entry family:

- `تُوَسْوِسُ`, `يَطْلُبُهُۥ`, `يَلْمِزُكَ`, `يُطِيقُونَهُۥ`,
  and `وَدَّعَكَ` are finite or form-sensitive rows. Entry prose such as
  "to whisper", "to request", "to defame", or "to be capable" is only routing
  evidence until the exact token exposes form, voice/aspect, agreement, and
  any object suffix.
- `وَسَطًا`, `ٱلْوُسْطَىٰ`, `أَوْسَطِ`, `ٱلْوَسْوَاسِ`,
  `بَدِيعُ`, `بِدْعًا`, and `نُسْخَتِهَا` are nominal, derivative,
  lexical, or POS-sensitive rows near verb entries. They are not finite verbs
  and must route to nominal/POS review before hover trust.
- `فَوَسَطْنَ`, `وَخَرَقُوا۟`, and `وَمُسْتَوْدَعَهَا` are
  component-only evidence. Their host family can route review, but it cannot
  certify the whole written token.

Rule: first decide whether the exact surface is a finite verb host, a
nominal/POS row, or component-only evidence. Only finite rows use this verb
form contract directly; nominal rows hand off to nominal derivative/POS review,
and component-only rows remain blockers.

## Dogfood finding: VN-15 finite strings and suffixes stay exact-addressed

VN-15 repeated the same finite-form leakage in the `v678-v722` tranche:

- `يُوَفِّقِ`, `يُؤْلُونَ`, `يَأْلُونَكُمْ`, `يَخْذُلْكُمْ`,
  `أَطْفَأَهَا`, and `يَسْتَفِزَّهُم` are finite or form-sensitive rows.
  Entry prose such as "to reconcile", "to vow", "to abandon", "to
  extinguish", or "to incite" is only a routing hint until aspect, form,
  voice, agreement, and object/referent roles are visible.
- `وَقِفُوهُمْ`, `خَوَّلْنَٰهُ`, `لَيَصْرِمُنَّهَا`, and
  `لَيَسْتَفِزُّونَكَ` require the host verb plus object suffix or emphatic
  nūn accounting. A hidden suffix field is not learner-ready morphology.
- `وَتَوْفِيقًا`, `فَيُحْفِكُمْ`, `لِيُطْفِـُٔوا۟`,
  `وَٱسْتَفْزِزْ`, and `فَٱفْسَحُوا۟` may provide component evidence for a
  host or function piece. They remain component-only blockers until the whole
  written token is parsed.

Rule: VN-15 rows may be repair candidates, but none are token decisions. Keep
finite rows in exact-address review until the verb form, mood/governor where
relevant, subject/object suffixes, and component-vs-whole-token boundary are
all visible to the learner.

## Dogfood finding: VN-16 passive and suffix-heavy finite rows

VN-16 found finite rows whose populated strings can sound plausible while still
missing form, voice, or object accounting:

- `كُبِتَ`, `كُبِتُوا۟`, and `كُوِّرَتْ` require passive/voice and
  agreement review. Do not reduce them to entry prose such as "to debase" or
  "to wrap around".
- `يَكْبِتَهُمْ`, `أَلْفَيْنَا`, `نُنَكِّسْهُ`, `فَهَزَمُوهُم`,
  `يَتِرَكُمْ`, `فَـَٔازَرَهُۥ`, and `تَؤُزُّهُمْ` require the finite host
  plus attached object/referent suffix. A learner hover that can be read
  without the suffix is still below certification.
- `لِتَلْفِتَنَا` adds a lām-governed finite host plus `نَا`; sarf can identify
  the host and suffix, but nahw must certify the lām function and mood before
  wording can propagate.

Rule: VN-16 rows remain exact-address repair candidates. Passive voice,
reduplicated/derived stems, and object suffixes are part of the token
contribution, not optional metadata.

## Dogfood finding: VN-17 finite and passive rows remain exact-addressed

VN-17 added another batch where a populated string can look acceptable while
still failing the finite-token contract:

- `رُجَّتِ`, `أُرْكِسُوا`, `زُحْزِحَ`, and `سُعِدُوا` require voice,
  aspect, and agreement review. Do not replace them with dictionary prose such
  as "to shake", "to avert", or "to be happy".
- `أَرْكَسَهُم`, `لَيُزْلِقُونَكَ`, `يَطْمِثْهُنَّ`,
  and `أَظْفَرَكُمْ` require finite host plus visible object/addressee suffix.
- `تَشْخَصُ`, `يَشْوِى`, and `صَغَتْ` require exact form, subject agreement,
  weak/hamzated/root-sensitive review, and context before English wording.

Rule: finite VN-17 rows are repair candidates, not token decisions. Keep them
below live apply until form, voice/aspect/mood, person/number/gender, and
attached suffix roles are visible to the learner and agreed by the required
sarf/nahw gate.

## Dogfood finding: VN-18 finite rows mix motion, haste, and destruction forms

VN-18 adds a compact finite set where entry prose would flatten tense, form, or
object contribution:

- `نَكَصَ` and `تَنكِصُونَ` require exact finite shape and subject/agreement
  review; a bare "to back away" hover is not rich-certified.
- `يُهْرَعُونَ`, `يَهِيجُ`, and `يَهِيمُونَ` require finite imperfect form,
  subject agreement, and context before English wording can propagate.
- `يُوبِقْهُنَّ` requires the finite host plus `هُنَّ` object/referent role.
  A learner hover that can be read without the suffix is still defective.
- `مَّوْبِقًۭا` is a nominal/POS row near a verb family; it routes out of
  finite-verb review and into nominal derivative/POS review.

Rule: VN-18 finite rows remain exact-address repair candidates. Do not let
dictionary infinitives or root-family prose stand in for aspect, form,
agreement, and suffix/object contribution.

## Dogfood finding: VN-19 finite rows need tense, agreement, and mood proof

VN-19 adds finite rows whose current hover can read like entry prose rather
than a token contribution:

- `تَذْهَلُ`, `تَذُودَانِ`, `أَذَاعُوا۟`, `رَبِحَت`, `يَرْتَعْ`,
  and `رَانَ` need exact finite form, subject/agreement, and context before
  they can teach a learner.
- `لَنَسْفَعًۢا`, `فَسَاهَمَ`, `فَشَرِّدْ`, `وَٱشْتَعَلَ`, and
  `لِيَسْحَتَكُم` additionally carry function particles or suffixes, so their
  host evidence is never a complete hover.
- If a finite token is governed by lām, fā', wāw, negation, or another
  function piece, sarf may identify the host but nahw must certify the
  function, mood, and clause relation before wording can propagate.

Rule: VN-19 finite rows remain exact-address repair candidates. A future hover
must name the finite form, voice/aspect/mood where relevant, person/number/
gender, and any attached object or function piece.

## Dogfood finding: VN-20 final finite tranche still rejects entry prose

VN-20 closes the verb/noun tranche series with another finite set where the
current string is populated but not learner-certified:

- `قَصَمْنَا`, `يَنقَضَّ`, `أَقْلِعِى`, `ٱنكَدَرَتْ`, `كُشِطَتْ`, and
  `يَكْلَؤُكُم` need exact finite form, subject/agreement, weak or hamzated
  root handling where relevant, and context before wording can propagate.
- `وَأَقْنَىٰ`, `وَأَكْدَىٰٓ`, `فَتُكْوَىٰ`, `فَٱلْتَقَمَهُ`,
  `فَأَلْهَمَهَا`, `لَمَسَخْنَٰهُمْ`, `وَنَمِيرُ`, and `وَٱنْحَرْ`
  expose useful host evidence, but the whole token includes a function piece,
  suffix, or mood/attachment decision.
- `فَٱلْتَقَمَهُ`, `فَأَلْهَمَهَا`, and `لَمَسَخْنَٰهُمْ` are especially
  unsafe because the learner must see the finite host and attached object or
  referent before trusting the English.

Rule: VN-20 finite rows remain exact-address repair candidates or
component-only blockers. A populated infinitive such as "to bless" or "to
swallow" is not a token hover until form, voice/aspect/mood, agreement,
function pieces, and suffix objects are visible.
