# Live Batch 020 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lane: `token_irab`
- Request packet: `bulk_twovote_requests_batch_020.jsonl`
- Vote packet: `bulk_twovote_votes_batch_020_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_020.jsonl`
- Public rows certified/applied: 213
- Unresolved rows kept pending: 50

## Certification

- Local certified batch SHA-256: `b15e3422135b749bb2a21bc17ac575eb1e0c1b53da3411ef2ccc8a64197930b1`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_020.jsonl`
- Result: PASS, 213 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no bare bāʾ-pronoun glosses, no leftover parenthetical source notation.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 7,094
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 7,307
- Rebuild diff: +213 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch020: 47,350 / 49,900 resolved = 94.89%
- After batch020: 47,563 / 49,900 resolved = 95.32%
- Remaining pending: 2,337

## Readback Samples

- `46:9:11` `بِى` -> `with me`
- `46:9:13` `بِكُمْ` -> `with you`
- `42:15:11` `بِمَآ` -> `in what`
- `40:12:8` `وَإِن` -> `but if`
- `12:100:27` `بِكُم` remained unresolved because both word sources omitted the bāʾ role.
- `21:47:19` `بِنَا` remained unresolved because both word sources omitted the bāʾ role.

## Residual After Batch020

- `token_irab`: 51
- `form_variant`: 842
- `verb_clitic`: 718
- `host_lexeme`: 179
- `new_entry_proposal`: 274
- `scholar_review`: 196
- `source_entry_repair`: 72
- `source_photo`: 4
- `reject_unsafe`: 1
