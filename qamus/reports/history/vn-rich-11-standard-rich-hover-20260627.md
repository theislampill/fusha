# VN-RICH-11 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-11 converts the eleventh standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn11-20260627.md` and the committed VN-11 samples as canonical input.

Source dogfood batch:

- verbs `v498` through `v542`
- nouns `n546` through `n595`
- `595` live hover rows reviewed in the original dogfood tranche
- `530` whole/resolved rows and `65` component-only evidence rows
- zero-row entries: `n546`, `n550`, `n552`, `n575`, `n579`, `n580`, `n582`, `n583`, `n586`, `n593`

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_11_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_11_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `8:41:3` | `غَنِمْتُم` | `token_only_override` | Finite Form I perfect verb needs second-person plural subject contribution rather than dictionary-infinitive wording. | `V:I:PERF:ACT:2MP:TOKEN-ONLY` | two_vote_required |
| `8:9:2` | `تَسْتَغِيثُونَ` | `token_only_override` | Form X imperfect verb needs prefix/stem/plural ending display and finite wording. | `V:X:IMPF:ACT:2MP:TOKEN-ONLY` | two_vote_required |
| `20:39:2` | `ٱقْذِفِيهِ` | `token_only_override` | Imperative host must expose attached object pronoun. | `V:I:IMPV:ACT:2FS+OBJ.3MS:TOKEN-ONLY` | two_vote_required |
| `25:46:2` | `قَبَضْنَٰهُ` | `token_only_override` | Finite first-person plural verb must expose attached object pronoun. | `V:I:PERF:ACT:1P+OBJ.3MS:TOKEN-ONLY` | two_vote_required |
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | `pending` | Fāʾ plus Form IV finite verb plus subject/object suffixes remain component-only. | `REM+V:IV:PERF:ACT:1P+OBJ.3MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:4:11` | `هُمْ` | `pending` | Pronoun/function token collided with a verb-entry family and needs role/referent review. | `PRON.3MP:ROLE-PENDING` | two_vote_required |
| `23:5:3` | `لِفُرُوجِهِمْ` | `pending` | Lām plus host noun plus attached possessor remain component-only. | `P:LI+N:GEN:PL+POSS.3MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `24:30:7` | `فُرُوجَهُمْ` | `pending` | Plural host noun must expose attached possessor before rich certification. | `N:ACC:PL+POSS.3MP:SUFFIX-PENDING` | two_vote_required |
| `4:94:24` | `مَغَانِمُ` | `token_only_override` | Nominal/POS row must block verb-entry leakage. | `N:NOM:INDEF:PL:TOKEN-ONLY` | two_vote_required |
| `31:34:7` | `ٱلْغَيْثَ` | `pending` | Definite noun with article remains component-only because routing came through a verb-entry family. | `ART+N:ACC:DEF:SG:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `76:15:5` | `فِضَّةٍۢ` | `pending` | Readable string hover still needs nominal case/role metadata. | `N:GEN:INDEF:SG:ROLE-PENDING` | two_vote_required |
| `4:77:7` | `كُفُّوٓا۟` | `pending` | POS-collision row needs imperative review rather than noun-entry propagation. | `V:I:IMPV:ACT:2MP:POS-COLLISION-PENDING` | two_vote_required |

No row is `rich_certified`. VN-11 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `token_only_override -> token-only rich metadata`: `8:41:3`, `8:9:2`, `20:39:2`, `25:46:2`, `4:94:24`.
- `known_defect -> pending component-only rich metadata`: `26:139:2`.
- `populated_uncertified -> pending rich metadata`: `2:4:11`, `23:5:3`, `24:30:7`, `31:34:7`, `76:15:5`, `4:77:7`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-11 already updated or routed through:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-11 already routed through:

- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, visible suffix pronouns, preposition-host relations, nominal/POS gates, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for finite verbs, imperative verbs, pronoun/function tokens, lām-plus-host-plus-suffix rows, article-plus-noun rows, suffix-bearing nouns, and POS-collision blockers.

Future tranche routing: prioritize finite-verb dictionary leakage, suffix-bearing hosts, pronoun/function token collisions, verb-entry nominal/POS leakage, and component-only preposition or fāʾ rows before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_11_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
