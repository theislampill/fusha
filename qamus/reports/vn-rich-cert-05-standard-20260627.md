# VN-RICH-CERT-05 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-05 converts the existing `VN-RICH-05` standard rich-hover sample into an explicit certification
queue. It does not redo VN dogfood or rich metadata generation; it uses committed rich-hover rows as source review
material.

Input samples:

- `qamus/examples/rich_hover_vn_rich_05_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_05_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_05_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_05_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_05_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 9 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 3 |
| `blocked` | 0 |
| `token_only_override` | 6 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. VN-RICH-05 is a review/certification bridge for suffix-bearing
finite verbs, stacked fāʾ/future/verb/pronoun composition, noun-versus-verb prose, body-part possessive rows,
contextual `رجال` wording, nominal derivative rows, and false-lām segmentation controls.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:4:11:1` | `يُوصِيكُمُ` | He instructs you | `token_only_override` | `token_only_override` | `V:IV:IMPF:ACT:3MS+OBJ.2MP:TOKEN-ONLY` | exact-address finite verb + object suffix review |
| `quran:60:8:15` | `تَبَرُّوهُمْ` | act kindly toward them | `token_only_override` | `token_only_override` | `V:I/II:IMPF:ACT:2MP+OBJ.3MP:TOKEN-ONLY` | exact-address finite verb + object suffix review |
| `quran:2:137:15` | `فَسَيَكْفِيكَهُمُ` | then He will suffice you against them | `pending` | `pending` | `FA+FUT+V:I:IMPF:ACT:3MS+OBJ.2MS+OBJ.3MP:PENDING` | stacked clitic/suffix two-vote review |
| `quran:12:3:5` | `ٱلْقَصَصِ` | the story | `token_only_override` | `token_only_override` | `ART+N:GEN/ACC:DEF:SG:PENDING` | exact-address noun case and sense review |
| `quran:12:21:25` | `غَالِبٌ` | prevailing | `token_only_override` | `token_only_override` | `N/ADJ:ACTIVE-PARTICIPLE:NOM:M:SG:INDEF:TOKEN-ONLY` | nominal derivative / active-participle review |
| `quran:2:239:3` | `فَرِجَالًا` | then on foot | `pending` | `pending` | `FA+N:ACC:INDEF:RAJUL-FAMILY:PENDING` | contextual `رجل` family and fāʾ review |
| `quran:10:37:14` | `يَدَيْهِ` | before it | `pending` | `pending` | `N:DUAL:BODY-PART+POSS.3MS:PENDING` | dual body-part idiom/referent review |
| `quran:10:26:7` | `وُجُوهَهُمْ` | their faces | `token_only_override` | `token_only_override` | `N:PL:BODY-PART+POSS.3MP:TOKEN-ONLY` | body-part possessor/referent review |
| `quran:37:11:5` | `لَّازِبٍ` | sticky clay | `token_only_override` | `token_only_override` | `ADJ:GEN:INDEF:FALSE-LAM:TOKEN-ONLY` | false-lām clitic guard and adjective review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `pending` keep their blocking sarf/nahw reason. Rows classified `token_only_override` are
exact-address review candidates only. No row is public-certified or live-applyable.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- finite verb hosts with attached object pronouns;
- stacked fāʾ, future prefix, finite host, and two attached pronouns;
- article plus noun host;
- nominal/active-participle-like one-piece rows;
- fāʾ plus contextual nominal host;
- body-part nouns with possessive suffixes;
- false-lām adjective rows.

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

Sarf updates: no procedure change. VN-05 reinforces existing morphology rules for suffix-bearing finite verbs,
stacked clitics, nominal derivatives, body-part possessive nouns, article/host segmentation, and false-clitic
controls.

Nahw updates: no procedure change. Existing gates already require two independent checks for suffix referents,
body-part idiom/referent rows, contextual `رجال` wording, fāʾ relation, and token-only overrides.

Curriculum updates: no new learner prose in this certification tranche. The rows are already represented in the VN
dogfood-to-curriculum synthesis as suffix omission, finite-verb dictionary leakage, body-part relational nouns,
component-only traps, and readable-English versus grammar-safe explanation.

Assessment/checkpoint updates: no new checkpoint. These rows reinforce current level-clearance policy: a learner or
agent cannot clear a row from readable English alone when suffixes, false clitics, body-part idiom, or exact role
reasoning are pending.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as suffix omission, finite verb
dictionary leakage, false clitic split, body-part relational noun, and component-only evidence traps.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind
owner-authorized preview/admin gates.

Future routing: continue RICH-CERT in bounded VN tranches. The next likely lane is `VN-RICH-CERT-06`, unless explicit
owner authorization starts RH-LIVE-00 preview scaffolding.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_05_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_05_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_05_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_05_standard.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage, live renderer, or live correctness claim.
