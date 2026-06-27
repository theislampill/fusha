# Full-Corpus Dogfood VN-13 - Thirteenth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo, service, rebuild, hover apply, or hover coverage/correctness claim was changed.

Source batch: `out/standard-tranche-vn13-20260627/`

## Scope

- Verbs: `v588` through `v632`.
- Nouns: `n646` through `n695`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `554`, including `492` whole/resolved rows and `62` component-only evidence rows.
- Zero-row entries: `n647`, `n650`, `n670`, `n676`, `n677`, `n678`.

This tranche advances dogfood review only. It does not create applyable hover decisions.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 387 |
| token_only_override | 159 |
| known_defect | 8 |

Routes:
| route | rows |
|---|---:|
| renderer_requirement | 320 |
| repair_candidate | 121 |
| blocker_queue_row | 113 |

Repair-preview-ready rows: `0`.

## Review Packets

Bounded reviewer packets were generated under `out/standard-tranche-vn13-20260627/`.
The committed inventory is a compact representative sample, not the full
packet output. It includes renderer-only rows plus explicit component-only,
finite-form, suffix, relation, and nominal/POS leakage examples so regression
gates can prove the lane boundaries without committing the full generated set.

All reviewed rows keep `may_apply_live:false`.

## Dominant Findings

VN-13 surfaced repeated classes:
- finite verb rows such as `أَحْرَصَ`, `حَرَصْتَ`, `يُخَٰدِعُونَ`, and `صَبَبْنَا` need exact form, voice/aspect, subject/agreement, and mood where governed before entry prose can become learner hover wording;
- suffix-bearing rows such as `سُهُولِهَا`, `نُورَهُۥ`, `سَمْكَهَا`, `لَأَعْنَتَكُمْ`, and `ٱقْتَرَفْتُمُوهَا` require attached object or possessor/reference contribution to stay visible;
- nominal/POS leakage appears where verb-entry family prose touches lexical nouns, plurals, verbal nouns, or adjective-like forms, with stronger VN-13 fixtures from `مَطَرَ`, `طَٰٓئِرٍۢ`, `عَجَلٍۢ`, and `إِعْصَارٌۭ`;
- component-only rows such as `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `فَصَبَّ`, and `وَخَابَ` improve routing but remain below whole-token certification and cannot create propagation-safe decisions;
- preposition/comparison and attached relation rows such as `بِمُصْرِخِكُمْ` require nahw review for function, attachment, or mood effects;
- renderer-only rows still need rich metadata but do not create applyable hover repairs by themselves.

## Compact Controller Table

| loc | surface | current gloss | defect class | state movement | next gate |
|---|---|---|---|---|---|
| 19:24:10 | `سَرِيًّۭا` | a moving stream | missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 7:74:3 | `سُهُولِهَا` | plains | missing_rich_renderer_segments;suffix_or_attached_pronoun_requires_visible_accounting | token_only_override -> repair_candidate | two_vote_exact_address_review |
| 2:264:21 | `صَفْوَانٍ` | (barren) rock | missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 18:17:17 | `فَجْوَةٍۢ` | open space | missing_rich_renderer_segments | token_only_override -> renderer_requirement | rich_renderer_metadata_backfill |
| 73:14:3 | `كَثِيبًا` | pile of sand | missing_rich_renderer_segments | token_only_override -> renderer_requirement | rich_renderer_metadata_backfill |
| 100:4:3 | `نَقْعًۭا` | (clouds of) dust | missing_rich_renderer_segments | token_only_override -> renderer_requirement | rich_renderer_metadata_backfill |
| 2:19:4 | `ٱلسَّمَآءِ` | sky, heavens | article_definiteness_requires_rich_segments;missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 2:22:10 | `ٱلسَّمَآءِ` | sky, heavens | article_definiteness_requires_rich_segments;missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 2:29:12 | `ٱلسَّمَآءِ` | sky, heavens | article_definiteness_requires_rich_segments;missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 2:59:15 | `ٱلسَّمَآءِ` | sky, heavens | article_definiteness_requires_rich_segments;missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 2:107:7 | `ٱلسَّمَٰوَٰتِ` | sky, heavens | article_definiteness_requires_rich_segments;missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |
| 2:116:10 | `ٱلسَّمَٰوَٰتِ` | sky, heavens | article_definiteness_requires_rich_segments;missing_rich_renderer_segments | populated_uncertified -> renderer_requirement | rich_renderer_metadata_backfill |

## Skill Impact

Committed sample: `qamus/examples/full_corpus_dogfood_vn13_skill_impact.sample.jsonl`

Rows:
- `finite_verb_dictionary_gloss_leakage`: 188 rows, updates `sarf/procedures/verb-form-and-mood-review.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `verb_object_suffix_or_attached_pronoun_not_visible`: 54 rows, updates `sarf/procedures/clitic-and-host-morphology.md, nahw/procedures/pronoun-attachment.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl, nahw/evals/suffix-pronoun-eval.jsonl`.
- `verb_entry_nominal_or_pos_leakage`: 52 rows, updates `sarf/procedures/nominal-derivative-decision.md`, regressions `sarf/evals/nominal-derivative-error-eval.jsonl`.
- `preposition_or_attached_relation_requires_nahw_review`: 40 rows, updates `nahw/procedures/preposition-pronoun.md, nahw/procedures/pp-attachment-review.md`, regressions `nahw/evals/particle-function-eval.jsonl, nahw/evals/irab-polysemy-eval.jsonl`.
- `component_only_candidate_no_whole_token_propagation`: 62 rows, updates `sarf/procedures/clitic-and-host-morphology.md, sarf/procedures/verb-form-and-mood-review.md`, regressions `sarf/evals/false-clitic-split-eval.jsonl`.
- `rich_renderer_missing_segments_only`: 320 rows, updates `none`, regressions `tools/check_regressions.py`. No-op reason: Rows whose only issue is missing_rich_renderer_segments or article display metadata are renderer backfill. They do not force a sarf/nahw rule unless form, suffix, function, POS, or attachment is implicated.

Repair-preview-ready remains `0`: this tranche did not run MCP/iʿrāb review, external source triangulation, two-vote adjudication, global grammar gates, owner approval, or apply planning.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn13_production_bug_lesson.sample.jsonl`

Lesson rows cover finite verb dictionary leakage, attached pronoun omission, nominal/POS leakage, preposition/attached relation review, and component-only overreach.

## Next Tranche

VN-14 should cover verbs `v633` through `v677` and nouns `n696` through `n745`.
