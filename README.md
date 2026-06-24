# Fusha — reusable Arabic language, source & intelligence layer

**Fusha** is the canonical, reusable research repo for Classical Arabic (fuṣḥā) language intelligence behind the
Dawah.Wiki / **Qamus** project. It holds the *portable* assets — schemas, indexes, morphology/syntax skills,
source-address graph, candidate-generation scripts, and catalogue research — that improve Qamus entry authoring,
qamus-highlight hover-gloss correctness, and future Qurʾān / Nawawī40 / Ṣaḥīḥayn lexical expansion.

> **Dawah.Wiki is the live product.** This repo is **not** the app. It never writes to the live site.

## What belongs here vs the live app

| Stays in the Dawah.Wiki live app repo | Lives (or is mirrored) here in Fusha |
|---|---|
| live qamus app, qamus-highlight runtime + deployed artifact | source-address graph **schema** + samples |
| service / systemd / timer / deploy scripts | Qamus 2,092 **index** export + scoreboards |
| website CSS/JS/nav/theme, live tests/smokes | candidate additions/augmentations (review-only) |
| production backups, private operational detail, secrets | Nawawī40 catalogue outputs; Ṣaḥīḥayn **plan** |
| the 5GB photographed source corpus (raw images) | locator **reports/manifests** (not raw images) |
| anything needed only to *run* qamus.dawah.wiki | reusable OCR/locator + normalization **scripts** |
| | qamus-highlight analysis **reports** (not deploy code) |
| | safe internal provenance schemas; authored-gloss schemas |
| | **sarf** + **nahw** agent skills; morphology/root/POS integration docs |

## Repo map
```
qamus/      schemas · indexes · reports · candidates · scripts   (the Qamus knowledge layer)
sarf/       morphology agent skill + drills + references + regressions
nahw/       syntax agent skill + drills + references + regressions
corpora/    source catalogue · nawawi40/out · sahihayn/PLAN
provenance/ source-boundary rules · informed_by schema
tools/      normalize_ar.py · qac_adapter.py · ocr_locator_notes
```

## Source-boundary rules (see `provenance/source-boundaries.md`)
- External references (Quran.com, QAC, Tanzil, sunnah.com) are **internal evidence for triangulation only**.
- **Never copy external gloss text.** Authored glosses are original, qamus-style English.
- `informed_by` is an **internal** provenance label (which sources informed the authoring). The **public**
  qamus-highlight hover artifact must show **only** `{"src":"qamus","kind":"authored"}` — no `informed_by`,
  no external source names, no OCR snippets, no crop/source-image paths.
- **Qurʾān text is never altered.** No raw source images, model weights, large OCR dumps, secrets, or private
  server paths are committed (this is a **public** repo).

## Generated-artifact rules
Large outputs (full indexes, OCR dumps) are **not** committed raw — commit a **sample + the generator script**,
and keep full output under a gitignored `out/`. Every committed index/report is reproducible from its script.

## Review workflow
Candidate entries / authored glosses / repairs are produced **review-only** (`review_status: needs_human_review`)
and flow through `qamus/reports/fusha-to-qamus-highlight-bridge.md` → human review → owner-gated apply. Nothing
here mutates live Qamus. See `AGENTS.md` for agent rules and `sarf/` + `nahw/` for the decision skills.
