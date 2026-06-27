# Full-Corpus Dogfood Batch — Nominal POS Leakage

Status: read-only dogfood processing. No live Qamus data, WBW artifact, mirror repo, service, rebuild, or hover apply was changed.

## Source Packet

- Packet: `out/full-corpus-dogfood-82c63dd-20260627-004825/review-packets/issue_nominal_pos_top100.jsonl`
- Packet shape: 100 prioritized rows; 1 `known_defect`, 99 `token_only_override`.
- This batch processed the first controller slice, focusing on populated hovers whose English shape leaked a verb/root infinitive onto a nominal, adjectival, or participial token.

## Controller Table

| loc | surface | current gloss | defect class | expected token contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 1:1:3 | الرَّحْمَٰنِ | to show mercy and compassion to | populated_hover_pos_leakage | nominal/name-like mercy attribute | token_only_override -> needs_sarf_review | token-only two-vote |
| 1:1:4 | الرَّحِيمِ | to show mercy and compassion to | populated_hover_pos_leakage | nominal/name-like mercy quality | token_only_override -> needs_sarf_review | token-only two-vote |
| 1:4:3 | ٱلدِّينِ | to be bound by an authority such as faith or judgment | populated_hover_pos_leakage | religion/judgment/recompense noun | token_only_override -> needs_sarf_review | token-only two-vote |
| 1:6:3 | ٱلْمُسْتَقِيمَ | to be steadfast in uprightness | populated_hover_pos_leakage | straight/upright descriptor | token_only_override -> needs_sarf_review | token-only two-vote |
| 2:5:8 | ٱلْمُفْلِحُونَ | to succeed | populated_hover_pos_leakage | the successful ones | token_only_override -> production_bug_lesson + sarf_regression_fixture | token-only two-vote |
| 2:6:4 | سَوَآءٌ | to be in the middle, with two even sides | populated_hover_pos_leakage | equal/alike/same in context | token_only_override -> needs_sarf_review + needs_nahw_review | token-only two-vote |
| 2:7:9 | غِشَٰوَةٌۭ | to cover | populated_hover_pos_leakage | a covering/cover | token_only_override -> needs_sarf_review | token-only two-vote |
| 2:7:12 | عَظِيمٌۭ | to be great | populated_hover_pos_leakage | great/immense quality | token_only_override -> needs_sarf_review | token-only two-vote |
| 2:22:7 | بِنَآءًۭ | to build | populated_hover_pos_leakage | a structure/building/canopy | token_only_override -> production_bug_lesson + sarf_regression_fixture | token-only two-vote |
| 2:25:31 | مُّطَهَّرَةٌۭ | to purify | populated_hover_pos_leakage | purified | token_only_override -> production_bug_lesson + sarf_regression_fixture | token-only two-vote |
| 2:30:6 | جَاعِلٌۭ | to make | populated_hover_pos_leakage | one who makes/places | token_only_override -> production_bug_lesson + sarf_regression_fixture | token-only two-vote |
| 2:36:16 | مُسْتَقَرٌّۭ | to settle | populated_hover_pos_leakage | dwelling/settling place or fixed term/contextual noun | token_only_override -> needs_sarf_review | token-only two-vote |

## Skill Impact

Updated sarf:

- `sarf/procedures/masdar-participle.md` now states that a populated hover is not shape certification and names `populated_hover_pos_leakage`.
- `sarf/drills/nominal-derivatives.md` now drills the live defect class with `ٱلْمُفْلِحُونَ`, `بِنَآءً`, `مُّطَهَّرَةٌ`, and `جَاعِلٌ`.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds `ND-025` through `ND-028`.
- `sarf/examples/qamus-regressions.jsonl` adds the repeated live defect patterns.

Updated nahw:

- `nahw/procedures/irab-case-mood.md` now explicitly rejects using case/iʿrāb to certify a verb-shaped hover on a nominal token. This is a handoff rule: nahw can decide role after sarf fixes the English shape.

Curriculum:

- `curriculum/drills/hover-composition-and-routing.md` now includes nominal POS leakage rows so the learner rejects populated but non-rich hovers.

## Production-Bug Lessons

Added `qamus/examples/dogfood_nominal_pos_production_bug_lesson.sample.jsonl` for:

- `quran:2:5:8` / `wbw:2:5:8` — `ٱلْمُفْلِحُونَ`
- `quran:2:22:7` / `wbw:2:22:7` — `بِنَآءًۭ`
- `quran:2:25:31` / `wbw:2:25:31` — `مُّطَهَّرَةٌۭ`
- `quran:2:30:6` / `wbw:2:30:6` — `جَاعِلٌۭ`

## No-Op Reasons

- No live repair preview is ready from this batch. All rows remain token-only/two-vote because the batch did not perform live source triangulation or owner-gated apply.
- Rows like `سَوَآءٌ` additionally need nahw/context review after sarf fixes the English shape.
- Some rows may ultimately be entry/sense repair candidates, but this batch intentionally stopped at read-only dogfood routing.

## Outputs

- `qamus/examples/full_corpus_dogfood_nominal_pos_batch_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_nominal_pos_production_bug_lesson.sample.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `sarf/examples/qamus-regressions.jsonl`
- `sarf/procedures/masdar-participle.md`
- `nahw/procedures/irab-case-mood.md`
- `sarf/drills/nominal-derivatives.md`
- `curriculum/drills/hover-composition-and-routing.md`

## Apply Status

`may_apply_live:false` for every row. This is row movement into validated next-state categories only:

- `token_only_override -> needs_sarf_review`
- `token_only_override -> needs_sarf_review + needs_nahw_review`
- `token_only_override -> production_bug_lesson + sarf_regression_fixture + skill_impact`

No hover coverage improvement is claimed.
