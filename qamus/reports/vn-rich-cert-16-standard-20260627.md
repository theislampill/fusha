# VN-RICH-CERT-16 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-16 converts the existing `VN-RICH-16` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, rich display backfill, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_16_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_16_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_16_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_16_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_16_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 29 |
| `rich_certified` | 0 |
| `preview_only` | 5 |
| `pending` | 10 |
| `blocked` | 0 |
| `token_only_override` | 14 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 10, 'rich_candidate': 5, 'token_only_override': 14}`.

The zero `rich_certified` count is intentional. VN-RICH-16 is a review/certification bridge for fā/wāw/lām prefixed verb component evidence, passive and finite verb form review, suffix-bearing verbs, weak-verb endings, nominal/POS leakage, masdar/adverbial rows, and renderer backfill. It does not authorize live apply, source-wide propagation, or family propagation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:26:94:1` | `فَكُبْكِبُوا` | to be repeatedly thrown headlong | `pending` | `pending` | `FA+V:PASS?:PERF:3MP:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:27:90:1` | `فَكُبَّتْ` | to be thrown facedown | `pending` | `pending` | `FA+V:PASS:PERF:3FS:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:58:5:8` | `كُبِتَ` | to debase | `rich_candidate` | `preview_only` | `V:I:PERF:PASS:3MS:VOICE-REVIEW` | Keep كُبِتَ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:67:22:3` | `مُكِبًّا` | to be thrown facedown | `token_only_override` | `token_only_override` | `PTCP.ACT:ACC:INDEF:M:SG:TOKEN-ONLY` | Keep مُكِبًّا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:3:127:7` | `يَكْبِتَهُمْ` | to debase | `token_only_override` | `token_only_override` | `V:I:IMPF:ACT:3MS+OBJ.3MP:TOKEN-ONLY` | Keep يَكْبِتَهُمْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:58:5:6` | `كُبِتُوا۟` | to debase | `token_only_override` | `token_only_override` | `V:I:PERF:PASS:3MP:TOKEN-ONLY` | Keep كُبِتُوا۟ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:39:5:1` | `يُكَوِّرُ` | to wrap around | `token_only_override` | `token_only_override` | `V:II:IMPF:ACT:3MS:TOKEN-ONLY` | Keep يُكَوِّرُ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:39:5:5` | `وَيُكَوِّرُ` | to wrap around | `pending` | `pending` | `CONJ+V:II:IMPF:ACT:3MS:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:81:1:3` | `كُوِّرَتْ` | to wrap around | `token_only_override` | `token_only_override` | `V:II:PERF:PASS:3FS:TOKEN-ONLY` | Keep كُوِّرَتْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:37:46:1` | `لَذَّةٍ` | to be delightful or delicious | `token_only_override` | `token_only_override` | `N/ADJ:GEN:INDEF:F:SG:TOKEN-ONLY` | Keep لَذَّةٍ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:43:71:11` | `وَتَلَذُّ` | to be delightful or delicious | `pending` | `pending` | `CONJ+V:I:IMPF:ACT:3FS:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:47:15:21` | `لَّذَّةٍۢ` | delicious | `token_only_override` | `token_only_override` | `N/ADJ:GEN:INDEF:F:SG:TOKEN-ONLY` | Keep لَّذَّةٍۢ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:10:78:3` | `لِتَلْفِتَنَا` | to divert one’s attention | `pending` | `pending` | `LAM+V:IMPF:ACT+OBJ.1P:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:11:81:15` | `يَلْتَفِتْ` | to look back | `rich_candidate` | `preview_only` | `V:VIII:IMPF:ACT:3MS:JUSSIVE-REVIEW` | Keep يَلْتَفِتْ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:15:65:9` | `يَلْتَفِتْ` | to look back | `rich_candidate` | `preview_only` | `V:VIII:IMPF:ACT:3MS:JUSSIVE-REVIEW` | Keep يَلْتَفِتْ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:17:104:14` | `لَفِيفًۭا` | to bundle together or wrap around | `token_only_override` | `token_only_override` | `N/ADJ:ACC:INDEF:M:SG:TOKEN-ONLY` | Keep لَفِيفًۭا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:75:29:1` | `وَٱلْتَفَّتِ` | to bundle together or wrap around | `pending` | `pending` | `CONJ+V:VIII:PERF:ACT:3FS:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:78:16:2` | `أَلْفَافًا` | to bundle together or wrap around | `token_only_override` | `token_only_override` | `N:ACC:INDEF:PL:TOKEN-ONLY` | Keep أَلْفَافًا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:12:25:7` | `وَأَلْفَيَا` | to find someone doing something | `pending` | `pending` | `CONJ+V:PERF:ACT:3DU:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:2:170:4` | `أَلْفَيْنَا` | to find someone doing something | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:1P:TOKEN-ONLY` | Keep أَلْفَيْنَا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:37:69:2` | `أَلْفَوْا` | to find someone doing something | `token_only_override` | `token_only_override` | `V:I:PERF:ACT:3MP:TOKEN-ONLY` | Keep أَلْفَوْا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:20:69:5` | `تَلْقَفْ` | to swallow up | `token_only_override` | `token_only_override` | `V:I:IMPF:ACT:3FS:JUSSIVE:TOKEN-ONLY` | Keep تَلْقَفْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:26:45:6` | `تَلْقَفُ` | to swallow up | `rich_candidate` | `preview_only` | `V:I:IMPF:ACT:3FS:INDICATIVE-REVIEW` | Keep تَلْقَفُ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:7:117:9` | `تَلْقَفُ` | to swallow up | `rich_candidate` | `preview_only` | `V:I:IMPF:ACT:3FS:INDICATIVE-REVIEW` | Keep تَلْقَفُ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:13:39:1` | `يَمْحُوا۟` | to erase or eliminate | `pending` | `pending` | `V:I:IMPF:ACT:3MS:WEAK:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:17:12:5` | `فَمَحَوْنَآ` | to erase or eliminate | `pending` | `pending` | `FA+V:I:PERF:ACT:1P:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:42:24:1` | `وَيَمْحُ` | to erase or eliminate | `pending` | `pending` | `CONJ+V:I:IMPF:ACT:3MS:WEAK:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:17:37:5` | `مَرَحًا` | exultantly | `token_only_override` | `token_only_override` | `MASDAR:ACC:INDEF:M:SG:TOKEN-ONLY` | Keep مَرَحًا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:31:18:9` | `مَرَحًا` | to act pridefully | `token_only_override` | `token_only_override` | `MASDAR:ACC:INDEF:M:SG:TOKEN-ONLY` | Keep مَرَحًا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |

## State Transitions

- `pending`: `quran:26:94:1`, `quran:27:90:1`, `quran:39:5:5`, `quran:43:71:11`, `quran:10:78:3`, `quran:75:29:1`, `quran:12:25:7`, `quran:13:39:1`, `quran:17:12:5`, `quran:42:24:1`.
- `preview_only`: `quran:58:5:8`, `quran:11:81:15`, `quran:15:65:9`, `quran:26:45:6`, `quran:7:117:9`.
- `token_only_override`: `quran:67:22:3`, `quran:3:127:7`, `quran:58:5:6`, `quran:39:5:1`, `quran:81:1:3`, `quran:37:46:1`, `quran:47:15:21`, `quran:17:104:14`, `quran:78:16:2`, `quran:2:170:4`, `quran:37:69:2`, `quran:20:69:5`, `quran:17:37:5`, `quran:31:18:9`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing finite-verb, passive voice, verb form/measure, weak-verb, suffix-pronoun, nominal-derivative, false-clitic, and component-only procedures already cover the repeated VN-16 defects. This is a real no-op because the tranche adds certification state, not a new morphology class.
- Nahw updates made: no new procedure update in this certification tranche; existing grammar-risk, particle-function, lām/governor, suffix/referent, token-only, and component-only gates already cover the pending reasons. This is a real no-op because all grammar-sensitive rows remain two-vote or pending.
- Curriculum updates made: no new prose in this bounded queue; VN synthesis and existing rich-hover lessons already teach finite verb state, passive voice, fā/wāw/lām contribution, weak endings, nominal/POS leakage, and component-only blockers. This tranche points future curriculum consolidation at these same examples rather than creating a parallel lesson.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, visible segment contribution, no readable-English-only certification, and two independent checks for suffix, mood/governor, passive voice, component-only, or token-only rows.
- Progress/missed-error categories added: no-op; the rows map to existing categories: finite verb dictionary leakage, passive voice loss, suffix omission, lām-governed verb review, component-only evidence trap, weak-verb ending trap, nominal/POS leakage, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-16 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue one bounded VN-RICH-CERT tranche at a time. Keep component-only prefixed verbs pending, token-only rows exact-addressed, and preview rows non-certified until compatible two-vote/owner gates exist.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_16_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_16_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_16_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_16_standard.sample.jsonl
python tools/check_regressions.py
```
