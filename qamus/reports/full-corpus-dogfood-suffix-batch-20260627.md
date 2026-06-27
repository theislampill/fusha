# Full-Corpus Hover Dogfood Batch - Suffix Pronouns - 2026-06-27

Status: repo-only dogfood output. No live Qamus mutation, WBW rebuild, service
restart, mirror sync, hover apply, or coverage claim happened.

Source evidence:

- `out/full-corpus-dogfood-82c63dd-20260627-004825/`
- controller reconciliation and next-state queues from the Phase 2 dogfood run
- read-only suffix omission scan:
  `qamus/reports/closure-2092/verb-suffix-omission-scan-20260625.md`

## Controller Table

| loc | surface | current gloss | defect class | expected token contribution | why not repair-ready | next gate | lesson id | target |
|---|---|---|---|---|---|---|---|---|
| `2:191:3` | `ثَقِفْتُمُوهُمْ` | to find/come upon in battle | verb object suffix omitted | you all found/came upon them in battle | exact-address two-vote still needed; no live apply authorized | exact-address two-vote | `lesson:2:191:3` | suffix eval + clitic drill |
| `2:220:12` | `تُخَالِطُوهُمْ` | partners | finite verb dictionary-gloss leakage | you mix/associate with them | entry-family text conflicts with finite verb; needs two-vote repair path | exact-address two-vote | `lesson:2:220:12` | `FCS-030`, `SP-020` |
| `2:220:22` | `لَأَعْنَتَكُمْ` | to make difficult; hardship | suffix omitted with mood/force review | He would have made things difficult for you | lām/force and object wording need nahw review | nahw two-vote | `lesson:2:220:22` | nahw routing drill |
| `2:231:12` | `تُمْسِكُوهُنَّ` | to hold/keep | verb object suffix omitted | you hold/keep them (fem. pl.) | exact-address two-vote still needed | exact-address two-vote | `lesson:2:231:12` | `FCS-031`, `SP-021` |
| `2:231:9` | `سَرِّحُوهُنَّ` | to release | verb object suffix omitted | release them (fem. pl.) | imperative/context review needed | exact-address two-vote | `lesson:2:231:9` | suffix drill |
| `2:237:6` | `تَمَسُّوهُنَّ` | to touch | verb object suffix omitted | you touch them (fem. pl.) | exact-address two-vote still needed | exact-address two-vote | `lesson:2:237:6` | suffix drill |
| `2:282:107` | `تَكْتُبُوهَا` | to write | verb object suffix omitted | you write it/her | `ها` referent must be certified | referent two-vote | `lesson:2:282:107` | `FCS-033`, `SP-022` |
| `2:189:23` | `أَبْوَٰبِهَا` | door, gate | noun possessive suffix hidden | its doors/gates | base gloss and referent review before apply | suffix base certification | `lesson:2:189:23` | `FCS-032`, `SP-023` |
| `2:200:4` | `آبَاءَكُمْ` | fathers | noun possessive suffix hidden | your fathers/forefathers | base gloss certification; no live apply authorized | suffix base certification | `lesson:2:200:4` | suffix-pronoun procedure |
| `2:223:1` | `نِسَآؤُكُمْ` | women/wives | noun possessive suffix hidden | your women/wives | base gloss and context certification | suffix base certification | `lesson:2:223:1` | suffix-pronoun procedure |

## State Transitions

- `token_only_override -> drill_regression_fixture`: 7 verb-object rows.
- `token_only_override -> needs_nahw_review`: 2 rows with lām/force or referent review.
- `populated_uncertified -> suffix_positive_control`: 3 noun-host rows.
- `known_defect_candidate -> skill_impact`: 1 finite-verb dictionary leakage row.
- `repair_preview_ready`: 0 rows.

No row became live-apply ready. The batch moves rows into skill-impact,
regression, drill, and exact next-gate queues only.

## Skill Impact

Committed skill-impact rows:
`qamus/examples/full_corpus_dogfood_suffix_batch_skill_impact.sample.jsonl`

Sarf updates:

- `sarf/procedures/verb-form-and-mood-review.md`: populated finite verbs are
  not complete if they drop subject/object suffixes.
- `sarf/procedures/suffix-pronoun-state.md`: noun-host possessives are positive
  controls and must not cover verb-host suffixes.
- `sarf/drills/clitic-and-host-morphology.md`: added verb-object and noun-host
  suffix examples.
- `sarf/evals/false-clitic-split-eval.jsonl`: rows `FCS-030` to `FCS-033`.

Nahw updates:

- `nahw/procedures/pronoun-attachment.md`: added the populated-hover object
  omission dogfood rule.
- `nahw/drills/grammar-routing-hard-cases.md`: added object-suffix and
  lām/force review examples.
- `nahw/evals/suffix-pronoun-eval.jsonl`: rows `SP-019` to `SP-023`.

No-op reasons:

- Noun-host rows (`أَبْوَٰبِهَا`, `آبَاءَكُمْ`, `نِسَآؤُكُمْ`) did not add a
  new nahw rule beyond `pronoun-attachment.md`; they are sarf/eval positive
  controls plus Qamus data/renderer repair candidates.
- No live repair preview is emitted because every row still needs exact-address
  review or base/referent certification.

## Renderer And Repair Requirements

Every row that later becomes rich-rendered must keep the Arabic token intact
while exposing:

- verb stem, subject/person marker, and object suffix for verb-host rows;
- noun host and possessive suffix for noun-host rows;
- `parse_key.key`, display classes, and learner-facing breakdown;
- public payload boundary `src=qamus`, `kind=authored`, `lang=en`.

This report does not authorize changing live Qamus. Any future repair must be a
separate owner-gated plan with backup, append-only ledger, rebuild, validation,
health check, public readback, and rollback path.
