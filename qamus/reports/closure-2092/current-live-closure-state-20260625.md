# Current Live Closure State

Date: 2026-06-25

## Live-Synced Artifact Identity

- `out/hover_stage/wbw-lookup.json`
  - SHA-256: `b2863636845795a2c96609eacfc96826857ff6832c277c91343548123acb1eb7`
  - bytes: 9,168,979
- `out/hover_stage/fusha-hover-token-decisions.jsonl`
  - SHA-256: `b503f563eca1d1ac2b85a8a337d6a296c08d832cadd140f9616eb78b57b671f3`
  - bytes: 2,530,949

## Coverage

- Total word locs: 49,900
- Resolved: 49,255
- Pending: 645
- Coverage: 98.71%

## Residual By Gate

- `two_vote`: 99
- `owner`: 274
- `scholar`: 197
- `source`: 75

## Residual By Lane

- `new_entry_proposal`: 274
- `scholar_review`: 196
- `source_entry_repair`: 71
- `form_variant`: 34
- `token_irab`: 35
- `host_lexeme`: 16
- `verb_clitic`: 14
- `source_photo`: 4
- `reject_unsafe`: 1

## Next Safe Work

The easy exact-source triangulation path has been drained. The remaining 99 public two-vote rows were rejected by
one of these current fast-path blockers:

- `preposition_role_omitted`
- `source_surface_mismatch`
- `ambiguous_source_surface_match`
- `missing_request_surface`

The next closure loop should not re-run broad source agreement. It should split into:

- preposition-role authoring with naḥw/iʿrāb evidence;
- source-entry repair for bad/missing examples or forms;
- owner-approved new-entry proposals;
- scholar/iʿrāb review for genuine same-surface ambiguity;
- source-photo review for the 4 photo-gated rows.

## Verified Gates

- `python tools\audit_all_hover_tokens.py`
- `python tools\build_blocker_root_cause_ledger.py`
- `python tools\build_pending_source_triangulation_table.py`
- `python tools\validate_pending_source_triangulation_table.py`
- `python tools\validate_qamus_completion_manifest.py`

All passed against the live-synced local staging artifact above.
