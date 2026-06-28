# VN-RICH-CERT-01 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-01 converts the existing `VN-RICH-01` standard rich-hover sample into an explicit certification queue.
It does not redo VN dogfood or rich metadata generation; it uses committed rich-hover rows as source review material.

Input samples:

- `qamus/examples/rich_hover_vn_rich_01_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_01_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_01_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_01_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_01_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 8 |
| `rich_certified` | 0 |
| `preview_only` | 1 |
| `pending` | 2 |
| `blocked` | 0 |
| `token_only_override` | 5 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. VN-RICH-01 is a review/certification bridge for weak-root verbs,
passive participles, suffix-bearing finite verbs, nominal/maṣdar rows, comparison nouns, and same-surface
context-sensitive nouns. Readable English is not enough to certify those states for live rich hover use.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:83:25:4` | `مَّخْتُومٍ` | sealed | `pending` | `pending` | `N/PTCP:GEN:M:SG:INDEF:PENDING` | passive-participle derivative and iʿrāb review |
| `quran:35:40:28` | `يَعِدُ` | promises | `token_only_override` | `token_only_override` | `V:I:IMPF:ACT:3MS:WEAK-WAW` | exact-address weak-root verb review |
| `quran:55:44:4` | `حَمِيمٍ` | scalding water | `pending` | `pending` | `N:GEN:M:SG:INDEF:SENSE-CONTEXT-PENDING` | same-surface sense/context review |
| `quran:5:38:8` | `نَكَٰلًۭا` | as a deterrent | `token_only_override` | `token_only_override` | `N:ACC:M:SG:INDEF:SENSE-TOKEN-ONLY` | exact-address nominal role review |
| `quran:2:275:19` | `مِثْلُ` | like | `token_only_override` | `token_only_override` | `N:NOM:M:SG:CONSTRUCT:COMPARISON:TOKEN-ONLY` | comparison noun / construct review |
| `quran:2:187:49` | `تُبَٰشِرُوهُنَّ` | be intimate with them | `token_only_override` | `token_only_override` | `V:III:IMPF:ACT:JUSS:2MP+SUBJ.2MP+OBJ.3FP` | suffix/referent/mood two-vote review |
| `quran:13:31:45` | `وَعْدُ` | promise | `token_only_override` | `token_only_override` | `N/MASDAR:NOM:M:SG:CONSTRUCT:TOKEN-ONLY` | maṣdar / iḍāfa review |
| `quran:78:34:2` | `دِهَاقًۭا` | full, overflowing | `rich_candidate` | `preview_only` | `N/ADJ:ACC:M:SG:INDEF:NO-SUFFIX` | false-suffix no-op plus syntactic-role review |

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
blocking sarf/nahw reason. The single `preview_only` row is a renderer/metadata preview, not a public-certified hover.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- suffix-bearing Form III imperfect verb display;
- weak-root finite verb display;
- passive participle / nominal derivative display;
- maṣdar and comparison noun display;
- false suffix no-op display where tanwīn/case ending is not a pronoun.

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

Sarf updates: no procedure change. VN-01 already installed the reusable morphology doctrine for weak roots, finite
verbs, suffix-bearing verbs, passive participles, maṣdar rows, and false suffix splits.

Nahw updates: no procedure change. Existing gates already require two independent checks for iʿrāb, comparison/
construct roles, suffix referents, and token-only override rows.

Curriculum updates: no new learner prose in this certification tranche. The rows are already represented in the VN
dogfood-to-curriculum synthesis as finite-verb leakage, suffix omission, nominal/POS leakage, and readable-English
versus grammar-safe explanation.

Assessment/checkpoint updates: no new checkpoint. The examples reinforce current grading policy: level advancement
cannot rely on readable English when the hidden sarf/nahw state is not explained.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as finite verb dictionary-gloss
leakage, object suffix omission, nominal derivative leakage, and same-surface wrong-sense traps.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind
owner-authorized preview/admin gates.

Future routing: continue RICH-CERT in bounded VN tranches. The next likely lane is `VN-RICH-CERT-02`, unless
explicit owner authorization starts RH-LIVE-00 preview scaffolding.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_01_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_01_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_01_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_01_standard.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage, live renderer, or live correctness claim.
