# Full-Corpus Dogfood VN-04 - Fourth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo,
service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/standard-tranche-vn04-20260627/`

## Scope

- Verbs: `v183` through `v227`.
- Nouns: `n196` through `n245`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `1,492`, including `1,219` whole/resolved rows and `273`
  component-only evidence rows.
- Zero-row entries: `n196`, `n197`, `n199`, `n216`, `n217`, `n220`,
  `n239`, `n240`.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 1,030 |
| token_only_override | 449 |
| pending/blocker | 9 |
| known_defect | 4 |

Routes:

- `blocker_queue_row`: `1,043`
- `repair_candidate`: `453`
- `production_bug_lesson`: `1,483`
- `drill_regression_fixture`: `1,483`
- `sarf_nahw_procedure_improvement`: controller route only; applied skill
  changes are listed below.

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated:

- verb sarf: `180` rows;
- noun sarf: `180` rows;
- nahw context: `15` rows;
- rich renderer: `200` rows;
- Qamus entry linkage: `200` rows;
- learner explanation: `200` rows.

The verb-sarf reviewer returned high-confidence findings for component-only
verb evidence, finite dictionary-infinitive leakage, missing voice/person,
derived-form collapse, missing suffix/proclitic contribution, weak/hamzated
forms, shadda/geminate collisions, and compound-entry POS/root leakage.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 12:42:10 | `فَأَنسَىٰهُ` | to forget; neglect | component-only weak finite verb | `فَ` + finite weak/causative host + `هُ` object | populated_uncertified -> blocker + lesson | two-vote whole-token proof |
| 15:3:1 | `ذَرْهُمْ` | to leave someone or something | imperative/object suffix hidden by entry prose | imperative weak-root host + `هُمْ` object | populated_uncertified -> suffix regression | two-vote exact-address review |
| 10:15:16 | `بَدِّلْهُ` | to change or replace | finite derived-form/object leakage | imperative/Form II host + `هُ` object | populated_uncertified -> blocker row | component-only blocker |
| 5:103:7 | `سَآئِبَةٍۢ` | A camel left to roam freely. | custom noun string not rich-certified | lexical noun + case metadata | known_defect -> lesson/renderer requirement | two-vote |
| 5:103:9 | `وَصِيلَةٍۢ` | A camel custom tied to continuous female births. | wāw + custom noun not rich-certified | `وَ` + lexical noun + case metadata | known_defect -> lesson/renderer requirement | two-vote |
| 15:9:4 | `ٱلذِّكْرَ` | to take note of, mention; remember; remind vigorously | noun gets verb infinitive | definite noun/reminder by context | known_defect -> POS/voice lesson | two-vote |
| 6:118:3 | `ذُكِرَ` | to take note of, mention; remember; remind vigorously | passive verb routed through noun/root entry | passive finite verb | known_defect -> passive/POS fixture | two-vote |
| 26:165:2 | `ٱلذُّكْرَانَ` | Male. | string-only nominal row | article + masculine plural/dual-looking noun | token_only_override -> needs_renderer_segments | rich metadata backfill |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` adds VN-04 weak-root,
  hamzated, passive, shadda/geminate, suffix, and component-only examples.
- `sarf/procedures/nominal-derivative-decision.md` adds the VN-04 `ذ ك ر`
  POS/voice collision rule.
- `sarf/drills/verb-measures.md` adds VN-04 weak/geminate finite-verb drills.
- `sarf/drills/nominal-derivatives.md` adds VN-04 `ذَكَر` / `ذِكْر` /
  `ذُكِرَ` and custom-noun drills.
- `sarf/evals/false-clitic-split-eval.jsonl` adds VN-04 weak finite verb,
  imperative suffix, and passive/POS controls.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds VN-04 nominal/POS
  collision controls.

Updated nahw:

- `nahw/drills/grammar-routing-hard-cases.md` adds VN-04 weak-verb,
  imperative, `ذ ك ر`, and custom-noun routing rows.
- `nahw/evals/irab-polysemy-eval.jsonl` adds VN-04 nominal/passive/imperative
  exact-address fixtures.

No-op reasons:

- The `1,030` string-populated rows routed to `needs_renderer_segments` mostly
  need parse-key and rich display metadata. Existing sarf/nahw doctrine already
  blocks rich certification until segment readiness exists.
- The `273` component-only rows remain component evidence only. They do not
  create new auto-safe rows, source agreement, closure coverage, or hover
  coverage.
- Repair-preview-ready rows remain `0`; this tranche did not run source
  triangulation, two-vote response, owner approval, or apply planning.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn04_production_bug_lesson.sample.jsonl`

Rows:

- `quran:12:42:10` / `wbw:12:42:10` - component-only weak finite verb with
  visible fā' and `هُ` object.
- `quran:15:3:1` / `wbw:15:3:1` - imperative weak verb plus `هُمْ` object
  hidden behind entry prose.
- `quran:15:9:4` / `wbw:15:9:4` - `ٱلذِّكْرَ` noun receives verb infinitive.
- `quran:6:118:3` / `wbw:6:118:3` - passive `ذُكِرَ` routed through noun/root
  entry prose.

## Renderer Requirements

VN-04 generated renderer requirements for:

- weak/hamzated/geminate finite verbs with visible proclitics and suffixes;
- passive finite verbs where color/parse metadata must preserve voice;
- custom noun rows where the entry string is readable but article/case and
  particle roles are not visible;
- `ذ ك ر` rows where the same root family contains male nouns, reminder nouns,
  and passive verbs.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche produced dogfood evidence and regression targets only. No
live source triangulation, two-vote response, owner approval, or apply plan was
run.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn04_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn04_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn04_production_bug_lesson.sample.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- sarf/nahw drill and procedure updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`,
  `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
