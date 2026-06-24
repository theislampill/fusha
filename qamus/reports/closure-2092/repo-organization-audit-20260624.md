# Repo organization & artifact-ergonomics audit (closure-2092, 2026-06-24)

Targeted owner/source audit — NOT a cosmetic rewrite. Companion: `repo-organization-audit-20260624.json`.

## Findings

| # | finding | severity | disposition |
|---|---|---|---|
| 1 | `token_irab_batch_002.{jsonl,provenance}` untracked while `_001`/`_003` are committed; batch_002 (+112, applied live) has a git provenance gap | medium | **fixed this tranche** (commit A) |
| 2 | 15 generated-style Markdown reports lack an explicit generator/source note | low | new gate **warns** (soft); follow-up queue, not blocking |
| 3 | Largest committed artifact `hover-token-audit-full.jsonl` = 10.1 MB | low | **keep** — load-bearing (5 consumers incl. completion-manifest + regressions), regenerable; acceptable for a public-dataset repo |
| 4 | Large committed dataset/index JSONL (entries 4.8 MB, usage-spine 4.5 MB, source-address 3.5 MB) | n/a | **keep** — these ARE the public deliverable (Xanadu dataset + graph) |
| 5 | Scoreboard pairs (`qamus-2092-scoreboard` vs `…-terminal-scoreboard`, `hover-gloss-scoreboard` vs `…-terminal-scoreboard`) | n/a | **already handled** — `<!-- HISTORICAL … current canonical: … -->` markers present (Tranche-3 fix) |
| 6 | No Markdown report-ergonomics gate existed (JSON had one) | medium | **fixed** — added `tools/check_report_ergonomics.py`, wired into `check_regressions.py` |

## What was verified clean

- 55 committed reports under `qamus/reports/` — **0 crushed one-line reports**, **0 crushed tables**
  (the A1 ergonomics pass already normalized these). Report-ergonomics gate exits 0.
- 9 reports carry explicit `HISTORICAL` markers → current/historical hygiene is in place.
- All 8 prior gates green on current state (see baseline).

## Durable improvements added

- `tools/check_report_ergonomics.py` — fails crushed one-line Markdown reports / crushed tables;
  soft-warns on generated reports lacking a generator note. Wired into `check_regressions.py`.
- `tools/build_blocker_root_cause_ledger.py` + `tools/validate_blocker_root_cause_ledger.py` —
  the Phase-3 root-cause ledger + its reconciling validator (wired into `check_regressions.py`).
- `tools/build_root_cause_yield_ledger.py` — Phase-4 yield ledger v2.

## Follow-up queue (non-blocking)

- Add a one-line generator/source note to the 15 flagged generated reports (soft warnings).
- Optional: convert `hover-token-audit-full.jsonl` to sample + `.meta.json` + gitignored full IF a
  consumer is taught to regenerate it first (deferred — current load-bearing status makes this risky).
