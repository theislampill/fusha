# VN-RICH-CERT-06 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-06 converts the existing `VN-RICH-06` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English or component evidence into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_06_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_06_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_06_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_06_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_06_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 13 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 10 |
| `blocked` | 0 |
| `token_only_override` | 3 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. VN-RICH-06 is a review/certification bridge for function-token collisions (`مِن`/`مَن`/`مَنَّ`), component-only noun evidence, possessed noun suffixes, state nouns, finite verb dictionary leakage, locative/relational attachment, Form X finite verb wording, and passive participle nominal rows.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:4:8` | `مِن` | from | `pending` | `pending` | `P:MIN:FUNCTION-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:30:13` | `مَن` | whoever | `pending` | `pending` | `REL:MAN:FUNCTION-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:57:6` | `ٱلْمَنَّ` | the manna | `pending` | `pending` | `ART+N:DEF:SG:MANNA:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:25:17` | `ثَمَرَةٍۢ` | fruit | `pending` | `pending` | `N:FRUIT:GEN:INDEF:SG:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:6:141:19` | `ثَمَرِهِۦٓ` | its fruit | `pending` | `pending` | `N:FRUIT+POSS.3MS:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:10:3` | `مَّرَضٌۭ` | sickness | `pending` | `pending` | `N:STATE:NOM:INDEF:SG:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:16:3` | `ٱشْتَرَوُا۟` | they traded | `pending` | `pending` | `V:VIII:PERF:ACT:3MP:TRADE-SENSE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:17:9` | `حَوْلَهُۥ` | around it | `pending` | `pending` | `N/ADV:LOC+POSS.3MS:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:68:19` | `بَيْنَ` | between | `pending` | `pending` | `LOC:BETWEEN:ATTACHMENT-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:90:24` | `غَضَبٍۢ` | wrath | `token_only_override` | `token_only_override` | `N/MASDAR:GEN:INDEF:ANGER:TOKEN-ONLY` | exact-address review plus owner-approved preview gate |
| `quran:2:42:2` | `تَلْبِسُوا۟` | you confuse | `token_only_override` | `token_only_override` | `V:I:IMPF:ACT:2MP:MOOD-PENDING:TOKEN-ONLY` | exact-address review plus owner-approved preview gate |
| `quran:2:60:2` | `ٱسْتَسْقَىٰ` | he asked for water | `token_only_override` | `token_only_override` | `V:X:PERF:ACT:3MS:REQUEST-WATER:TOKEN-ONLY` | exact-address review plus owner-approved preview gate |
| `quran:1:7:6` | `ٱلْمَغْضُوبِ` | those subject to wrath | `pending` | `pending` | `ART+PARTICIPLE:PASS:GEN:DEF:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `pending` keep their blocking sarf/nahw reason. Rows classified `token_only_override` are exact-address review candidates only. No row is public-certified or live-applyable.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- one-piece function tokens and relation tokens;
- article plus noun or participle host;
- nominal hosts with possessive suffixes;
- finite verb hosts with subject endings;
- Form X finite verb rows;
- passive-participle-like nominal rows.

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

Evidence labels remain in the internal sidecar with `public_exposable=false`. No source labels, MCP labels, QAC labels, Quran.com labels, OCR snippets, or local paths are authorized for public output.

## Flywheel Impact

Sarf updates: no procedure change. VN-06 reinforces existing morphology rules for finite verb features, Form X wording, noun/maṣdar versus verb prose, possessed suffixes, passive participles, article/host segmentation, and component-only blocker rows.

Nahw updates: no procedure change. Existing gates already require two independent checks for function-token collisions, PP/locative relation attachment, suffix referents, possessed noun relations, passive nominal roles, and token-only overrides.

Curriculum updates: no new learner prose in this certification tranche. These rows are already represented in the VN dogfood-to-curriculum synthesis as readable-English-not-certification, function-token collision, suffix omission, finite-verb dictionary leakage, maṣdar/participle distinction, and component-only evidence traps.

Assessment/checkpoint updates: no new checkpoint. These rows reinforce the current level-clearance policy: a learner or agent cannot clear a row from readable English alone when function, attachment, suffix referent, passive nominal role, or exact-address reasoning is pending.

Progress/missed-error categories: no new category. These rows map to existing function-token collision, suffix omission,
finite-verb dictionary leakage, maṣdar/participle distinction, passive nominal role, component-only trap, and token-only override categories.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as function-token flattening, finite verb dictionary leakage, suffix omission, nominal POS leakage, component-only evidence traps, and readable-English versus grammar-safe explanation.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind owner-authorized preview/admin gates.

Future tranche-routing implications: continue RICH-CERT in bounded VN tranches. The next likely lane is `VN-RICH-CERT-07`, unless explicit owner authorization starts RH-LIVE-00 preview scaffolding.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_06_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_06_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_06_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_06_standard.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover coverage, live renderer, or live correctness claim.
