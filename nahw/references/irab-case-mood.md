# Iʿrāb — case & mood, and what they tell the gloss

Iʿrāb is the system of case (on nouns) and mood (on present‑tense verbs) marked by the word's ending. For
qamus‑highlight the point is narrow: **the ending signals the syntactic role, and the role can change the English
wording or flip a tense** — but the ending is also a frequent source of false homographs, so read it, don't guess.

## Noun case (الإعراب الاسمي)

| case | Arabic | typical ending | role | gloss effect |
|---|---|---|---|---|
| nominative | الرفع | ‑ُ / ‑ٌ (ضمة) | subject (fāʿil), mubtadaʾ, khabar | the doer / the topic |
| accusative | النصب | ‑َ / ‑ً (فتحة) | object (mafʿūl), ḥāl, tamyīz | the done‑to / "as a …" |
| genitive | الجر | ‑ِ / ‑ٍ (كسرة) | after a preposition or as مضاف إليه | "of …", governed by the preposition |

The case ending does **not** change the lexeme's gloss, but it fixes the role: a nominative عَلِيمٌ is a predicate
("All‑Knowing"), an accusative عَلِيمًا is the same word in object/ḥāl position — **quarantine the whole
inflection family together** (the P5 lesson: a fix on عَلِيمًا must also cover عَلِيمٌ).

## Verb mood (الإعراب الفعلي) — the tense‑flipping cases

| mood | Arabic | trigger | gloss effect |
|---|---|---|---|
| indicative | الرفع | default present | "he does / is doing" |
| subjunctive | النصب | أَنْ, لَنْ, كَيْ, حَتَّى | "(that) he do / will never do" |
| jussive | الجزم | لَمْ, لَا الناهية, conditional | **لَمْ + jussive → PAST meaning** "did not"; "do not!" |

This is the operational payoff: **لَمْ يَلِدْ** is a present‑form verb in the jussive that means "He did **not**
beget" (past). The mood, set by the governing particle, overrides the surface tense. See
[`rules/negation-rules.json`](../rules/negation-rules.json).

## Indeclinables (المبني)

Particles, most pronouns, demonstratives, and relatives are **mabnī** (fixed ending) — they don't take iʿrāb.
Don't read a fixed final vowel on a pronoun/particle as a case marker or a root letter (e.g. the ـنا of إِلَيْنَا
is a fixed pronoun, not a declensional ending).

## Hand‑off

Use the ending to confirm the role and to respect mood‑driven tense; never let an ambiguous ending pick the
commoner reading. If the decisive vowel is absent and the role/tense matters → pending.
