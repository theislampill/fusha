# qamustypingfin closure state

AUDIT_START

Goal: audit and backfill qamustyping4 findings into learner-facing curriculum,
sarf/nahw curricula, sarf/nahw drills, README surfaces, and validators; then
commit/push/merge/install only after evidence is green.

Boundaries:

- no live Qamus mutation;
- no server mutation;
- no runtime/deploy file import;
- no external gloss copying;
- no public provenance leakage;
- stage explicit repo paths only;
- do not stage unrelated bulk Qamus rollout dumps.

Plan packet:

- qamustypingfin local planning packet outside this public repo:
  `00-index-and-audit.md`
- `01-curriculum-drill-backfill-plan.md`
- `02-sarf-nahw-backfill-plan.md`
- `03-release-merge-install-plan.md`
- `qamustypingfin-ledger.json`

Smoke A:

- `python tools/validate_qamustyping4_acceptance.py --self-test`: green
- `python tools/validate_sarf_nahw_curriculum_drills_readmes.py --self-test`: green
- `python tools/validate_parser_claims.py --self-test`: green
- `python tools/validate_source_artifact_ledger.py --self-test`: green

Implemented:

- central curriculum qamustyping4 all-qword regression drill expansion;
- central curriculum README qamustyping4 routing note;
- dogfood remediation and tutor routing rows for all-qword, vocalization,
  hidden finite-verb pieces, derivative/plural pieces, proper-name/no-root, and
  function clusters;
- sarf curriculum/drill qamustyping4 visible morphology backfill;
- nahw curriculum/drill qamustyping4 function/preposition/visual-closure
  backfill;
- two answer-key rows for qamustyping4 derivative and function-cluster drills;
- validator update so the sarf/nahw curriculum/drill surfaces must retain a
  qamustyping4 marker.

ANDON: stale branch-stack marker

Status: closed
Class: generated-artifact-mismatch / stale-doc-validator
Blocker: `validate_sarf_nahw_curriculum_drills_readmes.py` still required the
old branch-stack commit marker `8fcad75` in `README.md`.
Failing check: `python tools/validate_sarf_nahw_curriculum_drills_readmes.py --self-test`
Owner/source: validator + root README capability contract.
Next concrete action taken: changed the validator to require the durable
`qamustyping4` capability marker instead of an old branch-tip list.

5 Whys:

1. Why did the check fail? The README no longer named the old branch-tip SHA.
2. Why was the SHA absent? The README now describes the capability stack rather
   than preserving a stale "none merged to main" branch list.
3. Why was the validator tied to a SHA? It was built for a previous backprop
   lane where the branch tip was the freshness marker.
4. Why is that unsafe now? After qamustyping4, a stale commit marker is less
   useful than the actual capability marker future agents need to find.
5. What prevents recurrence? The validator checks for `qamustyping4`, and the
   qamustyping4 acceptance validator checks the detailed docs/ledger/fixtures.

Smoke B:

- `python tools/validate_qamustyping4_acceptance.py --self-test`: green
- `python tools/validate_sarf_nahw_curriculum_drills_readmes.py --self-test`: green
- `python tools/validate_drill_keys.py --self-test`: green
- `python tools/validate_parser_claims.py --self-test`: green
- `python tools/validate_source_artifact_ledger.py --self-test`: green
- `python scripts/build_claude_ai_project_pack.py`: green
- `python tools/validate_claude_ai_pack_drift.py`: green
- `python tools/check_artifact_ergonomics.py ...`: green
- `python tools/check_regressions.py`: green
- `git diff --check`: green

Terminal finding states:

- curriculum backfill: changed, verified.
- sarf backfill: changed, verified.
- nahw backfill: changed, verified.
- README backfill: changed, verified.
- validator backfill: changed, verified.
- old branch backprop merge: deferred; branch is stale and not used.
- live Qamus deployment/readback: deferred; executor-owned.

AUDIT_VERIFY

AUDIT_COMPLETE

Pre-commit closure status:

- qamustypingfin backfill plans: done in the local planning packet.
- repo backfill: changed and verified.
- staged surface: explicit current-thread Fusha/qamustyping/curriculum/sarf/nahw
  paths only.
- stale `sarf-nahw-curriculum-drills-readme-backprop` branch: treated as
  historical evidence only; no merge or cherry-pick.
- unrelated `qamus/candidates/qamus_2092` and `qamus/reports/closure-2092`
  dumps: not staged.
- release gates remaining after this audit record: commit, push, fast-forward
  main if safe, install Codex skills, and hand off executor steer.
