# Procedure — suggestion gating for iʿrāb

Decide whether an iʿrāb-touching correction may be offered, and at what gate. The rule: **an iʿrāb-sensitive correction is never
`auto_safe` without a stated governor justification.** Source of truth: [`tools/fusha_suggest.py`](../../tools/fusha_suggest.py)
(abstain-first) + [`tools/fusha_check.py`](../../tools/fusha_check.py) (`IRAB_SENSITIVE_ISSUE_CLASSES`).

## Input
A diagnostic whose `issue_class` is iʿrāb-sensitive (case/mood/governor/particle-function), plus the governor lattice for the token.

## Checks
1. **Governor present?** If the dependency lattice supplies a `governor_justification` for the asserted case → the correction may be
   offered at a gated tier (≥ two_vote), still never `auto_safe` for a structural edit.
2. **Governor absent/wrong?** → **reject** with `reject_reason='governor_not_justified'`, route to scholar / two-vote; do not offer an
   applied edit.
3. **Unvoweled / ambiguous?** → **abstain** (`reject_reason='ambiguous_unvoweled'` / `needs_context`); prefer abstain over a wrong fix.
4. **Never auto-apply.** The runtime never auto-applies an iʿrāb suggestion; it is a record for review.

## Output
A suggestion with `op ∈ {reject, abstain}` (no replacement) + a closed `reject_reason`, OR a gated hint (`safe_to_show_inline=false`,
`needs_review=true`) when a governor justification is attached. Never an `auto_safe` structural iʿrāb edit.

## Forbidden
An `auto_safe` iʿrāb/structural correction; an applied edit without a governor justification; an abstain/reject carrying a replacement.

## Test
`python tools/fusha_suggest.py --self-test` (the engine) + `nahw/evals/governor-dependency-lattice.jsonl` (the "iʿrāb correction not
auto-safe" case) + `tools/validate_sarf_nahw_skill_backprop.py`.
