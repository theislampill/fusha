# Source-photo verification — progress

Honest status of the **entry-data** verification lane (distinct from the hover aid, which is live and correct).
Entry fields — headword spelling, forms, sense list, sense-counts, total_uses — are verified against the
**photographed source** (the owner's printed dictionary). That corpus is **owner-gated and not available this
session**, so this lane cannot certify field repairs yet.

## Why the Tafsir MCP does NOT close this lane
The Tafsir MCP supplies **Qur'anic grammar/morphology** evidence (root, wazn, form, iʿrāb) — it does **not** hold
the printed Qamus dictionary's entry data, so it cannot confirm a headword's sense list or `total_uses`. MCP
strengthens the **hover/gloss** lane (form/voice/POS witness), not source-photo entry verification.

## Progress

| state | n | change |
|---|---:|---|
| entries `source_photo_verified` | **0** | no photo pass this session (honest) |
| `needs_source_photo_review` (āyāt hover-complete, fields unverified) | **214** | grew 163 → 190 → 202 → 214 as authoring landed (entries advance into this queue) |
| `needs_quran_ref_verification` (bad/range refs) | **10** | unchanged |
| `deferred_missing_source` (no addressable āyāt) | **7** | unchanged |
| certified source-verified repairs this tranche | **0** | `repairs/repair_batch_005_source_verified.jsonl` (empty by design) |

The 214 count rising is expected and healthy: every batch that makes an entry's example āyāt fully glossed
advances it from `needs_hover_authoring` into `needs_source_photo_review`. The hover aid for these entries is
already live and correct; only the entry DATA awaits the photo.

## What unblocks it
The retake worklist [`retake-source-photo-requests.md`](retake-source-photo-requests.md) lists each entry with
the exact field needing verification. When the owner provides a page photo:
`dry-run → backup_store → DawahAgent edit_entry_record → verify (versioned) → rebuild` (the proven كَظِيم path).

## Lane status: **BLOCKED — owner-gated (source corpus)**; all other lanes continue.
