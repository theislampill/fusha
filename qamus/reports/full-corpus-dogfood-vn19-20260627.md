# Full-Corpus Hover Dogfood VN-19 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service, mirror, or hover decision ledger was changed.

## Scope

- Verbs: `v858` through `v902`
- Nouns: `n946` through `n995`
- Entries inventoried: 95
- Live hover rows reviewed: 654
- Whole-token candidate rows: 636
- Component-only evidence rows: 18
- Repair-preview-ready rows: 0
- `may_apply_live`: false for every sampled row
- Zero-row entries: `n947`, `n961`, `n965`, `n967`, `n978`, `n980`, `n990`

## Classification Counts

| classification | count |
|---|---:|
| `populated_uncertified` | 530 |
| `token_only_override` | 124 |

## Issue Counts

| issue | count |
|---|---:|
| `article_definiteness_requires_rich_segments` | 133 |
| `component_only_candidate_no_whole_token_propagation` | 18 |
| `finite_verb_dictionary_gloss_or_form_review` | 45 |
| `missing_rich_renderer_segments` | 654 |
| `noun_hover_may_leak_verb_infinitive` | 2 |
| `preposition_or_attached_relation_requires_nahw_review` | 116 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 29 |
| `surface_family_requires_token_only_override` | 124 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 1 |

## Reviewer Findings

Verb-sarf review kept finite and component evidence gated:
- finite/form rows include `تَذْهَلُ`, `تَذُودَانِ`, `أَذَاعُوا۟`, `رَبِحَت`, `يَرْتَعْ`, and `رَانَ`;
- component-only rows include `لَنَسْفَعًۢا`, `فَسَاهَمَ`, `فَشَرِّدْ`, `وَٱشْتَعَلَ`, and `لِيَسْحَتَكُم`;
- noun/POS rows include `ٱلسَّبْتِ` and `وَأَتْرَفْنَٰهُمْ`, where entry-family evidence is useful but not a whole-token certification.

Nahw-function review found repeated exact-address gates:
- suffix rows around `قِطَّنَا`, `يَوْمُكُمُ`, `يَوْمِكُمْ`, `يَوْمِهِمْ`, `أَطْرَافِهَا`, and `طَرْفُهُمْ`;
- preposition/relation-sensitive rows around `سَنَةٍۢ`, `سَنَةٍ`, and `سَنَةًۭ`, whose apparent noun gloss still needs case, i'rab, and relation review;
- token-only override rows where day/time, share, split-parts, and edge/side families cannot inherit a broad family gloss without exact address and context.

## State Transitions

VN-19 did not produce apply-ready rows. It produced durable read-only state movement:
- `blocker_queue_row`: 18
- `renderer_requirement`: 314
- `repair_candidate`: 322

Component-only evidence remains `blocker_queue_row`; rich display gaps remain `renderer_requirement`; finite, suffix, relation, POS-sensitive, and token-family rows remain `repair_candidate` behind exact-address and two-vote/source gates.

## Skill Impact

- `article_definiteness_requires_rich_segments` no-op for sarf/nahw: renderer metadata requirement only; article segmentation already covered by sarf clitic-host procedure (133 rows).
- `component_only_candidate_no_whole_token_propagation` updates/reuses `sarf/procedures/clitic-and-host-morphology.md` and `sarf/evals/false-clitic-split-eval.jsonl` (18 rows).
- `finite_verb_dictionary_gloss_or_form_review` updates/reuses `sarf/procedures/verb-form-and-mood-review.md` and `sarf/evals/false-clitic-split-eval.jsonl` (45 rows).
- `missing_rich_renderer_segments` no-op for sarf/nahw: renderer metadata requirement only; no sarf/nahw rule change required (654 rows).
- `noun_hover_may_leak_verb_infinitive` updates/reuses `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` (2 rows).
- `preposition_or_attached_relation_requires_nahw_review` updates/reuses `nahw/procedures/preposition-pronoun.md;nahw/procedures/pp-attachment-review.md` and `nahw/evals/particle-function-eval.jsonl` (116 rows).
- `suffix_or_attached_pronoun_requires_visible_accounting` updates/reuses `nahw/procedures/pronoun-attachment.md` and `nahw/evals/suffix-pronoun-eval.jsonl` (29 rows).
- `surface_family_requires_token_only_override` updates/reuses `nahw/procedures/token-only-overrides.md` and `nahw/evals/irab-polysemy-eval.jsonl` (124 rows).
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review` updates/reuses `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` (1 rows).

No-op reason for live Qamus: all rows remain read-only candidates, blockers, or renderer requirements. None pass the global grammar, row-level, two-vote, source-triangulation, and rich-certification gates required for live apply.

## Committed Samples

- `qamus/examples/full_corpus_dogfood_vn19_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn19_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn19_production_bug_lesson.sample.jsonl`

Full generated VN-19 artifacts remain under ignored `out/` and are not a live source of truth.
