# Ṣaḥīḥayn — future expansion plan (catalogue-first, owner-gated)

**Status: PLAN ONLY. No ḥadīth content is staged, tokenized, or committed under this directory.
This file is a roadmap, not a green light.** Expansion past the nawawī40 pilot requires the
owner's explicit go-ahead. Nothing here may run against Ṣaḥīḥ al-Bukhārī or Ṣaḥīḥ Muslim text
until that gate is opened.

## Why catalogue-first, and why later

The nawawī40 pilot proves the full pipeline (catalogue → diff → reviewable candidates) on a
small, canonical, well-bounded text — 42 ḥadīth. The Ṣaḥīḥayn are orders of magnitude larger
and carry heavier responsibilities (numbering systems, isnād vs. matn, recurring formulae,
narrator chains). We do **not** scale up until:

1. the nawawī40 candidates have been through human review and the false-positive rate of the
   diff classifier is measured and acceptable;
2. the owner has decided the licensing/provenance posture for a larger ḥadīth corpus; and
3. the normalization guardrails have held across the pilot without a single verb-gloss-on-noun
   or homograph-particle miss.

This document is intentionally scoped to **vocabulary cataloguing only** — building a lexicon
of surface forms and diffing them against Qamus. It does **not** propose publishing ḥadīth
text, translations, or commentary.

## Hard constraints (inherited, non-negotiable)

- **No ḥadīth content now.** No matn, no isnād, no translations are staged or committed here.
- **Matn only, isnād excluded** when work eventually begins — the lexical target is the matn's
  Arabic vocabulary, not narrator chains. Isnād tokenization is explicitly out of scope.
- **Read-only text.** Surface forms preserved verbatim; nothing reshaped or re-pointed.
- **External references are evidence, never content.** sunnah.com et al. may be **named** as
  `access_method` / `informed_by` labels; their translation/commentary text is never copied.
- **Authored glosses only.** Any sense that could reach a public artifact is
  `{src:'qamus',kind:'authored'}`; PENDING beats a wrong gloss.
- **No private paths, no secrets, no live-site code, no raw OCR/image dumps.**

## Reuse: the pipeline is corpus-agnostic by design

The three pilot scripts already generalize. A Ṣaḥīḥayn run, when authorized, would reuse them
unchanged in shape:

| stage | pilot script | Ṣaḥīḥayn reuse |
|---|---|---|
| 1. catalogue | `catalogue_nawawi40.py` | a sibling `catalogue_sahihayn.py` (or `--corpus-id sahihayn`) reading a local **matn-only** dump via `--src`, same tokenizer + `normalize_ar` keys |
| 2. diff | `diff_against_qamus.py` | reused as-is — point `--lex` at the Ṣaḥīḥayn lexeme candidates |
| 3. stage | `make_candidate_payloads.py` | reused as-is — `source_scope:["sahihayn"]`, `status:"candidate"`, `review_status:"needs_review"` |

The only net-new code is a Ṣaḥīḥayn-specific stage-1 reader that:
- accepts the larger collection's numbering (book/chapter/ḥadīth) as the `ref`,
- splits matn from isnād **before** tokenizing (isnād dropped),
- normalizes recurring report formulae (e.g. transmission verbs) so they don't flood the
  candidate set, and
- records the named edition/dataset as `access_method` exactly as nawawī40 does.

## Phased roadmap (each phase owner-gated)

### Phase 0 — pilot validation (prerequisite, nawawī40)
- Run the nawawī40 pipeline end-to-end; have a human review the candidate streams.
- Measure: how many `already_in_qamus` were correct, how many `new_*` were real, how many
  homograph particles the harakah checker resolved vs. flagged.
- Exit criterion: classifier behavior understood and acceptable; **no** verb-gloss-on-noun or
  proper-name-as-verb in the staged candidates.

### Phase 1 — scope & provenance decision (owner)
- Owner sets the licensing/provenance posture for a larger ḥadīth corpus.
- Decide matn-source edition(s) and the `access_method` citation label(s).
- Confirm: matn-only, isnād excluded, vocabulary-catalogue-only — no text redistribution.

### Phase 2 — Ṣaḥīḥayn stage-1 reader (code, still no live publish)
- Build the matn/isnād splitter + numbering-aware reader.
- Dry-run the catalogue on a **small, owner-approved** subset first; sanity-check token counts
  and formula handling before any full pass.

### Phase 3 — diff & candidate staging (reuse stages 2–3)
- Diff the Ṣaḥīḥayn lexeme candidates against the Qamus index (now possibly grown by nawawī40).
- Stage `new_entries` / `occurrence_augments` / `review_queue` exactly as the pilot does.
- **Everything remains `status:"candidate"`, `review_status:"needs_review"`. Nothing publishes.**

### Phase 4 — human review & (separately gated) authoring
- Human review of every candidate; authored original glosses only.
- Any move from candidate → live entry is a **separate**, owner-gated step outside this repo's
  cataloguing tools.

## What this directory will and will not contain

Will (eventually, when authorized):
- `PLAN.md` (this file), and later an `out/` of **vocabulary catalogues and candidates** — the
  same JSONL shapes as `corpora/nawawi40/out/`.

Will **never** contain:
- Ṣaḥīḥayn matn paragraphs, isnād, translations, commentary, OCR dumps, or image data.

Until Phase 1 is signed off, the only file here is this plan.
