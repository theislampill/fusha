# Full-Corpus Hover Dogfood VN-15 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service,
mirror, or hover decision ledger was changed.

## Scope

- Verbs: `v678` through `v722`
- Nouns: `n746` through `n795`
- Entries inventoried: 95
- Live hover rows reviewed: 229
- Whole-token candidate rows: 199
- Component-only evidence rows: 30
- Repair-preview-ready rows: 0
- `may_apply_live`: false for every sampled row

## Classification Counts

| classification | count |
|---|---:|
| `populated_uncertified` | 105 |
| `token_only_override` | 124 |

## Issue Counts

| issue | count |
|---|---:|
| `missing_rich_renderer_segments` | 229 |
| `surface_family_requires_token_only_override` | 124 |
| `finite_verb_dictionary_gloss_or_form_review` | 74 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 66 |
| `preposition_or_attached_relation_requires_nahw_review` | 55 |
| `component_only_candidate_no_whole_token_propagation` | 30 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 23 |
| `article_definiteness_requires_rich_segments` | 16 |
| `noun_hover_may_leak_verb_infinitive` | 3 |

## Reviewer Findings

Verb-sarf review found four repeated classes:

- finite verb dictionary-gloss leakage: examples include `يُوَفِّقِ`,
  `يُؤْلُونَ`, `يَأْلُونَكُمْ`, `يَخْذُلْكُمْ`, `أَطْفَأَهَا`, and
  `يَسْتَفِزَّهُم`;
- verb-entry nominal/POS leakage: examples include `وِفَاقًا`,
  `ٱلْءَازِفَةُ`, `ٱلْمُخْبِتِينَ`, `وَالذَّارِيَاتِ`, and
  `مَطْوِيَّٰتٌۢ`;
- component-only evidence: examples include `وَتَوْفِيقًا`, `وَقِفُوهُمْ`,
  `فَيُحْفِكُمْ`, `لِيُطْفِـُٔوا۟`, and `وَٱسْتَفْزِزْ`;
- suffix-pronoun accounting: examples include `وَقِفُوهُمْ`,
  `يَأْلُونَكُمْ`, `يَخْذُلْكُمْ`, `خَوَّلْنَٰهُ`,
  `لَيَصْرِمُنَّهَا`, and `لَيَسْتَفِزُّونَكَ`.

Nahw-function review found four repeated classes:

- preposition/comparison rows need exact segmentation and attachment;
- suffix rows split by host into noun possessor/referent vs verb object;
- PP attachment remains uncertified without an attachment head;
- component-only function evidence must not become whole-token propagation.

## State Transitions

VN-15 did not produce apply-ready rows. It did produce durable dogfood state
movement:

- populated strings with finite verb entry prose -> `repair_candidate` with
  `rich_metadata_plus_exact_address_review` or `two_vote_exact_address_review`;
- component evidence below a written token -> `blocker_queue_row` with
  `component_only_blocker`;
- string-correct but display-only rows -> `renderer_requirement` with
  `rich_renderer_metadata_backfill`;
- suffix-bearing noun/verb rows -> exact-address suffix/referent or object
  review, not host-only hover certification.

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

No-op reason for live Qamus: all VN-15 rows remain read-only candidates,
blockers, or renderer requirements. None pass the global grammar, row-level,
two-vote, source-triangulation, and rich-certification gates required for live
apply.

## Committed Samples

- `qamus/examples/full_corpus_dogfood_vn15_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn15_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn15_production_bug_lesson.sample.jsonl`

Full generated VN-15 artifacts remain under ignored `out/` and are not a live
source of truth.
