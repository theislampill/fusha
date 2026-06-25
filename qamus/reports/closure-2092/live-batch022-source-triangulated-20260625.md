# Live Batch 022 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lane: `form_variant`
- Request packet: `bulk_twovote_requests_batch_022.jsonl`
- Vote packet: `bulk_twovote_votes_batch_022_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_022.jsonl`
- Public rows certified/applied: 303
- Unresolved rows kept pending: 100

## Certification

- Local certified batch SHA-256: `8995474f58cb59ad2b21d8efd6b35142de62e04272d22edfa6bb7ee5dbb64070`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_022.jsonl`
- Result: PASS, 303 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no preposition-role omissions, no lowercase standalone `i`/vocative `o`, no leftover parenthetical source notation.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 7,746
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 8,049
- Rebuild diff: +303 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch022: 48,002 / 49,900 resolved = 96.20%
- After batch022: 48,305 / 49,900 resolved = 96.80%
- Remaining pending: 1,595

## Readback Samples

- `42:16:15` `غَضَبٌۭ` -> `wrath`
- `43:5:1` `أَفَنَضْرِبُ` -> `then should We take away`
- `46:20:12` `وَٱسْتَمْتَعْتُم` -> `and you took your pleasures`
- `10:15:12` `بِقُرْءَانٍ` remained unresolved because source glosses omitted the bāʾ role.
- `10:38:3` `بِسُورَةٍ` remained unresolved because source glosses omitted the bāʾ role.

## Residual After Batch022

- `verb_clitic`: 718
- `new_entry_proposal`: 274
- `scholar_review`: 196
- `host_lexeme`: 179
- `form_variant`: 100
- `source_entry_repair`: 72
- `token_irab`: 51
- `source_photo`: 4
- `reject_unsafe`: 1
