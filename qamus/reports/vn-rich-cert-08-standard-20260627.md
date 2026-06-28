# VN-RICH-CERT-08 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-08 converts the existing `VN-RICH-08` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_08_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_08_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_08_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_08_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_08_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 11 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 7 |
| `blocked` | 0 |
| `token_only_override` | 4 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 7, 'token_only_override': 4}`.

The zero `rich_certified` count is intentional. VN-RICH-08 is a review/certification bridge for exception-frame review, lexical-noun vs exception-particle collision, lām plus proper-name PP attachment, false bāʾ splits, suffix-bearing nominal hosts, bāʾ component-only rows, finite passive verb dictionary leakage, and finite verb object suffixes.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:9:7` | `إِلَّآ` | except | `pending` | `pending` | `EXP:ILLA:EXCEPTION-FRAME-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:9:8:8` | `إِلًّۭا` | bond of kinship | `pending` | `pending` | `N:ILLAN:LEXICAL-NOUN:EXCEPTION-FALSE-POSITIVE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:1:2:2` | `لِلَّهِ` | belongs to Allah | `pending` | `pending` | `P:LAM+PN:ALLAH:PP-ATTACHMENT-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:68:17` | `بِكْرٌ` | virgin | `token_only_override` | `token_only_override` | `N:BIKR:NOM:INDEF:FALSE-BI-SPLIT:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:108:3:2` | `شَانِئَكَ` | your hater | `token_only_override` | `token_only_override` | `PART:ISM-FAIL:HOST+OBJ.2MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:7:157:26` | `إِصْرَهُمْ` | their burden | `token_only_override` | `token_only_override` | `N:BURDEN+POSS.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:81:15:3` | `بِالْخُنَّسِ` | by the hidden ones | `pending` | `pending` | `P:BI+ART+N:GEN:DEF:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:6:136:12` | `بِزَعْمِهِمْ` | by their claim | `pending` | `pending` | `P:BI+N:CLAIM+POSS.3MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:26:138:3` | `بِمُعَذَّبِينَ` | to be punished | `pending` | `pending` | `P:BI+PART:PASS:GEN:PL:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:86:8` | `يُخَفَّفُ` | is lightened | `pending` | `pending` | `V:II:IMPF:PASS:3MS:FORM-VOICE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:48:10:3` | `يُبَايِعُونَكَ` | they pledge to you | `token_only_override` | `token_only_override` | `V:III:IMPF:ACT:3MP+OBJ.2MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |

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

- Sarf updates made: no new procedure update in this certification tranche; existing false-clitic split, finite/passive verb, nominal derivative, and suffix-bearing host procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing exception/vocative, preposition-pronoun, PP attachment, token-only, and grammar-risk gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that readable English, source agreement, and component evidence do not equal rich certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where exception, PP, passive, suffix, or component-only reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: exception-frame uncertainty, false clitic split, suffix omission, finite/passive dictionary leakage, and component-only evidence trap.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-08 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_08_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_08_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_08_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_08_standard.sample.jsonl
python tools/check_regressions.py
```
