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
  against sibling rows before any form is forbidden. When two independent linguistic reviews (e.g. an Opus
  targeted re-review and an independent Sonnet linguistic vote) DISAGREE on whether the inventory is exhaustive,
  do not manufacture agreement or pick a side: teach only the safe intersection both reviews confirm as
  securely licensed, drop any exhaustive "only/exactly N" claim and any forbidden-answer that would hard-reject
  the disputed form, and record an honest blocker (in existing free-text fields — never invent a schema field
  for it) naming the open question for scholar review. A row's held/two-vote gate posture and public-eligibility
  fields stay unchanged; the disagreement is preserved, not resolved, by this bounded repair. When a review
  disagreement spans MULTIPLE disputed forms sharing the same shape of ambiguity (e.g. a kasra-merged AND a
  ḍamma-merged geminate-jussive candidate, both disputed by itbāʿ), a repair that only removes the hard-reject
  from ONE of them and leaves the other's prompt, expected answer, forbidden answer, required reasoning, or
  explanation still asserting it is "not licensed at all" has not preserved the disagreement — it has just
  picked a side for the untouched form while claiming otherwise. Check every disputed form named by either
  review, not only the one the finding happened to name first. A prompt that asks a learner to "correct" one
  specific disputed surface also presupposes that surface is wrong — that is the same defect even with no
  matching forbidden_answers entry, because the task framing itself picks a side; author the prompt around the
  safe-intersection fact instead of staging a disputed form as an error to fix.
- **diacritic-blind-grading-collision**: a row whose answer correctness depends on a vowel, shadda, or case/mood
  ending must declare an exact/diacritic-sensitive contract (never rely on the lenient recall normalizer alone,
  which discards every harakah and cannot discriminate a swapped-vowel or dropped-shadda hostile answer). When a
  row declares MULTIPLE exact surfaces, state explicitly whether they are a CONJUNCTION (every discriminating
  surface required — a contrastive/paradigm-pair row, e.g. two verbs' distinct stored vowels) or an ALTERNATION
  (any one licensed surface suffices — genuine spelling variants of one fact); an unmarked multi-surface
  contract must fail closed to the stricter conjunctive reading, never silently accept a learner who supplied
  only one half of a contrast. The hostile test proving this contract must exercise the REAL grader against a
  REAL substituted token drawn from the row's own authored text (or a constructed answer missing one required
  conjunctive surface) — a whole-sentence forbidden-answer-vs-gold-text membership check is vacuous (authored
  forbidden prose differs in wording from the gold sentence and so never fires) and does not satisfy this class.
- **undeclared-kc-shard-input**: every gate-bearing `curriculum/kc-catalog.d/*.jsonl` shard must be pinned by
  name in the loader; an undeclared shard must fail closed, never silently join the catalog. The fail-closed
  check must live at the shared loader's own choke point (the function every caller ultimately calls to read
  the catalog), not only inside one caller's private wrapper — a gate placed on a single consumer leaves every
  OTHER direct caller of the shared loader free to silently admit an undeclared shard. Pin every gate-bearing
  catalog artifact (the legacy catalog file, every declared shard, and the loader module itself) in the
  benchmark data manifest with a completeness guard that fails if any of them is removed or unpinned, so the
  pinned set can never silently drift from the loader's own declared-shard source of truth.
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
  reasoning together, adding no occurrence certification. When a rule has MULTIPLE structurally-parallel
  triggers sharing the SAME licensed exception (e.g. a fronted khabar and a fronted maʿmūl/complement of an
  otherwise-ordinary khabar both exempted by the same zarf/jarr-majrur positional-freedom exception), qualify
  every parallel trigger's own row and the KC clause together — qualifying only the first-discovered trigger
  and leaving a structurally identical sibling trigger unqualified is a recurrence of this same class, not a
  different defect.
- **english-register-forbidden-answer-missing**: a forbidden_answers list authored only in the source language
  of the misconception (e.g. Arabic prose) is unreachable from a learner answering in the row's own English
  register; every row needs at least one forbidden form reachable in the answer's own register.
- **mixed-script-or-digit-corrupted-token**: a transliteration corrupted by a stray digit (e.g. "a1n" for "in")
  or a token that fuses Latin and Arabic letters with no separator (e.g. "command-lام") is a prose-integrity
  defect; scan committed prose for both patterns and keep every token single-script.
- **convention-dependent-default-treated-as-universal**: an orthographic or grammatical default that depends on
  a specific, closed convention (e.g. dotless final yāʾ vs. alif maqṣūra) must name that convention explicitly
  and reject a claim that it holds universally, rather than clearing as an unconditional auto-safe fact.
- **disputed-adjudication-mirror-in-sibling-or-remediation-text**: repairing the one row/KC a finding named is
  not enough when the same disputed linguistic question is restated elsewhere in the same paradigm. Before
  closing a repair that preserves an open, two-vote-blocked disagreement (see
  `geminate-jussive-licensed-form-forbidden` above), check every SIBLING row of the same paradigm for the same
  hard-settled conclusion or exhaustive-inventory count stated in its own words, and check every learner-facing
  mirror of that row's content — a Train C remediation-index symptom cell, a dogfood/error-remediation summary,
  a KC's `plain_rule`/`teach_template`/`typical_error_feature` — for the same defect restated as routing or
  remediation prose. A prior repair that fixed only the row the finding quoted verbatim, while a sibling row's
  own concept/explanation field or the remediation index's learner-facing symptom text still asserted the
  identical settled conclusion or exhaustive count in different words, has not closed the finding — it has
  relocated it. Match by MEANING (a closed set of paraphrases: "form X is simply indicative, not a jussive",
  "this cell has its own N licensed shapes"), not by the one exact phrase the finding happened to quote.
