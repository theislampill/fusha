# Full-Corpus Hover Dogfood VN-18 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service, mirror, or hover decision ledger was changed.

## Scope

- Verbs: `v813` through `v857`
- Nouns: `n896` through `n945`
- Entries inventoried: 95
- Live hover rows reviewed: 938
- Whole-token candidate rows: 916
- Component-only evidence rows: 22
- Repair-preview-ready rows: 0
- `may_apply_live`: false for every sampled row

## Classification Counts

| classification | count |
|---|---:|
| `pending/blocker` | 28 |
| `populated_uncertified` | 761 |
| `token_only_override` | 149 |

## Issue Counts

| issue | count |
|---|---:|
| `article_definiteness_requires_rich_segments` | 52 |
| `component_only_candidate_no_whole_token_propagation` | 22 |
| `finite_verb_dictionary_gloss_or_form_review` | 32 |
| `missing_rich_renderer_segments` | 932 |
| `noun_hover_may_leak_verb_infinitive` | 5 |
| `preposition_or_attached_relation_requires_nahw_review` | 17 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 148 |
| `surface_family_requires_token_only_override` | 149 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 2 |

## Reviewer Findings

Verb-sarf review kept finite and component evidence gated:
- finite/form rows include `نَكَصَ`, `تَنكِصُونَ`, `يُهْرَعُونَ`, `يَهِيجُ`, `يَهِيمُونَ`, `مَّوْبِقًۭا`, and `يُوبِقْهُنَّ`;
- component-only rows include `بِٱلْمَعْرُوفِ`, `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`, `وَٱلْجِبَالُ`, `وَٱلشَّجَرُ`, and `يَـُٔودُهُۥ`;
- noun/POS rows include `ثَانِىَ`, `كُلًّۭا`, `أُو۟لِى`, `كُرْهٌۭ`, `كَرِهَ`, `مَّوْبِقًۭا`, and `وَاجِفَةٌ`.

Nahw-function review found repeated exact-address gates:
- suffix rows around `أَحَدُهُمْ`, `أَحَدِهِم`, `أَحَدِهِمَا`, `أَحَدُهُمَآ`, `أَحَدَكُم`, and `يُوبِقْهُنَّ`;
- bāʾ/wāw/function rows around `بِٱلْمَعْرُوفِ` and the 22:18 oath/conjunction-style cluster;
- token-only override rows where `أَحَد`, `وَٰحِد`, or inflected/suffixed variants cannot inherit one family gloss without exact context.

## State Transitions

VN-18 did not produce apply-ready rows. It produced durable read-only state movement:
- `blocker_queue_row`: 22
- `renderer_requirement`: 658
- `repair_candidate`: 258

Component-only evidence remains `blocker_queue_row`; rich display gaps remain `renderer_requirement`; finite, suffix, relation, POS-sensitive, and token-family rows remain `repair_candidate` behind exact-address and two-vote/source gates.

## Skill Impact

- `article_definiteness_requires_rich_segments` no-op for sarf/nahw: renderer metadata requirement only; article segmentation already covered by sarf clitic-host procedure (52 rows).
- `component_only_candidate_no_whole_token_propagation` updates/reuses `sarf/procedures/clitic-and-host-morphology.md` and `sarf/evals/false-clitic-split-eval.jsonl` (22 rows).
- `finite_verb_dictionary_gloss_or_form_review` updates/reuses `sarf/procedures/verb-form-and-mood-review.md` and `sarf/evals/false-clitic-split-eval.jsonl` (32 rows).
- `missing_rich_renderer_segments` no-op for sarf/nahw: renderer metadata requirement only; no sarf/nahw rule change required (932 rows).
- `noun_hover_may_leak_verb_infinitive` updates/reuses `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` (5 rows).
- `preposition_or_attached_relation_requires_nahw_review` updates/reuses `nahw/procedures/preposition-pronoun.md;nahw/procedures/pp-attachment-review.md` and `nahw/evals/particle-function-eval.jsonl` (17 rows).
- `suffix_or_attached_pronoun_requires_visible_accounting` updates/reuses `nahw/procedures/pronoun-attachment.md` and `nahw/evals/suffix-pronoun-eval.jsonl` (148 rows).
- `surface_family_requires_token_only_override` updates/reuses `nahw/procedures/token-only-overrides.md` and `nahw/evals/irab-polysemy-eval.jsonl` (149 rows).
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review` updates/reuses `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` (2 rows).

No-op reason for live Qamus: all rows remain read-only candidates, blockers, or renderer requirements. None pass the global grammar, row-level, two-vote, source-triangulation, and rich-certification gates required for live apply.

## Committed Samples

- `qamus/examples/full_corpus_dogfood_vn18_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn18_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn18_production_bug_lesson.sample.jsonl`

Full generated VN-18 artifacts remain under ignored `out/` and are not a live source of truth.
