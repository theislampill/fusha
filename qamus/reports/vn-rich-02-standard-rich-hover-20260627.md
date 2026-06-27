# VN-RICH-02 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-02 converts the second standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn02-20260627.md` and the committed VN-02 samples as canonical input.

Source dogfood batch:

- verbs `v093` through `v137`
- nouns `n096` through `n145`
- `1,375` live hover rows reviewed in the original dogfood tranche
- `1,086` whole/resolved rows and `289` component-only evidence rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_02_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_02_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `2:178:22` | `بِٱلْمَعْرُوفِ` | `pending` | bāʾ + article + nominal host, PP attachment pending | `P:BI+ART+N/PTCP:GEN:DEF:PENDING` | jar-majrūr attachment two-vote |
| `25:9:6` | `فَضَلُّوا۟` | `token_only_override` | root collision: ضلل verb, not فضل favor family | `FA+V:I:PERF:ACT:3MP:ROOT-DLL:TOKEN-ONLY` | root/POS quarantine |
| `17:70:12` | `وَفَضَّلْنَٰهُمْ` | `token_only_override` | Form II finite verb plus `هُمْ` object | `CONJ+V:II:PERF:ACT:1P+OBJ.3MP` | suffix/referent two-vote |
| `16:71:10` | `فُضِّلُوا۟` | `token_only_override` | passive Form II perfect, voice must not be erased | `V:II:PERF:PASS:3MP` | passive/form two-vote |
| `112:3:4` | `يُولَدْ` | `pending` | passive jussive under negation | `V:I:IMPF:PASS:JUSS:3MS:NEG-PENDING` | sarf + nahw two-vote |
| `36:78:3` | `يُحْيِي` | `pending` | proper-name vs finite verb collision | `V:IV:IMPF:ACT:3MS:POS-COLLISION-PENDING` | POS/source quarantine |
| `3:45:11` | `ٱلْمَسِيحُ` | `pending` | article + title + case metadata | `ART+N/TITLE:NOM:M:SG:DEF:PENDING` | title/article/case review |
| `90:3:1` | `وَوَالِدٍۢ` | `pending` | oath wāw + genitive nominal host | `OATH+N:GEN:M:SG:INDEF:PENDING` | oath attachment review |
| `33:32:3` | `لَسْتُنَّ` | `pending` | laysa-like finite form with 2fp subject marker | `V:LAYS:NEG:2FP:PRED-PENDING` | predicate/governance review |
| `10:83:11` | `فِرْعَوْنَ` | `rich_candidate` | proper-name metadata backfill | `PN:PHARAOH:CASE-PENDING` | case/role review before certification |

No row is `rich_certified`. VN-02 dogfood evidence is sufficient to shape rich metadata and blockers, not sufficient for live apply or family propagation.

## State Transitions

- `known_defect -> pending rich metadata`: `2:178:22`.
- `token_only_override -> token-only rich metadata`: `25:9:6`, `17:70:12`, `16:71:10`.
- `populated_uncertified -> pending rich metadata`: `112:3:4`, `3:45:11`, `90:3:1`, `33:32:3`.
- `pending/blocker -> pending rich metadata`: `36:78:3`.
- `populated_uncertified -> rich_candidate metadata`: `10:83:11`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-02 already updated:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/proper-noun.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/drills/homograph-regressions.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-02 already updated:

- `nahw/procedures/referent-context.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/drills/idafa-and-jar-majrur.md`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that readable English is not enough; passive voice, PP attachment, oath function, laysa agreement, and title/article/case state must be teachable.

Drills/evals/regressions: no new fixture needed. VN-02 already added repeated-defect drills and eval controls for passive voice, suffix-bearing verbs, proper/common collisions, and jar-majrūr/oath rows.

Production-bug lessons: no new lesson needed. The selected rows map to existing VN-02 lesson classes:

- `finite_verb_object_suffix_dictionary_leak`
- `passive_voice_erased_dictionary_leak`
- `proper_name_vs_finite_verb_collision`
- `proper_common_collision`
- `jar_majrur_noun_vs_verb_lexeme`

Renderer requirements: reinforced. Future Qamus UI must keep written tokens atomic while showing preposition/article/host, fāʾ/wāw functions, subject/object suffixes, passive voice, title/article, and proper-name metadata in the breakdown.

Future tranche routing: VN-RICH should continue prioritizing finite/passive verbs, preposition-host constructions, proper/common collisions, and laysa-like governance rows before broad positive backfill.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_02_standard.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_02_standard_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
