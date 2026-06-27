# Full-Corpus Dogfood VN-01 - First Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo,
service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/standard-tranche-vn01-20260627/`

## Scope

- Verbs: `v048` through `v092`.
- Nouns: `n046` through `n095`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `1,462`, including `893` whole/resolved rows and `569`
  component-only evidence rows.
- Zero-row entries: `n051`, `n052`, `n057`, `n058`, `n059`, `n060`, `n063`,
  `n085`, `n087`.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 1,294 |
| token_only_override | 162 |
| pending/blocker | 5 |
| known_defect | 1 |

Routes:

- `blocker_queue_row`: `1,299`
- `repair_candidate`: `163`
- `production_bug_lesson`: `163`
- `drill_regression_fixture`: `163`
- `sarf_nahw_procedure_improvement`: `6`

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated and reviewed:

- verb sarf: `160` rows;
- noun sarf: `160` rows;
- nahw context: `180` rows;
- rich renderer: `180` rows;
- Qamus entry linkage: `180` rows;
- learner explanation: `180` rows.

The reviewers converged on three VN-01 findings:

1. Finite verbs and suffix-bearing verbs remain overexposed to dictionary or
   phrase hovers unless the token address records form, subject agreement, and
   object suffixes.
2. Nominal surfaces inside verb-root entries can still inherit infinitive or
   semantic-family glosses.
3. Same-surface or same-root nominal senses require exact context review; a
   populated string is not enough for rich certification.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 33:63:1 | يَسْـَٔلُكَ | ask you | component_only_candidate_no_whole_token_propagation | imperfect verb plus `كَ` object; parse proof required | known_defect -> production_bug_lesson + regression fixture | token-only two-vote |
| 83:25:4 | مَّخْتُومٍ | to seal | nominal_surface_verb_gloss_leakage | nominal/passive-participle contribution, not infinitive | populated_uncertified -> production_bug_lesson + nominal derivative fixture | human review |
| 35:40:28 | يَعِدُ | promises | weak_root_homograph_entry_linkage_review | وعد promise verb, not عدو family by collapsed surface | token_only_override -> blocker queue row | token-only two-vote |
| 55:44:4 | حَمِيمٍ | intimate friend... | same_surface_wrong_sense_context | context-sensitive boiling/hot-water family review | token_only_override -> production_bug_lesson + nahw review | token-only two-vote |
| 5:38:8 | نَكَٰلًۭا | shackles... | same_root_wrong_nominal_sense | deterrent/punishment sense review | token_only_override -> repair candidate only | token-only two-vote |
| 2:275:19 | مِثْلُ | to be like, equal to | nominal_token_gets_verb_gloss | nominal comparison token, not verb infinitive | token_only_override -> regression fixture | token-only two-vote |
| 6:163:2 | شَرِيكَ | to associate... partner... | nominal_pos_leakage_and_family_spread | accusative nominal "partner" contribution | token_only_override -> regression fixture | token-only two-vote |
| 2:187:49 | تُبَٰشِرُوهُنَّ | for spouses to touch... | verb_object_suffix_omitted_or_hidden | finite verb plus `هُنَّ` object | token_only_override -> production_bug_lesson + suffix fixture | token-only two-vote |
| 13:31:45 | وَعْدُ | to promise | masdar_or_nominal_gets_verb_infinitive | maṣdar/noun "promise" contribution | token_only_override -> nominal derivative fixture | token-only two-vote |
| 78:34:2 | دِهَاقًۭا | full, overflowing | false_suffix_detector_on_tanwin_case_ending | no pronoun suffix; tanwīn/case ending only | token_only_override -> detector no-op note | no skill change |

## Skill Impact

Updated sarf:

- `sarf/drills/verb-measures.md` adds a VN-01 finite-verb row set for object
  suffixes, weak roots, and dictionary-infinitive leakage.
- `sarf/drills/clitic-and-host-morphology.md` adds VN-01 suffix-object and
  possessive-noun reminders.
- `sarf/drills/nominal-derivatives.md` adds VN-01 nominal-surface rows such as
  `مَّخْتُومٍ`, `مِثْلُ`, `وَعْدُ`, and `مَيْتًا`.
- `sarf/evals/false-clitic-split-eval.jsonl` adds suffix-bearing verb and
  noun-host controls.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds VN-01 nominal leakage
  controls.

Updated nahw:

- `nahw/drills/grammar-routing-hard-cases.md` adds VN-01 sense/context rows for
  `حَمِيمٍ`, `نَكَٰلًۭا`, `مِثْلُ`, and suffix-bearing verbs.
- `nahw/evals/irab-polysemy-eval.jsonl` adds exact-address context fixtures
  for same-surface sense and governed object-pronoun rows.

No-op reasons:

- Renderer-only rows remain `needs_renderer_segments`; they need rich metadata
  and UI support, not new sarf/nahw doctrine.
- `دِهَاقًۭا`, `زَنجَبِيلًا`, and `نَارًۭا` showed suffix-detector noise from
  tanwīn/case endings; existing false-clitic guards already cover the rule.
- Positive whole-token rows such as `ٱلتَّنُّورُ`, `ٱلْأَصْفَادِ`, and
  `مُّوسَى` still need rich display/linkage before certification, but they did
  not expose a new skill rule.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn01_production_bug_lesson.sample.jsonl`

Rows:

- `quran:73:20:66` / `wbw:73:20:66` - finite verb dictionary leakage.
- `quran:2:187:49` / `wbw:2:187:49` - object suffix hidden inside a verb hover.
- `quran:83:25:4` / `wbw:83:25:4` - nominal/passive participle gets a verb
  infinitive.
- `quran:55:44:4` / `wbw:55:44:4` - same-surface wrong sense context.

## Renderer Requirements

VN-01 generated renderer requirements for rows that are string-populated but not
rich-certified:

- finite verbs need prefix/stem/subject/object segment classes;
- suffix-bearing verbs need visible object-pronoun breakdown;
- noun tokens need article/case/number/possessive segment readiness;
- component-only candidates must stay separate from whole-token entry
  candidates and must not weaken a gate.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche did not perform live source triangulation, two-vote
review, or owner-gated apply planning. Every repair candidate remains
`may_apply_live:false`.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn01_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn01_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn01_production_bug_lesson.sample.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- sarf/nahw drill updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`, `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
