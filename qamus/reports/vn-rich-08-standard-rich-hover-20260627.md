# VN-RICH-08 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-08 converts the eighth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn08-20260627.md` and the committed VN-08 samples as canonical input.

Source dogfood batch:

- verbs `v363` through `v407`
- nouns `n396` through `n445`
- `1,016` live hover rows reviewed in the original dogfood tranche
- `910` whole/resolved rows and `106` component-only evidence rows
- zero-row entry: `n442`

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_08_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_08_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `2:9:7` | `إِلَّآ` | `pending` | Readable `except` still needs polarity, mustathnā/minhu, exception type, and case policy. | `EXP:ILLA:EXCEPTION-FRAME-PENDING` | two_vote_required |
| `9:8:8` | `إِلًّۭا` | `pending` | Lexical noun row must not inherit exception-particle routing from stripped surface. | `N:ILLAN:LEXICAL-NOUN:EXCEPTION-FALSE-POSITIVE-PENDING` | two_vote_required |
| `1:2:2` | `لِلَّهِ` | `pending` | Lām plus Allah proper-name host is not suffix morphology or host-only Allah. | `P:LAM+PN:ALLAH:PP-ATTACHMENT-PENDING` | two_vote_required |
| `2:68:17` | `بِكْرٌ` | `token_only_override` | Exact lexical noun/adjective blocks false bāʾ segmentation. | `N:BIKR:NOM:INDEF:FALSE-BI-SPLIT:TOKEN-ONLY` | two_vote_required |
| `108:3:2` | `شَانِئَكَ` | `token_only_override` | Suffix-bearing nominal row must expose the attached `كَ`. | `PART:ISM-FAIL:HOST+OBJ.2MS:TOKEN-ONLY` | two_vote_required |
| `7:157:26` | `إِصْرَهُمْ` | `token_only_override` | Burden noun must expose the attached `هُمْ` possessor. | `N:BURDEN+POSS.3MP:TOKEN-ONLY` | two_vote_required |
| `81:15:3` | `بِالْخُنَّسِ` | `pending` | Bāʾ plus article/host row remains component-only until PP attachment review. | `P:BI+ART+N:GEN:DEF:COMPONENT-ONLY-PENDING` | two_vote_required |
| `6:136:12` | `بِزَعْمِهِمْ` | `pending` | Bāʾ plus claim host plus suffix cannot inherit finite verb prose. | `P:BI+N:CLAIM+POSS.3MP:COMPONENT-ONLY-PENDING` | two_vote_required |
| `26:138:3` | `بِمُعَذَّبِينَ` | `pending` | Bāʾ plus governed passive/nominal host needs whole-token proof. | `P:BI+PART:PASS:GEN:PL:COMPONENT-ONLY-PENDING` | two_vote_required |
| `2:86:8` | `يُخَفَّفُ` | `pending` | Finite passive/imperfect form must replace broad dictionary prose. | `V:II:IMPF:PASS:3MS:FORM-VOICE-PENDING` | two_vote_required |
| `48:10:3` | `يُبَايِعُونَكَ` | `token_only_override` | Finite Form III verb must expose its attached `كَ` object suffix. | `V:III:IMPF:ACT:3MP+OBJ.2MS:TOKEN-ONLY` | two_vote_required |

No row is `rich_certified`. VN-08 dogfood evidence is sufficient to shape rich metadata, segment expectations, and blocker/gate state, not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `2:9:7`, `9:8:8`, `1:2:2`, `81:15:3`, `6:136:12`, `26:138:3`, `2:86:8`.
- `token_only_override -> token-only rich metadata`: `2:68:17`, `108:3:2`, `7:157:26`, `48:10:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-08 already updated:

- `sarf/procedures/bulk-source-triangulation.md`
- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/drills/verb-measures.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-08 already updated:

- `nahw/procedures/exception-and-vocative-review.md`
- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/suffix-pronoun-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve exception frames, strict-surface false-positive guards, PP relations, suffix pronouns, finite voice/form, and component-only blockers.

Drills/evals/regressions: no new fixture needed. VN-08 already added repeated-defect controls for exception-vs-lexical noun rows, lām+Allah PP routing, component-only candidate guards, finite/passive dictionary leakage, nominal/POS traps, and suffix-bearing hosts.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-08 lesson classes:

- `exception_particle_frame_vs_lexical_illan`
- `lam_allah_pp_not_suffix_pronoun`
- `component_only_candidate_no_whole_token_propagation`
- `finite_verb_or_passive_dictionary_gloss_leak`
- `nominal_pos_or_lexical_noun_near_verb_or_particle`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing exception particles and exception-frame blockers, lexical noun false positives, lām+proper-name PP rows, false bāʾ split guards, suffix-bearing nominal hosts, bāʾ+host+suffix rows, finite passive verbs, and finite verb object suffixes in the breakdown.

Future tranche routing: VN-RICH should keep selecting rows that expose exception/particle false positives, PP attachment, component-only candidate traps, finite/passive dictionary prose, false clitic splits, and suffix-bearing hosts before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_08_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_08_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
