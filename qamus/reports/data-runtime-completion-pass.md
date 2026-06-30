# Data / runtime completion pass — report

Status: repo-only data/runtime hardening. No live Qamus data, WBW artifacts, services, mirrors, or hover decision
ledgers were changed. Dry-run; source-clean; deterministic; no progress writes without an explicit flag. Branch
`fusha-data-runtime-completion-pass` off `8fcad75` (not merged to main; not force-pushed).

## What this pass closed (the 5 criticisms)

| # | Criticism | Verdict | What changed |
|---|---|---|---|
| 1 | Morphology lattice lacks real root/lemma/pattern data | partially true | `fusha_morphology_lattice.py` now has an OPTIONAL, opt-in QAC consult: with a user-supplied local `QacAdapter` + a source address it attaches the occurrence's `root` as a FACT + `informed_by:['qac']`; null + **byte-identical** default otherwise. Schema gained an optional `informed_by`. No QAC data vendored (GPL v3). |
| 2 | Public repo depends on private `qamus_wbw` | true | New `tools/qamus_wbw_adapter.py` (public-safe loader: `available()` / `load_services()` → actionable `SystemExit`, never a bare `ModuleNotFoundError`); `provenance/public-runnability.md` matrix classifies all 11 importers; `tools/validate_public_runnability.py` keeps the matrix in sync and blocks new unguarded importers. (Converting the 9 unguarded importers = P1.) |
| 3 | Checkpoint bank too small/uneven | partially true | `tools/fusha_checkpoint_coverage.py` reports rows by level/hardness/route, names empty bands (today: **6, 11, 12**), flags thin/heavy bands, and FAILs on any dangling cited procedure/route path (sample = 0 dangling). No fake generation. |
| 4 | No spaced repetition / review scheduling | true | `tools/fusha_review_scheduler.py` — deterministic Leitner (time passed in explicitly, no RNG); promotes only on a FULL pass; a right-answer-wrong-reason or pending two-vote **HOLDS**; a miss demotes. |
| 5 | Runtime is manual copy-paste | true | `tools/fusha_tutor_runtime.py` — offline loop: select next (due review / new) → grade against the answer key (content match + required-reasoning + forbidden-answer + two-vote; **never** a self-report) → route miss → Leitner update → progress written **only with `--write`** → replayable event log. |

## Validation
- Smoke A (baseline) = **845 ok / 0 FAIL**. Smoke B = **862 ok / 0 FAIL** (845 + 17 new gates).
- Every new tool ships `--self-test`; all wired into `tools/check_regressions.py`.
- Morphology default emit proven **byte-identical** to the pre-change baseline (`diff -q`).
- `validate_tutor_runtime.py`: statically + behaviorally proves the grader ignores self-reported correctness,
  the two-vote gate holds, promotion requires a full pass, no write occurs without `--write`, output is
  deterministic, and events/progress conform to the JSON schemas.

## Deep-research (re-run) + adversarial closure
- **Deep-research** `wfns8dglb` (106 agents; 14 findings, each verified **3-0** vs primary sources) confirmed every
  design choice — Leitner (no interval fuzz; Anki's fuzz deliberately avoided), ASAG verification-first grading
  (refuted: shallow bag-of-words alone), the sktime soft-dependency seam, QAC GPL-v3 + SAMA fee-gated + CAMeL-not-stdlib
  → user-local-TSV-never-vendor, and report-not-generate coverage. (The first run was a rate-limit artifact and was
  re-run.) Citations in the plan packet's `010-deep-research-findings.md`.
- **Adversarial review** (attack lanes + refute-verify) surfaced **3 confirmed** findings, all **fixed**:
  (1) `fusha_checkpoint_coverage` `heavy_bands` leaked out-of-roadmap levels and unbinned rows were invisible →
  bands constrained to 1–12 + an `out_of_roadmap` reconciliation line + a self-test; (2) the morphology lattice's
  "never auto_safe" assertion was **vacuous** (no unit exercised the arbitrary→two_vote upgrade) → added a voweled
  article-noun unit that FAILs if the upgrade is removed (proven); (3) the curriculum/drills/README anti-stale guard
  still hardcoded the prior tip `17e5419` → bumped to the current `8fcad75`.

## Design decision (research-backed)
A right-answer-wrong-reason / pending-two-vote outcome is **HELD** at its current Leitner box (re-due immediately),
not demoted to box 0. Deep-research finding [2] endorses both "refuse promotion" and "reset-on-failure"; refusing
promotion is the load-bearing safety property (it can never be marked mastered), and holding is gentler than a full
reset for a surface-correct answer. A strict reset-on-failure variant is recorded as a P2 option.

## Source-boundary / licensing
- QAC is **GPL v3** → never vendored. Only a user's own local export is consulted; the adapter ships, the data
  does not. `root`/POS are uncopyrightable facts; `informed_by:['qac']` is an internal breadcrumb stripped before
  any public artifact (source-boundaries §1.2/§2/§3). No external gloss/translation text copied.

## Public-runnability status
11 `qamus_wbw` importers: 1 public-runnable (`test_token_irab_help.py`), 1 maintainer-only-graceful
(`build_token_irab_decisions.py`), 9 maintainer-only-unguarded (crash at import on a clone). None is executed by
CI (3 appear only as existence checks), so public CI stays green. The matrix + validator make this honest and
prevent new unguarded importers; converting the 9 is P1.

## Not done (deferred, with reasons)
- Authoring checkpoint rows for empty bands 6/11/12 (scripture-adjacent → owner-reviewable) — P1.
- Converting the 9 unguarded importers to the shared loader (mechanical, none gate CI) — P1.
- Machine placement-test runner, drill answer-key fixtures, eval coverage thresholds, event-log replay validator — P1.
- Index integrity, dataset CI wiring, claude.ai pack drift, CEFR monotonicity property test — P2.
- Live-server-dependent export/source-photo tooling — blocked (needs non-public data); fenced + documented.
- Audio / speaking / dialect / conversational — out of scope (hard exclusion).

## How to drive the runtime (offline, deterministic)
```
python tools/fusha_tutor_runtime.py --select --now 0                     # what to attempt next
python tools/fusha_tutor_runtime.py --item <id> --answer answer.json --now 0        # dry-run grade (writes nothing)
python tools/fusha_tutor_runtime.py --item <id> --answer answer.json --progress me.json --event-log me.events.jsonl --write
python tools/fusha_checkpoint_coverage.py curriculum/assessment/level-checkpoints.sample.jsonl
```
Keep real learner progress + event logs OUTSIDE the repo (private).
