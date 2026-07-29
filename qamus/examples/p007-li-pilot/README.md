# P007_LI_NOUN_HOST_PILOT — vertical-slice closure with entry transclusion

Durable repository machinery for the first complete source-grounded P-00
vertical slice: the jarr clitic **لِـ** (source key `p007`, entry
`b10a1ee04666`, sense 2 `لِـ`) attached to **noun hosts** — **12 canonical
occurrences / 78 entry-page appearances / 49 typed facts**, taken end-to-end:
discovery → candidate lattice → verbatim MCP evidence → independent two-vote
review → fact-level certification (hash-chained store) → two-surface
projection with exact letter ownership → cross-page parity proof → live
reverse-check deltas → VN unlock measurement.

**Scope name everywhere: `P007_LI_NOUN_HOST_PILOT`.** The 12 occurrences are
the pilot population, NOT p007 accounted (p007 has 2,999 matrix rows; the
certified template's pattern ceiling is 580 rows / 1,266 appearances — ceiling
only, per-row evidence stays mandatory).

**NOT DEPLOYED.** Candidate mode throughout: nothing here mutates any live
surface. The production-difference table is the owner-gated candidate upgrade
set.

## Primary artifacts (lane evidence, committed verbatim)

| File | What it is |
|---|---|
| `family-selection.json` | family predicate, selection criteria, the 12 occurrences with appearance links |
| `candidate-lattice.jsonl` | pre-selection dependency lattice, 15 rows (12 in-family + 3 rejected rivals) |
| `mcp-evidence.jsonl` | verbatim Tafsir MCP records (warm-up, 12+3 `analyze_word` surface-matched, `fetch_ayah`) |
| `votes-a.jsonl` / `votes-b.jsonl` | the two independent vote lanes (reviewer-B: sanitized worklist + own MCP calls only) |
| `votes-b-mcp-calls.jsonl` | reviewer-B's independent MCP evidence (24 records) |
| `reviewer-b-worklist.json` | the sanitized, rival-symmetric controlled-vocabulary worklist |
| `two-vote-artifacts.v1.jsonl` | the 12 `qamus.two_vote_artifact.v1` bundles consumed by the certifier (12/12 `two_vote_verified`) |
| `two-vote-diff-report.json` | agreement diff report (empty — no disagreements) |
| `typed-facts.jsonl` | the 49-row typed-fact table with per-fact evidence policy |
| `certification/events.jsonl` | append-only hash-chained certification store (147 events; validate with `tools/certify_typed_fact.py --validate`) |
| `projections.jsonl` | 12 canonical two-surface projections + 78 appearance hashes |
| `parity-report.json` | cross-page parity proof + read-only live deltas |
| `reverse-trace.json` | projection → facts → events → two-vote → votes → MCP → matrix → live row |
| `live-rows.jsonl` | read-only capture of the 12 live rich-whitelist rows |
| `vn-unlock.json` | VN tranche unlock measurement (direct 78; pattern ceiling 1,266). Tranche keys use the `VNPROP-xx` proposal namespace (the universe's balanced-partition labels, renamed from bare `VN-xx` per the 2026-07-29 owner ruling): they are NOT contract window ids — VN-UNLOCK-PROOF-2026-07-29 Finding 0 proved the former proposal "VN-03" (v196–v296) shares no page with the contract VN-03 worklist window (v142–v188 + n0136–n0180) |

## Derived artifacts (regenerate with `python tools/build_p007_li_pilot.py`)

| File | What it is |
|---|---|
| `locations.json` | the 12-location table: canonical locs, surfaces, morpheme spans (base-letter + char), 78 appearance links, lattice pre-selection, the 3 rejected false candidates **with defeaters** (لِبَاسٌ lexical lām · لِيَغِيظَ lām-taʿlīl · لِى pronoun host), and the exact exceptions (NFC shadda/vowel order, fused wasla elision, diptote fatha sign, same-surface distinct artifacts, fronted-predicate governor representation) |
| `morpheme-occurrences.jsonl` | 12 `qamus.particle_morpheme_occurrence.v1` identity nodes with base-letter spans |
| `transclusion-edges.jsonl` | the entry-transclusion closure: per occurrence the explicit **entry edge** (`particle_entry_certified_edge` → `entry:b10a1ee04666`, i.e. morpheme_occurrence_instantiates_particle_entry) + **sense edge** (`particle_sense_certified_edge` → `sense:b10a1ee04666:2`, i.e. morpheme_occurrence_instantiates_particle_sense) + `clitic_host_edge` + `governor_edge` + `governed_expression_edge` (+ the entry reverse occurrence edge). A generic 'preposition' class without the entry/sense edge does NOT satisfy transclusion. |
| `entry-reverse-index.json` | p007 → its 12 certified occurrences → 78 appearances grouped by page class (n:22 / v:54 / p:2) |
| `two-vote-artifacts.v1_1.jsonl` | the v1 bundles migrated to `qamus.two_vote_artifact.v1.1` (governed enums + registry keys; substance untouched) |
| `migration-provenance.json` | every representational mapping of the v1→v1.1 migration, recorded |
| `production-difference.json` | NOT-DEPLOYED §5 table: occurrence · current public carve · candidate carve · colour classes · verdict (wrong / incomplete / legacy-coarse) · affected pages · required change · rollback unit — the 2 live carve forks (2:187:63, 4:11:5) + 12 colour-class deltas |

## Gate

`tools/validate_p007_pilot.py` (red-first, `--self-test`) — wired into
`tools/check_regressions.py` (P007PILOT block). Gates: 12-location integrity,
49-fact completeness against the hash-chained store, entry/sense edge presence
on every certified morpheme occurrence, parity hash stability (NFC lesson),
reverse-trace closure, production-difference honesty.

Registry keys added by this pilot (in `qamus/skills/reason-key-registry.jsonl`):
`jarr-clitic-li-majrur-visible-kasra`, `jarr-clitic-li-majrur-fatha-diptote`.

Provenance: dawahwiki packet `P00-VERTICAL-SLICE-2026-07-29` (lane-local
artifacts migrated into the repository unchanged; the certification store
consumed the v1 two-vote bundles).
