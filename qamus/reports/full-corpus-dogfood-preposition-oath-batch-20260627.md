# Full-Corpus Dogfood Batch - Preposition/Oath Host Defects - 2026-06-27

Status: read-only dogfood processing. No live Qamus mutation, WBW rebuild,
service restart, mirror sync, hover apply, or coverage claim was made.

## Scope

This batch processes a bounded high-yield packet from the populated-hover
dogfood queue: attached bā' / PP host hovers, oath-wāw host hovers, and
preposition + possessed-host rows that were populated or pending but not
skill-certified.

## Controller Table

| loc | surface | current gloss | defect class | expected contribution | why not repair-ready | next gate | lesson id | target |
|---|---|---|---|---|---|---|---|---|
| 95:1:5 | `وَٱلتِّينِ` | `fig` | oath_waw_host_only | by the fig | oath function needs exact-address certification | exact_address_two_vote | oath_waw_host_only | IP-028 / bug lesson |
| 95:1:6 | `وَٱلزَّيْتُونِ` | `olives` | oath_waw_host_only | and by the olive | coordination + oath frame must be verified | exact_address_two_vote | oath_waw_host_only | IP-029 / bug lesson |
| 95:2:1 | `وَطُورِ` | `and (the) Mount` | oath_waw_host_only | and by Mount | host text is readable but qasam function is not proven | nahw_two_vote | oath_waw_host_only | PF-045 / FCS-037 |
| 95:3:1 | `وَهَٰذَا` | `and this` | oath_waw_demonstrative_function_missing | and by this / and this | particle function decides the hover | nahw_two_vote | oath_waw_demonstrative_function_missing | PF-046 / IP-044 |
| 16:16:2 | `وَبِالنَّجْمِ` | null | waw_ba_host_pending | and by/through the star(s) | already gated; needs source triangulation + two-vote | source_triangulation_then_two_vote | covered_existing_fixture | IP-030 |
| 2:3:3 | `بِٱلْغَيْبِ` | the unseen | ba_article_host_only | in/by the unseen | PP relation must be certified | nahw_two_vote | ba_host_only | preposition procedure |
| 2:102:21 | `بِبَابِلَ` | Babylon | ba_place_host_only | in Babylon | place host lacks locative bā' proof | exact_address_two_vote | ba_place_host_only | FCS-039 / PF-047 |
| 2:87:15 | `بِرُوحِ` | spirit | ba_referent_host_only | with/by the Spirit | referent and relation are human-review gated | human_review_required | ba_referent_host_only | FCS-036 / IP-041 |
| 3:11:11 | `بِذُنُوبِهِمْ` | Sin. | ba_possessed_host_suffix_omitted | because of/for their sins | bā' relation + possessor need two-vote | exact_address_two_vote | ba_possessed_host_suffix_omitted | FCS-034 / PF-043 |
| 5:18:11 | `بِذُنُوبِكُم` | null | ba_possessed_host_suffix_pending | because of/for your sins | pending row needs source triangulation + two-vote | source_triangulation_then_two_vote | ba_possessed_host_suffix_omitted | FCS-035 / IP-042 |

## State Movement

- `known_defect -> production_bug_lesson + regression_fixture`: 5 rows.
- `populated_uncertified -> needs_nahw_review + regression_fixture`: 3 rows.
- `pending/blocker -> exact_next_gate`: 2 rows.
- `known_defect -> human_review_required + production_bug_lesson`: 1 row.
- `repair_preview_ready`: 0 rows. No row is unblocked enough for apply preview
  without the stated gate.

## Skill Impact

Updated sarf:

- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/drills/clitic-and-host-morphology.md`
- `sarf/evals/false-clitic-split-eval.jsonl`

Updated nahw:

- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/idafa-jar-majrur.md`
- `nahw/drills/grammar-routing-hard-cases.md`
- `nahw/evals/particle-function-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`

Updated curriculum:

- `curriculum/drills/hover-composition-and-routing.md`

No-op reason:

- `وَبِالنَّجْمِ` already had sarf/nahw fixture coverage (`IP-030` and the
  clitic drill). It remains in the closure blocker lane; no duplicate skill
  rule was added for that row.

## New Artifacts

- `qamus/examples/full_corpus_dogfood_preposition_oath_batch_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_preposition_oath_production_bug_lesson.sample.jsonl`

## Public Boundary

All rows are internal dogfood/skill artifacts. They do not authorize public
hover application and do not expose MCP, QAC, Quran.com, OCR, or source-photo
provenance as public hover payload.

## Next Gates

- Source-triangulate exact token addresses.
- Run two-vote or human review where specified.
- Build repair-preview packets only for rows that pass the gate.
- Keep every live apply owner-gated with backup, append-only ledger, rebuild,
  validation, health check, public readback, no-leak scan, and rollback path.
