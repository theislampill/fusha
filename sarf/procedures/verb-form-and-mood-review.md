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
