# Closure-2092 — final closure report (2026-06-24)

Qamus/engine closure tranche. Attacked **root causes**, not token symptoms. The headline result is a
**correction of the prior tranche's frontier claim** plus one fully-executed, measured high-yield lane.

## Headline

- The prior tranche concluded "safe frontier ~86%, 90% not safely reachable." **That was wrong** — it
  measured only one mechanism (surface-wide auto-glossing). Root-cause analysis (QAC gives every
  pending token a root) shows **90% IS reachable** via root-known structured authoring: expected
  safe-realizable ≈ **3,473 tokens → 92.83% ceiling**, vs **+2,061 needed for 90%**.
- Executed the top lever (`missing_form_variant_on_existing_entry`) end-to-end: **+425 resolved live,
  0 wrong glosses**, measured 2-vote approval **44.6%** — empirical calibration of the corrected model.

## Exact numbers

| metric | before | after |
|---|---:|---:|
| HEAD | `bceb366` | `<commit C>` (= origin/main) |
| coverage | 85.02% | **85.87%** |
| resolved / 49,900 | 42,424 | **42,849** |
| pending | 7,476 | 7,051 |
| token decisions | 2,164 | 2,589 |
| removed / changed by apply | — | **0 / 0** |
| wrong-gloss open | 0 | **0** |
| live health | 200 | 200 |

Coarse blockers: `stem_base_unknown` 5,993→**5,595** · `source_entry_unverified` 1,103→**1,076** ·
`same_surface_polysemy_requires_i3rab` 379 · `proper_noun_no_qamus_entry` 1.

## What was produced

- **Root-cause ledger** (`blocker-root-cause-ledger.jsonl`): all 7,051 pending tokens → a specific
  root cause with deciding evidence; validator wired into regressions.
- **Yield ledger v2** (`root-cause-yield-ledger.md`): levers ranked by safe-realizable yield; the
  corrected-frontier proof.
- **Form-variant batch** (`form_variant_batch_001.jsonl`): 121 certified families → 425 per-loc
  decisions, applied live.
- **Hover-quality audit** (`hover-gloss-quality-audit.*`): 42,849 resolved, 91.20% clean,
  **0 public source-leaks** (provenance invariant proven; fixed an "ocr"-in-"hypocrite" false positive).
- **Report-ergonomics gate** (`tools/check_report_ergonomics.py`): 0 crushed Markdown reports.
- **Baseline + repo-org audit** (`baseline-*`, `repo-organization-audit-*`); batch_002 provenance gap fixed.

## Required-field summary (Phase 18)

- live mutation occurred (qamus hover layer only, via the scoped deploy loop) — **not** a webroot /
  phpBB / wiki / DB write; rollback artifact `wbw-lookup.prev.json` retained.
- 2,092 entries audited mechanically (entry rollup reconciled); **live public-page crawl deferred**.
- hover tokens represented: 49,900; newly resolved this tranche: **425**.
- certified payloads produced: 121 families / 425 decisions (all applied).
- source-entry repairs: forms_array sub-cause folded into the batch; quran_refs/photo lanes deferred.
- stem-base: form-variant sub-lane executed (+425); host-lexeme / new-entry / particle lanes deferred.
- iʿrāb decisions: none this tranche (379 polysemy deferred); proper-noun blocker: 1 (token-addressable).
- source-photo: deferred. grammar-metadata audit: done. provenance leak check: **0 leaks**.
- bidirectional graph: 0 orphans (dedicated traversal validator deferred).
- gates run: artifact-ergonomics, report-ergonomics, regressions, grammar-evals, completion-manifest,
  entry-rollup, root-cause-ledger, sarf-skill, nahw-skill — **all PASS**.

## Remaining exact blockers + next command chain

Genuine-ambiguity residue ≈148 tokens; everything else is authorable. To continue toward 90%
(owner-paced, repeatable):

```
# top lever again (form-variant), next tiers:
python tools/build_form_variant_candidates.py --max-b 200 --max-c 200
  -> 2-vote workflow (form-variant-2vote) -> tools/build_form_variant_apply.py
  -> byte-safe append (backup) -> rebuild.sh -> re-stage -> regenerate audit/graph/matrix/ledgers
  -> gates -> commit.   (measured ~44.6% family approval; ~125–200 resolves/batch)
# then: host_lexeme_possessive (1,210), missing_qamus_entry new-entry proposals (473, owner-gated),
#       particle/pronoun-miscoded (418), remaining iʿrāb (379).
```

Each batch re-reconciles all scoreboards; coverage rises ~0.4–0.9 pt per batch until the residue is
all genuinely-ambiguous. 90% is bounded multi-batch work, **not** a wall of ambiguity.
