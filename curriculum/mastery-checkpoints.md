# Mastery checkpoints — clear each rung, and remediate by procedure

A checkpoint is the gate at the top of each rung of the
[`zero-to-fluency-roadmap.md`](zero-to-fluency-roadmap.md): the concrete thing you must be able
to do before you climb. This file does two jobs:

1. State the **pass bar** for every level (the same bars the roadmap names, gathered here).
2. Map every likely **learner error** back to the **exact ṣarf/nahw procedure** that fixes it —
   so a miss is never "study harder," it is "go read *this* file and re-drill."

> The principle, carried straight from the gloss pipeline: a wrong answer is not a small loss —
> it is a *regression*. The fix is never to push past it; it is to route the error to its
> procedure and clear it before moving up. **A precise blank beats a confident wrong** — for the
> authoring agent and for you.

## How to use a checkpoint

- Attempt the checkpoint **cold** — no hover, no notes.
- If you pass the bar, climb.
- If you miss, find your error's **shape** in the remediation table below, open the procedure it
  points to, re-drill that *one* thing, and re-attempt. Do not re-take the whole level; fix the
  specific machinery that slipped.

---

## Checkpoint pass bars (per level)

| Lvl | Checkpoint — you can… | Pass bar |
|---|---|---|
| 1 | read any vowelized 3-letter word aloud (sukūn + shadda) and write a dictated word | first-sight correct, no meaning required |
| 2 | gloss the nine core particles; read `لَمْ` vs `لِمَ` | all particles, both homographs |
| 3 | for 10 nouns: state gender + **attested** plural; add/strip `الْ` | 10/10, plurals from the entry not guessed |
| 4 | extract the root from 12 verbs; state past vs present | 12/12; **no** verb gloss on a noun |
| 5 | translate 5 iḍāfa + 5 jār-majrūr (3 with pronoun) | 10/10; `إِلَيْنَا` = "to us," root `أ ل ي` |
| 6 | label 5 sentences nominal/verbal + find subject; in verbal, mark doer + object | 5/5 type; doer/object by ending |
| 7 | disambiguate `مَنْ`/`مِنْ`, `إِنَّ`/`أَنَّ`, `مَا` in 8 phrases | 8/8, each with the deciding feature named |
| 8 | read an unseen short āyah: gloss covered words, **name** a PENDING for each blank | zero confident wrong glosses |
| 9 | from a root entry: list senses + derived forms; read 2 usage āyāt correctly | senses + forms from memory |
| 10 | read one short Nawawī matn: full parse, correct meaning | covered vs honestly-PENDING kept separate |
| 11 | read a short hadith with isnād: gloss the narration frame, read the matn | frame vs matn register distinguished |
| 12 | read an unseen paragraph: for each block a **named** PENDING + the procedure that clears it | most cleared by yourself |

---

## Error → remediation map

Find the *shape* of your error in the left column; open the procedure on the right; re-drill it.
The reason codes match the pending-reason vocabulary in
[`../nahw/README.md`](../nahw/README.md), so a learner's mistake and an agent's PENDING share one
language.

| Lvl | Error you made | Why it happens | Remediate with |
|---|---|---|---|
| 1 | dropped a sukūn/shadda, or read the wrong vowel | reading consonants, not harakāt | re-drill harakāt; build the habit later enforced in [`../sarf/drills/homograph-regressions.md`](../sarf/drills/homograph-regressions.md) |
| 2 | mixed up `لَمْ`/`لِمَ` (or any short particle) | read the first letter, not the content letter's harakah | [`../nahw/procedures/particle-decision.md`](../nahw/procedures/particle-decision.md) · [`../nahw/references/particles.md`](../nahw/references/particles.md) |
| 3 | wrong plural (invented instead of attested) | treated a broken plural as derivable | [`../sarf/procedures/noun-plural-gender.md`](../sarf/procedures/noun-plural-gender.md) — read the entry's `forms[]` |
| 3 | wrong gender | missed the tāʾ marbūṭa `ة` | same procedure; check the ending letter |
| 4 | wrong root | eyeballed instead of stripping by evidence | [`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md) |
| 4 | gave a noun a verb meaning (`pos_mismatch`) | pattern not checked before glossing | [`../sarf/procedures/verb-form.md`](../sarf/procedures/verb-form.md) · [`../sarf/references/masdar-participle-notes.md`](../sarf/references/masdar-participle-notes.md) |
| 4 | read a participle/maṣdar as a finite verb | gloss-shape rule not applied | [`../sarf/references/masdar-participle-notes.md`](../sarf/references/masdar-participle-notes.md) |
| 5 | mis-rendered preposition + pronoun; `إِلَيْنَا` read as root `ل ي ن` (`seat_collapsed`) | normalized the hamza/seat away | [`../nahw/procedures/preposition-pronoun.md`](../nahw/procedures/preposition-pronoun.md) · [`../nahw/references/jar-majrur.md`](../nahw/references/jar-majrur.md) |
| 5 | iḍāfa direction reversed ("house of the door") | head/dependent order not read | [`../nahw/procedures/idafa-jar-majrur.md`](../nahw/procedures/idafa-jar-majrur.md) · [`../nahw/references/idafa.md`](../nahw/references/idafa.md) |
| 6 | mislabeled sentence type or missed the subject | sentence-opener not identified | [`../nahw/procedures/referent-context.md`](../nahw/procedures/referent-context.md) · [`../nahw/drills/sentence-context.md`](../nahw/drills/sentence-context.md) |
| 6 | doer/object swapped | case endings not read | [`../nahw/references/irab-case-mood.md`](../nahw/references/irab-case-mood.md) |
| 7 | `مَنْ`/`مِنْ` or `إِنَّ`/`أَنَّ` confused (`homograph_haraka`) | content-letter harakah / hamza seat not read | [`../sarf/drills/homograph-regressions.md`](../sarf/drills/homograph-regressions.md) · [`../nahw/references/quranic-nahw-notes.md`](../nahw/references/quranic-nahw-notes.md) |
| 7 | `مَا` read as one fixed meaning | context not consulted | [`../nahw/procedures/particle-decision.md`](../nahw/procedures/particle-decision.md) |
| 8 | invented a gloss for a blank-hover word | guessed instead of PENDING | [`../sarf/procedures/hover-application.md`](../sarf/procedures/hover-application.md) |
| 8 | confident gloss that was wrong | skipped a check (root/pattern/sense) | re-run all three: [`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md) → [`../sarf/procedures/verb-form.md`](../sarf/procedures/verb-form.md) → context |
| 9 | picked the wrong sense of a multi-sense root (`multi_sense` / `contronym`) | sense chosen without context | [`../nahw/procedures/referent-context.md`](../nahw/procedures/referent-context.md) |
| 9 | could not relate a root's forms | derivation not internalized | [`../sarf/references/verb-measures-table.md`](../sarf/references/verb-measures-table.md) |
| 10 | parse broke on a long clause | grammar reasoning not gated | [`../nahw/procedures/grammar-risk-gate.md`](../nahw/procedures/grammar-risk-gate.md) · [`../nahw/drills/grammar-reasoning-safety.md`](../nahw/drills/grammar-reasoning-safety.md) |
| 10 | trusted an unreviewed candidate word | candidate ≠ authored | keep PENDING; see the review boundary in [`../corpora/nawawi40/nawawi40.summary.md`](../corpora/nawawi40/nawawi40.summary.md) |
| 11 | read isnād vocabulary as ordinary prose | register not separated | [`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md); future scope in [`../corpora/sahihayn/PLAN.md`](../corpora/sahihayn/PLAN.md) |
| 11 | asserted an unconfirmed weak/unknown root | root not human/QAC-confirmed | leave as a HINT, not a claim — the SN8/P17 discipline in [`../corpora/nawawi40/nawawi40.summary.md`](../corpora/nawawi40/nawawi40.summary.md) |
| 12 | vague "I don't know" instead of a precise reason | self-diagnosis not specific | name the reason from [`../nahw/README.md`](../nahw/README.md) (`homograph_haraka` / `pos_mismatch` / `multi_sense` / `contronym` / `referent_unresolved` / `proper_name` / `seat_collapsed`) |
| 12 | mistook a proper name for a verb/noun (`proper_name`) | name not recognized as a name | [`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md) — names are not roots to inflect |

---

## The remediation loop, in one line

**Miss → name the error's shape → open its procedure → re-drill that one thing → re-attempt the
checkpoint.** You climb the ladder not by clearing checkpoints once, but by making each missed
checkpoint route you to the exact procedure that turns the miss into a habit.

> Track yourself by **address**: when you clear Level 9 on root `qamus:v###`, log it; when you
> miss, log the error code and the procedure you re-drilled
> ([`../qamus/reports/source-address-model.md`](../qamus/reports/source-address-model.md)). Over
> time your own miss-log becomes the map of exactly where your fuṣḥā is still PENDING — and that
> map, read honestly, is the shortest path to independent reading.
