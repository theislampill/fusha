# Meta-transclusive projection — the engineering pipeline in 15 stages

Status: adopted 2026-07-29 (canonical architecture doc, precedence tier 4).
This doc is the engineering explanation of how one Qurʾānic occurrence goes
from raw discovery to a certified fact projected identically onto every page
that shows it. The 15-stage framing comes from the 2026-07-29 handoff steer
(precedence tier 3); every stage below is grounded in a real, committed tool.
The two-layer model it refines is `docs/parser/TRANSCLUSION.md` /
`docs/parser/meta-transclusive-lattice-projection.md` (source-address
transclusion + meta-transclusive lattice projection; loc-first reuse; family
summaries are never closure packets).

The end-to-end evidence that all 15 stages compose is the committed pilot
`qamus/examples/p007-li-pilot/` (12 occurrences → 49 facts → 12 projections →
78 appearances, zero hash forks).

## 1. The 15 stages

| # | Stage | Real tooling / artifact |
|---|---|---|
| 1 | **Family selection & discovery** — define the family predicate, enumerate candidate occurrences over the canonical example-āyah universe | `family-selection.json` (pilot); `tools/build_example_ayah_universe.py`; discovery classifier output is *candidate links*, never "occurrences" |
| 2 | **Candidate dependency lattice** — per occurrence, the rival analyses with guards and defeaters; rejected rivals stay in the lattice as regression guards | `candidate-lattice.jsonl` (12 in-family + 3 rejected rivals with defeaters); `qamus.particle_function_lattice.v1` in `qamus/schemas/particle-edge-ontology.schema.json` |
| 3 | **Verbatim MCP evidence capture** — warm-up, surface-matched `analyze_word`/`fetch_ayah`, every call recorded verbatim in the evidence plane | `mcp-evidence.jsonl`; discipline in `docs/architecture/evidence-and-certification.md` §2 |
| 4 | **Triangulation** — corroborate across independent sources; results stay private-side, only the authored conclusion goes public | `tools/build_pending_source_triangulation_table.py`, `tools/build_source_triangulated_votes.py`, `tools/validate_rh_live_source_triangulation_readiness.py` |
| 5 | **Independent two-vote review** — reviewer-B works from a sanitized, rival-symmetric worklist and its own MCP calls; agreement computed on conclusion + reason key | `votes-a.jsonl` / `votes-b.jsonl` / `votes-b-mcp-calls.jsonl` / `reviewer-b-worklist.json`; `tools/validate_two_vote_artifacts.py` (`qamus.two_vote_artifact.v1.1`) |
| 6 | **Agreement diff & reclassification** — disagreements surface as convention vs substance; unbacked historical claims become `two_vote_claimed_unverified`, never fabricated | `two-vote-diff-report.json`; `docs/certification-authority.md` §4 |
| 7 | **Typed-fact table** — the occurrence decomposes into per-fact rows (`clitic_host_segmentation`, `contextual_function`, `governor_relation`, `case_mood_governor`, `particle_rootlessness`, …), each with its own evidence mode, guards, defeaters, dependencies | `typed-facts.jsonl` (49 rows); `qamus/schemas/typed-claim-contract.schema.json`; `tools/typed_claim_contract.py` |
| 8 | **Fact-level certification** — the certifier transitions `candidate → review_required → certified` (or `blocked`/`rejected`) per fact against the evidence ladder; append-only hash-chained event trail; it re-opens the current two-vote bundle and refuses a value/reason/occurrence/surface mismatch | `tools/certify_typed_fact.py` (`--validate`, `--self-test`, `--demo-sufaha`); `tools/migrate_p007_claim_binding.py`; `certification/events.jsonl` (303 events: 147 historical + 156 append-only migration, including 12 dependency rebinds) |
| 9 | **Revocation & dependency indexing** — reverse dependency index so a de-certified input cascades; defeater fires → `blocked`; no silent downgrade | `tools/certify_typed_fact.py` revocation cascades; `docs/certification-authority.md` §5; `tools/reconcile_certification_stores.py` (typed-claim plane canonical, token ledger frozen) |
| 10 | **Typed-edge construction** — certified facts become graph edges (entry, sense, host, governor, governed, reverse) in the one shared graph | `transclusion-edges.jsonl`; `tools/build_typed_edge_crosswalk.py`; `docs/architecture/transclusion-graph.md` |
| 11 | **Two-surface projection** — one canonical typed-fact artifact per occurrence compiles to the rich-at-rest surface and the rich-hover surface; neither may carry a fact the artifact does not carry | `projections.jsonl`; `tools/fd_compiler.py` (+ `tools/fd2_rerun.py`); `tools/lattice_projectors.py` (registry-driven, read-only, candidate-only); `docs/qamus/particle-projection-contract.md` |
| 12 | **Parity validation** — every appearance of one occurrence carries the same projection hash (sha256 over the canonical serialization), modulo the closed 4-key presentation whitelist | `tools/validate_particle_projection_parity.py` (executable twin of the contract); `tools/validate_appearance_parity.py`; `parity-report.json` |
| 13 | **Appearance & reverse indexing** — occurrence → its appearances by page class; entry → its certified occurrences; reciprocity both ways | `entry-reverse-index.json`; `tools/build_occurrence_appearance_index.py`; `tools/build_full_source_address_graph.py` |
| 14 | **Website payload projection** — per appearance, one `qamus.website_projection_payload.v1` file for the separate website agent; validator is the schema of record | `tools/validate_website_payload.py`; `qamus/examples/website-payloads/`; `docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md` |
| 15 | **Readback, dogfood and gating** — read-only live deltas (never mutation), production-difference honesty, VN-unlock measurement, lessons back into rules/fixtures, all wired into the regression harness | `live-rows.jsonl`, `production-difference.json`, `vn-unlock.json`, `reverse-trace.json`; `tools/validate_p007_pilot.py` in `tools/check_regressions.py`; `docs/architecture/dogfood-flywheel.md` |

The reverse trace closes the loop: projection → facts → certification events
→ two-vote artifact → votes → MCP evidence → matrix row → live row
(`reverse-trace.json`, one chain per projection).

## 2. Canonical flow diagram

```
                     [1 family selection]
                              |
                     [2 candidate lattice] --(rejected rivals kept as defeaters)
                              |
        [3 MCP evidence] --- [4 triangulation]        (evidence plane, private-side)
                              |
                  [5 two-vote independent review]
                              |
                     [6 agreement diff]
                              |
                     [7 typed-fact table]             (facts, not words)
                              |
     [9 revocation index] <- [8 fact-level certification]   (hash-chained events)
                              |
                    [10 typed-edge graph]             (one graph, 31 edge types)
                              |
                  [11 two-surface projection]         (ONE artifact -> two surfaces)
                              |
                    [12 parity validation]            (same hash on every page)
                              |
              [13 appearance + reverse indexes]
                              |
                   [14 website payloads]              (website agent renders; never authors)
                              |
             [15 readback / dogfood / regression gate]
                              |
                 lessons -> rules/fixtures -> stage 1
```

## 3. Reuse safety: the five distinctions

The handoff steer distinguishes five reuse postures. Three of the five names
are steer-level concepts, not repo enums — the table gives the **greppable
repo encoding** for each, which is what validators actually enforce.

| Steer concept | Meaning | Repo encoding |
|---|---|---|
| **Exact-occurrence** | a fact certified at `quran:S:A:W` applies exactly there | gate E `exact_occurrence` in `tools/validate_segment_completeness.py` ("an exact source-addressed record may not fall back to generic"); token-level certification "does not authorize reuse elsewhere" (`docs/certification-policy.md` §0) |
| **Entry-level** | reuse licensed by the entry store itself (headword / documented forms) | tier-0/tier-A of the root-inheritance ladder in `qamus/lattice/registered-projectors.json` (`sarf.root_inherit_transclusion.v1`): qamus entry headword / `usage.forms` match, then self-join via carrier `entry_id` |
| **Family-reuse** | reuse across a certified family (same surface, same stem, same pattern family) under fanout gates | tiers B/C of the same ladder (certified same-surface / same-stem sibling); certified-lemma fanout gates `source_address_exact` / `lemma_pattern_pos` / `function_context` (`docs/certification-policy.md` §1) |
| **Guarded-analogous** | projection to analogous occurrences allowed only through registered projectors with named guards, routed to review | `gate_tier` enum in `qamus/schemas/projector-record.schema.json`: `auto_safe` / `two_vote_required` / `human_source_review_required` / `never_auto_resolve`; named guards in `tools/lattice_projectors.py` (`homograph_surface_ambiguity`, `surface_byte_exact`, `construction_match`, `divine_name_exclusion`, …) — "a guard violation BLOCKS; a homograph surface ROUTES to 2-vote (never auto-projects)". Nothing currently registered is `auto_safe`. |
| **Unsafe-surface-similarity** | letters look alike, so reuse the analysis — **forbidden** | the standing prohibition: "surface match NEVER authorizes reuse" (location-first doctrine); DR-2 "pattern alone NEVER certifies" (`qamus/reports/ROOT-INHERITANCE-JOIN.md`); "coverage is not disambiguation" (`docs/parser/largelexicon-collision-safety.md`); rejected rivals in stage 2 (e.g. لِبَاسٌ lexical lām vs لِـ clitic) are its regression guards |

Same-occurrence transclusion and guarded analogous projection are **distinct
operations**: the first moves a solved fact to another page, the second
proposes a *candidate* for a different occurrence and always re-enters the
pipeline at stage 2, never at stage 11.

## 4. False-closure rule

Inherited from `docs/parser/TRANSCLUSION.md`: an accepted crosswalk row is
**not** visual closure; a family summary row (`loc=multiple`) is **not** a
closure packet. Only exact rows carrying `qword_row_id`,
`exact_transclusion_group_key`, or `public_payload_hash` can close anything,
and `tools/validate_meta_transclusion_projection.py` (`--require-exact-rows`)
is the ANDON guard. A stage-11 projection with no stage-8 certified facts
under it is the defect family `source_clean_fact_available_but_not_projected`
in reverse — claiming projection without certification.

## 5. Where the pipeline is gated

`python tools/check_regressions.py` (no flags; CI greps for
`ALL REGRESSION CHECKS PASS`) runs the per-stage gates, including:
`certify_typed_fact.py --self-test` and `--demo-sufaha` (FACTCERT block),
`lattice_projectors.py self-test` + `tools/test_lattice_projectors`,
`validate_fd_compiler.py`, `tools/test_typed_edge_graph`,
`validate_typed_edge_graph.py`, `validate_particle_projection_parity.py
--self-test` + the committed sample, `tools/test_entry_transclusion_invariants`,
`build_entry_completion_state.py --self-test`, and the P007PILOT block
(`tools/validate_p007_pilot.py`). Tests live as `tools/test_*.py`
(unittest modules); there is no separate `tests/` directory.

---
Verified against: commit 637d7da (origin/main, 2026-07-29). Artifacts:
`qamus/examples/p007-li-pilot/` (all files named above),
`tools/certify_typed_fact.py`, `tools/lattice_projectors.py`,
`tools/fact_projectors.py`, `tools/fact_ledger.py`, `tools/fd_compiler.py`,
`tools/validate_particle_projection_parity.py`,
`tools/validate_appearance_parity.py`, `tools/validate_website_payload.py`,
`tools/validate_meta_transclusion_projection.py`,
`tools/validate_segment_completeness.py`,
`qamus/lattice/registered-projectors.json`,
`qamus/schemas/projector-record.schema.json`,
`docs/parser/TRANSCLUSION.md`; `tools/check_regressions.py`
ALL REGRESSION CHECKS PASS.
