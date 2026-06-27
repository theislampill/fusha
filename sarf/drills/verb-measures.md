# Drill — read the verb measure before you gloss

Each drill is a surface → the decision the sarf skill must make. Cover the answer; decide form, voice, and
gloss-shape; then check. Source paradigm: [`sarf/rules/verb-measures.json`](../rules/verb-measures.json).

## A. Form I vs derived form (same root, different verb)

| surface | root | answer |
|---|---|---|
| نَزَلَ | ن ز ل | Form I — "descended" (intransitive base) |
| نَزَّلَ | ن ز ل | Form II (shadda) — "sent down gradually" (causative/intensive) |
| أَنزَلَ | ن ز ل | Form IV (hamza) — "sent down" (causative) |
| عَلِمَ | ع ل م | Form I — "knew" |
| عَلَّمَ | ع ل م | Form II — "taught" (causative) |
| اِسْتَعْلَمَ | ع ل م | Form X — "sought to know / enquired" |

**Rule:** never gloss a derived form with the Form I sense. The shadda (II), the hamza (IV), the اِسْتَ‑ (X) each
change the verb. → `root-pattern-risk-rules.json#form_ii_vs_form_iv_same_root`.

## B. Active vs passive (the harakāt flip the English)

| surface | answer |
|---|---|
| خَلَقَ | active — "created" |
| خُلِقَ | passive (ḍamma–kasra) — "was created" |
| يَعْلَمُ | active — "he knows" |
| يُعْلَمُ | passive — "it is known" |

**Rule:** read the ḍamma–kasra signature of the passive before choosing wording. Passive ≠ active.

## C. Maṣdar / participle → nominal gloss (never a finite verb)

| surface | shape | gloss |
|---|---|---|
| ذِكْر | maṣdar | "remembrance" (NOT "he remembered") |
| اِسْتِغْفَار | maṣdar (X) | "seeking forgiveness" |
| كَاتِب | ism fāʿil | "writer / one who writes" |
| مُؤْمِنُونَ | ism fāʿil | "believers" (NOT "they believe") |
| مَخْلُوق | ism mafʿūl | "created thing" |
| مُعَلِّم / مُعَلَّم | fāʿil / mafʿūl | "teacher" / "taught one" (penult vowel decides) |

**Rule:** a noun‑pattern derivation takes a noun gloss. A "to …" verb gloss on a participle/maṣdar is the §3
POS‑mismatch defect.

## D. Negation rewrites the tense

| surface | answer |
|---|---|
| لَمْ يَلِدْ | لَمْ + jussive → PAST meaning: "He did not beget" |
| لَنْ يَفْعَلُوا | لَنْ + subjunctive → future: "they will never do" |

**Rule:** the governing negative, not the surface tense, sets the English. → `nahw/rules/negation-rules.json`.

## E. Irregular‑root recovery (weak / doubled / quadriliteral)

| surface | answer |
|---|---|
| قَالَ | hollow ق‑و‑ل; medial و → ā. "said" |
| أَقَامَ | Form IV of hollow ق‑و‑م; medial dropped. "established" |
| يَجِدُ | assimilated و‑ج‑د; C1 و drops in the present. "finds" |
| دَعَا | defective د‑ع‑و; C3 surfaces as ā. "called" |
| رَدَّ | geminate ر‑د‑د; shadda hides C3. "returned / repelled" |
| زَلْزَلَ | quadriliteral ز‑ل‑ز‑ل. "quaked" |

**Rule:** recover the hidden radical from the family (muḍāriʿ / QAC) before matching; never let `norm()` decide a
weak root. → [`weak-verbs.md`](../references/weak-verbs.md).

## F. VN-01 dogfood: finite token, not entry infinitive

| surface | reject | require before hover trust |
|---|---|---|
| `تَجِدُوهُ` | bare `to find` | imperfect verb + `هُ` object contribution |
| `تُبَٰشِرُوهُنَّ` | phrase/action gloss with no object suffix proof | verb host + feminine plural object `هُنَّ` |
| `عَادَيْتُم` | root family "enemy" prose only | finite person/number and form review |
| `يَعِدُ` | collapsed weak-root family routing | weak-root/source-address check before candidate entry |

Rule: if the token is finite, the hover is not certified until aspect, voice,
person/number/gender, form, and any suffix pronoun are available to the learner.
An English string may be plausible and still remain `populated_uncertified`.

## G. VN-02 dogfood: voice, derived form, and suffixes block lemma prose

| surface | reject | require before hover trust |
|---|---|---|
| `وَفَضَّلْنَٰهُمْ` | favor/bounty entry paragraph | `وَ` + Form II perfect 1cp + `هُمْ` object |
| `فُضِّلُوا۟` | active "to favor" wording | passive Form II perfect 3mp |
| `يُولَدْ` | active "to have children / beget" family | passive/jussive weak verb under negation |
| `فَشُدُّوا۟` | "to be strong" family | doubled-root imperative 2mp plus `فَ` |
| `ٱسْتَـْٔذَنَكَ` | bare "to seek permission" | hamzated Form X perfect plus `كَ` object |
| `وَٱصْطَبِرْ` | Form I patience infinitive | Form VIII imperative plus `وَ` |

Rule: a finite or imperative verb is not certified by its root-family prose.
The parse must show form, voice, aspect/mood, person/number, proclitics, and
visible suffixes.

## H. VN-03 dogfood: finite verbs and component-only rows

| surface | reject | require before hover trust |
|---|---|---|
| `عَقَلُوهُ` | `to reason; understand` | perfect plural verb + `هُ` object contribution |
| `أَعْجَلَكَ` | bare `to hasten` | finite/derived form plus `كَ` object |
| `وَيَسْتَعْجِلُونَكَ` | component-only "to hasten" family | `وَ` + finite verb + `كَ` object, with whole-token evidence |
| `فَأَهْلَكْنَاهُمْ` | readable phrase treated as complete proof | `فَ` + Form IV perfect 1cp + `هُمْ`, two-vote whole-token gate |
| `وَقُضِىَ` | active "to decree/judge" prose | passive voice and `وَ` function |
| `تَمَسُّوهُنَّ` | "touch" without object | doubled root + feminine-plural object `هُنَّ` |

Rule: component evidence can explain pieces, but it cannot certify the written
token. Finite wording, passive voice, weak/doubled roots, and object suffixes
stay gated until the exact token is parse-key ready.

## I. VN-04 dogfood: weak, hamzated, and shadda-bearing finite verbs

| surface | reject | require before hover trust |
|---|---|---|
| `فَأَنسَىٰهُ` | `to forget; neglect` | `فَ` + finite causative/weak-root host + `هُ` object |
| `ذَرْهُمْ` | `to leave someone or something` | imperative weak-root host + `هُمْ` object |
| `وَيَذَرَكَ` | bare leave-family prose | `وَ` function + imperfect/subjunctive-looking verb + `كَ` object |
| `بَدِّلْهُ` | `to change or replace` | imperative/Form II host + `هُ` object |
| `وَلَيُبَدِّلَنَّهُم` | broad replace-family prose | `وَ` + lām/emphasis + finite Form II/IV review + `هُم` object |
| `تُبَدَّلُ` | active replace infinitive | passive finite verb |
| `يَصُدُّونَ` / `يَصِدُّونَ` | one stripped-root hover | shadda + vowel/POS/context review |

Rule: weak radicals, passive signatures, emphatic nūn, and shadda are not
typography. They are the reason the token cannot be certified from an entry
infinitive or component-only root match.

## J. VN-05 dogfood: finite verbs, passive voice, and entry-class traps

| surface | reject | require before hover trust |
|---|---|---|
| `لِيَسْتَخْفُوا۟` | broad `to hide` family | lām/governor review + derived finite verb form/person/number |
| `تُخْفُوهُ` | `to hide` with no object | finite verb host + `هُ` object suffix |
| `فَسَيَكْفِيكَهُمُ` | bare `to be sufficient` | `فَ`/future stack + finite verb + `كَ`/`هُمُ` object structure |
| `تَبَرُّوهُمْ` | root-family kindness prose | finite verb + `هُمْ` object |
| `ٱسْتُهْزِئَ` / `وَيُسْتَهْزَأُ` | active `to mock` | passive voice and clause role |
| `غَالِبٌ` | `to overcome, defeat` | nominal/active-participle role before wording |
| `ٱلْقَصَصِ` | `to relate a story` | definite noun/story role and case/context |

Rule: entry class and root family are routing hints, not token identity. A verb
entry can contain nominal derivatives, and a finite verb can contain suffixes
and passive voice that the entry infinitive does not teach.

## K. VN-06 dogfood: verb entries can contain non-verbs

| surface | reject | require before hover trust |
|---|---|---|
| `مِن` / `مِّنَ` | treating `from` rows as `مَنَّ` verb-family evidence | strict particle surface + nahw preposition review |
| `مَنْ` | one shared lane with `مِن` or `مَنَّ` | relative/interrogative/conditional context |
| `ٱلْمَنَّ` | verb-entry proof from `مَنَّ` | article + lexical noun host review |
| `ثَمَرَةٍ` | `to bear fruit` verb hover | noun/case/state review |
| `مَرَضٌ` | finite `to be sick` wording | sickness/state noun review |
| `ٱشْتَرَوُا` | `to sell, buy, or trade depending on form` | exact form/sense/transitivity review |
| `تَلْبِسُوا` | broad dress/confuse family prose | finite verb form, mood, and object/context review |

Rule: a rich component or source-key candidate can improve review routing, but
it cannot certify the written token. If the row is a particle, lexical noun, or
nominal derivative inside a verb-entry family, route by the token's POS and
nahw context before any hover trust.

## L. VN-07 dogfood: strict surface before familiar verb roots

| surface | reject | require before hover trust |
|---|---|---|
| `مِنِّى` / `مِّنِّى` | `تَمَنَّى` wish-verb evidence | preposition `مِن` + first-person suffix and attachment context |
| `يَتَمَنَّوْهُ` | bare `to desire or wish` | Form V imperfect plural host + `هُ` object |
| `مَوَازِينُهُۥ` | `to weigh` | plural scales noun + `هُ` suffix |
| `ٱلْمِيزَان` / `وَزْنًا` | finite weighing verb | balance/weight noun or masdar role |
| `فَرِيضَةً` / `مَّفْرُوضًا` | `to ordain` | nominal derivative/ordained portion role |

Rule: strict surface, POS, suffixes, and derivative shape come before root
family reuse. The learner should see why the token contributes "from me",
"they wish for it", or "his scales", not only the dictionary family.

## M. VN-08 dogfood: passive verbs, exact nouns, and component-only evidence

| surface | reject | require before hover trust |
|---|---|---|
| `يُخَفَّفُ` | broad `to be light or make easy` prose | passive/imperfect finite analysis and context |
| `تَرَبُّصُ` | finite `to wait` hover | masdar/nominal POS and role |
| `فَتَرَبَّصُوا۟` | component-only host evidence becoming whole-token proof | fā' function + finite plural verb analysis |
| `يُبَايِعُونَكَ` | pledge-family infinitive with no object | finite verb + `كَ` object |
| `كَالُوهُمْ` | `to weigh or measure` with no object/surface form | finite verb + `هُمْ` object and exact context |
| `رَكَّبَكَ` | build/stack prose with no object | finite host + `كَ` object |
| `إِلًّۭا` | exception-particle route | lexical noun/POS review |

Rule: component-level candidates may make review faster, but they are not
learner-ready morphology. Whole-token certification needs the visible prefix,
host, suffix, POS, and function pieces, plus the exact address.

## N. VN-09 dogfood: finite verbs, suffixes, and lām-on-verb rows

| surface | reject | require before hover trust |
|---|---|---|
| `يَشْتَهُونَ` | `to desire` | imperfect plural finite contribution by exact context |
| `يَعْصِمُكَ` | `to protect against harm` | finite verb host + `كَ` object |
| `يَجْتَبِيكَ` | long entry-family explanation | finite verb host + `كَ` object |
| `وَفَدَيْنَٰهُ` | bare ransom-family infinitive | wāw + finite/perfect host + `هُ` object |
| `لِتُضَيِّقُوا۟` | component-only ضيق evidence | lām function/mood + finite plural host |
| `لِّيَطْمَئِنَّ` | bare tranquility infinitive | lām/governor plus form/mood review |
| `أَقْوَٰتَهَا` | host-only sustenance | nominal host + `هَا` suffix |
| `تَفَثَهُمْ` | host-only grooming | nominal host + `هُمْ` suffix |

Rule: VN-09 rows may be string-populated and still not teach the learner.
Certification needs finite form, suffixes, lām/function pieces, and
component-vs-whole-token proof.

## O. VN-10 dogfood: finite prose, suffixes, and nominal rows

| surface | reject | require before hover trust |
|---|---|---|
| `طَبَعَ` | `to seal one's heart` | perfect finite verb contribution by exact context |
| `ٱسْتَعِينُوا۟` | bare `to assist` | imperative/derived form, plural subject, and context |
| `تَعَاوَنُوا۟` | entry-family "to assist" | Form VI/plural finite contribution |
| `فَدَمَّرْنَٰهُمْ` | component destroy evidence | fā' + finite host + `هُمْ` object, whole-token proof |
| `وَارِدَهُمْ` | entry prose with hidden suffix | host/POS plus `هُمْ` suffix relation |
| `وَقُودُهَا` | fuel host with no suffix | nominal host + `هَا` suffix |
| `ٱلْمُسْتَعَانُ` | `to assist` | nominal/passive-participle-like POS review |
| `ٱلْمُوقَدَةُ` | active kindling verb family | definite passive-participle/adjectival role |

Rule: VN-10 rows separate three outcomes. Finite verbs require form/person
review, suffix-bearing hosts require visible pronoun accounting, and
nominal-looking rows in verb families require derivative/POS review. Rows whose
only defect is missing rich display metadata go to renderer backfill, not live
apply.

## P. VN-11 dogfood: pronoun collisions and component-only known defects

| surface | reject | require before hover trust |
|---|---|---|
| `غَنِمْتُم` / `غَنِمْتُمْ` | `to take war gains` | finite perfect plural contribution by exact context |
| `تَسْتَغِيثُونَ` / `يَسْتَغِيثُوا۟` | bare `to cry for aid` | finite form, subject, and context |
| `ٱقْذِفِيهِ` / `قَبَضْنَٰهُ` | verb-family prose with hidden suffix | verb host + attached suffix/object relation |
| `فَأَهْلَكْنَاهُمْ` | component-only destroy/ruin evidence | fā' + finite host + `هُمْ`, whole-token proof |
| `هُمْ` / `هُمُ` | verb-entry family propagation | standalone pronoun/function-token review |
| `مَغَانِمُ` / `غَنَمُ` | finite war-gains verb | plural nominal/livestock POS review |
| `لِفُرُوجِهِمْ` | component host evidence | lām + host + suffix + attachment review |

Rule: VN-11 adds a negative control. A Qamus candidate may be attached to a
standalone pronoun or component row, but that does not make the row a verb,
does not make it propagation-safe, and does not authorize live apply.

## Q. VN-12 dogfood: finite rows, suffixes, and nominal leakage

| surface | reject | require before hover trust |
|---|---|---|
| `يُحَرِّفُونَهُۥ` | `to twist/deviate from meaning` | finite Form II host + subject/agreement + `هُ` object |
| `ثَقِفْتُمُوهُمْ` | `to find/come upon in battle` | finite perfect `2mp` host + `هُمْ` object |
| `تُخَالِطُوهُمْ` | `partners` | finite verb host + object suffix; reject nominal leak |
| `ٱلصَّيْدِ` / `صَيْدُ` | `to hunt` | nominal/game or masdar role by exact context |
| `مَالَ` / `مَالِ` | raw surface-family propagation | exact POS/function context before reuse |
| `كَزَرْعٍ` | host-only cultivation | kāf relation + governed host + attachment |
| `فَرَشْنَٰهَا` | bare `to spread out` | fā' + finite host + `هَا` object |
| `وَفُرُشٍۢ` | host candidate as whole-token proof | wāw function + nominal host; component-only blocker |

Rule: VN-12 rows force the same question every time: "What is the written
token made of?" If any visible prefix, suffix, finite-form field, POS shift, or
component-only boundary is missing, the row is not a learner-ready hover.

## R. VN-13 dogfood: finite hosts, suffixes, and renderer-only rows

| surface | reject | require before hover trust |
|---|---|---|
| `أَحْرَصَ` / `حَرَصْتَ` | bare `to be keen` | finite form/person/context review |
| `يُخَٰدِعُونَ` / `يَخْدَعُونَ` | bare `to deceive` | form/voice/aspect and exact subject/context |
| `لَأَعْنَتَكُمْ` | infinitive hardship prose | lām/function plus finite host + `كُمْ` object |
| `ٱقْتَرَفْتُمُوهَا` | `to commit or earn` | finite perfect `2mp` host + `هَا` object |
| `سُهُولِهَا` / `نُورَهُۥ` | host-only noun | noun host + suffix/referent |
| `مَطَرَ` / `طَٰٓئِرٍۢ` | verb-infinitive wording on noun/context rows | exact POS and context before repair |
| `وَٱلشَّمْسُ` / `وَٱلْقَمَرُ` | component host evidence as whole-token proof | wāw + article + nominal host and function review |
| renderer-only rows | hover presence as certification | parse key, display segments, and learner breakdown |

Rule: VN-13 confirms the dogfood target is not "string exists". A row can
be populated, linked, or component-enriched and still need sarf/nahw review
before any candidate wording becomes applyable.

## S. VN-14 dogfood: finite rows must be separated from nominal/POS rows

| surface | reject | require before hover trust |
|---|---|---|
| `تُوَسْوِسُ` | bare `to whisper` | finite imperfect form, subject/agreement, and context |
| `يَطْلُبُهُۥ` | `to request, demand` | finite host plus `هُ` object/referent |
| `يَلْمِزُكَ` | `to defame, speak ill of` | finite host plus `كَ` addressee object |
| `وَدَّعَكَ` | farewell entry prose without addressee | finite host plus `كَ` object/context |
| `وَسَطًا` / `أَوْسَطِ` | treating all `و س ط` rows as finite verbs | nominal/elative POS, case/state, and context |
| `ٱلْوَسْوَاسِ` | finite whisper verb | definite lexical/nominal POS review |
| `بِجَهَازِهِمْ` | host family or supply verb alone | bā' + host + suffix and PP attachment |
| renderer-only rows | rich certification from hover presence | route to renderer metadata backfill unless grammar is implicated |

VN-14 adds an Andon lesson: do not let a detector named "verb tranche" classify
all rows as finite verbs. Exact surface/POS comes first, then form, suffix,
function, and learner breakdown.

## T. VN-15 dogfood: entry prose is not a finite verb hover

| surface | reject | require before hover trust |
|---|---|---|
| `يُوَفِّقِ` | `to reconcile` as bare entry prose | finite imperfect/form review and exact context |
| `يَأْلُونَكُمْ` | `to vow` without the addressee suffix | finite host plus `كُمْ` object/addressee accounting |
| `يَخْذُلْكُمْ` | `to abandon` with hidden `كُمْ` | finite host plus visible object suffix |
| `أَطْفَأَهَا` | `to extinguish` without `هَا` | finite/perfect host plus object/referent |
| `يَسْتَفِزَّهُم` | `to incite` without `هُم` | derived finite host plus object suffix |
| `وَقِفُوهُمْ` | component-only detain evidence | wāw + imperative/finite host + `هُمْ`, whole-token proof |
| `فَيُحْفِكُمْ` | host evidence as whole token | fā' function + finite host + `كُمْ` object |
| `لِيُطْفِـُٔوا۟` | host evidence only | lām function/mood + finite plural host |

Rule: rewrite each entry prose line into a token-aware gloss candidate only
after naming the finite form, subject/agreement, object suffix, and any
governing function. If those fields are missing, route the row to exact-address
review or component-only blocker.

## U. VN-16 dogfood: passive finite rows and hidden objects

| surface | reject | require before hover trust |
|---|---|---|
| `كُبِتَ` / `كُبِتُوا۟` | bare `to debase` | passive/voice, finite agreement, and context |
| `كُوِّرَتْ` / `يُكَوِّرُ` | root-family `to wrap around` | form, voice/aspect, subject/agreement |
| `يَكْبِتَهُمْ` | entry prose without `هُمْ` | finite host plus attached object/referent |
| `لِتَلْفِتَنَا` | host-only turning/glance wording | lām function + finite host + `نَا` object |
| `فَهَزَمُوهُم` | `to defeat` alone | fā' function + finite host + `هُم` object |
| `نُنَكِّسْهُ` / `تَؤُزُّهُمْ` | dictionary infinitive only | derived finite host plus suffix/referent |
| component-only finite rows | host candidate as whole-token proof | exact token parse and no live apply |

VN-16 keeps the same hard rule: a finite verb hover is not certified by the
entry's infinitive prose. Passive voice, derived form, subject/agreement, and
attached objects are learner-visible parts of the token.

## V. VN-17 dogfood: passive, weak, and suffix-heavy finite rows

| surface | reject | require before hover trust |
|---|---|---|
| `رُجَّتِ` | bare `to shake violently` | passive/perfect voice, agreement, and context |
| `أَرْكَسَهُم` / `أُرْكِسُوا` | entry prose `to regress` | Form IV/passive-active distinction plus suffix or subject |
| `زُحْزِحَ` | `to be kept away` as entry prose only | passive finite form and exact context |
| `سُعِدُوا` | happiness family gloss | passive/finite form and plural agreement |
| `تَشْخَصُ` / `يَشْوِى` / `صَغَتْ` | root-family infinitive wording | exact finite shape, weak/hamzated/root review, and subject |
| `يَطْمِثْهُنَّ` / `أَظْفَرَكُمْ` | dictionary infinitive without object | finite host plus attached object suffix |
| `لَيُزْلِقُونَكَ` | component host evidence | lām/function + finite host + `كَ` object |

VN-17 keeps finite rows non-applyable. The exercise is to state the verb form,
voice/aspect/mood, person/number/gender, and suffix role before proposing any
English hover.

## W. VN-18 dogfood: finite movement and destruction rows

| surface | reject | require before hover trust |
|---|---|---|
| `نَكَصَ` / `تَنكِصُونَ` | bare `to back away` | finite form and subject/agreement |
| `يُهْرَعُونَ` | entry prose `to hurry` only | imperfect agreement and context |
| `يَهِيجُ` / `يَهِيمُونَ` | root-family wording only | exact finite shape and subject role |
| `يُوبِقْهُنَّ` | `to doom/destroy` without `هُنَّ` | finite host plus object/referent suffix |
| `مَّوْبِقًۭا` | finite verb treatment | nominal/POS review and case/state |
| component rows | host family as whole-token proof | prefix/function/host/suffix parse |

VN-18 keeps these rows non-applyable. The exercise is to name finite form,
agreement, and suffix/object contribution before proposing a hover candidate.

## X. VN-19 dogfood: finite row review before dictionary prose

| surface | reject | require before hover trust |
|---|---|---|
| `تَذْهَلُ` / `تَذُودَانِ` | bare infinitive entry prose | finite imperfect form and subject/agreement |
| `أَذَاعُوا۟` / `رَبِحَت` | dictionary gloss only | perfect form, agreement, and context |
| `يَرْتَعْ` / `رَانَ` | root-family wording only | exact finite shape and clause role |
| `لَنَسْفَعًۢا` | host evidence without lām/function | lām/negation or emphasis function plus finite/mood review |
| `لِيَسْحَتَكُم` | host-only destruction wording | lām function, finite host, and `كُم` object |
| component rows | host family as whole-token proof | prefix/function/host/suffix parse |

VN-19 keeps finite rows non-applyable. The exercise is to name verb form,
voice/aspect/mood where relevant, person/number/gender, and object/function
pieces before proposing any English hover.
