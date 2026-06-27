# Full-Corpus Hover Dogfood Batch - Known Defects - 2026-06-27

Status: repo-only dogfood output. No live Qamus mutation, WBW rebuild, service
restart, mirror sync, hover coverage claim, or public apply happened.

Source batch:
`out/full-corpus-dogfood-82c63dd-20260627-004825/`

Controller inputs:

- `review-packets/subagent-reviews/production-bug-lesson-writer.jsonl`
- `review-packets/subagent-reviews/controller-reconciliation.jsonl`
- `review-packets/subagent-reviews/next-state-queues/`
- `review-packets/subagent-reviews/next-state-queues/known-defect-readiness/known-defect-readiness.jsonl`

## Controller Summary

- known-defect rows: `11`
- rows requiring production-bug lessons: `11`
- rows requiring renderer requirements: `11`
- rows requiring two-vote: `11`
- repair-preview-ready rows: `0`
- blocked by controller reconciliation: `11`
- public leak count: `0`
- `may_apply_live`: `false`

All 11 rows remain exact-addressed and controller-blocked. They may feed
lessons, drills, procedures, and regression fixtures, but they do not authorize
live repair, parse-family propagation, or raw-surface propagation.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | why not repair-ready | next gate | lesson id | target |
|---|---|---|---|---|---|---|---|---|
| `22:18:13` | `وَٱلشَّمْسُ` | and + the sun | conjunction/article breakdown not rich | `وَ` + `ٱل` + sun, with function role | reviewers disagree; rich renderer and grammar role still need reconciliation | controller reconciliation + two-vote | `lesson:22:18:13` | sarf clitic drill; nahw particle eval; renderer segments |
| `22:18:14` | `وَٱلْقَمَرُ` | and + the moon | conjunction/article breakdown not rich | `وَ` + `ٱل` + moon, with function role | same repeated class as 22:18:13 | controller reconciliation + two-vote | `lesson:22:18:14` | same class fixture |
| `22:18:15` | `وَٱلنُّجُومُ` | and + the stars | conjunction/article breakdown not rich | `وَ` + `ٱل` + stars, with function role | same repeated class as 22:18:13 | controller reconciliation + two-vote | `lesson:22:18:15` | same class fixture |
| `22:18:16` | `وَٱلْجِبَالُ` | and + the mountains | conjunction/article breakdown not rich | `وَ` + `ٱل` + mountains, with function role | same repeated class as 22:18:13 | controller reconciliation + two-vote | `lesson:22:18:16` | same class fixture |
| `22:18:17` | `وَٱلشَّجَرُ` | and + the trees | conjunction/article breakdown not rich | `وَ` + `ٱل` + trees, with function role | same repeated class; explicit regression row added | controller reconciliation + two-vote | `lesson:22:18:17` | `FCS-028`, `PF-042` |
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | so We destroyed them | finite verb component breakdown missing | fā' + Form IV perfect 1pl + object `هم` | fā' role and object-suffix breakdown need reconciliation | controller reconciliation + two-vote | `lesson:26:139:2` | `FCS-027`, `IP-036` |
| `2:178:22` | `بِٱلْمَعْرُوفِ` | by what is right/customary | preposition-host breakdown incomplete | bā' + article + nominal host + PP role | PP attachment/role still needs nahw gate | controller reconciliation + two-vote | `lesson:2:178:22` | `FCS-029`, `PF-041` |
| `2:21:1` | `يَٰٓأَيُّهَا` | you (who) | vocative collapse | `يَا` call + `أَيُّ` bridge + `هَا` attention + addressee | entry linkage and vocative role need reconciliation | controller reconciliation + two-vote | `lesson:2:21:1` | `PF-039`, `IP-037` |
| `33:63:1` | `يَسْـَٔلُكَ` | ask you | verb suffix breakdown missing | imperfect prefix + stem + object `كَ` | suffix is visible but full rich parse still needs reconciliation | controller reconciliation + two-vote | `lesson:33:63:1` | `FCS-026`, `IP-035` |
| `4:28:6` | `وَخُلِقَ` | and was created | passive verb/function breakdown missing | wāw + passive perfect 3ms verb | wāw role and passive parse must remain separate | controller reconciliation + two-vote | `lesson:4:28:6` | `PF-040`, `IP-039` |
| `4:28:8` | `ضَعِيفًۭا` | weak | nominal i'rab / entry linkage missing | weak, accusative indefinite nominal/adjectival role | entry linkage and exact i'rab role are not certified | controller reconciliation + two-vote | `lesson:4:28:8` | `IP-038`, entry-linkage review |

## State Transitions

- `known_defect -> production_bug_lesson`: 11 rows.
- `known_defect -> renderer_requirement`: 11 rows.
- `known_defect -> sarf_nahw_procedure_improvement`: 9 rows.
- `known_defect -> entry_linkage_review`: 2 rows.
- `known_defect -> repair_preview_ready`: 0 rows.

No row became apply-ready. The repair-preview packet remains empty until the
controller reconciles the multi-lane disagreements.

## Skill Impact

Committed skill-impact rows:
`qamus/examples/full_corpus_dogfood_known_defect_skill_impact.sample.jsonl`

Sarf updates:

- `sarf/procedures/clitic-and-host-morphology.md`: plus-sign hovers and
  bā'/article/host rows are not rich certification.
- `sarf/procedures/verb-form-and-mood-review.md`: finite verb rows require
  prefix/stem/form/subject/object breakdown.
- `sarf/drills/clitic-and-host-morphology.md`: dogfood rows added to the drill.
- `sarf/evals/false-clitic-split-eval.jsonl`: regression rows `FCS-026` to
  `FCS-029`.

Nahw updates:

- `nahw/procedures/function-token-hover-review.md`: string-correct rows may
  still be `string_correct_but_not_rich` or `needs_renderer_segments`.
- `nahw/procedures/exception-and-vocative-review.md`: `يَٰٓأَيُّهَا` is a
  vocative formula, not a one-piece "you (who)" token.
- `nahw/drills/grammar-routing-hard-cases.md`: dogfood rows added to routing.
- `nahw/evals/particle-function-eval.jsonl`: rows `PF-039` to `PF-042`.
- `nahw/evals/irab-polysemy-eval.jsonl`: rows `IP-035` to `IP-038`.

No-op reasons:

- `يَٰٓأَيُّهَا`: no new sarf rule was needed; the gap is nahw/vocative plus
  entry linkage.
- `ضَعِيفًۭا`: no new sarf rule was needed; the gap is exact entry linkage and
  i'rab role certification.

## Renderer Requirements

Rows needing rich segmentation must keep the written Arabic token intact while
making roles explicit in metadata and tooltip breakdown:

- conjunction/article/host: `22:18:13-17`
- fā' + verb + subject/object suffix: `26:139:2`
- bā' + article + host: `2:178:22`
- vocative formula: `2:21:1`
- imperfect prefix + stem + object suffix: `33:63:1`
- wāw + passive verb: `4:28:6`
- nominal/adjectival case marker: `4:28:8`

## Repair Preview Packet

Repair-preview-ready rows: `0`.

Reason: every known-defect row is currently
`controller_reconciliation_required`. The next repair-preview packet must be
built only after the controller resolves the route conflict and preserves
`may_apply_live:false` until a separate owner-gated apply plan is approved.

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`, `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement is claimed.
