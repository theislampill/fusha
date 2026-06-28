# VN-RICH-CERT-11 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-11 converts the existing `VN-RICH-11` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_11_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_11_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_11_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_11_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_11_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 12 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 7 |
| `blocked` | 0 |
| `token_only_override` | 5 |
| `may_apply_live=true` | 0 |

Source states: `{'token_only_override': 5, 'pending': 7}`.

The zero `rich_certified` count is intentional. VN-RICH-11 is a review/certification bridge for suffix-bearing finite verbs, imperative plus suffix rows, fāʾ plus finite verb object suffixes, pronoun/function-token uncertainty, preposition-host-plus-possessor rows, nominal case/POS review, and noun-entry vs verb/POS collisions.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:8:41:3` | `غَنِمْتُم` | you gained spoils | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:2MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:8:9:2` | `تَسْتَغِيثُونَ` | you seek aid | `token_only_override` | `token_only_override` | `V:X:IMPF:ACT:2MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:20:39:2` | `ٱقْذِفِيهِ` | cast him | `token_only_override` | `token_only_override` | `V:I:IMPV:ACT:2FS+OBJ.3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:25:46:2` | `قَبَضْنَٰهُ` | We drew it in | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:1P+OBJ.3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:26:139:2` | `فَأَهْلَكْنَاهُمْ` | so We destroyed them | `pending` | `pending` | `REM+V:IV:PERF:ACT:1P+OBJ.3MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:4:11` | `هُمْ` | they / them | `pending` | `pending` | `PRON.3MP:ROLE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:23:5:3` | `لِفُرُوجِهِمْ` | for their private parts | `pending` | `pending` | `P:LI+N:GEN:PL+POSS.3MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:24:30:7` | `فُرُوجَهُمْ` | their private parts | `pending` | `pending` | `N:ACC:PL+POSS.3MP:SUFFIX-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:4:94:24` | `مَغَانِمُ` | spoils | `token_only_override` | `token_only_override` | `N:NOM:INDEF:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:31:34:7` | `ٱلْغَيْثَ` | the rain | `pending` | `pending` | `ART+N:ACC:DEF:SG:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:76:15:5` | `فِضَّةٍۢ` | silver | `pending` | `pending` | `N:GEN:INDEF:SG:ROLE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:4:77:7` | `كُفُّوٓا۟` | restrain yourselves | `pending` | `pending` | `V:I:IMPV:ACT:2MP:POS-COLLISION-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:26:139:2`, `quran:2:4:11`, `quran:23:5:3`, `quran:24:30:7`, `quran:31:34:7`, `quran:76:15:5`, `quran:4:77:7`.
- `token_only_override -> token-only rich metadata`: `quran:8:41:3`, `quran:8:9:2`, `quran:20:39:2`, `quran:25:46:2`, `quran:4:94:24`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing verb-form/mood, clitic-host, suffix-pronoun, nominal/POS, and false-clitic split procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing pronoun-attachment, preposition-pronoun, PP attachment, token-only, function-token, and grammar-risk gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that readable English, source agreement, and component evidence do not equal rich certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, pronoun/function, fāʾ relation, preposition-host, nominal case, or POS-collision reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: suffix omission, finite verb object omission, component-only evidence trap, pronoun/function uncertainty, nominal/POS leakage, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-11 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_11_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_11_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_11_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_11_standard.sample.jsonl
python tools/check_regressions.py
```
