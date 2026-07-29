# Sarf executable map (as-built audit)

Verified against: commit `637d7da` (origin/main), audited 2026-07-29 by direct file reads and greps in this worktree. Every claim below is cited `file:line` (or `file` for whole-file/dir facts). This document describes what is IMPLEMENTED; anything intended-but-not-executable is in §8 (GAPs) with a work-packet stub reference. Nothing in this map is a release claim.

## 1. What the sarf subsystem is

The sarf skill is the morphology decision layer used BEFORE any Qamus gloss is authored or applied: root, POS, derived form/wazn, clitics, homograph quarantine, and the "PENDING beats a wrong gloss" contract (`sarf/README.md:9-28`). Its skill text is `sarf/SKILL.md` (633 lines): purpose/input/output contract (§1–3, `sarf/SKILL.md:68-94`), normalization ladder raw → `norm()` → `norm_strict()` → `bare()` → QAC → source-address (`sarf/SKILL.md:96-104`), root/POS/wazn ladders, clitic and suffix rules, homograph quarantine, and four CANDIDATE increments:

| Increment | Location | Content | Status |
|---|---|---|---|
| sarf@2.1 | `sarf/SKILL.md:405-462` | 16 projector-ready + 4 review-gated rules (2026-07-12 calibration) | CANDIDATE — "NOT released; does not amend @2" (`:405`) |
| sarf@2.2 | `sarf/SKILL.md:463-527` | closes ANDON detector gaps G1–G7 (QAMUS-RICH-NORM-001) | CANDIDATE (`:463`) |
| sarf@2.3 | `sarf/SKILL.md:528-590` | 6 root-certification gates (Window-1 measured flywheel) | CANDIDATE (`:528`) |
| sarf@2.4 | `sarf/SKILL.md:591-633` | 5 clitic/host + letter-ownership rules (P00 لِـ p007 pilot) | CANDIDATE (`:591`) |

Enforced executable gates are named in SKILL.md §13b (`sarf/SKILL.md:206-219`): `tools/validate_linguistic_decisions.py` plus the gate-tier ladder `auto_safe → two_vote_required → human_source_review_required → never_auto_resolve`. The gate-tier SSOT loaded by the harness is `nahw/evals/grammar-decision-gates.json` + `nahw/rules/two-vote-required-rules.json` (`tools/check_regressions.py:129-130`).

## 2. Rule stores: two disjoint stores, only one carries status

**Store A — `sarf/rules/*.json` (13 files, 1,152 lines).** Human-authored gate/quarantine data. No file carries `status`, `basis`, `guards`, or `defeaters` as schema fields (grep over `sarf/rules/` returns zero hits); provenance appears only in `verb-measures.json:115` and `root-pattern-risk-rules.json:56`.

| File | Entries | Example id / key |
|---|---|---|
| `hamza-gates.json` | 7 norm_collapses + 4 gates | `iman-vs-ayman` |
| `homograph-quarantines.json` | 30 quarantines | `مَن` (vs `مِن`) |
| `masdar-participle-gates.json` | 5 rules | `masdar_nominal` |
| `morphology-risk-rules.json` | 7 risk_flags + standing_order | `multi_sense_root` |
| `plural-gender-rules.json` | 7 patterns + 5 gender_cues + 5 forbidden_shortcuts | `msl-nominative` |
| `pos-mismatch-rules.json` | 4 rules + 7 examples | `drop-verb-gloss-on-nominal` |
| `root-decision-rules.json` | 5-rung ladder + 4 rules | `stop-at-first-certifying-rung` |
| `root-pattern-risk-rules.json` | 7 rules | `broken_plural_no_surface_link` |
| `suffix-pronoun-rules.json` | 11 enclitics + 3 forbidden + 1 gate | (no ids — keyed by enclitic) |
| `surface-state-transition-rules.json` | 8 transitions + 7 forbidden | keyed by `from_observation` |
| `verb-measure-gates.json` | 5 rules + 4 tiers | `form_dominant_sense_keyclean` |
| `verb-measures.json` | 10 forms I–X + rare/quadriliteral/geminate + 8 paradigm slots | `I` |
| `weak-root-gates.json` | 5 rules | `norm_only_weak` |

**Store B — `qamus/skills/rule-registry*.jsonl` (the accepted/candidate registry).** 242 rows across `rule-registry.jsonl` (171) + increments 21/22/23/24 (27/18/8/9) + `rule-registry-richseg.jsonl` (9). Sarf rows: 135 total = **55 accepted, 79 candidate, 1 blocked**. Uniform 16-field schema per row includes `status`, `gate`, `fact_family`, `abstention_condition`, `projector.guards`, `defeaters`, `evidence_addresses`, positive and negative examples, `code_references`, `test_references`, `provenance`. Gate tiers observed: `baseline@1-accepted` (55), `@2.1-candidate:redfirst+branch-proven` (19), `@2-candidate:gate10.3=covered_full` (17), `@2.2` (15), `@2.3-candidate:redfirst+window1-measured` (6), `@2.4-candidate:redfirst+p00-pilot-measured` (5), richseg (5), partial-coverage tiers (10 rows — see GAP-S7), `@2-blocked:blocked_insufficient_convention_exemplars` (1).

The two stores do not cross-reference each other by path (GAP-S3).

## 3. Fixtures and evals

Red-first skill fixtures with matching discriminator + test modules under `tools/skill_fixtures/`: `skill_fixtures.jsonl` (36, baseline @1/@2), increments 21/22/23/24 (55/37/27/26 rows), richseg (10); test modules `test_skill_fixtures_increment21..24.py`, `test_skill_fixtures_richseg.py`.

`sarf/evals/` — 11 banks: `false-clitic-split-eval.jsonl` (130 rows), `nominal-derivative-error-eval.jsonl` (113), `vn00-public-visual-andon.jsonl` (64), `vn00-aggressive-false-closure.jsonl` (20), `morphology-candidate-lattice.jsonl` (7), `largelexicon-collision-safety.jsonl` (3), `combining-mark-byte-exact-eval.jsonl` (2), `surfacemap-wbw-absent-eval.jsonl` (2), plus `sarf-state-machine-eval.json` (26 cases), `corpus-authoring-eval.json` (14), `qamus-regression-eval.json` (11 assertions). **Runner coverage is the largest sarf gap: `tools/fusha_eval_coverage.py` reports 20 nahw+sarf banks / 928 rows, of which only 1 bank has a runner — none of the sarf banks do** (GAP-S1).

`sarf/examples/` — `qamus-regressions.jsonl` (38), `root-form-decisions.jsonl` (10), `verb-measure-examples.jsonl` (18); parse-gated in the harness at `tools/check_regressions.py:413-429`. Additional morphology fixtures: `fusha/morphology/fixtures/rm40-eval-gold.jsonl` (3), `rm40-emitted.jsonl` (2), `rm40-generated-candidates.jsonl` (11).

Supporting material: 23 procedures in `sarf/procedures/` (14 existence-gated at `tools/check_regressions.py:156-163`; `tools/validate_sarf_skill.py:23-27` requires 17 by name), 6 drills, 7 references, 4-file curriculum (existence-gated at `tools/check_regressions.py:195`).

## 4. Producers (candidate generation)

All producers emit CANDIDATE-only packets with `live_mutation_allowed=false`, `public_materialization_allowed=false` and an "EXACT NONCLAIMS" section (e.g. `FAM5-REPORT.md:5,62-68`, `FB1-REPORT.md:15-17`, `PROOFN-REPORT.md:59`).

| Producer | Module (`tools/`) | Family | Reach | Candidates | Abstentions | Cited |
|---|---|---|---|---|---|---|
| FAM2 | `fam2_lexical_producer.py` | lexical_nouns_adjectives | family 121; sample 40 | 2 | 38 (95%) | `qamus/examples/fam2-lexical/generated/calibration-summary.json:2-8` |
| FAM3 | `fam3_number_producer.py` | number_words | 57 | 8 | 49 (86.0%) | `FAM3-REPORT.md:9-18,38` |
| FAM4 | `fam4_finite_verb_producer.py` | finite_verbs | 12 | 4 | 8 (66.7%) | `FAM4-REPORT.md:11-16,34` |
| FAM5 | `fam5_derived_verb_producer.py` | derived_verbs | 7 | 3 | 4 (57.1%) | `FAM5-REPORT.md:6,41-47` |
| FB1 | `build_clitic_pronoun_producer.py` | clitic_pronoun_compositions | 234 source / 48 selected | 41 | 7 `idgham_D_ambiguous_boundary` (14.6%) | `FB1-REPORT.md:5-11,47-92` |
| PROOF-V | `proofv_verb_producer.py` | verb, `فَٱتَّبِعْنِى` 19:43:10 | 1 token | 7 typed facts, 10 graph edges | 1 pending naḥw fact | `PROOFV-REPORT.md:5,39-41,90-91` |
| PROOF-N | `proofn_noun_sufaha.py` | noun `السُّفَهَاء` 2:13:12 | 1 token | 11/11 certified facts, 35 graph records | readback `declared_not_measured` | `PROOFN-REPORT.md:9,41,53,59-60` |

The 455-row P/V/N verified corpus is reprocessed by FD (`FD-REPORT.md`: 455 compile, 0 parity/reconstruction failures, but 455/455 missing a projector) and FD2 (`FD2-REPORT.md:7,12-16`: F-B candidate 201 / not-applicable 221 / unresolved 33; F-C candidate 159 / withheld 296). FD2 family denominators (`FD2-REPORT.md:17-27`): clitic_pronoun_compositions 234, lexical_nouns_adjectives 121, number_words 57, function_tokens 26, finite_verbs 12, derived_verbs 3, broken_plurals 1, proper_names 1. Three families have **no producer at all** (function_tokens, broken_plurals, proper_names — GAP-S9).

Abstention reason vocabularies are typed per producer (`FAM3-REPORT.md:46-70`; `FAM4-REPORT.md:40-51`; `FB1-REPORT.md:47-92`).

## 5. Certification and letter ownership

- Typed-claim contract F-A: `tools/typed_claim_contract.py` + `tools/validate_typed_claim_contract.py`, schema `qamus/schemas/typed-claim-contract.schema.json` — "a prose assertion is not itself a typed fact" (`FA-REPORT.md:10,17-28`).
- Decision gates: `tools/validate_linguistic_decisions.py` (`sarf/SKILL.md:209-211`).
- Certification state machine: `tools/certify_typed_fact.py:3-34` — `candidate → review_required → certified` (+ blocked/rejected), revocation with reverse-dependency cascade, hash-chained append-only events; governed by `docs/certification-authority.md` (which is itself **proposed**, not adopted — `docs/certification-authority.md:3`).
- Live certification evidence: `qamus/certification/p007-geometry-wave/typed-facts.jsonl` (1,362 facts, 20 fields incl. `ownership`, `guards`, `defeaters`) + `events.jsonl` (4,086 hash-chained events = 1,362 × 3 transitions).
- Letter ownership: rule `sarf-fused-lil-exact-letter-ownership` (byte-exact span carve; every base letter owns its trailing combining marks; identical surface carves identically at every occurrence) `sarf/SKILL.md:616-629`; canonical worked 7-span table `PROOFV-REPORT.md:45-53`; implementing code `tools/proofv_shared_compiler.py`, `tools/proofp_compiler.py`; ownership fields in `qamus/skills/particle-function-registry.jsonl` and `rule-registry-increment-24.jsonl`.

## 6. Projection and consumers

Two projector engines, both abstention-first, both candidate-only:

- `tools/lattice_projectors.py` — declarative predicates (`pred_c1_impf` :262, `pred_c5_enclitic` :273, `pred_fb1_clitic_pronoun` v1–v3 :286/:298/:327, `pred_tranche1_morphology` :361) and guards (`homograph_surface_ambiguity` :436, `surface_byte_exact` :445, `construction_match` :457). Registered in `qamus/lattice/registered-projectors.json` (schema `qamus.lattice.registered_projectors.v1`; `gate_authority` at `:5`: projectors emit CANDIDATE projections only, nothing mutates the live whitelist).
- `tools/fact_projectors.py` — registered projectors over the append-only fact ledger (`:1-7`): `sarf.documented_form.v1`, `sarf.paradigm_generated.v1` (RM-40; `gate_tier: two_vote_required`, kept out of the documented-form lookup plane, `:32-34`), `sarf.fam2..fam5.*`, `sarf.proofv.verb.v1`, plus typed input→output contracts (`:856-921`) and defeater checks (`homograph_norm_key_collision` :125, `harakah_blind_sole_candidate` :138, `liaison_clitic_mismatch` :146, and others :154-176).

Hover pipeline (the main consumer): `tools/audit_all_hover_tokens.py` audits all 49,900 Qurʾān example tokens (`:2`), reads the staging artifact `out/hover_stage/wbw-lookup.json` + `fusha-hover-token-decisions.jsonl` + `qamus/indexes/current` (`:5-9`), emits `qamus/reports/hover-token-audit-full.jsonl` with per-token terminal state `resolved | pending(exact blocker) | quarantine | repair_candidate` (`:17`); consumed by the harness at `tools/check_regressions.py:450,455-469`. Other consumers: `tools/export_hover_decisions.py`, `tools/build_canonical_hover_payload_table.py`, `tools/query_hover_token.py`, `tools/fd_compiler.py`. Public hover labels are fixed: "Ṣarf — how this piece forms the word" (`PROOFV-REPORT.md:75-76`).

Drills/tutoring consumers: `sarf/drills/dogfood-sarf-remediation.md`, `sarf/curriculum/dogfood-sarf-map.md`, and the tutor dispatcher `curriculum/tutor-runtime-routing.md:10-52` (learner mistake → sarf procedure routing). Parsing consumers: `tools/fusha_text_check.py`, `tools/fusha_suggest.py`, `tools/fusha_standalone_parse.py` (see `docs/subsystems/parser-and-tutor.md`).

**End-to-end chain (the only fully worked one):** `PROOFN-REPORT.md:11-29` — entry → sense → card → selected word → source-card evidence → display-local/canonical crosswalk → canonical occurrence → typed facts → certified attachment → shared compiler → at-rest projection → compact/expanded ṣarf/naḥw → rich hover → repeated appearances → public readback target (declared_not_measured) → reverse trace.

Candidate authoring inputs live under `qamus/candidates/{nawawi40,qamus_2092,repairs}/` as batch JSONL + `.provenance.jsonl` sidecar + `.report.md` triplets; the harness reads `suffix_pronoun_hover_batch_001.jsonl` at `tools/check_regressions.py:239` and `token_hover_decisions_batch_001.jsonl` at `:359`.

## 7. Per-category table

Legend: "runner" = an executable check that evaluates the bank's rows (not mere existence/parse gating).

| Category | Accepted rules | Candidate rules | Basis / guards / defeaters | Fixtures / evals | Actual producer | Corpus + P/V/N reach | Abstentions | GAP |
|---|---|---|---|---|---|---|---|---|
| Root identification | `root-decision-rules.json` (5-rung ladder + 4 rules; no status field) | registry @2.3 root-certification gates (6, candidate) | evidence ladder `sarf/README.md:53-59`; registry rows carry guards/defeaters | `root-form-decisions.jsonl` (10, parse-gated) | — (no dedicated producer) | via FD/FD2 455-row compile | risk-flag routed | no runner (GAP-S1) |
| Pattern / measure I–X | `verb-measures.json` (10 forms), `verb-measure-gates.json` (5) | @2.1/@2.2 registry rows | provenance `verb-measures.json:115`; tier ladder in gates file | `verb-measure-examples.jsonl` (18, parse-gated); drills | FAM4, FAM5 | FAM4 12 rows / FAM5 7 rows; P/V via PROOF-V | FAM4 66.7%, FAM5 57.1% | no eval runner |
| Weak roots | `weak-root-gates.json` (5) | — | gate triggers in file | none dedicated | FAM4 (typed `weak_root_pattern_unresolved` ×2, `FAM4-REPORT.md:48,50`) | 2 typed abstentions | typed | **no eval bank at all** (GAP-S1) |
| Hamza | `hamza-gates.json` (7+4) | @2.2 (hamzat al-waṣl handling, `FAM5-REPORT.md:55`) | norm_merges/certify_with fields | inside `qamus-regression-eval.json` | FAM5 governed field | — | — | bank dark |
| Plural / gender | `plural-gender-rules.json` (7+5+5) | — | forbidden_shortcuts | none dedicated | FAM2 | 121 family rows | 95% (worst of any producer) | broken_plurals has no producer (GAP-S9); FAM2 has no root report (GAP-S10) |
| Maṣdar / participle | `masdar-participle-gates.json` (5) | — | require/triggers fields | `nominal-derivative-error-eval.jsonl` (113) | — | — | — | 113-row bank dark (GAP-S1) |
| Suffix pronouns / clitics | `suffix-pronoun-rules.json` (11 enclitics) | @2.4 (5 rules), FB1 registry rows | fixture-backed adversarial set `FB1-REPORT.md:37-41` | `false-clitic-split-eval.jsonl` (130); FB1 8 positive + 9 adversarial fixtures | **FB1** | 234 source rows, 48 selected | 7 typed (14.6%) | 130-row bank dark; file has no rule ids (GAP-S5) |
| Homographs | `homograph-quarantines.json` (30) | — | `distinguish_by` + pending-not-commoner rule | `qamus-regression-eval.json` (11); inline harness asserts (visible in `tools/check_regressions.py` output) | defeater `homograph_norm_key_collision` (`fact_projectors.py:125`) | quarantine routing repo-wide | pending by design | quarantine JSON itself has no Python consumer outside attic (GAP-S4) |
| Exact reconstruction / surface state | `surface-state-transition-rules.json` (8+7 forbidden) | richseg registry rows (9, candidate) | two-vote flags per transition | `sarf-state-machine-eval.json` (26); `combining-mark-byte-exact-eval.jsonl` (2); byte-exact letter-ownership rule | PROOF-V 7-span carve; FD 0/455 reconstruction failures | full 455 | — | .json bank not row-counted by coverage tool |
| POS mismatch / proper names | `pos-mismatch-rules.json` (4+7) | — | pos_ladder | inside `qamus-regressions.jsonl` (38) | — | — | — | proper_names family has no producer (GAP-S9) |

## 8. GAPs (honest, with work-packet stubs)

- **GAP-S1 — 19 of 20 eval banks have no runner.** `tools/fusha_eval_coverage.py` (run in this worktree): 20 banks, 928 rows, 1 runner (`tools/run_grammar_evals.py` over a nahw bank). All sarf banks are dark; 7 `.json` object-form evals are not even row-counted. Work packet: WP-SARF-EVAL-RUNNERS — build runners for the 8 sarf jsonl banks + row-count the 3 .json evals, wire into `check_regressions.py`.
- **GAP-S2 — `sarf/reports/skill-completion-audit-20260624.md:17` claims "Complete: 11/11. Gaps: none"** while citing only dark banks; its generator is atticized (`attic/tools/build_engine_completion_audit.py`). WP-SARF-AUDIT-REGEN: regenerate or retract.
- **GAP-S3 — dual rule stores unlinked.** `sarf/rules/*.json` carry no status; `qamus/skills/rule-registry*.jsonl` carries status but never cites `sarf/rules/` paths. WP-SARF-RULE-CROSSWALK.
- **GAP-S4 — most `sarf/rules/*.json` read by nothing executable.** Only 2 files are existence-checked (`tools/check_regressions.py:188,233`); homograph-quarantines (30), plural-gender (17), hamza-gates (11), pos-mismatch (11), root-decision (9), root-pattern-risk (7), morphology-risk (7), surface-state (15) have no live Python consumer. WP-SARF-RULES-WIRING.
- **GAP-S5 — `suffix-pronoun-rules.json` has no rule ids/array** (`:2-23`); cannot be cited per-rule or fixture-gated. WP-SARF-SUFFIX-IDS.
- **GAP-S6 — all 80 increment rows (@2.1–@2.4 + richseg) are candidate; none accepted**; SKILL.md restates "NOT released" ×4.
- **GAP-S7 — 10 sarf registry rows have declared coverage holes** (`gate10.3=uncovered` ×2, `covered_positive_only` ×2, `covered_negative_only` ×5, `pending-coverage` ×1). WP-SARF-COVERAGE-HOLES.
- **GAP-S8 — `registered-projectors.json:3` says projectors key to *released* sarf@2 rule ids**, but many @2 rows are `@2-candidate:*`.
- **GAP-S9 — no producer for 3 of 8 families** (function_tokens 26, broken_plurals 1, proper_names 1; `fd2-455-report.json:130-137`). WP-SARF-MISSING-PRODUCERS.
- **GAP-S10 — FAM2 has no root-level report** (only `qamus/examples/fam2-lexical/generated/calibration-summary.json`); its 95% abstention rate is undocumented in prose. WP-SARF-FAM2-REPORT.
- **GAP-S11 — no single "rerun all producers" hook.** FAM/FB1/PROOF packets are committed artifacts; report builders exist per family but there is no FAM2 builder and no orchestrator. WP-SARF-PRODUCER-RERUN.
- **GAP-S12 — PROOF readback unverified live.** PROOF-N public readback `declared_not_measured` (`PROOFN-REPORT.md:28,60`); PROOF-V browser/font/live readback unrun (`PROOFV-REPORT.md:84-86,129-131`).
- **GAP-S13 — `certify_typed_fact.py` cannot certify the committed sufaha packet** (evidence file not in repo; demonstrated only on a temp-dir copy, `tools/certify_typed_fact.py:30-34`) while `PROOFN-REPORT.md:41` reports 11/11 certified.
- **GAP-S14 — `sarf/README.md:106-128` inventory is stale** (lists 6 rules files of 13, 4 drills of 6, 4 references of 7). WP-SARF-README-SYNC.
- **GAP-S15 — `norm_strict` re-implemented inline** in `tools/audit_all_hover_tokens.py:29-40` against the single-source rule `sarf/README.md:181-183`. WP-SARF-NORM-DEDUP.
- Minor: duplicated heading `sarf/SKILL.md:569` and `:573`; SKILL.md section numbering jumps 13d→18 with §§14–17 appearing after the principles block.

## 9. Harness

`python tools/check_regressions.py` (6,295 lines, no args) ends `ALL REGRESSION CHECKS PASS` (`:6295`); CI runs it on every PR (`.github/workflows/pr-gate.yml:50-59`) and on merge/daily (`.github/workflows/full-gate.yml:36-41`) with a clean-public-mode env assertion.
