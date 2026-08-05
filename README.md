# Fusha — the Arabic-competence flywheel behind Qamus

**Fusha** is a closed Arabic-competence flywheel. Quran-anchored ṣarf (morphology), naḥw (syntax), and
tarkeeb (iʿrāb composition) analysis run over a 2,092-entry lexicon; every claim is typed-fact
certified with exact-occurrence transclusion; curriculum absorption and delivery turn that
certified analysis into a learner ladder; a tutoring runtime drills and remediates against it.
The same certified pieces power the rich colour segmentation and hover glossing of
**qamus.dawah.wiki** — the live app this repo feeds but never writes to.

> **Dawah.Wiki is the live product.** This repo is **not** the app. It is a candidate-mode
> research and authoring layer: every artifact here is reviewable, diffable, and owner-gated
> before anything reaches the live site.

## The flywheel

Corpus work returns knowledge to the skills. A Qurʾānic occurrence is analysed by ṣarf + naḥw,
certified as typed facts with an exact source address, and folded back into the lexicon and the
rule references those same skills consult next time — so each certified occurrence makes the next
analysis better, not just bigger. The curriculum then absorbs that same certified state into a
graded learner ladder, and the tutoring runtime drills and remediates a learner against it. Nothing
leaves the loop uncertified: a word the engine cannot confidently author stays `PENDING` rather
than being guessed.

## Repo map

| Subsystem | What it holds | Leverage path |
|---|---|---|
| **sarf/** + **nahw/** | The skills: morphology and syntax decision procedures | `SKILL.md`, `procedures/`, `rules/`, `references/`, `evals/` in each |
| **qamus/data/current/entries.jsonl** | The lexicon: 2,092 entries (947 verb / 1,045 noun / 100 particle) | one JSONL record per entry, reviewable |
| **qamus/lattice/** | The example-āyah universe | appearance rows + unique occurrences + particle candidate matrix |
| **qamus/indexes/** | Reverse indexes from occurrence to appearance | `qamus/indexes/current/`, `LargeLexicon` |
| **tools/certify_typed_fact.py** + **qamus/certification/** | Fact-level certification | hash-chained event trails per certified claim |
| **curriculum/l1l6/** | The absorbed curriculum substrate | 226 inherited lessons as clean-room metadata + 166 canonical units + tranche machinery (`tools/select_tranche.py`) |
| **eval/fusha-bench-v1/** | The frozen benchmark | data manifest, model card, tutor-quarantine set |
| **docs/** | Architecture + subsystem maps | `docs/INDEX.md` is the authority-precedence entry point |

## State & verification

`python tools/check_regressions.py` must end **ALL PASS**; that is the only accepted evidence of
a green state. Machine-readable current state lives in `docs/current-state.yaml`. Never quote a
prose tally from a report, a plan, or this README as current — recompute it from the validators
and the ledgers. Point-in-time reports (calibration lanes, proofs, closed tranches) are archived
under `docs/reports/history/` with a banner marking them superseded; they are evidence of what was
true when they were written, not of what is true now.

## Work tracking

GitHub issues mirror the committed ledgers at tranche grain — curriculum tranches, qamus VN
windows, particle families. Two milestones anchor the programme: **234-lesson absorption**
(226 inherited lessons + 8 GPS-supplement lessons, tracked with separate denominators) and
**qamus.dawah.wiki rich completeness**. On any conflict between an issue checkbox and a ledger,
the ledger wins; issues are updated *from* ledger state, never the reverse.

## Custody & contribution

This is an **owner-directed, candidate-mode** repository, not a conventional open-source project.
Nothing here performs a live mutation — candidate entries, authored glosses, and repairs are
produced `needs_human_review` and flow through human review to an owner-gated apply. The source
site that this curriculum's lessons were originally drawn from is deliberately not named in this
repo; see `provenance/source-boundaries.md` for the sourcing rules that govern all external
material. External contributions are welcome within those rules — see `CONTRIBUTING.md` and
`AGENTS.md` before opening a PR or issue.

Qurʾān text is never altered. No raw source images, model weights, large OCR dumps, secrets, or
private server paths are committed — this is a public repo, and only the repo's own authored
output (`{"src":"qamus","kind":"authored","lang":"en"}`) is ever shown publicly; no external
gloss, translation, tafsīr, or OCR text is copied into public output.

## Start here

- **Zero-context onboarding:** `START-HERE-FOR-CONTINUATION.md` — read this first if you have no
  prior chat context.
- **Install the skills:** `INSTALL.md` — installs the sarf/nahw engine as a Claude or Codex skill.
- **Authority precedence for the docs themselves:** `docs/INDEX.md`.
