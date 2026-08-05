# VN-RICH-04 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-04 converts the fourth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn04-20260627.md` and the committed VN-04 samples as canonical input.

Source dogfood batch:

- verbs `v183` through `v227`
- nouns `n196` through `n245`
- `1,492` live hover rows reviewed in the original dogfood tranche
- `1,219` whole/resolved rows and `273` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_04_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_04_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `12:42:10` | `فَأَنسَىٰهُ` | `pending` | component-only weak/causative finite verb plus object suffix | `FA+V:IV:PERF:ACT:3MS+OBJ.3MS:PENDING` | whole-token and suffix two-vote |
| `15:3:1` | `ذَرْهُمْ` | `pending` | imperative weak-root host plus object suffix | `V:I:IMP:ACT:2MS+OBJ.3MP:PENDING` | exact-address imperative/suffix review |
| `10:15:16` | `بَدِّلْهُ` | `pending` | component-only Form II imperative plus object suffix | `V:II:IMP:ACT:2MS+OBJ.3MS:PENDING` | component-only blocker |
| `5:103:7` | `سَآئِبَةٍۢ` | `pending` | custom noun string lacks rich case/state metadata | `N:CUSTOM:GEN:F:SG:INDEF:PENDING` | noun role and case two-vote |
| `5:103:9` | `وَصِيلَةٍۢ` | `pending` | wāw plus custom noun not rich-certified | `CONJ+N:CUSTOM:GEN:F:SG:INDEF:PENDING` | wāw/function and noun role review |
| `15:9:4` | `الذِّكْرَ` | `pending` | definite noun receives verb infinitive prose | `ART+N:ACC:DEF:SG:PENDING` | noun/POS/case two-vote |
| `6:118:3` | `ذُكِرَ` | `pending` | passive finite verb routed through noun/root-family prose | `V:I:PERF:PASS:3MS:PENDING` | passive voice/POS two-vote |
| `26:165:2` | `ٱلذُّكْرَانَ` | `token_only_override` | article plus masculine plural/dual-looking nominal metadata backfill | `ART+N:ACC:M:PL:DEF:TOKEN-ONLY` | renderer metadata and case review |

No row is `rich_certified`. VN-04 dogfood evidence is sufficient to shape rich metadata and blockers, not sufficient for live apply or family propagation.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `12:42:10`, `15:3:1`, `10:15:16`.
- `known_defect -> pending rich metadata`: `5:103:7`, `5:103:9`, `15:9:4`, `6:118:3`.
- `token_only_override -> token-only rich metadata`: `26:165:2`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-04 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-04 already updated:

- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that readable English is not enough; weak/geminate finite verbs, imperatives, suffixes, passive voice, custom nouns, and article/case state must be teachable.

Drills/evals/regressions: no new fixture needed. VN-04 already added repeated-defect drills and eval controls for weak finite verbs, imperative suffixes, passive/POS leakage, and custom-noun rows.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-04 lesson classes:

- `component_only_weak_finite_verb_suffix`
- `imperative_object_suffix_dictionary_leak`
- `form_ii_imperative_object_suffix_leak`
- `custom_noun_string_not_rich_certified`
- `noun_hover_verb_infinitive_leak`
- `passive_voice_pos_leak`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing fāʾ/wāw functions, imperative/finite verb host, object suffixes, passive voice, article/noun segmentation, custom noun case/state, and parse keys in the breakdown.

Future tranche routing: VN-RICH should continue prioritizing weak/hamzated/geminate finite verbs, imperatives with suffixes, passive voice, component-only blockers, and POS collisions before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_04_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_04_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
