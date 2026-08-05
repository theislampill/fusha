# P-RICH-04 Lā / Alā / Idhā Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, service, mirror, renderer, or hover ledger was changed.

## Scope

P-RICH-04 targets high-impact function states that are easy to flatten into readable but non-teaching English:

- `لَآ` / `لَا` simple negation versus lā of genus
- `أَلَا` opening attention versus `أَلَّا` assimilated `أَنْ` + `لَا`
- `إِذَا` / `وَإِذَا` temporal-condition frames versus inferential/result `إِذًا`

Sample artifacts:

- `qamus/examples/rich_hover_p_rich_04_la_temporal_family.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_04_la_temporal_family_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `109:2:1` | `لَآ` | `rich_candidate` | simple verbal negation, not an omnibus lā inventory gloss | `NEG:LA:VERBAL` | clause scope review before propagation |
| `2:2:3` | `لَا` | `pending` | lā of genus requires noun/khabar frame | `NEG:LA_OF_GENUS:CASE_PENDING` | case/frame review |
| `39:3:1` | `أَلَا` | `rich_candidate` | opening attention particle | `ATTN:ALA:ISTIFTAH` | distinguish from `أَلَّا` in family routing |
| `4:3:3` | `أَلَّا` | `rich_candidate` | assimilated subordinator plus negation | `SUB+NEG:ALLA:AN_LA` | following clause/mood review before propagation |
| `113:3:4` | `إِذَا` | `pending` | temporal-condition state, not inferential `إِذًا` | `T:IDHA:TEMP_COND:PENDING` | temporal-condition relation review |
| `83:30:1` | `وَإِذَا` | `pending` | connector plus temporal condition | `CONJ+T:WA_IDHA:TEMP_COND_PENDING` | answer/result relation review |

No row is `rich_certified`. A readable English hover does not certify a hidden particle state.

## State Transitions

- `populated_uncertified -> rich_candidate`: simple verbal `لَآ`, `أَلَا`, `أَلَّا`.
- `populated_uncertified -> pending`: lā-of-genus frame, standalone temporal `إِذَا`, and prefixed `وَإِذَا`.

The movement is that every row now carries an exact function lane, segment contribution, learner explanation, and fail-closed gate.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The sidecar is internal-only and does not authorize public source labels. Public hover output remains authored Qamus wording only.

## Flywheel Impact

Sarf updates: no repo change. Particles in this tranche are ḥarf rows with no root/pattern morphology; current strict-surface and component-preservation rules already cover the morphology boundary.

Nahw updates: no repo change. Existing procedures already encode the reusable doctrine:

- `nahw/procedures/particle-function-decision.md`
- `nahw/procedures/conditionals.md`
- `nahw/references/particle-functions.md`
- `nahw/drills/particle-disambiguation.md`

Curriculum updates: no new prose needed in this tranche. Current curriculum already teaches `لَا`, `أَلَا`/`أَلَّا`, and `إِذَا`; this tranche adds exact rich-hover metadata examples.

Drills/evals/regressions: no new drill added. Existing particle-function evals and drills cover lā of genus, `أَلَا`/`أَلَّا`, and `إِذَا`/`إِذًا` collision risk.

Production-bug lessons: no new lesson added. The repeated defect classes are already represented as particle-function flattening, state collision, and component-loss lessons.

Renderer requirements: reinforced by example. The renderer must show the Qurʾānic token intact while exposing scrubbed segment rows for `لَا`, `أَلَّا`, and `وَإِذَا`.

Future tranche routing: P-RICH can now move toward VN-RICH calibration after any remaining particle rows are covered by existing P-RICH-01 through P-RICH-04 examples.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_04_la_temporal_family.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_p_rich_04_la_temporal_family_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
