# Bulk closure baseline — 2026-06-25

- HEAD `9210155` = origin/main `9210155` = remote `9210155`.
- Repo-local coverage: **43,589 / 49,900 = 87.35%**.
- Live coverage: **verified read-only**, matches repo-local at **87.35%**.
- Pending manifest rows: **6,311**. WBW pending markers: **4,524**.
- Live apply allowed this session: **no** — `fusha` is candidate/report only; live mutation is owner-gated outside this repo.
- Delta to 90%: **1,321** more resolved tokens (target **44,910**). Deterministic batch certifies **198**, leaving **1,123** if owner-applied.

## Gates run

- `python3 tools/check_regressions.py (PASS with UTF-8 I/O)`
- `python3 tools/validate_current_qamus_dataset.py (PASS)`
- `python3 tools/validate_qamus_completion_manifest.py (PASS)`
- `python3 tools/validate_surface_index_covers_usage_forms.py (PASS)`
- `python3 tools/validate_open_stem_lane_sanity.py (PASS)`
- `python3 tools/validate_bidirectional_links.py (PASS)`
- `python3 tools/run_grammar_evals.py (PASS)`
- `python3 tools/validate_pending_source_triangulation_table.py ... (PASS)`
- `python3 tools/validate_bulk_deterministic_hover_decisions.py ... (PASS)`
- `python3 tools/validate_token_hover_decisions.py bulk_deterministic_hover_batch_001.jsonl (PASS)`

## Pending blockers

- `same_surface_polysemy_requires_i3rab`: **380**
- `source_entry_unverified`: **1,775**
- `stem_base_unknown`: **4,156**

## Bulk table / batch

- Triangulation rows: **6,311**; deterministic auto-rule rows after stricter gates: **198**.
- Deterministic batch 001: **198** public-clean token decisions; no live apply performed.
