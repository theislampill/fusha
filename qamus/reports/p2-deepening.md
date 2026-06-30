# P2 deepening — leak SoT + governor/iʿrāb dependency lattice + cross-builder conflict

Status: **repo-only tooling. Dry-run.** No live Qamus mutation, no production, no service restart, no live coverage
claim. Every P2 tool asserts `live_writes == 0`; all public fields are source-clean `{src:qamus,kind:authored,lang:en}`
and scanned through the shared leak source-of-truth before emit. Built on the P1 slice (branch
`general-fusha-grammar-checker-flywheel-p1`, `a765cef`); P2 lands on `general-fusha-grammar-checker-p2`.

This slice implements **three** of the six P2 themes (E + B + F) and **plans** the other three (A morphology lattice,
C suggestion engine, D learner hint ladder). Plan packet: `parserplans/general-fusha-grammar-checker-p2/` (11 files).

## E — Leak-detector source of truth (`tools/leak_sot.py`)

Before P2, five leak detectors diverged silently (`fusha_check.LEAK_RE` superset vs four narrower ones). The cert
validator's `LEAK_TERMS` was **missing `tafsir` and `tanzil`** — a real gap: a tafsir/tanzil leak passed it.

- `tools/leak_sot.py` defines the canonical forbidden-token data **once** (source names + translation brands +
  provenance labels + path patterns + secrets) and derives **both** a compiled `LEAK_RE` (regex superset) and a
  `FORBIDDEN_LABELS` tuple projection, plus `scan()` / `is_leak()` / `redact()` and a **field-scope registry**.
- `fusha_check.LEAK_RE` now **re-exports** from `leak_sot` (`FC.LEAK_RE is leak_sot.LEAK_RE`), so every P1 + P2 validator
  that imports `FC.LEAK_RE` gets the SoT transparently — verified by all P1 self-tests staying green.
- `tools/validate_source_boundary.py` is the **drift gate**: it asserts `leak_sot` is a verified **superset** of every
  legacy detector's tokens (so consolidation lost nothing) and that the `tafsir`/`tanzil` gap is **closed**.
- **Intentional narrow scopes preserved** (linguistic-decisions scans gloss-only; public-private scans the whole
  serialized object incl. field names; cert scans public_payload-only). The ~46 other leak-bearing validators are
  **documented for migration**, not force-rewritten (refactor risk).

## B — Governor / iʿrāb / dependency candidate lattice (`tools/fusha_governor.py`)

An ʿāmil→maʿmūl (governor→governed) **candidate** lattice with the case/mood it consequently takes and the **rule that
justifies it** — the engineering synthesis that lets the checker say "genitive **because** governed by the preposition"
and detect "**right case, wrong/absent governor**". (Deep-research confirmed treebanks store head-pointer + relation
label but **not** case-as-a-consequence-of-governor, so this is built, not imported — F5–F8; the joint-encoding claim
was REFUTED.)

- **Conservative + ambiguity-preserving:** only the layer-1-safe heuristic resolves (a **standalone preposition governs
  the following noun in the genitive**); **PP-attachment** (which head the PP attaches to) stays `unresolved`; **iḍāfa**
  is a candidate with kept `ṣifa`/`badal` alternatives; a **coordinating wāw is correctly headless** (single-governor
  spine: at most one head — F6). For **arbitrary/unvoweled** input the case ending is not visible, so even the safe rule
  yields a `pending` heuristic candidate, never a confirmed reading. A heuristic edge **never overrides** source-addressed
  certainty.
- **`governor_not_justified`** (a case asserted with no justifying governor — the GP-WR "right answer, wrong reason"
  case) routes to scholar/iʿrāb review and is registered in the shared `fusha_check.IRAB_SENSITIVE_ISSUE_CLASSES`, so it
  can **never** be `auto_safe`.
- Schema `qamus/schemas/dependency-candidate-lattice.schema.json`; validator `tools/validate_dependency_lattice.py`
  (9 FAIL conditions: forced-single-parse, iʿrāb-edge-without-justification, auto_safe, heuristic-resolving-a-case,
  arbitrary-resolving, right-answer-wrong-reason mis-gated, leaks, …). Dependency roles bind to the **closed**
  `morphosyntax-token` `syntax.dependency` enum.

## F — Cross-builder conflict resolution (`tools/fusha_conflicts.py`)

An explicit record of a **disagreement** between the five builders (arbitrary checker, source-addressed checker,
rich-hover flywheel, certification validator, curriculum route). **P2 surfaces the conflict and routes it — it never
silently picks a side.**

- C1–C10 conflict types, each with a precedence-selected `winning_source_of_truth`, `gate_required = max(both readings)`,
  and a `next_action` that routes to two-vote / human / scholar review (or, for a public-gloss-vs-internal-lattice
  conflict, the public gloss stands and the lattice flags an internal review).
- **Master precedence:** source-addressed certainty > heuristic ; cert-validator gate > candidate gate ; deterministic
  verdict > suggestion ; qg-palette enum > segment-role ; source-clean public_boundary > internal evidence. A heuristic
  reading may **never** win over a source-addressed one (enforced by the validator).
- Schema `qamus/schemas/cross-builder-conflict.schema.json`; validator `tools/validate_cross_builder_conflict.py`.

## Smoke A / Smoke B

- **Smoke A** (before mutation): `python tools/check_regressions.py` → 805 ok / 0 FAIL.
- **Smoke B** (after this slice): `python tools/check_regressions.py` → **823 ok / 0 FAIL** — **+18 new P2 gates**,
  **zero regression** (the leak-SoT rewire is transparent; the `IRAB_SENSITIVE` addition is monotonic).

## What shipped (this slice)

- `tools/leak_sot.py`, `tools/validate_source_boundary.py`.
- `qamus/schemas/dependency-candidate-lattice.schema.json`, `tools/fusha_governor.py`, `tools/validate_dependency_lattice.py`.
- `qamus/schemas/cross-builder-conflict.schema.json`, `tools/fusha_conflicts.py`, `tools/validate_cross_builder_conflict.py`.
- Fixtures `qamus/examples/{dependency_lattice,cross_builder_conflict}.sample.jsonl` (+ `.meta.json`).
- `tools/fusha_check.py` — `LEAK_RE` re-exports from `leak_sot`; `governor_not_justified` added to `IRAB_SENSITIVE_ISSUE_CLASSES`.
- `tools/check_regressions.py` — 18 new P2 gates. `curriculum/tutor-runtime-routing.md` — governor + conflict routes.

## Deferred

- **P2 (planned, not built this slice):** A morphology candidate lattice (`001`), C suggestion/correction engine
  (`003`), D learner-feedback hint ladder (`004`).
- **P3:** model-assisted ranking (MADA-style feature-weighted disambiguation / neural disambiguator), full PP-attachment
  resolution, corpus-backed parsing deepening, two-vote consensus storage.
- **P4:** editor-service integration, owner-gated live rendering.

## Note for the Qamus rollout thread

Fusha P2 has deepened the general grammar-checking engine. No live Qamus state was changed. The checker now has
stronger morphology/governor/dependency/suggestion/learner-feedback foundations while preserving Qamus rich-hover as the
gold-data flywheel. Treat this as tooling and review acceleration, not live coverage progress.

## Note for a future general-editor thread

P2 deepens the first arbitrary-typing prototype toward a real Fusha/Classical Arabic editor checker. It should improve
morphology ambiguity, governor/dependency reasoning, safe suggestions, learner hints, and conflict handling. It is still
not full Arabic Grammarly; future work should deepen corpus-backed parsing, model-assisted ranking, editor service
integration, and owner-gated live rendering.
