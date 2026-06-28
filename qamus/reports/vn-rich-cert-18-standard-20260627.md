# VN-RICH-CERT-18 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-18 converts the existing `VN-RICH-18` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, rich display backfill, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_18_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_18_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_18_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_18_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 40 |
| `rich_certified` | 0 |
| `preview_only` | 18 |
| `pending` | 12 |
| `blocked` | 0 |
| `token_only_override` | 10 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 12, 'token_only_override': 10, 'rich_candidate': 18}`.

The zero `rich_certified` count is intentional. VN-RICH-18 is a review/certification bridge for preposition/article/host stacks, wāw plus article/noun rows, finite verb and suffix review, number/one-family nominal rows, component-only blockers, and renderer backfill. It does not authorize live apply, source-wide propagation, or family propagation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:2:178:22` | `بِٱلْمَعْرُوفِ` | by what is right/customary | `pending` | `pending` | `P+ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:22:18:13` | `وَٱلشَّمْسُ` | and + the sun | `pending` | `pending` | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:22:18:14` | `وَٱلْقَمَرُ` | and + the moon | `pending` | `pending` | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:22:18:15` | `وَٱلنُّجُومُ` | and + the stars | `pending` | `pending` | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:22:18:16` | `وَٱلْجِبَالُ` | and + the mountains | `pending` | `pending` | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:22:18:17` | `وَٱلشَّجَرُ` | and + the trees | `pending` | `pending` | `CONJ+ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:56:55:3` | `ٱلْهِيمِ` | camels roaming insanely due to extreme thirst | `pending` | `pending` | `ART+N:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:2:255:46` | `يَـُٔودُهُۥ` | to tire | `pending` | `pending` | `PFX+PRON+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:4:119:4` | `فَلَيُبَتِّكُنَّ` | to slit | `pending` | `pending` | `REM+PART+PFX+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:7:160:1` | `فَانْبَجَسَتْ` | to burst | `pending` | `pending` | `REM+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:27:19:1` | `فَتَبَسَّمَ` | to smile | `pending` | `pending` | `REM+V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:4:72:4` | `لَّيُبَطِّئَنَّ` | to lag behind | `pending` | `pending` | `V:COMPONENT-ONLY-PENDING` | Resolve component_only_candidate_no_whole_token_propagation with two independent sarf/nahw checks before rich certification. |
| `quran:8:48:19` | `نَكَصَ` | to back away | `token_only_override` | `token_only_override` | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | Keep نَكَصَ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:23:66:4` | `تَنكِصُونَ` | to back away | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep تَنكِصُونَ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:11:78:3` | `يُهْرَعُونَ` | to hurry, rush | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep يُهْرَعُونَ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:39:21:20` | `يَهِيجُ` | to dry up | `rich_candidate` | `preview_only` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep يَهِيجُ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:57:20:20` | `يَهِيجُ` | to dry up | `rich_candidate` | `preview_only` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep يَهِيجُ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:26:225:7` | `يَهِيمُونَ` | to roam aimlessly | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | Keep يَهِيمُونَ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:18:52:13` | `مَّوْبِقًۭا` | to doom | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep مَّوْبِقًۭا exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:42:34:2` | `يُوبِقْهُنَّ` | to doom | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN+OBJ:TOKEN-ONLY` | Keep يُوبِقْهُنَّ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:59:6:8` | `أَوْجَفْتُمْ` | to move rapidly | `token_only_override` | `token_only_override` | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | Keep أَوْجَفْتُمْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:79:8:3` | `وَاجِفَةٌ` | to move rapidly | `token_only_override` | `token_only_override` | `N/ADJ:NOMINATIVE:TOKEN-ONLY` | Keep وَاجِفَةٌ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:22:9:1` | `ثَانِىَ` | to fold | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep ثَانِىَ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:17:20:1` | `كُلًّۭا` | to each | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep كُلًّۭا preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:48:16:8` | `أُو۟لِى` | to turn away | `rich_candidate` | `preview_only` | `N:UNKNOWN:TOKEN-ONLY` | Keep أُو۟لِى preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:216:5` | `كُرْهٌۭ` | to hate, detest | `rich_candidate` | `preview_only` | `N:NOMINATIVE:TOKEN-ONLY` | Keep كُرْهٌۭ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:9:32:14` | `كَرِهَ` | to hate, detest | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:TOKEN-ONLY` | Keep كَرِهَ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:61:8` | `وَٰحِدٍۢ` | one; only one; someone; one (fmn.); one alone | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep وَٰحِدٍۢ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:102:27` | `أَحَدٍ` | anyone / one | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep أَحَدٍ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:102:48` | `أَحَدٍ` | anyone / one | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep أَحَدٍ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:136:4` | `أَحَدٍ` | anyone / one | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep أَحَدٍ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:163:3` | `وَٰحِدٌۭ` | one; only one; someone; one (fmn.); one alone | `rich_candidate` | `preview_only` | `N:NOMINATIVE:RICH-RENDERER-BACKFILL` | Keep وَٰحِدٌۭ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:180:5` | `أَحَدَكُمُ` | one; only one; someone; one (fmn.); one alone | `rich_candidate` | `preview_only` | `PRON+N+POSS:NOMINATIVE:RICH-RENDERER-BACKFILL` | Keep أَحَدَكُمُ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:213:4` | `وَٰحِدَةًۭ` | one; only one; someone; one (fmn.); one alone | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | Keep وَٰحِدَةًۭ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:266:2` | `أَحَدُكُمْ` | one; only one; someone; one (fmn.); one alone | `rich_candidate` | `preview_only` | `PRON+N+POSS:UNKNOWN:RICH-RENDERER-BACKFILL` | Keep أَحَدُكُمْ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:2:96:10` | `أَحَدُهُمْ` | one; only one; someone; one (fmn.); one alone | `token_only_override` | `token_only_override` | `PRON+N+POSS:UNKNOWN:TOKEN-ONLY` | Keep أَحَدُهُمْ exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:2:285:18` | `أَحَدٍۢ` | anyone / one | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep أَحَدٍۢ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:3:91:10` | `أَحَدِهِم` | one; only one; someone; one (fmn.); one alone | `token_only_override` | `token_only_override` | `N:UNKNOWN:TOKEN-ONLY` | Keep أَحَدِهِم exact-address only; require owner gate and compatible two-vote reasoning before any preview or apply. |
| `quran:3:153:6` | `أَحَدٍۢ` | anyone / one | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep أَحَدٍۢ preview-only; require compatible two-vote reasoning plus owner gate before public use. |
| `quran:4:1:13` | `وَٰحِدَةٍۢ` | one; only one; someone; one (fmn.); one alone | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | Keep وَٰحِدَةٍۢ preview-only; require compatible two-vote reasoning plus owner gate before public use. |

## State Transitions

- `pending`: `quran:2:178:22`, `quran:22:18:13`, `quran:22:18:14`, `quran:22:18:15`, `quran:22:18:16`, `quran:22:18:17`, `quran:56:55:3`, `quran:2:255:46`, `quran:4:119:4`, `quran:7:160:1`, `quran:27:19:1`, `quran:4:72:4`.
- `preview_only`: `quran:39:21:20`, `quran:57:20:20`, `quran:22:9:1`, `quran:17:20:1`, `quran:48:16:8`, `quran:2:216:5`, `quran:9:32:14`, `quran:2:61:8`, `quran:2:102:27`, `quran:2:102:48`, `quran:2:136:4`, `quran:2:163:3`, `quran:2:180:5`, `quran:2:213:4`, `quran:2:266:2`, `quran:2:285:18`, `quran:3:153:6`, `quran:4:1:13`.
- `token_only_override`: `quran:8:48:19`, `quran:23:66:4`, `quran:11:78:3`, `quran:26:225:7`, `quran:18:52:13`, `quran:42:34:2`, `quran:59:6:8`, `quran:79:8:3`, `quran:2:96:10`, `quran:3:91:10`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing clitic/host, article/host, finite-verb, suffix-pronoun, nominal-derivative, false-clitic, number/nominal, and component-only procedures already cover the repeated VN-18 defects. This is a real no-op because the tranche adds certification state, not a new morphology class.
- Nahw updates made: no new procedure update in this certification tranche; existing grammar-risk, preposition/PP-attachment, particle/function, suffix/referent, token-only, case-role, and component-only gates already cover the pending reasons. This is a real no-op because all grammar-sensitive rows remain two-vote or pending.
- Curriculum updates made: no new prose in this bounded queue; VN synthesis and existing rich-hover lessons already teach bāʾ+article+host, wāw+article+noun, suffix-bearing verbs/nouns, readable string vs rich certification, and component-only blockers. This tranche highlights the 22:18 sun/moon/stars/mountains/trees cluster as RH-LIVE preview material rather than public certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, visible segment contribution, no readable-English-only certification, and two independent checks for preposition-host, particle/article decomposition, suffix, component-only, token-only, or renderer-backfill rows.
- Progress/missed-error categories added: no-op; the rows map to existing categories: preposition-host contribution omitted, conjunction/article omission, suffix omission, finite verb dictionary leakage, component-only evidence trap, article/host segmentation, readable-English-only trap, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-18 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue one bounded VN-RICH-CERT tranche at a time. Keep the 22:18 cluster available as RH-LIVE preview candidates while maintaining component-only blockers until owner/two-vote gates exist.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_18_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_18_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_18_standard.sample.jsonl
python tools/check_regressions.py
```
