# P1 / P2 closure — report

Status: repo-only data/runtime closure of all open P1 (7) + P2 (5) plan items. Dry-run; source-clean; deterministic;
no live Qamus; no progress writes without an explicit flag. Continues branch `fusha-data-runtime-completion-pass`
(builds on the P0 data/runtime commit `f7b6d9f`). Not merged to main; not force-pushed.

## What landed

| Item | Verdict | Deliverable |
|---|---|---|
| P1-1 | done | 9 `qamus_wbw` importers converted to a lazy `qamus_wbw_adapter.load_services()` seam — each now imports cleanly + answers `--help` on a fresh clone (compile + `--help` verified, no `ModuleNotFoundError`); matrix flipped unguarded→guarded; `validate_public_runnability` green. |
| P1-2 | done | 6 source-clean checkpoint rows authored for the empty roadmap bands **6 / 11 / 12** (quran_example=null; L11/L12 two_vote_required=true; 0 dangling). Coverage `empty_bands` now `none`. |
| P1-3 | done | `tools/fusha_placement_test.py` + `placement-test.sample.jsonl` — deterministic placement runner reusing the tutor grader (content-only, not self-report); recommends the lowest uncleared rung. |
| P1-4 | done | `tools/validate_drill_keys.py` + 4 objective drill answer-key fixtures under `curriculum/drills/keys/`; the 7 deferred (open-prose/routing) drills are named in the validator docstring. |
| P1-5 | done | `tools/fusha_eval_coverage.py` — read-only coverage over all 11 `*.jsonl` eval banks (751 rows) + the runner gap; the 7 `.json` object-form artifacts are surfaced (not silently excluded). |
| P1-6 | done | `tools/validate_tutor_event_replay.py` — event-sourced replay reconstructs the runtime's progress state byte-for-byte; a tampered log is caught. |
| P1-7 | done | optional, DEFAULT-OFF grammar-reasoning bridge in `fusha_tutor_runtime.py` (delegates the reasoning check to `grade_grammar_reasoning` only when opted in; default output byte-identical; an agreement check, not an override). |
| P2-8 | done | `tools/validate_index_integrity.py` — every secondary index (by-lemma / by-root / by-quran-ref / by-normalized-surface) resolves to a live `by-entry-id` entry; 0 orphan ids on the real indexes; synthetic orphan caught. |
| P2-9 | **BLOCKED** | pre-existing `entries.jsonl` sha mismatch (working `a68245…` vs `checksums.json` `61a536…`; **not** CRLF — `.gitattributes` forces LF; owner-territory data). Documented in `dataset-integrity-blocker.md`; `tools/report_dataset_integrity.py` is a NON-fatal reporter (`--strict` exits 1). The validator is NOT hard-gated on the mismatched data; only the reporter's self-test is gated. No regeneration of the data/checksums (owner decision required). |
| P2-10 | done | `tools/validate_claude_ai_pack_drift.py` — read-only sha check of the 35 manifest rows (does NOT rebuild). The committed `knowledge-manifest.md` was stale across several prior stack commits; regenerated generator-first (`scripts/build_claude_ai_project_pack.py`; pack/ is gitignored so only the manifest changed) → 0 drift, gate wired clean. |
| P2-11 | done | `tools/validate_cefr_monotonicity.py` — proves the 7 CEFR levels' display-depth gating is monotonic via `fusha_cefr_gate`; no certification / forced-parse / withheld-reveal; non-monotonic ladder caught. |
| P2-12 | done | optional DEFAULT-OFF `mode="sm2"` in `fusha_review_scheduler.py` (canonical SuperMemo SM-2: I(1)=1, I(2)=6, I(n)=⌈I·EF⌉, EF init 2.5 floor 1.3, q<3 reset; **no fuzz**). `mode="leitner"` stays the byte-identical default; the right-answer-wrong-reason HOLD applies in both modes. |

## Validation
- Smoke A (P0 tip) = **862** → Smoke B = **886 ok / 0 FAIL** (+24 gates). Every new tool ships `--self-test`, all wired.
- Importer clone-safety independently verified (9× compile + `--help`, no `ModuleNotFoundError`).
- claude.ai manifest regenerated generator-first (single tracked file; pack/ gitignored).

## Adversarial review + fixes
The review's attack phase ran (10 lanes); its verify phase was cut off by a session usage limit, so findings were
**verified manually on the main thread**. Most lanes confirmed the claims HOLD (determinism; SM-2 hard-gate; content-only
grading; index reconciliation; eval reads all 11 jsonl banks; CEFR non-degenerate). Five genuine items, all fixed:
- **F1** (should_fix): placement rows had over-permissive single-token accepted-forms. Added a durable self-test guard
  proving **no** shipped row is clearable by a degenerate one-token answer (the required-reasoning gate already blocked it;
  the guard makes it permanent). 
- **F2** (latent): switching a Leitner-scheduled state into `mode="sm2"` computed `interval=0` (perpetually due). Added a
  migration guard (a state with no `interval` key starts the SM-2 ladder fresh) + a self-test.
- **F3** (nit): eval-coverage silently omitted the 7 `.json` eval artifacts → now surfaced explicitly.
- **F4** (nit): the 7 deferred drills are now named in `validate_drill_keys`.
- **F5** (nit): documented that placement uses a conservative all-items-clear (per-section partial credit intentionally
  not modeled — under-placing is safe).

## Remaining (future)
P2-9 stays owner-gated (dataset/checksum authority). Everything else in the P1/P2 ladder is closed. Further work is new
scope (authoring more checkpoint/drill keys, wiring runners for the `.json` eval artifacts, a learned disambiguator for the
morphology lattice's deep features).
