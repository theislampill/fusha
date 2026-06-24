# Fusha → production bridge status

How the Fusha intelligence layer is driving live Qamus / qamus-highlight, and where each lane stands.

## ⭐ CURRENT STATE — closure-2092 tranche 2026-06-24d (live 85.87%)

| lane | status |
|---|---|
| **live coverage** | **85.87%** (42,849/49,900); +425 this tranche (form-variant lever, 2-vote 44.6% approval), −0 removed, 0 wrong; 2,589 token decisions |
| **FRONTIER CORRECTED** | the prior "~86% / 90%-not-reachable" claim measured only surface-wide auto-gloss. Root-cause ledger (`closure-2092/`): every pending token has a QAC root → dominant lever is root-known authoring. Yield-v2 **~3,473 safe-realizable → 92.83% ceiling; 90% needs +2,061** — bounded multi-batch work, residue ~148 |
| **form-variant lane** | 121 collision-free families authored (entry-seeded, 2-vote); 122 homograph/voice-collision rejected, 28 disagreement-dropped |

### prior coverage-economics tranche 2026-06-24c (live 85.02%) — frontier claim SUPERSEDED above
| lane | status |
|---|---|
| live coverage | 85.02% (42,424/49,900); +1,260 (safe-surface +1,024, iʿrāb +236) |
| safe-surface lane | 430 collision-free families surface-wide (2-vote); 311 homograph rejected |

### prior corrective tranche 2026-06-24b (live 82.49%)

| lane | status |
|---|---|
| **artifact ergonomics (A1)** | repo dogfoodable — all committed JSON pretty / JSONL / `.min`; gate `check_artifact_ergonomics.py` (0 violations) wired into regressions; 14 one-line mega-indexes fixed |
| **token-iʿrāb polysemy (B3)** | **+188 applied** (2-vote, 50 verifiers) — وما/ألا/فما per-loc + content homographs (عاد transgressor/returned, جنّة garden/madness, ذكر, ذهب, أذن, يحيى=John); Tafsir-MCP iʿrāb on a sample (internal) |
| **host-lexeme (B2)** | **+101 applied** (2-vote, 26 authors) — possessed nouns w/ no dataset host (their evil deeds/your gods/their dwellings…); false-split/preposition/verb-host rejected |
| **source-photo (C0)** | entry→page locator for all 2,092 (candidate bands + verified); 3 head-on verified (بين 523, عبد 275, أخذ 273); 0 retakes; honest read-quality constraint documented |
| **live coverage** | **82.49%** (41,164 / 49,900); this tranche **+289**, −0 removed, −0 changed, **0 wrong glosses**; 904 token decisions |
| **GrammarProblems gate** | 88 cases + 8 wrong-reasoning traps; `grade_grammar_reasoning` AND-gate enforced |

### prior completion tranche 2026-06-24 (live 81.91%)

| lane | status |
|---|---|
| **complete public dataset (P0)** | `qamus/data/current/` — all **2,092** entries exported public-safe (0 leaks), 7 indexes, schema, validator, offline query tool; checksum-gated, LF-pinned |
| **source-address graph (P1)** | `*-full.json` — **28,393** addresses, **0 orphans**, all 10 Xanadu queries answerable offline (`query_source_address_graph.py`) |
| **2,092-entry matrix (P2)** | terminal status per entry, **0 unknown**; honest root-on-noun = curator style; 255 hover-complete |
| **49,900-token audit (P3)** | every token terminal — **40,875 resolved / 9,025 pending**, each pending an EXACT blocker, **no generic pending** |
| **suffix/pronoun (P4)** | +40 applied (2-vote certified); dataset-sourced bases; tanwīn-alef/homograph/verb-host correctly rejected; named classes + tests gated |
| **content batch (P5/P6)** | +30 applied (7 verb + 23 noun; 2-vote); 122/152 rejected as homograph/context/clitic — **0 wrong shipped** |
| **GrammarProblems gate (P9)** | 88 cases incl. **8 wrong-reasoning traps**, grader proves right-answer/wrong-reasoning FAILS |
| **corpus→Qamus (P10)** | bound to the **committed** dataset (`build_existing_qamus_index.py`); Nawawī40 fixtures deduped, 0 live writes |
| **source-photo (P7)** | corpus complete (0 missing, **0 retakes**); 2 entries visually verified by me (v008 بين 523, v027 عبد 275) |
| **live coverage** | **81.91%** (40,875 / 49,900); this tranche +70, −0 removed, −0 changed, **0 wrong glosses** |

History (earlier tranches) follows below.

<!-- HISTORICAL: sections below the current-state banner are point-in-time records -->

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
| **live hover coverage** | **81.77%** (40,805 / 49,900); trail … 79.93 → 80.68 → **B6 token-layer 81.41**; B2–B6 = 1,005 surface glosses + 363 token decisions, +4,627 occ, −0 removed; 61 MCP-backed |
| **language state machine** | built — 12,723 key-states (1,222 resolved, 156 quarantine_homograph, 11,345 pending); schemas + builder + query + report |
| **token-addressed override layer (B6)** | LIVE — per-`quran:S:A:W` decisions > surface-key TSV > pending; wired in `qamus_wbw/expand.py`; 363 decisions resolve لَمْ/لِمَ، مَن/مِن، أَمْ/أُمّ collisions the TSV cannot |
| **Tafsir MCP lane (TM1)** | AVAILABLE (direct HTTP) — internal Quran grammar/morphology evidence; build tool, NOT a skill dependency; 61 MCP-backed glosses live (tafsir_mcp_hover_batch_001) |
| **GrammarProblems eval gate** | 80 derived cases (≥72), `run_grammar_evals.py` PASS; `grade_grammar_reasoning.py` enforces answer+reasoning (self-test PASS) |
| **progressive-disclosure skills** | sarf 12 procedures, nahw 12 procedures + rules/evals/curriculum; SKILL.md is the gate+index |
| **ajami curriculum** | 12-level roadmap + qamus/quran/hadith paths + 8 drill sets + placement test + checkpoints |
| **source-adapter abstraction** | sources/source-adapter.schema.json + 4 manifests (tafsir_mcp/qac/quran_com/tanzil); skills are MCP-free but adapter-aware (generic "available source adapter"); all internal-only, none skill-required |
| **source-photo rescue (S8)** | corpus indexed (1,205 imgs, pages 2-471, 0 missing); 240 reclassified -> needs_manual_visual_review (0 needs_new_photo); ب ي ن verified-from-photo (523=523) |
| **suffix/pronoun lane** | LIVE — noun+possessive resolver (POS-gated; verb hosts excluded); 182 decisions; fixed visible أَعْمَالُنَا→"our deeds"; 81.41->81.77% |
| **token-addressed hover layer (B6)** | LIVE — 363 per-quran:S:A:W decisions resolve لَمْ/لِمَ، مَن/مِن، أَمْ/أُمّ collisions; 80.68->81.41% |
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
