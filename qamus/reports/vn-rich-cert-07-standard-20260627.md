# VN-RICH-CERT-07 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-07 converts the existing `VN-RICH-07` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_07_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_07_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_07_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_07_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_07_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 10 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 4 |
| `blocked` | 0 |
| `token_only_override` | 6 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 4, 'token_only_override': 6}`.

The zero `rich_certified` count is intentional. VN-RICH-07 is a review/certification bridge for preposition-pronoun attachment, finite verb object suffixes, kāda-sister predicate context, weighing-family noun/verb collisions, passive nominal derivative leakage, possessed nouns, missing nominal rows, and component-only verb evidence.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:38:7` | `مِّنِّى` | from me | `pending` | `pending` | `P:MIN+PRON.1S:ATTACHMENT-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:95:2` | `يَتَمَنَّوْهُ` | they wish for it | `token_only_override` | `token_only_override` | `V:V:IMPF:ACT:3MP+OBJ.3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:71:23` | `كَادُوا۟` | they almost | `pending` | `pending` | `V:KADA:PERF:ACT:3MP:PREDICATE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:7:8:6` | `مَوَٰزِينُهُۥ` | his scales | `token_only_override` | `token_only_override` | `N:PL:SCALES+POSS.3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:55:7:4` | `ٱلْمِيزَانَ` | the balance | `token_only_override` | `token_only_override` | `ART+N:ACC:DEF:SG:BALANCE:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:4:7:19` | `مَّفْرُوضًۭا` | ordained | `token_only_override` | `token_only_override` | `PART:ISM-MAFOOL:ACC:INDEF:SG:OBLIGATED:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:8:43:5` | `مَنَامِكَ` | your dream | `token_only_override` | `token_only_override` | `N:GEN:CONSTRUCT:DREAM+POSS.2MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:10:54:2` | `النَّدَامَةَ` | the remorse | `pending` | `pending` | `ART+N:ACC:DEF:SG:REMORSE:PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:47:5:3` | `بَالَهُمْ` | their state | `token_only_override` | `token_only_override` | `N:ACC:CONSTRUCT:STATE+POSS.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:219:16` | `تَتَفَكَّرُونَ` | you reflect | `pending` | `pending` | `V:V:IMPF:ACT:2MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |

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

- Sarf updates made: no new procedure update in this tranche; existing clitic/host, finite verb, nominal derivative, and noun/POS collision procedures already cover these repeated defects.
- Nahw updates made: no new procedure update in this tranche; pending rows explicitly route to two-vote or context review for preposition-pronoun attachment, kāda predicate context, missing nominal role, and component-only evidence.
- Curriculum updates made: no new curriculum file in this bounded certification queue; the tranche reinforces existing assessment lessons about suffix-bearing verbs, possessed nouns, and readable-English-not-certification.
- Assessment/checkpoint updates made: no-op; existing RICH-CERT assessment gates already require exact address, source-clean public payload, segment contribution, and two-vote where needed.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: suffix omission, host-only noun gloss, finite verb dictionary leakage, and component-only evidence trap.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; these rows instantiate already-recorded classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_07_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_07_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_07_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_07_standard.sample.jsonl
python tools/check_regressions.py
```
