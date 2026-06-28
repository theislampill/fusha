# VN-RICH-CERT-00 Calibration Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public
renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-00 converts a bounded set of existing VN-RICH verb/noun hard-case rows into an explicit
certification queue. It does not redo VN-RICH metadata generation; it uses those rows as source review material.

Input samples:

- `qamus/examples/rich_hover_vn_rich_00_calibration.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_03_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_20_standard.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_00_calibration.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_00_calibration_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_00_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 8 |
| `rich_certified` | 0 |
| `preview_only` | 1 |
| `pending` | 5 |
| `blocked` | 0 |
| `token_only_override` | 2 |
| `may_apply_live=true` | 0 |

The zero `rich_certified` count is intentional. These rows are useful calibration cases precisely because readable
English can hide required sarf/nahw state: finite verb features, passive voice, fāʾ/wāw function, attached pronouns,
bāʾ-preposition contribution, PP attachment, and token-only propagation risk.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:33:63:1` | `يَسْأَلُكَ` | ask you | `token_only_override` | `token_only_override` | `V:I:IMPF:ACT:3MS+OBJ.2MS` | exact-address owner/two-vote review |
| `quran:68:51:5` | `لَيُزْلِقُونَكَ` | would make you slip | `pending` | `pending` | `PART+V:IV:IMPF:ACT:3MP+OBJ.2MS:PENDING` | lām/function and suffix review |
| `quran:2:96:17` | `بِمُزَحْزِحِهِۦ` | by keeping him away | `pending` | `pending` | `P:BI+N:PTCP:GEN+POSS.3MS:PENDING` | bāʾ-host-suffix PP review |
| `quran:22:2:3` | `تَذْهَلُ` | will be distracted | `pending` | `pending` | `V:I:IMPF:ACT:3FS:PENDING` | finite-verb contextual gloss review |
| `quran:22:30:11` | `وَأُحِلَّتْ` | and were made lawful | `rich_candidate` | `preview_only` | `CONJ+V:IV:PERF:PASS:3FS` | passive voice and conjunction two-vote review |
| `quran:20:22:1` | `وَاضْمُمْ` | and draw close | `pending` | `pending` | `CONJ+V:I:IMPV:2MS:PENDING` | imperative plus wāw review |
| `quran:26:139:2` | `فَأَهْلَكْنَاهُمْ` | so We destroyed them | `pending` | `pending` | `FA+V:IV:PERF:ACT:1P+OBJ.3MP:PENDING` | fāʾ + finite verb + suffixes review |
| `quran:3:123:4` | `بِبَدْرٍ` | at Badr | `token_only_override` | `token_only_override` | `P+N:GEN:TOKEN-ONLY` | exact-address preposition-host review |

## Gate Policy

Every row records:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- `public_payload.src=qamus`, `kind=authored`, `lang=en`;
- `may_apply_live=false`;
- `parse_key_primary_identity=false`;
- `component_candidates_can_certify=false`;
- `owner=not_authorized`;
- renderer status as `fixture_not_live`.

Rows classified `token_only_override` are exact-address review candidates only. Rows classified `preview_only` are
valid rich metadata previews, not public-certified hovers. Rows classified `pending` retain unresolved sarf/nahw or
two-vote blockers and must not move by surface family or parse-key family.

## Renderer Fixture

The renderer fixture keeps `display.palette=qamus-grammar-v1` and scrubbed segment roles for:

- finite verb prefix/stem/object suffix;
- lām/fāʾ/wāw function pieces;
- bāʾ preposition plus governed host;
- subject and object suffix pronouns;
- passive perfect and imperative verb hosts.

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

Sarf updates: no procedure change. The calibration rows exercise already-added finite-verb, passive-voice,
suffix-pronoun, bāʾ-host, and component-only blocker doctrine.

Nahw updates: no procedure change. Existing gates already require two independent checks for particle/function,
PP attachment, suffix referent, and token-only override rows.

Curriculum updates: no new learner prose in this tranche. The examples are already represented in rich-hover and
assessment material as miniature lessons about visible pieces versus flat English.

Assessment/checkpoint updates: no new checkpoint. These rows reinforce the existing rule that readable English is not
level-clearance evidence when the sarf/nahw reason is missing.

Drills/evals/regressions: regression coverage is added by extending `tools/check_regressions.py` to validate this
certification sample and its sidecars.

Production-bug lessons: no new lesson. The repeated classes are already represented as suffix omission, finite verb
dictionary leakage, preposition-host omission, and readable-English/wrong-reasoning traps.

Renderer requirements: preview fixture added, with no live claim. Future RH-LIVE work can use these rows only behind
owner-authorized preview/admin gates.

Future routing: continue RICH-CERT in bounded tranches. The next likely lane is VN-RICH-CERT-01 unless RH-LIVE-00 is
explicitly owner-authorized.

## Validation

Required checks:

```text
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_00_calibration.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_00_calibration_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_00_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_00_calibration.sample.jsonl
```

Broader repo checks remain required before commit. This tranche is a source-only review artifact and makes no hover
coverage, live renderer, or live correctness claim.
