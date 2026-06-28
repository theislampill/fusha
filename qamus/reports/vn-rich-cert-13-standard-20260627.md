# VN-RICH-CERT-13 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-13 converts the existing `VN-RICH-13` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_13_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_13_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_13_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_13_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_13_renderer_fixture.sample.jsonl`

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

The zero `rich_certified` count is intentional. VN-RICH-13 is a review/certification bridge for suffix-bearing nouns, single-host nominal role backfill, article definiteness, conjunction-plus-article-plus-noun component evidence, nominal/POS review, preposition-host-suffix attachment, and finite verb state. It does not authorize live apply or family propagation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:19:24:10` | `سَرِيًّۭا` | a moving stream | `pending` | `pending` | `N:ACC:INDEF:SG:ROLE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:7:74:3` | `سُهُولِهَا` | plains | `token_only_override` | `token_only_override` | `N:GEN:CONSTRUCT:PL+POSS.3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:264:21` | `صَفْوَانٍ` | (barren) rock | `pending` | `pending` | `N:GEN:INDEF:SG:ROLE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:18:17:17` | `فَجْوَةٍۢ` | open space | `token_only_override` | `token_only_override` | `N:GEN:INDEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:73:14:3` | `كَثِيبًا` | pile of sand | `token_only_override` | `token_only_override` | `N:ACC:INDEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:100:4:3` | `نَقْعًۭا` | (clouds of) dust | `token_only_override` | `token_only_override` | `N:ACC:INDEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:19:4` | `ٱلسَّمَآءِ` | sky, heavens | `pending` | `pending` | `ART+N:GEN:DEF:SG-COLLECTIVE:ROLE-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:22:18:13` | `وَٱلشَّمْسُ` | and + the sun | `pending` | `pending` | `CONJ+ART+N:NOM:DEF:SG:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:96:2` | `أَحْرَصَ` | to be keen | `token_only_override` | `token_only_override` | `ISM:ELATIVE:ACC:TOKEN-ONLY-POS-REVIEW` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:25:40:7` | `مَطَرَ` | to rain or shower as torment | `pending` | `pending` | `N:ACC_OR_CONSTRUCT:SG:POS-REVIEW-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:14:22:30` | `بِمُصْرِخِكُمْ` | to cry for help; respond to cries | `pending` | `pending` | `P+N:GEN:HOST+POSS.2MP:ATTACHMENT-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:80:25:2` | `صَبَبْنَا` | We poured | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:1P:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:19:24:10`, `quran:2:264:21`, `quran:2:19:4`, `quran:22:18:13`, `quran:25:40:7`, `quran:14:22:30`.
- `token_only_override -> token-only rich metadata`: `quran:7:74:3`, `quran:18:17:17`, `quran:73:14:3`, `quran:100:4:3`, `quran:2:96:2`, `quran:80:25:2`.

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
- Nahw updates made: no new procedure update in this certification tranche; existing preposition-pronoun, PP attachment, grammar-risk, particle-function, and token-only gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that article/host contribution, preposition contribution, suffix referents, and component evidence must remain visible to the learner.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, preposition-host, nominal case, POS-collision, or component-only reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: suffix omission, article/host contribution, component-only evidence trap, nominal/POS leakage, preposition-host-suffix review, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-13 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_13_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_13_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_13_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_13_standard.sample.jsonl
python tools/check_regressions.py
```
