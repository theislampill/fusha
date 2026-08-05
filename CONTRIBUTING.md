# Contributing to Fusha

This repository is an **owner-directed programme**, not a conventional open-source project. Most
work is executed by coordinated agent lanes under standing owner rulings, and every change is
gated by executable checks. External PRs are welcome only within the rules below; when in doubt,
open an issue first.

## Orientation

- Start at `START-HERE-FOR-CONTINUATION.md`, then `docs/INDEX.md` (authority precedence).
- Owner rulings live in `docs/decision-ledger.md` — **decided items are never re-litigated** in
  PRs or issues; propose changes by asking, not by editing the ruling.
- The GitHub issue board is a **public mirror of the committed ledgers** at tranche grain
  (curriculum tranches, qamus VN windows VN-00..VN-20, particle families P-00..P-05). On any
  conflict, the ledgers win; issue checkboxes are updated *from* ledger state, never the reverse.

## Hard rules

1. **The harness gates everything.** `python tools/check_regressions.py` must pass in full.
   New behavior needs red-first fixtures: commit the failing case, then the fix.
2. **Generated artifacts are regenerated, never hand-edited.** Files marked GENERATED name their
   builder; run it (`--check` verifies byte-freshness). Hand-edits to ledgers/reports will be
   rejected even if "obviously correct".
3. **Denominators are never collapsed.** Facts ≠ occurrences ≠ entries ≠ appearances; candidate ≠
   certified ≠ deployed; span-live ≠ rich. Every number states its denominator and basis. No
   weaker state may borrow a stronger name.
4. **Custody.** Never commit source-site lesson prose, exercises, or answer keys (see
   `curriculum/l1l6/custody/custody-decision.md`); never name the source site; never include
   private-workspace packet contents, server topology, credentials, or live-deployment receipts.
   Evidence in public text = repo paths, PR numbers, blocker ids.
5. **Linguistic honesty.** Where the grammatical tradition genuinely splits, preserve attributed
   rival analyses — never pick a silent winner. Uncertain iʿrāb routes to pending/two-vote states,
   not to a guess. Qurʾānic text is quoted letter-perfect with sūrah:āyah citation or not at all.
6. **No live mutation.** This repo is candidate-mode toward the live site; deployment is a
   separately owner-gated lane. PRs that touch deployment machinery will not be merged without an
   explicit owner window.

## Pull requests

- One concern per PR; include the regenerated artifacts your change invalidates (hash-pinned
  inputs are checked).
- State plainly what the change does NOT claim (e.g. "candidate only, no certification implied").
- Reference the tranche issue your work belongs to; the closing comment discipline is described
  in each issue body.
