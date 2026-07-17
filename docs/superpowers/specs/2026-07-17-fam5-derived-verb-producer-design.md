# FAM5 derived-verb producer design

## Scope

FAM5 owns the bounded `derived_verbs` calibration population only. It reuses
the FAM4 finite-verb carrier, its entry-form join, shared verb-affix registry,
weak-root defeater registry, F-A typed-claim contract, evidence modes, and
candidate-only projector boundary. It does not project the corpus from a
surface template, and it does not mutate scripture, whitelist data, Qamus
entries, or a live runtime.

The working set is exactly seven rows: the three `derived_verbs` rows from
`strat-455.jsonl` plus the four FAM4 owner-gated rows at 4:72:4, 5:3:41,
12:51:21, and 14:26:6.

## Survey-first evidence boundary

| location | surface | written base-letter survey | template hypothesis | evidence situation | planned route |
| --- | --- | --- | --- | --- | --- |
| 3:141:4 | آمَنُوا | آ م ن و ا | Form IV perfect active 3MP; hamza/madda onset + plural subject suffix | v575 verified; occurrence-proxy fact addresses only; no exact entry-form match | source_gap |
| 42:20:3 | يُرِيدُ | ي ر ي د | Form IV imperfect active 3MS; weak middle radical ر و د is not letter-stable | v575 verified; occurrence-proxy fact addresses only; no exact entry-form match | source_gap |
| 42:20:12 | يُرِيدُ | ي ر ي د | same Form IV imperfect hypothesis as 42:20:3 | v575 verified; occurrence-proxy fact addresses only; no exact entry-form match | source_gap |
| 4:72:4 | لَّيُبَطِّئَنَّ | ل ي ب ط ئ ن ن | Form II imperfect active + oath/energic boundary; doubled stem letter and energic nūn | FAM4 packet owner-gated; whitelist context only; no direct entry-form attestation | owner_gated |
| 5:3:41 | أَكْمَلْتُ | أ ك م ل ت | Form IV perfect active 1CS; derivative hamza prefix + subject suffix | exact entry form `entry:efa9daeebae2:usage[0].forms[0]` and v575-verified FAM4 context | candidate |
| 12:51:21 | حَصْحَصَ | ح ص ح ص | quadriliteral Form-I perfect active 3MS; four root radicals | exact entry form `entry:08c89bbcbaad:usage[0].forms[0]` and v575-verified FAM4 context | candidate |
| 14:26:6 | ٱجْتُثَّتْ | ٱ ج ت ث ت | Form VIII passive perfect 3FS; hamzat al-waṣl, derivative infix ت, shared-letter gemination, feminine suffix | exact entry form `entry:e2b37f88f22f:usage[0].forms[0]` and v575-verified FAM4 context | candidate |

The source survey is part of the committed packet and is not a sampling
claim. Root hints from the STRAT rows remain non-certifying metadata until an
exact source-backed form is available.

## Contract and data flow

1. Merge caller-supplied STRAT rows with the four named FAM4 packet rows.
2. Join each row to caller-supplied entry fields using exact written surface
   or Quran-annotation-only equality. A whitelist ID, label, gloss, morphline,
   or surface template never creates a form fact.
3. Classify the written base letters with one owner class each. Derivational
   markers have their own role: Form-IV أ is `derivative_prefix`, Form-V/VI
   ت would be `derivative_prefix`, and Form-VIII ت is `derivative_infix`.
   Hamzat al-waṣl is its own governed role. A shadda is retained on one
   written base letter; Treatment-C metadata records the shared-letter and
   idghām A–D classification without creating a second span.
4. Emit a derived-form fact only when an attested registry pattern, exact
   entry-form evidence, v575 verification, letter-level ownership, and exact
   reconstruction all pass. Preserve root, template, derivational additions,
   inflectional additions, weak-letter operations, assimilation/gemination,
   hamzat al-waṣl, voice, person/number/gender, and mood status in the typed
   fact.
5. Otherwise emit exactly one typed unresolved fact with a precise route:
   `template_unresolved`, `owner_gated`, `weak_root_pattern_unresolved`, or
   `source_gap`. All projections remain `pre_apply_not_authorized`.

The public learner payload exposes the exact labels `Ṣarf — how this piece
forms the word` and `Naḥw — what this piece does here`. Naḥw does not certify
case or mood inside the sarf fact; the payload names the separate overlay.

## Fixtures and verification

The FAM5 fixture matrix contains at least six entry-backed positive cases for
the four attested form classes, including Form-IV active/passive, Form-II
gemination and energic-nūn boundary, quadriliteral, and Form-VIII
hamzat-al-waṣl/passive/gemination. It contains at least eight adversarial
cases covering surface-template-only input, naive Form-VIII splitting,
passive/active diacritics, missing energic boundary, forced triliteral
quadriliteral parsing, ungrounded hamzat al-waṣl, weak-root uncertainty, and
ambiguous entry joins. Tests first demonstrate the expected abstentions, then
the minimal producer makes them pass.

The committed packet includes all seven rows, typed candidates, unresolved
records, per-row survey/evidence table, and precision plus abstention counts by
form class. The report explicitly states the zero-false-projection basis and
the exact nonclaims.

## Out of scope

No corpus-wide template rule, assimilation rule, gemination rule, whitelist
append, public projection, gloss authoring, source invention, restart,
publication, commit push, or live mutation is part of FAM5. Future registry
and skill changes are recorded as candidate increments only.
