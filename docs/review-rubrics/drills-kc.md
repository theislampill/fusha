# Drills/KC authoring and review rubric

Read before authoring and during the single assembled-slice review.

- Quarantine every assessment/benchmark probe and every discovered runtime or authoring input; unlisted inputs fail closed.
- Author original prompts, answers, variants and explanations; never copy source prose or expose answer keys across the quarantine boundary.
- Bind every runtime row to an exact KC, misconception, remediation route, lesson contribution and stable runtime ID.
- Require correct conclusion and correct reason; reject a right label with a wrong governor, case/mood reason or derivation.
- Enforce the catalog gate: non-auto-safe and grammar-sensitive rows remain `two_vote_required` and cannot self-clear.
- Keep candidate specifications candidate; runtime practice mastery does not certify a linguistic fact or close a lesson/unit.
- Pin scoring paths and runtime artifacts; compute every reported metric rather than leaving asserted placeholders.
- Exercise ordinary tutor selection, grading, progress isolation and remediation—not a curriculum-local mock.
- Preserve `quran_example: null` or an explicit evidence-blocked posture when exact occurrence evidence is absent.
- Ensure bindings and generated accounting ship in the same slice as the consumer behavior.

Record findings by stable class so recurrence can be measured across tranches.

## T1b review-repair stable classes (F1-F11)

- **geminate-jussive-licensed-form-forbidden**: never author a row whose forbidden_answers reject a form another
  row of the same paradigm names as licensed; a geminate/weak-root inventory needs the FULL licensed set checked
  against sibling rows before any form is forbidden.
- **diacritic-blind-grading-collision**: a row whose answer correctness depends on a vowel, shadda, or case/mood
  ending must declare an exact/diacritic-sensitive contract (never rely on the lenient recall normalizer alone,
  which discards every harakah and cannot discriminate a swapped-vowel or dropped-shadda hostile answer).
- **undeclared-kc-shard-input**: every gate-bearing `curriculum/kc-catalog.d/*.jsonl` shard must be pinned by
  name in the loader; an undeclared shard must fail closed, never silently join the catalog.
- **runtime-batch-unregistered-in-harness**: a new key bank and its test module must be registered as their own
  explicit, individually-checked entries in the canonical regression harness, never left dark or hidden inside
  a mega-try that would mask which artifact broke.
- **remediation-index-silent-omission**: a reachable KC (bound to a real drill-key row) missing entirely from
  the remediation index is exactly as unsafe as one carrying the wrong runtime posture; the validator must
  reject both.
- **ambiguous-transliteration-homograph**: a Latin transliteration shared by two unrelated Arabic particles
  (e.g. "amma" for both عَمَّ and أَمَّا) is a real prose-safety defect; spell the closed inventory in Arabic
  script and name the disambiguation explicitly.
- **licensed-alternate-spelling-under-taught-as-error**: a row must accept every attested, licensed spelling of
  a form (e.g. a hamza carrier simplified before an identical following letter) while still rejecting the
  actual misconception; never narrow to one spelling out of convenience.
- **overgeneralized-cancellation-rule**: a government/agreement cancellation rule stated without its licensed
  exceptions (e.g. a zarf/jarr-majrur predicate) teaches a false absolute; qualify the rule and the row
  reasoning together, adding no occurrence certification.
- **english-register-forbidden-answer-missing**: a forbidden_answers list authored only in the source language
  of the misconception (e.g. Arabic prose) is unreachable from a learner answering in the row's own English
  register; every row needs at least one forbidden form reachable in the answer's own register.
- **mixed-script-or-digit-corrupted-token**: a transliteration corrupted by a stray digit (e.g. "a1n" for "in")
  or a token that fuses Latin and Arabic letters with no separator (e.g. "command-lام") is a prose-integrity
  defect; scan committed prose for both patterns and keep every token single-script.
- **convention-dependent-default-treated-as-universal**: an orthographic or grammatical default that depends on
  a specific, closed convention (e.g. dotless final yāʾ vs. alif maqṣūra) must name that convention explicitly
  and reject a claim that it holds universally, rather than clearing as an unconditional auto-safe fact.
