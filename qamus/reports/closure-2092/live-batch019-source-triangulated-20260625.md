# Live Batch 019 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lane: `token_irab`
- Request packet: `bulk_twovote_requests_batch_019.jsonl`
- Vote packet: `bulk_twovote_votes_batch_019_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_019.jsonl`
- Public rows certified/applied: 216
- Unresolved rows kept pending: 34

## Certification

- Local certified batch SHA-256: `3631f5727d67caf1cd8e57a67817efd91a5de40c35405bb0a1a98a6d72d76b4f`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_019.jsonl`
- Result: PASS, 216 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no bare bāʾ-pronoun glosses, no leftover parenthetical source notation.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 6,878
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 7,094
- Rebuild diff: +216 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch019: 47,134 / 49,900 resolved = 94.46%
- After batch019: 47,350 / 49,900 resolved = 94.89%
- Remaining pending: 2,550

## Readback Samples

- `16:49:6` `وَمَا` -> `and whatever`
- `14:5:2` `بِأَيَّامِ` -> `of the days`
- `17:110:10` `فَلَهُ` -> `to Him belongs`
- `10:1:5` `الٓر` -> `Alif Lam Ra`
- `12:100:27` `بِكُم` remained unresolved because both word sources omitted the bāʾ role (`preposition_role_omitted`).

## Method Lesson

Batch019 found two important hardening rules now copied into the installed sarf/nahw skills:

- Do not bind external word evidence by token loc alone; Qamus locs can be example-snippet-relative or basmala-offset. Bind by a unique Arabic surface match inside the ayah before comparing translations.
- Source agreement is not enough when morphology shows an attached preposition but English drops that role. Keep the row pending until the jar-majrūr function is authored.
