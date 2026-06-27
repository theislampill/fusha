# Full-Corpus Dogfood VN-00 — Verb/Noun Calibration

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo,
service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/vn00-dogfood-20260627/`

## Scope

- Verbs: `v001` through `v047`.
- Nouns: `n001` through `n045` in the repo source-key format (the owner prompt
  wrote `n0001` through `n0045`; this tranche normalizes to the live/Fusha
  canonical `n###` keys).
- Entries inventoried: `92` total (`47` verb, `45` noun).
- Full rows: `7,998`, including `6,981` whole/resolved rows and `1,017`
  component-only evidence rows.
- Zero-row entries: `n005`, `n006`, `n010`, `n011`, `n013`, `n036`, `n045`.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 7,463 |
| token_only_override | 484 |
| pending/blocker | 50 |
| known_defect | 1 |

Routes:

- `blocker_queue_row`: `7,513`
- `repair_candidate`: `485`
- `production_bug_lesson`: `485`
- `drill_regression_fixture`: `485`
- `sarf_nahw_procedure_improvement`: `51`

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated and reviewed:

- verb sarf: `140` rows;
- noun sarf: `140` rows;
- nahw context: `160` rows;
- rich renderer: `160` rows;
- Qamus entry linkage: `160` rows;
- learner explanation: `160` rows.

The reviewers agreed on the main issue: visible hover population is not
dogfood completion. Finite verbs, plural/possessive nouns, PP/iḍāfa tokens,
and component-only candidates need exact address, parse key, entry/sense or
blocker, and learner-visible breakdown before certification.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:13:8 | قَالُوا | to say... | finite_verb_dictionary_gloss_leakage | finite perfect active 3mp token contribution | populated_uncertified -> production_bug_lesson + regression_fixture | token-only two-vote |
| 2:57:14 | ظَلَمُونَا | to wrong | verb_object_suffix_omitted | 3mp verb plus `نا` object | populated_uncertified -> production_bug_lesson + regression_fixture | token-only two-vote |
| 2:14:10 | شَيَٰطِينِهِمْ | Satan/devil concept prose | possessive_plural_noun_gets_concept_entry_spread | plural host plus "their" | token_only_override -> production_bug_lesson + regression_fixture | token-only two-vote |
| 2:34:3 | لِلْمَلَٰٓئِكَةِ | angels / angelkind | lam_pp_plus_plural_noun_pos_leakage | lām + article + plural host + PP role | populated_uncertified -> needs_sarf_review + needs_nahw_review | component no-propagation two-vote |
| 2:83:11 | إِحْسَانًۭا | good/beautiful/best spread | masdar_gets_semantic_family_spread | maṣdar/action noun contribution | populated_uncertified -> production_bug_lesson + regression_fixture | token-only two-vote |
| 2:102:20 | ٱلْمَلَكَيْنِ | angels / angelkind | dual_number_homograph_collision | dual noun, exact sense required | populated_uncertified -> human_review_required | human review |
| 2:38:10 | تَبِعَ | null | pending_blocker_preserved | no public hover until blocker cleared | pending/blocker -> exact next gate preserved | human review |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` now names VN-00 finite-verb
  dictionary leakage and suffix-bearing verb examples.
- `sarf/procedures/noun-plural-gender.md` now names VN-00 plural/dual/suffix
  and concept-prose noun leakage.
- `sarf/procedures/proper-noun.md` now blocks name etymon prose as public hover
  text.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds VN-00 maṣdar/result and
  active-participle spread rows.
- `sarf/evals/false-clitic-split-eval.jsonl` adds verb-object suffix and
  possessive-noun rows.

Updated nahw:

- `nahw/procedures/idafa-jar-majrur.md` now names VN-00 lām, iḍāfa, zarf, and
  suffix relations.
- `nahw/procedures/referent-context.md` now names VN-00 Garden/Paradise,
  common/proper ilah, and concept-prose guards.
- `nahw/procedures/pp-attachment-review.md` now states that string-correct PP
  hovers are not attachment proof and component candidates cannot auto-safe a
  whole token.

No-op reasons:

- `الرَّحْمَٰنِ`, `الرَّحِيمِ`, `ٱلْمُسْتَقِيمَ`, and `جَاعِلٌ` are already
  covered by the nominal-derivative/POS leakage lane; VN-00 routes them to
  Qamus repair review rather than adding duplicate skill text.
- `قَالُوا`, `كَانُوا`, and many finite-verb rows were already forbidden by
  sarf; VN-00 adds regression examples because they recur at scale.
- Pending rows such as `تَبِعَ` produced no new skill text; preserving the
  blocker is the correct movement.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn00_production_bug_lesson.sample.jsonl`

Rows:

- `quran:2:13:8` / `wbw:2:13:8` — finite verb dictionary leakage.
- `quran:2:57:14` / `wbw:2:57:14` — verb object suffix omitted.
- `quran:2:14:10` / `wbw:2:14:10` — possessive plural noun plus concept spread.
- `quran:2:34:3` / `wbw:2:34:3` — lām + article + plural host is component-only.
- `quran:2:83:11` / `wbw:2:83:11` — maṣdar gets semantic-family spread.

## Renderer Requirements

VN-00 generated renderer requirements for rows that are string-populated but not
rich-certified:

- finite verb tokens need verb stem plus subject/object suffix classes;
- lām/bā'/wāw/fā' component rows need visible function classes, but component
  candidates must not certify the whole token;
- plural/dual noun tokens need number and suffix/possessive breakdown;
- concept or teaching prose must stay out of best-hover text.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche did not perform live source triangulation, two-vote
review, or owner-gated apply planning. Every repair candidate remains
`may_apply_live:false`.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn00_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn00_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn00_production_bug_lesson.sample.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- sarf/nahw procedure updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`, `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
