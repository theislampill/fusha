# curriculum — ʿajamī zero-to-fluency

`curriculum/` is the **learner-facing layer** of Fusha. The rest of the repo is built for an
agent that authors and certifies glosses; this directory turns the *same* assets — the ṣarf
procedures, the nahw decision rules, the Qamus entries, the hover-gloss state, and the
source-address graph — toward a human who wants to read fuṣḥā and, in time, the Qurʾān and
the Sunnah, starting from **zero**.

The learner this is written for is **ʿajamī**: a non-Arab adult who may not yet know the
letters, who has no teacher in the room, and who has been told for years that "real" Arabic
takes a decade. The mission here is the opposite claim, made honestly: a motivated beginner
can climb from *not reading the script* to *reading an āyah with understanding* on a fixed
ladder, where every rung is small, every rung has a checkpoint, and no rung asks the learner
to trust a word that the repo cannot back with an authored Qamus entry.

> This is a study layer, not a fatwā layer. It teaches **language**. Where it touches the
> Qurʾān it touches it as text to be read with care; the learner verifies meaning against
> the muṣḥaf and a qualified teacher. The repo never alters Qurʾān text and never ships a
> gloss it has not authored — see [`../README.md`](../README.md) and
> [`../provenance/source-boundaries.md`](../provenance/source-boundaries.md).

## The mission in one paragraph

Most beginner Arabic courses fail ʿajamī learners in one of two ways: they front-load grammar
tables the learner cannot yet *use*, or they teach "conversational" Arabic that never reaches
the Book. The Fusha ladder refuses both. It is **reading-first and procedure-first**: every
level teaches the smallest piece of ṣarf or nahw that unlocks *more real text*, drills it
against words the learner will actually meet, and proves the gain by having the learner read a
slightly harder passage than the level before. The end state is not "knows the grammar" — it
is **reads fuṣḥā independently, and reaches for the right tool when stuck.**

## The 12-level ladder

The full ladder, with goals, the exact ṣarf/nahw skills each level uses, the Qamus entries it
draws on, its drill, and its checkpoint, is in
[`zero-to-fluency-roadmap.md`](zero-to-fluency-roadmap.md). In brief:

| # | Level | Unlocks |
|---|---|---|
| 1 | Script & sounds | reading + writing the letters, harakāt, sukūn, shadda, tanwīn |
| 2 | Core particles | the high-frequency ḥurūf: `فِي`, `مِنْ`, `إِلَىٰ`, `عَلَىٰ`, `وَ`, `لَا` |
| 3 | Nouns: gender, number, definiteness | `الْ`, masc./fem., the sound + broken plural |
| 4 | Verbs & roots | the three-radical root, past/present, the idea of a wazn |
| 5 | Iḍāfa & jār-majrūr | the genitive construct and preposition + noun/pronoun |
| 6 | Nominal & verbal sentences | the two sentence types; subject/predicate; verb-first order |
| 7 | Qurʾānic function words | `مَنْ`/`مِنْ`, `مَا`, `إِنَّ`/`أَنَّ`, `الَّذِي`, conditionals |
| 8 | Reading a short āyah | a full short āyah, word by word, with the hover layer |
| 9 | Qamus root study | study a root as a *family*; senses, forms, usage |
| 10 | Reading al-Nawawī's Forty | classical prose hadith matn, with candidate vocab |
| 11 | Ṣaḥīḥayn preparation | the hadith-technical register; isnād vocabulary |
| 12 | Independent fuṣḥā reading | read unseen text; diagnose your own PENDING |

The first eight rungs build the machinery to read one āyah. Rungs 9–12 widen the reading from
a single āyah to a root family, then to classical prose, and finally to the open corpus.

## How the ladder links the rest of the repo

The curriculum does **not** restate ṣarf or nahw — it *routes* to them. Each level names the
procedures and references it leans on, so a learner (or an agent guiding a learner) always
lands on the same single source of truth the gloss-authoring side uses.

- **Ṣarf procedures** — when a level introduces roots, patterns, plurals, or verb forms it
  points into [`../sarf/`](../sarf/README.md): root extraction
  ([`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md)), verb forms
  ([`../sarf/procedures/verb-form.md`](../sarf/procedures/verb-form.md)), noun
  plural/gender ([`../sarf/procedures/noun-plural-gender.md`](../sarf/procedures/noun-plural-gender.md)),
  and the verb-measures reference
  ([`../sarf/references/verb-measures-table.md`](../sarf/references/verb-measures-table.md)).
- **Nahw procedures** — when a level introduces particles, iḍāfa, sentence type, or context
  it points into [`../nahw/`](../nahw/README.md): the particle decision
  ([`../nahw/procedures/particle-decision.md`](../nahw/procedures/particle-decision.md)),
  iḍāfa + jār-majrūr
  ([`../nahw/procedures/idafa-jar-majrur.md`](../nahw/procedures/idafa-jar-majrur.md)),
  and referent/context
  ([`../nahw/procedures/referent-context.md`](../nahw/procedures/referent-context.md)).
- **Qamus entries** — the words a learner reads are not arbitrary. They are drawn from the
  **2,092** existing entries indexed at
  [`../qamus/indexes/existing_qamus_index.min.json`](../qamus/indexes/existing_qamus_index.min.json),
  ordered by frequency within class, so early levels meet the most common words first. See
  [`qamus-learning-path.md`](qamus-learning-path.md).
- **Hover-gloss state** — from Level 8 on, the learner reads on `qamus.dawah.wiki`, where
  hovering or tapping a Qurʾānic word shows an **authored** English gloss
  (`{src:'qamus', kind:'authored'}`) when the word is covered, and shows **nothing** when it
  is not. A blank hover is a feature: it means "this word has not yet earned a certified
  gloss," and the learner falls back to procedure rather than to a guess. The coverage the
  learner sees is the same scoreboard the authoring side tracks at
  [`../qamus/reports/hover-gloss-terminal-scoreboard.md`](../qamus/reports/hover-gloss-terminal-scoreboard.md).
- **Source-address nodes** — every Qamus entry has a stable address (`qamus:v###` / `n###` /
  `p###`) and every Qurʾān word a position address (`quran:S:A:W`), per
  [`../qamus/reports/source-address-model.md`](../qamus/reports/source-address-model.md). The
  curriculum uses these as *study coordinates*: a root study at Level 9 is "open address
  `qamus:v443`, read every `usage_refs[]` it points at." Addresses give the learner a durable
  way to bookmark, revisit, and cross-link what they have studied.

## Files in this pack

```
curriculum/
  README.md                      ← you are here
  zero-to-fluency-roadmap.md     ← the 12 levels in full: goal · skills · entries · drill · checkpoint
  qamus-learning-path.md         ← how to study with qamus.dawah.wiki + the hover layer
  placement-test.md              ← self-scoring test → your starting level
  mastery-checkpoints.md         ← per-level checkpoints + error → remediation procedure map
```

A learner's path through these files: take [`placement-test.md`](placement-test.md) to find a
starting rung, climb [`zero-to-fluency-roadmap.md`](zero-to-fluency-roadmap.md) one level at a
time, use [`qamus-learning-path.md`](qamus-learning-path.md) for the daily reading habit, and
clear each rung against [`mastery-checkpoints.md`](mastery-checkpoints.md) before moving up.

## Hard rules honored here

- **Qurʾān text is never altered.** It appears as something to read, never edited for a drill.
- **The learner only ever sees authored content.** Hover glosses are `{src:'qamus',
  kind:'authored'}`; no external dictionary, textbook, or exam text is reproduced anywhere in
  this curriculum. Every drill item and example is original.
- **A blank beats a wrong answer.** The curriculum teaches the same discipline the gloss
  pipeline enforces: when root, pattern, or sense is uncertain, the honest move is PENDING —
  name the doubt and route to the right procedure — not a confident guess.
- **No private detail.** No server paths, secrets, IPs, or external source names as public
  authority. The learner studies on the public app only.
