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
