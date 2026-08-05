# IMPLEMENTAUDIT run — Fusha parser/checker substrate (001)

NORTHSTAR: Build the first Fusha source-addressed parser/checker substrate. Phase 0 (planning) →
implement P0 + smallest coherent P1 slice → audited handoff. Fusha-only. No live Qamus mutation.

## Baseline (Smoke A) — captured before any mutation
- Branch: `main` == `origin/main` @ `a544e6f` (tracked tree clean).
- Untracked: ~200 `qamus/candidates/qamus_2092/*` + `qamus/reports/closure-2092/*` files = the active
  rollout thread's outputs. NOT mine; leave untouched; never stage.
- `python3 tools/check_regressions.py` → exit 1: **776 ok / 2 FAIL**.
  - FAIL #1: `RH-LIVE-00 admin-preview bundle manifest validator self-test` (sha256 mismatch).
  - FAIL #2: `RH-LIVE-00 admin-preview bundle manifest sample validates` (sha256 mismatch).
  - CLASS: generated-artifact-mismatch (checksum drift). OWNER: RH-LIVE rollout thread. PRE-EXISTING on
    origin/main. BOUNDARY: do NOT fix (rollout-owned). Acceptance for THIS run = introduce **zero new
    failures** (FAIL count stays exactly 2, same two RH-LIVE lines) + green targeted validators on new artifacts.

## Truth owners (source-of-truth files)
- Boundaries: `provenance/source-boundaries.md`, `AGENTS.md` (public-hover invariant src=qamus/kind=authored/lang=en).
- Per-token IR (already exists): `qamus/schemas/morphosyntax-token.schema.json` (+ contract
  `qamus/reports/morphosyntax-token-contract.md`); validator `tools/validate_morphosyntax_token_metadata.py`.
- Per-token parse representation: `qamus/schemas/parse-key.schema.json` (`canonical_parse_object`).
- Decision record: `qamus/schemas/linguistic-decision.schema.json` + `tools/validate_linguistic_decisions.py`.
- Gate policy: `qamus/reports/grammar-risk-policy.md` + `nahw/evals/grammar-decision-gates.json`
  (gates: auto_safe | two_vote_required | human_source_review_required | never_auto_resolve).
- Edge graph (accelerator): `tools/build_full_source_address_graph.py`,
  `tools/query_source_address_graph.py`, `qamus/indexes/current/source-address-full.jsonl`.
- Learner routing: `curriculum/tutor-runtime-routing.md` (issue→procedure table).

## Design thesis (to be validated by inspection+research digests)
The substrate is NOT new linguistics — it is a UNIFYING SPINE + a CHECKER over existing edges:
1. ParseUnit IR: document/source-unit → sentence/ayah/example-card → token[] (reuse morphosyntax-token
   model) → issue[] → explanation-route → evidence/gate/public_boundary. Composes existing schemas; does
   not duplicate them.
2. Grammar-issue object: the 12 required issue classes, each with source-address anchor + token/card edge
   + gate + route_to (into tutor-runtime-routing procedures).
3. Checker: given a CLAIMED analysis for an addressed token, return a verdict
   {correct | pending | contradicted | out_of_scope | needs_two_vote | needs_human_review} with matched
   issue classes + gate + route. Source-addressed only at first (out_of_scope for unanchored arbitrary text).
4. Validator/self-test enforcing the required FAIL conditions; source-addressed fixture w/ the regression set.
5. tutor-runtime-routing extended so parser diagnostics surface as learner feedback.

## Gates remaining
Input gate: PASS (valid northstar). Pre-flight: PASS (baseline captured, 2 pre-existing unrelated fails
classified). Next: inspection + deep-research digests → write plan packet → implement → Smoke B → commit.

## Smoke B (after implementation) — captured in worktree _worktrees/fusha-parser-substrate (branch parser-checker-substrate)
- `python3 tools/check_regressions.py` -> exit 1: **785 ok / 2 FAIL**. ok +9 (mine); FAIL count UNCHANGED at 2
  (same two RH-LIVE admin-preview manifest lines). ZERO new failures. ACCEPTANCE MET.
- `tools/fusha_check.py --self-test` -> green (12 regression units, all 12 issue classes, out_of_scope boundary, dry-run).
- `tools/validate_parser_check.py --self-test` -> green (12 good units clean; all 6 FAIL conditions reject).
- fixture validates: 12 units, 0 violations. CLI round-trip: verdicts {contradicted:8,unsafe_reasoning:1,out_of_scope:1,grounded:2}; live_writes=0.
- `tools/check_artifact_ergonomics.py` -> OK. py ast.parse + json load -> OK.
- Files: 2 modified (curriculum/tutor-runtime-routing.md, tools/check_regressions.py) + 7 new (2 schemas, 2 tools,
  fixture jsonl+meta, parser-checker-substrate.md). Worktree clean (no rollout files). Adversarial 2-lens review in flight.

## Closure
- Adversarial 2-lens review (correctness + boundary/licensing) returned 13 findings; ALL real ones fixed:
  2 blocking (validator/checker target-resolver drift -> shared target_token(); unmatched-target-never-grounded),
  2 major (passive-participle FP -> ACTIVE_RE; observed-echo leak -> _redact + validator scans observed/expected),
  + minors (LEAK_RE translation brands+win-paths; ma standalone; irregular plurals via must_surface; dedup key;
  crosswalk ayah-only guard; particle_function/suffix_referent gated; out_of_scope boundary precedence).
  4 new review-hardening self-test assertions added. Re-verified all green.
- Commit c503842 on branch parser-checker-substrate (9 files, +1382). Pushed to origin/parser-checker-substrate.
- check_regressions: 785 ok / 2 FAIL (the 2 pre-existing RH-LIVE lines, UNCHANGED). Zero new failures.
- AUDIT_COMPLETE: terminal verified closure. Worktree _worktrees/fusha-parser-substrate retained for iteration.
