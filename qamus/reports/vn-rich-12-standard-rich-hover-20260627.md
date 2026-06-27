# VN-RICH-12 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-12 converts the twelfth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn12-20260627.md` and the committed VN-12 samples as canonical input.

Source dogfood batch:

- verbs `v543` through `v587`
- nouns `n596` through `n645`
- `580` live hover rows reviewed in the original dogfood tranche
- `507` whole/resolved rows and `73` component-only evidence rows
- zero-row entries: `n598`, `n612`, `n633`, `n634`, `n640`, `n641`, `n644`

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_12_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_12_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `2:75:13` | `يُحَرِّفُونَهُۥ` | `pending` | Form II imperfect verb plus plural subject marker and attached object suffix remain component-only. | `V:II:IMPF:ACT:3MP+OBJ.3MS:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:191:3` | `ثَقِفْتُمُوهُمْ` | `token_only_override` | Finite verb needs second-person plural subject and third-person plural object suffix. | `V:I:PERF:ACT:2MP+OBJ.3MP:TOKEN-ONLY` | two_vote_required |
| `2:220:12` | `تُخَالِطُوهُمْ` | `token_only_override` | Form III imperfect verb must block nominal gloss leakage and expose object suffix. | `V:III:IMPF:ACT:2MP+OBJ.3MP:TOKEN-ONLY` | two_vote_required |
| `5:1:20` | `ٱلصَّيْدِ` | `token_only_override` | Definite nominal token must not inherit a verb-entry infinitive. | `ART+N:GEN:DEF:SG:TOKEN-ONLY` | two_vote_required |
| `6:152:3` | `مَالَ` | `pending` | Readable wealth gloss still needs exact nominal case and construct-role review. | `N:ACC:CONSTRUCT:SG:ROLE-PENDING` | two_vote_required |
| `48:29:32` | `كَزَرْعٍ` | `pending` | Comparison/preposition kāf plus host noun remains component-only. | `P:KA+N:GEN:INDEF:SG:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `51:48:2` | `فَرَشْنَٰهَا` | `token_only_override` | Finite first-person plural verb must expose attached object suffix. | `V:I:PERF:ACT:1P+OBJ.3FS:TOKEN-ONLY` | two_vote_required |
| `56:34:1` | `وَفُرُشٍۢ` | `pending` | Conjunction plus nominal host remains component-only. | `CONJ+N:GEN:INDEF:PL:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:17:7` | `أَضَآءَتْ` | `pending` | Form IV finite verb with feminine subject marker remains component-only. | `V:IV:PERF:ACT:3FS:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:20:6` | `أَضَآءَ` | `token_only_override` | Form IV perfect verb needs finite wording, not dictionary-infinitive wording. | `V:IV:PERF:ACT:3MS:TOKEN-ONLY` | two_vote_required |
| `2:74:2` | `قَسَتْ` | `token_only_override` | Finite verb needs feminine subject marker visible. | `V:I:PERF:ACT:3FS:TOKEN-ONLY` | two_vote_required |
| `2:283:14` | `فَلْيُؤَدِّ` | `pending` | Fāʾ plus imperative lām plus jussive imperfect verb remains component-only. | `REM+IMPV-LAM+V:II:IMPF:JUSS:ACT:3MS:COMPONENT-ONLY-PENDING` | never_auto_resolve |

No row is `rich_certified`. VN-12 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `token_only_override -> token-only rich metadata`: `2:191:3`, `2:220:12`, `5:1:20`, `51:48:2`, `2:20:6`, `2:74:2`.
- `populated_uncertified -> pending component-only rich metadata`: `2:75:13`, `48:29:32`, `56:34:1`, `2:17:7`, `2:283:14`.
- `populated_uncertified -> pending role/case rich metadata`: `6:152:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-12 already updated or routed through:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-12 already routed through:

- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite verb state, visible suffix pronouns, preposition/comparison-host relations, nominal/POS gates, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for finite verbs, verb prefixes, subject/object pronouns, article-plus-noun rows, comparison/preposition-host rows, conjunction-plus-host rows, and imperative-lām governed verbs.

Future tranche routing: prioritize finite-verb dictionary leakage, suffix-bearing hosts, nominal/POS leakage, preposition/comparison relation rows, and component-only function pieces before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_12_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
