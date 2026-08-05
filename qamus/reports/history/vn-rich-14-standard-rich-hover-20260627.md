# VN-RICH-14 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-14 converts the fourteenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn14-20260627.md` and the committed VN-14 samples as canonical input.

Source dogfood batch:

- verbs `v633` through `v677`
- nouns `n696` through `n745`
- `262` live hover rows reviewed in the original dogfood tranche
- `213` whole-token rows and `49` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_14_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_14_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `22:18:17` | `وَٱلشَّجَرُ` | `pending` | wāw contribution | `CONJ+ART+N:NOM:DEF:SG:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `16:80:19` | `أَصْوَافِهَا` | `token_only_override` | plural host noun | `N:GEN:CONSTRUCT:PL+POSS.3FS:TOKEN-ONLY` | two_vote_required |
| `2:223:5` | `حَرْثَكُمْ` | `token_only_override` | construct noun | `N:ACC:CONSTRUCT:SG+POSS.2MP:TOKEN-ONLY` | two_vote_required |
| `2:143:4` | `وَسَطًۭا` | `token_only_override` | nominal/adjectival token | `N/ADJ:ACC:INDEF:SG:TOKEN-ONLY` | two_vote_required |
| `5:89:17` | `أَوْسَطِ` | `token_only_override` | nominal/elative contribution | `ISM-TAFDIL:GEN:DEF_OR_CONSTRUCT:TOKEN-ONLY` | two_vote_required |
| `68:28:2` | `أَوْسَطُهُمْ` | `token_only_override` | elative host | `ISM-TAFDIL:NOM:CONSTRUCT+POSS.3MP:TOKEN-ONLY` | two_vote_required |
| `50:16:6` | `تُوَسْوِسُ` | `token_only_override` | finite imperfect verb | `V:QUAD-I:IMPF:ACT:3FS:TOKEN-ONLY` | two_vote_required |
| `114:4:3` | `الْوَسْوَاسِ` | `token_only_override` | definite article | `ART+N:GEN:DEF:SG:TOKEN-ONLY` | two_vote_required |
| `6:76:11` | `أَفَلَ` | `token_only_override` | finite perfect verb | `V:I:PERF:ACT:3MS:TOKEN-ONLY` | two_vote_required |
| `6:76:15` | `ٱلْءَافِلِينَ` | `token_only_override` | article | `ART+PTCP.ACT:ACC/GEN:DEF:M:PL:TOKEN-ONLY` | two_vote_required |
| `57:27:20` | `ٱبْتَدَعُوهَا` | `token_only_override` | Form VIII finite verb | `V:VIII:PERF:ACT:3MP+OBJ.3FS:TOKEN-ONLY` | two_vote_required |
| `6:141:19` | `ثَمَرِهِۦٓ` | `pending` | nominal host | `N:GEN:CONSTRUCT:SG+POSS.3MS:POS-REVIEW-PENDING` | two_vote_required |
| `12:59:3` | `بِجَهَازِهِمْ` | `pending` | prefixed preposition | `P+N:GEN:HOST+POSS.3MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |

No row is `rich_certified`. VN-14 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `known_defect -> pending component-only rich metadata`: `22:18:17`.
- `token_only_override -> token-only rich metadata`: `16:80:19`, `2:223:5`, `2:143:4`, `5:89:17`, `68:28:2`, `50:16:6`, `114:4:3`, `6:76:11`, `6:76:15`, `57:27:20`.
- `populated_uncertified -> pending nominal/POS or relation blocker`: `6:141:19`, `12:59:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-14 already updated or routed through:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-14 already routed through:

- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, attached pronouns, article/host contribution, nominal/POS gates, false-prefix caution, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for conjunction-plus-article-plus-host rows, suffix-bearing nouns, article-plus-participle rows, finite verbs, nominal derivatives, and preposition-host-pronoun rows.

Future tranche routing: prioritize component-only function pieces, suffix-bearing hosts, finite-verb dictionary leakage, nominal/POS leakage, and bāʾ-host-suffix relations before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_14_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
