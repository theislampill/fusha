# P-RICH-03 An/Inna Family Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, service, mirror, renderer, or hover ledger was changed.

## Scope

P-RICH-03 targets the `أَنْ` / `أَنَّ` / `إِنْ` / `إِنَّ` family and close prefixed composites. These are high-risk because ordinary lookup keys can collapse hamza seat, shadda, and clause frame:

- light `أَنْ` versus shadda-bearing `أَنَّ`
- light `إِنْ` conditional versus light `إِنْ` negating frame
- `وَإِن` versus `وَإِنَّ`
- `بِأَنَّ` where prefixed bāʾ must not disappear
- `أَفَلَا` where interrogative hamza, fāʾ, and lā all contribute

Sample artifacts:

- `qamus/examples/rich_hover_p_rich_03_an_inna_family.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_03_an_inna_family_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `28:27:4` | `أَنْ` | `rich_candidate` | light subordinator, not emphatic particle | `SUB:AN:LIGHT` | following verb/clause review |
| `22:18:3` | `أَنَّ` | `rich_candidate` | shadda-bearing anna frame | `ACC:ANNA` | ism/khabar frame review |
| `10:48:5` | `إِن` | `rich_candidate` | conditional candidate | `COND:IN` | sharṭ/jawāb review |
| `35:23:1` | `إِنْ` | `pending` | negating in frame | `NEG:IN:FRAME_PENDING` | exception/negation-frame review |
| `2:198:21` | `وَإِن` | `pending` | connector plus conditional candidate | `CONJ+COND:WA_IN:PENDING` | shadda/frame collision review |
| `2:74:12` | `وَإِنَّ` | `rich_candidate` | connector plus inna frame | `CONJ+ACC:WA_INNA` | ism/khabar frame review |
| `22:6:2` | `بِأَنَّ` | `pending` | prefixed bāʾ plus anna clause | `P:BI+ACC:ANNA:CLAUSE_PENDING` | causal/prepositional scope review |
| `4:82:1` | `أَفَلَا` | `pending` | interrogative hamza plus fāʾ plus lā | `INTG+FA+LA:NEG_FRAME_PENDING` | question/negation-frame review |

No row is `rich_certified`. A readable English hover does not certify a hidden particle state.

## State Transitions

- `populated_uncertified -> rich_candidate`: `أَنْ`, `أَنَّ`, conditional `إِن`, `وَإِنَّ`.
- `populated_uncertified -> pending`: negative-frame `إِنْ`, `وَإِن`, `بِأَنَّ`, `أَفَلَا`.

The movement is that every row now carries an exact parse lane, segment contribution, and fail-closed gate.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The sidecar is internal-only and does not authorize public source labels. Public hover output remains authored Qamus wording only.

## Flywheel Impact

Sarf updates: no repo change. The current strict-surface and homograph rules already cover hamza seat and shadda risk.

Nahw updates: no repo change. The existing procedures already encode this family:

- `nahw/procedures/particle-function-decision.md`
- `nahw/procedures/conditionals.md`
- `nahw/procedures/governing-particle-mood-review.md`
- `nahw/references/particle-functions.md`

Curriculum updates: no new prose needed in this tranche. Existing particle drills already teach `أَنْ` / `إِنَّ` / `إِنْ`; this tranche adds exact rich-hover metadata examples.

Drills/evals/regressions: no new drill added. Existing fixtures cover `أَنْ`, `أَنَّ`, `إِنَّ`, `إِنْ`, `أَفَلَا`, and `بِأَنَّ`-style prefix preservation.

Production-bug lessons: no new lesson added. The repeated defect class is already present as particle-function flattening and component-loss in the dogfood lessons.

Renderer requirements: reinforced by example. The renderer must display the visible token intact while showing separate scrubbed segment rows for hamza/fāʾ/lā, bāʾ+anna, and connector+particle compounds.

Future tranche routing: continue P-RICH with remaining particles such as `أَلَا`/`أَلَّا`, `لَا` functions, `إِذَا`/`إِذْ` temporal frames, and remaining prefixed negation/condition families before moving to VN-RICH calibration.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_03_an_inna_family.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_p_rich_03_an_inna_family_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
