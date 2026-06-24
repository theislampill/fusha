# Provenance

This directory states **where Fusha's published facts come from, what counts as
evidence, and what may or may not be committed to this public repository.** It is
the contract every other directory (`qamus/`, `corpora/`, `tools/`, `sarf/`,
`nahw/`) is held to.

Read [`source-boundaries.md`](source-boundaries.md) for the exact, enforceable
rules. This file is the orientation.

---

## The one-sentence rule

> **External sources are *internal evidence* used to check our own work; the only
> thing we *publish* is original content we authored and can stand behind, and a
> public hover/gloss artifact carries `{src:'qamus', kind:'authored'}` and nothing
> else.**

Everything below is an unpacking of that sentence.

## Two kinds of "source"

Fusha distinguishes two roles a source can play, and never lets one leak into the
other:

| Role | What it means | What it may touch |
|---|---|---|
| **Evidence (internal)** | A reference we consulted *while authoring* to check a root, a part of speech, a verse boundary, or our reading of a word. | Private notes, validation scripts, `informed_by` labels in **internal** schemas. |
| **Publication (public)** | Text/data we wrote ourselves and are willing to attach our name to. | The committed files in this repo; the public hover artifact. |

The boundary between these two roles is the whole point of this directory. A fact
we *learned* from an external corpus does not become *publishable* by being true —
it becomes publishable by being **re-authored as our own original content**.

## What is and isn't copyrightable (why this is allowed at all)

- **Bare facts are not copyrightable.** That a given Qurʾanic word has the
  trilateral root `ك ت ب`, or that it is a perfect-tense verb, is a fact about the
  language. We may consult any corpus to *confirm* such a fact and we may name the
  corpus we consulted as an `informed_by` label **internally**.
- **Expressive text is copyrightable.** A particular English gloss, a definition's
  wording, an explanatory note, a curated example sentence — these are someone's
  authored expression. We **never copy** them. We write our own.
- **The Qurʾanic text itself is not ours to alter.** We reproduce it unchanged or
  not at all (see `source-boundaries.md` §4).

So: *roots and POS tags may be checked against external corpora and labelled as
`informed_by` internally; glosses, definitions, and notes are authored from
scratch.*

## The public-hover invariant

The public-facing word-by-word hover/gloss artifact is the most sensitive surface
in the whole project, because it is shipped to readers at scale. Its rule is
absolute and testable:

```
every published gloss object  ==  { src: 'qamus', kind: 'authored', ... }
```

- `src` is **always** `'qamus'`. Never `'qac'`, `'quran.com'`, `'tanzil'`,
  `'sunnah'`, or any external name.
- `kind` is **always** `'authored'`. There is no public `kind:'imported'`.
- A word we have **not** authored a confident gloss for is emitted as `PENDING`
  (or simply omitted) — **never** back-filled from an external gloss. *Always
  prefer PENDING over a wrong or borrowed gloss.*

`informed_by` may appear in **internal** build schemas (it records which corpus we
cross-checked a *fact* against). It is **stripped before publication** and must
never appear in the shipped artifact. A provenance test should assert exactly this.

## What may be committed to this public repo

**May commit:**
- Original prose, schemas, and documentation we wrote (this file, etc.).
- Stdlib-only tools and adapters that *describe how to read* an external corpus a
  user fetches themselves — but **not** the corpus data.
- Our own authored entry data, glosses, definitions, examples, and indexes.
- Reproductions of Qurʾanic text that are **unaltered** and used as primary
  scripture (not as a vehicle for someone else's commentary).
- Counts, statistics, and reports derived from our own content.

**May NOT commit:**
- Any external corpus file (QAC `.tsv`, Tanzil text dumps, Quran.com exports,
  sunnah.com data) — these are fetched offline by the user, never bundled.
- Any external gloss / definition / translation **text**, verbatim or lightly
  edited.
- Raw OCR dumps, scanned page images, or any image/binary of source material.
- Secrets, credentials, private server paths, IP addresses, or any live-app /
  deploy / service code.

When in doubt, the file does **not** go in. See `source-boundaries.md` for the
line-by-line enforcement and a pre-commit checklist.

## Files in this directory

- `README.md` — this orientation.
- `source-boundaries.md` — the exact rules, the `informed_by` policy, the
  public-hover invariant, and the commit checklist.
