# RH-LIVE VN Source-Photo Locator Repair - 2026-06-29

## Trigger

The RH-LIVE NorthStar addendum requires the edge graph to drive rollout instead of page-by-page manual rediscovery. During VN-RH-LIVE-00 preflight, the graph-derived worklist showed many VN rows with only candidate source-photo edges. A small ANDON probe found a systemic locator issue: early verb entries were being routed toward `pg019.jpeg`, while the photographed verb section visibly begins at `pg002.jpeg`.

## Repair

Updated `tools/build_source_photo_entry_locator.py` so candidate source-photo pages are interpolated inside their photographed dictionary sections, not across one global page span:

| Section | Source keys | Photo span |
|---|---:|---:|
| Verbs | `v001`-`v947` | `pg002`-`pg223` |
| Nouns | `n0001`-`n1045` | `pg224`-`pg452` |
| Particles | `p001`-`p100` | `pg453`-`pg471` |

Regenerated `qamus/indexes/source_photo_entry_locator.json`.

## Verification Samples

The repair was anchored with a tiny manual ANDON sample, then codified in tooling:

| Sample | Corrected locator state |
|---|---|
| `v001` | candidate `pg002.jpeg` |
| `v002` | candidate `pg002.jpeg` |
| `v003` | candidate band `pg002`-`pg008`, covering the observed early verb page |
| `v004` | candidate `pg003.jpeg` |
| `n001` | candidate `pg224.jpeg` |
| `p001` | candidate `pg453.jpeg` |
| `p100` | candidate `pg471.jpeg` |

The prior `pg019` early-verb route is now regression-protected.

## Regression Coverage

`tools/check_regressions.py` now checks:

- `section_page_candidate("v001") == 2`
- `section_page_candidate("n001") == 224`
- `section_page_candidate("p001") == 453`
- `section_page_candidate("p100") == 471`
- the committed locator artifact keeps `v001`, `n001`, and `p001` in their correct source sections.

## Rollout Impact

This does not certify any VN row by itself. It repairs the graph routing layer so VN source-photo review starts from the right section.

For VN rollout, the next deterministic action is:

1. Rebuild the live graph worklist using the corrected locator.
2. Reclassify source-photo candidate rows from the corrected section candidates.
3. Promote only rows with complete entry/card/word, source-photo, Qur'an/WBW, grammar, payload, and readback edges.
4. Keep rows with source-photo or canonical alignment uncertainty blocked with exact blocker classes.

## Boundaries

- Live Qamus mutation: no.
- Whitelist append: no.
- WBW rebuild: no.
- Service restart: no.
- Source/provenance leak: no.
- Public coverage claim: no.

This is a Fusha graph-spine repair and regression backfill for RH-LIVE VN preparation.
