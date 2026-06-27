# P-RICH-CERT-04 Lā / Alā / Idhā Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

P-RICH-CERT-04 converts the existing `P-RICH-04` lā / alā / idhā rich-hover sample into an explicit
certification queue.

Input sample:

- `qamus/examples/rich_hover_p_rich_04_la_temporal_family.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_04_la_temporal_family_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_p_rich_cert_04_la_temporal_family.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_04_la_temporal_family_evidence.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_04_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 6 |
| `rich_certified` | 0 |
| `preview_only` | 3 |
| `pending` | 3 |
| `blocked` | 0 |
| `token_only_override` | 0 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. The family is sensitive to simple verbal negation versus lā of
genus, `أَلَا` versus `أَلَّا`, and `إِذَا` temporal condition versus `إِذًا` inferential/result usage. Readable
English does not certify those hidden particle states.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:109:2:1` | `لَآ` | not | `rich_candidate` | `preview_only` | `NEG:LA:VERBAL` | clause-scope review |
| `quran:2:2:3` | `لَا` | no | `pending` | `pending` | `NEG:LA_OF_GENUS:CASE_PENDING` | lā-of-genus case/frame review |
| `quran:39:3:1` | `أَلَا` | indeed | `rich_candidate` | `preview_only` | `ATTN:ALA:ISTIFTAH` | attention-particle state review |
| `quran:4:3:3` | `أَلَّا` | that ... not | `rich_candidate` | `preview_only` | `SUB+NEG:ALLA:AN_LA` | subordinator plus negation frame review |
| `quran:113:3:4` | `إِذَا` | when | `pending` | `pending` | `T:IDHA:TEMP_COND:PENDING` | temporal-condition relation review |
| `quran:83:30:1` | `وَإِذَا` | and when | `pending` | `pending` | `CONJ+T:WA_IDHA:TEMP_COND_PENDING` | condition answer/result relation review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `preview_only` are valid rich metadata previews, not public-certified hovers. Rows classified
`pending` carry unresolved grammar-sensitive function/frame review and must not move by surface or parse-key family.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- whole-token negative and attention particles;
- assimilated subordinator plus negation in `أَلَّا`;
- whole-token and prefixed temporal-condition particles in `إِذَا` and `وَإِذَا`.

The fixture preserves:

```text
segments[].surface concatenates exactly to surface
```

It does not assert current live renderer support.

## Public Boundary

The public payload stays Qamus-authored only:

```json
{"gloss": "...", "src": "qamus", "kind": "authored", "lang": "en"}
```

Evidence labels remain in the internal sidecar with `public_exposable=false`. No source labels, MCP labels, QAC labels,
Quran.com labels, OCR snippets, or local paths are authorized for public output.

## Flywheel Impact

Sarf updates: no procedure change. These are ḥarf rows; current strict-surface and component-preservation doctrine
already covers the morphology boundary.

Nahw updates: no procedure change. Existing particle-function, negation, conditional, and temporal-condition
procedures already route these rows. This tranche preserves the unresolved gates instead of creating new rules.

Curriculum updates: no new learner prose. Existing particle and rich-hover curriculum already teaches the distinction
between readable English and certified hidden state.

Assessment/checkpoint updates: no new checkpoint. The rows reinforce current two-vote grading policy for particle
function, negation, and condition/result relations.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated defect class is already represented as particle-function
flattening, component loss, and readable-English/wrong-reasoning traps.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only after
owner authorization.

Future routing: continue RICH-CERT in bounded tranches. The next likely lane is VN-RICH-CERT calibration from known
verb/noun hard cases, unless another existing P-RICH source sample appears.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_p_rich_cert_04_la_temporal_family.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_p_rich_cert_04_la_temporal_family_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_p_rich_cert_04_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_04_la_temporal_family.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage or live correctness claim.
