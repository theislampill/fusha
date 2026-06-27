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
