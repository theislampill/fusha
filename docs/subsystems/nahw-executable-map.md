# Nahw executable map (as-built audit)

Verified against: commit `637d7da` (origin/main), audited 2026-07-29 by direct file reads and greps in this worktree. Claims cited `file:line`. Implemented behavior only; intended-but-not-executable items are GAP-marked in §8 with work-packet stubs.

Terminology note: **VN** in this repo means a page-range tranche over the authoritative `source_key` ordering of the 2,092 Qamus entries (947 verbs + 1,045 nouns + 100 particles); e.g. VN-00 = `v001-v047 + n0001-n0045` (`docs/VN-OPERATIONS.md:18-27`, `docs/GLOSSARY.md:70`). It is not "verbal noun".

## 1. What the nahw subsystem is

Nahw is the syntax/context disambiguation layer after norm → ṣarf (`nahw/README.md:25-29,56-62`): particle function, governor/iʿrāb, referent, negation scope, homograph resolution by context. Skill text `nahw/SKILL.md` (489 lines): grammar-safety ANDON — "a correct answer with wrong iʿrāb reasoning is unsafe"; two independent checks must agree on **conclusion AND reason** (`nahw/SKILL.md:12-19`); 25-link procedure index (`:21-46`); output contract JSON with `function_class`, `attachment`, `composition`, `parse_key`, `display.segments`, `decision`, `allowed_for_hover` (`:87-105`); governor/dependency-lattice section (`:275-314`); six nahw principles (`:318-326`).

Released tier is naḥw@2. Four CANDIDATE increments are appended, each stating "NOT released; does not amend @2": @2.1 8 rules (`nahw/SKILL.md:374-406`), @2.2 3 rules (`:408-427`), @2.3 2 rules (`:429-448`), @2.4 4 rules (`:450-488`). Machine rows live in `qamus/skills/rule-registry-increment-2N.jsonl` with discriminators `tools/skill_fixtures/skill_rules_increment2N.py`. All 17 nahw increment rows are `status: candidate` (GAP-N1). The registry row schema — where `status`, `projector.guards`, `defeaters`, `abstention_condition` actually live — is uniform with the sarf registry (see `docs/subsystems/sarf-executable-map.md` §2); `mood_basis` is a two-vote-artifact field, not a registry field.

## 2. Rules files (`nahw/rules/`, 12 files)

None of the 12 carries `basis`/`defeaters`/`status` fields; guard fields appear in `particle-context-rules.json` and `referent-guard-rules.json` only.

| File | Entries | Example |
|---|---|---|
| `context-sense-rules.json` | 2 rules + negation_sense_rule + polyseme quarantines | `qadara_contronym` (`:6`), `la_nafiya_lil_jins` (`:61`) |
| `funcword-homograph-prepass-rules.json` | 3 rules (`qamus.funcword_homograph_prepass_rules.v1`, `:57`) | `man_fatha_not_min` (`:21`) |
| `grammar-problems-gates.json` | 12 topic gates + 2 difficulty rules | `irab: {gate: two_vote_required, hover: never_auto}` (`:5`) |
| `grammar-problems-issue-clusters.json` | 5 clusters (`fusha/grammar-problems-issue-clusters@1`) | `issue_1_wrong_reasoning` (`:14`) |
| `irab-safety-gates.json` | 6 rules | `irab_assignment` requires "reasoning present" (`:5`) |
| `negation-rules.json` | 5 rules | `lam_jussive` (`:7`) |
| `particle-context-rules.json` | 7 rules with `distinguish_by`/`guard`/`pending_fallback` | `man_vs_min` (`:7`) |
| `preposition-pronoun-rules.json` | 4 rules, `renderings_by_referent` | `bihi` (`:7`), `ilayna` (`:37`) |
| `pronoun-attachment-rules.json` | 3 host rules + 2 forbidden + 2 two-vote triggers | `verb_host` (`:5`) |
| `referent-guard-rules.json` | 3 rules + 3 general guards | `halim_referent` (`:7`) |
| `state-transition-rules.json` | 10 transitions + 5 forbidden | `an_light_to_masdariyyah` (`:15`), `min_not_man` (`:124`) |
| `two-vote-required-rules.json` | 12 two-vote + 5 human-review + 5 never-auto triggers | protocol `must_agree_on: [conclusion, reasoning]` (`:36`) |

**Real SSOT enforcement:** `two-vote-required-rules.json` is a verified copy of `nahw/evals/grammar-decision-gates.json`; four-home parity is mutation-proven in `tools/test_gate_ssot.py:20-60` and asserted at `tools/check_regressions.py:128-144` ("grammar trigger lists match SSOT across all 4 homes").

Executable-consumption honesty: 5 of 12 files have **zero** executable consumer (GAP-N2); 2 more are existence-checked only (GAP-N3); the only executable homograph gate from this directory is the 3-rule prepass file via `tools/funcword_homograph_prepass.py:22`.

## 3. Governor / relation model (dependency candidate lattice)

Schema `qamus/schemas/dependency-candidate-lattice.schema.json` — "Fusha dependency / governor (iʿrāb) candidate lattice" (`:4`), `schema: fusha/dependency-candidate-lattice@1`:

- `input_mode`: `source_addressed | corpus_backed | arbitrary_typing` (`:46`).
- Edge fields (`:112`): `edge_id, dependent, headless, governor_type, rel_label, rel_label_ar, …`; `governor_type` `verb|noun|particle|none` (`:121`); `governor_family` incl. `jussive, inna_family, la_jins, istithna, hal, vocative, kana_family, null` (`:135`); `justification_rule` closed enum (`preposition_governs_genitive, idafa_governs_genitive, verb_governs_subject_nominative, …`, `:155`); `evidence_class` `source_addressed|heuristic|unknown` (`:161`); `decision_status` (`:169`); `gate` ladder (`:170`); routing `lane` incl. `scholar_irab_review` (`:176`).
- Builder: `tools/fusha_governor.py` — `build_dependency_lattice()` (`:173`); `governor_not_justified` routes to `scholar_irab_review` + `nahw/procedures/irab-case-mood.md` (`:94`); hard assert "governor edge may never be auto_safe" (`:326`); self-test (`:355-396`).
- Validator: `tools/validate_dependency_lattice.py` — 9 FAIL conditions (`:6-19`): case/mood without justification, ambiguous-marked-resolved, any `auto_safe` edge (`:84-86`), right-answer-wrong-reason under-gated, heuristic-resolved, `summary.live_writes != 0`, etc.
- Shared constant: `IRAB_SENSITIVE_ISSUE_CLASSES` incl. `governor_not_justified` (`tools/fusha_check.py:44-48`), imported by rich-hover and text-check validators.
- Harness gating: `tools/check_regressions.py:3267-3295` (schema/builder/validator existence + `--self-test` + "6 lattices, 0 violations" fixture run over `nahw/evals/governor-dependency-lattice.jsonl`, 7 rows).

**Two-vote v1.1 and `mood_basis`:** `qamus/schemas/two-vote-artifact.schema.json` — v1/v1.1 (`:4,:20`, conditional v1.1 block `:58`); `case_or_mood.mood_basis ∈ governed|tajarrud|default` (`:218-221`); `governor` required only when `mood_basis=governed` (`:206`). Enforced in `tools/validate_two_vote_artifacts.py`: `mood_basis` must be null when value=none (`:304`), governed-without-governor is an error (`:310-311`), `tajarrud/default only licenses raf3` (`:316`); legacy v1 nominal rule retained at `:389-392`.

## 4. "Bare label is not pedagogically complete"

The literal phrase does not appear in the repo; the nearest skill-text anchor is `nahw/SKILL.md:260` ("…must be visible where the public hover claims pedagogical completeness"). The doctrine is executable across four validators:

1. `tools/validate_segment_completeness.py` — the direct implementation: seven fail-closed completeness gates that "reject internally-consistent but pedagogically incomplete rows" (`:16-18`). Gate A `governor_to_segment` (asserted government must show its visible segment, `:20-21`); C `feature_to_display` (claimed prefix/suffix/article/pronoun must appear in `segments[]`, `:23-25`); E `exact_occurrence` (source-addressed records may not fall back to "as context requires", `:27-29`); F `explanation_truth` (`:30-31`).
2. `tools/check_rich_hover_norm.py` — `N-PED-01`: every segment carries a non-empty `gloss_contribution` (`:225-227`); `N-PED-02`: morphline may not hedge committed features (`:229-232`); `N-LANG-01` blocks internal meta-language and leaked label notation (`:65-74,:198-199`).
3. `tools/validate_nahw_skill.py:88-101` — irab-polysemy rows IP-026…IP-034 must carry `composition`, `attachment`, and `reject_host_only_gloss === True` (a host-only gloss is machine-rejected).
4. `tools/validate_vn00_aggressive_false_closure.py` — failure classes naming the defect: `tanwin_or_case_visible_but_unexplained` (`:84-101`), `common_particle_role_underexplained`, `preposition_pronoun_undersegmented`, `article_or_proclitic_not_explained` (`:50-55`).

Doc-level (non-executable): `docs/qamus/particle-projection-contract.md:84-102` — "Rootlessness is taught, never blank"; no Arabic iʿrāb prose in the teaching plane. There is no single named `bare_label` gate; the doctrine is distributed (GAP-N6).

## 5. Particle ↔ VN bidirectional constraint

Artifacts: `vn-ledger.jsonl` (7,740 rows = D3 displayed selected-word records; source-key distribution v 4,558 / n 2,916 / p 266), `vn-readiness-matrix.json`, `vn-graph-metrics.json`, `VNMAP-REPORT.md` (input spaces 100 p / 947 v / 1,045 n `:9-13`; denominators D1=2,092, D2=7,700, D3=7,740, D4 34,323 unique / 56,117 total `:19-27`).

Enforced bidirectionality:

- Ledger level: `tools/validate_vn_ledger.py:124-125` — every row with an `occurrence_id` must have `reverse_entry_relationship_present`; owner-enum `missing_edges` ordering (`:110-122`); denominator sum-check (`:139-140`); red-first mutations incl. reciprocity break (`:241-265`). Gated at `tools/check_regressions.py:5709-5737` (v2 at `:5793-5818`).
- **The worked particle↔VN fixture is the p007 لِـ pilot** (`qamus/examples/p007-li-pilot/`, 23 files). Particle→VN direction: `vn-unlock.json` — 12 certified occurrences → 78 appearances across `VNPROP-00…19` / `P-00…03`. VN→particle direction: `tools/validate_p007_pilot.py` — reverse edge kind `particle_entry_reverse_occurrence_edge` (`:81`); reverse edges must cover exactly the 12 certified occurrences (`:287-288`); reverse-trace closure gate 5 (`:307-347`); page-class totals must be `n:22 / v:54 / p:2` (`:388-393`); red-first `break_reverse_index` (`:514-534`).
- Rerun hooks: the pilot IS executable and deterministic offline — `tools/build_p007_li_pilot.py:35-37` ("Stdlib only. Deterministic: same inputs → byte-identical outputs"), gated at `tools/check_regressions.py:5959-5990`. The full-corpus VN ledger rebuild is **manual/external**: `VNMAP-REPORT.md:148` requires five explicit input paths not present in the repo; CI validates only the fixture subset (GAP-N8).
- Ceiling honesty: `vn-unlock.json#pattern_ceiling_li_kasra_clitic` — 580 matrix rows / 1,266 appearances is a ceiling only; each row still needs per-occurrence host-noun evidence (rejections cited at 48:29:42 and 2:187:9). Reporting 1,266 as coverage would be false closure (GAP-N9).

Particle projection contract: `docs/qamus/particle-projection-contract.md` (status **proposed** 2026-07-29, `:3`) — rich-at-rest + 13-item rich-hover teaching order, projection-hash cross-page parity (`:104-140`), per-occurrence artifact sharing (`:144-152`), candidate-vs-certified planes (`:154-175`). Executable twin `tools/validate_particle_projection_parity.py` (722 lines; parity hash, per-occurrence, rootless pedagogy, no-iʿrāb-prose, lattice/edge/vocabulary checks at `:131-329`; "Where this prose and the validator disagree, the validator is the bug and this doc is the spec", `:18-21`), gated at `tools/check_regressions.py:5859-5893` against the committed fixture sample `qamus/examples/particle_projection_parity.sample.json` only. `qamus/schemas/particle-edge-ontology.schema.json:5` — a certified iʿrāb-bearing edge structurally requires a two-vote artifact reference; the homograph candidate lattice allows at most one certified winner (`:402`, `maxContains: 1`). The template deck `docs/qamus/particle-rich-hover-templates.md` is proposal-status with no validator consumer (GAP-N7).

## 6. Per-category status

| Category | Rules data | Executable gate | Fixtures/evals | GAP |
|---|---|---|---|---|
| Homograph function words | `funcword-homograph-prepass-rules.json` (3), `particle-context-rules.json` (7), `state-transition-rules.json` forbidden set | `tools/funcword_homograph_prepass.py` + 13 tests (`tools/test_funcword_homograph_prepass.py`, incl. 31-correction calibration `:112`); gated `check_regressions.py:2990` | prepass tests; `particle-function-eval.jsonl` (119) | particle-context/state-transition files not machine-read (GAP-N2/N3) |
| Governor / iʿrāb | lattice schema + `irab-safety-gates.json` (6) | `fusha_governor.py`, `validate_dependency_lattice.py` (9 FAILs), gated `:3267-3295` | `governor-dependency-lattice.jsonl` (7 rows, replayed via `tools/replay_sarfnahw_evals.py:48-49`) | irab-safety-gates.json unconsumed; only 7 lattice rows |
| Right-answer-wrong-reason | `grammar-problems-issue-clusters.json` (5) | `tools/grade_grammar_reasoning.py` (AND-gate; self-test `check_regressions.py:4972`), `tools/run_grammar_evals.py` | `grammar-problems-derived-eval.jsonl` (88, the ONLY bank with a scoreboard runner); `irab-right-answer-wrong-reason.jsonl` (6, replayed) | `grammar-wrong-reasoning-cases.jsonl` (8) has no runner (GAP-N4) |
| Negation / scope | `negation-rules.json` (5) | none | none dedicated | GAP-N2 |
| Preposition + pronoun / referent | `preposition-pronoun-rules.json` (4), `referent-guard-rules.json` (3) | none | `suffix-pronoun-eval.jsonl` (71); `tools/test_suffix_pronoun.py` gated `:472-473` | rule files unconsumed (GAP-N2) |
| Pronoun attachment | `pronoun-attachment-rules.json` | existence-check only (`check_regressions.py:234`) | irab-polysemy IP rows with `reject_host_only_gloss` | GAP-N3 |
| Polysemy / context sense | `context-sense-rules.json` (2+) | `validate_nahw_skill.py:76-80` (17 required regression surfaces) | `irab-polysemy-eval.jsonl` (130) | context-sense file unconsumed |
| Two-vote / gates SSOT | `two-vote-required-rules.json` | `test_gate_ssot.py` 4-home parity; `validate_two_vote_artifacts.py` v1/v1.1 | mutation-proven | — |
| Clause relations / exceptions (istithnāʾ, ḥāl, etc.) | asserted `nahw/SKILL.md:226-230`; `governor_family` enum has `istithna, hal, la_jins, vocative` | schema enum only | **no fixture bank exercising them** | GAP-N10 |

Inventory: 28 procedures, 9 references, 8 drills (1,381 lines), 5 curriculum files, 21 eval files (12 jsonl / 4 json / 5 md), 2 example jsonl (10 + 24 rows). `tools/validate_nahw_skill.py` requires 20 procedures, 6 references, 3 evals, 2 drills, ≥25 particle-function cases, 16 required particles, 17 iʿrāb-polysemy surfaces, and MCP-freedom (`:23-112`); gated `check_regressions.py:3336-3337` — but it is structural, not behavioural (GAP-N5).

## 7. Pipeline participation

1. **Candidate generation** — `tools/corpus_to_hover_decisions.py:5-13` (`particle_or_construction` verdict routes to nahw procedures); `tools/export_token_hover_decisions.py:8,70` (same-surface polysemy left pending "needs iʿrāb"); `tools/fusha_governor.py`; `tools/build_rich_hover_morphosyntax_candidates.py:198-202`; `tools/funcword_homograph_prepass.py`.
2. **Gating/certification** — `nahw/evals/grammar-decision-gates.json` SSOT consumed by `tools/build_two_vote_packets.py:52` (packets carry `nahw_evidence`, `:75,:1100`), `build_funcword_two_vote_packets.py`, `build_rebind_two_vote_packets.py`; artifacts validated by `validate_two_vote_artifacts.py`; conflicts surfaced (never side-picked) by `tools/fusha_conflicts.py`.
3. **Projection** — `build_canonical_hover_payload_table.py` + validator; `check_rich_hover_norm.py`; `validate_segment_completeness.py`; `validate_particle_projection_parity.py`; false-closure ANDON `validate_vn00_aggressive_false_closure.py` + `validate_meta_transclusion_projection.py` (gated `check_regressions.py:3344-3352`).
4. **Drills/tutoring** — `tools/fusha_learner_feedback.py:5-9` (KC violation record; bottom-out withheld unless `gate==auto_safe ∧ decision_status==resolved ∧ ¬right_answer_wrong_reason`; hints never downgrade a gate); CEFR depth gate `tools/fusha_cefr_gate.py` (iʿrāb terminology C1+ only, `nahw/SKILL.md:295-296`); back-propagation validators `validate_sarf_nahw_skill_backprop.py`, `validate_sarf_nahw_curriculum_drills_readmes.py` (gated `:3330-3333`).

## 8. GAPs (honest, with work-packet stubs)

- **GAP-N1 — all 17 nahw increment rules candidate-only**, none released (increment files 21/22/23/24). WP-NAHW-INCREMENT-RELEASE-REVIEW.
- **GAP-N2 — 5 of 12 rules files have zero executable consumer** (`context-sense`, `particle-context`, `preposition-pronoun`, `referent-guard`, `irab-safety-gates`; `negation-rules` only in attic). These encode nahw principles 1/2/4/5 and are documentation-grade only. WP-NAHW-RULES-WIRING.
- **GAP-N3 — `state-transition-rules.json` and `pronoun-attachment-rules.json` existence-checked only** (`check_regressions.py:188,234`); their forbidden-collision tables (مِن/مَن، لَمْ/لِمَ، أَنَّ/إِنَّ) are not machine-enforced from those files. WP-NAHW-STATE-TABLE-ENFORCE.
- **GAP-N4 — 5 eval files have no runner** (`nahw-state-machine-eval.json`, `hover-context-eval.json`, `largelexicon-function-collision-safety.jsonl`, `public-boundary-scanner-eval.jsonl`, `grammar-wrong-reasoning-cases.jsonl`). WP-NAHW-EVAL-RUNNERS.
- **GAP-N5 — `validate_nahw_skill.py` is structural, not behavioural**; executable answer-grading covers only the 88-row derived eval + 24 replay rows out of 21 eval files. WP-NAHW-BEHAVIOURAL-GATES.
- **GAP-N6 — no single "bare label" gate**; pedagogical completeness spread over 3 validators; nothing propagates the two-vote `mood_basis`/governor requirement into public hover payloads. WP-NAHW-BARE-LABEL-GATE.
- **GAP-N7 — particle contract proposed, template deck unenforced**; parity validator runs on a committed fixture only, never live corpus rows. WP-NAHW-PARTICLE-CONTRACT-ADOPT.
- **GAP-N8 — VN full-corpus rerun is manual/external** (5 out-of-repo inputs, `VNMAP-REPORT.md:148`); reproducible only at p007 pilot scale. WP-NAHW-VN-RERUN-HOOK.
- **GAP-N9 — p007 pattern ceiling non-transferable** (per-occurrence host-noun evidence required before the certified template applies).
- **GAP-N10 — clause-relation/exception categories asserted with no fixtures** (`nahw/SKILL.md:226-230` vs the deliberately-subset `rel_label` enum). WP-NAHW-CLAUSE-FIXTURES.
- **GAP-N11 — `nahw/reports/skill-completion-audit-20260624.md` is a stale coverage matrix** (2026-06-24, predates @2.1–@2.4; marks modes "complete" on checklist basis, not test results). WP-NAHW-AUDIT-REGEN.
