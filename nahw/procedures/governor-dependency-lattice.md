# Procedure — governor / dependency candidate lattice

Build a **conservative** ʿāmil→maʿmūl (governor→governed) candidate lattice and read it without asserting an unjustified case. Source
of truth: [`tools/fusha_governor.py`](../../tools/fusha_governor.py) (`build_dependency_lattice`) +
[`qamus/schemas/dependency-candidate-lattice.schema.json`](../../qamus/schemas/dependency-candidate-lattice.schema.json).

## Input
A unit (source-addressed or arbitrary) with its tokens (and visible endings where available), optionally the sarf morphology candidates.

## Checks (conservative — resolve as little as possible)
1. **Single-governor spine.** Each governed node has at most one head; a coordinating wāw is **headless** (no invented governor).
2. **Layer-1-safe only, with evidence.** A standalone preposition → genitive resolves **only when the ending is confirmed** (voweled /
   source-addressed). Arbitrary/unvoweled → stays a candidate (gate ≥ two_vote), never resolved.
3. **PP-attachment unresolved.** Keep the prepositional-phrase head (verb / nominal / hidden hāl / hidden ṣifa / clause) **unresolved**
   unless evidence justifies it — never pick a head from the surface.
4. **iḍāfa alternatives.** A bare noun+noun keeps muḍāf-ilayh (genitive) / nominal-sentence khabar (nominative) / ṣifa / badal as
   alternatives; assert a case only when the ending is visible.
5. **Justify before asserting.** Attach a `governor_justification` to any case/mood you assert; if none, the edge is
   `governor_not_justified` → see [`irab-right-answer-wrong-reason.md`](irab-right-answer-wrong-reason.md).

## Output
A dependency lattice of edges, each with a dependent, an optional candidate head (or `headless`), a `rel_label`, an
`assigned_case_mood` (null when not visible), a `governor_justification`, a `gate` (never `auto_safe` for iʿrāb), and
`unresolved_alternatives[]` for an ambiguous edge.

## Forbidden
Resolving PP-attachment without evidence; asserting a case with no governor; inventing a governor for a headless wāw; forcing one
iḍāfa reading when the ending is not visible; an `auto_safe` iʿrāb edge.

## Test
`python tools/fusha_governor.py --self-test` + `python tools/validate_dependency_lattice.py --self-test` (the engine) +
`nahw/evals/governor-dependency-lattice.jsonl`, checked by `tools/validate_sarf_nahw_skill_backprop.py`.
