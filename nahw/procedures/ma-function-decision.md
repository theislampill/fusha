# Ma Function Decision

Do not assign one default hover to `ما`. Classify from context and i'rab.

Decision path:

1. Is it negative? If yes, does it act like laysa with subject/predicate?
2. Is it relative, meaning `what / that which`?
3. Is it interrogative?
4. Is it masdariyya/source-like, converting a clause into a verbal noun idea?
5. Is it conditional?
6. Is it preventive/kāffa after an inna-like particle, blocking that particle
   from governing the sentence?
7. Is it extra/intensifying in a construction where no compact hover should
   overclaim?

For written tokens such as `وما`, preserve both the prefix contribution and
the classified role of `ما`. If the role is not clear, keep the row pending
with `ma_function_uncertain`.

## Dogfood finding: VN-09 `لِمَا` and `لَّمَّا`

VN-09 found one entry family carrying several functions and surfaces:

- `لِمَا` / `لِمَآ`: lām plus `ما`; decide whether `ما` is relative,
  interrogative, source-like, conditional, or another function, and record the
  lām relation/attachment.
- `لَمَّا` / `لَّمَّا`: temporal, negative/not-yet, or exception-like
  construction by context. Do not merge it with `لِمَا`.
- `لَّمًّۭا` and `ٱللَّمَمَ`: lexical noun rows; exact surface and POS block
  particle/function propagation.

Decision guard:

1. Read the exact vowels/shadda/tanwīn before choosing the lane.
2. If the token begins with lām plus `ما`, record both the lām function and
   the `ما` function.
3. If the token is `لَّمَّا`, route to temporal/negative/exception review by
   context.
4. If lexical noun evidence is present, keep it in the nominal/POS lane.

Readable English such as "for what", "to that which", "when", "not yet", or
"there is no ... except" is not rich certification until the construction and
attachment are recorded.
