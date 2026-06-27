# Full-Corpus Dogfood Particle Tranche - Remaining 67 (2026-06-27)

Status: repo-only, read-only dogfood processing. No live Qamus mutation, no WBW rebuild, no service restart, no mirror sync, no hover apply, and no hover-coverage claim.

## Baseline

- Base commit: `c2e7169d6b6752126df2af8b72ea4846071cec46`
- Batch id: `full-corpus-dogfood-20260627-particle-remaining67`
- Top 33 high-impact particles were already handled in `qamus/reports/full-corpus-dogfood-particle-tranche-20260627.md`.
- This tranche selects the remaining 67 particle entries from the 100-particle matrix and excludes the top-33 except for shared defect-class regression pressure.

## Inventory Counts

- Remaining particle entries inventoried: 67
- Whole-token live hover rows: 4670
- Component-only evidence rows: 3
- Whole-token classes: `{"populated_uncertified": 4644, "token_only_override": 26}`
- Component-only classes: `{"known_defect": 3}`
- Function review buckets: `{"component_candidate_no_propagation": 3, "exact_address_certification": 26, "function_review_required": 3360, "interrogative_subordinator_review": 253, "negation_or_ma_function_review": 155, "subordinator_or_inna_review": 576, "temporal_condition_review": 300}`

## High-Yield Entry Families

| entry | particle | rows | class summary | controller route |
|---|---:|---:|---|---|
| `e7c05664fd33` | `مَنْ` | 1738 | `{"populated_uncertified": 1738}` | needs_nahw_review / strict surface split |
| `71ced968e7f8` | `إِنْ` | 577 | `{"populated_uncertified": 577}` | needs_nahw_review / strict surface split |
| `91a3a5a825a1` | `الَّذِينَ` | 516 | `{"populated_uncertified": 515, "token_only_override": 1}` | exact-address token review; no family propagation |
| `a6cc21000bae` | `ثُمَّ` | 205 | `{"populated_uncertified": 205}` | needs_nahw_review / strict surface split |
| `e8da25fd56d5` | `ثَمَّ` | 205 | `{"populated_uncertified": 205}` | needs_nahw_review / strict surface split |
| `cc6e15fd47bf` | `إِذَا` | 150 | `{"populated_uncertified": 150}` | needs_nahw_review / strict surface split |
| `a22616256978` | `إِذًا` | 150 | `{"populated_uncertified": 150}` | needs_nahw_review / strict surface split |
| `ba6c4a322d27` | `هُوَ` | 150 | `{"populated_uncertified": 149, "token_only_override": 1}` | exact-address token review; no family propagation |
| `b851675d8484` | `هُمْ` | 143 | `{"component:known_defect": 1, "populated_uncertified": 142}` | renderer requirement; component-only no propagation |
| `9389cc128849` | `لِمَ` | 115 | `{"populated_uncertified": 115}` | needs_nahw_review / strict surface split |
| `d8b8169ae3d3` | `أَمْ` | 82 | `{"populated_uncertified": 82}` | needs_nahw_review / strict surface split |
| `4aeb20b7beca` | `قَدْ` | 80 | `{"populated_uncertified": 79, "token_only_override": 1}` | exact-address token review; no family propagation |
| `8ce3f76e3e4c` | `بَلْ` | 73 | `{"populated_uncertified": 73}` | needs_nahw_review / strict surface split |
| `d5a538513041` | `كَمَا` | 46 | `{"populated_uncertified": 46}` | needs_nahw_review / strict surface split |
| `05b7e99ba847` | `أَنْتُمْ` | 44 | `{"populated_uncertified": 42, "token_only_override": 2}` | exact-address token review; no family propagation |

## State Transitions

- `populated_uncertified -> needs_nahw_review`: entry-pair and function-family rows such as `مَنْ`, `إِنْ`, `ثُمَّ/ثَمَّ`, `إِذَا/إِذًا`, `هَلْ`, `مَاذَا`, `أَنَا/أَنَّا`.
- `token_only_override -> exact_address_certification_packet`: 26 rows such as `لِكَيْلَا`, `لَيْتَنِي`, `إِيَّاكَ`, and `لَكُنَّا`; none are propagation-ready.
- `known_defect -> renderer_requirement + no_propagation`: 3 component-only rows (`فَأَهْلَكْنَاهُمْ`, `يَسْـَٔلُكَ`) remain internal evidence only.
- `populated_uncertified -> documented_no_op`: repeated classes already covered by `مَن/مِن`, `لَم/لِمَ`, `أَم/أُمّ`, `كَلَّا/كُلّ`, `نَعَم/نِعْمَ` rules gained regression pressure but not duplicate doctrine.

## Skill Impact

- Updated nahw particle routing for `إِذَا/إِذًا`, `ثُمَّ/ثَمَّ`, `هَلْ`, `مَاذَا`, `كَيْ/لِكَيْلَا`, `لَيْتَنِي`, and `أَنَا/أَنَّا`.
- Updated sarf clitic/homograph guidance for component candidates, suffix-bearing particles, `لَكُنَّا/لَكِنْ`, `قَد/قُدَّ`, and `نَعَم/نِعْمَ`.
- Added particle-function and false-clitic regression fixtures to make these gates executable.
- Added production-bug lesson rows for repeated defect classes; all rows keep `may_apply_live:false`.

## Zero-Row Entries

17 remaining particle entries had matrix counts but no matching whole/component live rows in this tranche inventory. They are not inferred complete; they require source-audit regeneration or separate lookup before any conclusion:

`حَتَّى`, `بَلَى`, `ذَانِكَ`, `أَ`, `أُولَئِكَ`, `هَذِهِ`, `إِيَّاكُمْ`, `كَأَيِّن`, `هَؤُلَاءِ`, `هَذَا`, `تَـ`, `مَتَى`, `هَذَانِ`, `لَاتَ`, `اللَّذَانِ`, `سَـ`, `إِيَّايَ`

## Committed Samples

- `qamus/examples/full_corpus_dogfood_particle_remaining67_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_particle_remaining67_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_particle_remaining67_production_bug_lesson.sample.jsonl`

Full generated row artifacts remain under ignored `out/particle-dogfood-remaining-20260627/`.

## Not Changed

- Live Qamus data and public pages.
- WBW lookup/build artifacts.
- Mirror repository state.
- Hover coverage or closure ledgers.
