# VN-RICH-10 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-10 converts the tenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn10-20260627.md` and the committed VN-10 samples as canonical input.

Source dogfood batch:

- verbs `v453` through `v497`
- nouns `n496` through `n545`
- `319` live hover rows reviewed in the original dogfood tranche
- `232` whole/resolved rows and `87` component-only evidence rows
- zero-row entries: `n501`, `n510`, `n511`, `n517`, `n534`, `n536`, `n544`

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_10_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_10_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `16:108:3` | `طَبَعَ` | `pending` | Finite perfect verb still needs token-form wording instead of dictionary infinitive prose. | `V:I:PERF:ACT:3MS:FINITE-FORM-PENDING` | two_vote_required |
| `12:18:15` | `ٱلْمُسْتَعَانُ` | `token_only_override` | Definite nominal/passive-participle-like row must not inherit a bare verb gloss. | `ART+PTCP:PASS:NOM:DEF:SG:TOKEN-ONLY` | two_vote_required |
| `3:119:22` | `بِغَيْظِكُمْ` | `pending` | Bāʾ plus host plus `كُمْ` suffix remains component-only until attachment and suffix review. | `P:BI+N:GEN+POSS.2MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `48:29:42` | `لِيَغِيظَ` | `pending` | Lām plus finite imperfect verb needs function and mood review. | `LAM+V:I:IMPF:ACT:3MS:MOOD-PENDING:COMPONENT-ONLY` | never_auto_resolve |
| `12:19:4` | `وَارِدَهُمْ` | `token_only_override` | Nominal/participle-like host must expose attached `هُمْ` possessor/reference. | `PTCP:ACT+POSS.3MP:TOKEN-ONLY` | two_vote_required |
| `2:24:9` | `وَقُودُهَا` | `pending` | Nominal fuel host must expose attached `هَا` possessor/reference. | `N:FUEL+POSS.3FS:SUFFIX-PENDING` | two_vote_required |
| `25:36:8` | `فَدَمَّرْنَٰهُمْ` | `pending` | Fāʾ plus finite verb plus `هُمْ` object remains component-only until whole-token proof. | `REM+V:II:PERF:ACT:1P+OBJ.3MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `37:136:2` | `دَمَّرْنَا` | `token_only_override` | Finite Form II perfect verb must expose first-person plural subject marking. | `V:II:PERF:ACT:1P:TOKEN-ONLY` | two_vote_required |
| `2:104:6` | `رَٰعِنَا` | `token_only_override` | Address/context-sensitive token must expose visible `نَا` and keep exact role pending. | `V:IMPV?+OBJ.1P:TOKEN-ONLY:CONTEXT-PENDING` | two_vote_required |
| `10:27:7` | `وَتَرْهَقُهُمْ` | `pending` | Wāw plus finite verb plus `هُمْ` object remains component-only until whole-token proof. | `CONJ+V:I:IMPF:ACT:3FS+OBJ.3MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `7:54:19` | `حَثِيثًۭا` | `token_only_override` | String looks plausible but still needs parse/display role metadata. | `ADJ/ADV:ACC:INDEF:ROLE-PENDING` | two_vote_required |
| `5:2:43` | `تَعَاوَنُوا۟` | `token_only_override` | Finite Form VI plural command-like verb must preserve mutual/cooperative form. | `V:VI:IMPV:ACT:2MP:TOKEN-ONLY` | two_vote_required |
| `104:6:3` | `ٱلْمُوقَدَةُ` | `token_only_override` | Definite passive-participle/adjectival row needs nominal derivative role metadata. | `ART+PTCP:PASS:NOM:DEF:FS:TOKEN-ONLY` | two_vote_required |

No row is `rich_certified`. VN-10 dogfood evidence is sufficient to shape rich metadata, segment expectations, and blocker/gate state, not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `16:108:3`, `3:119:22`, `48:29:42`, `2:24:9`, `25:36:8`, `10:27:7`.
- `token_only_override -> token-only rich metadata`: `12:18:15`, `12:19:4`, `37:136:2`, `2:104:6`, `7:54:19`, `5:2:43`, `104:6:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-10 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/drills/verb-measures.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-10 already updated:

- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, suffix pronouns, function-token splits, nominal derivative/POS gates, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for finite verbs, suffix-bearing verbs and nouns, lām-on-verb function/mood review, bāʾ plus host plus suffix rows, nominal/passive-participle rows, and renderer-only metadata backfill.

Future tranche routing: prioritize finite-verb dictionary leakage, verb-entry nominal/POS leakage, suffix-bearing hosts, and component-only lām/bāʾ rows before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_10_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
