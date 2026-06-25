# Live hover apply/readback — 2026-06-25

Private operational paths are intentionally omitted. This report records the public-safe evidence from the gated live apply sequence.

| metric | value |
|---|---:|
| coverage before this continuation | 43,589 / 49,900 = 87.35% |
| current coverage after batch 012 | 46,422 / 49,900 = 93.03% |
| total newly resolved this continuation | 2,833 |
| exact blocker-ledger pending | 3,478 |
| generated lookup pending markers | 2,675 |
| public provenance leaks in lookup | 0 |

## Applied Batches

- `bulk_deterministic_hover_batch_001.jsonl`: +198 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_001.jsonl`: +92 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_002.jsonl`: +39 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_003.jsonl`: +443 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_004.jsonl`: +592 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_005.jsonl`: +383 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_006.jsonl`: +200 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_007.jsonl`: +187 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_008.jsonl`: +191 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_009.jsonl`: +201 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_010.jsonl`: +186 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_011.jsonl`: +108 / -0 / ~0.
- `bulk_certified_apply_batch_20260625_012.jsonl`: +13 / -0 / ~0; SHA-256 `30585cf13ff7253f5c0204926ef5aa3e4982fb7205b7b704205d4c5e08ea80cf`.

## Latest Gate Evidence

- Batch 012 dry-run: +13 / -0 / ~0, projected 46,422 / 49,900 = 93.03%.
- Batch 012 live apply: backup created, token ledger appended atomically, rebuild wrapper passed via `bash`.
- Health: `/` 200 and `/healthz` 200.
- Sample readback: `33:56:13` submission; `38:15:2` looks; `11:17:25` appointed place; `15:29:6` my spirit; `25:75:9` peace.

## Remaining Blockers

- `stem_base_unknown`: 2,261.
- `source_entry_unverified`: 861.
- `same_surface_polysemy_requires_i3rab`: 356.

## Public Crawl Note

A fresh post-batch 012 public crawl passed: 2,092/2,092 pages crawled, 2,092 HTTP 200, 0 render errors, 0 headword mismatches, and 0 hover mismatches across 109,106 hover detail rows.
