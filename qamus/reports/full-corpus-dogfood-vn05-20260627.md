# Full-Corpus Dogfood VN-05 - Fifth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/standard-tranche-vn05-20260627/`

## Scope

- Verbs: `v228` through `v272`.
- Nouns: `n246` through `n295`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `1,191`, including `1,009` whole/resolved rows and `182`
  component-only evidence rows.
- Zero-row entries: `n252`, `n285`, `n289`, `n293`, `n294`, `n295`.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 762 |
| token_only_override | 418 |
| pending/blocker | 11 |

Routes:

- `blocker_queue_row`: `193`
- `renderer_requirement`: `580`
- `repair_candidate`: `418`

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated:

- verb sarf: `180` rows;
- noun sarf: `180` rows;
- nahw context: `200` rows;
- rich renderer: `200` rows;
- Qamus entry linkage: `200` rows;
- learner explanation: `200` rows.

Read-only reviewer findings named repeated classes: finite-verb infinitive
leakage, derived-form conflation, suffix pronoun omission, proclitic
whole-token gaps, governing-particle mood gaps, passive voice collapse,
verb-entry nominal leakage, body-part rich-renderer gaps, `ر ج ل`
lemma-shape collision, false lām splitting, and omnibus referent glosses.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 4:11:1 | `يُوصِيكُمُ` | to instruct, command, advise, or leave a last will | finite verb object suffix hidden by entry prose | finite verb + `كُم` object | token_only_override -> lesson + suffix regression | two-vote exact-address review |
| 60:8:15 | `تَبَرُّوهُمْ` | to act kindly, vast in grace | root-family prose hides object suffix | finite verb + `هُمْ` object | token_only_override -> lesson + suffix regression | two-vote exact-address review |
| 2:137:15 | `فَسَيَكْفِيكَهُمُ` | to be sufficient | stacked pronoun/object leakage | `فَ`/future stack + verb + `كَ` + `هُمُ` | populated_uncertified -> blocker row | component-only blocker |
| 12:3:5 | `ٱلْقَصَصِ` | to relate a story, tracing events one after another | story noun gets verb infinitive | definite noun/story role | token_only_override -> nominal regression + lesson | two-vote |
| 12:21:25 | `غَالِبٌ` | to overcome, defeat | active participle gets verb infinitive | nominal/active-participle role | token_only_override -> nominal derivative fixture | two-vote |
| 2:239:3 | `فَرِجَالًا` | legs | `ر ج ل` lemma-shape collision | whole-token fā + contextual on-foot/nominal review | populated_uncertified -> blocker + lesson | component-only blocker |
| 10:37:14 | `يَدَيْهِ` | hand and idiomatic extensions involving front, agency, regret, and cutting hands | omnibus body-part gloss | dual body-part + possessor/context | populated_uncertified -> renderer requirement | rich metadata backfill |
| 10:26:7 | `وُجُوهَهُمْ` | face and idiomatic meanings such as pleasure, first part of day, and Allah's Face | referent-sensitive omnibus gloss | plural possessed face by context | token_only_override -> referent fixture | human/two-vote review |
| 37:11:5 | `لَّازِبٍ` | sticky | false lām particle route | lexical adjective host, no lām particle | token_only_override -> false-clitic negative control | rich metadata backfill |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` adds VN-05 finite-derived,
  passive, suffixed, and verb-entry nominal leakage cases.
- `sarf/procedures/nominal-derivative-decision.md` adds VN-05 story noun,
  active-participle, `ر ج ل`, and `وَجْه` collision rules.
- `sarf/procedures/noun-plural-gender.md` adds VN-05 body-part, life-stage,
  suffix/number, and article/state distinction rules.
- `sarf/procedures/clitic-and-host-morphology.md` adds false-lām and
  component-only noun propagation guards.
- `sarf/drills/verb-measures.md` adds VN-05 finite/passive/suffixed verb
  drills.
- `sarf/drills/nominal-derivatives.md` adds VN-05 body-part and lemma-shape
  drills.
- `sarf/evals/false-clitic-split-eval.jsonl` adds suffix/object, stacked
  pronoun, false-lām, and component-only noun cases.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds story noun,
  active-participle, `ر ج ل`, `وَجْه`, and life-stage noun cases.

Updated nahw:

- `nahw/procedures/referent-context.md` adds VN-05 `يَد`, `وَجْه`, and
  `ر ج ل` referent/context guard.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-05 verb-object,
  noun/POS, body-part, false-lām, and context routing rows.
- `nahw/evals/irab-polysemy-eval.jsonl` adds VN-05 exact-address fixtures for
  suffix verbs, `ٱلْقَصَصِ`, `فَرِجَالًا`, `يَدَيْهِ`, and `وُجُوهَهُمْ`.
- `nahw/evals/particle-function-eval.jsonl` adds false-lām and
  `فَرِجَالًا` function-routing controls.

No-op reasons:

- The `580` renderer requirements need parse-key and rich display metadata.
  They are not live repair-ready from this tranche.
- The `182` component-only rows remain component evidence only. They do not
  create auto-safe rows, source agreement, closure coverage, or hover coverage.
- Repair-preview-ready rows remain `0`; this tranche did not run source
  triangulation, two-vote response, owner approval, or apply planning.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn05_production_bug_lesson.sample.jsonl`

Rows:

- `quran:4:11:1` / `wbw:4:11:1` - finite verb plus `كُم` object hidden by
  entry infinitive prose.
- `quran:60:8:15` / `wbw:60:8:15` - verb plus `هُمْ` object hidden by root
  family prose.
- `quran:12:3:5` / `wbw:12:3:5` - definite story noun receives verb
  infinitive.
- `quran:12:21:25` / `wbw:12:21:25` - active-participle-looking noun receives
  verb infinitive.
- `quran:2:239:3` / `wbw:2:239:3` - `ر ج ل` root family and component-only
  evidence mix leg/feet with on-foot context.

## Renderer Requirements

VN-05 generated renderer requirements for:

- finite verbs with suffix/object pronouns and passive voice;
- nouns with article/state/number/suffix morphology;
- body-part rows where a bare lemma or omnibus entry paragraph hides
  referent-sensitive context;
- false-clitic negative controls, especially lexical initial lām;
- component-only noun rows that require whole-token segmentation before hover
  trust.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche produced dogfood evidence and regression targets only. No
live source triangulation, two-vote response, owner approval, or apply plan was
run.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn05_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn05_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn05_production_bug_lesson.sample.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`
- sarf/nahw drill and procedure updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`,
  `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
