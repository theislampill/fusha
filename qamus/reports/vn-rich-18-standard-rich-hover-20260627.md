# VN-RICH-18 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-18 converts the eighteenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn18-20260627.md` and the committed VN-18 samples as canonical input.

Source dogfood batch:

- verbs `v813` through `v857`
- nouns `n896` through `n945`
- `938` live hover rows reviewed in the original dogfood tranche
- `916` whole-token candidate rows and `22` component-only evidence rows
- `0` repair-preview-ready rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_18_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_18_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `2:178:22` | `بِٱلْمَعْرُوفِ` | `pending` | Component evidence cannot certify the whole written token. | `P+ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `22:18:13` | `وَٱلشَّمْسُ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `22:18:14` | `وَٱلْقَمَرُ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `22:18:15` | `وَٱلنُّجُومُ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `22:18:16` | `وَٱلْجِبَالُ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `22:18:17` | `وَٱلشَّجَرُ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `56:55:3` | `ٱلْهِيمِ` | `pending` | Component evidence cannot certify the whole written token. | `ART+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:255:46` | `يَـُٔودُهُۥ` | `pending` | Component evidence cannot certify the whole written token. | `PFX+PRON+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `4:119:4` | `فَلَيُبَتِّكُنَّ` | `pending` | Component evidence cannot certify the whole written token. | `REM+PART+PFX+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `7:160:1` | `فَانْبَجَسَتْ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `27:19:1` | `فَتَبَسَّمَ` | `pending` | Component evidence cannot certify the whole written token. | `REM+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `4:72:4` | `لَّيُبَطِّئَنَّ` | `pending` | Component evidence cannot certify the whole written token. | `V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `8:48:19` | `نَكَصَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `23:66:4` | `تَنكِصُونَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `11:78:3` | `يُهْرَعُونَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `39:21:20` | `يَهِيجُ` | `rich_candidate` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `57:20:20` | `يَهِيجُ` | `rich_candidate` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `26:225:7` | `يَهِيمُونَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `18:52:13` | `مَّوْبِقًۭا` | `token_only_override` | Nominal/POS-family row needs exact role and derivation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `42:34:2` | `يُوبِقْهُنَّ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:IMPERFECT:UNKNOWN+OBJ:TOKEN-ONLY` | two_vote_required |
| `59:6:8` | `أَوْجَفْتُمْ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `79:8:3` | `وَاجِفَةٌ` | `token_only_override` | Nominal/POS-family row needs exact role and derivation review before rich certification. | `N/ADJ:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `22:9:1` | `ثَانِىَ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `17:20:1` | `كُلًّۭا` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `48:16:8` | `أُو۟لِى` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `2:216:5` | `كُرْهٌۭ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `9:32:14` | `كَرِهَ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `2:61:8` | `وَٰحِدٍۢ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:102:27` | `أَحَدٍ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:102:48` | `أَحَدٍ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:136:4` | `أَحَدٍ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:163:3` | `وَٰحِدٌۭ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:NOMINATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:180:5` | `أَحَدَكُمُ` | `rich_candidate` | Readable string needs rich segment display before certification. | `PRON+N+POSS:NOMINATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:213:4` | `وَٰحِدَةًۭ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:266:2` | `أَحَدُكُمْ` | `rich_candidate` | Readable string needs rich segment display before certification. | `PRON+N+POSS:UNKNOWN:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `2:96:10` | `أَحَدُهُمْ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `PRON+N+POSS:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `2:285:18` | `أَحَدٍۢ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `3:91:10` | `أَحَدِهِم` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `3:153:6` | `أَحَدٍۢ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |
| `4:1:13` | `وَٰحِدَةٍۢ` | `rich_candidate` | Readable string needs rich segment display before certification. | `N:GENITIVE:RICH-RENDERER-BACKFILL` | human_source_review_required |

No row is `rich_certified`. VN-18 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

State counts in this sample:

- `pending`: 12
- `rich_candidate`: 18
- `token_only_override`: 10

## State Transitions

- `component-only evidence -> pending component-only rich metadata`: `بِٱلْمَعْرُوفِ`, the 22:18 sun/moon/stars/mountains/trees cluster, `يَـُٔودُهُۥ`, fā/lām-prefixed verbs, and similar component rows.
- `finite verb strings -> exact-address rich metadata`: `نَكَصَ`, `تَنكِصُونَ`, `يُهْرَعُونَ`, `يَهِيجُ`, `يَهِيمُونَ`, `يُوبِقْهُنَّ`, `أَوْجَفْتُمْ`, and related rows, with VN-RICH-18 avoiding prefix splits unless the row has explicit morphology support.
- `suffix-bearing rows -> token-only rich metadata`: `أَحَدُهُمْ`, `أَحَدِهِم`, `أَحَدَكُم`, `يُوبِقْهُنَّ`, and related exact-address rows keep visible suffix contribution gated.
- `nominal/POS leakage -> token-only or candidate rich metadata`: `ثَانِىَ`, `كُلًّۭا`, `أُو۟لِى`, `كُرْهٌۭ`, `كَرِهَ`, `مَّوْبِقًۭا`, `ٱلْهِيمِ`, and `وَاجِفَةٌ`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

- `missing_rich_renderer_segments` no-op for sarf/nahw: renderer metadata requirement only; no new skill edit is needed in this tranche (34 sampled rows).
- `suffix_or_attached_pronoun_requires_visible_accounting` routes to existing `nahw/procedures/pronoun-attachment.md`; no new skill edit is needed in this tranche (17 sampled rows).
- `component_only_candidate_no_whole_token_propagation` routes to existing `sarf/procedures/clitic-and-host-morphology.md` and component-only gate coverage; no new skill edit is needed in this tranche (12 sampled rows).
- `surface_family_requires_token_only_override` routes to existing `nahw/procedures/token-only-overrides.md`; no new skill edit is needed in this tranche (10 sampled rows).
- `finite_verb_dictionary_gloss_or_form_review` routes to existing `sarf/procedures/verb-form-and-mood-review.md`; no new skill edit is needed in this tranche (10 sampled rows).
- `preposition_or_attached_relation_requires_nahw_review` routes to existing `nahw/procedures/preposition-pronoun.md` and `nahw/procedures/pp-attachment-review.md`; no new skill edit is needed in this tranche (9 sampled rows).
- `noun_hover_may_leak_verb_infinitive` routes to existing `sarf/procedures/nominal-derivative-decision.md`; no new skill edit is needed in this tranche (5 sampled rows).
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review` remains covered by existing VN dogfood procedures or exact blocker routing; no new skill edit is needed in this tranche (2 sampled rows).
- `article_definiteness_requires_rich_segments` no-op for sarf/nahw: article segmentation is already covered by clitic-host procedure and renderer metadata requirements (1 sampled rows).

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve function prefixes, article/host segmentation, finite verb state, suffix pronouns, preposition/governor relations, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for bāʾ/wāw/fā/lām prefixed rows, definite article rows, suffix-bearing nouns and verbs, finite verb rows, and nominal/POS rows whose current English string cannot teach composition by itself.

Future tranche routing: prioritize component-only rows, oath/conjunction/article clusters, suffix-heavy `أحد/واحد` rows, finite verb dictionary leakage, and noun/verb POS family collisions before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_18_standard.sample.jsonl
run the internal-only evidence sidecar scan
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_sarf_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_nahw_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/run_grammar_evals.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/check_regressions.py
git diff --check
```
