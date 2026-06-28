# P-RICH-CERT-03 An/Inna Family Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

P-RICH-CERT-03 converts the existing `P-RICH-03` `أَنْ` / `أَنَّ` / `إِنْ` / `إِنَّ` family rich-hover sample into an
explicit certification queue.

Input sample:

- `qamus/examples/rich_hover_p_rich_03_an_inna_family.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_03_an_inna_family_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_p_rich_cert_03_an_inna_family.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_03_an_inna_family_evidence.sample.jsonl`
- `qamus/examples/rich_cert_p_rich_cert_03_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 8 |
| `rich_certified` | 0 |
| `preview_only` | 4 |
| `pending` | 4 |
| `blocked` | 0 |
| `token_only_override` | 0 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. The family is sensitive to hamza seat, shadda, conditional versus
negative frame, accusative-particle scope, and prefixed particles. A readable English hover does not certify the
hidden grammar state.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:28:27:4` | `أَنْ` | that | `rich_candidate` | `preview_only` | `SUB:AN:LIGHT` | light-subordinator clause review |
| `quran:22:18:3` | `أَنَّ` | that | `rich_candidate` | `preview_only` | `ACC:ANNA` | ism/khabar anna frame review |
| `quran:10:48:5` | `إِن` | if | `rich_candidate` | `preview_only` | `COND:IN` | sharṭ/jawāb conditional review |
| `quran:35:23:1` | `إِنْ` | not | `pending` | `pending` | `NEG:IN:FRAME_PENDING` | negation/exception-frame review |
| `quran:2:198:21` | `وَإِن` | and if | `pending` | `pending` | `CONJ+COND:WA_IN:PENDING` | connector plus in-function collision review |
| `quran:2:74:12` | `وَإِنَّ` | and indeed | `rich_candidate` | `preview_only` | `CONJ+ACC:WA_INNA` | connector plus inna-frame review |
| `quran:22:6:2` | `بِأَنَّ` | because | `pending` | `pending` | `P:BI+ACC:ANNA:CLAUSE_PENDING` | bāʾ plus anna-clause scope review |
| `quran:4:82:1` | `أَفَلَا` | then do not | `pending` | `pending` | `INTG+FA+LA:NEG_FRAME_PENDING` | interrogative/fāʾ/lā frame review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `preview_only` are valid rich metadata previews, not public-certified hovers. Rows classified `pending`
carry unresolved grammar-sensitive function/frame review and must not move by surface or parse-key family.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- whole-token subordinating, conditional, negative, and accusative particles;
- connector + particle composites such as `وَإِنَّ`;
- preposition + particle/clause composites such as `بِأَنَّ`;
- interrogative + fāʾ + lā composites such as `أَفَلَا`.

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

Sarf updates: no procedure change. Strict-surface and shadda/hamza-risk doctrine already lives in the sarf homograph
and clitic-host procedures.

Nahw updates: no procedure change. Existing particle-function, conditional, governing-particle, and `ما` procedures
already route these rows. The certification queue preserves the unresolved gates instead of creating new rules.

Curriculum updates: no new learner prose. Existing particle and rich-hover curriculum already teaches the distinction
between readable English and certified hidden state.

Assessment/checkpoint updates: no new checkpoint. Current assessment rules already require exact particle function,
clause relation, and two-vote review for `أَن`/`إِن`/`إِنَّ`-family rows before level clearance.

Progress/missed-error categories: no new category. These rows map to existing particle-function flattening,
subordinator/accusative-particle confusion, readable-English-only, and component-loss categories.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated defect class is already represented as particle-function
flattening, component loss, and readable-English/wrong-reasoning traps.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only after
owner authorization.

Future tranche-routing implications: continue RICH-CERT in bounded tranches. The next likely tranche is P-RICH-CERT-04 for `لَا` and
temporal/negative function families.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_p_rich_cert_03_an_inna_family.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_p_rich_cert_03_an_inna_family_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_p_rich_cert_03_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_03_an_inna_family.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage or live correctness claim.
