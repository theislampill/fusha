> **Historical lane report** (moved from the repo root 2026-08-05). Point-in-time evidence; tallies herein are superseded — current state lives in `docs/current-state.yaml` and the generated ledgers. Do not quote numbers from this file.

# ONTOLOGY RECONCILIATION REPORT

## Scope and evidence boundary

This lane implements the pre-approved F-B/F-C §8 ONTOLOGY RECONCILIATION contract in the `andon-ontology-reconciliation` checkout. The source inputs were:

- `../../data/wbw.css`: the live qg custom properties, selectors, light-mode overrides, and `.92` `qg-verb-prefix` opacity.
- `qamus/schemas/morphosyntax-token.schema.json`: the display-class enum.
- `docs/parser/qamus-grammar-v1-class-map.md`, `docs/GLOSSARY.md`, and `tools/validate_schema_coherence.py`: existing canonical/alias policy.
- The current renderer fallback contract was read from the supplied `wbw.js` surface; no renderer file was changed.

The reproducible source is `tools/build_qg_ontology_registry.py`; the consistency gate is `tools/validate_qg_registry.py`. The generated artifacts are:

- `qamus/registry/qg-class-reconciliation.json` and `.md`
- `qamus/registry/palette-collision-matrix.json` and `.md`

## Q6-1 reconciliation result

The live CSS yields **38** classes: 37 styled semantic roles plus the live generic `qg-segment` fallback. The schema enum has **41** values: 40 canonical entries plus the `qg-negative` legacy alias. The union table contains **42** rows.

The derived valid final ontology count is **39**:

- 37 public canonical classes
- 2 canonical but internal classes: `qg-case`, `qg-relation`
- excluded from that count: live generic fallback `qg-segment`, status-only `qg-unknown`, and legacy alias `qg-negative`

`qg-unknown` is recorded as a status entry pointing to `projection-status`, not as a public qg class. `qg-negative` normalizes to `qg-negation`; no linguistic distinction was found in the existing class-map, glossary, or validator policy, and new output must not emit the alias.

`qg-verb-prefix` remains the live class and is not renamed. Its row records a required owner decision to split the typed person/tense prefix from the derivational marker, with a migration note and `decision_made: false`.

## Q6-5 palette collision result

The matrix computes all **703** class pairs in each theme using exact RGB comparison followed by CIE76 delta-E. The four named owner pairs are exact RGB collisions in both themes:

- conjunction / particle
- question / subject-pronoun
- preposition / oath
- negation / result-fa

The complete flagged totals are:

| theme | exact RGB | near (delta-E < 10) | flagged total |
|---|---:|---:|---:|
| dark | 11 | 7 | 18 |
| light | 18 | 15 | 33 |

The matrix identifies the current non-colour channel as conditional typed label/role text for semantic classes. It marks every pair containing `qg-segment` `REQUIRED-MISSING`, because the generic fallback cannot supply a semantic distinguisher. A blank projected label/role remains missing even where a renderer fallback path exists.

## Q6-6 static accessibility floor

The registry records static ratios against both page and panel backgrounds in both themes. The normal-text floor is **4.5:1**. There are **22** live class/background ratio failures, all in the light theme: 20 page-only failures plus both page and panel for `qg-verb-prefix` after its declared `.92` opacity. The six internal/status-only class-theme checks have no colour and are reported as `REQUIRED-MISSING`, not as numeric contrast failures.

The stylesheet delegates the `--du-*` backgrounds/text to the companion URETHANE token sheet. The registry preserves the CSS expressions and records the local default token snapshot used for static RGB resolution. This is a static source calculation only.

## Harness and verification

The new registry validator is wired into `tools/check_regressions.py` alongside its focused test and self-test. The focused checks and schema-coherence self-test passed during implementation. The final full harness result is recorded here after the terminal verification run.

- Smoke A baseline: the first 120-second probe was tool-timeout-limited after reaching the late harness checks; it did not produce a pass/fail claim.
- Focused registry tests: pass, 3 tests.
- Registry validator self-test: pass, 3 red-first mutation proofs.
- Schema-coherence self-test: pass, 5 lints plus red-first proofs.
- Full command: `python tools/check_regressions.py`.
- Full result: **exit 0 — `ALL REGRESSION CHECKS PASS`** (final terminal run completed in 286.6 seconds).

## Exact NONCLAIMS

- No renderer CSS or JavaScript was changed.
- No file under `../../data` was changed; no live/public app, server, SSH, deploy, restart, whitelist, or production mutation was performed.
- No collision was recoloured, no alias was renamed in live data, and no `qg-verb-prefix` split was applied. The split and any target names/colours remain owner-gated.
- No owner decision was made about collision remediation, legend policy, qg-case/qg-relation public projection, qg-unknown taxonomy beyond the supplied status boundary, or the future split target classes.
- No Arabic root, lemma, singular/plural relation, derivational template, case, mood, governor, agreement, or referent was adjudicated or certified.
- The static ratios do not prove computed browser values, gradient text behaviour, forced-colours behaviour, device-pixel rendering, screen-reader output, or public DOM readback. Those remain renderer-phase deliverables.
- The result does not claim that any generated registry artifact has been pushed, released, published, or deployed.
