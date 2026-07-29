# Largelexicon as built (audit)

Verified against: commit `637d7da` (origin/main), audited 2026-07-29 by direct file reads, line counts, live manifest reads, and validator smoke-runs in this worktree (all five largelexicon validators pass: claim-boundary, source-ledger, parser, transclusion, denominator-join). Claims cited `file:line`. GAPs in §8.

## 1. What largelexicon actually is

A **source-clean, dependency-free candidate/lookup substrate** generated from the 2,092 authored Qamus entries (`qamus/data/current/entries.jsonl`), projected into lemma/form/stem fact tables plus a 117,117-row all-visible-qword denominator and crosswalk graph. It is a worklist accelerator and an abstention-gated parser candidate source — explicitly NOT a disambiguator, not live Qamus progress, not certified NLP (`docs/parser/largelexicon-claim-boundary.md:3-5,29-35`; `docs/parser/largelexicon-implementation.md:124-126`).

Key operational rule: "Largelexicon coverage is not disambiguation" — collisions must route to `lexical_collision_requires_context` / `pending_context` / `ambiguous` / two-vote packet; `safe_for_public_hover` and `safe_for_qamus_executor_autopromote` are the consumer contract, and downstream must never infer safety from candidate order (`docs/parser/largelexicon-claim-boundary.md:45-51`; `qamus/procedures/largelexicon-rollout-consumption.md:36-48` — "Do not consume `morphology_candidates[0]` directly").

## 2. Data model

| Table (committed) | Rows | Schema |
|---|---|---|
| `fusha/lexicon/largelexicon/lemma-source.full.jsonl` | 2,092 | `lemma-source@1`: `entry_id` (12-hex), `lemma`, `forms[]`, `root`, `pos`, `gloss_hint`, `no_root_reason` (mandatory when root empty), `risk_flags[]`, `source_keys[]`, `source_status: qamus_current_authored`, `public_boundary {src:qamus, kind:authored, lang:en}` |
| `fusha/lexicon/largelexicon/form-source.full.jsonl` | 8,483 | `form-source@1`: adds `form_id`, `surface`, `surface_bare`, `surface_norm_strict` |
| `fusha/morphology/data/largelexicon-stems.full.jsonl` | 8,483 | `stem-source@1`: adds `stem_id`, `generation_key` (`qamus:<entry_id>:<nnn>`), `gloss_shape`, `features{}`, `pattern`, `form`, and `visible_segments[]` (`{surface, role, qg_class, gloss}` — segments must concatenate to the exact Arabic surface, ANDON rule `docs/parser/largelexicon-implementation.md:80`) |
| qword denominator (54 shards) | 117,117 | `qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json` |
| qword crosswalk | 117,117 | `qamus/schemas/largelexicon-qword-crosswalk.schema.json` (`@2`) |

Crosswalk row identity: `qword_row_id` = `llx-qword-<entry_id>-<usage>-<example>-<qword>`; `source_keys` `^[nvp][0-9]{3,4}$`; nullable `canonical_quran_loc`/`canonical_wbw_loc`; `source_dependencies` minItems 1; `risk_flags` **maxItems 0** (any risk flag fails the schema); multiword guard requires `surface_is_multiword` + reason. Canonical address forms: `quran:S:A:W` and `wbw:S:A:W` are binding; `missing-loc|…` and `sarf:surface:…` are diagnostic only, never reuse authority (`docs/parser/TRANSCLUSION.md:18-22`).

Affix layer: `fusha/morphology/data/largelexicon-affix-compatibility.json` — 8 guarded rules (بـ/لـ/و/ف proclitics, object/possessive suffix pronouns, sound plural suffixes, mīm derivative prefix, tanwīn-alif false-suffix guard); every `safe_projection` is conditional (`candidate_only_until_*_certified`, `guard_only`).

Commit gate: `fusha/lexicon/largelexicon/source-clean-table-allowlist.json` — 5 allowlisted tables with `minimum_rows` floors (2092/7000/7000/100000/100000), `runtime_dependency_policy: dependency_free`, `private_only_sources` = {`qac_raw_tsv`, `mcp_raw_response`, `quran_foundation_raw_response`, `quran_com_raw_response`, `source_photo_or_ocr_dump`}; a full table is committable only if allowlisted AND `tools/validate_largelexicon_source_ledger.py --self-test` passes (`docs/parser/largelexicon-source-ledger.md:19-22`). RM-40 paradigm-generated forms live in a separate artifact and are never merged (allowlist note).

**Live counts** (manifest read at audit time, `qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json`): `canonical_crosswalk_accepted` 88,386 / `canonical_crosswalk_demoted` 37 / `source_crosswalk_packet_ready` 28,694. The hard-coded `85877/31240` in `docs/parser/meta-transclusive-lattice-projection.md:35-36` and `docs/QURANIC-ANCHOR-AND-FLYWHEEL.md:100-101` is a superseded 2026-07-03 snapshot (so marked at `docs/parser/TRANSCLUSION.md:42-43`) — GAP-L2.

## 3. Inputs

Only `qamus/data/current/entries.jsonl` (authored candidate data) may feed public tables; external NLP/QAC/MCP/Quran.com dumps are private evidence only, "never public wording or source labels" (`docs/parser/largelexicon-source-ledger.md:9-14,96-103`). The crosswalk adopter `tools/adopt_largelexicon_qword_crosswalk.py:3-7` consumes private executor evidence and writes only the source-clean projection; it fail-closes on wrong `public_boundary`, `live_mutation_allowed != false`, or missing `source_dependencies` (`:69-84`), with atomic sharded writes + rollback via `largelexicon_common` (`:21-38`).

## 4. Outputs and consumers

- **Mandated readers:** `tools/largelexicon_table_reader.py` (the only sanctioned denominator access; "Do not recreate a second qword denominator database", `qamus/procedures/largelexicon-rollout-consumption.md:70-74`), `tools/fusha_largelexicon_cli.py`, `tools/fusha_standalone_parse.py --db largelexicon`, `tools/fusha_morph_analyze.py` / `fusha_morph_generate.py --db largelexicon`.
- **Runtime consumers of the collision bank** (`fusha/parser/eval/largelexicon-collision-regressions.jsonl`, 7 rows, `fusha/largelexicon-collision-regression@1` with `forbidden_top[]` + `or_gate` abstention statuses): `tools/fusha_suggest.py:40`, `tools/fusha_text_check.py:616`, `tools/validate_largelexicon_parser.py:15`.
- **Curriculum/tutor:** `curriculum/largelexicon-tutor-routing.md` (finding→route table; "source-address crosswalk missing → Qamus source graph repair packet, not learner drill", `:14`; tutor must say "Qamus has a candidate analysis" until Mode A gates pass, `:37-39`); drills `curriculum/drills/largelexicon-collision-abstention.md` (5 cases, e.g. reject `ال+له` for الله) and `largelexicon-morphology-and-hover.md`.
- **Flywheel artifacts:** `tools/build_largelexicon_flywheel_artifacts.py` → 160-row sample (`qamus/examples/largelexicon/flywheel-artifacts.sample.jsonl`) with routes `source_crosswalk_packet→[qamus_source_graph,qamus_executor]`, `candidate_for_executor_validation→[sarf,nahw,qamus_executor,curriculum]`, `validator_packet`, `parser_packet→[sarf,nahw,parser]`.
- **Tooling scale:** 30 `tools/*largelexicon*` files (6 builders, 4 helpers/CLI, 20 validators); 491 non-attic files mention largelexicon.

Consumption procedure: `qamus/procedures/largelexicon-rollout-consumption.md` (179 lines) — CLI-first (`analyze-token`, `analyze-card`, `project-hover`, `validate-mode-a`, `gate-rh-live-candidates`, `:23-34`); autopromote only via `tools/validate_rh_live_source_addressed_candidates.py` with source-address trace + exact locs + source-clean preview + segment-concat exactness + supported qamus-grammar-v1 classes + no unresolved flags (`:56-68`); every consumed row must preserve forward AND reverse trace or it is a repair packet, not closure (`:95-100`); 9 terminal dispositions (`:126-136`); VN-00 public false-closure executor gate (`:143-178`).

## 5. Safe-flow table (what may / may not flow from Qamus)

| MAY flow (and where enforced) | MAY NOT flow (and where enforced) |
|---|---|
| Certified/authored lexeme, root, pattern, form, POS, gloss_hint, `no_root_reason` facts (lemma/form/stem tables; boundary constants `tools/largelexicon_common.py:61-62`) | Page-context and occurrence-specific syntax — routed as packets, never projected (claim-boundary `:29-35`; enforced structurally via packet classes, not a lint — GAP-L6) |
| Guarded affix rules with conditional `safe_projection` (`largelexicon-affix-compatibility.json`) | Source wording / external prose, source labels, paths — `FORBIDDEN_PUBLIC_SUBSTRINGS` = {mcp, tafsir, qac, quran.com, /srv/, c:\, source photo, ocr, …} with leak check raising (`tools/largelexicon_common.py:65-76,94-115,1404-1405`) |
| Provenance triple `{src:qamus, kind:authored, lang:en}` + `source_keys` + canonical `quran:S:A:W`/`wbw:S:A:W` locs | Unresolved items promoted as hovers — `safe_for_*` consumer contract + crosswalk schema `risk_flags maxItems 0` |
| Exception rows with closed `exception_reason` enum and private `evidence_backlink` | Surface-similarity inferences — loc-first rule; `validate_largelexicon_denominator_join.py` rejects raw `qword_index` identity (`docs/parser/largelexicon-implementation.md:36-39`) |
| Crosswalk status (accepted/demoted/packet_ready) as **support evidence — never hover closure** (`docs/parser/largelexicon-source-ledger.md:84-86`) | Overclaim prose — `tools/validate_largelexicon_claim_boundary.py:21-40` lints claim surfaces for forbidden phrases ("camel-tools equivalent", "claims live qamus progress", …) and required disclaimers |

## 6. Transclusion model

Two layers (`docs/parser/TRANSCLUSION.md:16-25`; `docs/parser/meta-transclusive-lattice-projection.md:3-15`): source-clean tables are transclusions of Qamus entries; dependents must regenerate or go stale when a source row changes (Xanadu framing, `docs/parser/largelexicon-collision-safety.md:63-66`). Full-scan transclusion validation over all 117,117 rows is wired and passing (`tools/validate_largelexicon_transclusion.py`; cited as an OBSERVED RESULT at `docs/QURANIC-ANCHOR-AND-FLYWHEEL.md:103-104`). Six required recurring projection families are listed at `meta-transclusive-lattice-projection.md:52-59`; false-closure rules at `:74-87` and `TRANSCLUSION.md:66-74`.

## 7. Limitations (self-declared and measured)

- **Schema-migration posture (most important):** `qamus/indexes/largelexicon/RELEASE.json` reports `validation.pass_rows: 0` with `violation_rows == row_count` for EVERY committed table (form 8,483; lemma 2,092; stem 8,483; crosswalk 117,117; denominator 117,117). Presence of a table is NOT a claim its rows passed the target schema gate (defect box, `docs/parser/TRANSCLUSION.md:3-13`) — GAP-L1.
- Not CAMeL/MADAMIRA/Stanza-equivalent; no trained disambiguation or dependency parsing (`claim-boundary.md:29-35`).
- No measured OOV / error-rate / disambiguation-accuracy / abstention-quality metrics anywhere (`docs/parser/largelexicon-largerollout3-implementation.md:76-78`).
- 1 known unrepaired source-card gap: entry `2a071cd0b50e` / `n993` / مَلْجَأ (`pg443.jpeg`, 42:47) has `examples: []`, so "all 2,092 entries have qword rows" is blocked at 2,091 (`largelexicon-implementation.md:116-122`).
- 28,694 crosswalk rows remain `source_crosswalk_packet_ready`; 37 demoted.
- Homograph quarantine interplay: 30-entry `sarf/rules/homograph-quarantines.json` ("norm() must never decide any of these; absent diacritic → pending, never the commoner reading"); crosswalk-gap quarantines under `qamus/indexes/largelexicon/crosswalk-gap/` (lane-a waves with `quarantined_divergent_ayah_refs`; lane-b waves with per-row `data_quality_quarantine`; wave-03 queue after: `multiple_qword_candidates` 5,447, `unique_qword_candidate` 51, `in_crosswalk_morphline_repair` 13, `no_qword_candidate` 10).

## 8. GAPs — unwired flywheel connections (with work-packet stubs)

- **GAP-L1 — all committed tables fail the target schema gate** (v1→v2 migration posture; `RELEASE.json` pass_rows 0 everywhere). WP-LLX-SCHEMA-MIGRATION: migrate tables to `@2` schemas until `pass_rows == row_count`, then drop the defect box.
- **GAP-L2 — stale hard-coded counts** (85,877/31,240) in `meta-transclusive-lattice-projection.md:35-36` and `QURANIC-ANCHOR-AND-FLYWHEEL.md:100-101` vs live 88,386/28,694. WP-LLX-STALE-COUNTS: replace with manifest pointers per the refuse-to-transcribe pattern of `largelexicon-implementation.md:107-115`.
- **GAP-L3 — largelexicon ↔ fact ledger/projectors: no code linkage at all.** Grep for `lexeme_plane`/"lexeme plane" returns zero hits; `tools/fact_projectors.py`, `fact_ledger.py`, `lattice_projectors.py` never mention largelexicon. The phrase "fact_projectors lexeme plane" has **no referent in this repo**: the lexeme-level tables and the fact-ledger projector system are two disconnected subsystems. The repo's actual "plane" vocabulary is the typed-claim plane (`docs/certification-store-reconciliation.md`) and the documented-form lookup plane (`tools/fact_projectors.py:32-34`). WP-LLX-FACT-LEDGER-BRIDGE: design a typed projector whose `input_fact_types` reads largelexicon stem/crosswalk rows, abstention-first, two-vote gated.
- **GAP-L4 — canonical hover payload compiler not adopted**: dry-run only, "NOT adopted for live output" (`largelexicon-implementation.md:130-132`; charter `QURANIC-ANCHOR-AND-FLYWHEEL.md:100-102`). WP-LLX-COMPILER-ADOPTION (blocked on ADR-003 defects, see `docs/parser/canonical-hover-payload-table.md:115-123`).
- **GAP-L5 — flywheel loop is an ARCHITECTURAL COMMITMENT, hypotheses H1–H7 unevaluated** ("no controlled cross-corpus experiment has yet been run", `QURANIC-ANCHOR-AND-FLYWHEEL.md:44-53,109-136`); the word "largelexicon" appears zero times in the flywheel doc — the connection is implicit via numbers only. WP-LLX-FLYWHEEL-EXPERIMENT.
- **GAP-L6 — page-context/occurrence-syntax exclusion is structural, not linted**: packet routing enforces it in practice, but no validator scans public tables for occurrence-syntax leakage the way `FORBIDDEN_PUBLIC_SUBSTRINGS` scans for source labels. WP-LLX-OCCURRENCE-LEAK-LINT.
- **GAP-L7 — flywheel artifacts are a 160-row sample**, not a full 117,117-row projection. WP-LLX-FLYWHEEL-FULL-PROJECTION.
- **GAP-L8 — n993/مَلْجَأ source-card repair outstanding** (blocks the 2,092-complete claim). WP-LLX-N993-REPAIR.
