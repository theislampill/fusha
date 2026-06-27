# VN-RICH-01 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-01 converts the first standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn01-20260627.md` and its committed samples as canonical input, not commit messages.

Source dogfood batch:

- verbs `v048` through `v092`
- nouns `n046` through `n095`
- `1,462` live hover rows reviewed in the original dogfood tranche
- `893` whole/resolved rows and `569` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_01_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_01_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `83:25:4` | `مَّخْتُومٍ` | `pending` | passive participle / nominal token was receiving verb infinitive | `N/PTCP:GEN:M:SG:INDEF:PENDING` | derivative + iʿrāb review |
| `35:40:28` | `يَعِدُ` | `token_only_override` | weak-root promise verb must not collide with another root family | `V:I:IMPF:ACT:3MS:WEAK-WAW` | token-only two-vote before apply |
| `55:44:4` | `حَمِيمٍ` | `pending` | same-surface nominal sense needs context review | `N:GEN:M:SG:INDEF:SENSE-CONTEXT-PENDING` | sense + iʿrāb two-vote |
| `5:38:8` | `نَكَٰلًۭا` | `token_only_override` | same-root wrong nominal sense | `N:ACC:M:SG:INDEF:SENSE-TOKEN-ONLY` | token-only two-vote |
| `2:275:19` | `مِثْلُ` | `token_only_override` | comparison noun was exposed to verb-like infinitive wording | `N:NOM:M:SG:CONSTRUCT:COMPARISON:TOKEN-ONLY` | nominal role review |
| `2:187:49` | `تُبَٰشِرُوهُنَّ` | `token_only_override` | finite verb + subject marker + object suffix must be visible | `V:III:IMPF:ACT:JUSS:2MP+SUBJ.2MP+OBJ.3FP` | suffix/referent/mood two-vote |
| `13:31:45` | `وَعْدُ` | `token_only_override` | maṣdar/nominal token was exposed to verb infinitive | `N/MASDAR:NOM:M:SG:CONSTRUCT:TOKEN-ONLY` | iḍāfa / nominal role review |
| `78:34:2` | `دِهَاقًۭا` | `rich_candidate` | false suffix detector no-op: tanwīn/case ending is not pronoun | `N/ADJ:ACC:M:SG:INDEF:NO-SUFFIX` | syntactic role review before certification |

No row is `rich_certified`. Existing visible hover text and repo-internal dogfood state are enough to shape metadata candidates, not enough to claim live rich certification.

## State Transitions

- `populated_uncertified -> pending rich metadata`: `83:25:4`, `55:44:4`.
- `token_only_override -> token-only rich metadata`: `35:40:28`, `5:38:8`, `2:275:19`, `2:187:49`, `13:31:45`.
- `detector_precision_noop -> rich_candidate metadata`: `78:34:2`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only. It records repo-internal dogfood lineage without authorizing public source labels.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-01 already updated:

- `sarf/drills/verb-measures.md`
- `sarf/drills/clitic-and-host-morphology.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-01 already updated:

- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule: a hover is not rich-safe unless it teaches the visible token pieces and the hidden sarf/nahw state.

Drills/evals/regressions: no new fixture needed. VN-01 already added repeated-defect drills and eval controls for suffix verbs, finite-verb leakage, nominal derivatives, and context-sensitive senses.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-01 lesson classes:

- `finite_verb_dictionary_gloss_leakage`
- `verb_object_suffix_omitted_or_hidden`
- `nominal_surface_verb_gloss_leakage`
- `same_surface_wrong_sense_context`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing prefix/stem/subject/object and nominal-derivative breakdown rows.

Future tranche routing: VN-RICH should continue in bounded tranches, prioritizing suffix-bearing finite verbs, nominal derivative leakage, weak-root collisions, and same-surface context traps before broad positive rows.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_01_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_01_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
