# Live Batch 024 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lane: `verb_clitic`
- Request packet: `bulk_twovote_requests_batch_024.jsonl`
- Vote packet: `bulk_twovote_votes_batch_024_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_024.jsonl`
- Public rows certified/applied: 209
- Unresolved rows kept pending: 48

## Certification

- Local certified batch SHA-256: `609c3f32a42f11f50acf96be648410474cb4cc15ab070916f2bd62ce31915a01`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_024.jsonl`
- Result: PASS, 209 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no bracket/quote/dash leftovers, no lowercase standalone `i`/vocative `o`.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 8,510
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 8,719
- Rebuild diff: +209 added, -0 removed, ~0 changed
- Service health after restart: 200

## Coverage

- Before batch024: 48,766 / 49,900 resolved = 97.73%
- After batch024: 48,975 / 49,900 resolved = 98.15%
- Remaining pending: 925

## Readback Samples

- `59:3:7` `لَعَذَّبَهُمْ` -> `certainly He would have punished them`
- `5:110:13` `أَيَّدتُّكَ` -> `I strengthened you`
- `5:41:39` `تُؤْتَوْهُ` -> `you are given it`
- `60:8:11` `يُخْرِجُوكُم` -> `drive you out`
- `12:37:3` `علمني` remained unresolved because the Arabic surface did not uniquely match the source word.

## Residual After Batch024

- `new_entry_proposal`: 274
- `scholar_review`: 196
- `host_lexeme`: 179
- `form_variant`: 100
- `source_entry_repair`: 72
- `token_irab`: 51
- `verb_clitic`: 48
- `source_photo`: 4
- `reject_unsafe`: 1
