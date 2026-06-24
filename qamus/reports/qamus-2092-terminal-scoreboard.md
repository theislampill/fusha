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
*lever* for the live product is not entry mutation — it is the **hover authored-gloss batch** (P4/P5/P13), which
turns pending tokens into resolved qamus-authored glosses without touching entry data.

## P11 audit-completion (GP/P-tranche) — field-level, HONEST
Full matrix: `qamus-2092-audit-completion.json`. Distinguishes *classified* from *actually verified*:
**0 entries are `fully_verified`** (no source-photo pass this tranche; `*_verified` flags reflect only
measurable evidence — refs valid, QAC root agreement, hover coverage).

| audit terminal state | n (live 77.31%) |
|---|---:|
| `needs_hover_authoring` (≥1 pending token in its āyāt) | **1,873** |
| `needs_source_photo_review` (āyāt hover-complete; source verification outstanding) | **202** |
| `needs_quran_ref_verification` (bad/range refs) | **10** |
| `deferred_missing_source` (no addressable āyāt) | **7** |
| **total / unknown** | **2,092 / 0** |

By Fusha index class (per-entry matrices `qamus/reports/{nouns,verbs}/`): **nouns 1,022 @ 79.00%**,
**verbs 970 @ 77.10%**, **particles 100** (PP1). N1/V1 applied 55 glosses (+689 occ); B2 applied 159 (+1,571);
**B3 applied 186 (+1,013) → 77.31%**. As entries become hover-complete they advance `needs_hover_authoring` →
`needs_source_photo_review` (163 → 190 → 202), so the source-photo queue grows as authoring lands.

- root-verified-vs-QAC: measurable cross-check recorded per entry.
- **كَظِيم repair — APPLIED LIVE (gate opened):** the صفة مشبهة gloss-shape fix (verb "to suppress anger" →
  adjectival) was applied via the qamus app `edit_entry_record` (DawahAgent = author; versioned v2→v3 +
  auto-backup); entry count 2092 (edit, not create); propagated to its 3 hover tokens. **1 entry repaired this
  tranche** (`repairs/repair_batch_004_kazim_applied`). ID note: the Fusha index `qamus:n259` is a build-ordinal;
  the entry's own `source_keys=['n365']`.
