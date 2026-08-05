# VN-RICH-CERT-17 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-17 converts the existing `VN-RICH-17` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, rich display backfill, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_17_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_17_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_17_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_17_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_17_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 40 |
| `rich_certified` | 0 |
| `preview_only` | 4 |
| `pending` | 10 |
| `blocked` | 0 |
| `token_only_override` | 26 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 10, 'token_only_override': 26, 'rich_candidate': 4}`.

The zero `rich_certified` count is intentional. VN-RICH-17 is a review/certification bridge for attached preposition-host-suffix stacks, lām-governed verbs, finite/passive verb form review, suffix-bearing nominal rows, article/host rows, noun/verb POS family collisions, and renderer backfill. It does not authorize live apply, source-wide propagation, or family propagation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:96:17` | `بِمُزَحْزِحِهِۦ` | to be kept away / keep away | `pending` | `pending` | `P+PRON+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:68:51:5` | `لَيُزْلِقُونَكَ` | to cause to slip | `pending` | `pending` | `PART+PFX+PRON+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:31:20:13` | `وَأَسْبَغَ` | to be ample / lavish | `pending` | `pending` | `CONJ+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:11:105:10` | `وَسَعِيدٌۭ` | to be joyful | `pending` | `pending` | `CONJ+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:2:30:16` | `وَيَسْفِكُ` | to spill blood | `pending` | `pending` | `CONJ+PFX+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:12:86:3` | `أَشْكُوا۟` | to complain, to voice one’s sorrow | `pending` | `pending` | `V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:20:22:1` | `وَاضْمُمْ` | to bring together | `pending` | `pending` | `CONJ+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:28:32:10` | `وَٱضْمُمْ` | to bring together | `pending` | `pending` | `CONJ+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:56:4:2` | `رُجَّتِ` | to shake violently | `token_only_override` | `token_only_override` | `V:unknown:PERFECT:PASSIVE:TOKEN-ONLY` | Keep رُجَّتِ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:4:88:2` | `أَرْكَسَهُم` | to regress | `token_only_override` | `token_only_override` | `V:IV:PERFECT:UNKNOWN:TOKEN-ONLY` | Keep أَرْكَسَهُم exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:4:91:5` | `أُرْكِسُوا` | to regress | `token_only_override` | `token_only_override` | `V:IV:PERFECT:PASSIVE:TOKEN-ONLY` | Keep أُرْكِسُوا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:3:185:11` | `زُحْزِحَ` | to be kept away / keep away | `token_only_override` | `token_only_override` | `V:unknown:PERFECT:PASSIVE:TOKEN-ONLY` | Keep زُحْزِحَ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:11:108:3` | `سُعِدُوا` | to be joyful | `token_only_override` | `token_only_override` | `V:unknown:PERFECT:PASSIVE:TOKEN-ONLY` | Keep سُعِدُوا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:14:42:2` | `تَشْخَصُ` | to stare in horror | `token_only_override` | `token_only_override` | `V:unknown:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep تَشْخَصُ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:18:29:23` | `يَشْوِى` | to burn | `token_only_override` | `token_only_override` | `V:unknown:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep يَشْوِى exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:66:4:2` | `صَغَتْ` | to incline away, drift away | `token_only_override` | `token_only_override` | `V:unknown:PERFECT:UNKNOWN:TOKEN-ONLY` | Keep صَغَتْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:8:43:16` | `سَلَّمَ` | to bring about safety, well-being | `rich_candidate` | `preview_only` | `UNKNOWN:REVIEW` | Keep سَلَّمَ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:56:4:4` | `رَجًّا` | to shake violently | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep رَجًّا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:18:40:15` | `زَلَقًا` | to cause to slip | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep زَلَقًا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:34:11:3` | `سَٰبِغَٰتٍۢ` | to be ample / lavish | `token_only_override` | `token_only_override` | `ADJ:GENITIVE:TOKEN-ONLY` | Keep سَٰبِغَٰتٍۢ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:21:97:6` | `شَٰخِصَةٌ` | to stare in horror | `token_only_override` | `token_only_override` | `ADJ:NOMINATIVE:TOKEN-ONLY` | Keep شَٰخِصَةٌ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:36:55:6` | `شُغُلٍۢ` | to busy / be occupied | `token_only_override` | `token_only_override` | `N:GENITIVE:TOKEN-ONLY` | Keep شُغُلٍۢ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:6:146:7` | `ظُفُرٍ` | claw (or hoof) | `rich_candidate` | `preview_only` | `N:GENITIVE:ROLE-PENDING` | Keep ظُفُرٍ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:17:79:5` | `نَافِلَةًۭ` | an additional favour | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:ROLE-PENDING` | Keep نَافِلَةًۭ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:21:72:5` | `نَافِلَةًۭ` | an additional favour | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:ROLE-PENDING` | Keep نَافِلَةًۭ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:14:24:11` | `أَصْلُهَا` | root, base, stem (always in reference to trees) | `token_only_override` | `token_only_override` | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | Keep أَصْلُهَا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:59:5:9` | `أُصُولِهَا` | root, base, stem (always in reference to trees) | `token_only_override` | `token_only_override` | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | Keep أُصُولِهَا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:3:154:62` | `مَضَاجِعِهِمْ` | resting places; beds | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | Keep مَضَاجِعِهِمْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:50:22:9` | `غِطَآءَكَ` | veil (on one’s eyes, making them unable to see the truth) | `token_only_override` | `token_only_override` | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | Keep غِطَآءَكَ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:2:255:42` | `كُرْسِيُّهُ` | seat, throne | `token_only_override` | `token_only_override` | `N+POSS:NOMINATIVE:TOKEN-ONLY` | Keep كُرْسِيُّهُ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:55:72:4` | `ٱلْخِيَامِ` | pavilions | `token_only_override` | `token_only_override` | `ART+N:GENITIVE:TOKEN-ONLY` | Keep ٱلْخِيَامِ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:3:141:1` | `وَلِيُمَحِّصَ` | to filter, refine | `pending` | `pending` | `CONJ+PURP+PFX+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:3:154:68` | `وَلِيُمَحِّصَ` | to filter, refine | `pending` | `pending` | `CONJ+PURP+PFX+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:8:1:7` | `ٱلْأَنفَالِ` | war gains (an additional favour after victory) | `token_only_override` | `token_only_override` | `ART+N:GENITIVE:TOKEN-ONLY` | Keep ٱلْأَنفَالِ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:8:1:9` | `ٱلْأَنفَالُ` | war gains (an additional favour after victory) | `token_only_override` | `token_only_override` | `ART+N:NOMINATIVE:TOKEN-ONLY` | Keep ٱلْأَنفَالُ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:25:53:13` | `بَرْزَخًۭا` | barrier | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep بَرْزَخًۭا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:55:20:2` | `بَرْزَخٌ` | barrier | `token_only_override` | `token_only_override` | `N:NOMINATIVE:TOKEN-ONLY` | Keep بَرْزَخٌ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:83:9:2` | `مَّرْقُومٌ` | inscription, writing | `token_only_override` | `token_only_override` | `N:NOMINATIVE:TOKEN-ONLY` | Keep مَّرْقُومٌ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:76:15:8` | `قَوَارِيرَا۠` | crystals | `token_only_override` | `token_only_override` | `N:UNKNOWN:TOKEN-ONLY` | Keep قَوَارِيرَا۠ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:76:16:1` | `قَوَارِيرَا۟` | crystals | `token_only_override` | `token_only_override` | `N:UNKNOWN:TOKEN-ONLY` | Keep قَوَارِيرَا۟ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |

## State Transitions

- `pending`: `quran:2:96:17`, `quran:68:51:5`, `quran:31:20:13`, `quran:11:105:10`, `quran:2:30:16`, `quran:12:86:3`, `quran:20:22:1`, `quran:28:32:10`, `quran:3:141:1`, `quran:3:154:68`.
- `preview_only`: `quran:8:43:16`, `quran:6:146:7`, `quran:17:79:5`, `quran:21:72:5`.
- `token_only_override`: `quran:56:4:2`, `quran:4:88:2`, `quran:4:91:5`, `quran:3:185:11`, `quran:11:108:3`, `quran:14:42:2`, `quran:18:29:23`, `quran:66:4:2`, `quran:56:4:4`, `quran:18:40:15`, `quran:34:11:3`, `quran:21:97:6`, `quran:36:55:6`, `quran:14:24:11`, `quran:59:5:9`, `quran:3:154:62`, `quran:50:22:9`, `quran:2:255:42`, `quran:55:72:4`, `quran:8:1:7`, `quran:8:1:9`, `quran:25:53:13`, `quran:55:20:2`, `quran:83:9:2`, `quran:76:15:8`, `quran:76:16:1`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing finite-verb, passive voice, verb form/measure, suffix-pronoun, nominal-derivative, article/host, false-clitic, and component-only procedures already cover the repeated VN-17 defects. This is a real no-op because the tranche adds certification state, not a new morphology class.
- Nahw updates made: no new procedure update in this certification tranche; existing grammar-risk, preposition/PP-attachment, lām/governor, suffix/referent, token-only, article/host, and component-only gates already cover the pending reasons. This is a real no-op because all grammar-sensitive rows remain two-vote or pending.
- Curriculum updates made: no new prose in this bounded queue; VN synthesis and existing rich-hover lessons already teach preposition-host-suffix stacks, lām-governed verbs, passive/finite verb state, suffix contribution, article/host segmentation, and component-only blockers. This tranche points future curriculum consolidation at these same examples rather than creating a parallel lesson.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, visible segment contribution, no readable-English-only certification, and two independent checks for preposition-host, suffix, mood/governor, passive voice, component-only, or token-only rows.
- Progress/missed-error categories added: no-op; the rows map to existing categories: preposition-host contribution omitted, finite verb dictionary leakage, passive voice loss, suffix omission, lām-governed verb review, component-only evidence trap, article/host segmentation, nominal/POS leakage, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-17 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue one bounded VN-RICH-CERT tranche at a time. Keep component-only prefixed/governed rows pending, token-only rows exact-addressed, and preview rows non-certified until compatible two-vote/owner gates exist.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_17_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_17_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_17_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_17_standard.sample.jsonl
python tools/check_regressions.py
```
