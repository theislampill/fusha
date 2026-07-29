# Parser and tutor as consumers (as-built + target audit)

Verified against: commit `637d7da` (origin/main), audited 2026-07-29 by direct file reads, greps, and live `--self-test` runs of the three CLIs in this worktree. Claims cited `file:line`. This doc separates what EXISTS (with tests) from the target-state parser/tutor vision; every aspirational item is GAP-marked in §6.

## 1. The future arbitrary parser and tutor — position in the architecture

The charter commits to "arbitrary-text parsing and tutoring as downstream consumers" of the Qurʾān-anchored candidate machinery (`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md:87`), with "provenance and ambiguity … never traded away for throughput" (`:88`). The design invariant, implemented today in every consumer below: the parser and tutor consume the SAME candidate interfaces (candidate lattices, typed facts, gates) that Qamus authoring uses — they never grow a private analysis path.

What Qamus contributes to both: the 2,092-entry authored lexicon and its indexes (`qamus/indexes/current/`), the largelexicon candidate tables (see `docs/subsystems/largelexicon-as-built.md`), the certified typed-fact plane (`tools/certify_typed_fact.py`), the gate SSOT (`nahw/evals/grammar-decision-gates.json`), and the qamus-grammar-v1 display class vocabulary (`docs/parser/qamus-grammar-v1-class-map.md`).

## 2. Implemented parser surface (executable today)

All three CLIs pass `--self-test` in this worktree and are wired into the harness (`tools/check_regressions.py:3167-3178` and `:3306-3318`).

| Tool | Schema | Contract |
|---|---|---|
| `tools/fusha_text_check.py` (699 lines) | `fusha/text-check@1` (`:39`) | Three input modes (`:5-8`): `source_addressed` (exact `S:A:W`), `corpus_backed` (`corpus:*` ids; gate FLOOR `two_vote_required` — corpus membership alone is never `auto_safe`), `arbitrary_typing` (never `auto_safe`). 12 diagnostic classes with severity/gate/lane/procedure (`:44-56`), mirrored for tutors at `curriculum/tutor-runtime-routing.md:112-125`. |
| `tools/fusha_suggest.py` (371 lines) | `fusha/suggestion@1` (`:29`) | Abstain-first edit ops `INSERT/DELETE/REPLACE/MERGE/SPLIT/RETAIN/REJECT/ABSTAIN`; structural + iʿrāb-sensitive edits never `auto_safe`; overlapping edits NMS-resolved into a C10 conflict (`:5-12`). Loads the largelexicon collision bank (`:40`); every emitted string passes `leak_sot.scan()`. |
| `tools/fusha_learner_feedback.py` (203 lines) | `fusha/learner-feedback-event@1` (`:23`) | KC Violation Record + Point→Teach→Bottom-out ladder; **bottom-out withheld** unless `gate==auto_safe ∧ decision_status==resolved ∧ ¬right_answer_wrong_reason_marker` (`:7-11`); KC SSOT `curriculum/kc-catalog.json` (`:25`); RM-45 asserts every `ISSUE_ROUTE` class maps to a KC (`:31-37`). |

Supporting parser substrate: `tools/fusha_standalone_parse.py` (316 lines; seed lexicon `fusha/lexicon/fusha-lemmas.jsonl`), `tools/fusha_governor.py` (dependency lattice builder), `tools/fusha_morph_analyze.py` / `fusha_morph_generate.py`, validators `tools/validate_fusha_text_check.py`, `validate_learner_feedback.py`. Boundary: the standalone parser is "not a full arbitrary-text grammar checker" — intentionally tiny seed lexicon, no live Qamus/MCP/QAC consultation, no RH-LIVE append (`qamus/reports/standalone-fusha-parser-mvp.md:44-49`); the whole current parser is "a dependency-free smoke substrate", not arbitrary-text certification (`docs/parser/claim-boundary.md:3-5`; stronger claims require named validators, new source-ledger review, metrics, model cards, owner authorization, `:9-15`).

## 3. The candidate interfaces both consumers share

- **Morphology candidate lattice** — `qamus/schemas/morphology-candidate-lattice.schema.json`; builder `tools/fusha_morphology_lattice.py` (`sarf/README.md:135-145`); tutor routing by `evidence_class` at `curriculum/tutor-runtime-routing.md:157-168`.
- **Dependency/governor candidate lattice** — `qamus/schemas/dependency-candidate-lattice.schema.json`, `input_mode` covers `arbitrary_typing` by design (`:46`); no governor edge may be `auto_safe` (`tools/fusha_governor.py:326`). See `docs/subsystems/nahw-executable-map.md` §3.
- **Winning + defeated analyses** — implemented in the particle ontology, not in curriculum: `qamus/schemas/particle-edge-ontology.schema.json:402` (homograph candidate lattice: `mutually_exclusive_candidates` each with its own guards and defeaters; `maxContains: 1` — at most one may ever be certified), `:359` (a certified winning function requires an evidence bundle + two-vote artifact), `:369,:424` (`compatible_functions` coexist within the winner, never as alternatives). The projection contract requires field 10 "Alternatives — the surviving non-winning candidates" and field 11 "Reason — why the winning analysis wins (the discriminating guard)" (`docs/qamus/particle-projection-contract.md:73-75`). Tutoring is contracted to teach from both winners and defeated candidates via those fields; today the executable surface is the polysemy eval bank (`nahw/evals/irab-polysemy-eval.jsonl`, 130 rows) and defeat vocabulary in fixtures (`sarf/evals/false-clitic-split-eval.jsonl:115`).
- **Hover payload row types** a future parser joins (`docs/parser/canonical-hover-payload-table.md`): canonical payload (`qamus/canonical-hover-payload@1`, source-clean body hash, `lemma_status ∈ exact|inferred|candidate|missing|conflict|blocked`, `:22-37`), occurrence binding (`exact_transclusion_group_key = quran:S:A:W|normalized-surface`; forbidden identity keys raw `qword_index` / `missing-loc|…` / `sarf:surface:…`, `:40-62`), exception rows (`:65-72`). Status: schemas + validator landed; compiler dry-run only (GAP-P4).
- **Public display vocabulary** — ~40 `qg-*` classes generated from the morphosyntax-token enum; qg classes are display roles, never provenance; zero parse-hash exposure in public fields, `parse_key.summary` is compact learner ASCII (`docs/parser/qamus-grammar-v1-class-map.md:5-77`; detectors `tools/leak_sot.py`, `tools/validate_public_private_boundary.py`).

## 4. What tutoring uses (implemented)

The tutor runtime is a **dispatcher, not a skill** (`curriculum/tutor-runtime-routing.md:1-8`), with ten routing tables: learner mistake → sarf/nahw procedure (`:10-52`); situation → curriculum (`:54-67`); parser issue class → route (`:76-97`); arbitrary-text class → route (`:104-125`); governor-lattice edge → route (`:130-147`); cross-builder conflict (`:149-155`); morphology lattice by `evidence_class` (`:157-168`); suggestion outcome (`:170-182`); KC hint ladder with `cefr_band` (`:184-200`); CEFR display gating (`:202-208`). Runtime module `tools/fusha_tutor_runtime.py`; CEFR gate `tools/fusha_cefr_gate.py` (CEFR is scaffolding, not certification; iʿrāb terminology C1+ only, `nahw/SKILL.md:295-296`).

Curriculum inventory: 20 root files (incl. `zero-to-fluency-roadmap.md` 350 lines, `quran-reading-path.md`, `hadith-reading-path.md`, `placement-test.md`, `kc-catalog.json`), 22 drills under `curriculum/drills/`, assessment schemas + sample keys under `curriculum/assessment/`, progress **templates** under `curriculum/progress/` (templates only — GAP-P5), and the dogfood-derived reports under `curriculum/reports/`.

Largelexicon boundary in tutoring: the tutor must say "Qamus has a candidate analysis" until Mode A source-address + sarf/nahw gates pass; unknown tokens become questions, not corrections (`curriculum/largelexicon-tutor-routing.md:37-39`); source-graph defects route to repair packets, "not learner drill" (`:14`).

## 5. Dogfood output types (required and implemented)

Machine contracts:

- `qamus/schemas/dogfood-event-ledger.schema.json` (`qamus.dogfood_event.v1`) — a chain of events reconstructing defect → typed facts → rules → fixtures → projector/validator changes → skill updates → analogous discoveries → shadow tests → deploys → readbacks → lesson; closed `loop_stage` enum starting `defect_found`; "events are evidence, not narrative" (`:5,:23-40`).
- `qamus/schemas/full-corpus-hover-dogfood-audit.schema.json` — row-level read-only audit of live hover grammar completeness, 24 required fields (`quran_loc`, `dogfood_class`, `sarf`, `nahw`, `entry_linkage`, `certification`, `learner_breakdown_blocker`, `detectors`, `routes`); "Populated hover text is not sufficient for certification" (`:5`).

Tooling (13 builders/validators in `tools/`): `build_full_corpus_hover_dogfood_audit.py`, lane packets, next-state queues, review pack, known-defect readiness, production-bug lessons, shadow review pack, reconcile/summarize scripts, plus `validate_full_corpus_hover_dogfood_audit.py`, `validate_full_corpus_dogfood_review_outputs.py`, `validate_full_corpus_dogfood_subagent_lanes.py`.

Dogfood → curriculum wiring (the return edge of the flywheel): `curriculum/vn-dogfood-to-curriculum-synthesis-20260627.md` (460 lines), `curriculum/reports/dogfood-curriculum-crosswalk-20260627.md`, `curriculum/drills/dogfood-error-remediation-index.md`, `sarf/drills/dogfood-sarf-remediation.md`, `sarf/curriculum/dogfood-sarf-map.md`, `nahw/drills/dogfood-nahw-remediation.md`.

Fullest worked vertical slice: `qamus/examples/p007-li-pilot/` (24 files: candidate lattice, 49-row typed-fact table with per-fact evidence policy, two-vote artifacts v1 + v1.1, votes A/B + MCP evidence, transclusion edges, projections, live rows, `reverse-trace.json` "projection → facts → events → two-vote → votes → MCP → matrix → live row", parity report, production-difference honesty, reviewer worklist, vn-unlock; gates listed `qamus/examples/p007-li-pilot/README.md:56-59`).

## 6. GAPs (with work-packet stubs)

- **GAP-P1 — arbitrary-text parsing is capability-bounded by design, not "done".** Tiny seed lexicon, no external consultation (`qamus/reports/standalone-fusha-parser-mvp.md:44-49`); arbitrary text can never reach certification by construction (floors at `two_vote_required`, `tools/fusha_text_check.py:42-43`). The target arbitrary parser remains future work. WP-PARSER-ARBITRARY-SCALEUP (requires: source-ledger review, split manifests, metrics, model cards, owner authorization per `docs/parser/claim-boundary.md:15`).
- **GAP-P2 — the `fusha analyze-token / analyze-card / project-hover / validate-mode-a` CLI family in `docs/parser/fusha-cli-contract.md:19-89` has no implementing scripts** — the contract doc describes an older/target command surface; the implemented surface is the three CLIs of §2. WP-PARSER-CLI-RECONCILE: either implement the contract commands or restate the contract over the shipped CLIs.
- **GAP-P3 — no tutoring question-list artifact.** Nearest existing pieces: the human-review-packet "question to answer" requirement (`docs/parser/fusha-cli-contract.md:113-122`), `exact_question` per queued status (`tools/tranche1_projection.py:687`), and the p007 reviewer worklist. WP-TUTOR-QUESTION-LIST: define a learner-facing question-list schema fed from pending/defeated candidates.
- **GAP-P4 — canonical hover payload compiler dry-run only** (defects TR-01/02/04/05/06 open, gated on ADR-003; `docs/parser/canonical-hover-payload-table.md:115-129`). WP-PARSER-PAYLOAD-COMPILER-ADOPT.
- **GAP-P5 — learner feedback loop is one-directional.** No learner-state store; `curriculum/progress/*.template.md` are unwired templates; bottom-out always withheld in arbitrary mode, so the loop terminates in "route to review" rather than a closed feedback cycle (`curriculum/tutor-runtime-routing.md:186-189`). WP-TUTOR-LEARNER-STATE.
- **GAP-P6 — certified-lemma fanout coverage near zero** ("only illustrative sample + reject fixtures", `docs/certification-policy.md:16-19`); the certification authority is `proposed`, not adopted (`docs/certification-authority.md:3`). WP-CERT-FANOUT-COVERAGE.
- **GAP-P7 — winning/defeated tutoring surface is schema-complete but content-thin**: the ontology and projection fields exist; no tutor-facing renderer consumes the alternatives/reason fields yet. WP-TUTOR-DEFEATED-ANALYSES-RENDER.
