# Live Batch 025 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lanes: all remaining public `two_vote` rows from the post-batch024 table
- Request packet: `bulk_twovote_requests_batch_025.jsonl`
- Vote packet: `bulk_twovote_votes_batch_025_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_025.jsonl`
- Public rows certified/applied: 152
- Unresolved rows kept pending: 226

## Certification

- Local certified batch SHA-256: `d94b9b68af45233d25430abd0ad5e8020f85eccf3fda13882ea6089d9635f3c5`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_025.jsonl`
- Result: PASS, 152 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no preposition-role omissions, no bracket/quote/dash leftovers, no lowercase standalone `i`/vocative `o`.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 8,719
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 8,871
- Rebuild diff: +152 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch025: 48,975 / 49,900 resolved = 98.15%
- After batch025: 49,127 / 49,900 resolved = 98.45%
- Remaining pending: 773

## Readback Samples

- `10:58:4` `وَبِرَحْمَتِهِۦ` -> `and in His Mercy`
- `12:31:3` `بِمَكْرِهِنَّ` -> `of their scheming`
- `19:4:12` `بِدُعَآئِكَ` -> `in my supplication to You`
- `24:11:24` `كِبْرَهُۥ` -> `took upon himself a greater share of it`
- `10:15:12` `بِقُرْءَانٍ` remained unresolved because source glosses omitted the bāʾ role.
- `12:37:3` `علمني` remained unresolved because the Arabic surface did not uniquely match the source word.

## Residual After Batch025

- `new_entry_proposal`: 274
- `scholar_review`: 196
- `form_variant`: 100
- `source_entry_repair`: 72
- `token_irab`: 51
- `verb_clitic`: 48
- `host_lexeme`: 27
- `source_photo`: 4
- `reject_unsafe`: 1

The remaining public two-vote rows (226 total) are not safe for the current exact-source fast path. They were held pending for one of: `preposition_role_omitted`, `source_surface_mismatch`, `source_translation_disagreement`, `source_translation_uncertain`, `ambiguous_source_surface_match`, or `missing_request_surface`.
