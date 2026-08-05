# VN-RICH-CERT-09 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-09 converts the existing `VN-RICH-09` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_09_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_09_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_09_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_09_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_09_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 12 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 8 |
| `blocked` | 0 |
| `token_only_override` | 4 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 8, 'token_only_override': 4}`.

The zero `rich_certified` count is intentional. VN-RICH-09 is a review/certification bridge for finite verb dictionary-gloss leakage, component-only conjunction/preposition/lām rows, suffix-bearing finite verbs, suffix-bearing nominal hosts, lām/mā and lamma-family function collisions, comparison/preposition hosts, and false raw-prefix segmentation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:34:54:5` | `يَشْتَهُونَ` | they desire | `pending` | `pending` | `V:I:IMPF:ACT:3MP:FINITE-FORM-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:9:25:16` | `وَضَاقَتْ` | and it became straitened | `pending` | `pending` | `CONJ+V:I:PERF:ACT:3FS:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:65:6:9` | `لِتُضَيِّقُوا۟` | so that you constrain | `pending` | `pending` | `LAM+V:II:IMPF:ACT:2MP:MOOD-PENDING:COMPONENT-ONLY` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:5:67:16` | `يَعْصِمُكَ` | protects you | `token_only_override` | `token_only_override` | `V:I:IMPF:ACT:3MS+OBJ.2MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:12:6:2` | `يَجْتَبِيكَ` | chooses you | `token_only_override` | `token_only_override` | `V:VIII:IMPF:ACT:3MS+OBJ.2MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:37:107:1` | `وَفَدَيْنَٰهُ` | and We ransomed him | `pending` | `pending` | `CONJ+V:I:PERF:ACT:1P+OBJ.3MS:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:41:10:10` | `أَقْوَٰتَهَا` | its sustenance | `token_only_override` | `token_only_override` | `N:PROVISIONS+POSS.3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:16:77:1` | `كَلَمْحِ` | like a blink | `pending` | `pending` | `P:KAF+N:GEN:COMPARISON:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:213:37` | `لِمَا` | to that which | `pending` | `pending` | `LAM+MA:FUNCTION-PENDING:ATTACHMENT-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:86:4:4` | `لَّمَّا` | there is no ... except | `pending` | `pending` | `LAMMA:FUNCTION-COLLISION:NEG-EXCEPTIVE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:9:114:21` | `لَأَوَّٰهٌ` | tender-hearted | `pending` | `pending` | `LAM?+N:AWWAH:NOM:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:22:29:3` | `تَفَثَهُمْ` | their grooming rites | `token_only_override` | `token_only_override` | `N:RITES+POSS.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:34:54:5`, `quran:9:25:16`, `quran:65:6:9`, `quran:37:107:1`, `quran:16:77:1`, `quran:2:213:37`, `quran:86:4:4`, `quran:9:114:21`.
- `token_only_override -> token-only rich metadata`: `quran:5:67:16`, `quran:12:6:2`, `quran:41:10:10`, `quran:22:29:3`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

All public payload previews remain source-clean:

- `src=qamus`
- `kind=authored`
- `lang=en`
- no internal evidence labels are public-exposable
- no live renderer claim is made

Internal evidence labels are confined to the evidence sidecar and remain `public_exposable=false`.

## Renderer Requirement

The renderer fixture is preview/admin-only. It preserves segment surfaces for future non-destructive display tests, but does not claim current live renderer support. Every row keeps `surface_text_invariant=segments_concat_equals_surface`; any future UI must preserve the atomic Qur'anic visible token while using role metadata for color/tooltip rows.

## Flywheel Impact

- Sarf updates made: no new procedure update in this certification tranche; existing verb-form/mood, clitic-host, nominal-host, and false-clitic split procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing mā-function, lām/particle-function, preposition-pronoun, PP attachment, token-only, and grammar-risk gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that readable English, source agreement, and component evidence do not equal rich certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, lām/mā, lamma, preposition-host, finite verb, or component-only reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: finite dictionary leakage, suffix omission, component-only evidence trap, function-token uncertainty, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-09 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_09_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_09_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_09_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_09_standard.sample.jsonl
python tools/check_regressions.py
```
