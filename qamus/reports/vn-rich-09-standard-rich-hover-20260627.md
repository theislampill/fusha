# VN-RICH-09 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-09 converts the ninth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn09-20260627.md` and the committed VN-09 samples as canonical input.

Source dogfood batch:

- verbs `v408` through `v452`
- nouns `n446` through `n495`
- `442` live hover rows reviewed in the original dogfood tranche
- `319` whole/resolved rows and `123` component-only evidence rows
- zero-row entries: none

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_09_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_09_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `34:54:5` | `يَشْتَهُونَ` | `pending` | Finite plural imperfect verb still needs token-form wording instead of dictionary infinitive prose. | `V:I:IMPF:ACT:3MP:FINITE-FORM-PENDING` | two_vote_required |
| `9:25:16` | `وَضَاقَتْ` | `pending` | Wāw plus finite feminine verb remains component-only until whole-token proof. | `CONJ+V:I:PERF:ACT:3FS:COMPONENT-ONLY-PENDING` | two_vote_required |
| `65:6:9` | `لِتُضَيِّقُوا۟` | `pending` | Lām plus finite plural verb needs function and mood review. | `LAM+V:II:IMPF:ACT:2MP:MOOD-PENDING:COMPONENT-ONLY` | two_vote_required |
| `5:67:16` | `يَعْصِمُكَ` | `token_only_override` | Finite verb must expose attached `كَ` object suffix. | `V:I:IMPF:ACT:3MS+OBJ.2MS:TOKEN-ONLY` | two_vote_required |
| `12:6:2` | `يَجْتَبِيكَ` | `token_only_override` | Finite verb must expose attached `كَ` object suffix. | `V:VIII:IMPF:ACT:3MS+OBJ.2MS:TOKEN-ONLY` | two_vote_required |
| `37:107:1` | `وَفَدَيْنَٰهُ` | `pending` | Wāw plus finite verb plus `هُ` suffix remains component-only until whole-token proof. | `CONJ+V:I:PERF:ACT:1P+OBJ.3MS:COMPONENT-ONLY-PENDING` | two_vote_required |
| `41:10:10` | `أَقْوَٰتَهَا` | `token_only_override` | Nominal host must expose attached `هَا` possessor/reference. | `N:PROVISIONS+POSS.3FS:TOKEN-ONLY` | two_vote_required |
| `16:77:1` | `كَلَمْحِ` | `pending` | Kāf comparison/preposition plus noun host needs attachment review. | `P:KAF+N:GEN:COMPARISON:COMPONENT-ONLY-PENDING` | two_vote_required |
| `2:213:37` | `لِمَا` | `pending` | Lām relation plus classified `ما` function and attachment remain uncertified. | `LAM+MA:FUNCTION-PENDING:ATTACHMENT-PENDING` | two_vote_required |
| `86:4:4` | `لَّمَّا` | `pending` | Lamma-family function collision needs exact negative/exceptive/temporal review. | `LAMMA:FUNCTION-COLLISION:NEG-EXCEPTIVE-PENDING` | two_vote_required |
| `9:114:21` | `لَأَوَّٰهٌ` | `pending` | Lām-looking opening plus lexical host remains component-only until exact POS/segment proof. | `LAM?+N:AWWAH:NOM:COMPONENT-ONLY-PENDING` | two_vote_required |
| `22:29:3` | `تَفَثَهُمْ` | `token_only_override` | Nominal host must expose attached `هُمْ` possessor/reference. | `N:RITES+POSS.3MP:TOKEN-ONLY` | two_vote_required |

No row is `rich_certified`. VN-09 dogfood evidence is sufficient to shape rich metadata, segment expectations, and blocker/gate state, not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `34:54:5`, `9:25:16`, `65:6:9`, `37:107:1`, `16:77:1`, `2:213:37`, `86:4:4`, `9:114:21`.
- `token_only_override -> token-only rich metadata`: `5:67:16`, `12:6:2`, `41:10:10`, `22:29:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-09 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/drills/verb-measures.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-09 already updated:

- `nahw/procedures/ma-function-decision.md`
- `nahw/procedures/exception-and-vocative-review.md`
- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, suffix pronouns, function-token splits, strict-surface false-positive guards, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for finite verbs, suffix-bearing verbs and nouns, lām-on-verb function/mood review, lām/mā and lamma-family function splits, comparison/preposition hosts, and component-only rows.

Future tranche routing: prioritize suffix-bearing finite verbs, lām/mā and lamma-family function collisions, and false raw-prefix segmentation before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools\validate_morphosyntax_token_metadata.py qamus\examples\rich_hover_vn_rich_09_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools\validate_sarf_skill.py
python tools\validate_nahw_skill.py
python tools\run_grammar_evals.py
python tools\check_regressions.py
```
