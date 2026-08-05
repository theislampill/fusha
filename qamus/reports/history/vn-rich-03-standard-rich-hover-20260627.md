# VN-RICH-03 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-03 converts the third standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn03-20260627.md` and the committed VN-03 samples as canonical input.

Source dogfood batch:

- verbs `v138` through `v182`
- nouns `n146` through `n195`
- `904` live hover rows reviewed in the original dogfood tranche
- `618` whole/resolved rows and `286` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_03_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_03_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | `pending` | component-only Form IV finite verb plus subject/object suffixes | `FA+V:IV:PERF:ACT:1P+OBJ.3MP:PENDING` | whole-token and suffix two-vote |
| `4:28:8` | `ضَعِيفًۭا` | `pending` | nominal/adjectival token collides with verb-entry component | `N/ADJ:ACC:M:SG:INDEF:PENDING` | exact iʿrāb role review |
| `1:4:3` | `ٱلدِّينِ` | `token_only_override` | definite noun receives verb-family prose | `ART+N:GEN:DEF:SG:TOKEN-ONLY` | noun/iḍāfa two-vote |
| `109:6:2` | `دِينُكُمْ` | `token_only_override` | possessed noun needs visible suffix accounting | `N:SG+POSS.2MP:TOKEN-ONLY` | exact-address suffix review |
| `2:71:13` | `مُسَلَّمَةٌۭ` | `token_only_override` | concept gloss on adjectival/passive-participle token | `N/PTCP:NOM:F:SG:INDEF:TOKEN-ONLY` | nominal derivative two-vote |
| `2:128:3` | `مُسْلِمَيْنِ` | `token_only_override` | Islam concept prose on dual participial/person token | `N/PTCP:DUAL:M:INDEF:CASE-PENDING:TOKEN-ONLY` | dual/case review |
| `2:75:17` | `عَقَلُوهُ` | `token_only_override` | finite verb dictionary gloss hides object suffix | `V:I:PERF:ACT:3MP+OBJ.3MS:TOKEN-ONLY` | form/suffix two-vote |
| `13:6:1` | `وَيَسْتَعْجِلُونَكَ` | `pending` | component-only Form X imperfect plus object suffix | `CONJ+V:X:IMPF:ACT:3MP+OBJ.2MS:PENDING` | component-only blocker |
| `20:83:2` | `أَعْجَلَكَ` | `token_only_override` | finite Form IV verb hides `كَ` object | `V:IV:PERF:ACT:3MS+OBJ.2MS:TOKEN-ONLY` | form/suffix two-vote |
| `16:91:2` | `بِعَهْدِ` | `pending` | bāʾ plus nominal host inherits verb-family covenant prose | `P:BI+N:GEN:SG:PENDING` | PP attachment review |
| `24:31:10` | `زِينَتَهُنَّ` | `pending` | possessed nominal needs suffix/referent metadata | `N:SG+POSS.3FP:PENDING` | suffix/referent review |
| `30:2:2` | `ٱلرُّومُ` | `token_only_override` | article plus proper group noun metadata backfill | `ART+PN:GROUP:NOM:DEF:TOKEN-ONLY` | case/role review before certification |

No row is `rich_certified`. VN-03 dogfood evidence is sufficient to shape rich metadata and blockers, not sufficient for live apply or family propagation.

## State Transitions

- `known_defect -> pending rich metadata`: `26:139:2`, `4:28:8`.
- `token_only_override -> token-only rich metadata`: `1:4:3`, `109:6:2`, `2:71:13`, `2:128:3`, `2:75:17`, `20:83:2`, `30:2:2`.
- `populated_uncertified -> pending rich metadata`: `13:6:1`, `16:91:2`, `24:31:10`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-03 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/proper-noun.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/drills/homograph-regressions.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-03 already updated:

- `nahw/procedures/referent-context.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/drills/idafa-and-jar-majrur.md`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that readable English is not enough; suffixes, nominal/adjectival role, possessed nouns, jar-majrūr attachment, and proper group noun state must be teachable.

Drills/evals/regressions: no new fixture needed. VN-03 already added repeated-defect drills and eval controls for finite suffix verbs, nominal/POS leakage, proper/common collisions, and iḍāfa/jar-majrūr rows.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-03 lesson classes:

- `finite_verb_object_suffix_dictionary_leak`
- `component_only_finite_verb_suffix_blocker`
- `nominal_adjectival_token_component_collision`
- `noun_hover_verb_infinitive_leak`
- `concept_gloss_on_participle_or_adjective`
- `preposition_nominal_host_verb_family_leak`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing fāʾ/wāw functions, verb prefix/stem/suffix, noun/article/possessor, bāʾ+host, nominal/adjectival state, proper group noun state, and parse keys in the breakdown.

Future tranche routing: VN-RICH should continue prioritizing suffix-bearing finite verbs, concept gloss leakage on nominal derivatives, component-only blockers, possessed nominals, and proper group nouns before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_03_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_03_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
