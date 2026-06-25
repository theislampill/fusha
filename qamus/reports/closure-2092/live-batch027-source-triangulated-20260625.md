# Live Batch 027 Source-Triangulated Hover Apply

Date: 2026-06-25

## Scope

- Lanes: residual public `two_vote` rows after batch026
- Request packet: `bulk_twovote_requests_batch_027.jsonl`
- Vote packet: `bulk_twovote_votes_batch_027_source.jsonl`
- Certified batch: `bulk_twovote_certified_batch_027.jsonl`
- Public rows certified/applied: 10
- Unresolved rows kept pending: 99

## Tool Fix

Batch027 used the updated preposition-role preservation list that treats comparative `kaf` roles expressed as
`as` or `like` as preserved. This recovered a narrow set of comparative `kaf` rows while still rejecting rows
where the source gloss omitted an attached preposition role, where Arabic source surfaces did not match, where
the source surface was ambiguous, or where the request had no usable surface.

## Certification

- Local certified batch SHA-256: `f9f46fe501b1611cd0367549b548d77d034e074f881c410b3add40fdba44811d`
- Validator: `python tools\validate_token_hover_decisions.py qamus\candidates\qamus_2092\bulk_twovote_certified_batch_027.jsonl`
- Result: PASS, 10 token decisions, public invariant clean.
- Spot scan: no public source-name leaks, no comparative `kaf` role omissions, and no boundary punctuation leftovers.

## Live Gate

- Upload SHA matched local SHA.
- Existing live decisions before append: 8,989
- Batch overlap with existing live decisions: 0
- Existing live decisions after append: 8,999
- Public route checks after rebuild: 200
- Targeted readback matched the 10 applied rows.

## Coverage

- Before batch027: 49,245 / 49,900 resolved = 98.69%
- After batch027: 49,255 / 49,900 resolved = 98.71%
- Remaining pending: 645

## Readback Samples

- `10:24:5` `كَمَآءٍ` -> `like the water`
- `10:27:6` -> `like it`
- `13:16:34` -> `like His creation`
- `24:35:7` `كَمِشْكَوٰةٍۢ` -> `like a niche`
- `2:165:10` `كَحُبِّ` -> `as they should love`
- `2:200:3` `كَذِكْرِكُمْ` -> `as you remember`
- `38:28:7` `كَٱلْمُفْسِدِينَ` -> `like those who spread corruption`
- `55:37:6` -> `like murky oil`
- `56:23:1` `كَأَمْثَٰلِ` -> `like`
- `77:32:4` -> `as the fortress`
- `10:15:12` `بِقُرْءَانٍ` remained unresolved because source glosses omitted the bāʾ role.
- `15:87:3` `الْمَثَانِي` remained unresolved because the Arabic surface did not uniquely match the source word.

## Residual After Batch027

- `new_entry_proposal`: 274
- `scholar_review`: 196
- `source_entry_repair`: 71
- `form_variant`: 34
- `token_irab`: 35
- `host_lexeme`: 16
- `verb_clitic`: 14
- `source_photo`: 4
- `reject_unsafe`: 1

The exact-source fast path is now drained for the current tooling. Remaining `two_vote` rows require authored
preposition-role review, source-entry repair, or iʿrāb/scholar routing rather than another broad source-agreement
retry.
