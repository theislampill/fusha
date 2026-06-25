# Live Batch 026 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lanes: residual public `two_vote` rows after batch025
- Request packet: `bulk_twovote_requests_batch_026.jsonl`
- Vote packet: `bulk_twovote_votes_batch_026_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_026.jsonl`
- Public rows certified/applied: 118
- Unresolved rows kept pending: 108

## Tool Fix

Batch026 used the updated source normalizer that strips boundary quote/dash/terminal punctuation before comparing
source translations and before authoring public glosses. This converted punctuation-only source mismatches into
certified rows while still rejecting true source disagreement, source-surface mismatch, duplicate Arabic surfaces,
and preposition-role omissions.

## Certification

- Local certified batch SHA-256: `668a12807e0ed1a4c5b00c7e82a4b24a68ccba2618ef5247c6eb1c3303033e76`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_026.jsonl`
- Result: PASS, 118 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no preposition-role omissions, no bracket/quote/dash/period leftovers, no lowercase standalone `i`/vocative `o`.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 8,871
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 8,989
- Rebuild diff: +118 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch026: 49,127 / 49,900 resolved = 98.45%
- After batch026: 49,245 / 49,900 resolved = 98.69%
- Remaining pending: 655

## Readback Samples

- `11:54:7` `بِسُوءٍ` -> `with evil`
- `19:12:1` `يَٰيَحْيَىٰ` -> `O Yahya`
- `20:94:2` `يَبْنَؤُمَّ` -> `O son of my mother`
- `2:67:12` `أَتَتَّخِذُنَا` -> `do you take us`
- `10:15:12` `بِقُرْءَانٍ` remained unresolved because source glosses omitted the bāʾ role.
- `15:87:3` `الْمَثَانِي` remained unresolved because the Arabic surface did not uniquely match the source word.

## Residual After Batch026

- `new_entry_proposal`: 274
- `scholar_review`: 196
- `source_entry_repair`: 71
- `form_variant`: 42
- `token_irab`: 35
- `host_lexeme`: 18
- `verb_clitic`: 14
- `source_photo`: 4
- `reject_unsafe`: 1

The remaining public two-vote rows are 109 total and are no longer safe for the exact-source fast path without
additional authoring, source-entry repair, or iʿrāb/scholar gating.
