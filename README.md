# Fusha — reusable Arabic language, source & intelligence layer

**Fusha** is the canonical, reusable research repo for Classical Arabic (fuṣḥā) language intelligence behind the
Dawah.Wiki / **Qamus** project. It holds the *portable* assets — schemas, indexes, morphology/syntax skills,
source-address graph, candidate-generation scripts, and catalogue research — that improve Qamus entry authoring,
qamus-highlight hover-gloss correctness, and future Qurʾān / Nawawī40 / Ṣaḥīḥayn lexical expansion.

> **Dawah.Wiki is the live product.** This repo is **not** the app. It never writes to the live site.

## Architecture: the Qamus is the cart, sarf/nahw is the engine

The **Qamus is the cart** (the lexicon/output). The **sarf + nahw skills are the engine** that pulls it; external
sources are **fuel/evidence**, never public output; the **source-address + state graphs are the transmission**.
The engine can pull the existing Qamus, **generate new Qamus** from a corpus, author hover glosses, audit grammar
(the GrammarProblems gate: right answer *and* right reasoning), teach ajami learners, and know when a token must
stay **pending**. It is **MCP-free** — it consults *available source adapters* (`sources/README.md`) only as
optional internal evidence. Full architecture + worked examples: `curriculum/qamus-driven-fluency-engine.md`.
For rich learner hovers, the engine now also targets a source-clean parse-key/color layer:
`curriculum/qamus-hover-parse-key-and-color.md` explains how sarf/nahw decisions become a compact `parse_key`
and scrubbed `qamus-grammar-v1` display classes without leaking QAC/Tafsir/screenshot provenance.

### Engine contract (P2/P2b grammar-checker back-propagation)

Beyond source-addressed hover authoring, the engine now also checks **arbitrary typed Fusha** and exposes its reasoning as data.
Two certainty regimes, kept distinct: a **source-addressed** token (exact `S:A:W`) can reach confirmed readings; **arbitrary typing**
has no source-address certainty and stays ambiguity-preserving. The contracts (each cites an executable tool as its source of truth):

- **Morphology candidate lattice** — analyse-then-rank: keep every competing reading of an unvoweled token, with `score` + `rank`
  (never a boolean `correct`); `>1` candidate ⇒ pending. [`tools/fusha_morphology_lattice.py`](tools/fusha_morphology_lattice.py).
- **Clitic segmentation candidates** — proclitic/enclitic peels as candidates (a lone single-letter peel is low-confidence/likely a
  radical; a tanwīn-alif is not the pronoun نا). [`tools/fusha_text_check.py`](tools/fusha_text_check.py).
- **Governor / iʿrāb dependency lattice** — a case/mood **value** is paired with its **governor justification**; a correct ending
  with an absent/wrong governor is `governor_not_justified` (right answer, wrong reason) → scholar/two-vote review, **never
  `auto_safe`**; PP-attachment stays unresolved unless justified; iḍāfa keeps its alternatives. [`tools/fusha_governor.py`](tools/fusha_governor.py).
- **Abstention-first suggestions** — corrections that retain/reject/abstain rather than overcorrect; iʿrāb edits are never `auto_safe`
  without a governor. [`tools/fusha_suggest.py`](tools/fusha_suggest.py).
- **Learner hint ladder** — Point → Teach → Bottom-out, with Bottom-out withheld past the gate. [`tools/fusha_learner_feedback.py`](tools/fusha_learner_feedback.py).
- **CEFR is scaffolding, not certification** — explanation depth is gated by a *caller-supplied* learner level; the engine never
  assesses or certifies a learner. [`tools/fusha_cefr_gate.py`](tools/fusha_cefr_gate.py).
- **Offline learning runtime** — a deterministic tutor loop grades checkpoints against the answer key (never model self-report),
  schedules reviews by Leitner box, holds hard grammar until two independent checks agree, and persists progress only with an
  explicit `--write`. [`tools/fusha_tutor_runtime.py`](tools/fusha_tutor_runtime.py) ·
  [`tools/fusha_review_scheduler.py`](tools/fusha_review_scheduler.py) · [`tools/fusha_checkpoint_coverage.py`](tools/fusha_checkpoint_coverage.py).
- **Real morphology data, source-clean** — the lattice can confirm an occurrence's `root` as a FACT from *your own local* QAC export
  (QAC is GPL v3 — consulted, never vendored) with an internal `informed_by:['qac']` breadcrumb; the field is null when absent. Which
  public tools need the private WBW services is mapped honestly in [`provenance/public-runnability.md`](provenance/public-runnability.md)
  via the public-safe seam [`tools/qamus_wbw_adapter.py`](tools/qamus_wbw_adapter.py).

The sarf/nahw **skills**, **curriculum/**, and **drills/** teach these contracts; the **evals** + `tools/check_regressions.py` keep
the docs aligned with the tools. This is **tooling** — not live Qamus coverage progress. Fusha-only branch stack (owner-gated, none
merged to main): `a765cef` (P1 general checker + rich-hover flywheel) ← `8365bf7` (P2 governor / leak SoT / conflict) ← `b6a0b4c`
(P2b learning + CEFR) ← `17e5419` (sarf/nahw skill back-prop) ← `8fcad75` (curriculum/drills/README back-prop) ← this branch
(data/runtime completion: tutor runtime, Leitner scheduler, checkpoint coverage, qamus_wbw public-safety, QAC morphology wiring).

**The engine in five examples** (each a regression fixture): أَعْمَالُنَا → "our deeds" (noun stem + possessive,
POS-gated); لَمْ vs لِمَ → "did not" vs "why" (particle state split); مِن vs مَن → "from" vs "who/whoever" (harakat
split); كَظِيم → adjectival ṣifa, **not** the infinitive verb; نَزَّلَ vs نَزَلَ → form II vs I split.

**Install it** as a Claude/Codex skill — see `INSTALL.md` (`scripts/install_claude_skills.py --dry-run`).
**Agent-facing** entry: `sarf/SKILL.md` + `nahw/SKILL.md`. **Learner-facing** entry: `curriculum/`.

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
  qamus-highlight hover artifact must show **only** `{"src":"qamus","kind":"authored","lang":"en"}` — no `informed_by`,
  no external source names, no OCR snippets, no crop/source-image paths.
- **Qurʾān text is never altered.** No raw source images, model weights, large OCR dumps, secrets, or private
  server paths are committed (this is a **public** repo).

## Generated-artifact rules
Large outputs (full indexes, OCR dumps) are **not** committed raw — commit a **sample + the generator script**,
and keep full output under a gitignored `out/`. Every committed index/report is reproducible from its script.

## Artifact ergonomics — how to review the data (humans & agents)
Every committed artifact is **reviewable and diffable** (enforced by `tools/check_artifact_ergonomics.py`,
gated in `check_regressions.py`; classified in `qamus/reports/artifact-taxonomy.md`):
- **reviewer-facing JSON** is pretty (`indent=2`, `sort_keys`, `ensure_ascii=False`, trailing newline) — open it
  and read it; diffs are line-by-line. The navigational lookup indexes (`qamus/indexes/current/by-*.json`) are here.
- **large row-records are JSONL** (one record per line) with a pretty `*.meta.json` sidecar — e.g.
  `qamus/data/current/entries.jsonl`, `qamus/indexes/current/{source-address-full,quran-usage-spine-full,
  qamus-entry-field-addresses}.jsonl`, `qamus/reports/hover-token-audit-full.jsonl`. Grep a line; each is valid JSON.
- **compact is allowed only** for `*.min.json` (machine-only, regenerable from the reviewable dataset) and
  `checksums.json`. Nothing else may be a one-line mega-file.
- query any of it offline, no server: `tools/query_current_qamus.py`, `tools/query_source_address_graph.py`,
  `tools/query_hover_token.py`.

## Review workflow
Candidate entries / authored glosses / repairs are produced **review-only** (`review_status: needs_human_review`)
and flow through `qamus/reports/fusha-to-qamus-highlight-bridge.md` → human review → owner-gated apply. Nothing
here mutates live Qamus. See `AGENTS.md` for agent rules and `sarf/` + `nahw/` for the decision skills.
