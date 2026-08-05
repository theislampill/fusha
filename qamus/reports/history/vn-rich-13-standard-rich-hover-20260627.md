# VN-RICH-13 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-13 converts the thirteenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn13-20260627.md` and the committed VN-13 samples as canonical input.

Source dogfood batch:

- verbs `v588` through `v632`
- nouns `n646` through `n695`
- `554` live hover rows reviewed in the original dogfood tranche
- `492` whole/resolved rows and `62` component-only evidence rows
- zero-row entries: `n647`, `n650`, `n670`, `n676`, `n677`, `n678`

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_13_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_13_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `19:24:10` | `سَرِيًّۭا` | `pending` | nominal surface | `N:ACC:INDEF:SG:ROLE-PENDING` | two_vote_required |
| `7:74:3` | `سُهُولِهَا` | `token_only_override` | plural noun host | `N:GEN:CONSTRUCT:PL+POSS.3FS:TOKEN-ONLY` | two_vote_required |
| `2:264:21` | `صَفْوَانٍ` | `pending` | noun host | `N:GEN:INDEF:SG:ROLE-PENDING` | two_vote_required |
| `18:17:17` | `فَجْوَةٍۢ` | `token_only_override` | noun token | `N:GEN:INDEF:SG:TOKEN-ONLY` | two_vote_required |
| `73:14:3` | `كَثِيبًا` | `token_only_override` | noun token | `N:ACC:INDEF:SG:TOKEN-ONLY` | two_vote_required |
| `100:4:3` | `نَقْعًۭا` | `token_only_override` | noun token | `N:ACC:INDEF:SG:TOKEN-ONLY` | two_vote_required |
| `2:19:4` | `ٱلسَّمَآءِ` | `pending` | definite article | `ART+N:GEN:DEF:SG-COLLECTIVE:ROLE-PENDING` | two_vote_required |
| `22:18:13` | `وَٱلشَّمْسُ` | `pending` | wāw contribution | `CONJ+ART+N:NOM:DEF:SG:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:96:2` | `أَحْرَصَ` | `token_only_override` | POS review | `ISM:ELATIVE:ACC:TOKEN-ONLY-POS-REVIEW` | two_vote_required |
| `25:40:7` | `مَطَرَ` | `pending` | nominal/POS review | `N:ACC_OR_CONSTRUCT:SG:POS-REVIEW-PENDING` | two_vote_required |
| `14:22:30` | `بِمُصْرِخِكُمْ` | `pending` | prefixed preposition | `P+N:GEN:HOST+POSS.2MP:ATTACHMENT-PENDING` | two_vote_required |
| `80:25:2` | `صَبَبْنَا` | `token_only_override` | finite verb stem | `V:I:PERF:ACT:1P:TOKEN-ONLY` | two_vote_required |

No row is `rich_certified`. VN-13 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `token_only_override -> token-only rich metadata`: `7:74:3`, `18:17:17`, `73:14:3`, `100:4:3`, `2:96:2`, `80:25:2`.
- `populated_uncertified -> pending renderer/role metadata`: `19:24:10`, `2:264:21`, `2:19:4`.
- `populated_uncertified -> pending component-only metadata`: `22:18:13`.
- `known_defect -> pending POS or attachment blocker`: `25:40:7`, `14:22:30`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-13 already updated or routed through:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-13 already routed through:

- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, attached pronouns, article/host contribution, nominal/POS gates, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for suffix-bearing nouns, article-plus-noun rows, conjunction-plus-article-plus-host rows, preposition-host-pronoun rows, finite verbs with subject marking, and single-host nouns whose string is readable but not yet rich.

Future tranche routing: prioritize finite-verb dictionary leakage, suffix-bearing hosts, nominal/POS leakage, preposition/attached relation rows, article definiteness rows, and component-only function pieces before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_13_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
