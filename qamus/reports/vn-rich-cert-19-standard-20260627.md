# VN-RICH-CERT-19 Standard Certification Queue

Repo-only rich-hover certification queue. This report converts the VN-RICH seed rows into conservative production-readiness classes without authorizing live apply, public rollout, WBW rebuild, mirror sync, service restart, or hover-ledger mutation.

## Inputs

- Source rich-hover sample: `qamus/examples/rich_hover_vn_rich_19_standard.sample.jsonl`
- Source evidence sidecar: `qamus/examples/rich_hover_vn_rich_19_standard_evidence.sample.jsonl`
- Identity remains exact `quran:S:A:W` / `wbw:S:A:W`; `parse_key` is not primary identity.

## Outputs

- Certification queue: `qamus/examples/rich_cert_vn_rich_cert_19_standard.sample.jsonl`
- Internal evidence sidecar: `qamus/examples/rich_cert_vn_rich_cert_19_standard_evidence.sample.jsonl`
- Renderer fixture: `qamus/examples/rich_cert_vn_rich_cert_19_renderer_fixture.sample.jsonl`

## Counts

- Rows: `40`
- `pending`: 10
- `preview_only`: 13
- `token_only_override`: 17
- `rich_certified`: 0
- `may_apply_live=true`: 0
- `component_candidates_can_certify=true`: 0
- `parse_key_primary_identity=true`: 0

Source-state counts:

- `pending`: 10
- `rich_candidate`: 13
- `token_only_override`: 17

Blocker counts:

- `component_only_candidate_no_whole_token_propagation`: 10
- `none`: 30

## Rows

| Loc | Surface | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|
| `20:130:17` | `وَأَطْرَافَ` | `pending` | `pending` | `CONJ+N:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `23:33:10` | `وَأَتْرَفْنَٰهُمْ` | `pending` | `pending` | `CONJ+UNK+PRON:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `96:15:5` | `لَنَسْفَعًۢا` | `pending` | `pending` | `PART+UNK:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `37:141:1` | `فَسَاهَمَ` | `pending` | `pending` | `REM+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `8:57:5` | `فَشَرِّدْ` | `pending` | `pending` | `REM+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `19:4:7` | `وَٱشْتَعَلَ` | `pending` | `pending` | `CONJ+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `2:260:22` | `فَصُرْهُنَّ` | `pending` | `pending` | `REM+V+PRON:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `51:29:5` | `فَصَكَّتْ` | `pending` | `pending` | `REM+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `9:30:14` | `يُضَٰهِـُٔونَ` | `pending` | `pending` | `PFX+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `91:6:3` | `طَحَىٰهَا` | `pending` | `pending` | `V+PRON:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `22:2:3` | `تَذْهَلُ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `28:23:15` | `تَذُودَانِ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `4:83:8` | `أَذَاعُوا۟` | `token_only_override` | `token_only_override` | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `2:16:7` | `رَبِحَت` | `token_only_override` | `token_only_override` | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `12:12:4` | `يَرْتَعْ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `83:14:3` | `رَانَ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:PERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `11:31:17` | `تَزْدَرِىٓ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `37:94:3` | `يَزِفُّونَ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `38:16:4` | `قِطَّنَا` | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `21:103:8` | `يَوْمُكُمُ` | `token_only_override` | `token_only_override` | `N+POSS:NOMINATIVE:TOKEN-ONLY` | `required_not_complete` |
| `6:130:13` | `يَوْمِكُمْ` | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `7:51:14` | `يَوْمِهِمْ` | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `13:41:8` | `أَطْرَافِهَا` | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `14:43:7` | `طَرْفُهُمْ` | `token_only_override` | `token_only_override` | `N+POSS:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `27:40:14` | `طَرْفُكَ` | `token_only_override` | `token_only_override` | `N+POSS:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `3:195:24` | `سَبِيلِى` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `22:47:12` | `سَنَةٍۢ` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `29:14:9` | `سَنَةٍ` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `2:96:14` | `سَنَةٍۢ` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `32:5:15` | `سَنَةٍۢ` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `46:15:20` | `سَنَةًۭ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `5:26:6` | `سَنَةًۭ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `70:4:11` | `سَنَةٍۢ` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `10:45:7` | `سَاعَةًۭ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `15:91:4` | `عِضِينَ` | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `12:92:5` | `الْيَوْمَ` | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `101:4:1` | `يَوْمَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `10:15:38` | `يَوْمٍ` | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `10:93:19` | `يَوْمَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `11:105:1` | `يَوْمَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |

No row is `rich_certified`. VN-19 evidence is useful for exact segment roles, parse keys, learner explanations, blockers, and renderer fixtures. It is not sufficient for live apply, broad public rollout, source-wide propagation, or family propagation.

## Public Boundary

Every row keeps public preview payloads source-clean as `src=qamus`, `kind=authored`, `lang=en`. Internal evidence labels stay only in the sidecar. No source label is authorized for public hover output.

## Flywheel Impact

- Sarf updates: no new sarf procedure edit in this tranche; VN-19 reuses the committed finite-verb, suffix-pronoun, nominal-derivative, and component-only gates already represented in sarf procedures/drills/evals.
- Nahw updates: no new nahw procedure edit in this tranche; VN-19 reuses the committed relation-sensitive, preposition/governor, case/iʿrāb, and token-only override gates already represented in nahw procedures/drills/evals.
- Curriculum updates: no new curriculum prose needed in this tranche; the rows reinforce existing VN/RICH lessons that readable English is not rich certification and component evidence cannot certify a whole token.
- Assessment/checkpoint updates: no new checkpoint file needed; these rows remain suitable future assessment examples for finite verbs, suffix-bearing nouns, and relation-sensitive nominals.
- Progress/missed-error categories: no new category needed; use the existing finite-verb dictionary leakage, suffix/pronoun omitted, component-only trap, and renderer-segmentation categories.
- Drills/evals/regressions: regression hook added via `tools/check_regressions.py`; no new grammar eval is required because no row advances to certification.
- Production-bug lessons: no new lesson file required; VN-19 belongs to existing repeated classes rather than a new defect class.
- Renderer requirements: VN-19 emits renderer fixtures for prefixed verbs/nouns, suffix-bearing rows, and nominal rows whose flat English cannot teach composition.
- Future tranche routing: continue exact-address gating for component-only, finite verb, suffix-heavy nominal, relation-sensitive nominal, and renderer-only rows; do not promote family-wide before two-vote/source gates.

Repeated issue counts observed in source parse-key components:

- `article_definiteness_requires_rich_segments`: 1
- `component_only_candidate_no_whole_token_propagation`: 10
- `finite_verb_dictionary_gloss_or_form_review`: 16
- `missing_rich_renderer_segments`: 40
- `noun_hover_may_leak_verb_infinitive`: 1
- `preposition_or_attached_relation_requires_nahw_review`: 16
- `suffix_or_attached_pronoun_requires_visible_accounting`: 11
- `surface_family_requires_token_only_override`: 17
- `verb_entry_nominal_derivative_or_lexical_noun_pos_review`: 1

## Acceptance Commands

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_19_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_19_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_19_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_19_standard.sample.jsonl
python tools/check_regressions.py
git diff --check
```
