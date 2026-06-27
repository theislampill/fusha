# P-RICH-CERT-02 Particle Collision Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

P-RICH-CERT-02 converts the existing `P-RICH-02` particle collision and composite-function rich-hover sample into an
explicit certification queue.

Input sample:

- `qamus/examples/rich_hover_p_rich_02_particle_collision.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_02_particle_collision_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_p_rich_cert_02_particle_collision.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_02_particle_collision_evidence.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_02_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 8 |
| `rich_certified` | 0 |
| `preview_only` | 1 |
| `token_only_override` | 1 |
| `pending` | 4 |
| `blocked` | 2 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. This tranche is about surface-neighbor separation and composite
particle states. It must not promote a readable English hover into rich certification when the hidden grammar state
still depends on strict-surface, clause-frame, mood/governor, or token-only review.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:145:30` | `إِذًۭا` | then | `pending` | `blocked` | `RES:IDHAN` | strict-surface collision and clause-relation review |
| `quran:2:28:7` | `ثُمَّ` | then | `rich_candidate` | `preview_only` | `CONJ:THUMMA` | sequence-scope review if the hover teaches clause relation |
| `quran:2:26:24` | `مَاذَآ` | what | `pending` | `pending` | `INTG:MADHA:PENDING` | `ما` + clause-frame classification |
| `quran:3:153:14` | `لِّكَيْلَا` | so that not | `token_only_override` | `token_only_override` | `LAM:PURP+SUB:KAY+NEG:LA` | exact-address purpose/subordinator/negation review |
| `quran:2:258:21` | `أَنَا۠` | I | `pending` | `blocked` | `PRON:1S:INDEP` | strict-surface pronoun/subordinator collision review |
| `quran:2:213:37` | `لِمَا` | for what | `pending` | `pending` | `P:LI+MA:FUNC_PENDING` | lām relation plus `ما` function and attachment review |
| `quran:86:4:4` | `لَّمَّا` | surely over | `pending` | `pending` | `PART:LAMMA:FUNC_PENDING` | exact lammā construction review |
| `quran:3:47:19` | `فَإِنَّمَا` | then only | `pending` | `pending` | `FA+INNA+MA:RESTRICTIVE_PENDING` | restriction-scope and compound-particle review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `blocked` carry `never_auto_resolve` evidence from the source rich-hover row. These must not be moved by
parse key or surface-family propagation. The token-only row preserves exact-address scope and likewise cannot propagate
by surface or parse family.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and the existing scrubbed segment roles, while preserving
the exact surface invariant:

```text
segments[].surface concatenates exactly to surface
```

This fixture is preview/admin material only. It does not assert current live renderer support.

## Public Boundary

The public payload stays Qamus-authored only:

```json
{"gloss": "...", "src": "qamus", "kind": "authored", "lang": "en"}
```

Evidence labels remain in the internal sidecar with `public_exposable=false`. No source labels, MCP labels, QAC labels,
Quran.com labels, OCR snippets, or local paths are authorized for public output.

## Flywheel Impact

Sarf updates: no procedure change. The strict-surface and homograph doctrine is already present in
`sarf/procedures/homograph-risk.md`.

Nahw updates: no procedure change. Existing particle-function, `ما`, conditional, and governing-particle procedures
already route these rows. P-RICH-CERT-02 preserves their blocker state rather than creating new doctrine.

Curriculum updates: no new learner prose in this tranche. These rows instantiate the existing lesson that lookalike
surfaces need hidden-state separation before certification.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The source collision classes were already captured in the particle dogfood and
VN dogfood lesson samples.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only after
owner authorization.

Future routing: continue RICH-CERT in bounded tranches. Rows with `never_auto_resolve` should be routed to strict
surface collision review before any certification or apply-readiness planning.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_p_rich_cert_02_particle_collision.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_p_rich_cert_02_particle_collision_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_p_rich_cert_02_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_02_particle_collision.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage or live correctness claim.
