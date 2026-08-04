# Tranche 001 — Derivation & Template Runtime Drills

## What this is

An ordinary-tutor practice surface for twenty-two related misconceptions about **derivational templates and
their downstream reconstruction effects** in Arabic morphology (sarf) and syntax (nahw): certifying a noun's
final-letter class before applying any hidden-exponent rule, selecting a passive template by root class,
excluding a nominal template's own augment from the root, deriving a governing verbal noun's own arguments
and its own weak-radical realization, licensing a participle's identity/state reading against a bounded event,
and grounding grammatical terminology in its own Arabic licensing conditions instead of an imported English
category.

Every item here is graded by the ordinary offline runtime (`tools/fusha_tutor_runtime.py`) against an answer
key (`curriculum/drills/keys/tranche-001-derivation-template-runtime.keys.jsonl`). It is a practice loop, **not
an assessment and never usable as independent assessment**: no item here closes, certifies, or completes any
lesson or unit. This surface routes a learner back to hands-on morphology/syntax practice after a miss; it does
not itself grant mastery of a unit, and it does not close this lesson or complete this unit.

## The six knowledge components (KCs) in this batch

Twenty-two items, one per targeted misconception, are organised into six small, coherent knowledge components.
Each KC is exercised by at least two of the twenty-two items:

1. **`kc-t1-derivation-noun-final-class-declension`** — a noun or participle's case-marking behavior is decided
   by a certified final-letter class (single bare glide preceded by kasra, geminated glide, alif, or
   post-long-vowel hamza), and each class marks or covers its case differently; gemination, glide-vs-alif-vs-hamza
   identity, and the exact indefinite-nominative/genitive glide-drop slots must all be checked before a
   hidden-exponent or full-declension rule is applied.
2. **`kc-t1-derivation-passive-voice-construction`** — the passive is carried by one fixed vowel pairing per
   tense, never by a substituted consonant or any other vowel combination; a hollow root's medial glide cannot
   bear that pairing directly and instead realizes a long-vowel passive melody; a promoted object takes
   nominative case from its new subject position, never the accusative it held before promotion; and the
   construction is defined by omitting the agent, so no agent-naming phrase is ever licensed on it.
3. **`kc-t1-derivation-root-template-letter-discipline`** — a nominal derivative template's own fixed consonant
   is excluded from the root by matching against the closed template inventory, never counted merely from
   adjacency; and two derivatives of one root built on different templates (agent vs. patient) are told apart
   by their own prefix and vowel skeleton, never by the shared radicals alone.
4. **`kc-t1-derivation-idafa-masdar-argument-case`** — a construct's second term is genitive from the construct
   relation itself, independently of the first term's own case; a governing verbal noun's agent is genitive as
   the construct's second term while its object stays accusative under parent-verb government; and a verbal
   noun's weak radical is realized in the verbal-noun template's own slot, never copied unchanged from a finite
   verb's own altered surface.
5. **`kc-t1-derivation-participle-usage-licensing`** — a participle names an identity, role, or persisting
   state, never a single bounded past occurrence, which needs the perfect verb instead; the derivational form
   used must match the event actually intended rather than whichever is simplest or most recently learned; and
   a participle-shaped modifier's label (attribute vs. circumstantial) is decided by the definiteness-agreement
   test against its head, not by case or shape alone.
6. **`kc-t1-derivation-terminology-category-discipline`** — an Arabic grammatical category is learned from its
   own Arabic definition and licensing environment, never by importing an English category's assumptions; a
   forgotten label's function is recovered by decomposing it into its own ordinary Arabic components; and the
   presence or absence of a verb is checked before choosing between a verb-licensed category (fa'il) and a
   verbless-sentence category (mubtada'), since one English label such as "the subject" must never cover both.

## How to use this surface

Load the bank through the ordinary runtime:

```
python tools/fusha_tutor_runtime.py --bank curriculum/drills/keys/tranche-001-derivation-template-runtime.keys.jsonl --select
```

Every item in this bank is `two_vote_required: true`. The runtime can grade the CONTENT of your answer and
reasoning, but it never independently clears a two-vote fact gate: a fully correct answer with fully correct
reasoning is **held**, not cleared, until a separately governed process supplies the external, occurrence-bound
certification this batch does not attempt. A held item is not a miss — content mastery and fact clearance are
reported separately.

## The mc-0094 routing repair

The legacy KC `kc-dictionary-infinitive-leakage` (in `curriculum/kc-catalog.json`) already lists `mc-0094`
among its misconceptions, but its own topic is a different defect: glossing an inflected token with the
dictionary's "to ..." infinitive entry instead of a form-aware gloss. `mc-0094` is actually about deriving a
verbal noun (masdar) from its own template rather than copying the finite verb's own surface alteration — a
masdar-specific reconstruction question, not a hover-gloss-shape question, and its route does not match this
lesson. Reusing `kc-dictionary-infinitive-leakage` here would misdirect remediation to an unrelated lesson, so
this batch instead defines a new, route-local KC, `kc-t1-derivation-idafa-masdar-argument-case`, and pins
`mc-0094`'s primary row (`T1DT-03`) to it.

## What this surface is not

- **Not assessment.** These items are drawn from candidate misconception specifications for pedagogical
  restatement only; the candidate provenance itself is never usable as independent assessment or evidence, and
  none of these twenty-two original items are frozen probes of any kind.
- **Not certification.** No item here is certified, and answering every item correctly does not certify a fact,
  a root, a template assignment, a case decision, or an occurrence. Nothing here is public-eligible, and no
  example carries or implies a canonical Qur'anic occurrence (`quran_example` is null on every row).
- **Not lesson or unit closure.** This batch advances practice coverage for twenty-two specific misconception
  clusters spanning six existing lessons (L2.M4.02, L4.M4.04, L5.M4.01, L6.M3.01, L6.M3.07, L6.M6.04); it does
  not claim that any of those lessons or their parent units are now closed or complete, and no downstream
  process should read this batch as closing this lesson or completing this unit.

## Negative boundaries this batch practices

- A correct label with a wrong derivation/reconstruction reason is rejected — content correctness alone does
  not clear an item; the required reasoning must also be present.
- A noun's final-letter class (single bare glide, geminated glide, alif, hamza) is certified before any
  hidden-exponent or full-declension rule is applied; a class is never assumed from shape or resemblance alone.
- The sound-stem passive vowel-pairing template is never applied consonant-by-consonant to a hollow or otherwise
  weak/geminate stem.
- The surface past-tense alteration of a finite verb is never copied onto a verbal noun's own, independently
  derived template slot.
- No swallowed radical: a template's own fixed augment (an instrument-noun mim, a participle prefix) is never
  promoted to a root letter merely from adjacency.
- Contextual or pattern-suggested meaning is never promoted to a lexeme, sense, translation, occurrence
  identity, or certification decision; a pattern only ever licenses a reconstruction fact, not a lexical
  meaning claim.
- Candidate-specification provenance is pedagogical seed material only and never becomes assessment or
  certification evidence.
- Every item in this bank stays held under the two-vote gate; none is auto-cleared by this runtime.
