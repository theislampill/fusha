# VN-RICH-20 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-20 converts the twentieth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn20-20260627.md` and the committed VN-20 samples as canonical input.

Source dogfood batch:

- verbs `v903` through `v947`
- nouns `n996` through `n1045`
- `1101` live hover rows reviewed in the original dogfood tranche
- `1088` whole-token candidate rows in the original dogfood tranche
- `13` component-only evidence rows in the original dogfood tranche
- `0` repair-preview-ready rows in the original dogfood tranche

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_20_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_20_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `53:48:4` | `وَأَقْنَىٰ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `53:34:3` | `وَأَكْدَىٰٓ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `9:35:7` | `فَتُكْوَىٰ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `37:142:1` | `فَٱلْتَقَمَهُ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V+PRON:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `25:7:9` | `ٱلْأَسْوَاقِ` | `rich_candidate` | Readable string needs rich segment display before certification. | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `28:15:17` | `عَدُوِّهِۦ` | `rich_candidate` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | human_source_review_required |
| `28:15:25` | `عَدُوِّهِۦ` | `rich_candidate` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | human_source_review_required |
| `2:158:2` | `ٱلصَّفَا` | `rich_candidate` | Readable string needs rich segment display before certification. | `ART+N:UNKNOWN:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `21:11:2` | `قَصَمْنَا` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:PERFECT:UNKNOWN+PRON:TOKEN-ONLY` | two_vote_required |
| `18:77:17` | `يَنقَضَّ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `11:44:6` | `أَقْلِعِى` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `19:59:4` | `خَلْفٌ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `28:11:7` | `جُنُبٍۢ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `67:15:9` | `مَنَاكِبِهَا` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `2:182:9` | `بَيْنَهُمْ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `2:188:4` | `بَيْنَكُم` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `2:213:32` | `بَيْنَهُمْ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `3:123:4` | `بِبَدْرٍ` | `token_only_override` | Preposition-host row needs exact attachment review before rich certification. | `P+N:GEN:TOKEN-ONLY` | two_vote_required |
| `3:96:7` | `بِبَكَّةَ` | `token_only_override` | Preposition-host row needs exact attachment review before rich certification. | `P+N:GEN:TOKEN-ONLY` | two_vote_required |
| `23:20:5` | `سَيْنَآءَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `95:2:2` | `سِينِينَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `20:12:9` | `طُوًۭى` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `55:33:9` | `أَقْطَارِ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `5:95:26` | `ٱلْكَعْبَةِ` | `token_only_override` | Readable string needs rich segment display before certification. | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | two_vote_required |
| `58:11:9` | `ٱلْمَجَٰلِسِ` | `token_only_override` | Readable string needs rich segment display before certification. | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | two_vote_required |
| `11:44:13` | `ٱلْجُودِىِّ` | `token_only_override` | Readable string needs rich segment display before certification. | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | two_vote_required |
| `48:24:9` | `مَكَّةَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `21:96:3` | `حَدَبٍ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `9:25:8` | `حُنَيْنٍ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `28:30:3` | `شَاطِئِ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `33:26:8` | `صَيَاصِيهِمْ` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `2:198:12` | `عَرَفَٰتٍۢ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `9:25:5` | `مَوَاطِنَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `2:68:19` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:97:14` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:102:40` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:136:3` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:164:38` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:213:15` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:224:10` | `بَيْنَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |

No row is `rich_certified`. VN-20 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

State counts in this sample:

- `pending`: 4
- `rich_candidate`: 17
- `token_only_override`: 19

## State Transitions

- `component-only evidence -> pending component-only rich metadata`: `وَأَقْنَىٰ`, `وَأَكْدَىٰٓ`, `فَتُكْوَىٰ`, and `فَٱلْتَقَمَهُ`.
- `finite verb strings -> exact-address rich metadata`: `قَصَمْنَا`, `يَنقَضَّ`, `أَقْلِعِى`, and the component-only verb rows stay gated behind source/two-vote review.
- `suffix-bearing rows -> token-only rich metadata`: `مَنَاكِبِهَا`, `بَيْنَهُمْ`, `بَيْنَكُم`, `عَدُوِّهِۦ`, and `صَيَاصِيهِمْ` keep visible suffix contribution gated.
- `relation-sensitive location/proper rows -> token-only rich metadata`: `بِبَدْرٍ`, `بِبَكَّةَ`, `مَكَّةَ`, `سَيْنَآءَ`, `سِينِينَ`, `طُوًۭى`, `ٱلْكَعْبَةِ`, and similar rows remain exact-address candidates.
- `renderer-only rows -> rich candidate metadata`: rows such as `ٱلْأَسْوَاقِ`, `ٱلصَّفَا`, `عَرَفَٰتٍۢ`, and repeated `بَيْنَ` rows keep rich display requirements without claiming live renderer support.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

- `article_definiteness_requires_rich_segments`: 5 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `component_only_candidate_no_whole_token_propagation`: 4 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `finite_verb_dictionary_gloss_or_form_review`: 7 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `missing_rich_renderer_segments`: 40 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `noun_hover_may_leak_verb_infinitive`: 2 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `preposition_or_attached_relation_requires_nahw_review`: 6 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `suffix_or_attached_pronoun_requires_visible_accounting`: 6 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.
- `surface_family_requires_token_only_override`: 19 sampled rows; uses existing dogfood skill/curriculum routing from VN-20, with no new sarf/nahw edit required in this tranche.

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, suffix pronouns, relation-sensitive nominal roles, preposition/governor review, component-only blockers, and renderer requirements.

Renderer requirements: this tranche emits segment expectations for prefixed verbs, attached-pronoun rows, article-bearing nouns, proper/location nouns, between/side/location relation nouns, and rows whose current English string cannot teach composition by itself.

Future tranche routing: prioritize exact-address finite verbs, suffix-heavy relation nouns, preposition-host location rows, and component-only rows before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_20_standard.sample.jsonl
run the internal-only evidence sidecar scan
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_sarf_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_nahw_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/run_grammar_evals.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/check_regressions.py
git diff --check
```
