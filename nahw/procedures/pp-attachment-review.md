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

VN-08 repeated the same attachment boundary in two ways:

- `لِلَّهِ` can be string-correct as "belongs to Allah" or "to Allah", but it
  is not rich-certified until lām, the proper-name host, and the attachment or
  predicate relation are recorded.
- `بِالْخُنَّسِ` and `بِزَعْمِهِمْ` may arrive through host or component
  evidence, but a hover that teaches only "lurking" or "to claim" drops the
  preposition, governed noun, suffix (where present), and attachment head.

Component-only bā/lām evidence remains a blocker row until the whole written
token has an exact parse and an attachment decision.

## Dogfood finding: VN-09 lām-on-verb and comparison/PP rows

VN-09 added lām-on-verb and comparison rows that need nahw before hover trust:

- `لِتُضَيِّقُوا۟`, `لِّيَطْمَئِنَّ`, `لِيَفْتَدُوا۟`,
  `لِّتَسْلُكُوا۟`, and `لِتَشْقَىٰٓ` require lām function, governed mood, and
  clause relation review.
- `لَمُدْرَكُونَ` and `لَيُسْجَنَنَّ` are emphatic or oath/emphasis-like lām
  contexts, not purpose lām by default.
- `كَلَمْحِ` and `كَٱلْجَوَابِ` need comparison/preposition plus host and
  attachment proof.
- `بِعِصَمِ`, `بِٱلْبُخْلِ`, and `بِسَبَبٍ` need PP attachment; host-only
  glosses are not rich-certified.

If the lām or bā' contribution is clear enough for public wording, it must be
visible. If function or attachment is still unknown, use exact blockers such as
`lam_function_uncertified`, `mood_governor_uncertified`,
`pp_attachment_uncertified`, or `comparison_attachment_uncertified`.
