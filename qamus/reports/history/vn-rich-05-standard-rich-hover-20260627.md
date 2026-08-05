# VN-RICH-05 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-05 converts the fifth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn05-20260627.md` and the committed VN-05 samples as canonical input.

Source dogfood batch:

- verbs `v228` through `v272`
- nouns `n246` through `n295`
- `1,191` live hover rows reviewed in the original dogfood tranche
- `1,009` whole/resolved rows and `182` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_05_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_05_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `4:11:1` | `يُوصِيكُمُ` | `token_only_override` | finite verb plus `كُم` object suffix hidden by infinitive prose | `V:IV:IMPF:ACT:3MS+OBJ.2MP:TOKEN-ONLY` | exact-address suffix/form two-vote |
| `60:8:15` | `تَبَرُّوهُمْ` | `token_only_override` | finite verb plus `هُمْ` object suffix hidden by root-family prose | `V:I/II:IMPF:ACT:2MP+OBJ.3MP:TOKEN-ONLY` | exact-address suffix/form two-vote |
| `2:137:15` | `فَسَيَكْفِيكَهُمُ` | `pending` | fāʾ/future/verb/pronoun stack is component-only evidence | `FA+FUT+V:I:IMPF:ACT:3MS+OBJ.2MS+OBJ.3MP:PENDING` | component-only blocker and two-vote |
| `12:3:5` | `ٱلْقَصَصِ` | `token_only_override` | article-bearing story noun receives verb-infinitive prose | `ART+N:GEN/ACC:DEF:SG:PENDING` | noun/POS/case two-vote |
| `12:21:25` | `غَالِبٌ` | `token_only_override` | nominal derivative receives verb-infinitive prose | `N/ADJ:ACTIVE-PARTICIPLE:NOM:M:SG:INDEF:TOKEN-ONLY` | nominal derivative two-vote |
| `2:239:3` | `فَرِجَالًا` | `pending` | `ر ج ل` family collision plus fāʾ component-only route | `FA+N:ACC:INDEF:RAJUL-FAMILY:PENDING` | component-only/context two-vote |
| `10:37:14` | `يَدَيْهِ` | `pending` | dual body-part/relational noun plus possessor hidden by omnibus entry prose | `N:DUAL:BODY-PART+POSS.3MS:PENDING` | referent/context two-vote |
| `10:26:7` | `وُجُوهَهُمْ` | `token_only_override` | plural body-part noun plus possessor hidden by omnibus entry prose | `N:PL:BODY-PART+POSS.3MP:TOKEN-ONLY` | referent/case two-vote |
| `37:11:5` | `لَّازِبٍ` | `token_only_override` | lexical initial lām must not be split as lām particle | `ADJ:GEN:INDEF:FALSE-LAM:TOKEN-ONLY` | renderer metadata backfill |

No row is `rich_certified`. VN-05 dogfood evidence is sufficient to shape rich metadata and blockers, not sufficient for live apply or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `2:137:15`, `2:239:3`, `10:37:14`.
- `token_only_override -> token-only rich metadata`: `4:11:1`, `60:8:15`, `12:3:5`, `12:21:25`, `10:26:7`, `37:11:5`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-05 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/noun-plural-gender.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-05 already updated:

- `nahw/procedures/referent-context.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that a readable English hover is not rich-certified unless it exposes the visible verb suffixes, stacked proclitics, noun/POS state, body-part referents, or false-clitic guard.

Drills/evals/regressions: no new fixture needed. VN-05 already added repeated-defect drills and eval controls for finite verb suffixes, nominal derivative/POS leakage, `ر ج ل` family collisions, body-part referent rows, and false lām splitting.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-05 lesson classes:

- `finite_verb_object_suffix_infinitive_leak`
- `verb_object_suffix_root_family_leak`
- `story_noun_gets_verb_infinitive`
- `active_participle_gets_verb_infinitive`
- `root_key_lemma_shape_collision`
- `body_part_omnibus_referent_gloss`
- `false_lam_proclitic_attachment`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing verb host/object suffixes, fāʾ/future stacks, article/noun segmentation, body-part possessor suffixes, and false-clitic negative controls in the breakdown.

Future tranche routing: VN-RICH should continue prioritizing finite verbs with visible suffixes, stacked clitic tokens, noun/POS leakage, body-part/referent rows, component-only blockers, and false-clitic controls before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_05_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_05_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
