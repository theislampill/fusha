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

## Next GO (owner-gated)
Apply the confirmed P4 batch live (done in this tranche if verify completes), then: ramp the next pending tier
(multi-sense roots resolved by `nahw` context), and — on owner approval — the 102 impossible_root QAC-root
candidates and the Nawawī40 reviewed additions.
