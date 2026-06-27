# Full-Corpus Hover Dogfood VN-20 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service, mirror, or hover decision ledger was changed.

## Scope

- Verbs: `v903` through `v947`
- Nouns: `n996` through `n1045`
- Entries inventoried: 95
- Live hover rows reviewed: 1101
- Whole-token candidate rows: 1088
- Component-only evidence rows: 13
- Repair-preview-ready rows: 0
- `may_apply_live`: false for every sampled row
- Zero-row entries: `v912`, `v932`, `v933`, `n1005`, `n1006`, `n1007`, `n1008`, `n1012`, `n1014`, `n1015`, `n1018`

## Classification Counts

| item | count |
|---|---:|
| `populated_uncertified` | 983 |
| `token_only_override` | 116 |
| `pending/blocker` | 2 |

## Issue Counts

| item | count |
|---|---:|
| `missing_rich_renderer_segments` | 1101 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 356 |
| `finite_verb_dictionary_gloss_or_form_review` | 176 |
| `surface_family_requires_token_only_override` | 116 |
| `article_definiteness_requires_rich_segments` | 27 |
| `preposition_or_attached_relation_requires_nahw_review` | 15 |
| `component_only_candidate_no_whole_token_propagation` | 13 |
| `noun_hover_may_leak_verb_infinitive` | 2 |

## Reviewer Findings

Verb-sarf review kept finite and component evidence gated:
- finite/form rows include `قَصَمْنَا`, `يَنقَضَّ`, `أَقْلِعِى`, `وَأَقْنَىٰ`, `ٱنكَدَرَتْ`, `وَأَكْدَىٰٓ`, `كُشِطَتْ`, `يَكْلَؤُكُم`;
- component-only rows include `وَأَقْنَىٰ`, `وَأَكْدَىٰٓ`, `فَتُكْوَىٰ`, `فَٱلْتَقَمَهُ`, `فَأَلْهَمَهَا`, `لَمَسَخْنَٰهُمْ`, `وَنَمِيرُ`, `وَٱنْحَرْ`.

Nahw-function review found repeated exact-address gates:
- suffix or relation rows include `ٱلْأَسْوَاقِ`, `سَيْنَآءَ`, `سِينِينَ`, `طُوًۭى`, `أَقْطَارِ`, `ٱلْكَعْبَةِ`, `بِبَدْرٍ`, `بِبَكَّةَ`, `مَكَّةَ`, `ٱلْمَجَٰلِسِ`;
- token-only override rows remain exact-address candidates where family-level propagation is unsafe without compatible grammar reasoning.

## State Transitions

VN-20 did not produce apply-ready rows. It produced durable read-only state movement:
- `blocker_queue_row`: 13
- `renderer_requirement`: 625
- `repair_candidate`: 463

Component-only evidence remains `blocker_queue_row`; rich display gaps remain `renderer_requirement`; finite, suffix, relation, POS-sensitive, and token-family rows remain `repair_candidate` behind exact-address and two-vote/source gates.

## Skill Impact

- `article_definiteness_requires_rich_segments` no-op for sarf/nahw: sarf/procedures/clitic-and-host-morphology.md and sarf/evals/false-clitic-split-eval.jsonl (27 rows). Reason: renderer metadata requirement only; article segmentation already covered by sarf clitic-host procedure
- `component_only_candidate_no_whole_token_propagation` updates/reuses sarf/procedures/clitic-and-host-morphology.md and sarf/evals/false-clitic-split-eval.jsonl (13 rows).
- `finite_verb_dictionary_gloss_or_form_review` updates/reuses sarf/procedures/verb-form-and-mood-review.md and sarf/evals/false-clitic-split-eval.jsonl (176 rows).
- `missing_rich_renderer_segments` no-op for sarf/nahw: qamus/reports/full-corpus-dogfood-vn20-20260627.md and tools/check_regressions.py (1101 rows). Reason: renderer metadata requirement only; no sarf/nahw rule change required
- `noun_hover_may_leak_verb_infinitive` updates/reuses sarf/procedures/nominal-derivative-decision.md and sarf/evals/nominal-derivative-error-eval.jsonl (2 rows).
- `preposition_or_attached_relation_requires_nahw_review` updates/reuses nahw/procedures/preposition-pronoun.md;nahw/procedures/pp-attachment-review.md and nahw/evals/particle-function-eval.jsonl (15 rows).
- `suffix_or_attached_pronoun_requires_visible_accounting` updates/reuses nahw/procedures/pronoun-attachment.md and nahw/evals/suffix-pronoun-eval.jsonl (356 rows).
- `surface_family_requires_token_only_override` updates/reuses nahw/procedures/token-only-overrides.md and nahw/evals/irab-polysemy-eval.jsonl (116 rows).

No-op reason for live Qamus: all rows remain read-only candidates, blockers, or renderer requirements. None pass the global grammar, row-level, two-vote, source-triangulation, and rich-certification gates required for live apply.

## Committed Samples

- `qamus/examples/full_corpus_dogfood_vn20_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn20_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn20_production_bug_lesson.sample.jsonl`

Full generated VN-20 artifacts remain under ignored `out/` and are not a live source of truth.
