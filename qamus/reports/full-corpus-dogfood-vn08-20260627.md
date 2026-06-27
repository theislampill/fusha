# Full-Corpus Dogfood VN-08 - Eighth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage/correctness claim was
changed.

Source batch: `out/standard-tranche-vn08-20260627/`

## Scope

- Verbs: `v363` through `v407`.
- Nouns: `n396` through `n445`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `1,016`, including `910` whole/resolved rows and `106`
  component-only evidence rows.
- Zero-row entries: `n442`.

This tranche advances dogfood review only. It does not create applyable hover
decisions.

## Controller Counts

| class | rows |
|---|---:|
| pending/blocker | 1 |
| populated_uncertified | 741 |
| token_only_override | 274 |

Routes:

- `blocker_queue_row`: `742`
- `repair_candidate`: `274`

Repair-preview-ready rows: `0`.

## Review Packets

Bounded reviewer packets were generated:

- entry linkage review: `240` rows;
- learner explanation review: `240` rows;
- rich renderer review: `240` rows;
- nahw context review: `240` rows;
- noun sarf review: `240` rows;
- verb sarf review: `240` rows.

Subagent review confirmed all reviewed rows kept `may_apply_live:false`.

## Dominant Findings

VN-08 surfaced four repeated classes:

- `إِلَّا` / `إِلَّآ` rows were readable as "except" but not rich-certified.
  They need polarity, mustathnā/minhu, exception type, and case policy.
- `إِلًّۭا` rows are lexical noun rows ("bond/tie"), not exception particles.
  Exact surface must block stripped-surface exception propagation.
- `لِلَّهِ` rows need lām + Allah proper-name PP/predicate review. They are
  not suffix-pronoun rows and not host-only Allah rows.
- Component-only rows such as `فَتَرَبَّصُوا۟`, `بِمُعَذَّبِينَ`,
  `بِالْخُنَّسِ`, and `بِزَعْمِهِمْ` may improve candidate routing, but they
  cannot create whole-token certification, `auto_safe`, closure coverage, or
  hover coverage.

The tranche also repeated finite-verb/object-suffix and nominal/POS leakage:
`يُخَفَّفُ`, `يُبَايِعُونَكَ`, `كَالُوهُمْ`, `رَكَّبَكَ`, `تَرَبُّصُ`,
`شَانِئَكَ`, `إِصْرَهُمْ`, and `مَّرْقَدِنَا`.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:9:7 | `إِلَّآ` | except | exception frame missing | exception particle plus full exception frame | populated_uncertified -> needs_nahw_review/blocker | two-vote exact-address review |
| 9:8:8 | `إِلًّۭا` | bond of kinship | lexical noun vs exception false-positive | bond/tie noun by exact context | populated_uncertified -> lexical noun false-positive guard | two-vote exact-address review |
| 1:2:2 | `لِلَّهِ` | belongs to Allah | lām + Allah PP not suffix row | lām relation plus proper-name host | populated_uncertified -> needs_nahw_review | two-vote PP/attachment review |
| 2:68:17 | `بِكْرٌ` | virgin | false bā split risk | lexical noun/adjective, not PP split | token_only_override -> false-preposition fixture | exact surface/POS review |
| 108:3:2 | `شَانِئَكَ` | hater | suffix omitted | hater/one who hates + `كَ` | token_only_override -> suffix fixture | rich metadata backfill |
| 7:157:26 | `إِصْرَهُمْ` | burden, heavy commitment | suffix omitted | burden + `هُمْ` | token_only_override -> suffix fixture | rich metadata backfill |
| 81:15:3 | `بِالْخُنَّسِ` | lurking, hiding | component-only PP evidence | bā' + article/host + attachment | component_only -> blocker | two-vote PP review |
| 6:136:12 | `بِزَعْمِهِمْ` | to claim | component-only PP + suffix | bā' + claim/host + their + attachment | component_only -> blocker | two-vote PP/suffix review |
| 26:138:3 | `بِمُعَذَّبِينَ` | to punish | component-only host evidence | bā' + governed passive-participle-like host | component_only -> blocker | whole-token proof |
| 2:86:8 | `يُخَفَّفُ` | to be light or make something light/easy | finite/passive dictionary leakage | passive/imperfect verb by exact context | populated_uncertified -> needs_sarf_review | rich metadata backfill |
| 48:10:3 | `يُبَايِعُونَكَ` | to exchange a pledge for a heavenly reward | object suffix hidden | finite verb + `كَ` object | populated_uncertified -> suffix/finite fixture | rich metadata backfill |

## Skill Impact

Updated nahw:

- `nahw/procedures/exception-and-vocative-review.md` now records the VN-08
  `إِلَّا` exception-frame requirement and lexical `إِلًّا` false-positive.
- `nahw/procedures/preposition-pronoun.md` now records the lām + Allah PP
  false suffix guard.
- `nahw/procedures/pp-attachment-review.md` now records VN-08 `لِلَّهِ`,
  `بِالْخُنَّسِ`, and `بِزَعْمِهِمْ` PP attachment blockers.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-08 exception, PP, false
  bā split, and suffix-routing drills.
- `nahw/evals/particle-function-eval.jsonl`, `nahw/evals/irab-polysemy-eval.jsonl`,
  and `nahw/evals/suffix-pronoun-eval.jsonl` add VN-08 fixtures.

Updated sarf:

- `sarf/procedures/bulk-source-triangulation.md` now explicitly separates
  component-level candidate evidence from whole-token certification.
- `sarf/procedures/verb-form-and-mood-review.md` records VN-08 passive/finite
  and component-only verb rows.
- `sarf/procedures/nominal-derivative-decision.md` records VN-08 nominal/POS
  traps around `تَرَبُّصُ`, `إِلًّا`, `بِكْرٌ`, and `لِلَّهِ`.
- `sarf/drills/verb-measures.md` adds VN-08 verb/POS/component drills.
- `sarf/evals/false-clitic-split-eval.jsonl` and
  `sarf/evals/nominal-derivative-error-eval.jsonl` add VN-08 fixtures.

No-op reasons:

- Entry `n442` had zero live hover rows in this tranche, so it is manifest-only
  and did not produce skill or repair output.
- Repair-preview-ready remains `0`: this tranche did not run MCP/i'rab review,
  external source triangulation, two-vote adjudication, global grammar gates,
  owner approval, or apply planning.
- Learner explanation review was packet-shaped but not rich-certified; VN-08
  committed production-bug lessons to preserve the teachable failures instead.

## Production-Bug Lessons

Committed sample:
`qamus/examples/dogfood_vn08_production_bug_lesson.sample.jsonl`

Rows:

- `quran:2:9:7` / `wbw:2:9:7` - exception frame missing behind readable
  "except".
- `quran:9:8:8` / `wbw:9:8:8` - lexical `إِلًّا` false-positive guard.
- `quran:1:2:2` / `wbw:1:2:2` - lām + Allah PP is not suffix morphology.
- `quran:9:24:24` / `wbw:9:24:24` - component-only waiting evidence cannot
  certify `فَتَرَبَّصُوا۟`.
- `quran:48:10:3` / `wbw:48:10:3` - finite verb with `كَ` object suffix.

## Renderer Requirements

VN-08 generated renderer requirements for:

- exception particles with explicit exception-frame breakdown;
- lexical noun false-positive rows that must not receive function-token colors;
- lām + Allah PP/proper-name rows;
- bā' + host/suffix/attachment rows;
- finite verbs with visible object suffixes;
- component-only evidence rows that must remain visually and procedurally
  blocked until whole-token rich metadata exists.

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
