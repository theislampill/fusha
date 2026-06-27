# Full-Corpus Hover Dogfood VN-17 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service, mirror, or hover decision ledger was changed.

## Scope

- Verbs: `v768` through `v812`
- Nouns: `n846` through `n895`
- Entries inventoried: 95
- Live hover rows reviewed: 136
- Whole-token candidate rows: 112
- Component-only evidence rows: 24
- Repair-preview-ready rows: 0
- `may_apply_live`: false for every sampled row

## Classification Counts

| classification | count |
|---|---:|
| `pending/blocker` | 3 |
| `populated_uncertified` | 41 |
| `token_only_override` | 92 |

## Issue Counts

| issue | count |
|---|---:|
| `article_definiteness_requires_rich_segments` | 24 |
| `component_only_candidate_no_whole_token_propagation` | 24 |
| `finite_verb_dictionary_gloss_or_form_review` | 38 |
| `missing_rich_renderer_segments` | 136 |
| `noun_hover_may_leak_verb_infinitive` | 1 |
| `preposition_or_attached_relation_requires_nahw_review` | 3 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 41 |
| `surface_family_requires_token_only_override` | 92 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 14 |

## Reviewer Findings

Verb-sarf review kept finite/form rows separate from nominal/POS and component-only evidence:
- finite or form-sensitive rows: `رُجَّتِ`, `أَرْكَسَهُم`, `أُرْكِسُوا`, `زُحْزِحَ`, `سُعِدُوا`, `تَشْخَصُ`, `يَشْوِى`, `صَغَتْ`;
- nominal, derivative, or POS-sensitive rows near verb entries: `رَجًّا`, `زَلَقًا`, `سَٰبِغَٰتٍۢ`, `وَسَعِيدٌۭ`, `شَٰخِصَةٌ`, `شُغُلٍۢ`, `ظُفُرٍ`, `عَبَثًۭا`;
- component-only evidence rows: `بِمُزَحْزِحِهِۦ`, `لَيُزْلِقُونَكَ`, `وَأَسْبَغَ`, `وَسَعِيدٌۭ`, `وَيَسْفِكُ`, `أَشْكُوا۟`, `وَاضْمُمْ`, `وَٱضْمُمْ`.

Nahw-function review kept exact-address rows gated:
- attached suffix or pronoun rows: `نَافِلَةًۭ`, `أَصْلُهَا`, `أُصُولِهَا`, `مَضَاجِعِهِمْ`, `غِطَآءَكَ`, `كُرْسِيُّهُ`, `ٱلْخِيَامِ`, `زَيْتُهَا`;
- preposition or attached-relation rows: `بِمُزَحْزِحِهِۦ`, `وَلِيُمَحِّصَ`;
- surface-family matches remain token-only when context, referent, or morphosyntax changes the learner contribution.

## State Transitions

VN-17 did not produce apply-ready rows. It produced durable read-only state movement:
- `blocker_queue_row`: 24
- `renderer_requirement`: 8
- `repair_candidate`: 104

Component-only evidence remains `blocker_queue_row`; rich display gaps remain `renderer_requirement`; finite, suffix, relation, or POS-sensitive rows remain `repair_candidate` behind exact-address and two-vote/source gates.

## Skill Impact

- `article_definiteness_requires_rich_segments` no-op for sarf/nahw: renderer metadata requirement only; article segmentation already covered by sarf clitic-host procedure (24 rows).
- `component_only_candidate_no_whole_token_propagation` updates/reuses `sarf/procedures/clitic-and-host-morphology.md` and `sarf/evals/false-clitic-split-eval.jsonl` (24 rows).
- `finite_verb_dictionary_gloss_or_form_review` updates/reuses `sarf/procedures/verb-form-and-mood-review.md` and `sarf/evals/false-clitic-split-eval.jsonl` (38 rows).
- `missing_rich_renderer_segments` no-op for sarf/nahw: renderer metadata requirement only; no sarf/nahw rule change required (136 rows).
- `noun_hover_may_leak_verb_infinitive` updates/reuses `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` (1 rows).
- `preposition_or_attached_relation_requires_nahw_review` updates/reuses `nahw/procedures/preposition-pronoun.md;nahw/procedures/pp-attachment-review.md` and `nahw/evals/particle-function-eval.jsonl` (3 rows).
- `suffix_or_attached_pronoun_requires_visible_accounting` updates/reuses `nahw/procedures/pronoun-attachment.md` and `nahw/evals/suffix-pronoun-eval.jsonl` (41 rows).
- `surface_family_requires_token_only_override` updates/reuses `nahw/procedures/token-only-overrides.md` and `nahw/evals/irab-polysemy-eval.jsonl` (92 rows).
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review` updates/reuses `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` (14 rows).

No-op reason for live Qamus: all rows remain read-only candidates, blockers, or renderer requirements. None pass the global grammar, row-level, two-vote, source-triangulation, and rich-certification gates required for live apply.

## Committed Samples

- `qamus/examples/full_corpus_dogfood_vn17_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn17_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn17_production_bug_lesson.sample.jsonl`

Full generated VN-17 artifacts remain under ignored `out/` and are not a live source of truth.
