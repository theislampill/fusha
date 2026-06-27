# Full-Corpus Dogfood Vocative Batch - 2026-06-27

Status: read-only dogfood processing. No live Qamus data, WBW build, service,
mirror, hover decision ledger, or public artifact was changed.

Baseline packet:

- Source packet: `out/full-corpus-dogfood-82c63dd-20260627-004825/review-packets/issue_vocative_top100.jsonl`
- Packet summary: 100 packets, with 1 `known_defect`, 97 `needs_nahw_review`,
  and 2 `token_only_override`.
- Live mutation: `may_apply_live:false` for every sampled row.

## Controller Rows

| loc | surface | current gloss | defect class | expected token contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 2:21:1 | `يَٰٓأَيُّهَا` | you (who) | vocative formula collapsed | call + bridge + attention + following addressee | `known_defect -> production_bug_lesson + regression_fixture + skill_impact` | exact-address two-vote |
| 2:104:1 | `يَٰٓأَيُّهَا` | O you (who) | formula not rich-certified | same formula pieces plus following addressee | `populated_uncertified -> needs_nahw_review + regression_fixture` | nahw two-vote |
| 2:35:2 | `يَٰٓـَٔادَمُ` | O Adam | address phrase not rich-certified | vocative call + proper-name addressee | `populated_uncertified -> needs_nahw_review + drill fixture` | nahw two-vote |
| 2:40:1 | `يَٰبَنِىٓ` | Son. | vocative call omitted | call + addressee/possessive structure | `populated_uncertified -> production_bug_lesson + needs_nahw_review` | nahw two-vote |
| 2:54:5 | `يَٰقَوْمِ` | O my people! | addressee role not rich-certified | call + addressee + possession/idafa review | `populated_uncertified -> needs_nahw_review + regression_fixture` | nahw two-vote |
| 2:61:3 | `يَٰمُوسَىٰ` | O Moses | addressee role not rich-certified | call + proper-name addressee | `populated_uncertified -> needs_nahw_review` | nahw two-vote |
| 6:59:27 | `يَابِسٍ` | dry | false vocative detector | lexical host, no call particle | `token_only_override -> detector_false_positive + sarf_regression_fixture` | detector guard only |
| 12:43:15 | `يَابِسَٰتٍۢ` | dry | false vocative detector | lexical feminine plural host, no call particle | `token_only_override -> detector_false_positive + sarf_regression_fixture` | detector guard only |

## Skill Impact

Updated sarf:

- `sarf/procedures/clitic-and-host-morphology.md` now blocks raw `يا` prefix
  splitting unless sarf proves a real vocative piece.
- `sarf/drills/clitic-and-host-morphology.md` now includes `يَابِسٍ` and
  `يَابِسَٰتٍ` as false-vocative positive controls.
- `sarf/evals/false-clitic-split-eval.jsonl` adds `FCS-040` and `FCS-041`.

Updated nahw:

- `nahw/procedures/exception-and-vocative-review.md` now requires call particle,
  bridge/support word, attention particle, and following addressee to stay
  explainable.
- `nahw/procedures/function-token-hover-review.md` adds `يا` / `أيها`
  function-token routing and rejects lexical yā false positives.
- `nahw/drills/grammar-routing-hard-cases.md` adds vocative formula/addressee
  and false-positive rows.
- `nahw/evals/particle-function-eval.jsonl` adds `PF-048` and `PF-049`.
- `nahw/evals/irab-polysemy-eval.jsonl` adds `IP-045` and `IP-046`.

Updated curriculum:

- `curriculum/drills/hover-composition-and-routing.md` now teaches both
  `يَٰقَوْمِ` and lexical `يَابِسٍ` routing.

No-op reasons:

- `يَٰٓـَٔادَمُ`, `يَٰقَوْمِ`, and `يَٰمُوسَىٰ` do not need new sarf rules beyond
  fused-host preservation; the missing layer is nahw/addressee explanation.
- `يَابِسٍ` and `يَابِسَٰتٍ` do not need Qamus hover repair; they need detector
  and skill guardrails.

## Outputs

- Skill-impact sample:
  `qamus/examples/full_corpus_dogfood_vocative_batch_skill_impact.sample.jsonl`
- Production-bug lessons:
  `qamus/examples/dogfood_vocative_production_bug_lesson.sample.jsonl`
- Regression fixtures:
  `sarf/evals/false-clitic-split-eval.jsonl`,
  `nahw/evals/particle-function-eval.jsonl`,
  `nahw/evals/irab-polysemy-eval.jsonl`

## Apply Status

No row is repair-preview-ready from this batch. The known public hover defect at
`2:21:1` still requires exact-address two-vote review and owner-gated apply
before any live Qamus mutation.
