# VN-RICH-CERT-02 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-02 converts the existing `VN-RICH-02` standard rich-hover sample into an explicit certification queue.
It does not redo VN dogfood or rich metadata generation; it uses committed rich-hover rows as source review material.

Input samples:

- `qamus/examples/rich_hover_vn_rich_02_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_02_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_02_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_02_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_02_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 10 |
| `rich_certified` | 0 |
| `preview_only` | 1 |
| `pending` | 6 |
| `blocked` | 0 |
| `token_only_override` | 3 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. VN-RICH-02 is a review/certification bridge for bāʾ-host PP
attachment, root/POS collisions, Form II active/passive contrast, passive jussive under negation, title/article
case state, oath wāw, and laysa-like finite agreement.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:178:22` | `بِٱلْمَعْرُوفِ` | by what is right/customary | `pending` | `pending` | `P:BI+ART+N/PTCP:GEN:DEF:PENDING` | bāʾ-host PP attachment review |
| `quran:25:9:6` | `فَضَلُّوا۟` | so they went astray | `token_only_override` | `token_only_override` | `FA+V:I:PERF:ACT:3MP:ROOT-DLL:TOKEN-ONLY` | exact-address root/POS quarantine review |
| `quran:17:70:12` | `وَفَضَّلْنَٰهُمْ` | and We favored them | `token_only_override` | `token_only_override` | `CONJ+V:II:PERF:ACT:1P+OBJ.3MP` | Form II finite verb + object suffix review |
| `quran:16:71:10` | `فُضِّلُوا۟` | they were favored | `token_only_override` | `token_only_override` | `V:II:PERF:PASS:3MP` | passive voice review |
| `quran:112:3:4` | `يُولَدْ` | is begotten | `pending` | `pending` | `V:I:IMPF:PASS:JUSS:3MS:NEG-PENDING` | passive jussive / negation review |
| `quran:36:78:3` | `يُحْيِي` | gives life | `pending` | `pending` | `V:IV:IMPF:ACT:3MS:POS-COLLISION-PENDING` | proper-name versus finite-verb collision review |
| `quran:3:45:11` | `ٱلْمَسِيحُ` | the Messiah | `pending` | `pending` | `ART+N/TITLE:NOM:M:SG:DEF:PENDING` | title/article/case review |
| `quran:90:3:1` | `وَوَالِدٍۢ` | and by a parent | `pending` | `pending` | `OATH+N:GEN:M:SG:INDEF:PENDING` | oath wāw attachment review |
| `quran:33:32:3` | `لَسْتُنَّ` | you are not | `pending` | `pending` | `V:LAYS:NEG:2FP:PRED-PENDING` | laysa-like predicate/governance review |
| `quran:10:83:11` | `فِرْعَوْنَ` | Pharaoh | `rich_candidate` | `preview_only` | `PN:PHARAOH:CASE-PENDING` | proper-name case/role review |

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
blocking sarf/nahw reason. The single `preview_only` proper-name row is a renderer/metadata preview, not a
public-certified hover.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- bāʾ + article + nominal host;
- fāʾ/wāw function plus finite verbs;
- subject/object suffixes;
- Form II passive and active verb contrast;
- oath wāw plus genitive nominal host;
- title/article and proper-name rows.

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

Sarf updates: no procedure change. VN-02 already installed the reusable morphology doctrine for weak/root collisions,
Form II active/passive contrast, passive jussive, proper-name collision handling, and laysa-like forms.

Nahw updates: no procedure change. Existing gates already require two independent checks for PP attachment, oath
relations, negation/governance, title/case state, and token-only override rows.

Curriculum updates: no new learner prose in this certification tranche. The rows are already represented in the VN
dogfood-to-curriculum synthesis as preposition-host omission, passive voice loss, proper/common collision, oath
function, and readable-English versus grammar-safe explanation.

Assessment/checkpoint updates: no new checkpoint. The examples reinforce current grading policy: readable English
cannot clear the item when function, voice, case, or referent reasoning is pending.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as preposition-host omission,
passive voice erased by dictionary leakage, proper-name/finite-verb collision, and function-token flattening.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind
owner-authorized preview/admin gates.

Future routing: continue RICH-CERT in bounded VN tranches. The next likely lane is `VN-RICH-CERT-03`, unless
explicit owner authorization starts RH-LIVE-00 preview scaffolding.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_02_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_02_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_02_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_02_standard.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage, live renderer, or live correctness claim.
