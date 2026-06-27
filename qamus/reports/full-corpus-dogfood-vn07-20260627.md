# Full-Corpus Dogfood VN-07 - Seventh Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage/correctness claim was
changed.

Source batch: `out/standard-tranche-vn07-20260627/`

## Scope

- Verbs: `v318` through `v362`.
- Nouns: `n346` through `n395`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `627`, including `434` whole/resolved rows and `193`
  component-only evidence rows.
- Zero-row entries: none.

This leaves the dogfood lane aligned with the tranche schedule; it does not
change live hover data.

## Controller Counts

| class | rows |
|---|---:|
| pending/blocker | 5 |
| populated_uncertified | 372 |
| token_only_override | 250 |

Routes:

- `blocker_queue_row`: `377`
- `repair_candidate`: `250`

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated:

- entry linkage review: `200` rows;
- learner explanation review: `200` rows;
- rich renderer review: `200` rows;
- nahw context review: `0` rows from the automatic lane detector;
- noun sarf review: `0` rows from the automatic lane detector;
- verb sarf review: `0` rows from the automatic lane detector.

Manual controller review still found repeated skill-impact classes below. The
zero rows in those automatic packets are detector limitations, not proof that
the tranche has no grammar work.

## Dominant Findings

VN-07 is dominated by string-populated rows that need rich segmentation, plus
candidate-linkage examples already familiar from earlier tranches:

- `مِنِّى` / `مِّنِّى` appeared in the `تَمَنَّى` tranche. These are
  preposition-plus-pronoun rows, not wish-verb hovers.
- `يَتَمَنَّوْهُ` is a finite Form V verb with an attached `هُ` object; the
  object cannot vanish behind "to desire or wish".
- `مَوَازِينُهُۥ`, `ٱلْمَوَازِينَ`, `ٱلْمِيزَان`, and `وَزْنًا` appeared
  inside the `وَزَنُوهُمْ` family. They are scales/balance/weight noun or
  masdar rows, sometimes suffix-bearing, not finite "to weigh" rows.
- `كَادُوا`, `يَكَادُ`, and related rows need the kāda-sister construction and
  predicate/context before a learner-safe hover.
- `فَرِيضَةً`, `مَّفْرُوضًا`, and `فَارِضٌ` show verb-entry nominal derivative
  leakage around `فَرَضَ`.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:38:7 | `مِّنِّى` | from | preposition-pronoun row in verb tranche | `مِن` + 1sg suffix; from me/Me by context | populated_uncertified -> needs_nahw_review/blocker | two-vote exact-address review |
| 2:95:2 | `يَتَمَنَّوْهُ` | to desire or wish... | finite verb object suffix hidden | Form V imperfect plural + `هُ` object | token_only_override -> suffix/finite fixture | rich metadata backfill + exact-address review |
| 2:71:23 | `كَادُوا۟` | to almost do, but not do | near-verb dictionary gloss | kāda-sister construction + predicate context | populated_uncertified -> needs_nahw_review | two-vote exact-address review |
| 7:8:6 | `مَوَٰزِينُهُۥ` | to weigh | weighing noun row in verb tranche | plural scales noun + `هُ` suffix | token_only_override -> nominal/suffix fixture | rich metadata backfill |
| 55:7:4 | `ٱلْمِيزَانَ` | the balance | article + noun, not finite verb | definite balance noun by case/context | token_only_override -> renderer requirement | rich metadata backfill |
| 4:7:19 | `مَّفْرُوضًۭا` | to ordain, obligate... | nominal derivative gets verb prose | ordained/obligated portion by POS/context | token_only_override -> nominal derivative fixture | rich metadata backfill |
| 8:43:5 | `مَنَامِكَ` | a dream in one's sleep | suffix not visible | dream/sleep noun + `كَ` possessor | token_only_override -> suffix review | rich metadata backfill |
| 10:54:2 | `النَّدَامَةَ` | null | pending nominal row | regret noun by exact context | pending/blocker -> blocker queue | two-vote exact-address review |
| 47:5:3 | `بَالَهُمْ` | state, condition | suffix-bearing noun host | state/condition + `هُمْ` | token_only_override -> suffix review | rich metadata backfill |
| 2:219:16 | `تَتَفَكَّرُونَ` | to ponder deeply... | component-only verb evidence | finite verb review below whole-token gate | component_only -> blocker | component-only blocker |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` adds VN-07 strict-surface
  examples for `مِنِّى`, `يَتَمَنَّوْهُ`, weighing-family nouns, and
  `فَرَضَ` nominal rows.
- `sarf/procedures/nominal-derivative-decision.md` records the VN-07
  obligation/allotment derivative class for `مَّفْرُوضًا` and related rows.
- `sarf/procedures/clitic-and-host-morphology.md` adds VN-07 preposition
  suffix, finite object suffix, and possessed noun examples.
- `sarf/drills/verb-measures.md` adds VN-07 strict-surface drill rows.
- `sarf/evals/false-clitic-split-eval.jsonl` adds VN-07 fixtures for
  `مِنِّى`, `يَتَمَنَّوْهُ`, and `مَوَازِينُهُۥ`.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds `مَّفْرُوضًا` as a
  passive-participle/nominal derivative row that must not inherit finite verb
  prose.

Updated nahw:

- `nahw/procedures/particle-function-decision.md` adds VN-07
  preposition-plus-pronoun routing.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-07 preposition,
  near-verb, and noun-family rows.
- `nahw/evals/particle-function-eval.jsonl` adds `مِنِّى`.
- `nahw/evals/irab-polysemy-eval.jsonl` adds `مِنِّى`,
  `يَتَمَنَّوْهُ`, `مَوَازِينُهُۥ`, and `كَادُوا۟`.

No-op reasons:

- Repair-preview-ready rows remain `0`; this tranche did not run source
  triangulation, MCP/i'rab review, two-vote response, owner approval, or apply
  planning.
- The automatic `nahw`/`sarf` packets were empty because the detector only
  surfaced missing rich segmentation. The manual controller preserved the
  repeated grammar classes in skill/eval artifacts instead of silently calling
  the tranche renderer-only.
- Component-only evidence remains below whole-token certification. It may
  enrich candidates but cannot create `auto_safe`, closure coverage, hover
  coverage, or parse-family propagation.

## Production-Bug Lessons

Committed sample:
`qamus/examples/dogfood_vn07_production_bug_lesson.sample.jsonl`

Rows:

- `quran:2:38:7` / `wbw:2:38:7` - `مِنِّى` misfiled through a verb-entry
  candidate lane.
- `quran:2:95:2` / `wbw:2:95:2` - finite Form V verb hides attached `هُ`
  object.
- `quran:2:71:23` / `wbw:2:71:23` - kāda-sister row needs predicate/context.
- `quran:7:8:6` / `wbw:7:8:6` - scales noun and suffix hidden by weighing
  verb family.
- `quran:4:7:19` / `wbw:4:7:19` - nominal derivative inherited verb prose.

## Renderer Requirements

VN-07 generated renderer requirements for:

- preposition plus attached pronoun rows;
- finite verb rows with object suffixes;
- near-verb constructions whose parse key must preserve construction role;
- definite/plural/possessed noun rows inside verb-entry families;
- component-only evidence rows that must stay blocked until whole-token rich
  parse metadata exists.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche produced dogfood evidence, lessons, and regression targets
only. It did not run global grammar gates, MCP/source triangulation, two-vote
review, owner approval, or any live apply plan.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn07_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn07_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn07_production_bug_lesson.sample.jsonl`
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
- Candidate token-decision JSONL is not applyable from this tranche. Live apply
  remains owner-gated after all verb/noun tranches, final full-corpus rerun,
  global grammar gates, row-level gates, dual/two-vote gates, source/MCP
  triangulation, rebuild proof, health check, public readback, no-leak scan,
  and rollback plan.
