# P2b — learning engine + CEFR (bridge report)

The P2b slice over the P2 deepening (`general-fusha-grammar-checker-p2`, `8365bf7`). It lands the three PLAN-ONLY P2 learning
deliverables plus a new CEFR layer. Fusha-only; dry-run (`live_writes == 0`); source-clean; ambiguity-preserving; never overcorrect.
Plan packet: `parserplans/general-fusha-grammar-checker-p2b-learning-cefr/` (11 files).

## A — morphology candidate lattice
`tools/fusha_morphology_lattice.py` + `qamus/schemas/morphology-candidate-lattice.schema.json`. Populates the empty
`morphology_candidates[]` placeholder (`fusha_text_check.py`) with the competing out-of-context readings of a token, RANKED
(`score` AND `rank`, never a boolean `correct`) — analyze-then-rank (CAMeL Tools / MADAMIRA / CALIMA-Star; ~12 analyses/word).
It CONSUMES the clitic `segment_candidates` (`segment_candidate_ref` indexes a real row), never rebuilds them. Conservative and
honest: `root`/`lemma`/`pattern` and deep features stay null (P3 fills them with a learned disambiguator); the deliverable is the
POS/segmentation competition + `evidence_class` + ranking + ambiguity preservation. A `>1`-candidate token stays `pending` /
`surface_only|candidate`. Validator FAILs M1–M8 in `validate_fusha_text_check.py`.

## C — suggestion / correction engine
`tools/fusha_suggest.py`; `$defs.suggestion` extended in `fusha-text-check.schema.json`. Abstain-first (M2/F0.5 favours precision;
valid edits recur, spurious don't). **Edit-op decision (P2b):** the prior P2 plan kept `op` closed at `insert|delete|replace|merge|
split|none`; the P2b mandate requires INSERT/DELETE/REPLACE/MERGE/SPLIT/**RETAIN/REJECT/ABSTAIN**, so the op enum is EXTENDED with
`retain`/`reject`/`abstain` (`none` is a legacy alias of `abstain`). `retain/reject/abstain` carry no replacement; `reject/abstain`
carry a closed `reject_reason`. **`edit.target` decision:** `tok:N` is the canonical primary key (always defined across modes);
`edit.source_locus` is an optional `S:A:W` back-reference. iʿrāb-sensitive and structural edits are never `auto_safe`; overlapping
edits are 1D-span NMS-resolved and the loser surfaced as a **C10** conflict (`make_conflict`), never silently dropped. Validator
FAILs 8b/8c/9b/10/11 in `validate_fusha_text_check.py`.

## D — learner-feedback hint ladder
`tools/fusha_learner_feedback.py` + `qamus/schemas/learner-feedback-event.schema.json` + `learner-kc-catalog.schema.json` +
`curriculum/kc-catalog.json` (8 authored KCs) + `tools/validate_learner_feedback.py` (FAIL-LF-1…10). A typed Knowledge Component +
Point → Teach → Bottom-out ladder (ITS/model-tracing first-principles — **no external research citation**). Bottom-out is WITHHELD
unless `gate==auto_safe ∧ decision_status==resolved ∧ right_answer_wrong_reason_marker==false`. Teach references the **cause** (the
governor) for iʿrāb-sensitive classes. Routes resolve on disk; every hint string is source-clean.

## CEFR — instruction + gating
`qamus/schemas/cefr-fusha-level.schema.json` + `curriculum/cefr-fusha-levels.json` (7 authored levels) +
`curriculum/cefr-fusha-instruction.md` + `tools/validate_cefr_fusha_instruction.py` (CEFR-1…7) + `tools/fusha_cefr_gate.py` (the
monotonic-safe projection). **Scaffolding, never certification:** it gates display for a caller-supplied level (visibility,
metalanguage, aggressiveness, hint depth, example difficulty) and never lowers a gate, forces a parse, reveals a withheld Bottom-out,
copies CoE descriptor prose, or asserts a learner's level. Beginner bands carry no iʿrāb-sensitive class. **Documented gap:** the
CEFR-licensing research lane was interrupted (session limit) — the design is conservative by construction (copies nothing, certifies
nothing).

## Invariants (all gated in `tools/check_regressions.py`)
Never collapse unvoweled ambiguity; ranking not a boolean; abstain > overcorrect; iʿrāb output never `auto_safe` without a governor;
Bottom-out withheld past the gate; CEFR scaffolds never certifies; source-clean; closed enums stay closed; `live_writes == 0`.
