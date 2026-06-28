# VN-RICH-CERT-12 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-12 converts the existing `VN-RICH-12` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_12_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_12_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_12_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_12_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_12_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 12 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 6 |
| `blocked` | 0 |
| `token_only_override` | 6 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 6, 'token_only_override': 6}`.

The zero `rich_certified` count is intentional. VN-RICH-12 is a review/certification bridge for finite verb dictionary leakage, suffix-bearing verbs, Form II/III/IV verb state, definite nominal/POS leakage, preposition/comparison-host rows, conjunction-plus-host rows, feminine subject markers, and fāʾ plus imperative lām mood/governor review.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:75:13` | `يُحَرِّفُونَهُۥ` | they distort it | `pending` | `pending` | `V:II:IMPF:ACT:3MP+OBJ.3MS:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:191:3` | `ثَقِفْتُمُوهُمْ` | you found them | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:2MP+OBJ.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:220:12` | `تُخَالِطُوهُمْ` | you mix with them | `token_only_override` | `token_only_override` | `V:III:IMPF:ACT:2MP+OBJ.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:5:1:20` | `ٱلصَّيْدِ` | the game | `token_only_override` | `token_only_override` | `ART+N:GEN:DEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:6:152:3` | `مَالَ` | wealth | `pending` | `pending` | `N:ACC:CONSTRUCT:SG:ROLE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:48:29:32` | `كَزَرْعٍ` | like a crop | `pending` | `pending` | `P:KA+N:GEN:INDEF:SG:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:51:48:2` | `فَرَشْنَٰهَا` | We spread it out | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:1P+OBJ.3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:56:34:1` | `وَفُرُشٍۢ` | and furnishings | `pending` | `pending` | `CONJ+N:GEN:INDEF:PL:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:17:7` | `أَضَآءَتْ` | it lit up | `pending` | `pending` | `V:IV:PERF:ACT:3FS:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:20:6` | `أَضَآءَ` | it lit up | `token_only_override` | `token_only_override` | `V:IV:PERF:ACT:3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:74:2` | `قَسَتْ` | became hard | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:283:14` | `فَلْيُؤَدِّ` | then let him deliver | `pending` | `pending` | `REM+IMPV-LAM+V:II:IMPF:JUSS:ACT:3MS:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:2:75:13`, `quran:6:152:3`, `quran:48:29:32`, `quran:56:34:1`, `quran:2:17:7`, `quran:2:283:14`.
- `token_only_override -> token-only rich metadata`: `quran:2:191:3`, `quran:2:220:12`, `quran:5:1:20`, `quran:51:48:2`, `quran:2:20:6`, `quran:2:74:2`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing verb-form/mood, clitic-host, nominal/POS, suffix-pronoun, and finite-verb dictionary-leakage procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing preposition-pronoun, PP attachment, governing-particle mood, token-only, and grammar-risk gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that readable English, source agreement, and component evidence do not equal rich certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, fāʾ/lām relation, preposition-host, nominal case, or POS-collision reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: suffix omission, finite verb object omission, component-only evidence trap, nominal/POS leakage, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-12 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_12_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_12_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_12_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_12_standard.sample.jsonl
python tools/check_regressions.py
```
