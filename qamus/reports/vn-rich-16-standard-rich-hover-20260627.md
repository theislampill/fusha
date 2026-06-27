# VN-RICH-16 Standard Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, mirror repo, service, rebuild, renderer, hover ledger, or public hover payload was changed.

## Scope

VN-RICH-16 converts the sixteenth standard VN dogfood tranche into rich-hover metadata shape. It uses `qamus/reports/full-corpus-dogfood-vn16-20260627.md` and the committed VN-16 samples as canonical input.

Source dogfood batch:

- verbs `v723` through `v767`
- nouns `n796` through `n845`
- `302` live hover rows reviewed in the original dogfood tranche
- `277` whole-token rows and `25` component-only evidence rows
- `0` repair-preview-ready rows

Rich sample artifacts:

- `qamus/examples/rich_hover_vn_rich_16_standard.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_16_standard_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Gate |
|---|---|---|---|---|---|
| `26:94:1` | `فَكُبْكِبُوا` | `pending` | Fā plus finite verb components; component evidence cannot certify whole-token routing. | `FA+V:PASS?:PERF:3MP:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `27:90:1` | `فَكُبَّتْ` | `pending` | Fā plus passive perfect verb components; component evidence cannot certify whole-token routing. | `FA+V:PASS:PERF:3FS:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `58:5:8` | `كُبِتَ` | `rich_candidate` | Passive perfect finite verb; dictionary infinitive wording is insufficient. | `V:I:PERF:PASS:3MS:VOICE-REVIEW` | two_vote_required |
| `67:22:3` | `مُكِبًّا` | `token_only_override` | Accusative active participle/adjectival nominal; block verb infinitive leakage. | `PTCP.ACT:ACC:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `3:127:7` | `يَكْبِتَهُمْ` | `token_only_override` | Imperfect active verb with attached third masculine plural object pronoun. | `V:I:IMPF:ACT:3MS+OBJ.3MP:TOKEN-ONLY` | two_vote_required |
| `58:5:6` | `كُبِتُوا۟` | `token_only_override` | Passive perfect verb with plural subject ending. | `V:I:PERF:PASS:3MP:TOKEN-ONLY` | two_vote_required |
| `39:5:1` | `يُكَوِّرُ` | `token_only_override` | Form II imperfect active finite verb needing exact-address wording. | `V:II:IMPF:ACT:3MS:TOKEN-ONLY` | two_vote_required |
| `39:5:5` | `وَيُكَوِّرُ` | `pending` | Conjunction plus Form II imperfect verb; component evidence cannot certify whole-token routing. | `CONJ+V:II:IMPF:ACT:3MS:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `81:1:3` | `كُوِّرَتْ` | `token_only_override` | Form II passive perfect feminine verb needing exact-address wording. | `V:II:PERF:PASS:3FS:TOKEN-ONLY` | two_vote_required |
| `37:46:1` | `لَذَّةٍ` | `token_only_override` | Genitive indefinite noun/adjective; block verb-entry wording. | `N/ADJ:GEN:INDEF:F:SG:TOKEN-ONLY` | two_vote_required |
| `43:71:11` | `وَتَلَذُّ` | `pending` | Conjunction plus imperfect verb components; component evidence cannot certify whole-token routing. | `CONJ+V:I:IMPF:ACT:3FS:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `47:15:21` | `لَّذَّةٍۢ` | `token_only_override` | Genitive indefinite noun/adjective needing exact-address review. | `N/ADJ:GEN:INDEF:F:SG:TOKEN-ONLY` | two_vote_required |
| `10:78:3` | `لِتَلْفِتَنَا` | `pending` | Lām-governed imperfect verb with attached object pronoun; component evidence cannot certify whole-token routing. | `LAM+V:IMPF:ACT+OBJ.1P:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `11:81:15` | `يَلْتَفِتْ` | `rich_candidate` | Form VIII imperfect verb with mood review pending. | `V:VIII:IMPF:ACT:3MS:JUSSIVE-REVIEW` | two_vote_required |
| `15:65:9` | `يَلْتَفِتْ` | `rich_candidate` | Form VIII imperfect verb with mood review pending. | `V:VIII:IMPF:ACT:3MS:JUSSIVE-REVIEW` | two_vote_required |
| `17:104:14` | `لَفِيفًۭا` | `token_only_override` | Accusative nominal/adjectival token; block verb-entry wording. | `N/ADJ:ACC:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `75:29:1` | `وَٱلْتَفَّتِ` | `pending` | Conjunction plus Form VIII verb host; initial alif-lām shape is lexical verb material, not an article split. | `CONJ+V:VIII:PERF:ACT:3FS:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `78:16:2` | `أَلْفَافًا` | `token_only_override` | Accusative plural noun; block verb-entry wording. | `N:ACC:INDEF:PL:TOKEN-ONLY` | two_vote_required |
| `12:25:7` | `وَأَلْفَيَا` | `pending` | Conjunction plus perfect dual verb; component evidence cannot certify whole-token routing. | `CONJ+V:PERF:ACT:3DU:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `2:170:4` | `أَلْفَيْنَا` | `token_only_override` | Perfect active verb with first-person plural subject suffix. | `V:I:PERF:ACT:1P:TOKEN-ONLY` | two_vote_required |
| `37:69:2` | `أَلْفَوْا` | `token_only_override` | Perfect active verb with third masculine plural subject suffix. | `V:I:PERF:ACT:3MP:TOKEN-ONLY` | two_vote_required |
| `20:69:5` | `تَلْقَفْ` | `token_only_override` | Jussive imperfect finite verb needing exact-address wording. | `V:I:IMPF:ACT:3FS:JUSSIVE:TOKEN-ONLY` | two_vote_required |
| `26:45:6` | `تَلْقَفُ` | `rich_candidate` | Indicative imperfect finite verb needing exact-address wording. | `V:I:IMPF:ACT:3FS:INDICATIVE-REVIEW` | two_vote_required |
| `7:117:9` | `تَلْقَفُ` | `rich_candidate` | Indicative imperfect finite verb needing exact-address wording. | `V:I:IMPF:ACT:3FS:INDICATIVE-REVIEW` | two_vote_required |
| `13:39:1` | `يَمْحُوا۟` | `pending` | Weak imperfect verb components; final written wāw/alif is not a plural subject proof. | `V:I:IMPF:ACT:3MS:WEAK:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `17:12:5` | `فَمَحَوْنَآ` | `pending` | Fā plus weak perfect verb with first-person plural subject; component evidence cannot certify whole-token routing. | `FA+V:I:PERF:ACT:1P:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `42:24:1` | `وَيَمْحُ` | `pending` | Conjunction plus weak imperfect verb; component evidence cannot certify whole-token routing. | `CONJ+V:I:IMPF:ACT:3MS:WEAK:COMPONENT-ONLY-PENDING` | never_auto_resolve |
| `17:37:5` | `مَرَحًا` | `token_only_override` | Accusative masdar/adverbial token needing exact-address review. | `MASDAR:ACC:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |
| `31:18:9` | `مَرَحًا` | `token_only_override` | Accusative masdar/adverbial token; current hover may leak verb wording. | `MASDAR:ACC:INDEF:M:SG:TOKEN-ONLY` | two_vote_required |

No row is `rich_certified`. VN-16 evidence is sufficient to shape segment expectations, parse keys, learner explanations, and blocker/gate state. It is not sufficient for live apply, source-wide propagation, or family propagation.

State counts in this sample:

- `pending`: 10
- `token_only_override`: 14
- `rich_candidate`: 5

Note: the VN-16 inventory lists `58:5:8` under two entry candidates. The rich sample keeps one exact token row and records the collision as gate pressure rather than duplicating the token address.

## State Transitions

- `component-only evidence -> pending component-only rich metadata`: fā/wāw/lām prefixed verb rows such as `26:94:1`, `27:90:1`, `39:5:5`, `10:78:3`, `75:29:1`, `12:25:7`, and weak-verb erase rows.
- `finite/passive verb strings -> exact-address rich metadata`: `58:5:8`, `3:127:7`, `58:5:6`, `39:5:1`, `81:1:3`, `11:81:15`, `15:65:9`, `2:170:4`, `37:69:2`, `20:69:5`, `26:45:6`, `7:117:9`.
- `suffix-bearing verb rows -> token-only rich metadata`: `3:127:7`, `2:170:4`, and component-only `10:78:3`.
- `nominal/POS leakage -> token-only rich metadata`: `67:22:3`, `37:46:1`, `47:15:21`, `17:104:14`, `78:16:2`, `17:37:5`, `31:18:9`.

The movement is into exact segment roles, parse keys, learner explanations, and blocker/gate state. It is not a hover apply.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar is internal-only and does not authorize public source labels or external prose.

## Flywheel Impact

Sarf updates: no new source edit in this rich tranche. VN-16 already updated or routed through:

- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/procedures/nominal-derivative-decision.md`
- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/verb-measures.md`
- `sarf/drills/nominal-derivatives.md`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`

Nahw updates: no new source edit in this rich tranche. VN-16 already routed through:

- `nahw/procedures/pronoun-attachment.md`
- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/suffix-pronoun-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`

Curriculum updates: no new prose needed. This tranche applies the committed VN synthesis rule that rich hovers must preserve finite/passive verb state, suffix objects, lām-governed verb review, false-prefix caution, weak-verb endings, nominal/POS gates, and component-only blockers.

Renderer requirements: this tranche emits segment expectations for fā/wāw prefixed verbs, lām-on-verb rows, suffix-bearing finite verbs, passive voice rows, weak verbs, nominal/adjectival tokens, and lexical false-prefix rows.

Future tranche routing: prioritize passive/voice-sensitive finite verbs, lām-on-verb mood/governor rows, suffix-bearing verbs, weak-verb endings that look like pronouns, and nominal/POS leakage before any family-wide propagation.

## Acceptance Commands

Run before commit:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_16_standard.sample.jsonl
run the internal-only evidence sidecar scan
git diff --check
python tools/validate_sarf_skill.py
python tools/validate_nahw_skill.py
python tools/run_grammar_evals.py
python tools/check_regressions.py
```
