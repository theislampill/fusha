# VN-RICH-CERT-20 Standard Certification Queue

Repo-only rich-hover certification queue. This report converts the VN-RICH seed rows into conservative production-readiness classes without authorizing live apply, public rollout, WBW rebuild, mirror sync, service restart, or hover-ledger mutation.

## Inputs

- Source rich-hover sample: `qamus/examples/rich_hover_vn_rich_20_standard.sample.jsonl`
- Source evidence sidecar: `qamus/examples/rich_hover_vn_rich_20_standard_evidence.sample.jsonl`
- Identity remains exact `quran:S:A:W` / `wbw:S:A:W`; `parse_key` is not primary identity.

## Outputs

- Certification queue: `qamus/examples/rich_cert_vn_rich_cert_20_standard.sample.jsonl`
- Internal evidence sidecar: `qamus/examples/rich_cert_vn_rich_cert_20_standard_evidence.sample.jsonl`
- Renderer fixture: `qamus/examples/rich_cert_vn_rich_cert_20_renderer_fixture.sample.jsonl`

## Counts

- Rows: `40`
- `pending`: 4
- `preview_only`: 17
- `token_only_override`: 19
- `rich_certified`: 0
- `may_apply_live=true`: 0
- `component_candidates_can_certify=true`: 0
- `parse_key_primary_identity=true`: 0

Source-state counts:

- `pending`: 4
- `rich_candidate`: 17
- `token_only_override`: 19

Blocker counts:

- `component_only_candidate_no_whole_token_propagation`: 4
- `none`: 36

## Rows

| Loc | Surface | Source state | Certification state | Parse key | Next gate |
|---|---|---|---|---|---|
| `53:48:4` | `وَأَقْنَىٰ` | `pending` | `pending` | `CONJ+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `53:34:3` | `وَأَكْدَىٰٓ` | `pending` | `pending` | `CONJ+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `9:35:7` | `فَتُكْوَىٰ` | `pending` | `pending` | `REM+V:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `37:142:1` | `فَٱلْتَقَمَهُ` | `pending` | `pending` | `REM+V+PRON:COMPONENT-ONLY-PENDING` | `required_not_complete` |
| `25:7:9` | `ٱلْأَسْوَاقِ` | `rich_candidate` | `preview_only` | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `28:15:17` | `عَدُوِّهِۦ` | `rich_candidate` | `preview_only` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `28:15:25` | `عَدُوِّهِۦ` | `rich_candidate` | `preview_only` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `2:158:2` | `ٱلصَّفَا` | `rich_candidate` | `preview_only` | `ART+N:UNKNOWN:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `21:11:2` | `قَصَمْنَا` | `token_only_override` | `token_only_override` | `V:UNKNOWN:PERFECT:UNKNOWN+PRON:TOKEN-ONLY` | `required_not_complete` |
| `18:77:17` | `يَنقَضَّ` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `11:44:6` | `أَقْلِعِى` | `token_only_override` | `token_only_override` | `V:UNKNOWN:IMPERFECT:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `19:59:4` | `خَلْفٌ` | `rich_candidate` | `preview_only` | `N:NOMINATIVE:TOKEN-ONLY` | `required_not_complete` |
| `28:11:7` | `جُنُبٍۢ` | `rich_candidate` | `preview_only` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `67:15:9` | `مَنَاكِبِهَا` | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `2:182:9` | `بَيْنَهُمْ` | `rich_candidate` | `preview_only` | `N:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `2:188:4` | `بَيْنَكُم` | `rich_candidate` | `preview_only` | `N:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `2:213:32` | `بَيْنَهُمْ` | `rich_candidate` | `preview_only` | `N:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `3:123:4` | `بِبَدْرٍ` | `token_only_override` | `token_only_override` | `P+N:GEN:TOKEN-ONLY` | `required_not_complete` |
| `3:96:7` | `بِبَكَّةَ` | `token_only_override` | `token_only_override` | `P+N:GEN:TOKEN-ONLY` | `required_not_complete` |
| `23:20:5` | `سَيْنَآءَ` | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `95:2:2` | `سِينِينَ` | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `20:12:9` | `طُوًۭى` | `token_only_override` | `token_only_override` | `N:UNKNOWN:TOKEN-ONLY` | `required_not_complete` |
| `55:33:9` | `أَقْطَارِ` | `token_only_override` | `token_only_override` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `5:95:26` | `ٱلْكَعْبَةِ` | `token_only_override` | `token_only_override` | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `58:11:9` | `ٱلْمَجَٰلِسِ` | `token_only_override` | `token_only_override` | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `11:44:13` | `ٱلْجُودِىِّ` | `token_only_override` | `token_only_override` | `ART+N:GENITIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `48:24:9` | `مَكَّةَ` | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `21:96:3` | `حَدَبٍ` | `token_only_override` | `token_only_override` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `9:25:8` | `حُنَيْنٍ` | `token_only_override` | `token_only_override` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `28:30:3` | `شَاطِئِ` | `token_only_override` | `token_only_override` | `N:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `33:26:8` | `صَيَاصِيهِمْ` | `token_only_override` | `token_only_override` | `N+POSS:GENITIVE:TOKEN-ONLY` | `required_not_complete` |
| `2:198:12` | `عَرَفَٰتٍۢ` | `rich_candidate` | `preview_only` | `N:GENITIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `9:25:5` | `مَوَاطِنَ` | `token_only_override` | `token_only_override` | `N:ACCUSATIVE:TOKEN-ONLY` | `required_not_complete` |
| `2:68:19` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `2:97:14` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `2:102:40` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `2:136:3` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `2:164:38` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `2:213:15` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |
| `2:224:10` | `بَيْنَ` | `rich_candidate` | `preview_only` | `N:ACCUSATIVE:RICH-RENDERER-BACKFILL` | `required_not_complete` |

No row is `rich_certified`. VN-20 evidence is useful for exact segment roles, parse keys, learner explanations, blockers, and renderer fixtures. It is not sufficient for live apply, broad public rollout, source-wide propagation, or family propagation.

## Public Boundary

Every row keeps public preview payloads source-clean as `src=qamus`, `kind=authored`, `lang=en`. Internal evidence labels stay only in the sidecar. No source label is authorized for public hover output.

## Flywheel Impact

- Sarf updates: no new sarf procedure edit in this tranche; VN-20 reuses the committed finite-verb, suffix-pronoun, article/host, nominal-derivative, proper/common, and component-only gates already represented in sarf procedures/drills/evals.
- Nahw updates: no new nahw procedure edit in this tranche; VN-20 reuses the committed relation-sensitive, preposition/governor, case/iʿrāb, PP/location, and token-only override gates already represented in nahw procedures/drills/evals.
- Curriculum updates: no new curriculum prose needed in this tranche; the rows reinforce existing VN/RICH lessons that readable English is not rich certification and component evidence cannot certify a whole token.
- Assessment/checkpoint updates: no new checkpoint file needed; these rows remain suitable future assessment examples for preposition-host location rows, finite verbs, suffix-bearing nouns, and relation-sensitive location nouns.
- Progress/missed-error categories: no new category needed; use the existing finite-verb dictionary leakage, suffix/pronoun omitted, preposition-host omitted, component-only trap, and renderer-segmentation categories.
- Drills/evals/regressions: regression hook added via `tools/check_regressions.py`; no new grammar eval is required because no row advances to certification.
- Production-bug lessons: no new lesson file required; VN-20 belongs to existing repeated classes rather than a new defect class.
- Renderer requirements: VN-20 emits renderer fixtures for prefixed verbs, article-bearing nouns, suffix-bearing location nouns, preposition-host place names, and `بَيْنَ` relation rows whose flat English cannot teach composition.
- Future tranche-routing implications: VN-RICH-CERT standard tranches are now complete; the next step is the required RICH-CERT flywheel consolidation checkpoint before any RH-LIVE preview planning.

Repeated issue counts observed in source parse-key components:

- `article_definiteness_requires_rich_segments`: 5
- `component_only_candidate_no_whole_token_propagation`: 4
- `finite_verb_dictionary_gloss_or_form_review`: 7
- `missing_rich_renderer_segments`: 40
- `noun_hover_may_leak_verb_infinitive`: 2
- `preposition_or_attached_relation_requires_nahw_review`: 6
- `suffix_or_attached_pronoun_requires_visible_accounting`: 6
- `surface_family_requires_token_only_override`: 19

## Acceptance Commands

```powershell
python tools/validate_rich_hover_certification.py qamus/examples/rich_cert_vn_rich_cert_20_standard.sample.jsonl --evidence-jsonl qamus/examples/rich_cert_vn_rich_cert_20_standard_evidence.sample.jsonl --renderer-jsonl qamus/examples/rich_cert_vn_rich_cert_20_renderer_fixture.sample.jsonl
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_20_standard.sample.jsonl
python tools/check_regressions.py
git diff --check
```
