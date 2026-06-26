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

Rich-hover readiness:

- include form/voice/aspect/person/number in `parse_key.key`, e.g.
  `V:IV:PERF:ACT:1P+OBJ.3MS`;
- assign `qg-verb` to the stem and `qg-pronoun` to visible subject/object
  suffixes;
- hand any governing particle, mood, prohibition, cause/result, or condition
  relation to nahw before finalizing the parse key;
- leave the row pending if the verb can only be described by a root-family or
  infinitive gloss.
