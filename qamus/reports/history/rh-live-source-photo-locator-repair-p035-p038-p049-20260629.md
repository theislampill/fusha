# RH-LIVE Source-Photo Locator Repair: P-RH-LIVE-02 residual source cards

Date: 2026-06-29

## Scope

This is a repo-only Qamus graph/source-photo locator repair prompted by RH-LIVE P-RH-LIVE-02 source-card ANDON work. It does not mutate live Qamus, does not append rich-hover payloads, does not rebuild WBW, and does not claim row certification.

## Finding

The current source-photo locator carried broad candidate pages for several particle entries. Visual inspection of the owner-provided photographed book pages showed that the candidate pages were wrong or too loose for several entries:

- `p035` `فِي`: verified on `pg460.jpeg`, not `pg457.jpeg`
- `p036` `عَلَى`: verified on `pg460.jpeg`, not `pg457.jpeg`
- `p037` `إِلَى`: verified on `pg460.jpeg`, not `pg457.jpeg`
- `p038` `عَنْ`: verified on `pg460.jpeg`, not `pg458.jpeg`
- `p049` `مَتَى`: verified on `pg462.jpeg`, not `pg460.jpeg`
- `p060` `لَوْ`: verified on `pg464.jpeg`, not `pg462.jpeg`
- `p064` `هَذَا`: verified on `pg465.jpeg`, not `pg463.jpeg`
- `p065` `هَذِهِ`: verified on `pg465.jpeg`, not `pg463.jpeg`
- `p066` `هَذَانِ`: verified on `pg465.jpeg`, not `pg464.jpeg`
- `p068` `هَؤُلَاءِ`: verified on `pg465.jpeg`, not `pg464.jpeg`
- `p070` `أُولَئِكَ`: verified on `pg466.jpeg`, not `pg465.jpeg`

`p034` was already repaired as a verified `pg459.jpeg` entry with examples continuing on `pg460.jpeg`; this patch follows that existing locator shape.

`p098` was already a verified locator row in the graph and needed no source-photo locator change in this pass.

## Change

Updated `qamus/indexes/source_photo_entry_locator.json` for the eleven newly verified entries:

- set `confidence` to `photo_verified`
- set exact `page`, `page_image`, `verified_page`, and `verified_page_image`
- tightened `candidate_page_band` to the verified page
- added `verified_value` and `visual_note`

## Rollout Implication

The affected P-RH-LIVE-02 source-card rows remain blocked until the source-card Arabic, canonical Qur'an/WBW span, and rich-hover payload gates are separately reconciled. This repair only fixes the source-photo locator edge, which is required before deterministic fragment overrides or rich-hover deployment.

In particular, this locator repair does not certify any rich-hover row by itself. Rows with canonical Qur'an/WBW span mismatch, display-local fragment mismatch, or unresolved selected target words must stay blocked until the graph crosswalk and hover payload gates pass.

## Public Boundary

This report and locator metadata are internal graph/source artifacts. Public rich-hover payloads must remain Qamus-authored and source-clean; they must not expose photo paths, graph paths, MCP/source labels, or internal provenance.
