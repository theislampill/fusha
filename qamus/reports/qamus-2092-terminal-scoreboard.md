# Qamus 2,092 — terminal scoreboard

Every entry has exactly one terminal state (full matrix: `qamus-2092-terminal-matrix.json`). Counts reconcile
to **2,092**, zero unclassified. No live Qamus entry was mutated this tranche.

| terminal state | n | gate |
|---|---:|---|
| clean / already-correct | **1,882** | — (serving glosses) |
| repaired-live this tranche | **0** | — (no certified error class; see repair_batch_001) |
| certified-pending payload | **0** | — |
| source-located (needs-visual-certification) | **69** | owner-gated (scripture visual cert) |
| needs-source-locator | **87** | OCR section window → match headword |
| needs-sarf-review (QAC form-error) | **44** | sarf-review the form→root before any repair |
| needs-nahw-review | 0 | (folded into hover decisions) |
| needs-external-reference-authoring | (see hover scoreboard) | drives the P4 batch, not entry edits |
| duplicate/merge-risk | **10** | confirm the homograph/sense split is intentional |
| source-missing | 0 | — |
| deferred/ambiguous | 0 | — |
| **remaining unclassified** | **0** | — |

## Anomaly classes (before → after this program)
- count_mismatch: 30 (earlier snapshot) → **0** (resolved in current data).
- all-zero total_uses: 27 (earlier) → **0**.
- impossible_root: 126 flagged → re-diagnosed as a **curator noun-keying style** (not an error); **102** have a
  QAC-derivable radical root recorded as owner-gated candidates (`repair_batch_001.evidence.jsonl`).
- QAC-surfaced form-assignment errors: **137** entries (44 land in needs-sarf-review after de-overlap).

## Top next actions
The 50 highest-value non-clean entries (by usage refs) are in `qamus-2092-terminal-matrix.md`. The biggest
*lever* for the live product is not entry mutation — it is the **hover authored-gloss batch** (P4/P5), which
turns pending tokens into resolved qamus-authored glosses without touching entry data.
