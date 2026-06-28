# VN-RICH-CERT-04 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-04 converts the existing `VN-RICH-04` standard rich-hover sample into an explicit certification
queue. It does not redo VN dogfood or rich metadata generation; it uses committed rich-hover rows as source review
material.

Input samples:

- `qamus/examples/rich_hover_vn_rich_04_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_04_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_04_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_04_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_04_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 8 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 7 |
| `blocked` | 0 |
| `token_only_override` | 1 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. VN-RICH-04 is a review/certification bridge for fāʾ plus finite
Form IV verb and object suffix, imperative verb suffix rows, Qurʾānic custom nouns, definite noun versus verb-family
prose, passive voice preservation, and exact-address article plus nominal host review.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:12:42:10` | `فَأَنسَىٰهُ` | so he made him forget | `pending` | `pending` | `FA+V:IV:PERF:ACT:3MS+OBJ.3MS:PENDING` | fāʾ + Form IV finite verb + object suffix two-vote review |
| `quran:15:3:1` | `ذَرْهُمْ` | leave them | `pending` | `pending` | `V:I:IMP:ACT:2MS+OBJ.3MP:PENDING` | imperative host + object suffix two-vote review |
| `quran:10:15:16` | `بَدِّلْهُ` | change it | `pending` | `pending` | `V:II:IMP:ACT:2MS+OBJ.3MS:PENDING` | Form II imperative host + object suffix two-vote review |
| `quran:5:103:7` | `سَآئِبَةٍۢ` | a freed-roaming she-camel custom | `pending` | `pending` | `N:CUSTOM:GEN:F:SG:INDEF:PENDING` | custom noun case and role review |
| `quran:5:103:9` | `وَصِيلَةٍۢ` | and a wasilah custom | `pending` | `pending` | `CONJ+N:CUSTOM:GEN:F:SG:INDEF:PENDING` | wāw plus custom noun role review |
| `quran:15:9:4` | `الذِّكْرَ` | the reminder | `pending` | `pending` | `ART+N:ACC:DEF:SG:PENDING` | definite noun versus verb-family prose review |
| `quran:6:118:3` | `ذُكِرَ` | was mentioned | `pending` | `pending` | `V:I:PERF:PASS:3MS:PENDING` | passive finite verb POS/voice review |
| `quran:26:165:2` | `ٱلذُّكْرَانَ` | the males | `token_only_override` | `token_only_override` | `ART+N:ACC:M:PL:DEF:TOKEN-ONLY` | exact-address article, number, and role review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `pending` keep the blocking sarf/nahw reason and require two independent checks before certification.
The row classified `token_only_override` is exact-address review material only. No row is public-certified or
live-applyable.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- fāʾ connector plus finite Form IV verb host;
- imperative hosts with attached object pronouns;
- prefixed wāw plus custom noun host;
- definite article plus noun host;
- passive finite verb host;
- one-piece custom noun rows.

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

Sarf updates: no procedure change. VN-04 reinforces existing morphology rules for imperative hosts, Form II/Form IV
verbs, passive finite verbs, attached object suffixes, article/host segmentation, and noun-versus-verb-family
collisions.

Nahw updates: no procedure change. Existing gates already require two independent checks for suffix referents,
custom-noun case/role metadata, passive verb reasoning, and token-only overrides.

Curriculum updates: no new learner prose in this certification tranche. The rows are already represented in the VN
dogfood-to-curriculum synthesis as suffix omission, finite-verb dictionary leakage, passive voice loss, article/host
segmentation, and readable-English versus grammar-safe explanation.

Assessment/checkpoint updates: no new checkpoint. These rows reinforce the current grading rule: an English gloss that
looks readable cannot clear a row when suffix contribution, passive voice, POS, or iʿrāb reasoning is pending.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as suffix omission, finite verb
dictionary leakage, passive voice loss, and noun/verb/POS collision.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind
owner-authorized preview/admin gates.

Future routing: continue RICH-CERT in bounded VN tranches. The next likely lane is `VN-RICH-CERT-05`, unless explicit
owner authorization starts RH-LIVE-00 preview scaffolding.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_04_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_04_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_04_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_04_standard.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage, live renderer, or live correctness claim.
