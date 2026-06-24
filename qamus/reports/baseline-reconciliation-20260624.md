# Baseline reconciliation — 2026-06-24 (corrective tranche)

## Verified (not trusted)
| item | value | source |
|---|---|---|
| HEAD = origin/main | `f87c164` (clean) | git |
| live health / entries | 200 / 2,092 | `/healthz` |
| live coverage | **82.49%** — 41,164 / 49,900 | live wbw-lookup `_meta` |
| source_sha | `65797d7d5599fadd` | live artifact |
| token decisions | 904 | live ref jsonl |
| public split | **947 verb / 1,045 noun / 100 particle** | homepage + dataset `section` |
| blockers | stem_base_unknown 6,866 · source_entry_unverified 1,349 · same_surface_polysemy 520 · proper_noun 1 | hover-token-audit-full |
| gates | ergonomics / regressions / dataset / grammar / skill-install all PASS | local |

## Authoritative resolution of contradictions
- **Section split: 947/1045/100 is authoritative** (the public/live `section` field, in the dataset
  and on the homepage). The `970/1022/100` seen in some reports was the **superseded Fusha
  index-ordinal class count** (build-ordinals ≠ source_keys) — not the public split.
- **Coverage: 82.49% is authoritative** (live artifact `_meta.count`). `80.68% / 40,260` was an
  older P12-era figure in superseded reports.

## Stale reports found + action
| report | stale value | action |
|---|---|---|
| hover-token-completion.md/.json | 80.68% / 40,260 | .md marked HISTORICAL; .json removed (superseded by hover-token-audit-full.jsonl) |
| qamus-2092-scoreboard.md | 970/1022 | marked HISTORICAL (superseded by qamus-2092-terminal-scoreboard.md) |
| source-address-completion.md | 1022 | marked HISTORICAL (superseded by xanadu-completion-report.md) |
| language-state-machine-report.md | 80.68 / 40,260 | marked HISTORICAL |
| token-addressed-hover-layer.md | 80.68 | marked HISTORICAL |
| suffix-pronoun-{expansion,hover}-report.md | 81.77 | marked HISTORICAL (point-in-time batch records) |
| {noun,verb}-proofing-matrix.md | 970/1022 | **regenerated** from canonical P2 matrix → 947/1045/100 (`build_proofing_matrices.py`) |
| {noun,verb}-proofing-matrix.json, qamus-2092-{terminal-matrix,audit-completion}.json | 970/1022 | removed (superseded orphans) |
| fusha-production-bridge-status.md | history | current banner at top; history below the `<!-- HISTORICAL -->` marker |

## Gate added
`tools/validate_report_reconciliation.py` (wired into `check_regressions.py`) fails if any
non-HISTORICAL report carries a superseded current-claim — prevents future scoreboard drift.
