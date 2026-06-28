# P-RICH-CERT-01 Particle Function Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

P-RICH-CERT-01 converts the existing `P-RICH-01` particle/function rich-hover sample into an explicit certification
queue. It does not redo the particle dogfood review and it does not certify public hover correctness. It answers the
new question:

> Can this rich-hover row teach the learner what each Arabic piece contributes, and if not, what gate remains?

Input sample:

- `qamus/examples/rich_hover_p_rich_01_particle_function.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_01_particle_function_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_p_rich_cert_01_particle_function.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_01_particle_function_evidence.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_01_renderer_fixture.sample.jsonl`
- `tools/validate_rich_hover_certification.py`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 10 |
| `rich_certified` | 0 |
| `preview_only` | 7 |
| `pending` | 3 |
| `blocked` | 0 |
| `renderer_requirement` | 0 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. The tranche contains function particles, negation, exception,
interrogation, temporal particles, and mood-governing particles. Those rows remain grammar-sensitive and require
two independent source/nahw checks before rich certification.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:4:8` | `مِن` | from | `rich_candidate` | `preview_only` | `P:MIN` | two-vote PP/function review |
| `quran:2:9:5` | `وَمَا` | and not | `rich_candidate` | `preview_only` | `CONJ+MA:NEG` | two-vote `ما` function review |
| `quran:2:9:7` | `إِلَّآ` | except | `pending` | `pending` | `EXP:ILLA` | exception-frame review |
| `quran:2:30:1` | `وَإِذْ` | and when | `rich_candidate` | `preview_only` | `CONJ+T:IDH` | temporal/clause relation review |
| `quran:2:19:1` | `أَوْ` | or | `rich_candidate` | `preview_only` | `CONJ:AW` | disjunction/context review |
| `quran:2:210:1` | `هَلْ` | do | `pending` | `pending` | `INTG:HAL` | interrogative-frame review |
| `quran:2:6:1` | `إِنَّ` | indeed | `rich_candidate` | `preview_only` | `ACC:INNA` | ism/khabar inna review |
| `quran:112:3:1` | `لَمْ` | did not | `rich_candidate` | `preview_only` | `NEG:LAM:JUSS` | jussive-governor review |
| `quran:72:12:9` | `وَلَن` | and never | `rich_candidate` | `preview_only` | `CONJ+NEG:LAN:SUBJ` | subjunctive-governor review |
| `quran:68:8:1` | `فَلَا` | so do not | `pending` | `pending` | `FA+LA:NEG_OR_PRO` | prohibition/negation review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows with `preview_only` are useful rich-hover metadata previews, not certified decisions. Rows with `pending`
retain the original blocker and must not be promoted by English readability alone.

## Renderer Fixture

The renderer fixture gives future admin/preview work a stable segment payload while preserving the surface invariant:

```text
segments[].surface concatenates exactly to surface
```

This is not a live renderer claim. RH-LIVE remains owner-gated because live renderer work would touch the public app.

## Public Boundary

The certification sample public payload contains only:

```json
{"gloss": "...", "src": "qamus", "kind": "authored", "lang": "en"}
```

The evidence sidecar keeps internal evidence labels private and marks every row `public_exposable=false`. No source
labels, MCP labels, QAC labels, Quran.com labels, OCR snippets, or local paths are authorized for public output.

## Flywheel Impact

Sarf updates: no code or procedure change. This tranche reclassifies already-reviewed particle/function rows and does
not expose a new morphology rule.

Nahw updates: no procedure change. The rows still point to existing particle/function, governing-particle, exception,
and `ما` decision procedures; the next movement requires two-vote review, not new doctrine.

Curriculum updates: no new lesson. The existing rich-hover curriculum already teaches that a readable English hover is
not rich certification; this tranche supplies a validator-backed example of that rule.

Assessment/checkpoint updates: no new checkpoint. Current assessment rules already require function-token reasoning,
exact token address, public-safe output, and two-vote review for grammar-sensitive particle rows.

Progress/missed-error categories: no new category. These rows map to existing particle-function flattening, component
loss, readable-English-only, and source-agreement-with-wrong-reasoning categories.

Drills/evals/regressions: regression coverage added through `tools/validate_rich_hover_certification.py` and
`tools/check_regressions.py`.

Production-bug lessons: no new production-bug lesson. The source defects are already represented in the particle
dogfood lesson set.

Renderer requirements: preview fixture added, with no live renderer claim. Future RH-LIVE work can consume the fixture
only after owner authorization.

Future tranche-routing implications: continue RICH-CERT in bounded tranches. Do not begin live renderer/admin scaffolding or apply planning
from this artifact alone.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py --self-test
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_p_rich_cert_01_particle_function.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_p_rich_cert_01_particle_function_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_p_rich_cert_01_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_01_particle_function.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage or live correctness claim.
