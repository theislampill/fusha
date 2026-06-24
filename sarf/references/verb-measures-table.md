# Verb measures (الأوزان) — triliteral forms I–X

Machine-readable source: [`sarf/rules/verb-measures.json`](../rules/verb-measures.json). Model root **ك‑ت‑ب**
("to write"). This is the operational paradigm the sarf skill uses to decide a form, choose active vs.
passive wording, and gloss maṣdars/participles correctly — **not** a grammar lesson.

## The eight paradigm slots (every chart column)

| slot | Arabic term | English label on the charts | gloss shape |
|---|---|---|---|
| past active | الماضي المعلوم | Past (Known) — "he wrote" | finite past verb |
| past passive | الماضي المجهول | Past (Unknown) — "it was written" | finite past **passive** |
| present active | المضارع المعلوم | Present/Future (Known) — "he is writing" | finite present verb |
| present passive | المضارع المجهول | Present/Future (Unknown) — "it is written" | finite present **passive** |
| imperative | الأمر | Command/Order — "write!" | command |
| maṣdar | المصدر | "verbal idea in the form of a noun" — "writing" | **nominal** ("the act of …") |
| ism fāʿil | اسم الفاعل | "person who does the act" — "writer" | **nominal** ("the one who …") |
| ism mafʿūl | اسم المفعول | "person/thing the act is intended toward" — "written" | **nominal** ("the one/thing …‑ed") |

Two negations the charts add (and the hover gloss must respect):
- **لَنْ + subjunctive** → "he will **not** do" (categorical future negation).
- **لَمْ + jussive** → "he has **not** / did **not** do" — **لَمْ turns a present‑tense *form* into a *past meaning*.**

## Forms I–X

| form | wazn (past) | present | maṣdar | ism fāʿil | ism mafʿūl | sense | Qurʾānic example |
|---|---|---|---|---|---|---|---|
| I | فَعَلَ | يَفْعُلُ/يَفْعِلُ/يَفْعَلُ | *samāʿī* (learned) | فَاعِل | مَفْعُول | base action | خَلَقَ, كَتَبَ |
| II | فَعَّلَ | يُفَعِّلُ | تَفْعِيل | مُفَعِّل | مُفَعَّل | intensive / causative | عَلَّمَ, نَزَّلَ, بَشَّرَ |
| III | فَاعَلَ | يُفَاعِلُ | مُفَاعَلَة/فِعَال | مُفَاعِل | مُفَاعَل | associative / attempting | جَاهَدَ, قَاتَلَ |
| IV | أَفْعَلَ | يُفْعِلُ | إِفْعَال | مُفْعِل | مُفْعَل | causative | أَنزَلَ, أَخْرَجَ, أَقَامَ |
| V | تَفَعَّلَ | يَتَفَعَّلُ | تَفَعُّل | مُتَفَعِّل | مُتَفَعَّل | reflexive of II | تَنَزَّلَ, تَذَكَّرَ |
| VI | تَفَاعَلَ | يَتَفَاعَلُ | تَفَاعُل | مُتَفَاعِل | مُتَفَاعَل | reciprocal / mutual | تَعَاوَنَ, تَسَاءَلَ |
| VII | اِنْفَعَلَ | يَنْفَعِلُ | اِنْفِعَال | مُنْفَعِل | — | mediopassive ("become …") | اِنفَطَرَ, اِنقَلَبَ |
| VIII | اِفْتَعَلَ | يَفْتَعِلُ | اِفْتِعَال | مُفْتَعِل | مُفْتَعَل | reflexive / middle | اِتَّقَى, اِخْتَلَفَ, اِزْدَادَ |
| IX | اِفْعَلَّ | يَفْعَلُّ | اِفْعِلَال | مُفْعَلّ | — | colours / defects | اِسْوَدَّ, اِبْيَضَّ |
| X | اِسْتَفْعَلَ | يَسْتَفْعِلُ | اِسْتِفْعَال | مُسْتَفْعِل | مُسْتَفْعَل | seeking / esteeming | اِسْتَغْفَرَ, اِسْتَكْبَرَ |

Rare **XI–XV** = "specialised, very rare in use" (the charts flag them); **quadriliteral** فَعْلَلَ (model "to roll" =
دَحْرَجَ → زَلْزَلَ, وَسْوَسَ); **geminate** مضاعف (model "to shake" = هَزَّ → مَدَّ, رَدَّ, ضَلَّ). See the JSON.

## Why this matters for Qamus / qamus-highlight (the operational payoff)

1. **Form II vs Form IV are different verbs.** نَزَّلَ (II, "sent down gradually") ≠ أَنزَلَ (IV, "sent down"). Same
   root ن‑ز‑ل; a hover gloss must not collapse them. Likewise عَلَّمَ (II) ≠ Form I عَلِمَ ("knew").
2. **Maṣdar takes a *nominal* gloss, never a finite verb.** ذِكْر = "remembrance" (not "he remembered"); إِنفَاق =
   "spending"; اِسْتِغْفَار = "seeking forgiveness". A maṣdar glossed as a finite verb is a wrong gloss.
3. **Participles are agent/patient nouns.** كَاتِب = "writer / one who writes"; مَكْتُوب = "written / decreed";
   مُؤْمِن = "believer"; مَخْلُوق = "created (thing)". Never put a verb infinitive on a participle.
4. **Passive ≠ active.** خُلِقَ "was created" ≠ خَلَقَ "created"; the unknown‑agent vowelling (ḍamma‑kasra) flips the
   English. Read the harakāt before choosing the wording.
5. **لَمْ over a present form = past meaning.** لَمْ يَلِدْ = "He did not beget" (not "he does not beget").

## Provenance

Structure (slot set, form ladder, English labels, the colours/defects + seeking/esteeming sense notes) was
*observed* in third‑party teaching verb‑charts (catalogued in `corpora/sarfnahw/`, licensing under review) and the
open‑source **qutrub** conjugator roster. **All Arabic above is standard classical morphology authored for this
repo** — the chart Arabic is a non‑Unicode legacy font and was never extracted or copied. None of this ships as
hover text; live hover records stay `{src:"qamus",kind:"authored"}`.
