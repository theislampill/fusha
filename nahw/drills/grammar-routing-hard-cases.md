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

## 4d. VN-02 voice, negation, and referent gates

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `يُولَدْ` | passive/jussive under negation; decide with sarf + negation gate | active "to have children / beget" family prose |
| `لَسْتُنَّ` | finite laysa form with 2fp subject and predicate governance | generic "is/are not" without subject suffix |
| `أَوَلَيْسَ` | interrogative + waw + laysa composition | bare negation/laysa component hover |
| `يُحْيِي` | verb POS and referent check | Prophet Yahya name hover |
| `صَالِحًا` | common adjective vs Prophet name by exact context | surface-family propagation |
| `عَادَ` | finite verb vs people-name by harakāt/POS/context | proper-people hover |
| `ٱلْمَسِيحُ` | title/article/case rich metadata | hiding title form inside another proper-name entry |

If the row is readable but not explainable through exact token identity,
function, and referent, keep it `populated_uncertified`.

## 4e. VN-03 noun/verb component and suffix-context gates

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `فَأَهْلَكْنَاهُمْ` | `فَ` function plus Form IV verb-object stack; two-vote whole-token proof | treating component evidence as a resolved row |
| `ضَعِيفًا` | nominal/adjectival accusative role and predicate/state context | assuming the good English word "weak" is rich certification |
| `ٱلدِّينِ` | definite/genitive noun role, often construct context | verb infinitive "to be bound..." |
| `دِينُكُمْ` | possessed noun with `كُمْ`; construction decides wording | broad faith/religion prose with no possessor |
| `بِعَهْدِ` | attached bā' plus majrūr nominal and PP attachment | verb phrase "to make a covenant..." |
| `زِينَتَهُنَّ` | nominal host plus feminine-plural possessor; referent/context review | verb-family or host-only adornment prose |
| `وَيَسْتَعْجِلُونَكَ` | wāw function plus verb-object relation | bare "to hasten" |

Readable English is not enough. A row remains `populated_uncertified` when the
learner cannot see the function particle, noun role, attached possessor/object,
or i'rab relation that makes the wording true.

## 4f. VN-04 weak verbs and ذ ك ر POS/voice routing

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `فَأَنسَىٰهُ` | fā' relation plus finite weak/causative verb and `هُ` object | root infinitive "to forget" |
| `ذَرْهُمْ` | imperative force plus `هُمْ` object and clause context | entry prose "to leave someone..." |
| `وَيَذَرَكَ` | wāw function, governed mood/context, and `كَ` object | bare weak-root gloss |
| `ٱلذِّكْرَ` | definite nominal role and local sense | verb infinitive "to remember" |
| `ذُكِرَ` | passive finite verb and clause role | noun-entry or active/root-family prose |
| `وَصِيلَةٍ` | wāw function plus customary noun/case review | host-only custom noun string with no particle/case |

The same root may yield a masculine noun, a reminder noun, or a passive verb.
Nahw must keep the clause role and any particle relation separate from sarf's
root/POS decision.

## 4g. VN-05 verb-entry nouns and body-part referents

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `يُوصِيكُمُ` | finite verb plus `كُم` object and command/instruction context | entry infinitive "to instruct..." |
| `تَبَرُّوهُمْ` | finite verb plus `هُمْ` object and object relation | root-family kindness prose |
| `ٱلْقَصَصِ` | definite noun/story role and local case/context | verb infinitive "to relate a story" |
| `غَالِبٌ` | nominal/active-participle role | finite/infinitive "to overcome" |
| `فَرِجَالًا` | whole-token proof plus travel/body-part context | component-only "legs" |
| `يَدَيْهِ` | dual/suffix morphology plus idiom/referent review | omnibus `hand` entry paragraph |
| `وُجُوهَهُمْ` | plural/suffix morphology plus referent-sensitive face/context review | one hover listing face, pleasure, daybreak, and divine-reference alternatives |
| `لَّازِبٍ` | adjective/host role; no lām particle unless segmentation proves it | lām-preposition or lām-purpose route from first letter |

VN-05 rows prove that "readable" English is not equivalent to learner-safe
nahw. If the row needs object referent, PP/idiom attachment, body-part sense,
or false-clitic rejection, keep it out of `rich_certified` until the exact
address has a context decision.

## 4h. VN-06 function-token and verb-entry candidate collisions

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `مِن` / `مِّنَ` | preposition + jar-majrūr attachment review | treating the row as evidence for verb `مَنَّ` |
| `مَنْ` | relative/interrogative/conditional function by clause context | merging it with `مِن` or a verb root family |
| `ٱلْمَنَّ` | definite lexical noun entry review | verb-entry or particle-family propagation |
| `بَيْنَ` | locative/adverb/prepositional construction by context | broad verb-entry candidate from source key |
| `حَوْلَهُۥ` | adverbial/nominal host plus `هُ` suffix | host-only "around" with no possessor/reference review |
| `ثَمَرَةٍ` | noun role, case/state, and local referent | `to bear fruit` from the verb entry |
| `مَرَضٌ` | noun/state and referent-sensitive sickness context | finite verb or omnibus spiritual-sickness prose |
| `ٱشْتَرَوُا` | exact form and context-selected contronym sense | "sell, buy, or trade depending on form" |

VN-06 proves that candidate enrichment is not certification. If the token
arrives through a component-only or source-key join, nahw still decides the
function, attachment, and context before the hover can be learner-safe.

## 4i. VN-07 preposition, near-verb, and noun-family routing

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `مِنِّى` / `مِّنِّى` | `مِن` preposition + first-person suffix and attachment/referent context | treating it as `تَمَنَّى` evidence |
| `يَتَمَنَّوْهُ` | finite Form V verb plus `هُ` object | bare wish-family infinitive |
| `يَكَادُ` / `كَادُوا` | kāda-sister construction and following predicate/context | generic "to almost do" |
| `مَوَازِينُهُۥ` | plural noun plus suffix and judgment/scales context | finite `to weigh` |
| `فَارِضٌ` / `فَرِيضَةً` | noun/adjective/masdar role by case and context | verb-entry "to ordain" |

The same root family can produce a governed particle row, a finite verb, a
near-verb construction, a masdar, or a possessed noun. Candidate linkage only
points to a review lane; nahw still decides function, attachment, and
contextual contribution.

## 4j. VN-08 exception, PP, and suffix false-positive routing

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `إِلَّآ` | exception frame: polarity, mustathnā/minhu, type, case policy | "except" string alone |
| `إِلًّۭا` | lexical noun/POS row | exception-particle route from stripped surface |
| `لِلَّهِ` | lām + Allah proper-name PP and attachment/predicate context | host-only "Allah" or false suffix-pronoun route |
| `بِكْرٌ` | lexical noun/adjective exact surface | false bā' preposition split |
| `بِالْخُنَّسِ` | bā' + article/host + attachment review | component-only "lurking" |
| `بِزَعْمِهِمْ` | bā' + masdar/host + `هِمْ` + attachment | bare "to claim" |
| `شَانِئَكَ` / `إِصْرَهُمْ` | noun host plus suffix/referent | host-only "hater" or "burden" |

VN-08 teaches two negative controls: exact surface can turn an apparent
function token into a lexical noun, and proper-name PP rows can look like suffix
rows when the detector only sees final letters. Do not let either path weaken
the two-vote gate.

## 4k. VN-09 lām/mā, suffix, and renderer-only routing

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `لِمَا` | lām relation plus classified `ما` function and attachment | using "for what/to that which" as proof |
| `لَّمَّا` | negative/temporal/exception construction by context | merging with `لِمَا` or lexical `لَمَم` |
| `لِتُضَيِّقُوا۟` | lām function/mood plus finite plural verb | component-only ضيق evidence |
| `كَلَمْحِ` | comparison/preposition plus host and attachment | host-only blink gloss |
| `يَعْصِمُكَ` | finite verb plus `كَ` object | infinitive "to protect" |
| `أَقْوَٰتَهَا` | nominal host plus `هَا` suffix and referent | host-only sustenance |
| `لَأَوَّٰهٌ` | exact lexical/POS review; no raw lām route unless segmented | false preposition/emphasis split |
| renderer-only rows | metadata backfill if no grammar defect exists | inventing a new sarf/nahw rule for missing display segments |

VN-09 separates three outcomes: grammar defect, component-only blocker, and
renderer metadata miss. Do not treat a populated hover as rich-certified unless
the function pieces, suffixes, parse key, and learner-facing breakdown are
present.

## 4l. VN-10 lām/bā', suffix, and renderer-only routing

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `بِغَيْظِكُمْ` | bā' + host + `كُمْ` + PP attachment/referent | verb-family "to enrage" |
| `لِيَغِيظَ` / `لِيُضِيعَ` | lām function, mood/governor, and finite host | component-only host evidence |
| `وَارِدَهُمْ` | suffix/referent and POS review | entry-family prose with hidden `هُمْ` |
| `وَقُودُهَا` | nominal host plus `هَا` suffix and context | host-only fuel wording |
| `ٱلْمُسْتَعَانُ` | nominal/passive-participle-like role and referent | "to assist" infinitive |
| `ٱلْمُوقَدَةُ` | passive participle/adjectival role | active kindling verb family |
| `حَثِيثًۭا` and similar rows | renderer metadata backfill if wording survives review | claiming rich certification from string presence |

VN-10 keeps the apply boundary explicit: none of these rows can be live-applied
from dogfood alone. They need exact token identity, rich segments, compatible
sarf/nahw reasoning, and two-vote/MCP/source evidence where grammar-sensitive.

## 4m. VN-11 pronouns, lām/kāf rows, and known component defects

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `هُمْ` / `هُمُ` | standalone pronoun role and referent review | verb-entry source-key propagation |
| `لِفُرُوجِهِمْ` | lām relation + host + `هِمْ` + PP/attachment | host-only private-parts gloss |
| `كَسَادَهَا` / `كَبَدٍ` | exact lexical or relation classification | raw kāf as comparison/preposition |
| `لَٱنفَضُّوا۟` | lām function/mood plus finite host | treating initial lām as automatically safe |
| `فَأَهْلَكْنَاهُمْ` | fā' + finite host + `هُمْ`, whole-token proof | component-only host evidence |
| `كُفُّوٓا۟` | POS/mood review | noun-tranche entry text as token hover |
| renderer-only rows | metadata backfill if no grammar defect exists | claiming rich certification from text presence |

VN-11 reinforces the edit boundary: a row can be populated, source-linked, or
component-matched and still fail rich hover certification. Route by exact
token, role, attachment, and compatible reason before any family propagation.

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

## 4n. VN-12 comparison, suffix, and nominal/POS routing

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `يُحَرِّفُونَهُۥ` | verb object suffix and referent review | root/entry prose without `هُ` |
| `ثَقِفْتُمُوهُمْ` | finite subject ending plus `هُمْ` object | dictionary infinitive only |
| `تُخَالِطُوهُمْ` | finite verb + object suffix + context | nominal "partners" leak |
| `كَزَرْعٍ` | comparison/preposition relation + host + attachment | host-only cultivation |
| `فَلْيُؤَدِّ` | fā' + lām function + mood/governor | component host evidence |
| `مَالَ` / `مَالِ` | exact POS/function and sentence role | surface-family propagation |
| `وَفُرُشٍۢ` | wāw function + nominal host; component-only blocker | host candidate as whole token |
| renderer-only noun rows | rich metadata backfill if wording survives review | claiming certification from string presence |

VN-12 keeps live apply closed. A row may enter a repair packet only as a
candidate; it still needs exact address, public-safe authored wording,
compatible sarf/nahw reasons, and two-vote or MCP/source evidence when the
grammar is sensitive.

## 4o. VN-13 conjunction, suffix, and POS-routing controls

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `وَٱلشَّمْسُ` / `وَٱلْقَمَرُ` | wāw function + article + nominal host + case/state | host candidate or visible text alone |
| `سُهُولِهَا` / `نُورَهُۥ` | noun host plus suffix/referent review | host-only "plains" or "light" |
| `لَأَعْنَتَكُمْ` | lām/function + finite host + `كُمْ` object | hardship-family infinitive |
| `ٱقْتَرَفْتُمُوهَا` | finite subject ending plus `هَا` object | dictionary infinitive only |
| `بِمُصْرِخِكُمْ` | bā' + host + suffix and attachment | root-family "cry for help" |
| `مَطَرَ` / `طَٰٓئِرٍۢ` | exact POS/context and possible token-only repair | noun entry getting verb infinitive wording |
| `وَخَابَ` / `فَصَبَّ` | component-only blocker until prefixed function and host agree | component host proof as whole-token proof |
| renderer-only rows | rich metadata backfill if no grammar defect exists | claiming rich certification from hover presence |

VN-13 adds no live-apply exception. A candidate must still pass exact address,
public-safe authored text, compatible sarf/nahw reasons, source/MCP evidence
where needed, and two-vote review for grammar-sensitive rows.

## 4p. VN-14 suffix, relation, and detector-boundary controls

| token | route before hover trust | unsafe shortcut |
|---|---|---|
| `أَصْوَافِهَا` | noun host plus `هَا` possessor/referent | host-only `wool` |
| `يَلْمِزُكَ` / `وَدَّعَكَ` | finite host plus `كَ` object/addressee | dictionary infinitive only |
| `بِجَهَازِهِمْ` | bā' + host + `هِمْ` and PP attachment | supply/provide host prose |
| `لِيُدْحِضُوا۟` / `لِيَمِيزَ` | lām function + mood/governor + clause relation | component host evidence |
| `بِدْعًا` / `كَهَيْـَٔةِ` | relation/comparison or attachment review | root-family invention/shape prose |
| `وَٱلشَّجَرُ` | component-only blocker until wāw/article/host function agree | host candidate as whole token |
| `ثَمَرِهِۦ` | noun host + suffix/referent; possible POS repair | verb infinitive "to fruit" |
| renderer-only rows | rich metadata backfill if no grammar defect exists | claiming rich certification from text presence |

VN-14 keeps the two-vote and MCP/source-evidence gates intact. A candidate can
be useful for review while remaining non-applyable because the suffix, relation,
or POS/function reasoning is not yet certified.
