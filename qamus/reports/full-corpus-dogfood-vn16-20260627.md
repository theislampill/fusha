# Full-Corpus Hover Dogfood VN-16 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service,
mirror, or hover decision ledger was changed.

## Scope

- Verbs: `v723` through `v767`
- Nouns: `n796` through `n845`
- Entries inventoried: 95
- Live hover rows reviewed: 302
- Whole-token candidate rows: 277
- Component-only evidence rows: 25
- Repair-preview-ready rows: 0
- `may_apply_live`: false for every sampled row

## Classification Counts

| classification | count |
|---|---:|
| `populated_uncertified` | 142 |
| `token_only_override` | 160 |

## Issue Counts

| issue | count |
|---|---:|
| `missing_rich_renderer_segments` | 302 |
| `surface_family_requires_token_only_override` | 160 |
| `article_definiteness_requires_rich_segments` | 67 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 61 |
| `finite_verb_dictionary_gloss_or_form_review` | 58 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 46 |
| `component_only_candidate_no_whole_token_propagation` | 25 |
| `preposition_or_attached_relation_requires_nahw_review` | 7 |

## Reviewer Findings

Verb-sarf review found four repeated classes:

- passive or voice-sensitive finite rows, including `كُبِتَ`, `كُبِتُوا۟`,
  `يُكَوِّرُ`, and `كُوِّرَتْ`;
- suffix-bearing finite rows, including `يَكْبِتَهُمْ`, `لِتَلْفِتَنَا`,
  `أَلْفَيْنَا`, `نُنَكِّسْهُ`, `فَهَزَمُوهُم`, `يَتِرَكُمْ`,
  `فَـَٔازَرَهُۥ`, and `تَؤُزُّهُمْ`;
- verb-entry nominal/POS leakage, including `مُكِبًّا`, `لَذَّةٍ`,
  `لَّذَّةٍۢ`, `ٱللُّؤْلُؤُ`, `ٱلْحَدِيدِ`, `ٱلْقِطْرِ`,
  `ٱلْيَاقُوتُ`, and `لُحُومُهَا`;
- component-only evidence below full written tokens, including `فَكُبْكِبُوا`,
  `فَكُبَّتْ`, `وَيُكَوِّرُ`, `وَتَلَذُّ`, `وَٱلْتَفَّتِ`,
  `وَأَلْفَيَا`, and `يَمْحُوا۟`.

Nahw-function review found four repeated classes:

- lām-on-verb rows need lām function, mood/governor, finite host, and object
  suffix review;
- suffix rows split by host type: noun possessor/referent vs verb object;
- raw first-letter bā' or lām is not a preposition/governor without strict
  segmentation, as in `لِبَاسٌۭ` and `بِضَاعَتَهُمْ`;
- PP attachment begins only after segmentation proves a real particle.

## State Transitions

VN-16 did not produce apply-ready rows. It did produce durable dogfood state
movement:

- finite/passive and suffix-bearing verb strings -> `repair_candidate` with
  `rich_metadata_plus_exact_address_review` or `two_vote_exact_address_review`;
- component evidence below a written token -> `blocker_queue_row` with
  `component_only_blocker`;
- string-correct but display-only rows -> `renderer_requirement` with
  `rich_renderer_metadata_backfill`;
- lexical false-prefix rows -> sarf/POS or suffix review, not a PP/governor
  lane by raw surface.

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Updated nahw:

- `nahw/procedures/pronoun-attachment.md`
- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/suffix-pronoun-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`

No-op reason for live Qamus: all VN-16 rows remain read-only candidates,
blockers, or renderer requirements. None pass the global grammar, row-level,
two-vote, source-triangulation, and rich-certification gates required for live
apply.

## Committed Samples

- `qamus/examples/full_corpus_dogfood_vn16_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn16_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn16_production_bug_lesson.sample.jsonl`

Full generated VN-16 artifacts remain under ignored `out/` and are not a live
source of truth.
