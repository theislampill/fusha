# Token-only override review

Use this when the current hover is attached to the right entry family but the
exact Qur'anic token still cannot safely inherit a surface-wide or parse-family
gloss.

## Input

- exact `quran:S:A:W` and `wbw:S:A:W`
- raw surface and current hover
- linked entry/sense candidate, if any
- parse family, collision class, and dogfood detector output
- sarf output for host, clitics, suffixes, and POS
- nahw output for role, attachment, case/mood, referent, and function

## Checks

1. **Identity:** the token address is primary. Do not edit by Arabic surface,
   entry text, or parse key alone.
2. **Family safety:** if siblings differ by case, referent, suffix, function,
   article, i'rab role, PP attachment, or context, keep the row token-only.
3. **Visible contribution:** a token-only repair must preserve every visible
   grammar piece: proclitic, article, host, suffix, function, and role.
4. **Gate:** if the reason involves i'rab, particle function, PP attachment,
   vocative/exception, negation, relative/interrogative/conditional function,
   suffix referent, or homograph risk, require two compatible reasons.
5. **Publication:** the future public hover remains qamus-authored only. Internal
   evidence may explain the decision but cannot appear in the public payload.

## VN-17 examples

- `ٱلْأَنفَالِ` and `ٱلْأَنفَالُ` share a surface family but differ by exact
  case/context. Keep entry reuse token-addressed until the i'rab role is known.
- `أَصْلُهَا` and `أُصُولِهَا` require host number plus `هَا` referent; a
  bare "root/origin" hover is not learner-complete.
- `بَرْزَخًۭا` and `بَرْزَخٌ` need exact case/context before a phrase or
  entry-family gloss can propagate.
- `قَوَارِيرَ` and `قَوَارِيرَا۠` require exact orthography/case handling; do
  not collapse them into one raw-surface decision.
- `أَوْتَادًا` and `ٱلْأَوْتَادِ` need definiteness and case/context review
  before a family-wide hover is safe.

## Output

Emit a token-only row with:

- exact `quran:S:A:W` and `wbw:S:A:W`
- current hover and proposed authored hover or precise pending reason
- entry/sense link or no-entry rationale
- `requested_scope: token_only`
- required gate and reason-agreement key if two-vote is required
- rollback target for any future append-only decision

## Forbidden

- No surface-wide edit from this lane.
- No parse-key-family edit unless a separate impact preview proves every sibling.
- No live apply from a dogfood tranche.
- No "right answer, wrong reasoning" approval.

## Feeds

Hover repair previews, blocker queues, production-bug lessons, and learner
drills. This procedure is a gate, not an apply path.
