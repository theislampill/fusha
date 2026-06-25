# Bulk two-vote request batch 018

Request packet only. No votes have been cast, no decisions are approved, and no live apply occurred.

| metric | value |
|---|---:|
| selected request rows | 40 |
| eligible low/medium two-vote rows | 728 |
| chunk size | 40 |
| chunks | 1 |

## Review Contract

- Required lenses: `sarf-primary`, `nahw-primary`.
- Required vote fields: `decision`, `concise_authored_gloss`, `sarf_reasoning`, `nahw_reasoning`, `reason_agreement_key`, `blocker_if_rejected`.
- Reconcile only when both votes agree on `decision`, `concise_authored_gloss`, and `reason_agreement_key`.
- Validator: `python3 tools/validate_bulk_two_vote_requests.py qamus\candidates\qamus_2092\bulk_twovote_requests_batch_018.jsonl --table qamus\reports\closure-2092\pending-source-triangulation-table.jsonl --manifest qamus\reports\closure-2092\bulk-two-vote-requests-batch-018.json`.
- Reconciler: `python3 tools/reconcile_bulk_two_vote_results.py --requests qamus\candidates\qamus_2092\bulk_twovote_requests_batch_018.jsonl --votes <votes.jsonl>`.

## By Lane

- `verb_clitic`: **40**
