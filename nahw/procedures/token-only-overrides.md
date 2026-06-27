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

## VN-18 examples

- `أَحَدُهُمْ`, `أَحَدِهِم`, `أَحَدِهِمَا`, and `أَحَدَكُم`
  share the one/anyone family, but suffix, case, and referent make the hover
  exact-addressed.
- `وَٰحِدٍۢ`, `وَٰحِدًا`, `وَٰحِدَةًۭ`, and `ٱلْوَٰحِدُ`
  require gender, case, definiteness, and sentence role before one family
  wording can propagate.
- `ثَانِىَ`, `كُلًّۭا`, `أُو۟لِى`, and `كُرْهٌۭ` show why a token-only
  review may be needed even when the entry family is obvious: exact POS and
  i'rab decide what the learner should see.
- `بِٱلْمَعْرُوفِ` and the 22:18 wāw + article + host cluster remain
  component-only or two-vote rows until the whole written token is parsed.

## VN-19 examples

- `قِطَّنَا`, `يَوْمُكُمُ`, `يَوْمِكُمْ`, `يَوْمِهِمْ`, and
  `يَوْمَهُمُ` share common nominal families, but suffix, case, and referent
  make each hover exact-addressed.
- `ٱلْيَوْمَ`, `يَوْمٍ`, `ٱلْأَيَّامُ`, and related day-family rows cannot
  receive one family-wide wording until definiteness, case, number, and
  sentence role are known.
- `سَنَةٍۢ`, `سَنَةٍ`, and `سَنَةًۭ` may be string-populated as "year", but
  their case and i'rab context still decide whether they can become
  learner-ready.
- `أَطْرَافِهَا`, `طَرْفُهُمْ`, and `وَأَطْرَافَ` require exact token
  accounting for host number/case plus suffix or wāw contribution.
- `ٱلسَّبْتِ` must stay exact-addressed when the visible hover leaks
  verb-infinitive prose into a noun token.

## VN-20 examples

- `سَيْنَآءَ` and `سِينِينَ` share a place-name family but still need exact
  address, case, and context before family wording can propagate.
- `طُوًۭى` and `أَقْطَارِ` require exact valley/place or side/region context
  and i'rab role.
- `بِبَدْرٍ` and `بِبَكَّةَ` require the bā' relation plus named-place host
  and PP attachment; a place name alone drops visible grammar.
- `مَكَّةَ` and `ٱلْكَعْبَةِ` need exact location, case, and contextual role.
- `وَأَقْنَىٰ`, `وَأَكْدَىٰٓ`, `فَٱلْتَقَمَهُ`, and `فَأَلْهَمَهَا`
  require function piece plus finite host and suffix where present before any
  sibling propagation.

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
