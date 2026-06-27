# Full-Corpus Dogfood Batch - Particle-First Tranche - 2026-06-27

Status: read-only dogfood processing. No live Qamus mutation, WBW rebuild,
service restart, mirror sync, hover apply, or coverage claim was made.

## Scope

This tranche audits the 33 highest-frequency / highest-functional-impact Qamus
particle entries from the 100 particle-entry section against the current
full-corpus dogfood snapshot:

`out/full-corpus-dogfood-82c63dd-20260627-004825/full-corpus-hover-dogfood-audit.jsonl`

The tranche uses live-derived dogfood rows as evidence, but it does not treat
live hover population as dogfooding completion.

## Counts

- Particle entries selected: 33.
- Whole-token instances linked to those entries: 9,965.
- Component-only evidence rows: 14.
- Whole-token class counts:
  - `populated_uncertified`: 9,893.
  - `token_only_override`: 70.
  - `known_defect`: 1.
  - `pending/blocker`: 1.
- Component-only candidates stayed separate from whole-token entry resolution.

## Selected Entries

| rank | entry id | form | matrix resolved/pending | dogfood whole-token class summary |
|---:|---|---|---:|---|
| 1 | `5c405be976bd` | `مِنْ` | 138 / 5 | 2,086 populated_uncertified; 5 token_only_override |
| 2 | `896fc440f451` | `هُنَّ` | 142 / 1 | 6 populated_uncertified |
| 3 | `b8e480aebafe` | `مَا` | 132 / 10 | 671 populated_uncertified |
| 4 | `1f50dcf7931c` | `إِلَى` | 134 / 6 | 278 populated_uncertified; 1 token_only_override |
| 5 | `ca5dd7eb89ec` | `ذَٰلِكَ` | 119 / 9 | 251 populated_uncertified; 3 token_only_override |
| 6 | `a1feead9300b` | `فِي` | 119 / 6 | 1,021 populated_uncertified; 4 token_only_override |
| 7 | `d04ce63e31af` | `يَا` | 109 / 3 | 1 known_defect; 107 populated_uncertified; 1 token_only_override |
| 8 | `4318e2561011` | `أَنَّ` | 91 / 9 | 582 populated_uncertified; 4 token_only_override |
| 9 | `12ed817accf5` | `أَيّ` | 93 / 7 | 12 populated_uncertified; 8 token_only_override |
| 10 | `632fbb107c44` | `أَنْ` | 78 / 7 | 417 populated_uncertified |
| 11 | `afe866d4f423` | `لَمْ` | 81 / 4 | 115 populated_uncertified |
| 12 | `b10a1ee04666` | `لَـ / لِـ` | 77 / 7 | 813 populated_uncertified; 7 token_only_override |
| 13 | `b00eef6e0665` | `تِلْكَ` | 77 / 5 | 12 populated_uncertified; 4 token_only_override |
| 14 | `2fcbd8198aa6` | `بِـ` | 74 / 5 | 1 component-only known_defect |
| 15 | `08b05deced53` | `إِنَّ` | 70 / 6 | 980 populated_uncertified; 7 token_only_override |
| 16 | `1ab446228cab` | `كَمْ` | 75 / 1 | 3 populated_uncertified; 1 token_only_override |
| 17 | `cee928fb679c` | `لَوْ` | 69 / 6 | 75 populated_uncertified; 2 token_only_override |
| 18 | `5935ecfb1ec5` | `الْ` | 72 / 2 | 6 component-only known_defect |
| 19 | `fd8d287473fa` | `أَوْ` | 68 / 5 | 201 populated_uncertified; 1 token_only_override |
| 20 | `7bb317131add` | `لَعَلَّ` | 73 / 0 | 65 populated_uncertified; 5 token_only_override |
| 21 | `557361a66a43` | `الَّذِي` | 63 / 6 | 158 populated_uncertified; 1 token_only_override |
| 22 | `7f25d6c3e392` | `هُمَا` | 66 / 3 | 1 token_only_override |
| 23 | `157442d7e625` | `عَنْ` | 59 / 8 | 267 populated_uncertified; 2 token_only_override |
| 24 | `790e8c848efc` | `كَأَنَّ` | 60 / 4 | 21 populated_uncertified; 5 token_only_override |
| 25 | `e042319a89e3` | `إِلَّا` | 57 / 4 | 381 populated_uncertified |
| 26 | `dbbc876bd82f` | `ذَا` | 48 / 2 | 11 populated_uncertified |
| 27 | `b7570549e851` | `عَلَى` | 45 / 4 | 628 populated_uncertified; 1 pending/blocker; 5 token_only_override |
| 28 | `3c0edd60b334` | `لَمَّا` | 46 / 3 | 42 populated_uncertified |
| 29 | `19de33871698` | `لَا` | 46 / 2 | 593 populated_uncertified; 1 token_only_override |
| 30 | `a23a0c853dd8` | `وَ` | 46 / 2 | 6 component-only known_defect |
| 31 | `7f1f8b8e29e6` | `إِذْ` | 41 / 1 | 93 populated_uncertified; 2 token_only_override |
| 32 | `32dbdef93c77` | `إِيَّاهُمْ` | 39 / 3 | 0 whole-token rows in this snapshot |
| 33 | `d768c574ae8f` | `عَسَى` | 38 / 4 | 4 populated_uncertified |

## Function-Aware Findings

1. `مَا`, `وَمَا`, and `فَمَا` are not one-gloss particles. Existing
   `ما` rules cover the grammar, but the dogfood queue needs exact packet
   mapping to the fired rung or `ma_function_uncertain`.
2. Clear kasra `مِن` rows were being swept into broad `ma/man` uncertainty.
   They should split to preposition/PP review, while fatḥa `مَنْ` remains in
   relative/interrogative/conditional review.
3. `لَا`, `لَمْ`, and `لَنْ` hovers are often readable but uncertified because
   the governed word and mood/case are not recorded.
4. `إِنْ`, `إِنَّ`, `أَنْ`, `أَنَّ`, and `أَلَّا` need seat/shadda plus clause
   role before rich certification.
5. `ثُمَّ`, `هَلْ`, `إِلَّا`, and `إِذْ` / `إِذَا` exposed target-specific
   particle gaps, so this tranche added drill/eval/procedure coverage.
6. Component candidates (`وَ`, `بِـ`, `ال`) are useful renderer/learner evidence
   but not whole-token entry resolution.
7. The preposition/oath packet exposed detector overreach for lexical initial
   bā/lām/fā/kāf. Sarf now requires positive segmentation evidence before
   routing to clitic review.

## State Movement

- `populated_uncertified -> needs_nahw_review + skill_impact_mapping`:
  high-frequency particles whose visible strings need function/scope/case/mood
  certification.
- `component_candidate_only -> renderer_requirement + no_propagation`: 14 rows
  where a particle entry appears as a component of a richer written token.
- `detector_overreach -> sarf_guard + regression_fixture`: lexical initial
  bā/lām/fā examples now have false-clitic regression guards.
- `known_defect -> production_bug_lesson + regression_fixture`: repeated
  particle defects for false clitic routing, sequence scope, question frame, and
  exception structure.

No row became `repair_preview_ready` in this tranche.

## Skill Impact

Updated sarf:

- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/evals/false-clitic-split-eval.jsonl`

Updated nahw:

- `nahw/procedures/particle-decision.md`
- `nahw/procedures/particle-function-decision.md`
- `nahw/procedures/exception-and-vocative-review.md`
- `nahw/procedures/conditionals.md`
- `nahw/drills/particle-disambiguation.md`
- `nahw/drills/particles.md`
- `nahw/evals/particle-function-eval.jsonl`

No-op examples:

- `مَا`, `لَا`, `لَمْ`, `لَنْ`, `إِنْ`, `أَنْ`, and related particles already had
  core procedures/evals. Their tranche impact is explicit next-gate routing, not
  duplicate doctrine.
- `أَوْ` already has core disjunction coverage; current rows remain
  string-populated until scope/renderer metadata exists.

## New Artifacts

- `qamus/examples/full_corpus_dogfood_particle_tranche_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_particle_tranche_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_particle_tranche_production_bug_lesson.sample.jsonl`
- Generated full inventory, not committed because `out/` is ignored by policy:
  - `out/particle-dogfood-tranche-20260627/particle-instance-inventory.jsonl`
  - `out/particle-dogfood-tranche-20260627/particle-component-only-inventory.jsonl`
  - `out/particle-dogfood-tranche-20260627/particle-tranche-summary.json`

## Public Boundary

All rows are internal dogfood/skill artifacts. They do not authorize public
hover application and do not expose MCP, QAC, Quran.com, OCR, or source-photo
provenance as public hover payload.

## Next Gates

- Build exact-address review packets by particle function cluster.
- Record function, scope, governed word, case/mood, and renderer segment needs.
- Produce repair-preview packets only after two-vote or human-review gates pass.
- Keep every live apply owner-gated with backup, append-only ledger, rebuild,
  validation, health check, public readback, no-leak scan, and rollback path.
