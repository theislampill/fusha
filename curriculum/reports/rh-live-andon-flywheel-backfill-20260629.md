# RH-LIVE ANDON Flywheel Backfill - 2026-06-29

This report records the repo-only teaching and skill updates made after RH-LIVE public-rollout ANDONs exposed
reusable learner failures. It does not mutate live Qamus, does not append whitelist rows, does not rebuild WBW, and
does not claim public coverage movement.

## Inputs Mined

- RH-LIVE particle rollout ANDONs from p066, p072, p074, p075, p077, p078, p079, p084, p094, and p096-p100.
- Existing RH-LIVE split-layer/role-color fixture lessons.
- Existing adjacent-context gloss lesson for `يَسْأَلُكَ`.
- Existing curriculum assessment/progress/tutor-runtime scaffolding.
- Existing sarf/nahw dogfood drills and parse-key/color curriculum.

No external source wording was copied into learner-facing curriculum. The examples below are Qamus-authored
teaching prompts derived from observed defect classes.

## Repeated Findings Promoted

| finding | example shape | repo surface updated | blocker class taught |
|---|---|---|---|
| Role color cannot collapse morphology into broad POS | `يُحْيِي`, `فَأَهْلَكْنَاهُمْ` | `curriculum/qamus-hover-parse-key-and-color.md`, `curriculum/drills/parse-key-and-color-layer.md`, schema/validator | `renderer_only_gap`, `hidden_imperfect_prefix` |
| Dual/plural endings must be visible | `بُرْهَٰنَانِ`, `قاعدون`, `ٱلْغَٰلِبُونَ` | sarf drills, assessment row `L3-dual-burhanan`, missed-error log | `hidden_number_morphology` |
| Participle/adjective rows must not inherit infinitives | `مُّطَاعٍۢ`, `قَدِيرٌ`-style adjective rows | `sarf/drills/nominal-derivatives.md`, assessment row `L5-participle-mutaa` | `hidden_derivative_shape`, `finite_verb_dictionary_gloss` |
| Passive suffix-bearing verbs need more than host gloss | `أُورِثْتُمُوهَا` | `sarf/drills/clitic-and-host-morphology.md`, assessment row `L7-passive-suffix-urithtumuha` | `suffix_omitted`, `wrong_irab_reasoning` |
| Learner explanations must teach Arabic, not workflow | hover explanation containing process/source-boundary prose | `nahw/drills/dogfood-nahw-remediation.md`, assessment row `L8-process-prose-hover` | `process_prose_in_hover` |
| Qur'an display text must be deterministic before segmentation | missing hamza/maddah/diacritics or selected target word | sarf/nahw dogfood drills, assessment row `L8-source-text-display-gate`, tutor routing | `quran_display_text_mismatch` |
| Card-level rollout reporting cannot hide visible flat cards | p007-style "row denominator complete" with visible blocked card | `curriculum/drills/hover-composition-and-routing.md`, missed-error log, tutor routing | `card_level_coverage_hidden` |
| Noun/adjective hosts need root/base where certifiable | common noun/adjective rows with blank root while proper/function rows need no-root reason | `sarf/SKILL.md`, parse-key/color contract | `root_family_vibes`, `renderer_only_gap` |
| Fine-grained grammar facts must still use supported renderer classes | live validator rejected unsupported active-participle/adverb classes | `curriculum/qamus-hover-parse-key-and-color.md`, `qamus/reports/morphosyntax-token-contract.md`, `sarf/SKILL.md`, `nahw/SKILL.md`, parse/color drill | `unsupported_renderer_class`, `grammar_fact_hidden_by_class_mismatch` |

## Explicit No-Ops

| finding | no-op reason |
|---|---|
| `يَسْأَلُكَ` token contribution vs adjacent subject | Already covered by assessment row `L8-verb-suffix-yasaluka`, hover-composition drill, and RH-LIVE context-gloss fixture. This pass only references it as precedent. |
| Parenthesis wrapping and horizontal scroll in live cards | Renderer/app layout issue, not a sarf/nahw skill rule. Kept as a source/display warning in drill prose; no live app change made here. |
| Entry URL p/v/n graph generation | Live rollout tooling issue. This backfill records the card-level/source-text lesson but does not edit live graph generation. |
| Additional live whitelist payloads | Out of scope for this repo-only curriculum pass. No live Qamus mutation was authorized by this task. |

## Files Updated

- `curriculum/qamus-hover-parse-key-and-color.md`
- `curriculum/drills/parse-key-and-color-layer.md`
- `curriculum/drills/hover-composition-and-routing.md`
- `curriculum/assessment/level-checkpoints.sample.jsonl`
- `curriculum/progress/missed-error-log.template.md`
- `curriculum/tutor-runtime-routing.md`
- `sarf/SKILL.md`
- `sarf/drills/dogfood-sarf-remediation.md`
- `sarf/drills/clitic-and-host-morphology.md`
- `sarf/drills/nominal-derivatives.md`
- `nahw/SKILL.md`
- `nahw/drills/dogfood-nahw-remediation.md`
- `qamus/schemas/morphosyntax-token.schema.json`
- `qamus/reports/morphosyntax-token-contract.md`
- `tools/validate_morphosyntax_token_metadata.py`

## Addendum: VN-RH-LIVE-00 Renderer-Class Normalization

During a later VN-RH-LIVE-00 append, the live renderer validator accepted the grammar analysis but rejected payload
classes outside the committed palette. The repaired rule is: keep active-participle and adverbial facts in sarf/nahw
fields, segment labels, morphlines, and learner explanations, but render them with supported classes unless a future
change updates schema, CSS, DOM fixture, validators, and regression checks together.

## Future Work

- Migrate older broad-class fixtures toward role-aware preferred classes in a dedicated fixture-only pass.
- Add a repo-side validator for card-level rollout reports so visible blocked cards cannot be hidden by row-only
  denominators.
- Extend rich-hover fixture samples for noun/adjective number and derivative shapes after the live data packet is
  stable.
- Continue the live RH-LIVE rollout in its own lane; feed any new repeated defect class back into this curriculum
  and skill flywheel.

## Validation

- `python tools/validate_morphosyntax_token_metadata.py --self-test` - pass.
- `python tools/validate_morphosyntax_token_metadata.py qamus/examples/morphosyntax_token.sample.jsonl` - pass.
- `python tools/validate_curriculum_assessment.py --self-test` - pass.
- `python tools/validate_curriculum_assessment.py curriculum/assessment/level-checkpoints.sample.jsonl` - pass.
- `python tools/validate_sarf_skill.py` - pass.
- `python tools/validate_nahw_skill.py` - pass.
- `python tools/run_grammar_evals.py` - pass, 88 cases and 8 wrong-reasoning traps.
- `python tools/check_regressions.py` - pass.
- `git diff --check` - pass.
