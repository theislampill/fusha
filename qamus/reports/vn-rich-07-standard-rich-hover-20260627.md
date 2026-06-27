# VN-RICH-07 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-07 converts the seventh standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn07-20260627.md` and the committed VN-07 samples as canonical input.

Source dogfood batch:

- verbs `v318` through `v362`
- nouns `n346` through `n395`
- `627` live hover rows reviewed in the original dogfood tranche
- `434` whole/resolved rows and `193` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_07_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_07_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `2:38:7` | `مِّنِّى` | `pending` | Preposition plus attached first-person pronoun cannot be certified through a verb-entry candidate. | `P:MIN+PRON.1S:ATTACHMENT-PENDING` | two_vote_required |
| `2:95:2` | `يَتَمَنَّوْهُ` | `token_only_override` | The Form V imperfect host and attached object pronoun must both be visible. | `V:V:IMPF:ACT:3MP+OBJ.3MS:TOKEN-ONLY` | two_vote_required |
| `2:71:23` | `كَادُوا۟` | `pending` | Kāda-sister construction needs predicate/context before rich certification. | `V:KADA:PERF:ACT:3MP:PREDICATE-PENDING` | two_vote_required |
| `7:8:6` | `مَوَٰزِينُهُۥ` | `token_only_override` | Plural scales noun plus possessive suffix must not inherit the finite weighing verb gloss. | `N:PL:SCALES+POSS.3MS:TOKEN-ONLY` | two_vote_required |
| `55:7:4` | `ٱلْمِيزَانَ` | `token_only_override` | Definite balance noun requires article plus host segmentation, not verb-family prose. | `ART+N:ACC:DEF:SG:BALANCE:TOKEN-ONLY` | two_vote_required |
| `4:7:19` | `مَّفْرُوضًۭا` | `token_only_override` | Passive nominal derivative must block bare finite-verb wording. | `PART:ISM-MAFOOL:ACC:INDEF:SG:OBLIGATED:TOKEN-ONLY` | two_vote_required |
| `8:43:5` | `مَنَامِكَ` | `token_only_override` | Possessed dream/sleep noun needs the second-person suffix contribution. | `N:GEN:CONSTRUCT:DREAM+POSS.2MS:TOKEN-ONLY` | two_vote_required |
| `10:54:2` | `النَّدَامَةَ` | `pending` | Missing nominal row needs exact-address review before rich certification. | `ART+N:ACC:DEF:SG:REMORSE:PENDING` | two_vote_required |
| `47:5:3` | `بَالَهُمْ` | `token_only_override` | Possessed state/condition noun needs the third-person plural suffix contribution. | `N:ACC:CONSTRUCT:STATE+POSS.3MP:TOKEN-ONLY` | two_vote_required |
| `2:219:16` | `تَتَفَكَّرُونَ` | `pending` | Component-only evidence cannot certify or propagate the whole finite verb token. | `V:V:IMPF:ACT:2MP:COMPONENT-ONLY-PENDING` | two_vote_required |

No row is `rich_certified`. VN-07 dogfood evidence is sufficient to shape rich metadata, segment expectations, and blocker/gate state, not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `2:38:7`, `2:71:23`, `10:54:2`, `2:219:16`.
- `token_only_override -> token-only rich metadata`: `2:95:2`, `7:8:6`, `55:7:4`, `4:7:19`, `8:43:5`, `47:5:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-07 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/verb-measures.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-07 already updated:

- `nahw/procedures/particle-function-decision.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve strict surface, POS, finite verb form, suffixes, function-token status, and component-only blockers.

Drills/evals/regressions: no new fixture needed. VN-07 already added repeated-defect controls for preposition-pronoun rows, finite verb object suffixes, kāda-sister context, weighing-family nominal leakage, possessed noun hosts, and nominal derivative leakage.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-07 lesson classes:

- `preposition_pronoun_candidate_in_verb_tranche`
- `finite_verb_object_suffix_or_dictionary_gloss_leak`
- `near_verb_kada_predicate_context_needed`
- `weighing_family_nominal_rows_inside_verb_tranche`
- `verb_entry_nominal_derivative_pos_leak`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing preposition+pronoun rows, finite verb prefix/host/object-suffix rows, kāda-sister construction blockers, article+noun rows, possessed noun hosts, nominal derivatives, and component-only blockers in the breakdown.

Future tranche routing: VN-RICH should continue selecting exact rows that expose finite dictionary leakage, POS-family leakage, suffix/possessor loss, article+noun segmentation, and component-only candidate traps before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_07_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_07_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
