# Full-Corpus Dogfood VN-02 - Second Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo,
service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/standard-tranche-vn02-20260627/`

## Scope

- Verbs: `v093` through `v137`.
- Nouns: `n096` through `n145`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `1,375`, including `1,086` whole/resolved rows and `289`
  component-only evidence rows.
- Zero-row entries: `n100`, `n105`, `n115`, `n116`, `n117`, `n118`,
  `n119`, `n122`, `n127`, `n130`, `n131`, `n134`, `n139`, `n140`,
  `n141`, `n142`, `n143`, `n145`.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 1,156 |
| token_only_override | 194 |
| pending/blocker | 24 |
| known_defect | 1 |

Routes:

- `blocker_queue_row`: `1,180`
- `repair_candidate`: `195`
- `production_bug_lesson`: `195`
- `drill_regression_fixture`: `195`
- `sarf_nahw_procedure_improvement`: controller route only; applied skill
  changes are listed below.

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated and reviewed:

- verb sarf: `180` rows;
- noun sarf: `180` rows;
- nahw context: `200` rows;
- rich renderer: `200` rows;
- Qamus entry linkage: handled by the main thread from the generated indices;
- learner explanation: handled by the main thread from the generated indices.

The reviewers converged on four VN-02 findings:

1. Finite and derived verbs still inherit dictionary prose unless form, voice,
   aspect, subject agreement, and suffix pronouns are recorded per token.
2. Passive voice and governed mood are visible grammar, not optional gloss
   polish. `فُضِّلُوا۟`, `يُولَدْ`, and laysa forms remain exact-address
   gated.
3. Proper nouns, titles, common adjectives, and finite verbs collide in the
   same entry families. `يُحْيِي` must not inherit `يَحْيَى`; `صَالِح` needs
   name/common context; `ٱلْمَسِيح` needs title/article/case handling.
4. Many populated proper-name rows remain string-only. They need source-clean
   parse-key and segment metadata before rich certification, but this is a
   renderer/data-contract issue rather than a new sarf/nahw rule.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:178:22 | `بِٱلْمَعْرُوفِ` | by what is right/customary | component-only/preposition relation | `بِـ` + definite nominal host with jar-majrūr attachment | known_defect -> production_bug_lesson + regression fixture | two-vote nahw |
| 25:9:6 | `فَضَلُّوا۟` | favor/bounty family prose | root collision / doubled-root misfile | `فَـ` + ض ل ل perfect 3mp "went astray" family, not ف ض ل | token_only_override -> quarantine | root/POS review |
| 17:70:12 | `وَفَضَّلْنَٰهُمْ` | favor/bounty family prose | finite verb object suffix leakage | `وَ` + Form II perfect 1cp + `هُمْ` object | populated_uncertified -> suffix regression | token-only two-vote |
| 16:71:10 | `فُضِّلُوا۟` | favor/bounty family prose | passive voice erased | passive Form II perfect 3mp | token_only_override -> passive fixture | token-only two-vote |
| 112:3:4 | `يُولَدْ` | active birth/child family prose | passive jussive under negation | passive/jussive weak verb in negation frame | populated_uncertified -> nahw+sarf fixture | two-vote |
| 36:78:3 | `يُحْيِي` | Prophet Yahya family | proper-name vs finite verb collision | finite verb from ح ي ي, not `يَحْيَى` the name | pending/blocker -> homograph fixture | POS/referent quarantine |
| 11:61:4 | `صَٰلِحًۭا` | pending/unpopulated | proper/common collision | Prophet Ṣāliḥ or common "righteous" by context | pending/blocker -> referent fixture | human review |
| 3:45:11 | `ٱلْمَسِيحُ` | the Messiah | title folded into proper-name entry | article + title/nominal host + case | populated_uncertified -> renderer/title blocker | title/article/case review |
| 5:95:43 | `عَادَ` | ʿĀd people family | proper people vs finite verb homograph | finite verb `returned/repeated`, not people-name | populated_uncertified -> homograph fixture | POS/referent quarantine |
| 90:3:1 | `وَوَالِدٍۢ` | birth/parent family prose | oath wāw plus nominal role lost | oath `وَ` + majrūr nominal "parent/father" | populated_uncertified -> nahw fixture | oath/PP review |
| 33:32:3 | `لَسْتُنَّ` | is/are no or not | finite laysa suffix/person missing | laysa-like finite 2fp with predicate governance | populated_uncertified -> finite laysa fixture | nahw+sarf review |
| 10:83:11 | `فِرْعَوْنَ` | Pharaoh | string-only proper-name row | proper/title noun with case and rich segment metadata | populated_uncertified -> needs_renderer_segments | renderer metadata |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` adds VN-02 passive, derived
  form, and suffix-bearing examples.
- `sarf/procedures/proper-noun.md` adds VN-02 name/title/common collision
  examples for `يَحْيَى/يُحْيِي`, `صَالِح`, `ٱلْمَسِيح`, `أَحْمَد`, and
  `عَاد`.
- `sarf/drills/verb-measures.md` adds VN-02 finite/passive/derived-form rows.
- `sarf/drills/nominal-derivatives.md` adds title/common rows from VN-02.
- `sarf/drills/homograph-regressions.md` adds proper-name vs verb/common
  collision prompts.
- `sarf/evals/false-clitic-split-eval.jsonl` adds VN-02 finite/passive/suffix
  controls.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds VN-02 title/common
  and POS-collision controls.

Updated nahw:

- `nahw/procedures/referent-context.md` adds VN-02 proper/common and
  people-name/verb homograph examples.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-02 rows for passive
  jussive, laysa agreement, title/article, and referent-sensitive collisions.
- `nahw/drills/idafa-and-jar-majrur.md` adds VN-02 bāʾ/oath/nominal rows.
- `nahw/evals/irab-polysemy-eval.jsonl` adds exact-address fixtures for
  `بِدَيْنٍ`, `وَوَالِدٍۢ`, `لَسْتُنَّ`, `يُحْيِي`, and `عَادَ`.

No-op reasons:

- Renderer-only proper-name rows such as `فِرْعَوْنَ`, `إِبْرَٰهِيمَ`,
  `نُوحٍ`, and `يُوسُفَ` need parse-key and display metadata backfill. The
  existing sarf/nahw doctrine already says these are not rich-certified.
- Component-only rows remain component evidence only; Phase 2.8 already blocks
  them from contributing to `auto_safe` or hover coverage.
- Repair-preview-ready rows remain `0`; this tranche did not run source
  triangulation, two-vote review, or owner-gated apply planning.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn02_production_bug_lesson.sample.jsonl`

Rows:

- `quran:17:70:12` / `wbw:17:70:12` - finite Form II verb plus object suffix
  hidden by dictionary prose.
- `quran:16:71:10` / `wbw:16:71:10` - passive voice erased by active/root
  family prose.
- `quran:36:78:3` / `wbw:36:78:3` - proper-name vs finite verb collision.
- `quran:11:61:4` / `wbw:11:61:4` - proper-name vs common adjective collision.
- `quran:2:282:6` / `wbw:2:282:6` - attached bāʾ plus noun receives a
  verb-derived gloss.

## Renderer Requirements

VN-02 generated renderer requirements for string-populated but non-rich rows:

- proper-name tokens need `PROPN`/title parse keys, case/form metadata, and
  visible segment readiness;
- title/article tokens such as `ٱلْمَسِيحُ` need article + host display
  metadata rather than being hidden inside the `عِيسَى` entry;
- finite verbs need prefix/stem/suffix classes and passive/voice metadata;
- visible Arabic must remain atomic while parse rows teach the pieces.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche produced dogfood evidence and regression targets only. No
live source triangulation, two-vote response, owner approval, or apply plan was
run.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn02_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn02_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn02_production_bug_lesson.sample.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- sarf/nahw drill and procedure updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`, `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
