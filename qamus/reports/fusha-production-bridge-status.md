# Fusha → production bridge status

How the Fusha intelligence layer is driving live Qamus / qamus-highlight, and where each lane stands.

## The production loop (operational)
```
Fusha decision engine (sarf+nahw rules + QAC + Qamus index)
  → linguistic-decision JSONL (authored_gloss | pending | quarantine | repair_candidate)
  → 2-vote verification
  → export_hover_decisions.py → fusha-hover-decisions.tsv  (gitignored server ref)
  → live expand.py `fusha` pass applies it (src=qamus)  → rebuild.sh → deploy → verify
```
Entry repairs take the parallel, owner-gated path (`edit_entry_record` + backup + DawahAgent).

## Lane status
| lane | status |
|---|---|
| **sarf/nahw skills** | operational — SKILL.md + 4+4 machine-readable rule files; runner self-test PASS |
| **executable decision layer** | `run_linguistic_decisions.py` (runner) + `validate_linguistic_decisions.py` + `export_hover_decisions.py` |
| **Qamus 2,092 terminal matrix** | complete — 2,092 reconciled, 0 unclassified |
| **hover-token terminal matrix** | complete — 49,900 classified, no silent unknown, 0 known wrong open |
| **P4 authored-gloss batch** | top pending vocabulary authored + 2-vote verified |
| **P5 live apply** | `fusha` pass wired into expand.py (no-op until the tsv lands), proven byte-stable |
| **P6 source-corpus repair** | terminally classified — 0 certified error fields; 102 owner-gated QAC-root candidates |
| **Nawawī40 catalogue** | first pass (720 candidates) + skill-refinement available via the runner |
| **source-address graph** | 2,092 entry nodes, 0 orphan; operational backlinks (`build_decision_backlinks.py`) answer the 10 graph queries |
| **live hover coverage** | **79.93%** (39,887 / 49,900); trail … 72.14 → 75.28 → 77.31 → 78.78 → **B5 79.93** (B2–B5 = 716 glosses, +3,891 occ, −0 removed; B5 first MCP-aware, 61 MCP-backed) |
| **language state machine** | built — 12,723 key-states (933 resolved, 156 quarantine_homograph, 11,634 pending); schemas + builder + query + report |
| **Tafsir MCP lane (TM1)** | AVAILABLE (direct HTTP) — internal Quran grammar/morphology evidence; build tool, NOT a skill dependency; 61 MCP-backed glosses live (tafsir_mcp_hover_batch_001) |
| **GrammarProblems eval gate** | 80 derived cases (≥72), `run_grammar_evals.py` PASS; `grade_grammar_reasoning.py` enforces answer+reasoning (self-test PASS) |
| **progressive-disclosure skills** | sarf 12 procedures, nahw 12 procedures + rules/evals/curriculum; SKILL.md is the gate+index |
| **ajami curriculum** | 12-level roadmap + qamus/quran/hadith paths + 8 drill sets + placement test + checkpoints |
| **corpus → Qamus pipeline** | `corpus_to_qamus_candidates.py` + `corpus_to_hover_decisions.py` (Nawawī40-proven, 0 live writes) |

## Boundaries held
No live entry mutated; Fusha public-clean (0 leaks); no external gloss text; public hover = `src:"qamus"` only;
QAC internal-reference only; Qurʾān text unaltered; OCR never authority.

## GrammarProblems / P-tranche update (live coverage 70.47%)
| lane | status |
|---|---|
| **GrammarProblems eval gate (GP0)** | matrix + 4-tier gates + policy + drill; warning in SKILL/AGENTS; enforced |
| **executable gates (P10)** | `validate_linguistic_decisions.py` rejects below-gate / no-reasoning / non-exportable; 6 new rule files; schema +gate/+triggers/+reasoning; 25 regression checks |
| **audit-completion (P11)** | 2,092 field-level, **0 unknown, 0 fully_verified** (honest); top-100 finish-next |
| **hover-token completion (P12)** | 49,900 classified, 0 silent; top-500 pending pool |
| **P13 reference-assisted batch** | **23 APPLIED LIVE** (+694 occ, coverage 69.08→70.47%, 0 removed); ~21 homograph/referent/polysemy terminally pending |
| **P14 entry repair** | كَظِيم certified **payload** (`repair_batch_002_p14`), owner-gated apply — 0 entries mutated |
| **P15 source-address** | 2,092 nodes (v970/n1022/p100), 7 splits, 0 orphan; duplicate-avoidance report |
| **P17 Nawawī40** | re-run under GP gates; 189 weak-root hints (low-conf), 0 live writes |

## PP1 particle-first proofing + Q2 (live coverage 70.76%)
| lane | status |
|---|---|
| **baseline reconciliation** | report + live AGREE at 70.47%→70.76%; GitHub not stale (69.08 was SN7 history); CURRENT-LIVE banner added |
| **ID reconciliation** | Fusha index `qamus:nNNN` = build-ordinal ≠ entry `source_keys` (index n259=كَظِيم, entry source_key n365) |
| **PP1 particle p001–p100** | 100 particles proofed, 219-āyah source-addressed spine (3,245 nodes); **26 content glosses APPLIED LIVE** (+141 occ → 70.76%), 4 homographs pending |
| **Q2 كَظِيم repair** | **APPLIED LIVE** via `edit_entry_record` (gate opened): verb→adjectival صفة مشبهة; v2→v3 versioned+backup; 1 entry repaired |

## Boundaries held (this tranche)
No live entry mutated; Fusha public-clean (0 leaks); no external gloss text; public hover = `src:"qamus"` only;
QAC internal-reference only; Qurʾān text unaltered; OCR never authority. Rollback ready (tsv `.bak-p13` +
`wbw-lookup.prev.json`).

## Next GO (owner-gated)
Apply the P14 كَظِيم entry-repair payload via the DawahAgent path; ramp the next pending tier (the ~21 P13
homographs need phrase-aware/two-vote resolution); the 102 impossible_root QAC-root candidates and Nawawī40
reviewed additions remain owner-gated.
