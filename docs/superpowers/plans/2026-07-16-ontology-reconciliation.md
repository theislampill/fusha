# Ontology Reconciliation Implementation Plan

> **For agentic workers:** This plan is being executed inline in the pre-approved ONTO lane brief.

**Goal:** Reconcile the live qg palette with the schema enum and legacy alias policy, compute static palette collisions and contrast floors, and gate the registry through the full regression harness.

**Architecture:** `tools/build_qg_ontology_registry.py` reads the external `../../data/wbw.css` contract and the schema enum, then emits the two requested registry artifacts. `tools/validate_qg_registry.py` is the executable consistency gate and is called by `tools/check_regressions.py`; it validates coverage, required fields, owner-boundary statuses, and collision/contrast artifact integrity. No renderer or external data file is modified.

**Tech Stack:** Python 3 standard library, JSON, Markdown, existing `tools/check_regressions.py` harness.

## Global Constraints

- Work only in `../../onto-wt` on `andon-ontology-reconciliation`.
- Preserve all 38 live CSS classes, 40 canonical schema roles, the `qg-negative` alias, and explicit Q6-2/Q6-5/Q6-6 boundaries.
- Keep `qg-case` and `qg-relation` canonical but internal; represent `qg-unknown` as a projection-status entry, not a class.
- Record the required `qg-verb-prefix` person-prefix/derivational-marker split without renaming live classes.
- Do not change renderer, `../../data`, live/public app, push, tag, release, or deployment surfaces.

## Tasks

1. Add red-first tests for registry coverage and required-field validation.
2. Implement CSS/schema parsing, semantic metadata, CSS-token resolution, CIE76 pairwise collision computation, and static WCAG contrast calculation.
3. Generate `qamus/registry/qg-class-reconciliation.json/.md` and `qamus/registry/palette-collision-matrix.json/.md`.
4. Wire the validator self-test into `tools/check_regressions.py` and add `docs/reports/history/2026-07-16-ONTO-REPORT.md` with exact nonclaims.
5. Run focused tests, artifact ergonomics, schema coherence, the full regression harness, `git diff --check`, and the final staged review; commit with an `onto:` prefix and do not push.
