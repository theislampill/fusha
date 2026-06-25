# Repo state and curriculum mission audit — 2026-06-25

This audit records the current public-repo state that the curriculum and drills
should teach from. It is not a live-Qamus coverage claim; it is a read of the
local checkout synced to GitHub `main`.

## Verified repo state

- Remote `main` was checked with `git ls-remote origin refs/heads/main`.
- Local `main`, `origin/main`, and GitHub `main` all point at
  `e5b105a22df46fd45ec884adf63ba0441ccbeefd`.
- Latest commit: `e5b105a Add QAC grammar routing procedures`.
- The working tree also contains many untracked closure candidate/report
  artifacts under `qamus/candidates/qamus_2092/` and
  `qamus/reports/closure-2092/`. Curriculum edits must avoid relying on those
  as committed source unless explicitly checked.

## Commit-history signal

The curriculum and drill folders were not added as a generic textbook. They grew
out of the same closure work that hardened Qamus hover-glossing:

- `F0-F11` bootstrapped the reusable Fusha repo: source boundary, Qamus indexes,
  sarf/nahw references, drills, and corpus plans.
- `SN4-SN5` added verb charts, AMAU/SN-derived sarf-nahw references, and
  learner remediation.
- `GP0` introduced the GrammarProblems gate: grammar decisions require a correct
  answer and a correct reason.
- `Architecture tranche` and `Installable sarf/nahw engine` made the cart/engine
  shape explicit: Qamus is output, sarf+nahw are the engine.
- `post-hygiene` and `audit` commits added tutor routing, artifact ergonomics,
  source-boundary checks, and curriculum paths.
- June 25 commits hardened the production lessons: source triangulation, clitic
  preservation, verb/pronoun hover repairs, morphosyntax gates, and QAC grammar
  routing procedures.

## Current mission

The curriculum exists to turn the same guardrails used by Qamus into a learner's
reading method:

1. Read the written Arabic token exactly.
2. Segment visible pieces before accepting a host gloss.
3. Classify morphology before choosing English.
4. Let nahw decide function, role, case, mood, and referent.
5. Treat QAC and external material as internal evidence only.
6. Prefer a precise pending reason over a confident wrong answer.

That means the curriculum should not drift into ordinary "Arabic lesson" mode.
It should teach learners how Qamus avoids wrong hovers, then use those same
habits to read Qur'an, Nawawi40, Sahihayn preparation, and later Fusha texts.

## Current closure finding to teach from

The committed report
`qamus/reports/closure-2092/current-live-closure-state-20260625.md` reports a
staged/live-synced artifact at 49,255 resolved of 49,900 total tokens, with 645
pending tokens. Treat that number as a repo report, not as a fresh live crawl.

The important curriculum lesson is not the percentage; it is the shape of the
remaining blockers:

- owner-gated new entries are vocabulary growth, not grammar guessing;
- scholar/i'rab rows are reasoning gates, not broad auto-authoring lanes;
- source-entry repair rows need better examples/forms, not borrowed gloss text;
- two-vote rows now mostly fail on exact token identity, clitic/preposition
  preservation, duplicate surfaces, or surface mismatch.

Learners should absorb the same distinction: a blank hover is not ignorance; it
is a named safety boundary.

## Latest tooling/procedure state

The repo now contains:

- `qamus/procedures/grammar-resource-usage.md`
- `qamus/procedures/closure-lane-routing.md`
- `qamus/procedures/source-triangulation-and-public-boundary.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/verb-form-and-mood-review.md`
- `nahw/procedures/function-token-hover-review.md`
- `nahw/procedures/governing-particle-mood-review.md`
- `nahw/procedures/ma-function-decision.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/procedures/exception-and-vocative-review.md`
- `tools/qac_concept_map_adapter.py`
- `tools/test_qac_concept_map_adapter.py`

The curriculum should route learners and agents to these files instead of
repeating their whole content.

## QAC and grammar-resource boundary

QAC concept-map and grammar-resource material may help with:

- semantic routing, such as proper-name vs common-word collision review;
- concept-aware curriculum grouping, such as prophets, places, plants, books,
  body parts, and afterlife locations;
- review prioritization and blocker labels.

It must not be used as:

- a translation source;
- public hover provenance;
- a replacement for sarf, nahw, i'rab, root/POS, or verse context;
- proof that a homographic token takes a concept-map sense.

The public hover boundary remains exactly: `src=qamus`, `kind=authored`,
`lang=en`.

## Update target

Based on the latest state, the learner-facing files need to emphasize three
skills more explicitly:

1. **Clitic composition:** attached bā', lām, kāf, wāw, fā', and suffix pronouns
   must change the visible learning answer when they change the token's
   contribution.
2. **Grammar routing:** `ما`, `و`, `ف`, governing lām/lan/lam/lā, PP attachment,
   conditionals, hāl, vocatives, and exceptions are routing problems before they
   are gloss problems.
3. **Semantic caution:** proper names and concept categories are useful review
   metadata, but only verse-specific sarf/nahw/i'rab can certify a token hover.
