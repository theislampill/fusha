# VN-RICH-19 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-19 converts the nineteenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn19-20260627.md` and the committed VN-19 samples as canonical input.

Source dogfood batch:

- verbs `v858` through `v902`
- nouns `n946` through `n995`
- `654` live hover rows reviewed in the original dogfood tranche
- `636` whole-token candidate rows and `18` component-only evidence rows
- `0` repair-preview-ready rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_19_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_19_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `20:130:17` | `وَأَطْرَافَ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `23:33:10` | `وَأَتْرَفْنَٰهُمْ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+UNK+PRON:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `96:15:5` | `لَنَسْفَعًۢا` | `pending` | Component evidence cannot certify the whole written token. | `PART+UNK:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `37:141:1` | `فَسَاهَمَ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `8:57:5` | `فَشَرِّدْ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `19:4:7` | `وَٱشْتَعَلَ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:260:22` | `فَصُرْهُنَّ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V+PRON:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `51:29:5` | `فَصَكَّتْ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `9:30:14` | `يُضَٰهِـُٔونَ` | `pending` | Component evidence cannot certify the whole written token. | `PFX+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `91:6:3` | `طَحَىٰهَا` | `pending` | Component evidence cannot certify the whole written token. | `V+PRON:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `22:2:3` | `تَذْهَلُ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `28:23:15` | `تَذُودَانِ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `4:83:8` | `أَذَاعُوا۟` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `2:16:7` | `رَبِحَت` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `12:12:4` | `يَرْتَعْ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `83:14:3` | `رَانَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `11:31:17` | `تَزْدَرِىٓ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `37:94:3` | `يَزِفُّونَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `38:16:4` | `قِطَّنَا` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `21:103:8` | `يَوْمُكُمُ` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `6:130:13` | `يَوْمِكُمْ` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `7:51:14` | `يَوْمِهِمْ` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `13:41:8` | `أَطْرَافِهَا` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `14:43:7` | `طَرْفُهُمْ` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `27:40:14` | `طَرْفُكَ` | `token_only_override` | Suffix-bearing nominal row needs exact-address review before rich certification. | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `3:195:24` | `سَبِيلِى` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `22:47:12` | `سَنَةٍۢ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `29:14:9` | `سَنَةٍ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `2:96:14` | `سَنَةٍۢ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `32:5:15` | `سَنَةٍۢ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `46:15:20` | `سَنَةًۭ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `5:26:6` | `سَنَةًۭ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `70:4:11` | `سَنَةٍۢ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `10:45:7` | `سَاعَةًۭ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `15:91:4` | `عِضِينَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `12:92:5` | `الْيَوْمَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `101:4:1` | `يَوْمَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `10:15:38` | `يَوْمٍ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `10:93:19` | `يَوْمَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `11:105:1` | `يَوْمَ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |

No row is `rich_certified`. VN-19 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

State counts in this sample:

- `pending`: 10
- `rich_candidate`: 13
- `token_only_override`: 17

## State Transitions

- `component-only evidence -> pending component-only rich metadata`: `وَأَطْرَافَ`, `وَأَتْرَفْنَٰهُمْ`, `لَنَسْفَعًۢا`, `فَسَاهَمَ`, `فَشَرِّدْ`, `وَٱشْتَعَلَ`, `فَصُرْهُنَّ`, `فَصَكَّتْ`, `يُضَٰهِـُٔونَ`, and `طَحَىٰهَا`.
- `finite verb strings -> exact-address rich metadata`: `تَذْهَلُ`, `تَذُودَانِ`, `أَذَاعُوا۟`, `رَبِحَت`, `يَرْتَعْ`, `رَانَ`, `تَزْدَرِىٓ`, and `يَزِفُّونَ`.
- `suffix-bearing rows -> token-only rich metadata`: `قِطَّنَا`, `يَوْمُكُمُ`, `يَوْمِكُمْ`, `يَوْمِهِمْ`, `أَطْرَافِهَا`, `طَرْفُهُمْ`, `طَرْفُكَ`, and `سَبِيلِى` keep visible suffix contribution gated.
- `relation-sensitive nominal rows -> rich candidate metadata`: the `سَنَة` and `سَاعَة` rows keep case/iʿrāb and relation review gated before rich certification.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

- `article_definiteness_requires_rich_segments`: 1 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `component_only_candidate_no_whole_token_propagation`: 10 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `finite_verb_dictionary_gloss_or_form_review`: 16 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `missing_rich_renderer_segments`: 40 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `noun_hover_may_leak_verb_infinitive`: 1 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `preposition_or_attached_relation_requires_nahw_review`: 16 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `suffix_or_attached_pronoun_requires_visible_accounting`: 11 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `surface_family_requires_token_only_override`: 17 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review`: 1 sampled rows; uses existing dogfood skill/curriculum routing from VN-19, with no new sarf/nahw edit required in this tranche.

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, suffix pronouns, relation-sensitive nominal roles, preposition/governor review, component-only blockers, and renderer requirements.

Renderer requirements: this tranche emits segment expectations for wāw/fā/lām-prefixed rows, suffix-bearing nouns and verbs, finite verb rows, day/time nominal rows, and relation-sensitive nominal rows whose current English string cannot teach composition by itself.

Future tranche routing: prioritize component-only rows, exact-address finite verb rows, suffix-heavy time/share/edge nouns, and relation-sensitive year/hour nouns before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_19_standard.sample.jsonl
run the internal-only evidence sidecar scan
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_sarf_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_nahw_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/run_grammar_evals.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/check_regressions.py
git diff --check
```
