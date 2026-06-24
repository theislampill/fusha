# Zero → fluency — a naḥw learning path for ʿajamī learners

**Ṣarf tells you what a word *could* be; naḥw tells you what it *is here*.** This path teaches
the *here* — syntax — for a learner who comes to Arabic from outside it (no childhood ear for
case endings, no intuition for which word governs which). It is not a textbook; it is a
**procedure-first** ladder where every stage names: the *skill*, the *procedure* that performs
it, the *drill* that trains it, the *Qamus examples* that ground it in real āyāt, and a
**mastery checkpoint** you must clear before climbing.

> All content here is original authored teaching. Qurʾān words appear only as evidence, by
> address (`quran:S:A:W`, e.g. `quran:112:3:2`), never altered. External corpora are internal
> evidence only; the public render carries `{src:'qamus', kind:'authored'}`. See
> [`../README.md`](../README.md) for the layer and [`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md)
> for how a citation points back without copying.

## How to use this ladder

Each stage is **read the procedure → do the drill → check yourself against the Qamus examples →
clear the checkpoint.** Do not skip a checkpoint because a stage "looks easy" — the failure
modes compound. A learner who guesses case endings at Stage 6 was already guessing governors at
Stage 5. The whole point of naḥw is to **stop guessing**: when the evidence does not decide,
the disciplined answer is **pending**, never a confident wrong reading.

Drill files: [`drills-beginner.md`](drills-beginner.md) · [`drills-intermediate.md`](drills-intermediate.md) ·
[`drills-advanced.md`](drills-advanced.md).

---

## Stage 1 — Particles (الْحُرُوف): the closed set you must read exactly

**Skill.** Recognize the high-frequency function words and read the **content letter's harakah**
(after any `و`/`ف` proclitic), not the first letter. `مَنْ` ('who') vs `مِنْ` ('from') vs `مَنَّ`
(verb) all collapse under `norm()` — the harakah on the **م** and the shadda on the **ن**
separate them.

- **Procedure:** [`../procedures/particle-decision.md`](../procedures/particle-decision.md)
- **Reference:** [`../drills/particles.md`](../drills/particles.md), [`../references/particles.md`](../references/particles.md)
- **Drill:** [`drills-beginner.md`](drills-beginner.md) §1 (identify the particle)
- **Qamus examples:** `وَالْعَصْرِ` `quran:103:1:1` (`وَ` = oath 'by', not 'and'); `لَمْ يَلِدْ`
  `quran:112:3:1` (`لَمْ` = 'did not', forces the next verb to past).

**Checkpoint 1.** Given ten diacritized function words from real āyāt, name each one's function
and gloss, **and** for any word stripped of diacritics say `pending: homograph_haraka` rather
than guess. A wrong particle gloss poisons the whole āyah's parse.

---

## Stage 2 — Prepositions & pronouns: the jār-majrūr and the attached pronoun

**Skill.** A preposition always puts its object in the **genitive (jarr)**, so a *verb* gloss
after a preposition is impossible. Attached pronouns (`ـه/ـها/ـهم/ـكم/ـنا`) change the *wording*
of the phrase, not the head's sense: `بِهِ` 'with it / in it', `لَهُ` 'for him', `إِلَيْنَا`
'to us'. **Guard:** `إِلَيْنَا` is `إِلَى` + `نا` (root أ-ل-ي), **not** root ل-ي-ن ('soft') — the
hamza seat `norm()` drops is load-bearing.

- **Procedure:** [`../procedures/preposition-pronoun.md`](../procedures/preposition-pronoun.md)
- **Reference:** [`../references/jar-majrur.md`](../references/jar-majrur.md)
- **Drill:** [`drills-beginner.md`](drills-beginner.md) §2 (preposition + its object)
- **Qamus examples:** `فِي الْأَرْضِ` `quran:2:30:9` (object jarr, a noun); `عَلَيْهِمْ`
  `quran:1:7:2` ('upon them / against them'); `إِلَيْنَا` `quran:2:136:13` ('to us', not ل-ي-ن).

**Checkpoint 2.** For each of `بِهِ`, `لَهُ`, `فِيهِ`, `عَلَيْهِمْ`, `إِلَيْنَا` give the
referent-correct gloss, and state why no `إِلَى…` form is ever glossed from root ل-ي-ن.

---

## Stage 3 — Negation (النفي): the particle sets the tense, not the surface form

**Skill.** The **governing negative**, not the verb's surface tense, decides the English.
`لَمْ` + jussive negates the **past** ('did not'), even though the verb is present-form; `لَنْ` +
subjunctive is categorical **future** negation ('will never'); `لَا` is multi-function (simple
negation / prohibition + jussive / *lā al-nāfiyah lil-jins* 'there is no'); `لَيْسَ` negates a
nominal sentence ('is not'); `مَا` negation is **only one** of its readings.

- **Procedure:** [`../procedures/negation.md`](../procedures/negation.md)
- **Reference:** [`../references/irab-case-mood.md`](../references/irab-case-mood.md) (verb-mood section)
- **Drill:** [`drills-intermediate.md`](drills-intermediate.md) §3 (negation type)
- **Qamus examples:** `لَمْ يَلِدْ وَلَمْ يُولَدْ` `quran:112:3:1` (past negation, jussive); `لَا
  تَحْزَنْ` `quran:9:40:11` (prohibition, jussive); `لَا إِلَٰهَ إِلَّا اللَّهُ` (`لَا` of genus,
  'there is no').

**Checkpoint 3.** For a verb under each of `لَمْ` / `لَنْ` / `لَا` / `مَا`, state the resulting
tense/polarity **and** the mood it forces; default `مَا` to nothing — emit `pending: multi_sense`
when the frame is unclear.

---

## Stage 4 — Iḍāfa & jār-majrūr as constructs: gloss the *relationship*

**Skill.** In an **iḍāfa** (genitive construct) the head loses tanwīn and `ال`; its
**definiteness and the relationship** come from the second term: `عِنْدَ ٱللَّهِ` = 'in the sight
of Allah' (not bare 'near'), `بَيْتُ ٱللَّهِ` = 'the House of Allah' (definite). A ẓarf
(`عِنْدَ/بَيْنَ/فَوْقَ/تَحْتَ`) heads an iḍāfa of place/time — gloss the relation, not the adverb
alone. In a **jār-majrūr** the genitive noun is 'of …', governed by the preposition.

- **Procedure:** [`../procedures/idafa-jar-majrur.md`](../procedures/idafa-jar-majrur.md)
- **Reference:** [`../references/idafa.md`](../references/idafa.md), [`../drills/idafa-and-jar-majrur.md`](../drills/idafa-and-jar-majrur.md)
- **Drill:** [`drills-intermediate.md`](drills-intermediate.md) §1 (iḍāfa) and §2 (jar-majrūr)
- **Qamus examples:** `رَبِّ الْعَالَمِينَ` `quran:1:2:2` ('Lord of the worlds', definite by the
  second term); `عِنْدَ رَبِّهِمْ` `quran:3:169:5` ('with their Lord').

**Checkpoint 4.** Given a two-term construct, say which term carries definiteness, render the
relationship, and **never** gloss the head as indefinite when the construct is definite.

---

## Stage 5 — Nominal vs. verbal sentences: find the first governor

**Skill.** A **nominal** sentence opens with a noun/pronoun (mubtadaʾ + khabar, both rafʿ); a
**verbal** sentence opens with a verb (fiʿl + fāʿil, the doer, then a mafʿūl in naṣb). The same
surface noun glosses with a different **role** by sentence type, and a verb-vs-noun homograph is
settled by **position**. If a clause opens with `إِنَّ`/`أَنَّ`, the next noun is its *subject* in
naṣb — not a verb's object.

- **Reference / drill:** [`../drills/sentence-context.md`](../drills/sentence-context.md) §1–§2
- **Drill:** [`drills-beginner.md`](drills-beginner.md) §3 (subject/predicate);
  [`drills-intermediate.md`](drills-intermediate.md) §4 (relative vs interrogative)
- **Qamus examples:** `إِنَّ اللَّهَ` `quran:2:20:18` ('indeed Allah' — subject in naṣb, nominal);
  `قَالَ رَبِّ` `quran:19:4:1` (verbal: fiʿl then the doer).

**Checkpoint 5.** For five āyāt openings, name the sentence type, identify the **first governing
element** (verb / `إِنَّ`-family / preposition / conditional), and assign roles **before** glossing
any noun. Reject any candidate gloss whose POS contradicts the governor (`pending: pos_mismatch`).

---

## Stage 6 — Case & mood (الإعراب): the ending fixes the role and can flip the tense

**Skill.** Read the ending: **rafʿ** (ضمة) = subject/predicate, **naṣb** (فتحة) = object/ḥāl/
tamyīz, **jarr** (كسرة) = after a preposition or as muḍāf ilayhi. The case ending does **not**
change the lexeme's gloss but it fixes the role — and **mood flips tense**: `لَمْ` + jussive →
past ('did not beget'), `أَنْ`/`لَنْ` + subjunctive. Indeclinables (particles, pronouns,
demonstratives) are **mabnī** — their fixed final vowel is not a case marker.

- **Reference:** [`../references/irab-case-mood.md`](../references/irab-case-mood.md)
- **Drill:** [`drills-advanced.md`](drills-advanced.md) §1 (iʿrāb case/mood)
- **Qamus examples:** `لَمْ يَلِدْ` `quran:112:3:1` (present-form, jussive, **past** meaning);
  `عَلِيمٌ` vs `عَلِيمًا` (same lexeme, rafʿ predicate vs naṣb object — quarantine the whole
  inflection family together).

**Checkpoint 6.** Given an ending, state the case/mood, the role it assigns, and the tense
effect; if the decisive vowel is absent and the role/tense matters → **pending**, never the
commoner reading.

---

## Stage 7 — Qurʾanic function words in context: governors, conditionals, referents

**Skill.** The highest tier ties it all together: a **governing particle** pins the POS and mood
of its complement; **conditionals** (`إِنْ`, `مَنْ`, `مَا` + jazm) take a sharṭ and a jawāb (often
headed by apodosis `فَـ`); **contronyms** flip by context (`يَقْدِرُ` paired with `يَبْسُط` =
'restricts', not 'is able'); and the **referent guard** keeps a human's `حَلِيمٌ` ('forbearing')
from being typeset as a Divine Name. This is exactly where a general LLM collapses, so the
discipline is: answer **and** reasoning must both be right, or emit a precise `pending:`.

- **Reference:** [`../references/quranic-nahw-notes.md`](../references/quranic-nahw-notes.md),
  [`../drills/sentence-context.md`](../drills/sentence-context.md) §3–§7
- **Procedure / gate:** [`../procedures/grammar-risk-gate.md`](../procedures/grammar-risk-gate.md)
- **Drill:** [`drills-advanced.md`](drills-advanced.md) §2–§4 (conditional vs emphatic; the
  GrammarProblems failure classes)
- **Qamus examples:** `يَبْسُطُ ٱلرِّزْقَ … وَيَقْدِرُ` `quran:13:26:4` (contrast frame →
  'restricts'); `إِنَّهُ كَانَ حَلِيمًا` of Ibrāhīm `quran:11:75:4` ('forbearing', human virtue).

**Checkpoint 7 (fluency gate).** Take an unseen āyah and produce, for each token: root/POS,
case/mood, role assigned by its governor, and a cited gloss — **or** the most specific
`pending:` reason. Pass only when no token carries a confident wrong reading. This is the bar
the [GrammarProblems gate](../evals/grammar-problems-matrix.md) enforces in the pipeline.

---

## The through-line

| stage | adds | the question it answers |
|---|---|---|
| 1 particles | the closed set + harakah reading | "which function word is this?" |
| 2 prep + pronoun | jarr governance, clitic wording | "what does the preposition do to its object?" |
| 3 negation | particle-set tense/polarity | "what is actually being negated, and when?" |
| 4 iḍāfa / jar-majrūr | construct definiteness + relationship | "whose? of what? definite or not?" |
| 5 sentence type | the first governor → roles | "is the first noun a topic or a doer?" |
| 6 case / mood | the ending → role, the tense flip | "what role does the ending mark? did the mood move the tense?" |
| 7 Qurʾanic function | conditionals, contronyms, referents, the gate | "which of the candidate readings holds *in this āyah*?" |

**Ṣarf narrows; naḥw decides.** When naḥw cannot decide, the answer is **pending** — and a
precise pending is mastery, not failure.
