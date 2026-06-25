# Deep-research findings index (closure-2092 open-stem readiness)

Consolidates `dr01.md`–`dr05.md`. Every verdict was **verified against current code+data**, not trusted.
Companion: `deep-research-findings-index.json`.

## Confirmed engine defects (high severity — fixed this tranche)

| id | claim | verdict | evidence (current) | fix |
|---|---|---|---|---|
| F1 | surface index built from headwords only | **confirmed** | 5,075/6,659 form keys absent from `by_norm`; 1,100 pending tokens index-recoverable | exporter + rebuilder add `usage[].forms`; validator; audit marker |
| F2 | host_lexeme polluted with verb-clitics | **confirmed** | 780/1,210 rows `qac_pos==V` | split to `verb_clitic_object_or_subject_candidate`; host_lexeme noun-only |
| F3 | أتي/رأي misrouted as missing-entry | **confirmed** | 89 rows flatten-match existing entries (أتي 55, رأي 34) | flatten QAC roots before by-root lookup |
| F4 | forms_array includes function words | **confirmed** | 494/633 rows `qac_pos==P`; 138 N/V | route P/function-word to particle/token lane |
| F11 | coverage-90 report reads as current frontier | **confirmed** | "90% not safely reachable" unmarked | HISTORICAL / surface-frontier-only banner |
| F12 | committed batch validators not hard-gated | **confirmed** | no batch/provenance gate in check_regressions | family-batch validator + `--provenance` + wiring |

## Confirmed truthfulness defects (medium — fixed this tranche)

- **F6** stale `existing_qamus_index.json` + old scoreboard names in docs/curriculum → sweep + `validate_canonical_paths.py`.
- **F7** stale `82.49%`/`41,164` baked into proofing matrices + generator + manifest summary → dynamic compute / HISTORICAL.
- **F8** `root-cause-yield-ledger.md` hardcodes 3,859/657 (rows sum 3,461/633) → compute dynamically.
- **F9** blocker-ledger preamble/`_source` says 85.02% while rows are 85.87-era → compute dynamically.
- **F10** `final-closure-report` `<commit C>` placeholder → `74607a9`.
- **F5** `build_decision_backlinks.py` stale path → silent `entry_nodes:0` → fail closed (verify first).
- **F17** "2,092 audited" overstated → status-vocabulary honesty.
- **F19** no bidirectional-link validator → add (modest, graph-only).
- **F20** missing scar-family regression fixtures → add.
- **F13** suffix-pronoun validator too strict for leading and/for prefixes → loosen (verify first).

## Narrowed / lower-priority

- **F14** "git ls-files vacuous in no-git" — dr03 disputes; verify which validators actually call it, add filesystem
  fallback only where present (`check_report_ergonomics` already has one).
- **F18** `usage.examples[].en` in public export — `NOTICE.md` states these are qamus-authored; **report-only note,
  no dataset rewrite** this tranche.
- **F21** tutor runtime — dr03 narrows: production drills already exist; add a **routing appendix**, not a new skill.
- **F15** claude.ai pack missing → build text-only skeleton + verifier.
- **F16** corpus fixture validator missing → add; run Nawawī40; Ṣaḥīḥayn stays plan-only.
- **F22** live-deployment claims unverifiable from repo → label log-claimed.

## Non-actions (false positives / out of scope)

- Reverting the closure-2092 tranche — **no**; all 5 audits agree: continue from `74607a9`, hygiene-first.
- Rewriting the public dataset for `examples[].en` — **no** (F18); decision + separate tranche if ever.
- Mass corpus import / Ṣaḥīḥayn — **no**; plan-only.
