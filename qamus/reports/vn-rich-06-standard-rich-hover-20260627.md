# VN-RICH-06 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-06 converts the sixth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn06-20260627.md` and the committed VN-06 samples as canonical input.

Source dogfood batch:

- verbs `v273` through `v317`
- nouns `n296` through `n345`
- `2,711` live hover rows reviewed in the original dogfood tranche
- `2,498` whole/resolved rows and `213` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_06_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_06_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `2:4:8` | `مِن` | `pending` | The token is a preposition/function word, not a verb-entry family member. | `P:MIN:FUNCTION-PENDING` | two_vote_required |
| `2:30:13` | `مَن` | `pending` | Clause function, not surface family, controls the hover contribution. | `REL:MAN:FUNCTION-PENDING` | two_vote_required |
| `2:57:6` | `ٱلْمَنَّ` | `pending` | Article plus noun segmentation must remain visible without importing verb-entry prose. | `ART+N:DEF:SG:MANNA:PENDING` | two_vote_required |
| `2:25:17` | `ثَمَرَةٍۢ` | `pending` | Noun POS and case review block verb-entry propagation. | `N:FRUIT:GEN:INDEF:SG:PENDING` | two_vote_required |
| `6:141:19` | `ثَمَرِهِۦٓ` | `pending` | The possessive suffix must be visible and component-only evidence cannot certify the whole token. | `N:FRUIT+POSS.3MS:PENDING` | two_vote_required |
| `2:10:3` | `مَّرَضٌۭ` | `pending` | Readable English is not enough without noun role and context review. | `N:STATE:NOM:INDEF:SG:PENDING` | two_vote_required |
| `2:16:3` | `ٱشْتَرَوُا۟` | `pending` | The token needs one context-selected finite contribution, not slash prose. | `V:VIII:PERF:ACT:3MP:TRADE-SENSE-PENDING` | two_vote_required |
| `2:17:9` | `حَوْلَهُۥ` | `pending` | The suffix referent and relation are context-sensitive. | `N/ADV:LOC+POSS.3MS:PENDING` | two_vote_required |
| `2:68:19` | `بَيْنَ` | `pending` | Relation and attachment review are required for rich certification. | `LOC:BETWEEN:ATTACHMENT-PENDING` | two_vote_required |
| `2:90:24` | `غَضَبٍۢ` | `token_only_override` | Nominal shape must block infinitive verb prose. | `N/MASDAR:GEN:INDEF:ANGER:TOKEN-ONLY` | two_vote_required |
| `2:42:2` | `تَلْبِسُوا۟` | `token_only_override` | Finite person/number and mood must be visible before live apply. | `V:I:IMPF:ACT:2MP:MOOD-PENDING:TOKEN-ONLY` | two_vote_required |
| `2:60:2` | `ٱسْتَسْقَىٰ` | `token_only_override` | Form X and finite person must control the rich hover shape. | `V:X:PERF:ACT:3MS:REQUEST-WATER:TOKEN-ONLY` | two_vote_required |
| `1:7:6` | `ٱلْمَغْضُوبِ` | `pending` | Component-only evidence cannot certify a whole-token passive nominal hover. | `ART+PARTICIPLE:PASS:GEN:DEF:PENDING` | two_vote_required |

No row is `rich_certified`. VN-06 dogfood evidence is sufficient to shape rich metadata and blockers, not sufficient for live apply, source-wide propagation, or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `2:4:8`, `2:30:13`, `2:57:6`, `2:25:17`, `6:141:19`, `2:10:3`, `2:16:3`, `2:17:9`, `2:68:19`, `1:7:6`.
- `token_only_override -> token-only rich metadata`: `2:90:24`, `2:42:2`, `2:60:2`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-06 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-06 already updated:

- `nahw/procedures/particle-function-decision.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that a readable English hover is not rich-certified unless it exposes strict surface, POS, function, finite verb form, suffixes, and component-only blockers.

Drills/evals/regressions: no new fixture needed. VN-06 already added repeated-defect controls for `مِن`/`مَن`/`ٱلْمَنَّ`, verb-entry noun leakage, finite slash prose, suffix-bearing hosts, and component-only evidence.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-06 lesson classes:

- `verb_entry_function_token_candidate_leak`
- `man_min_manna_surface_family_collision`
- `verb_entry_candidate_on_lexical_noun`
- `contronym_slash_gloss_form_selection`
- `suffix_bearing_adverbial_host_only`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing preposition/function rows, article+noun rows, suffix-bearing hosts, finite verb form/person, passive participle state, and component-only blockers in the breakdown.

Future tranche routing: VN-RICH should keep prioritizing strict-surface collision families, component-only blockers, finite dictionary prose, nominal/POS leakage, relation tokens, and suffix-bearing hosts before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_06_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_06_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
