# Procedure — iʿrāb right-answer-wrong-reason (`governor_not_justified`)

Detect the case where the case/mood ENDING is right but the GOVERNOR reasoning is absent or wrong, and route it for review. This is
the executable form of the grammar-safety gate: **a correct answer with wrong iʿrāb reasoning is unsafe.** Source of truth:
[`tools/fusha_governor.py`](../../tools/fusha_governor.py) (`governor_not_justified` edges) +
[`tools/fusha_check.py`](../../tools/fusha_check.py) (`IRAB_SENSITIVE_ISSUE_CLASSES`); oracle:
[`../evals/grammar-wrong-reasoning-cases.jsonl`](../evals/grammar-wrong-reasoning-cases.jsonl) (GP-WR-001…).

## Input
A proposed iʿrāb claim: a token, an asserted `case_mood`, and the claimed governing element + reasoning (if any).

## Checks
1. **Absent governor.** A case asserted with no named ʿāmil and no recognised iʿrāb basis → `governor_not_justified`.
2. **Wrong governor.** A named governor that contradicts the asserted case (e.g. a **preposition** claimed to assign anything other
   than the **genitive**) → `governor_not_justified` (right answer, wrong reason).
3. **Two independent checks.** An iʿrāb/case/mood decision needs two checks agreeing on **conclusion AND reason** (the GrammarProblems
   gate); a single confident assertion is not evidence.

## Output
A `governor_not_justified` marker → `gate ∈ {two_vote_required, human_source_review_required, never_auto_resolve}`, routed to
[`irab-case-mood.md`](irab-case-mood.md) / scholar / two-vote review. **Never** an `auto_safe` hover.

## Forbidden
Shipping a correct ending with an unjustified/contradictory governor as resolved; treating LLM confidence as governor evidence;
auto-resolving an iʿrāb decision.

## Test
`nahw/evals/irab-right-answer-wrong-reason.jsonl` (a preposition asserting a non-genitive; a case with no governor) +
`tools/validate_sarf_nahw_skill_backprop.py`; aligned with the GP-WR oracle.
