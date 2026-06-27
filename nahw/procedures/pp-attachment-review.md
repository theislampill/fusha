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

## Dogfood finding: VN-10 component relations stay gated

VN-10 repeated the PP/function boundary in rows such as:

- `بِغَيْظِكُمْ`: preposition + governed host + suffix + attachment required.
- `لِيَغِيظَ` / `لِيُضِيعَ`: lām function and mood/governor required before
  the verb-family host can be used.
- `لَزُلْفَىٰ` and `لَمَعْزُولُونَ`: raw initial lām is not automatically a
  purpose or genitive lām.
- `كِفْلٌۭ` / `كِفْلَيْنِ`: raw kāf-looking spelling does not prove a
  comparison/preposition; segment evidence is required.

Rule: PP or lām/kāf/bā evidence discovered as a component candidate is a route
to review, not a public hover. Keep these rows `component_only_blocker` or
`two_vote_exact_address_review` until attachment, function, and token POS
agree.

## Dogfood finding: VN-11 relation rows and false-prefix guards

VN-11 repeated PP/function gating in a different entry range:

- `لِفُرُوجِهِمْ`: lām relation + host + suffix + attachment required.
- `لَٱنفَضُّوا۟`: lām plus finite host needs function/mood review before the
  verb-family candidate can be used.
- `كَسَادَهَا`, `كَبَدٍ`, and `كَالِحُونَ`: initial kāf may be lexical or
  comparison-like; raw surface is not attachment proof.
- `لِوَاذًۭا`, `لَحْنِ`, and `لَنَاكِبُونَ`: lām-looking rows need exact
  segmentation and syntactic role before review.

Rule: the presence of a plausible English string does not certify attachment.
The dogfood lane may emit a repair candidate or renderer requirement, but live
apply still waits for exact-address proof, two compatible reasons when needed,
and no public provenance leakage.

## Dogfood finding: VN-12 attachment rows remain review lanes

VN-12 repeated the attachment boundary with fresh examples:

- `كَزَرْعٍ` needs comparison/preposition function, governed host, and
  attachment proof.
- `فَلْيُؤَدِّ` and `لِّيُوَاطِـُٔوا۟` need lām function and mood/governor
  review before a host verb candidate can be used.
- `وَفُرُشٍۢ`, `وَجَٰوَزْنَا`, and similar wāw/fā' rows may have useful host
  candidates, but the whole-token relation and clause attachment still need
  exact-address review.

Rule: component evidence is a route to the PP/function reviewer, not an
attachment decision. Keep the row non-applyable until function, host, case or
mood, and attachment agree.

## Dogfood finding: VN-13 attachment and conjunction rows need exact siblings

VN-13 adds rows where the visible English can be plausible while the syntax is
still not certified:

- `وَٱلشَّمْسُ` and `وَٱلْقَمَرُ` need wāw function, article/host
  segmentation, case/state, and rich display before they can teach a learner.
- `بِمُصْرِخِكُمْ` and `بِطَارِدِ` need bā' relation plus host and suffix or
  clause attachment; host/root evidence alone is not enough.
- `لَأَعْنَتَكُمْ` and lām-like rows require function/mood/referent review
  before a finite host candidate becomes a public hover.

Rule: attachment proof is a reasoned relation, not a text match. VN-13 keeps
these rows in blocker, two-vote, or repair-candidate queues until exact
function, host, and attachment agree.

## Dogfood finding: VN-15 PP/comparison rows require a head

VN-15 repeated the attachment boundary with rows such as `كَالصَّرِيمِ`,
`بِٱلْعُرْوَةِ`, `بِالْعَرَاءِ`, `بِٱلْعَرَآءِ`, and `بِقَبَسٍ`.

For these rows, a string-plausible relation is not enough. Record:

- the actual particle or comparison prefix;
- the governed host and case/state;
- whether the attachment head is a visible verb, visible nominal, hidden hāl,
  hidden ṣifa, or still unknown;
- whether the English relation depends on that attachment.

Rows with only host evidence or missing attachment head remain
`pp_attachment_uncertified` or `two_vote_exact_address_review`, not live
decisions.

## Dogfood finding: VN-16 attachment starts after segmentation

VN-16 found mostly detector boundary rows rather than certified PP rows:
`لِتَلْفِتَنَا` needs lām function and mood review, while `لِبَاسٌۭ` and
`بِضَاعَتَهُمْ` are lexical-host rows unless a separate particle is proved.

Attachment review therefore begins only after sarf/segmentation says there is
a real particle or comparison prefix. Once that is proved, record the governed
host, case/mood effect, attachment head, and whether English wording depends
on the attachment. Without those, the row stays a repair candidate or blocker,
not a live decision.
