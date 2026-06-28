# VN-RICH-CERT-15 Standard Certification Queue

Status: repo-only rich-hover certification tranche. No live Qamus data, WBW build artifact, service, mirror, public renderer, or hover decision ledger was changed.

## Scope

VN-RICH-CERT-15 converts the existing `VN-RICH-15` standard rich-hover sample into an explicit certification queue. It preserves the source tranche's safety posture instead of turning readable English, component evidence, rich display backfill, or exact-address token-only rows into public certification.

Input samples:

- `qamus/examples/rich_hover_vn_rich_15_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_15_standard_evidence.sample.jsonl`

Output artifacts:

- `qamus/examples/rich_cert_vn_rich_cert_15_standard.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_15_standard_evidence.sample.jsonl`
- `qamus/examples/rich_cert_vn_rich_cert_15_renderer_fixture.sample.jsonl`

## Classification Result

| Metric | Count |
|---|---:|
| rows reviewed | 30 |
| `rich_certified` | 0 |
| `preview_only` | 10 |
| `pending` | 2 |
| `blocked` | 0 |
| `token_only_override` | 18 |
| `may_apply_live=true` | 0 |

Source states: `{'pending': 2, 'token_only_override': 18, 'rich_candidate': 10}`.

The zero `rich_certified` count is intentional. VN-RICH-15 is a review/certification bridge for conjunction-plus-masdar component evidence, suffix-bearing construct nouns and masdars, nominal/POS leakage, plant and grain noun families, minimizer nouns, and renderer backfill. It does not authorize live apply, source-wide propagation, or family propagation.

## Controller Table

| Loc | Surface | Current gloss | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|---|
| `quran:4:62:3` | `وَتَوْفِيقًا` | to hit the mark; reconcile; success/fitting | `pending` | `pending` | `CONJ+MASDAR:ACC:INDEF:COMPONENT-ONLY-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:2:61:18` | `بَقْلِهَا` | herbs | `token_only_override` | `token_only_override` | `N:GEN:CONSTRUCT+POSS.3FS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:11:88:29` | `تَوْفِيقِىٓ` | to hit the mark; reconcile; success/fitting | `token_only_override` | `token_only_override` | `MASDAR:CONSTRUCT+POSS.1S:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:78:26:2` | `وِفَاقًا` | to hit the mark; reconcile; success/fitting | `token_only_override` | `token_only_override` | `MASDAR:ACC:INDEF:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:187:40` | `ٱلْأَسْوَدِ` | to be covered with gloom, darkness | `pending` | `pending` | `ART+ADJ:GEN:DEF:M:SG:POS-REVIEW-PENDING` | resolve exact blocker with compatible two-vote sarf/nahw reasoning |
| `quran:13:4:7` | `أَعْنَٰبٍۢ` | grapes, vineyards | `rich_candidate` | `preview_only` | `N:GEN:INDEF:PL:ROLE-PENDING` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:18:32:9` | `أَعْنَٰبٍۢ` | grapes, vineyards | `rich_candidate` | `preview_only` | `N:GEN:INDEF:PL:ROLE-PENDING` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:6:99:27` | `أَعْنَابٍۢ` | grapes, vineyards | `token_only_override` | `token_only_override` | `N:GEN:INDEF:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:36:57:3` | `فَٰكِهَةٌۭ` | fruit | `rich_candidate` | `preview_only` | `N:NOM:INDEF:F:SG:RENDERER-BACKFILL` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:55:11:2` | `فَٰكِهَةٌۭ` | fruit | `rich_candidate` | `preview_only` | `N:NOM:INDEF:F:SG:RENDERER-BACKFILL` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:24:35:21` | `زَيْتُونَةٍۢ` | olives | `token_only_override` | `token_only_override` | `N:GEN:INDEF:F:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:12:43:12` | `سُنۢبُلَٰتٍ` | ear of grain | `token_only_override` | `token_only_override` | `N:GEN:INDEF:F:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:12:47:10` | `سُنۢبُلِهِۦٓ` | ear of grain | `token_only_override` | `token_only_override` | `N:GEN:CONSTRUCT+POSS.3MS:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:261:12` | `سَنَابِلَ` | ear of grain | `token_only_override` | `token_only_override` | `N:ACC:INDEF:F:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:2:261:15` | `سُنۢبُلَةٍۢ` | ear of grain | `token_only_override` | `token_only_override` | `N:GEN:INDEF:F:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:34:16:15` | `سِدْرٍۢ` | lote tree | `rich_candidate` | `preview_only` | `N:GEN:INDEF:M:SG:RENDERER-BACKFILL` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:53:14:2` | `سِدْرَةِ` | lote tree | `token_only_override` | `token_only_override` | `N:GEN:CONSTRUCT:F:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:56:28:2` | `سِدْرٍۢ` | lote tree | `rich_candidate` | `preview_only` | `N:GEN:INDEF:M:SG:RENDERER-BACKFILL` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:19:23:4` | `جِذْعِ` | tree trunk | `token_only_override` | `token_only_override` | `N:GEN:INDEF:M:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:20:71:20` | `جُذُوعِ` | tree trunk | `token_only_override` | `token_only_override` | `N:GEN:INDEF:M:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:78:32:1` | `حَدَآئِقَ` | orchards, gardens | `token_only_override` | `token_only_override` | `N:ACC:INDEF:F:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:12:44:2` | `أَضْغَٰثُ` | a bunch of confused dreams | `token_only_override` | `token_only_override` | `N:NOM:INDEF:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:21:5:3` | `أضغاث` | a bunch of confused dreams | `token_only_override` | `token_only_override` | `N:NOM:INDEF:PL:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:38:44:3` | `ضِغْثًۭا` | a bundle of green and dry grass | `token_only_override` | `token_only_override` | `N:ACC:INDEF:M:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:17:71:15` | `فَتِيلًۭا` | the thread of a date stone | `token_only_override` | `token_only_override` | `N:ACC:INDEF:M:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:4:49:14` | `فَتِيلًا` | the thread of a date stone | `rich_candidate` | `preview_only` | `N:ACC:INDEF:M:SG:ROLE-PENDING` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:4:77:48` | `فَتِيلًا` | the thread of a date stone | `rich_candidate` | `preview_only` | `N:ACC:INDEF:M:SG:ROLE-PENDING` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:4:124:16` | `نَقِيرًۭا` | the speck (or small mark) on a date stone | `rich_candidate` | `preview_only` | `N:ACC:INDEF:M:SG:RENDERER-BACKFILL` | preview-only; compatible two-vote plus owner gate before public use |
| `quran:35:13:28` | `قِطْمِيرٍ` | the skin of a date stone | `token_only_override` | `token_only_override` | `N:GEN:INDEF:M:SG:TOKEN-ONLY` | keep exact-address only; owner/two-vote before preview/apply |
| `quran:20:121:10` | `وَرَقِ` | tree leaves | `rich_candidate` | `preview_only` | `N:GEN:CONSTRUCT:M:SG:ROLE-PENDING` | preview-only; compatible two-vote plus owner gate before public use |

## State Transitions

- `populated_uncertified -> pending rich metadata`: `quran:4:62:3`, `quran:2:187:40`.
- `rich_candidate -> preview-only rich metadata`: `quran:13:4:7`, `quran:18:32:9`, `quran:36:57:3`, `quran:55:11:2`, `quran:34:16:15`, `quran:56:28:2`, `quran:4:49:14`, `quran:4:77:48`, `quran:4:124:16`, `quran:20:121:10`.
- `token_only_override -> token-only rich metadata`: `quran:2:61:18`, `quran:11:88:29`, `quran:78:26:2`, `quran:6:99:27`, `quran:24:35:21`, `quran:12:43:12`, `quran:12:47:10`, `quran:2:261:12`, `quran:2:261:15`, `quran:53:14:2`, `quran:19:23:4`, `quran:20:71:20`, `quran:78:32:1`, `quran:12:44:2`, `quran:21:5:3`, `quran:38:44:3`, `quran:17:71:15`, `quran:35:13:28`.

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

- Sarf updates made: no new procedure update in this certification tranche; existing clitic/host, nominal/POS, nominal-derivative, false-clitic, suffix-pronoun, and finite/dictionary leakage procedures already cover the repeated defects.
- Nahw updates made: no new procedure update in this certification tranche; existing preposition-pronoun, PP attachment, grammar-risk, particle-function, article/host, token-only, case-role, and component-only gates already cover the pending reasons.
- Curriculum updates made: no new curriculum prose in this bounded queue; the tranche reinforces existing lessons that conjunction contribution, suffix possessors, nominal role, minimizer nouns, and component evidence must remain visible to the learner without becoming public certification.
- Assessment/checkpoint updates made: no-op; current assessment gates already require exact address, segment contribution, and two-vote where suffix, nominal case, POS-collision, component-only, or role-sensitive reasoning is involved.
- Progress/missed-error categories added: no-op; this tranche maps to existing categories: suffix omission, component-only evidence trap, nominal/POS leakage, renderer-only backfill, minimizer noun review, and token-only override.
- Drills/evals/regressions added: this tranche adds regression coverage through `tools/check_regressions.py` once wired below.
- Production-bug lessons added: no-op; rows instantiate already-recorded VN-15 lesson classes rather than a new class.
- Renderer requirements added: yes, the renderer fixture records preview-only segment/display requirements without live claims.
- Future tranche-routing implications: continue bounded VN-RICH-CERT tranches. Rows with token-only status should remain exact-address only until owner/two-vote authorization; preview rows should not be treated as certified because renderer metadata alone is not grammar proof; pending rows should not be silently promoted by source agreement alone.

## Validation Commands

Run after this report is generated:

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_15_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_15_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_15_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_15_standard.sample.jsonl
python tools/check_regressions.py
```
