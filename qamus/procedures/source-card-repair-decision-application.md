# Source-Card Repair Decision Application

Use this procedure when a source-card/example repair worklist row needs a terminal decision.

## Decision statuses

- `accepted_exact`
- `accepted_with_display_edit`
- `accepted_with_crosswalk`
- `rejected_wrong_source`
- `rejected_ambiguous_surface`
- `needs_owner`
- `needs_scholar_irab`
- `needs_source_photo_review`
- `superseded`

## Required fields

Every decision record must conform to
`qamus/schemas/source-card-example-repair-decision.schema.json` and include `decision_status`,
`downstream_invalidates`, and `public_boundary`.

## Workflow

1. Load the repair row and source-card evidence.
2. Compare displayed fragment, selected qword, and candidate canonical source address.
3. Decide one exact status.
4. If accepted, list downstream artifacts to invalidate: qword denominator, qword crosswalk, hover candidates,
   Plan 15 flywheel, curriculum samples, and executor worklists as applicable.
5. Regenerate downstream artifacts from source-of-truth builders.
6. Run the qword/crosswalk/transclusion validators.

Accepted source-card repairs can unblock hovers; rejected repairs should become validator fixtures so the same
bad row is not proposed again.
