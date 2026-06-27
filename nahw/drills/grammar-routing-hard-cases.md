# Drill — grammar routing hard cases

**Goal:** route a token or construction to the right nahw decision before any
hover text is authored. These are the June 25 closure hard-tail cases: the
surface is often familiar, but the function is not safe until the governor,
attachment, clause role, or i'rab is known.

Use this with:

- [`../procedures/function-token-hover-review.md`](../procedures/function-token-hover-review.md)
- [`../procedures/governing-particle-mood-review.md`](../procedures/governing-particle-mood-review.md)
- [`../procedures/ma-function-decision.md`](../procedures/ma-function-decision.md)
- [`../procedures/pp-attachment-review.md`](../procedures/pp-attachment-review.md)
- [`../procedures/exception-and-vocative-review.md`](../procedures/exception-and-vocative-review.md)

## 1. Function particles are not one-gloss words

| construction | decide first | possible route | unsafe shortcut |
|---|---|---|---|
| `مَا` | function in this clause | negative, relative, interrogative, masdariyya, negative like laysa, preventive | one fixed "what/not" |
| `وَمَا` | one written token, multiple grammatical pieces | wāw + the correct `ما` function | counting it as two Qur'anic word tokens, or one undivided gloss |
| `وَ` | particle function | conjunction, oath-preposition, comitative, resumption by context | always "and" |
| `فَـ` | particle function | resumption, coordination, result, supplement, cause | always "then" |
| `أَ` | hamza function | interrogation or equalization ("whether") | treating every hamza as a question |
| `لَا` | negation/prohibition/genus/preventive context | simple negation, prohibition+jussive, no-of-genus, la like anna | generic "no" |
| `يَٰٓأَيُّهَا` | vocative formula pieces | `يَا` call + `أَيُّ` bridge + `هَا` attention + following addressee | one-piece "you (who)" |
| `يَٰٓـَٔادَمُ` | fused vocative + proper-name addressee | call particle plus addressee; case/addressee role matters | bare "Adam" or phrase with no vocative structure |
| `يَٰقَوْمِ` | vocative + possessed/common addressee | call particle plus addressee; possession/iḍāfa may matter | bare "people" or "my people" with hidden call |
| `يَابِسٍ` | not a vocative | sarf must keep yā inside the lexical stem | routing by raw `يا` prefix |
| `وَخُلِقَ` | wāw function + passive verb | resumption/coordination plus passive perfect verb | phrase text with no role proof |
| `بِٱلْمَعْرُوفِ` | bā' relation and PP attachment | preposition + definite nominal + attachment/review gate | host phrase with no bā' role |
| `بِذُنُوبِهِمْ` | bā' relation + possessed host | causal/prepositional relation plus possessor; PP attachment if needed | host-only "sin/sins" |
| `بِرُوحِ` | bā' relation + referent | relation and referent decide "with/by"; host-only is unsafe | bare "spirit" |
| `وَطُورِ` | oath/coordinating wāw | qasam frame and governed host | host-only "Mount" |
| `وَهَٰذَا` | oath/coordinating wāw + demonstrative | frame and demonstrative reference | bare "this" |
| `تُخَالِطُوهُمْ` | attached object pronoun | verb-object relation; "with them" is not optional | treating the entry noun "partners" as the token hover |
| `لَأَعْنَتَكُمْ` | lām/emphasis + Form IV verb + object `كم` | mood/force and "you" need review | bare hardship lemma |
| `تُمْسِكُوهُنَّ` | verb + feminine plural object | object referent and command/context gate | "hold" without "them" |
| `تَكْتُبُوهَا` | verb + object `ها` | referent decides it/her but suffix must remain visible | bare "write" |

When the function is unclear, the correct output is a precise pending reason,
not a broad particle gloss.

## 2. Governors before imperfect verbs

Do not gloss the verb until the governor has been named.

| governor | what it can force | learner-facing consequence |
|---|---|---|
| `لَمْ` | jussive mood with past negation | present-form verb reads as "did not ..." |
| `لَنْ` | subjunctive mood with future negation | "will never/not ..." |
| purpose `لِـ` | subjunctive or purpose clause | lām is not only "for"; it may mean "so that/to" |
| causal `فَـ` | subjunctive after cause/result | fā' is not ordinary coordination |
| prohibition `لَا` | jussive command not to do | route as prohibition, not simple statement |
| imperative/result frame | jawāb amr | result relation belongs to the clause |
| kāda and sisters | ism kāda + imperfect khabar | the imperfect verb is khabar kāda, not a free verb |

## 3. Attachment is part of meaning

A prepositional phrase is not finished when the preposition and majrur noun are
identified. It must attach to something:

- visible verb;
- visible noun/adjective;
- nominal-sentence predicate;
- hidden hāl;
- hidden ṣifa;
- clause-level frame;
- unknown attachment, which remains pending.

If the attachment changes the learner-facing sense and is not certified, route
to `pp_attachment_uncertified`.

## 4. Clause roles that should not be collapsed into token glosses

| role | what to record | unsafe hover behavior |
|---|---|---|
| relative clause | antecedent and clause scope | token gloss copies a whole phrase |
| conditional | shart and jawab | `فَـ` result treated as simple "and" |
| temporal `إِذَا` | temporal condition + answer | bare "when" with no clause role |
| hāl | circumstantial accusative and owner | adjective gloss without role |
| maf'ul li-ajlih | purpose/cause accusative | noun gloss only |
| maf'ul ma'ahu | comitative object with wāw | ordinary conjunction |
| tamyīz | measure/specification and head | number or measure gloss without accusative role |
| murakkab number | compound number pieces + counted noun | translating each piece as an isolated noun |
| vocative | caller particle + munada structure | noun gloss only |
| exception | mustathna, mustathna minhu, type | bare `إِلَّا` without exception frame |

## 4b. VN-00 relationship hovers that are not rich yet

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `لِلَّهِ` | lām + proper noun plus clause role | host-only "Allah" or entry-only "belongs to" with no address proof |
| `لِلْمَلَٰٓئِكَةِ` | lām + article + plural host, then PP attachment | component host "angels" as whole-token hover |
| `بِإِحْسَٰنٍ` | bā' relation plus maṣdar/case role | family spread from ح س ن |
| `بَيْنَكُم` | zarf + attached pronoun and attachment target | treating the letters as a verb-entry candidate |
| `لِيَحْكُمَ` | purpose lām governing subjunctive imperfect | simple "for/to" plus verb lemma |

These rows may already look acceptable in English. They are still not
`rich_certified` until exact address, governor/attachment, parse key, and entry
or no-entry rationale are all present.

## 4c. VN-01 same-surface and suffix-context hovers

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `حَمِيمٍ` | same-surface nominal sense by āyah context | carrying "intimate friend" into a punishment/boiling context |
| `نَكَٰلًۭا` | accusative nominal role plus exact sense review | shackles sense by root family only |
| `مِثْلُ` | nominal comparison construction | verb infinitive "to be like" as best hover |
| `تُبَٰشِرُوهُنَّ` | contextual verb-object relation with `هُنَّ` visible | phrase gloss that hides the attached object |
| `تَجِدُوهُ` | verb-object relation and referent review | bare "to find" |

These rows are not fixed by more English fluency. They need exact address,
parse key, sarf shape, and nahw context agreement before any live repair packet.

## 5. QAC concept metadata is a routing aid only

If concept metadata says a form may be a prophet, historic person, people,
place, plant, body part, book, or other semantic category, use that as a review
flag:

- proper-name/common-word collision;
- named-entity span;
- semantic-family curriculum grouping;
- owner/scholar routing.

Do not use it as a hover translation, public provenance label, or replacement
for sarf, nahw, i'rab, or verse context.

## Graduation check

For a mixed set of twenty rows, produce:

```text
surface:
function/governor/attachment:
required evidence:
allowed lane:
unsafe shortcut rejected:
public hover allowed? yes/no
parse_key.key:
display classes:
pending reason:
```

Pass only when every allowed hover preserves the token's contribution and every
unsafe row is routed to an exact blocker.
For rich-hover readiness, also pass only when each resolved row has a compact
ASCII parse key and segment/function classes from the `qamus-grammar-v1` palette.
If the grammar route is not certified, do not assign a reassuring color; keep
the blocker visible.

Dogfood batch check: the row may be string-populated and still fail this drill.
For each repeated defect class, produce one of:

- nahw procedure updated;
- nahw eval/drill fixture added;
- documented no-op because the issue is Qamus data, entry linkage, or renderer
  only.
