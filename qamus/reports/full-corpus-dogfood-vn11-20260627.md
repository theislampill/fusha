# Full-Corpus Dogfood VN-11 - Eleventh Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage/correctness claim was
changed.

Source batch: `out/standard-tranche-vn11-20260627/`

## Scope

- Verbs: `v498` through `v542`.
- Nouns: `n546` through `n595`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `595`, including `530` whole/resolved rows and `65` component-only evidence rows.
- Zero-row entries: `n546`, `n550`, `n552`, `n575`, `n579`, `n580`, `n582`, `n583`, `n586`, `n593`.

This tranche advances dogfood review only. It does not create applyable hover
decisions.

## Controller Counts

| class | rows |
|---|---:|
| known_defect | 1 |
| populated_uncertified | 434 |
| token_only_override | 160 |

Routes:

| route | rows |
|---|---:|
| blocker_queue_row | 272 |
| renderer_requirement | 186 |
| repair_candidate | 137 |

Repair-preview-ready rows: `0`.

## Review Packets

Bounded reviewer packets were generated:

- entry linkage review: `240` rows;
- learner explanation review: `240` rows;
- rich renderer review: `240` rows;
- nahw context review: `190` rows;
- noun sarf review: `203` rows;
- verb sarf review: `240` rows.

All reviewed rows keep `may_apply_live:false`.

## Dominant Findings

VN-11 surfaced seven repeated classes:

- finite verb rows such as `غَنِمْتُم`, `تَسْتَغِيثُونَ`, `يُغَاثُوا۟`,
  `قَبَضْنَٰهُ`, and `ٱقْذِفِيهِ` still need exact form, voice/aspect,
  subject/object, and suffix contribution before public wording can be trusted;
- component-only rows such as `فَٱسْتَغَٰثَهُ`, `لِفُرُوجِهِمْ`,
  `فَٱقْذِفِيهِ`, `فَقَذَفْنَٰهَا`, and the known `فَأَهْلَكْنَاهُمْ`
  improve routing but remain below whole-token certification;
- standalone pronoun/function rows such as `هُمْ` and `هُمُ` collide with the
  `v508` family and must be reviewed as pronoun/function tokens, not as verb
  entry propagation;
- preposition/relation rows such as `لِفُرُوجِهِمْ`, `كَسَادَهَا`,
  `كَبَدٍ`, `لَٱنفَضُّوا۟`, and `لَنَاكِبُونَ` require function,
  attachment, mood, or false-prefix review;
- nominal/POS leakage appears in `مَغَانِمُ`, `غَنَمُ`, `ٱلْغَيْثَ`,
  `فُرُوجَهُمْ`, `فِضَّةٍۢ`, and the noun-tranche `كُفُّوٓا۟` row;
- suffix-bearing rows such as `ظَعْنِكُمْ`, `كَسَادَهَا`, `نَحْبَهُۥ`,
  `قَبَضْنَٰهُ`, and `ٱقْذِفِيهِ` cannot hide attached pronoun or possessive
  contribution;
- renderer-only rows such as `كُلِّ` and `كُفُوًا` need rich metadata but did
  not force a new sarf/nahw rule by themselves.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 8:41:3 | `غَنِمْتُم` | to take war gains | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review | finite form, subject/agreement, voice/context before gloss | token_only_override -> repair_candidate | rich_metadata_plus_exact_address_review |
| 8:9:2 | `تَسْتَغِيثُونَ` | to cry for aid | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review | finite form, subject/agreement, voice/context before gloss | token_only_override -> repair_candidate | rich_metadata_plus_exact_address_review |
| 20:39:2 | `ٱقْذِفِيهِ` | to throw, cast, hurl | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | token_only_override -> repair_candidate | two_vote_exact_address_review |
| 25:46:2 | `قَبَضْنَٰهُ` | to hold in one’s hand | missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | token_only_override -> repair_candidate | two_vote_exact_address_review |
| 26:139:2 | `فَأَهْلَكْنَاهُمْ` | so We destroyed them | component_only_candidate_no_whole_token_propagation;finite_verb_dictionary_gloss_or_form_review;suffix_or_attached_pronoun_requires_visible_accounting | host plus visible suffix/pronoun contribution | known_defect -> blocker_queue_row | component_only_blocker |
| 2:4:11 | `هُمْ` | they, their | missing_rich_renderer_segments;verb_entry_pronoun_or_function_token_candidate_requires_nahw_review | pronoun/function token role, not verb-entry propagation | populated_uncertified -> blocker_queue_row | two_vote_exact_address_review |
| 23:5:3 | `لِفُرُوجِهِمْ` | private parts / chastity | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;preposition_or_attached_relation_requires_nahw_review | preposition/function relation plus host/attachment | populated_uncertified -> blocker_queue_row | component_only_blocker |
| 24:30:7 | `فُرُوجَهُمْ` | their private parts | missing_rich_renderer_segments;verb_entry_nominal_derivative_or_lexical_noun_pos_review;suffix_or_attached_pronoun_requires_visible_accounting | nominal/POS/case or mood review before reuse | populated_uncertified -> blocker_queue_row | two_vote_exact_address_review |
| 4:94:24 | `مَغَانِمُ` | spoils | missing_rich_renderer_segments;verb_entry_nominal_derivative_or_lexical_noun_pos_review | nominal/POS/case or mood review before reuse | token_only_override -> repair_candidate | rich_metadata_plus_exact_address_review |
| 31:34:7 | `ٱلْغَيْثَ` | to be aided with water | component_only_candidate_no_whole_token_propagation;missing_rich_renderer_segments;finite_verb_dictionary_gloss_or_form_review;verb_entry_nominal_derivative_or_lexical_noun_pos_review;article_definiteness_requires_rich_segments | nominal/POS/case or mood review before reuse | populated_uncertified -> blocker_queue_row | component_only_blocker |
| 76:15:5 | `فِضَّةٍۢ` | silver | missing_rich_renderer_segments;verb_entry_nominal_derivative_or_lexical_noun_pos_review | nominal/POS/case or mood review before reuse | populated_uncertified -> blocker_queue_row | rich_metadata_plus_exact_address_review |
| 4:77:7 | `كُفُّوٓا۟` | to hold someone’s hand back | missing_rich_renderer_segments;noun_hover_may_leak_verb_infinitive | nominal/POS/case or mood review before reuse | populated_uncertified -> blocker_queue_row | two_vote_exact_address_review |

## Skill Impact

Committed sample: `qamus/examples/full_corpus_dogfood_vn11_skill_impact.sample.jsonl`

Rows:

- `finite_verb_dictionary_gloss_leakage`: 195 rows, updates `sarf/procedures/verb-form-and-mood-review.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `suffix_or_object_pronoun_not_visible`: 28 rows, updates `sarf/procedures/clitic-and-host-morphology.md, nahw/procedures/preposition-pronoun.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl, nahw/evals/suffix-pronoun-eval.jsonl`.
- `verb_entry_pronoun_or_function_token_candidate_collision`: 142 rows, updates `sarf/procedures/nominal-derivative-decision.md, nahw/procedures/pronoun-attachment.md`, regressions `nahw/evals/particle-function-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `verb_entry_nominal_derivative_or_pos_leakage`: 68 rows, updates `sarf/procedures/nominal-derivative-decision.md`, regressions `sarf/evals/nominal-derivative-error-eval.jsonl`.
- `preposition_or_attached_relation_requires_nahw_review`: 20 rows, updates `nahw/procedures/preposition-pronoun.md, nahw/procedures/pp-attachment-review.md`, regressions `nahw/evals/particle-function-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `component_only_candidate_no_whole_token_propagation`: 65 rows, updates `sarf/procedures/clitic-and-host-morphology.md, sarf/procedures/verb-form-and-mood-review.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl`.
- `rich_renderer_missing_segments_only`: 186 rows, updates `none`, regressions `tools/check_regressions.py`.

No-op reasons:

- Rows whose only defect is `missing_rich_renderer_segments` with whole-token
  evidence are renderer metadata backfill, not linguistic re-authoring.
- Repair-preview-ready remains `0`: this tranche did not run MCP/i'rab review,
  external source triangulation, two-vote adjudication, global grammar gates,
  owner approval, or apply planning.
- Component-only rows remain blockers even when they supply useful candidate
  evidence.

## Production-Bug Lessons

Committed sample:
`qamus/examples/dogfood_vn11_production_bug_lesson.sample.jsonl`

Rows:

- `quran:8:41:3` / `wbw:8:41:3` - finite_verb_dictionary_gloss_leakage.
- `quran:20:39:2` / `wbw:20:39:2` - verb_object_suffix_omitted_or_hidden.
- `quran:26:139:2` / `wbw:26:139:2` - component_only_finite_verb_object_suffix.
- `quran:2:4:11` / `wbw:2:4:11` - verb_entry_pronoun_or_function_token_candidate_collision.
- `quran:23:5:3` / `wbw:23:5:3` - preposition_host_suffix_hidden.
- `quran:4:94:24` / `wbw:4:94:24` - verb_entry_nominal_derivative_or_pos_leakage.
- `quran:4:77:7` / `wbw:4:77:7` - noun_hover_may_leak_verb_infinitive.
- `quran:112:4:4` / `wbw:112:4:4` - renderer_metadata_only_not_linguistic_certification.

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`,
  `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
- Candidate token-decision JSONL is not applyable from this tranche. Live apply
  remains owner-gated after all verb/noun tranches, final full-corpus rerun,
  global grammar gates, row-level gates, dual/two-vote gates, source/MCP
  triangulation, rebuild proof, health check, public readback, no-leak scan,
  and rollback plan.
