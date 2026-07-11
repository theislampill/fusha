# Continuous integration (public GitHub Actions)

ARCHITECTURAL COMMITMENT (T9A, Shadow Flywheel Activation Program): every change to
this repository is verified remotely, in **clean public mode**, with no access to any
private production overlay. Production-only scanner behavior is exercised exclusively
through the synthetic fixtures already embedded in the regression harness (fresh
subprocesses; see the T2.1 ambient-isolation block in `tools/check_regressions.py`).

## Workflows

### `pr-gate.yml` — every pull request
Fast, fail-closed verification of the exact classes the program treats as
non-negotiable:

| step | command | what it proves |
|---|---|---|
| strict dataset integrity | `tools/validate_current_qamus_dataset.py` | the committed 2,092-entry public dataset + indexes accept (fail-closed) |
| schema validation | `--self-test` of `validate_canonical_hover_payload_table.py`, `build_canonical_hover_payload_table.py`, `compile_canonical_hover_whitelist_packet.py`, `report_g8_adoption_packet.py` | payload/binding/exception schemas and the compiler contract |
| public/private boundary | `tools/validate_public_private_boundary.py --self-test` | boundary objects reject private-shaped rows |
| changed-artifact + manifest checks | `tools/validate_claude_ai_pack_drift.py`, `tools/validate_artifact_freshness.py`, `tools/validate_canonical_paths.py`, `tools/validate_index_integrity.py` | pack-member drift, artifact freshness/retirement, stale canonical paths, index referential integrity |
| regression harness | `tools/check_regressions.py` (complete) | the full regression harness including source-hash, manifest-hash, leak-lint, and T8 hash-durability gates — measured 2m42s at adoption, so the "fast subset" requirement is satisfied by running everything |

### `full-gate.yml` — merge to `main`, daily schedule, manual dispatch
Runs the **complete** harness `python tools/check_regressions.py` and requires the
literal final line `ALL REGRESSION CHECKS PASS` (exit code enforced as well). The
ok-count is printed into the job log and the full log is uploaded as an artifact.
The accepted count at adoption of this workflow was **1060 ok / 0 FAIL**; later
counts are expected to grow and each growth must be explained by the commit that
introduced it (see `impl-records` acceptance records in the operator workspace).

## Boundary rules (binding)

- No workflow may reference, fetch, mount, or require the private production overlay.
  The overlay is discovered explicitly only (`FUSHA_LEAK_LOCAL` or an explicit path
  argument); CI sets neither, so every CI run is public-mode by construction, and the
  workflows assert both variables are empty before running gates.
- No workflow may write to the repository, publish artifacts consumed by any
  production system, or hold credentials for the operator infrastructure.
  `permissions: contents: read` is pinned in every workflow.
- CI results are evidence, not adoption: a green run never authorizes deployment of
  the canonical compiler (ADR-003 G8 adoption remains an explicit owner decision).
