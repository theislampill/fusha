# VN-RICH-CERT-14 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-14 converts the existing `VN-RICH-14` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_14_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_14_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_14_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_14_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_14_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 13 |
| `rich_certified` | 0 |
| `preview_only` | 0 |
| `pending` | 3 |
| `blocked` | 0 |
| `token_only_override` | 10 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 3, 'token_only_override': 10}`.

The zero `rich_certified` count is intentional. VN-RICH-14 is a review/certification bridge for conjunction-plus-article-plus-noun component evidence, suffix-bearing construct nouns, elative/nominal rows, finite verbs, article-plus-participle rows, nominal/POS review, and bāʾ-host-suffix attachment. It does not authorize live apply or family propagation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:22:18:17` | `وَٱلشَّجَرُ` | and + the trees | `pending` | `pending` | `CONJ+ART+N:NOM:DEF:SG:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:16:80:19` | `أَصْوَافِهَا` | wool | `token_only_override` | `token_only_override` | `N:GEN:CONSTRUCT:PL+POSS.3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:223:5` | `حَرْثَكُمْ` | harvest, farm | `token_only_override` | `token_only_override` | `N:ACC:CONSTRUCT:SG+POSS.2MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:143:4` | `وَسَطًۭا` | central, best, upright, moderate | `token_only_override` | `token_only_override` | `N/ADJ:ACC:INDEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:5:89:17` | `أَوْسَطِ` | to be/plunge into the middle; middle or average | `token_only_override` | `token_only_override` | `ISM-TAFDIL:GEN:DEF_OR_CONSTRUCT:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:68:28:2` | `أَوْسَطُهُمْ` | central, best, upright, moderate | `token_only_override` | `token_only_override` | `ISM-TAFDIL:NOM:CONSTRUCT+POSS.3MP:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:50:16:6` | `تُوَسْوِسُ` | to whisper | `token_only_override` | `token_only_override` | `V:QUAD-I:IMPF:ACT:3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:114:4:3` | `الْوَسْوَاسِ` | the whisperer | `token_only_override` | `token_only_override` | `ART+N:GEN:DEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:6:76:11` | `أَفَلَ` | for a star to set | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:6:76:15` | `ٱلْءَافِلِينَ` | for a star to set | `token_only_override` | `token_only_override` | `ART+PTCP.ACT:ACC/GEN:DEF:M:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:57:27:20` | `ٱبْتَدَعُوهَا` | to invent; make up | `token_only_override` | `token_only_override` | `V:VIII:PERF:ACT:3MP+OBJ.3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:6:141:19` | `ثَمَرِهِۦٓ` | to fruit; bear fruit | `pending` | `pending` | `N:GEN:CONSTRUCT:SG+POSS.3MS:POS-REVIEW-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:12:59:3` | `بِجَهَازِهِمْ` | to supply/provide | `pending` | `pending` | `P+N:GEN:HOST+POSS.3MP:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:22:18:17`, `quran:6:141:19`, `quran:12:59:3`.
- `token_only_override -> token-only rich metadata`: `quran:16:80:19`, `quran:2:223:5`, `quran:2:143:4`, `quran:5:89:17`, `quran:68:28:2`, `quran:50:16:6`, `quran:114:4:3`, `quran:6:76:11`, `quran:6:76:15`, `quran:57:27:20`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing clitic/host, nominal/POS, finite-verb, false-clitic, nominal-derivative, and suffix-pronoun procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing preposition-pronoun, PP attachment, grammar-risk, particle-function, article/host, and token-only gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that article/host contribution, preposition contribution, suffix referents, and component evidence must remain visible to the learner.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, preposition-host, nominal case, POS-collision, or component-only reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: suffix omission, article/host contribution, component-only evidence trap, nominal/POS leakage, preposition-host-suffix review, finite-verb dictionary leakage, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-14 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_14_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_14_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_14_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_14_standard.sample.jsonl
python tools/check_regressions.py
```
