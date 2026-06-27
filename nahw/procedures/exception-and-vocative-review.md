# Exception And Vocative Review

Exceptions:

- identify the particle, usually `إلا`;
- record the main noun (`mustathna minhu`) when present;
- record the excepted noun (`mustathna`);
- classify polarity: positive, negative, prohibition, or interrogation;
- classify type: connected, disconnected, or empty/main noun omitted;
- decide whether case follows accusative exception rules or apposition.

Dogfood note: `إِلَّا` rows with a readable "except" hover are still not
rich-certified unless the exception frame is recorded. The controller row must
name the polarity, whether the main noun is mentioned or omitted, the exception
type (connected, disconnected, or mufarragh), and the case policy. If any of
those are unknown, classify the row as `needs_nahw_review` with
`exception_structure_uncertified`, not `rich_certified`.

VN-08 dogfood note: do not route by a stripped `إلا`-looking surface alone.
`إِلَّا` / `إِلَّآ` need the exception frame above, but `إِلًّۭا` at
`9:8:8` and `9:10:5` is a lexical noun ("bond/tie"), not the exception
particle. The exact shadda/tanwīn and token address must block exception
propagation. Treat an English "except" string as populated text only until the
exception frame is proven; treat lexical `إِلًّا` as a noun/POS row.

Vocatives:

- identify the vocative particle;
- record the addressee and whether it is definite, indefinite, or an idafa head;
- identify whether `أَيُّهَا` / `أَيَّتُهَا` is a Qur'anic vocative bridge,
  not a standalone relative/demonstrative gloss;
- preserve attached pronouns and possessed forms;
- preserve the difference between the call particle, bridge/support word,
  attention particle, and following addressee;
- do not collapse `يا قومنا` to only `our people`.

Dogfood note: `يَٰٓأَيُّهَا` is not a one-piece "you (who)" hover. Treat it as a
vocative formula whose pieces must remain explainable:

- `يَا` supplies the call, usually "O";
- `أَيُّ` is the vocative bridge/support word;
- `هَا` is an attention particle attached to the formula;
- the following nominal supplies the addressee.

If the entry linkage or no-entry function-token rationale is missing, route to
entry-linkage review plus nahw review. Do not repair by raw surface text, and do
not propagate the formula without exact token addresses and a two-vote gate.

Dogfood note: a readable phrase can still be uncertified. `يَٰٓـَٔادَمُ`,
`يَٰقَوْمِ`, `يَٰمُوسَىٰ`, and `يَٰبَنِىٓ` may read fluently as "O Adam",
"O my people", "O Moses", or "O children...", but the rich hover still needs a
breakdown of call particle plus addressee and, where present, possession or
iḍāfa. A host-only addressee gloss is not learner-ready.

False-positive guard: nahw should not accept a vocative route from raw surface
shape alone. If sarf identifies the initial yā as part of a lexical host
(`يَابِسٍ`, `يَابِسَٰتٍ`), classify the vocative detector as a false positive
and do not create a vocative parse key.

When case behavior or scope affects the hover, route to nahw/two-vote or
scholar review.
