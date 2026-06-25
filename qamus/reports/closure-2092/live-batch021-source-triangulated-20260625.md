# Live Batch 021 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lane: `form_variant`
- Request packet: `bulk_twovote_requests_batch_021.jsonl`
- Vote packet: `bulk_twovote_votes_batch_021_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_021.jsonl`
- Public rows certified/applied: 439
- Unresolved rows kept pending: 61

## Certification

- Local certified batch SHA-256: `021c64c82bf30dbc30004cbe2bea760ff50ce3b3d038eba6a4ba5968a81b3671`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_021.jsonl`
- Result: PASS, 439 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no bare bāʾ-role omissions, no lowercase standalone `i`/vocative `o`, no leftover parenthetical source notation.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 7,307
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 7,746
- Rebuild diff: +439 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch021: 47,563 / 49,900 resolved = 95.32%
- After batch021: 48,002 / 49,900 resolved = 96.20%
- Remaining pending: 1,898

## Readback Samples

- `108:2:1` `فَصَلِّ` -> `so pray`
- `11:34:5` `أَرَدتُّ` -> `I wish`
- `11:62:2` `يَٰصَٰلِحُ` -> `O Salih`
- `17:106:1` `وَقُرْءَانًۭا` -> `and the Quran`
- `10:15:12` `بِقُرْءَانٍ` remained unresolved because source glosses omitted the bāʾ role.
- `10:38:3` `بِسُورَةٍ` remained unresolved because source glosses omitted the bāʾ role.

## Residual After Batch021

- `verb_clitic`: 718
- `form_variant`: 403
- `new_entry_proposal`: 274
- `scholar_review`: 196
- `host_lexeme`: 179
- `source_entry_repair`: 72
- `token_irab`: 51
- `source_photo`: 4
- `reject_unsafe`: 1
