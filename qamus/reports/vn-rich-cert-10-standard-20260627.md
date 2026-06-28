# VN-RICH-CERT-10 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-10 converts the existing `VN-RICH-10` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_10_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_10_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_10_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_10_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_10_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 13 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 6 |
| `blocked` | 0 |
| `token_only_override` | 7 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 6, 'token_only_override': 7}`.

The zero `rich_certified` count is intentional. VN-RICH-10 is a review/certification bridge for finite verb dictionary-gloss leakage, suffix-bearing nominal hosts, component-only bāʾ/lām/fāʾ rows, token-only finite verbs, passive/participle nominal rows, and false family propagation traps.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:16:108:3` | `طَبَعَ` | He sealed | `pending` | `pending` | `V:I:PERF:ACT:3MS:FINITE-FORM-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:12:18:15` | `ٱلْمُسْتَعَانُ` | the One sought for help | `token_only_override` | `token_only_override` | `ART+PTCP:PASS:NOM:DEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:3:119:22` | `بِغَيْظِكُمْ` | with your rage | `pending` | `pending` | `P:BI+N:GEN+POSS.2MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:48:29:42` | `لِيَغِيظَ` | so that He may enrage | `pending` | `pending` | `LAM+V:I:IMPF:ACT:3MS:MOOD-PENDING:COMPONENT-ONLY` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:12:19:4` | `وَارِدَهُمْ` | their water-drawer | `token_only_override` | `token_only_override` | `PTCP:ACT+POSS.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:24:9` | `وَقُودُهَا` | its fuel | `pending` | `pending` | `N:FUEL+POSS.3FS:SUFFIX-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:25:36:8` | `فَدَمَّرْنَٰهُمْ` | so We destroyed them | `pending` | `pending` | `REM+V:II:PERF:ACT:1P+OBJ.3MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:37:136:2` | `دَمَّرْنَا` | We destroyed | `token_only_override` | `token_only_override` | `V:II:PERF:ACT:1P:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:104:6` | `رَٰعِنَا` | attend to us | `token_only_override` | `token_only_override` | `V:IMPV?+OBJ.1P:TOKEN-ONLY:CONTEXT-PENDING` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:10:27:7` | `وَتَرْهَقُهُمْ` | and it will cover them | `pending` | `pending` | `CONJ+V:I:IMPF:ACT:3FS+OBJ.3MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:7:54:19` | `حَثِيثًۭا` | rapidly | `token_only_override` | `token_only_override` | `ADJ/ADV:ACC:INDEF:ROLE-PENDING` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:5:2:43` | `تَعَاوَنُوا۟` | cooperate with one another | `token_only_override` | `token_only_override` | `V:VI:IMPV:ACT:2MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:104:6:3` | `ٱلْمُوقَدَةُ` | the kindled one | `token_only_override` | `token_only_override` | `ART+PTCP:PASS:NOM:DEF:FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:16:108:3`, `quran:3:119:22`, `quran:48:29:42`, `quran:2:24:9`, `quran:25:36:8`, `quran:10:27:7`.
- `token_only_override -> token-only rich metadata`: `quran:12:18:15`, `quran:12:19:4`, `quran:37:136:2`, `quran:2:104:6`, `quran:7:54:19`, `quran:5:2:43`, `quran:104:6:3`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing verb-form/mood, clitic-host, nominal-host, passive/participle, and false-clitic split procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing particle-function, governing-particle mood, preposition-pronoun, PP attachment, token-only, and grammar-risk gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that readable English, source agreement, and component evidence do not equal rich certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, preposition-host, lām-on-verb, finite verb, or component-only reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: finite dictionary leakage, suffix omission, component-only evidence trap, token-only override, passive/participle review, and false raw-prefix segmentation.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-10 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_10_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_10_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_10_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_10_standard.sample.jsonl
python tools/check_regressions.py
```
