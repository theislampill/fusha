# Model routing guide — which capability tier may do what

Continuation-machinery lane (handoff steer section 15). Controlling principle
(owner decision ledger, transfer ruling): **deterministic-tooling competence
never implies linguistic-adjudication competence.** Route by *task class*,
never by confidence. When in doubt, route DOWN the permission (treat the task
as the higher tier) and UP the escalation.

## Tier 1 — deterministic / tooling (any competent model, incl. low-cost)

May run without linguistic judgment because outputs are recomputed, validated,
or mechanically constrained:

- Running builders/validators and reporting their exit status verbatim
  (`tools/check_regressions.py`, `tools/build_pvn_rollout_map.py`,
  `tools/build_current_state.py`, `tools/validate_p007_universe.py`, …).
- Regenerating committed generated artifacts (universe, matrix, rollout map,
  readiness matrices) with unchanged builder code.
- Artifact ergonomics, formatting, JSONL↔meta sidecar maintenance
  (`tools/check_artifact_ergonomics.py`, `tools/format_review_json.py`).
- Mechanical queue bookkeeping: counting rows, splitting waves, carrying
  packet pointers, updating tallies FROM validator output.
- Deterministic recompiles specified by an existing packet (e.g. the VN-00
  note-normalize wave) where a validator defines success.
- Git/PR mechanics, sample extraction, checksum/manifest work.

Tier 1 must NOT: author or edit any Arabic gloss, choose between analyses,
touch certification decisions, or reword linguistic content while "cleaning".

## Tier 2 — linguistic execution (strong general model + the repo skills)

Requires loading `sarf/SKILL.md` + `nahw/SKILL.md` and following the evidence
ladders:

- Direct-source attestation work: bounded Tafsir MCP lookups,
  surface-matching, triangulation, drafting evidence bundles for
  `tools/certify_typed_fact.py` (e.g. the direct-source w2 queue).
- Two-vote participation as ONE voter (reviewer-B must be genuinely
  independent; the MCP is never reviewer-B).
- Authoring candidate glosses (original English, uncertainty preserved) and
  candidate typed facts/edges — always candidate-mode.
- Classifying candidate populations with named guards; writing defeaters for
  rejected candidates.
- Dogfood review passes that produce fixtures and defect reports.

Tier 2 must NOT: certify its own two-vote artifacts alone, resolve
substantive reviewer disagreements, decide multi-sense/iʿrāb questions
without the two-check rule, or promote candidate rules.

## Tier 3 — adjudication (owner / scholar / arbitration only)

Never delegated to any model, at any capability:

- Owner decisions: deploy windows, entry-store mutation, rule adjudication
  (@2.x), namespace/contract rulings, anything on the live site.
- Scholar questions (qirāʾāt bifurcations, genuinely disputed analyses) —
  routed as packets via `docs/blockers.yaml`.
- Arbitration of substantive two-vote disagreements.
- Scripture-facing certification (a human verifies refs/counts).

## The abstain-and-packetize rule

Any task that exceeds your tier, or where the evidence ladder cannot be
satisfied from available sources, is completed by ABSTAINING and producing a
self-contained packet: row ids, evidence addresses consulted, the exact
undecided question, and the tier that must answer it. Queue it
(`qamus/work-queues/` or `docs/blockers.yaml`). An honest packet is a
finished deliverable; a guessed answer is a defect. "Prefer pending over
wrong" applies at every tier.
