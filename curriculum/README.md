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

Fluency here is **reading-focused**: Qurʾānic Arabic and classical/register-adjacent fuṣḥā reading,
with sarf + nahw reasoning for unseen texts. The grammar backbone transfers to broader Arabic study,
but this repo is not a complete speaking, listening, dialect, or general MSA news/conversation course.

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

## Current repo state this curriculum teaches from

The current public `main` state audited on 2026-06-25 is recorded in
[`repo-state-and-mission-audit-20260625.md`](repo-state-and-mission-audit-20260625.md). The
short version: Fusha is no longer only a set of root and particle lessons. It now contains
Qamus closure procedures for grammar-resource usage, source-triangulation boundaries,
closure-lane routing, clitic/host morphology, governing-particle mood, `مَا` function
decisions, PP attachment, exception/vocative review, and an internal-only QAC concept-map
adapter.

The learner-facing consequence is simple: hovers are not dictionary substitutions. They are
small contextual claims that survived sarf, nahw, source-boundary, and public-provenance
gates. When a hover is blank, the curriculum teaches the learner to name the blocker:
unknown entry, clitic role, function particle, PP attachment, iʿrāb, proper-name collision, or
source repair. A precise blank is part of the method.

The grammar-checker engine also scaffolds explanation depth by a **CEFR-aligned learner level — but as scaffolding, not
certification.** The morphology candidate lattice, governor dependencies, and abstention gates are unchanged at every level; CEFR
decides only *how much metalanguage* a learner sees (root/pattern at B1+, iʿrāb/governor reasoning at C1+). A1 and C2 see the **same
blank** when a token is uncertified — a blank is a precise blocker, never a level judgement. The engine never assesses or certifies a
learner's CEFR level; the level is supplied by the caller. See [`../tools/fusha_cefr_gate.py`](../tools/fusha_cefr_gate.py) and
[`cefr-fusha-instruction.md`](cefr-fusha-instruction.md).

The next learner-facing layer is a **parse-key and color contract**: every rich hover should be
able to show how the Arabic token is composed and why the best gloss is safe. That contract is
documented in [`qamus-hover-parse-key-and-color.md`](qamus-hover-parse-key-and-color.md) and
drilled in [`drills/parse-key-and-color-layer.md`](drills/parse-key-and-color-layer.md). It
uses scrubbed Qamus role classes such as `qg-verb`, `qg-noun`, `qg-preposition`, and
`qg-pronoun`; it does not expose QAC/Tafsir/screenshot labels as public provenance.

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
  (`{src:'qamus', kind:'authored', lang:'en'}`) when the word is covered, and shows **nothing** when it
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
- **Grammar-resource routing** — screenshots, QAC grammar labels, Tafsir/iʿrāb evidence, and
  concept-map metadata are internal study aids. They may route a learner or reviewer to
  "proper name," "place," "oath wāw," "hidden PP attachment," or "scholar review," but they do
  not supply public hover wording. See
  [`../qamus/procedures/grammar-resource-usage.md`](../qamus/procedures/grammar-resource-usage.md).

## Files in this pack

```
curriculum/
  README.md                      ← you are here
  zero-to-fluency-roadmap.md     ← the 12 levels in full: goal · skills · entries · drill · checkpoint
  qamus-learning-path.md         ← how to study with qamus.dawah.wiki + the hover layer
  quran-reading-path.md          ← graded short-suwar reading path
  hadith-reading-path.md         ← Nawawī40 prose path, with Ṣaḥīḥayn kept owner-gated
  placement-test.md              ← self-scoring test → your starting level
  mastery-checkpoints.md         ← per-level checkpoints + error → remediation procedure map
  assessment/                    ← answer-key schema, grading rubric, sample checkpoint rows
  progress/                      ← learner progress + missed-error log templates (templates only)
  tutor-session-protocol.md      ← tutoring startup and grading loop
  repo-state-and-mission-audit-20260625.md ← current GitHub/repo-state audit for curriculum updates
  qamus-hover-parse-key-and-color.md ← rich-hover parse-key + color-role guidance
  vn-dogfood-to-curriculum-synthesis-20260627.md ← verb/noun dogfood defects mapped to learner units
  reports/dogfood-curriculum-crosswalk-20260627.md ← dogfood finding → curriculum/drill crosswalk
  drills/
    hover-composition-and-routing.md ← written token → pieces → sarf/nahw route → safe hover
    parse-key-and-color-layer.md     ← pieces → parse_key + display palette rows
    dogfood-error-remediation-index.md ← repeated hover failure → remediation route
```

A learner's path through these files: take [`placement-test.md`](placement-test.md) to find a
starting rung, climb [`zero-to-fluency-roadmap.md`](zero-to-fluency-roadmap.md) one level at a
time, use [`qamus-learning-path.md`](qamus-learning-path.md) for the daily reading habit, run
[`drills/hover-composition-and-routing.md`](drills/hover-composition-and-routing.md) whenever a
written token hides multiple pieces, and clear each rung against
[`mastery-checkpoints.md`](mastery-checkpoints.md) before moving up.
Use [`assessment/grading-rubric.md`](assessment/grading-rubric.md) and
[`progress/learner-progress.template.md`](progress/learner-progress.template.md) to make that
clearance stateful rather than informal.
When working on rich hovers, pair
[`drills/hover-composition-and-routing.md`](drills/hover-composition-and-routing.md) with
[`drills/parse-key-and-color-layer.md`](drills/parse-key-and-color-layer.md): first account for
the pieces, then produce a validated parse-key/display contract.
After a dogfood tranche, use
[`vn-dogfood-to-curriculum-synthesis-20260627.md`](vn-dogfood-to-curriculum-synthesis-20260627.md)
to decide whether the finding belongs in a sarf procedure, a nahw procedure, a drill, a
regression fixture, a renderer requirement, or a documented no-op.
For RH-LIVE public-rollout ANDONs, also check
[`reports/rh-live-andon-flywheel-backfill-20260629.md`](reports/rh-live-andon-flywheel-backfill-20260629.md),
which records the newer lessons about role-aware colors, deterministic Qurʾān display text, card-level
coverage, and learner-facing hover prose.

## Assessment, Progress, And Tutoring Runtime

The ladder is not an honor system. A learner clears a level only after attempting the checkpoint
cold and grading it with an answer key, rubric, or procedure-linked two-check rule:

- [`assessment/grading-rubric.md`](assessment/grading-rubric.md) defines level-clearance rules.
- [`assessment/answer-key.schema.md`](assessment/answer-key.schema.md) defines the JSONL checkpoint format.
- [`assessment/level-checkpoints.sample.jsonl`](assessment/level-checkpoints.sample.jsonl) gives concrete,
  dogfood-derived sample checkpoint rows.
- [`progress/learner-progress.template.md`](progress/learner-progress.template.md) tracks level state.
- [`progress/missed-error-log.template.md`](progress/missed-error-log.template.md) tracks recurring misses.
- [`tutor-session-protocol.md`](tutor-session-protocol.md) tells a tutor/agent how to load the repo, grade,
  remediate, and avoid confidence-only hard grammar grading.

For iʿrāb, case, mood, particle function, PP attachment, exception, vocative, oath, pronoun referent, token-only
override, and component-only evidence, the tutor requires two independent checks or an answer-key-backed rubric.
If two checks agree on English but disagree on the grammar reason, the level is not cleared.

## Hard rules honored here

- **Qurʾān text is never altered.** It appears as something to read, never edited for a drill.
- **The learner only ever sees authored content.** Hover glosses are `{src:'qamus',
  kind:'authored', lang:'en'}`; no external dictionary, textbook, or exam text is reproduced anywhere in
  this curriculum. Every drill item and example is original.
- **A blank beats a wrong answer.** The curriculum teaches the same discipline the gloss
  pipeline enforces: when root, pattern, or sense is uncertain, the honest move is PENDING —
  name the doubt and route to the right procedure — not a confident guess.
- **No private detail.** No server paths, secrets, IPs, or external source names as public
  authority. The learner studies on the public app only.
