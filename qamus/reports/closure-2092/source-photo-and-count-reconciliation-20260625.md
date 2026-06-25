# Source-photo + count reconciliation — 2026-06-25 (Phase 4)

## Source-entry repair queue (refreshed, read-only, gated)

| mode | entry candidates | tokens | gate |
|---|---:|---:|---|
| `forms_array` (add inflected surface to forms[]) | 85 | 149 | field-level, no blind add_form, 2-vote |
| `quran_refs` (add missing āyah ref) | 41 | 71 | field-level |
| `source_photo` (visual verification needed) | 4 | 4 | **source-gated (owner crops)** |

The `source_photo` lane is the source-photo "batch-006": 4 entries whose field values cannot be
resolved without a head-on crop of the owner's physical source page. Validator:
`SOURCE-ENTRY REPAIR OK — field-level repair candidates, gated, no blind add_form, no leak`.

## Count reconciliation — internally consistent

For all **2,092** entries, compared claimed `total_uses` against the number of distinct example
āyāt cited and the sum of per-sense counts:

- **0 entries** where cited example āyāt **exceed** claimed `total_uses` — i.e. no entry shows more
  examples than it claims uses. The expected relationship (cited examples ⊆ total uses) holds
  everywhere. No internal count contradiction.

## What remains owner/source-gated (honest)

Digit-level verification — does an entry's `total_uses` match the **count printed in the physical
source book** — requires reading the owner's source-page crop. That is a source-gated visual step
(`source_photo_visual_needed`, 4 queued); it is NOT resolvable from the repo or the live site, and
OCR is discovery-only, never final authority. The corpus of source pages is complete (0 missing
pages per the rescue audit); the remaining work is **head-on crops**, owner-provided.

## Blocks

- coverage-to-90: **no** (these are entry-data quality items, not hover blockers, except the small
  source-gated lanes that stay pending by design).
- public output: **no** (repair candidates carry `public_provenance_clean: true`, no leak).
