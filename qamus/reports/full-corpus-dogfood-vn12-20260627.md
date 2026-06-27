# Full-Corpus Dogfood VN-12 - Twelfth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo, service, rebuild, hover apply, or hover coverage/correctness claim was changed.

Source batch: `out/standard-tranche-vn12-20260627/`

## Scope

- Verbs: `v543` through `v587`.
- Nouns: `n596` through `n645`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `580`, including `507` whole/resolved rows and `73` component-only evidence rows.
- Zero-row entries: `n598`, `n612`, `n633`, `n634`, `n640`, `n641`, `n644`.

This tranche advances dogfood review only. It does not create applyable hover decisions.

## Controller Counts

| class | rows |
|---|---:|
| known_defect | 1 |
| pending/blocker | 7 |
| populated_uncertified | 445 |
| token_only_override | 127 |

Routes:
| route | rows |
|---|---:|
| blocker_queue_row | 101 |
| renderer_requirement | 434 |
| repair_candidate | 45 |

Repair-preview-ready rows: `0`.

## Review Packets

Bounded reviewer packets were generated:
- entry linkage review: `240` rows committed to packet sample from `580` matching rows;
- learner explanation review: `240` rows committed to packet sample from `580` matching rows;
- rich renderer review: `240` rows committed to packet sample from `580` matching rows;
- nahw context review: `240` rows committed to packet sample from `354` matching rows;
- noun sarf review: `240` rows committed to packet sample from `462` matching rows;
- verb sarf review: `146` rows committed to packet sample from `146` matching rows;

All reviewed rows keep `may_apply_live:false`.

## Dominant Findings

VN-12 surfaced repeated classes:
- finite verb rows such as `أَضَآءَ`, `تُثِيرُ`, `ثَقِفْتُمُوهُمْ`, `أَفْرِغْ`, and `تَحُسُّونَهُم` need exact form, subject/agreement, voice/aspect, mood where governed, and suffix contribution before public wording can be trusted;
- suffix-bearing rows such as `يُحَرِّفُونَهُۥ`, `ثَقِفْتُمُوهُمْ`, `جَاوَزَهُۥ`, `فَرَشْنَٰهَا`, and `أَسْرَهُمْ` cannot hide object or possessor/reference contribution;
- nominal/POS leakage appears around `ٱلصَّيْدِ`, `صَيْدُ`, `مَالَ`, `شِفَآءٌۭ`, `زَرْعٍ`, and `جُوعٍۢ`, where verb-entry family prose must not override exact token role;
- component-only rows such as `فَلْيُؤَدِّ`, `فَٱصْطَادُوا۟`, `وَجَٰوَزْنَا`, `كَزَرْعٍ`, and `وَفُرُشٍۢ` improve routing but remain below whole-token certification;
- preposition/comparison and attached relation rows require nahw review for function, attachment, or mood effects;
- renderer-only rows still need rich metadata but do not create applyable hover repairs by themselves.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:75:13 | `يُحَرِّفُونَهُۥ` | to twist/deviate from meaning | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | populated_uncertified -> blocker_queue_row | component_only_blocker |
| 2:191:3 | `ثَقِفْتُمُوهُمْ` | to find/come upon in battle | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | token_only_override -> repair_candidate | two_vote_exact_address_review |
| 2:220:12 | `تُخَالِطُوهُمْ` | partners | missing_rich_renderer_segments;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | token_only_override -> repair_candidate | two_vote_exact_address_review |
| 5:1:20 | `ٱلصَّيْدِ` | to hunt | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;verb_entry_nominal_derivative_or_lexical_noun_pos_review | finite form, subject/agreement, voice/context before gloss | token_only_override -> repair_candidate | rich_metadata_plus_exact_address_review |
| 6:152:3 | `مَالَ` | money, wealth | missing_rich_renderer_segments;verb_entry_nominal_derivative_or_lexical_noun_pos_review | nominal/POS/case or mood review before reuse | populated_uncertified -> blocker_queue_row | two_vote_exact_address_review |
| 48:29:32 | `كَزَرْعٍ` | to plant or sow crops | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;verb_entry_nominal_derivative_or_lexical_noun_pos_review;preposition_or_attached_relation_requires_nahw_review | preposition/function relation plus host/attachment | populated_uncertified -> blocker_queue_row | component_only_blocker |
| 51:48:2 | `فَرَشْنَٰهَا` | to spread out | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | token_only_override -> repair_candidate | two_vote_exact_address_review |
| 56:34:1 | `وَفُرُشٍۢ` | furnishings | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;verb_entry_nominal_derivative_or_lexical_noun_pos_review;preposition_or_attached_relation_requires_nahw_review | preposition/function relation plus host/attachment | populated_uncertified -> blocker_queue_row | component_only_blocker |
| 2:17:7 | `أَضَآءَتْ` | to light/shine | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review | finite form, subject/agreement, voice/context before gloss | populated_uncertified -> blocker_queue_row | component_only_blocker |
| 2:20:6 | `أَضَآءَ` | to light/shine | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review | finite form, subject/agreement, voice/context before gloss | token_only_override -> repair_candidate | rich_metadata_plus_exact_address_review |
| 2:74:2 | `قَسَتْ` | to be hard | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review | finite form, subject/agreement, voice/context before gloss | token_only_override -> repair_candidate | rich_metadata_plus_exact_address_review |
| 2:283:14 | `فَلْيُؤَدِّ` | to hand over/pay | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;preposition_or_attached_relation_requires_nahw_review | preposition/function relation plus host/attachment | populated_uncertified -> blocker_queue_row | component_only_blocker |

## Skill Impact

Committed sample: `qamus/examples/full_corpus_dogfood_vn12_skill_impact.sample.jsonl`

Rows:
- `finite_verb_dictionary_gloss_leakage`: 117 rows, updates `sarf/procedures/verb-form-and-mood-review.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `verb_object_suffix_or_attached_pronoun_not_visible`: 21 rows, updates `sarf/procedures/clitic-and-host-morphology.md, nahw/procedures/pronoun-attachment.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl, nahw/evals/suffix-pronoun-eval.jsonl`.
- `verb_entry_nominal_or_pos_leakage`: 28 rows, updates `sarf/procedures/nominal-derivative-decision.md`, regressions `sarf/evals/nominal-derivative-error-eval.jsonl`.
- `preposition_or_attached_relation_requires_nahw_review`: 36 rows, updates `nahw/procedures/preposition-pronoun.md, nahw/procedures/pp-attachment-review.md`, regressions `nahw/evals/particle-function-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `component_only_candidate_no_whole_token_propagation`: 73 rows, updates `sarf/procedures/clitic-and-host-morphology.md, sarf/procedures/verb-form-and-mood-review.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl`.
- `rich_renderer_missing_segments_only`: 434 rows, updates `none`, regressions `tools/check_regressions.py`.

No-op reasons:

- Rows whose only defect is `missing_rich_renderer_segments` with whole-token evidence are renderer metadata backfill, not linguistic re-authoring.
- Repair-preview-ready remains `0`: this tranche did not run MCP/iʿrāb review, external source triangulation, two-vote adjudication, global grammar gates, owner approval, or apply planning.
- Component-only rows remain blockers even when they supply useful candidate evidence.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn12_production_bug_lesson.sample.jsonl`

Lesson rows cover verb object suffix omission, finite verb dictionary leakage, nominal/POS leakage, preposition/comparison host relation, and component-only conjunction+host evidence.

## Next Tranche

VN-13 should cover verbs `v588` through `v632` and nouns `n646` through `n695`.
