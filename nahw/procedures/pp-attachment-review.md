# PP Attachment Review

For a preposition phrase, record:

- the preposition;
- the governed noun or pronoun;
- the genitive relationship;
- the attachment head;
- whether the head is visible or implicit;
- whether attachment is to a verb, nominal, hidden hal, hidden sifa, or unknown.

The hover may stay compact, but the decision metadata must not pretend the
preposition belongs only to the host. A host-only hover is unsafe when the
preposition contributes meaning.

Use blocker labels:

- `pp_attachment_visible_verb`;
- `pp_attachment_visible_nominal`;
- `pp_attachment_hidden_hal`;
- `pp_attachment_hidden_sifa`;
- `pp_attachment_unknown`.

If the attachment head controls the English contribution and is unclear, route
to nahw/two-vote or scholar review.

## Dogfood finding: string-correct PP hovers are not attachment proof

The VN-00 tranche found rows such as `لِلَّهِ`, `لِلْمَلَٰٓئِكَةِ`,
`بِإِحْسَٰنٍ`, `بَيْنَكُم`, and `لِيَحْكُمَ` where the visible English may
include the preposition or purpose relation, but the graph still lacks a
certified attachment, governor, or exact entry/sense. Classify these as
`string_correct_but_not_rich` or `needs_nahw_review`, not `rich_certified`.

Component candidates from rich WBW segments may explain `لِـ`, `بِـ`, or a
host noun, but they do not become whole-token candidates and they never weaken
the gate to `auto_safe`.
