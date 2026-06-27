# Full-Corpus Dogfood VN-10 - Tenth Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror
repo, service, rebuild, hover apply, or hover coverage/correctness claim was
changed.

Source batch: `out/standard-tranche-vn10-20260627/`

## Scope

- Verbs: `v453` through `v497`.
- Nouns: `n496` through `n545`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `319`, including `232` whole/resolved rows and `87` component-only evidence rows.
- Zero-row entries: `n501`, `n510`, `n511`, `n517`, `n534`, `n536`, `n544`.

This tranche advances dogfood review only. It does not create applyable hover
decisions.

## Controller Counts

| class | rows |
|---|---:|
| pending/blocker | 1 |
| populated_uncertified | 136 |
| token_only_override | 182 |

Routes:

- `blocker_queue_row`: `129`
- `renderer_requirement`: `8`
- `repair_candidate`: `182`

Repair-preview-ready rows: `0`.

## Review Packets

Bounded reviewer packets were generated:

- entry linkage review: `240` rows;
- learner explanation review: `240` rows;
- rich renderer review: `240` rows;
- nahw context review: `23` rows;
- noun sarf review: `43` rows;
- verb sarf review: `240` rows.

All reviewed rows keep `may_apply_live:false`.

## Dominant Findings

VN-10 surfaced six repeated classes:

- finite verbs such as `طَبَعَ`, `ٱسْتَعِينُوا۟`, `تَعَاوَنُوا۟`,
  `دَمَّرْنَا`, and `تَرْهَقُهُمْ` still inherit entry infinitive prose
  instead of exact finite form, subject, voice, and suffix contribution;
- component-only rows such as `فَأَعِينُونِى`, `وَأَعَانَهُۥ`,
  `فَدَمَّرْنَٰهُمْ`, `فَفِرُّوٓا۟`, and `وَمُقَصِّرِينَ` improve routing
  but remain below whole-token certification;
- lām/bāʾ rows such as `بِغَيْظِكُمْ`, `لِيَغِيظَ`, and `لِيُضِيعَ`
  require function, PP/attachment, suffix, or mood review before propagation;
- verb-entry nominal/POS leakage appears in `ٱلْمُسْتَعَانُ`,
  `ٱلْغَيْظِ`, `ٱلْمَفَرُّ`, `ٱلْوِرْدُ`, `ٱلْمُوقَدَةُ`, and
  `ٱلرِّعَآءُ`;
- suffix-bearing rows such as `وَارِدَهُمْ`, `وَقُودُهَا`, `رَٰعِنَا`,
  `رَعَوْهَا`, and `تَرْهَقُهُمْ` cannot hide attached pronoun or possessive
  contribution;
- renderer-only rows such as `حَثِيثًۭا`, `حَرْدٍ`, `حَرَسًۭا`,
  `حَنِيذٍۢ`, and `مُتَحَيِّزًا` need rich metadata but did not force a new
  sarf/nahw rule by themselves.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 16:108:3 | `طَبَعَ` | to seal one’s heart | finite verb dictionary leakage | finite perfect verb contribution | populated_uncertified -> needs_sarf_review | exact finite-form review |
| 12:18:15 | `ٱلْمُسْتَعَانُ` | to assist | verb-entry nominal/POS leakage | nominal/passive-participle-like role | token_only_override -> nominal POS review | derivative + referent review |
| 3:119:22 | `بِغَيْظِكُمْ` | to enrage | bāʾ + host + suffix hidden | bāʾ relation + host + `كُمْ` | component_only -> blocker | PP/suffix review |
| 48:29:42 | `لِيَغِيظَ` | to enrage | lām + finite verb component-only | lām function + finite host | component_only -> blocker | lām/mood review |
| 12:19:4 | `وَارِدَهُمْ` | to arrive at flowing water or the Fire | suffix hidden | host + `هُمْ` relation | token_only_override -> suffix fixture | exact-address review |
| 2:24:9 | `وَقُودُهَا` | fuel for a kindled fire | suffix hidden on nominal host | fuel + `هَا` relation | populated_uncertified -> suffix review | exact-address review |
| 25:36:8 | `فَدَمَّرْنَٰهُمْ` | to destroy | component-only finite verb + object | `فَ` + finite host + `هُمْ` | component_only -> blocker | whole-token proof |
| 2:104:6 | `رَٰعِنَا` | to tend to, care for, live up to | finite/context plus suffix risk | exact host + `نَا`/address-context review | token_only_override -> suffix/context fixture | two-vote if wording changes |
| 10:27:7 | `وَتَرْهَقُهُمْ` | to cover, overwhelm, burden or pressure | wāw + finite verb + object | wāw + finite host + `هُمْ` | component_only -> blocker | whole-token proof |
| 7:54:19 | `حَثِيثًۭا` | rapidly | renderer-only metadata miss | adverbial/nominal role metadata | token_only_override -> needs_renderer_segments | metadata backfill |
| 5:2:43 | `تَعَاوَنُوا۟` | to assist | finite Form VI/plural contribution | finite plural mutual/cooperative action | token_only_override -> finite form review | exact-address review |
| 104:6:3 | `ٱلْمُوقَدَةُ` | kindled | nominal/passive participle row | definite passive-participle/adjectival role | token_only_override -> nominal derivative review | derivative/POS gate |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` now records VN-10 finite
  verb dictionary leakage and lām-on-verb component blockers.
- `sarf/procedures/clitic-and-host-morphology.md` now records VN-10 suffix and
  component-only rows such as `وَارِدَهُمْ`, `وَقُودُهَا`,
  `فَدَمَّرْنَٰهُمْ`, `رَٰعِنَا`, and `تَرْهَقُهُمْ`.
- `sarf/procedures/nominal-derivative-decision.md` now records VN-10
  verb-entry nominal/POS leakage examples.
- `sarf/drills/verb-measures.md` adds VN-10 finite-form, suffix, and
  component-only prompts.
- `sarf/evals/false-clitic-split-eval.jsonl` and
  `sarf/evals/nominal-derivative-error-eval.jsonl` add VN-10 fixtures.

Updated nahw:

- `nahw/procedures/preposition-pronoun.md` and
  `nahw/procedures/pp-attachment-review.md` now record VN-10 bāʾ/lām rows and
  false whole-token propagation guards.
- `nahw/drills/grammar-routing-hard-cases.md` adds VN-10 lām/bāʾ, suffix,
  nominal/POS, component-only, and renderer-only distinctions.
- `nahw/evals/particle-function-eval.jsonl`, `nahw/evals/irab-polysemy-eval.jsonl`,
  and `nahw/evals/suffix-pronoun-eval.jsonl` add VN-10 fixtures.

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
`qamus/examples/dogfood_vn10_production_bug_lesson.sample.jsonl`

Rows:

- `quran:16:108:3` / `wbw:16:108:3` - finite verb dictionary leakage.
- `quran:12:18:15` / `wbw:12:18:15` - verb-entry nominal/POS leakage.
- `quran:48:29:42` / `wbw:48:29:42` - component-only lām + finite verb blocker.
- `quran:3:119:22` / `wbw:3:119:22` - bāʾ + host + suffix hidden.
- `quran:12:19:4` / `wbw:12:19:4` - attached suffix not visible.
- `quran:25:36:8` / `wbw:25:36:8` - component-only finite verb + object suffix.
- `quran:7:54:19` / `wbw:7:54:19` - renderer metadata only.

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
