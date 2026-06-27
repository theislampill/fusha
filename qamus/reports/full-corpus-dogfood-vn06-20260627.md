# Full-Corpus Dogfood VN-06 - Sixth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/standard-tranche-vn06-20260627/`

## Scope

- Verbs: `v273` through `v317`.
- Nouns: `n296` through `n345`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `2711`, including `2498` whole/resolved rows and `213` component-only evidence rows.
- Zero-row entries: `n300`, `n305`, `n308`, `n313`, `n322`, `n326`.

## Controller Counts

| class | rows |
|---|---:|
| known_defect | 1 |
| pending/blocker | 18 |
| populated_uncertified | 2427 |
| token_only_override | 265 |

Routes:

- `blocker_queue_row`: `2445`
- `repair_candidate`: `266`

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated:

- entry linkage review: `200` rows;
- learner explanation review: `200` rows;
- nahw context review: `200` rows;
- noun sarf review: `180` rows;
- rich renderer review: `200` rows;
- verb sarf review: `180` rows;

## Dominant Finding

VN-06 is dominated by a candidate-linkage/POS-function issue: `v285` (`مَنَّ`, root `م ن ن`) collected `مِن`, `مِّن`, `مِنَ`, `مَنْ`, and `ٱلْمَنَّ` rows. The readable English strings (`from`, `who / whoever`, `manna`) are not proof that a verb-entry family can certify the token. Strict surface, POS, and nahw function decide the lane.

Other repeated classes:

- verb-entry nominal rows: `ثَمَرَةٍ`, `ثَمَرِهِۦ`, `مَرَضٌ`, `ٱلْمَنَّ`, `مُصَلًّى`, `غَضَبٍ`, `خِزْىٌ`;
- finite or derived verbs with dictionary/slash prose: `ٱشْتَرَوُا`, `يَوَدُّ`, `ٱسْتَسْقَىٰ`, `تَلْبِسُوا`;
- suffix-bearing nominal/adverbial rows: `حَوْلَهُۥ`, `ثَمَرِهِۦ`;
- component-only rows that are useful for routing but not whole-token certificates.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:4:8 | `مِن` | from | verb-entry function-token candidate leak | preposition + PP attachment | populated_uncertified -> needs_nahw_review/blocker | two-vote exact-address review |
| 2:97:2 | `مَن` | who / whoever | `مَنْ`/`مِن`/`مَنَّ` family collision | relative/interrogative/conditional by context | populated_uncertified -> particle-function blocker | two-vote exact-address review |
| 2:57:6 | `ٱلْمَنَّ` | manna... | lexical noun inside verb/function candidate family | definite noun host | populated_uncertified -> needs_sarf_review | two-vote exact-address review |
| 2:25:17 | `ثَمَرَةٍ` | fruit | verb-entry noun leak | fruit noun/case role | populated_uncertified -> nominal regression | two-vote exact-address review |
| 6:141:19 | `ثَمَرِهِۦ` | to fruit; bear fruit | possessed noun gets verb infinitive | noun host + `هِ` possessor | component_only -> suffix/nominal blocker | component-only blocker |
| 2:10:3 | `مَّرَضٌۭ` | spiritual sickness / hypocrisy... | state noun vs finite verb family | sickness/state noun by context | populated_uncertified -> context blocker | two-vote exact-address review |
| 2:16:3 | `ٱشْتَرَوُا۟` | to sell, buy, or trade depending on form | slash/contronym finite verb leak | exact finite trade sense by context | populated_uncertified -> production bug lesson | two-vote exact-address review |
| 2:17:9 | `حَوْلَهُۥ` | all around | suffix-bearing adverbial host hidden | around it/him by referent | populated_uncertified -> suffix fixture | two-vote exact-address review |
| 2:68:19 | `بَيْنَ` | between | function/adverb/preposition row in verb tranche | relation + attachment | populated_uncertified -> nahw blocker | two-vote exact-address review |
| 2:90:24 | `غَضَبٍۢ` | to be angry | masdar/noun gets verb infinitive | anger/wrath noun by context | token_only_override -> nominal fixture | rich metadata backfill |
| 2:42:2 | `تَلْبِسُوا۟` | to confuse something by dressing it as something else | finite verb dictionary prose | finite verb form/mood/context | token_only_override -> finite verb review | rich metadata backfill |
| 1:7:6 | `ٱلْمَغْضُوبِ` | to be angry | component-only passive/nominal evidence | governed passive participle/nominal row | component_only -> blocker | component-only blocker |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` adds VN-06 verb-entry candidate leakage and slash/finite verb guards.
- `sarf/procedures/nominal-derivative-decision.md` adds VN-06 lexical noun rows inside verb-entry families.
- `sarf/procedures/clitic-and-host-morphology.md` adds VN-06 component-candidate-vs-whole-token rules.
- `sarf/drills/verb-measures.md` adds VN-06 verb entries that contain non-verbs.
- `sarf/drills/nominal-derivatives.md` adds VN-06 fruit/sickness/manna/place-noun rows.
- `sarf/evals/false-clitic-split-eval.jsonl` adds VN-06 particle, suffix, and possessed noun guards.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds VN-06 lexical noun and masdar/place rows.

Updated nahw:

- `nahw/procedures/particle-function-decision.md` adds VN-06 strict-surface function-token routing for `مِن`, `مَنْ`, and `ٱلْمَنَّ`.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-06 function-token and candidate-linkage rows.
- `nahw/evals/particle-function-eval.jsonl` adds VN-06 `مِن`, `مَنْ`, `بَيْنَ`, and bā'/pronoun routing controls.
- `nahw/evals/irab-polysemy-eval.jsonl` adds VN-06 exact-address function, noun, contronym, and suffix fixtures.

No-op reasons:

- Repair-preview-ready rows remain `0`; this tranche did not run source triangulation, two-vote response, owner approval, or apply planning.
- Component-only evidence remains below whole-token certification. It may enrich candidates but cannot create `auto_safe`, closure coverage, or hover coverage.
- The `missing_rich_renderer_segments` flag is a renderer/metadata requirement, not a live-apply authorization.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn06_production_bug_lesson.sample.jsonl`

Rows:

- `quran:2:4:8` / `wbw:2:4:8` - function-token `مِن` misfiled through verb-entry candidate evidence.
- `quran:2:97:2` / `wbw:2:97:2` - `مَنْ` needs function/context selection and cannot merge with `مِن` or `مَنَّ`.
- `quran:2:25:17` / `wbw:2:25:17` - fruit noun row reviewed through `أَثْمَرَ` verb-entry candidate family.
- `quran:2:16:3` / `wbw:2:16:3` - finite trade verb inherited contronym slash prose.
- `quran:2:17:9` / `wbw:2:17:9` - suffix-bearing adverbial/nominal row hid the attached `هُ` contribution.

## Renderer Requirements

VN-06 generated renderer requirements for:

- particle/function rows with strict-surface segmentation;
- finite verbs whose public string is still dictionary or slash prose;
- lexical nouns and nominal derivatives inside verb-entry candidate families;
- suffix-bearing nouns/adverbials;
- component-only evidence rows that must stay blocked until whole-token parse metadata exists.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche produced dogfood evidence and regression targets only. No live source triangulation, two-vote response, owner approval, or apply plan was run.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn06_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn06_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn06_production_bug_lesson.sample.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`
- sarf/nahw drill and procedure updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`, `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
