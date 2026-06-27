# Full-Corpus Dogfood VN-14 - 2026-06-27

Status: repo-only dogfood tranche. No live Qamus data, WBW artifact, service,
mirror, or hover decision ledger was mutated.

## Scope

- Verbs: `v633-v677`
- Nouns: `n696-n745`
- Entries inventoried: 95
- Live hover rows in tranche: 262
- Whole-token rows: 213
- Component-only evidence rows: 49

Full local evidence was generated under:

`out/standard-tranche-vn14-20260627/`

Committed review slices:

- `qamus/examples/full_corpus_dogfood_vn14_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn14_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn14_production_bug_lesson.sample.jsonl`

## Classification

| Classification | Count |
|---|---:|
| `known_defect` | 1 |
| `populated_uncertified` | 142 |
| `token_only_override` | 119 |

## Issue Counts

| Issue | Count |
|---|---:|
| `article_definiteness_requires_rich_segments` | 68 |
| `component_only_candidate_no_whole_token_propagation` | 49 |
| `finite_verb_dictionary_gloss_or_form_review` | 94 |
| `missing_rich_renderer_segments` | 261 |
| `noun_hover_may_leak_verb_infinitive` | 1 |
| `preposition_or_attached_relation_requires_nahw_review` | 8 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 21 |
| `surface_family_requires_token_only_override` | 119 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 52 |

## State Transitions

| Transition | Count |
|---|---:|
| `blocker_queue_row` | 49 |
| `renderer_requirement` | 112 |
| `repair_candidate` | 101 |

All VN-14 rows have `may_apply_live:false`. Repair candidates are candidate
packets only; they are not owner-authorized live decisions.

## Skill Impact

VN-14 produced grammar dogfood for three active skill areas:

- finite verb dictionary-gloss leakage, routed to
  `sarf/procedures/verb-form-and-mood-review.md`;
- visible suffix/object/possessor accounting, routed to
  `sarf/procedures/clitic-and-host-morphology.md` and
  `nahw/procedures/pronoun-attachment.md`;
- verb-entry nominal/POS leakage, routed to
  `sarf/procedures/nominal-derivative-decision.md`.

Renderer-only rows are deliberately no-op for sarf/nahw. They route to rich
renderer metadata backfill unless a suffix, finite form, function, POS, or
attachment defect is also present.

## Representative Rows

| Loc | Surface | Current gloss | Route |
|---|---|---|---|
| `quran:22:18:17` | `وَٱلشَّجَرُ` | `and + the trees` | `component_only_blocker` |
| `quran:16:80:19` | `أَصْوَافِهَا` | `wool` | `two_vote_exact_address_review` |
| `quran:68:28:2` | `أَوْسَطُهُمْ` | `central, best, upright, moderate` | `two_vote_exact_address_review` |
| `quran:50:16:6` | `تُوَسْوِسُ` | `to whisper` | `rich_metadata_plus_exact_address_review` |
| `quran:6:141:19` | `ثَمَرِهِۦٓ` | `to fruit; bear fruit` | `rich_metadata_plus_exact_address_review` |
| `quran:12:59:3` | `بِجَهَازِهِمْ` | `to supply/provide` | `component_only_blocker` |
| `quran:22:73:4` | `يَطْلُبُهُۥ` | `to request, demand` | `two_vote_exact_address_review` |
| `quran:49:11:7` | `يَلْمِزُكَ` | `to defame, speak ill of` | `two_vote_exact_address_review` |

## Zero-Row Entries

The following tranche entries had no live hover rows in the current audit
snapshot:

`n710`, `n712`, `n717`, `n719`, `n720`, `n723`, `n724`, `n725`, `n728`,
`n731`, `n734`, `n735`, `n736`, `n737`.

## Next Tranche

VN-15 should cover:

- verbs: `v678-v722`
- nouns: `n746-n795`

Keep the same rule: candidate packets and skill dogfood only, no live apply.
