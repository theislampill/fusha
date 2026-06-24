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
| **source-address graph** | 2,092 entry nodes, 9,937 evidence links, 0 orphan (live, regenerable) |

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

## Boundaries held (this tranche)
No live entry mutated; Fusha public-clean (0 leaks); no external gloss text; public hover = `src:"qamus"` only;
QAC internal-reference only; Qurʾān text unaltered; OCR never authority. Rollback ready (tsv `.bak-p13` +
`wbw-lookup.prev.json`).

## Next GO (owner-gated)
Apply the P14 كَظِيم entry-repair payload via the DawahAgent path; ramp the next pending tier (the ~21 P13
homographs need phrase-aware/two-vote resolution); the 102 impossible_root QAC-root candidates and Nawawī40
reviewed additions remain owner-gated.
