# VN-RICH-CERT-03 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-03 converts the existing `VN-RICH-03` standard rich-hover sample into an explicit certification
queue. It does not redo VN dogfood or rich metadata generation; it uses committed rich-hover rows as source review
material.

Input samples:

- `qamus/examples/rich_hover_vn_rich_03_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_03_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_03_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_03_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_03_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 12 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 5 |
| `blocked` | 0 |
| `token_only_override` | 7 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. VN-RICH-03 is a review/certification bridge for finite verb
suffixes, Form IV/Form X object-pronoun hovers, dīn concept and possessive rows, nominal/adjectival iʿrāb, bāʾ-host
attachment, possessive nominal suffixes, and article plus proper-group noun rows.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:26:139:2` | `فَأَهْلَكْنَاهُمْ` | so We destroyed them | `pending` | `pending` | `FA+V:IV:PERF:ACT:1P+OBJ.3MP:PENDING` | finite Form IV verb + subject/object suffix two-vote review |
| `quran:4:28:8` | `ضَعِيفًۭا` | weak | `pending` | `pending` | `N/ADJ:ACC:M:SG:INDEF:PENDING` | nominal/adjectival iʿrāb role review |
| `quran:1:4:3` | `ٱلدِّينِ` | the religion/judgment | `token_only_override` | `token_only_override` | `ART+N:GEN:DEF:SG:TOKEN-ONLY` | exact-address dīn concept/sense review |
| `quran:109:6:2` | `دِينُكُمْ` | your religion | `token_only_override` | `token_only_override` | `N:SG+POSS.2MP:TOKEN-ONLY` | possessive dīn token-only review |
| `quran:2:71:13` | `مُسَلَّمَةٌۭ` | sound / free from defect | `token_only_override` | `token_only_override` | `N/PTCP:NOM:F:SG:INDEF:TOKEN-ONLY` | nominal/adjectival concept-propagation review |
| `quran:2:128:3` | `مُسْلِمَيْنِ` | two submitting ones | `token_only_override` | `token_only_override` | `N/PTCP:DUAL:M:INDEF:CASE-PENDING:TOKEN-ONLY` | dual participial noun and case review |
| `quran:2:75:17` | `عَقَلُوهُ` | they understood it | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:3MP+OBJ.3MS:TOKEN-ONLY` | finite verb + object suffix review |
| `quran:13:6:1` | `وَيَسْتَعْجِلُونَكَ` | and they ask you to hasten | `pending` | `pending` | `CONJ+V:X:IMPF:ACT:3MP+OBJ.2MS:PENDING` | Form X finite verb + object suffix two-vote review |
| `quran:20:83:2` | `أَعْجَلَكَ` | made you hasten | `token_only_override` | `token_only_override` | `V:IV:PERF:ACT:3MS+OBJ.2MS:TOKEN-ONLY` | Form IV finite verb + object suffix review |
| `quran:16:91:2` | `بِعَهْدِ` | by the covenant | `pending` | `pending` | `P:BI+N:GEN:SG:PENDING` | bāʾ-host nominal attachment review |
| `quran:24:31:10` | `زِينَتَهُنَّ` | their adornment | `pending` | `pending` | `N:SG+POSS.3FP:PENDING` | possessive nominal suffix role/referent review |
| `quran:30:2:2` | `ٱلرُّومُ` | the Romans | `token_only_override` | `token_only_override` | `ART+PN:GROUP:NOM:DEF:TOKEN-ONLY` | proper group noun article/case review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `token_only_override` are exact-address review candidates only. Rows classified `pending` keep the
blocking sarf/nahw reason. No row is public-certified or live-applyable.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- fāʾ/wāw function plus finite verbs;
- Form IV and Form X finite hosts;
- subject and object suffix pronouns;
- article plus noun/proper-group noun rows;
- possessive nominal suffixes;
- bāʾ plus genitive nominal host;
- nominal/adjectival one-piece rows.

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

Sarf updates: no procedure change. VN-03 reinforces existing morphology rules for suffix-bearing finite verbs,
Form IV/Form X verb hosts, nominal derivatives, possessive suffixes, article/host segmentation, and proper/common
or concept collision guards.

Nahw updates: no procedure change. Existing gates already require two independent checks for bāʾ attachment,
iʿrāb-sensitive nominal/adjectival roles, suffix referents, and token-only overrides.

Curriculum updates: no new learner prose in this certification tranche. The rows are already represented in the VN
dogfood-to-curriculum synthesis as finite-verb dictionary leakage, suffix omission, preposition-host omission,
dīn concept leakage, and readable-English versus grammar-safe explanation.

Assessment/checkpoint updates: no new checkpoint. The examples reinforce current grading policy: a readable hover
cannot clear a row when suffix contribution, exact sense, or iʿrāb reasoning is pending.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as suffix omission, finite verb
dictionary leakage, concept/proper collision, and preposition-host omission.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind
owner-authorized preview/admin gates.

Future routing: continue RICH-CERT in bounded VN tranches. The next likely lane is `VN-RICH-CERT-04`, unless
explicit owner authorization starts RH-LIVE-00 preview scaffolding.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_03_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_03_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_03_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_03_standard.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage, live renderer, or live correctness claim.
