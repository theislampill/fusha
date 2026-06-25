# Live Batch 023 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lane: `verb_clitic`
- Request packet: `bulk_twovote_requests_batch_023.jsonl`
- Vote packet: `bulk_twovote_votes_batch_023_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_023.jsonl`
- Public rows certified/applied: 461
- Unresolved rows kept pending: 39

## Certification

- Local certified batch SHA-256: `48ea8123b2a79d04d4d2936bcbe5ec438f62b089d0d4880eb14982c57bd81a84`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_023.jsonl`
- Result: PASS, 461 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no bracket/quote/dash leftovers, no lowercase standalone `i`/vocative `o`.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 8,049
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 8,510
- Rebuild diff: +461 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch023: 48,305 / 49,900 resolved = 96.80%
- After batch023: 48,766 / 49,900 resolved = 97.73%
- Remaining pending: 1,134

## Readback Samples

- `10:107:11` `يُرِدْكَ` -> `he intends for you`
- `11:88:20` `أَنْهَىٰكُمْ` -> `I forbid you`
- `12:31:19` `أَكْبَرْنَهُۥ` -> `they greatly admired him`
- `14:22:12` `فَأَخْلَفْتُكُمْ` -> `but I betrayed you`
- `12:37:3` `علمني` remained unresolved because the Arabic surface did not uniquely match the source word.

## Residual After Batch023

- `new_entry_proposal`: 274
- `verb_clitic`: 257
- `scholar_review`: 196
- `host_lexeme`: 179
- `form_variant`: 100
- `source_entry_repair`: 72
- `token_irab`: 51
- `source_photo`: 4
- `reject_unsafe`: 1
