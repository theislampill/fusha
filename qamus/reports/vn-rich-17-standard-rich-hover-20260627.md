# VN-RICH-17 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-17 converts the seventeenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn17-20260627.md` and the committed VN-17 samples as canonical input.

Source dogfood batch:

- verbs `v768` through `v812`
- nouns `n846` through `n895`
- `136` live hover rows reviewed in the original dogfood tranche
- `112` whole-token candidate rows and `24` component-only evidence rows
- `0` repair-preview-ready rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_17_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_17_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `2:96:17` | `بِمُزَحْزِحِهِۦ` | `pending` | Component evidence cannot certify the whole written token. | `P+PRON+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `68:51:5` | `لَيُزْلِقُونَكَ` | `pending` | Component evidence cannot certify the whole written token. | `PART+PFX+PRON+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `31:20:13` | `وَأَسْبَغَ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `11:105:10` | `وَسَعِيدٌۭ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+N:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:30:16` | `وَيَسْفِكُ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+PFX+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `12:86:3` | `أَشْكُوا۟` | `pending` | Component evidence cannot certify the whole written token. | `V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `20:22:1` | `وَاضْمُمْ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `28:32:10` | `وَٱضْمُمْ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `56:4:2` | `رُجَّتِ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:unknown:PERFECT:PASSIVE:TOKEN-ONLY` | two_vote_required |
| `4:88:2` | `أَرْكَسَهُم` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:IV:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `4:91:5` | `أُرْكِسُوا` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:IV:PERFECT:PASSIVE:TOKEN-ONLY` | two_vote_required |
| `3:185:11` | `زُحْزِحَ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:unknown:PERFECT:PASSIVE:TOKEN-ONLY` | two_vote_required |
| `11:108:3` | `سُعِدُوا` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:unknown:PERFECT:PASSIVE:TOKEN-ONLY` | two_vote_required |
| `14:42:2` | `تَشْخَصُ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:unknown:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `18:29:23` | `يَشْوِى` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:unknown:IMPERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `66:4:2` | `صَغَتْ` | `token_only_override` | Finite verb row needs exact-address sarf/nahw review before rich certification. | `V:unknown:PERFECT:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `8:43:16` | `سَلَّمَ` | `rich_candidate` | POS or entry-family collision remains unresolved. | `UNKNOWN:REVIEW` | two_vote_required |
| `56:4:4` | `رَجًّا` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `18:40:15` | `زَلَقًا` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `34:11:3` | `سَٰبِغَٰتٍۢ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `ADJ:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `21:97:6` | `شَٰخِصَةٌ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `ADJ:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `36:55:6` | `شُغُلٍۢ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `6:146:7` | `ظُفُرٍ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:GENITIVE:ROLE-PENDING` | two_vote_required |
| `17:79:5` | `نَافِلَةًۭ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:ROLE-PENDING` | two_vote_required |
| `21:72:5` | `نَافِلَةًۭ` | `rich_candidate` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:ROLE-PENDING` | two_vote_required |
| `14:24:11` | `أَصْلُهَا` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `59:5:9` | `أُصُولِهَا` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `3:154:62` | `مَضَاجِعِهِمْ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N+POSS:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `50:22:9` | `غِطَآءَكَ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `2:255:42` | `كُرْسِيُّهُ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N+POSS:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `55:72:4` | `ٱلْخِيَامِ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `ART+N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `3:141:1` | `وَلِيُمَحِّصَ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+PURP+PFX+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `3:154:68` | `وَلِيُمَحِّصَ` | `pending` | Component evidence cannot certify the whole written token. | `CONJ+PURP+PFX+V:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `8:1:7` | `ٱلْأَنفَالِ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `ART+N:GENITIVE:TOKEN-ONLY` | two_vote_required |
| `8:1:9` | `ٱلْأَنفَالُ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `ART+N:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `25:53:13` | `بَرْزَخًۭا` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:ACCUSATIVE:TOKEN-ONLY` | two_vote_required |
| `55:20:2` | `بَرْزَخٌ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `83:9:2` | `مَّرْقُومٌ` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:NOMINATIVE:TOKEN-ONLY` | two_vote_required |
| `76:15:8` | `قَوَارِيرَا۠` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |
| `76:16:1` | `قَوَارِيرَا۟` | `token_only_override` | Nominal row needs exact role, case, and segmentation review before rich certification. | `N:UNKNOWN:TOKEN-ONLY` | two_vote_required |

No row is `rich_certified`. VN-17 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

State counts in this sample:

- `pending`: 10
- `rich_candidate`: 4
- `token_only_override`: 26

## State Transitions

- `component-only evidence -> pending component-only rich metadata`: prefixed, governed, or attached-relation rows such as `2:96:17`, `68:51:5`, `31:20:13`, `11:105:10`, `2:30:16`, `12:86:3`, `20:22:1`, `28:32:10`, `3:141:1`, and `3:154:68`.
- `finite/passive verb strings -> exact-address rich metadata`: `56:4:2`, `4:88:2`, `4:91:5`, `3:185:11`, `11:108:3`, `14:42:2`, `18:29:23`, and `66:4:2`.
- `suffix-bearing rows -> token-only rich metadata`: tree-root, resting-place, veil, seat, pavilion, oil, and governed verb/pronoun rows keep visible suffix contribution gated.
- `nominal/POS leakage -> token-only or pending rich metadata`: `56:4:4`, `18:40:15`, `34:11:3`, `21:97:6`, `36:55:6`, `6:146:7`, `8:43:16`, and related rows.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

- `article_definiteness_requires_rich_segments` no-op for sarf/nahw: renderer metadata requirement only; article segmentation already covered by sarf clitic-host procedure (24 rows).
- `component_only_candidate_no_whole_token_propagation` routes to existing `sarf/procedures/clitic-and-host-morphology.md` and `sarf/evals/false-clitic-split-eval.jsonl` coverage; no new skill edit is needed in this tranche (24 rows).
- `finite_verb_dictionary_gloss_or_form_review` routes to existing `sarf/procedures/verb-form-and-mood-review.md` and `sarf/evals/false-clitic-split-eval.jsonl` coverage; no new skill edit is needed in this tranche (38 rows).
- `missing_rich_renderer_segments` no-op for sarf/nahw: renderer metadata requirement only; no sarf/nahw rule change required (136 rows).
- `noun_hover_may_leak_verb_infinitive` routes to existing `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` coverage; no new skill edit is needed in this tranche (1 row).
- `preposition_or_attached_relation_requires_nahw_review` routes to existing `nahw/procedures/preposition-pronoun.md`, `nahw/procedures/pp-attachment-review.md`, and `nahw/evals/particle-function-eval.jsonl` coverage; no new skill edit is needed in this tranche (3 rows).
- `suffix_or_attached_pronoun_requires_visible_accounting` routes to existing `nahw/procedures/pronoun-attachment.md` and `nahw/evals/suffix-pronoun-eval.jsonl` coverage; no new skill edit is needed in this tranche (41 rows).
- `surface_family_requires_token_only_override` routes to existing `nahw/procedures/token-only-overrides.md` and `nahw/evals/irab-polysemy-eval.jsonl` coverage; no new skill edit is needed in this tranche (92 rows).
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review` routes to existing `sarf/procedures/nominal-derivative-decision.md` and `sarf/evals/nominal-derivative-error-eval.jsonl` coverage; no new skill edit is needed in this tranche (14 rows).

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite/passive verb state, attached suffixes, preposition/governor relations, article/host segmentation, nominal/POS gates, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for bāʾ/wa/fā/lām prefixed rows, suffix-bearing nouns and verbs, passive/finite verb rows, definite article rows, and nominal/adjectival rows whose current English string cannot teach composition by itself.

Future tranche routing: prioritize attached preposition-host-suffix stacks, lām-governed verbs, finite/passive verb dictionary leakage, suffix-bearing nominal rows, and noun/verb POS family collisions before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_17_standard.sample.jsonl
run the internal-only evidence sidecar scan
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_sarf_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/validate_nahw_skill.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/run_grammar_evals.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tools/check_regressions.py
git diff --check
```
