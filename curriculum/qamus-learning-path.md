# Qamus learning path — studying with the public app + hover layer

This is the **daily reading habit** the ladder hangs on. The
[`zero-to-fluency-roadmap.md`](zero-to-fluency-roadmap.md) tells you *what* to learn at each
rung; this file tells you *how* to turn `qamus.dawah.wiki` and its hover layer into the loop
that actually moves you up the ladder.

> Everything below uses the **public app only**. The learner sees authored content
> (`{src:'qamus', kind:'authored'}`) and Qurʾān text; nothing internal, no external dictionary
> text, no source names. The repo's boundary rules are in
> [`../provenance/source-boundaries.md`](../provenance/source-boundaries.md).

## The loop, in five moves

The habit is a five-step loop you can run on one root in fifteen minutes. It is the same shape
whether you are at Level 8 (one āyah) or Level 12 (a full passage).

```
pick a root → read the entry → study the forms → read the āyāt with hover → drill
     ▲                                                                        │
     └────────────────────────── pick the next root ──────────────────────────┘
```

### 1. Pick a root

Do not pick at random. Climb by **frequency**: the Qamus entries are ordered most-common-first
within each class, so the earliest entries are the words you will meet most. Early on, take the
next verb root you have not studied. At Level 9 and up, follow a root you keep hitting in your
reading. Each root has a stable **address** — `qamus:v###` (verb), `qamus:n###` (noun),
`qamus:p###` (particle) — which is your durable bookmark
([`../qamus/reports/source-address-model.md`](../qamus/reports/source-address-model.md)).

### 2. Read the entry

Open the root's page. Read, in order:

- the **root** (its three radicals) and the **headword**;
- every **sense** — most roots carry several related meanings; do not stop at the first;
- the **total uses** — how often this root appears, which tells you how much it is worth;
- the **notes**, where present, which flag the traps.

The senses are an authored *family*, not a single equals-sign. A root means a cluster, and
context picks the member — which is exactly what the nahw layer decides
([`../nahw/procedures/referent-context.md`](../nahw/procedures/referent-context.md)).

### 3. Study the forms

Read the entry's attested **forms** — the actual surfaces the root takes in the text. This is
where ṣarf pays off: a single root spreads into a past verb, a present verb, a maṣdar, a
participle, a plural. Relate them with
[`../sarf/procedures/verb-form.md`](../sarf/procedures/verb-form.md) and, for nouns,
[`../sarf/procedures/noun-plural-gender.md`](../sarf/procedures/noun-plural-gender.md). Say each
form aloud and name what it is: *"`عَالِم` — ism fāʿil, the one who knows; `مَعْلُوم` — ism
mafʿūl, the thing known; `عِلْم` — maṣdar, knowledge."* Watch the meaning rotate with the
shape, not the root.

### 4. Read the example āyāt with hover

Each entry points at its **usage refs** — `surah:ayah` addresses (`quran:S:A:W`) where the root
appears. Open each āyah on `qamus.dawah.wiki` and read the form *in its sentence*:

- **Hover or tap** a word. A covered word shows an **authored English gloss plaque**. An
  uncovered word shows **nothing**.
- **A blank hover is information, not a failure.** It means the word has not yet earned a
  certified gloss. That is your cue to parse it yourself by procedure — never to invent a
  meaning. (This is the same bar the authoring side holds: see
  [`../sarf/procedures/hover-application.md`](../sarf/procedures/hover-application.md).)
- **Read the gloss against the āyah, not instead of it.** The plaque is a single high-confidence
  word-sense for *that position*; it is a backstop after you have tried, not a substitute for
  trying.

The coverage you see grows as the Qamus entries grow — the same scoreboard the project tracks
at [`../qamus/reports/hover-gloss-scoreboard.md`](../qamus/reports/hover-gloss-scoreboard.md).
So a word blank today may be glossed next month; revisit your hard roots.

> **What the hover never does.** It never shows you who narrated the gloss, an external
> dictionary's wording, or a source name. It shows authored English or it shows nothing. If you
> ever feel you are "reading a dictionary," step back — the point is to read *Arabic* with the
> gloss as a net, not to read English about Arabic.

### 5. Drill

Close the gloss and prove the gain:

- **Cover-and-recall.** Read each usage āyah with the hover off; gloss the studied root's form
  yourself; only then turn hover on to check.
- **Form round-trip.** Given the root, produce its past, present, maṣdar, and participle; given
  a surface form, name the root and what form it is.
- **Sense-in-context.** For two different usage āyāt of the same root, say *which* sense holds
  and what in the sentence decides it.

A drill is passed when you can do all three without the plaque, on a word you had to PENDING the
day before.

## Using source-address nodes as study coordinates

The addresses are not just identifiers — they are how you **navigate and bookmark** your study.

- **Bookmark by address.** "Studied `qamus:v443` today; revisit at `qamus:v443#ref=43:83`"
  records exactly which root *and which āyah* you read, durably.
- **Follow `usage_refs[]` as a reading list.** An entry's refs are a curated set of āyāt that
  use this root — read them as a unit to feel the root's range.
- **Use `wbw:S:A:W` to think about coverage.** Each Qurʾān word position has a hover slot. When
  a slot is blank, you have found an honest gap, not a mistake — note it and move on.
- **Resolve before you trust.** When you meet a *new* word in your own reading, the disciplined
  move (Level 12) is to resolve it to an address before believing a meaning — the same
  duplicate-avoidance probe the authoring side runs
  ([`../qamus/reports/source-address-model.md`](../qamus/reports/source-address-model.md)).

## A worked fifteen-minute session

1. **Pick.** Next unstudied frequent verb root, address `qamus:v###`.
2. **Read.** Its senses — say there are three; read all three and the total-uses count.
3. **Forms.** Produce past `فَعَلَ`, present `يَفْعَلُ`, maṣdar, ism fāʿil; say each aloud.
4. **Āyāt.** Open its three `usage_refs[]`; read each form in context; hover to check; for any
   blank word in the āyah, write a *named* PENDING (homograph? noun-vs-verb? unclear root?).
5. **Drill.** Cover the glosses; re-read all three āyāt; recall the root's sense in each.

Log the address and the date. Tomorrow, start by re-reading yesterday's PENDINGs before picking
a new root. That re-reading is where the ladder is actually climbed.

## Hard rules honored here

- **Public app only; authored content only.** Hover shows `{src:'qamus', kind:'authored'}` or
  nothing. No external dictionary, textbook, or source name is ever the authority.
- **Qurʾān text is read, never altered.** Verify meaning against the muṣḥaf and a teacher.
- **A blank hover is correct.** Coverage grows by authoring more entries, never by guessing.
  When the plaque is blank, parse by procedure — do not invent.
- **Read Arabic, not English about Arabic.** The gloss is a net under the trapeze, not the act.
