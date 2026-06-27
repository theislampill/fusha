# Full-Corpus Dogfood VN-09 - Ninth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage/correctness claim was
changed.

Source batch: `out/standard-tranche-vn09-20260627/`

## Scope

- Verbs: `v408` through `v452`.
- Nouns: `n446` through `n495`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `442`, including `319` whole/resolved rows and `123`
  component-only evidence rows.
- Zero-row entries: none.

This tranche advances dogfood review only. It does not create applyable hover
decisions.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 241 |
| token_only_override | 201 |

Routes:

- `blocker_queue_row`: `241`
- `repair_candidate`: `201`

Repair-preview-ready rows: `0`.

## Review Packets

Bounded reviewer packets were generated:

- entry linkage review: `240` rows;
- learner explanation review: `240` rows;
- rich renderer review: `240` rows;
- nahw context review: `55` rows;
- noun sarf review: `115` rows;
- verb sarf review: `240` rows.

Subagent review confirmed all reviewed rows kept `may_apply_live:false`.

## Dominant Findings

VN-09 surfaced five repeated classes:

- finite verbs such as `يَشْتَهُونَ`, `يَعْصِمُكَ`, `يَجْتَبِيكَ`, and
  `وَفَدَيْنَٰهُ` still inherit entry infinitive prose instead of exact finite
  form, subject, and suffix contribution;
- component-only rows such as `لِتُضَيِّقُوا۟`, `كَلَمْحِ`, and `لَأَوَّٰهٌ`
  improved candidate routing but must remain below whole-token certification;
- `لِمَا` / `لَّمَّا` / `لَمَّا` / `لَّمًّا` / `ٱللَّمَمَ` style families need
  strict surface, particle function, exception/negative/temporal role, and
  attachment review before any propagation;
- nominal rows such as `أَقْوَٰتَهَا`, `تَفَثَهُمْ`, `مَوَٰقِيتُ`,
  `ٱلسِّجْنُ`, and `ٱلشَّهَوَٰتِ` require suffix, POS, number/state/case, and
  derivative review instead of verb-entry family reuse;
- whole-token rows whose only defect is missing rich renderer metadata should
  move to renderer metadata backfill, not force a new linguistic skill rule.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 34:54:5 | `يَشْتَهُونَ` | to desire | finite verb dictionary leakage | plural imperfect finite contribution | populated_uncertified -> needs_sarf_review | rich metadata + two-vote if wording changes |
| 9:25:16 | `وَضَاقَتْ` | to strain, distress | component-only finite verb family | wāw + finite feminine verb | component_only -> blocker | whole-token proof |
| 65:6:9 | `لِتُضَيِّقُوا۟` | to strain, distress | lām + finite verb component-only | lām function + finite plural verb | component_only -> blocker | lām/mood review |
| 5:67:16 | `يَعْصِمُكَ` | to protect against harm | object suffix hidden | finite verb + `كَ` object | token_only_override -> suffix fixture | rich metadata + exact-address review |
| 12:6:2 | `يَجْتَبِيكَ` | to choose someone as if filling their reservoir with blessings | object suffix hidden | finite verb + `كَ` object | token_only_override -> suffix fixture | rich metadata + exact-address review |
| 37:107:1 | `وَفَدَيْنَٰهُ` | to ransom or compensate | component-only verb + suffix | wāw + finite verb + `هُ` object | component_only -> blocker | whole-token proof |
| 41:10:10 | `أَقْوَٰتَهَا` | means of sustenance | possessive suffix hidden | sustenance/provisions + `هَا` | token_only_override -> suffix fixture | rich metadata + exact-address review |
| 16:77:1 | `كَلَمْحِ` | blink (of an eye) | component-only comparison/PP row | kāf/comparison + host + attachment | component_only -> blocker | PP/comparison review |
| 2:213:37 | `لِمَا` | to that which | lām + mā function/attachment | lām relation + classified mā | populated_uncertified -> needs_nahw_review | two-vote exact-address review |
| 86:4:4 | `لَّمَّا` | there is no ... except | lamma function collision | negative/exceptive construction by context | populated_uncertified -> needs_nahw_review | two-vote exact-address review |
| 9:114:21 | `لَأَوَّٰهٌ` | tender-hearted | component-only false lām/suffix risk | lexical host; no whole-token propagation | component_only -> blocker | exact POS/segment proof |
| 22:29:3 | `تَفَثَهُمْ` | grooming | possessive suffix hidden | grooming/rites + `هُمْ` | token_only_override -> suffix fixture | rich metadata + exact-address review |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` now records VN-09 finite
  verb dictionary leakage, lām-on-verb component blockers, and weak/hamzated
  review examples.
- `sarf/procedures/clitic-and-host-morphology.md` now records VN-09 suffix
  and component-only rows such as `يَعْصِمُكَ`, `يَجْتَبِيكَ`,
  `أَقْوَٰتَهَا`, `تَفَثَهُمْ`, `لِتُضَيِّقُوا۟`, and `وَفَدَيْنَٰهُ`.
- `sarf/procedures/nominal-derivative-decision.md` now records VN-09
  verb-entry nominal/POS leakage and entry-family collision examples.
- `sarf/drills/verb-measures.md` adds VN-09 finite-verb, suffix, and
  component-only drills.
- `sarf/evals/false-clitic-split-eval.jsonl` and
  `sarf/evals/nominal-derivative-error-eval.jsonl` add VN-09 fixtures.

Updated nahw:

- `nahw/procedures/ma-function-decision.md` now records the `لِمَا` and
  `لَّمَّا` split, and blocks one-entry-family propagation across function
  and lexical noun readings.
- `nahw/procedures/exception-and-vocative-review.md` now records `لَّمَّا`
  exception/negative construction review.
- `nahw/procedures/preposition-pronoun.md` and
  `nahw/procedures/pp-attachment-review.md` now record VN-09 component-only
  preposition/comparison/attachment rows and false raw-prefix guards.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-09 lām/mā, lām-on-verb,
  suffix, component-only, and renderer-only distinctions.
- `nahw/evals/particle-function-eval.jsonl`, `nahw/evals/irab-polysemy-eval.jsonl`,
  and `nahw/evals/suffix-pronoun-eval.jsonl` add VN-09 fixtures.

No-op reasons:

- Rows whose only defect is `missing_rich_renderer_segments` with whole-token
  evidence are renderer metadata backfill, not linguistic re-authoring.
- Repair-preview-ready remains `0`: this tranche did not run MCP/i'rab review,
  external source triangulation, two-vote adjudication, global grammar gates,
  owner approval, or apply planning.
- Component-only rows remain blockers even when they supply useful candidate
  evidence.

## Production-Bug Lessons

Committed sample:
`qamus/examples/dogfood_vn09_production_bug_lesson.sample.jsonl`

Rows:

- `quran:34:54:5` / `wbw:34:54:5` - finite verb dictionary leakage.
- `quran:5:67:16` / `wbw:5:67:16` - finite verb with `كَ` object suffix.
- `quran:12:6:2` / `wbw:12:6:2` - finite verb with `كَ` object suffix.
- `quran:65:6:9` / `wbw:65:6:9` - component-only lām + finite verb blocker.
- `quran:2:213:37` / `wbw:2:213:37` - `لِمَا` lām + mā function/attachment.
- `quran:86:4:4` / `wbw:86:4:4` - `لَّمَّا` function collision.
- `quran:41:10:10` / `wbw:41:10:10` - nominal suffix not visible.

## Renderer Requirements

VN-09 generated renderer requirements for:

- finite verbs with person/number/form and visible suffixes;
- lām-on-verb rows with function/mood review;
- `لِمَا` / `لَّمَّا` families with function-specific rows;
- preposition/comparison + host rows such as `كَلَمْحِ`;
- suffix-bearing nominal hosts such as `أَقْوَٰتَهَا` and `تَفَثَهُمْ`;
- renderer-only rows that need rich segments but not fresh sarf/nahw wording.

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
