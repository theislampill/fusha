# Tranche 001 — contextual مَا runtime (T1MC)

This drill surface backs `curriculum/drills/keys/tranche-001-ma-context-runtime.keys.jsonl` (rows `T1MC-01`
through `T1MC-49`). It is a **remediation and practice surface, never assessment or certification**: no row
here is usable as independent assessment, and completing this drill does not certify mastery, does not close
any lesson, and does not close any unit. Every row is `two_vote_required: true` and `public_eligible: false`;
the ordinary tutor holds each item pending independent review even after a fully correct answer with fully
correct reasoning.

## What this drill teaches

The same written مَا carries a different occurrence-bound function almost every time it appears: relative,
negative, interrogative, conditional, masdariyya, exclamatory/idiomatic, or a genuinely unresolved rival
between two of those. A correct label with the wrong function, governor, scope, referent, mood/case reason,
or rival disposition still fails — sounding right is not being right. Each of the 14 knowledge components (KCs)
below isolates one coherent, occurrence-bound مَا diagnostic; a learner works through constructed practice
sentences (never a real Qurʾānic occurrence — every row here is `quran_example: null`,
`occurrence_status: no_committed_occurrence_evidence`) that force the diagnostic to matter.

## The 14 knowledge components

- `kc-t1-ma-context-masdariyya-verbal-noun-substitution` — مَا المصدرية vs مَا الموصولة: the resumptive-pronoun
  test and the masdar-substitution test decide which is present, never frequency.
- `kc-t1-ma-context-hijaziyya-tamimiyya-nullifiers` — مَا الحجازية's laysa-like government (ism marfūʿ, khabar
  manṣūb) is conditional; إلا-breaking, predicate/complement fronting, a following بل, or a preceding
  interrogative hamza each cancel or bypass it.
- `kc-t1-ma-context-amma-kaffa-jawab-fa` — أَمَّا is إنْ fused with مَا الكافة, presupposing an unstated
  condition; its جواب needs the obligatory فاء الجواب in every apodosis shape.
- `kc-t1-ma-context-exclamatory-interrogative-case` — the exclamatory frozen taʿajjub verb's accusative object
  vs the interrogative elative predicate's genitive complement; the answer-expectation test decides which.
- `kc-t1-ma-context-negated-possession-lam-subjunctive` — مَا لَكَ أَنْ + subjunctive denies a right or
  entitlement as one frame; a bare command-lام without أَنْ is a different, jussive-governing frame.
- `kc-t1-ma-context-lamma-jazm-vs-temporal-rival` — لَمَّا الجازمة (jussive-governing "not yet") vs the
  unrelated non-governing temporal لَمَّا ("when"): same surface, rival dispositions.
- `kc-t1-ma-context-ma-zala-kana-sister-government` — مَا زَالَ/بَرِحَ/فَتِئَ/انْفَكَّ: negative-only
  kāna-sisters, ism marfūʿ / khabar manṣūb, meaning continuing state, never single-event negation.
- `kc-t1-ma-context-ma-dama-temporal-not-negation` — مَا دَامَ is a fossilized durative-limit frame; its مَا
  contributes no negation at all, despite the identical surface.
- `kc-t1-ma-context-ma-nafiya-no-mood-government` — plain مَا negates a statement with no mood effect on the
  following verb, unlike لَا's prohibitive use or لَمْ's past-shifting jussive government.
- `kc-t1-ma-context-istifham-alif-elision-preposition` — interrogative مَا drops its alif under a
  directly-governing preposition (لِمَ، عَمَّ، مِمَّ، فِيمَ، بِمَ), with مِنْ's own nūn assimilating into the mīm.
- `kc-t1-ma-context-relative-preposition-majrur-government` — relative/masdariyya مَا keeps its alif after a
  preposition; some verbs lexically fix their own preposition, and مِمَّا (source) ≠ فِيمَا (topic).
- `kc-t1-ma-context-ma-vs-man-rational-referent` — مَا's required clause-initial scope, its default
  singular-masculine agreement, and the مَا (non-rational) vs مَن (rational) referent split.
- `kc-t1-ma-context-innama-kaffa-restriction-scope` — إِنَّمَا is إِنَّ neutralized by مَا الكافة into a
  restriction targeting the LAST-mentioned element; plain إِنَّ and إِنَّمَا are not interchangeable.
- `kc-t1-ma-context-lamma-jazm-requires-mudari` — لَمَّا الجازمة only ever governs a مضارع verb; pairing it
  with a ماضٍ verb is ungrammatical, not merely unusual.

## How a row is graded

Each row carries an `expected_answer`, `accepted_variants`, `forbidden_answers`, and `required_reasoning`
through the ordinary `tools/fusha_tutor_runtime.py` grader (content-only; never a self-report). A correct
answer with missing or wrong `required_reasoning` is rejected and routed back to this lesson surface. A
correct answer with correct reasoning is `held_for_fact_gate` (content mastered, but pending the row's
mandatory two-vote fact gate) — it is never silently cleared, and a learner-declared `second_check` never
clears it either.

## Scope discipline

This lesson advances the contextual مَا / negation / nawāsikh / hidden-structure capability lattice —
principally `u-n01` — across `L1.M5.04`, `L1.M5.05`, `L1.M5.07`, `L2.M1.02`, `L2.M1.04`, `L2.M5.02`,
`L2.M5.03`, `L3.M4.04`, `L3.M4.08`, `L4.M2.04`, `L4.M3.07`, `L4.M5.10`, `L5.M1.06`, and `L6.M4.06`. It does
**not** close or certify any of those lessons, and it does not close or certify `u-n01` or any other unit;
adding these 49 rows to the bank advances coverage of one capability lattice, nothing more.
