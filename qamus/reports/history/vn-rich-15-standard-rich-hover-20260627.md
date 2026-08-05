# VN-RICH-15 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-15 converts the fifteenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn15-20260627.md` and the committed VN-15 samples as canonical input.

Source dogfood batch:

- verbs `v678` through `v722`
- nouns `n746` through `n795`
- `229` live hover rows reviewed in the original dogfood tranche
- `199` whole-token rows and `30` component-only evidence rows
- `0` repair-preview-ready rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_15_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_15_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `4:62:3` | `وَتَوْفِيقًا` | `pending` | Conjunction plus accusative masdar-like nominal; component evidence cannot certify the whole token. | `CONJ+MASDAR:ACC:INDEF:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:61:18` | `بَقْلِهَا` | `token_only_override` | Genitive construct noun with attached third feminine singular possessor. | `N:GEN:CONSTRUCT+POSS.3FS:TOKEN-ONLY` | two_vote_required |
| `11:88:29` | `تَوْفِيقِىٓ` | `token_only_override` | Masdar-like construct noun with attached first-person singular possessor. | `MASDAR:CONSTRUCT+POSS.1S:TOKEN-ONLY` | two_vote_required |
| `78:26:2` | `وِفَاقًا` | `token_only_override` | Accusative indefinite masdar-like nominal; block finite or dictionary-verb leakage. | `MASDAR:ACC:INDEF:SG:TOKEN-ONLY` | two_vote_required |
| `2:187:40` | `ٱلْأَسْوَدِ` | `pending` | Definite genitive adjective/nominal token; current hover leaks verb-entry wording. | `ART+ADJ:GEN:DEF:M:SG:POS-REVIEW-PENDING` | two_vote_required |
| `13:4:7` | `أَعْنَٰبٍۢ` | `rich_candidate` | Indefinite genitive plural noun requiring exact relation review. | `N:GEN:INDEF:PL:ROLE-PENDING` | two_vote_required |
| `18:32:9` | `أَعْنَٰبٍۢ` | `rich_candidate` | Indefinite genitive plural noun requiring exact relation review. | `N:GEN:INDEF:PL:ROLE-PENDING` | two_vote_required |
| `6:99:27` | `أَعْنَابٍۢ` | `token_only_override` | Indefinite genitive plural noun with token-only review. | `N:GEN:INDEF:PL:TOKEN-ONLY` | two_vote_required |
| `36:57:3` | `فَٰكِهَةٌۭ` | `rich_candidate` | Indefinite nominative noun needing renderer metadata backfill. | `N:NOM:INDEF:F:SG:RENDERER-BACKFILL` | two_vote_required |
| `55:11:2` | `فَٰكِهَةٌۭ` | `rich_candidate` | Indefinite nominative noun needing renderer metadata backfill. | `N:NOM:INDEF:F:SG:RENDERER-BACKFILL` | two_vote_required |
| `24:35:21` | `زَيْتُونَةٍۢ` | `token_only_override` | Indefinite genitive singular noun requiring exact-address display metadata. | `N:GEN:INDEF:F:SG:TOKEN-ONLY` | two_vote_required |
| `12:43:12` | `سُنۢبُلَٰتٍ` | `token_only_override` | Indefinite plural noun from the grain-ear family. | `N:GEN:INDEF:F:PL:TOKEN-ONLY` | two_vote_required |
| `12:47:10` | `سُنۢبُلِهِۦٓ` | `token_only_override` | Genitive construct noun with attached third masculine singular possessor. | `N:GEN:CONSTRUCT+POSS.3MS:TOKEN-ONLY` | two_vote_required |
| `2:261:12` | `سَنَابِلَ` | `token_only_override` | Indefinite accusative broken plural noun. | `N:ACC:INDEF:F:PL:TOKEN-ONLY` | two_vote_required |
| `2:261:15` | `سُنۢبُلَةٍۢ` | `token_only_override` | Indefinite genitive singular noun. | `N:GEN:INDEF:F:SG:TOKEN-ONLY` | two_vote_required |
| `34:16:15` | `سِدْرٍۢ` | `rich_candidate` | Indefinite genitive noun needing renderer metadata. | `N:GEN:INDEF:M:SG:RENDERER-BACKFILL` | two_vote_required |
| `53:14:2` | `سِدْرَةِ` | `token_only_override` | Genitive construct-like noun needing exact-address review. | `N:GEN:CONSTRUCT:F:SG:TOKEN-ONLY` | two_vote_required |
| `56:28:2` | `سِدْرٍۢ` | `rich_candidate` | Indefinite genitive noun needing renderer metadata. | `N:GEN:INDEF:M:SG:RENDERER-BACKFILL` | two_vote_required |
| `19:23:4` | `جِذْعِ` | `token_only_override` | Genitive singular common noun needing exact-address metadata. | `N:GEN:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `20:71:20` | `جُذُوعِ` | `token_only_override` | Genitive plural common noun needing exact-address metadata. | `N:GEN:INDEF:M:PL:TOKEN-ONLY` | two_vote_required |
| `78:32:1` | `حَدَآئِقَ` | `token_only_override` | Accusative plural common noun needing exact-address metadata. | `N:ACC:INDEF:F:PL:TOKEN-ONLY` | two_vote_required |
| `12:44:2` | `أَضْغَٰثُ` | `token_only_override` | Indefinite plural noun requiring exact-address review. | `N:NOM:INDEF:PL:TOKEN-ONLY` | two_vote_required |
| `21:5:3` | `أضغاث` | `token_only_override` | Indefinite plural noun requiring exact-address review. | `N:NOM:INDEF:PL:TOKEN-ONLY` | two_vote_required |
| `38:44:3` | `ضِغْثًۭا` | `token_only_override` | Accusative singular noun requiring exact-address review. | `N:ACC:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `17:71:15` | `فَتِيلًۭا` | `token_only_override` | Accusative singular noun requiring exact-address review. | `N:ACC:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `4:49:14` | `فَتِيلًا` | `rich_candidate` | Accusative singular noun with minimizer role pending. | `N:ACC:INDEF:M:SG:ROLE-PENDING` | two_vote_required |
| `4:77:48` | `فَتِيلًا` | `rich_candidate` | Accusative singular noun with minimizer role pending. | `N:ACC:INDEF:M:SG:ROLE-PENDING` | two_vote_required |
| `4:124:16` | `نَقِيرًۭا` | `rich_candidate` | Accusative singular noun needing renderer metadata. | `N:ACC:INDEF:M:SG:RENDERER-BACKFILL` | two_vote_required |
| `35:13:28` | `قِطْمِيرٍ` | `token_only_override` | Genitive singular noun requiring exact-address metadata. | `N:GEN:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `20:121:10` | `وَرَقِ` | `rich_candidate` | Genitive construct-like noun requiring relation review. | `N:GEN:CONSTRUCT:M:SG:ROLE-PENDING` | two_vote_required |

No row is `rich_certified`. VN-15 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

State counts in this sample:

- `pending`: 2
- `token_only_override`: 18
- `rich_candidate`: 10

## State Transitions

- `component-only evidence -> pending component-only rich metadata`: `4:62:3`.
- `suffix-bearing noun/masdar rows -> token-only rich metadata`: `2:61:18`, `11:88:29`, `12:47:10`.
- `nominal/POS leakage -> pending or token-only rich metadata`: `78:26:2`, `2:187:40`.
- `string-only noun rows -> rich renderer candidate or token-only rich metadata`: plant, grain-ear, tree, date-stone, and leaf rows in the sample.
- `preposition/attachment-sensitive noun rows -> two-vote exact-address candidates`: grape, fruit, bundle, date-stone, and leaf examples.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-15 already updated or routed through:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-15 already routed through:

- `nahw/procedures/pronoun-attachment.md`
- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/suffix-pronoun-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve nominal/POS gates, suffix possessors, case/role blockers, component-only blockers, and renderer-only backfill without treating readable English as rich certification.

Renderer requirements: this tranche emits segment expectations for conjunction-plus-nominal rows, suffix-bearing nouns and masdars, article-plus-adjective rows, plural/singular noun families, minimizer nouns, and construct-like relation rows.

Future tranche routing: prioritize component-only function pieces, suffix-bearing nominal hosts, finite-verb dictionary leakage, nominal/POS leakage, date-stone minimizer nouns, and case/attachment-sensitive plant/fruit rows before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_15_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
