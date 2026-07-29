# Golden commands — one canonical command per operation

Continuation-machinery lane (handoff steer section 16). **Only commands that
exist in this repo are listed as runnable; missing operations are GAP-marked**
so nobody invents an invocation. Every command is run from the repo root with
the repo's Python 3. Unless stated otherwise: mutation scope = *repo working
tree only* (this repo NEVER mutates anything live), and exit expectation =
exit 0 with the stated terminal line.

| # | Operation | Canonical command |
|---|-----------|-------------------|
| 1 | Environment / repo verify | `git rev-parse HEAD && python tools/check_regressions.py` |
| 2 | Full regression gate | `python tools/check_regressions.py` |
| 3 | Universe build | `python tools/build_example_ayah_universe.py` |
| 4 | p007 reverse universe (+ geometry wave) | `python tools/build_p007_geometry_wave.py` |
| 5 | Entry reverse index (pilot) | `python tools/build_p007_li_pilot.py` |
| 6 | Particle classification (matrix) | `python tools/build_particle_occurrence_matrix.py` |
| 7 | Evidence ingestion (Tafsir MCP) | `python tools/fetch_tafsir_mcp_ayah.py --help` (per-āyah fetch; cache validated by `python tools/validate_tafsir_mcp_cache.py`) |
| 8 | Two-vote assembly | `python tools/build_bulk_two_vote_requests.py` |
| 9 | Two-vote validation | `python tools/validate_two_vote_artifacts.py` |
| 10 | Certify / revoke typed facts | `python tools/certify_typed_fact.py --validate <store-dir>`; counts: `--count <store-dir>`; engine self-test: `--self-test` |
| 11 | Projection compile (typed-fact plane) | `python tools/fd_compiler.py` |
| 12 | Parity (particle projection contract) | `python tools/validate_particle_projection_parity.py` |
| 13 | Parity (appearance grain) | `python tools/validate_appearance_parity.py` |
| 14 | Reverse trace check (pilot) | `python tools/validate_p007_pilot.py` |
| 15 | p007 tally recompute | `python tools/validate_p007_universe.py` |
| 16 | Fixtures (hazard + invariants) | `python -m unittest tools.test_hazard_fixtures tools.test_entry_transclusion_invariants -q` |
| 17 | VN readiness | `python tools/build_vn_readiness_v2.py` then `python tools/validate_vn_readiness_v2.py` |
| 18 | Website payload validation | `python tools/validate_website_payload.py` |
| 19 | Website payload generation | **GAP** — samples under `qamus/examples/website-payloads/` are hand-assembled per `docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`; no committed generator yet |
| 20 | Programme state refresh | `python tools/build_current_state.py` (freshness: `--check`) |
| 21 | P/V/N rollout map | `python tools/build_pvn_rollout_map.py` (freshness: `--check`; invariants: `--self-test`) |
| 22 | Artifact ergonomics | `python tools/check_artifact_ergonomics.py` |
| 23 | Public-boundary scan | `python tools/scan_public_boundary.py` |
| 24 | Deploy-packet prep | **GAP / LOCKED — owner-gated.** No command exists in this repo by design; a deploy packet is proposed only in an owner window after strata-complete evidence + website-agent contract confirmation (see `docs/decision-ledger.md`) |

## Details per operation

1. **Environment / repo verify** — inputs: checkout. Outputs: HEAD sha +
   harness verdict. Exit: `ALL REGRESSION CHECKS PASS`. Report: stdout.
2. **check_regressions** — the only merge gate. Inputs: whole repo. Outputs:
   one `ok/FAIL` line per check (1,100+). Mutation: none. Report: stdout;
   failures list at the end.
3. **Universe build** — inputs: `qamus/data/current/entries.jsonl`, appearance
   index, loc-surface index, particle membership. Outputs:
   `qamus/lattice/example-ayah-universe.jsonl` (+ `.occurrences.jsonl`,
   `.meta.json`). Exit: row/occurrence tallies matching the meta. Validated by
   `tools/validate_example_universe.py` + `tools/test_example_ayah_universe.py`.
4. **p007 reverse universe** — inputs: universe, matrix, classification,
   geometry store, pilot. Outputs: `qamus/lattice/p007-reverse-universe.jsonl`
   + meta (11 `P007_*` state tallies). Recompute check: command 15.
5. **Entry reverse index (pilot)** — outputs the pilot artifact set under
   `qamus/examples/p007-li-pilot/` incl. `entry-reverse-index.json` and
   `reverse-trace.json`. Corpus-wide reverse edges live at
   `qamus/lattice/entry-occurrence-edges.jsonl`.
6. **Particle classification** — inputs: universe + particle membership.
   Outputs: `qamus/lattice/particle-occurrence-matrix.jsonl` + meta.
   Terminology guard: rows are **candidate particle-entry/sense links from the
   discovery classifier**, never "particle occurrences".
7. **Evidence ingestion** — network: Tafsir MCP only, bounded (≤3 retries),
   surface-matched. Outputs: evidence refs (e.g.
   `qamus/lattice/p007-mcp-evidence-refs.jsonl`); verbatim text stays in the
   evidence plane. Mutation: evidence files only.
8. **Two-vote assembly** — outputs sanitized reviewer worklists/request
   packets. Reviewer-B independence is procedural: B sees the sanitized
   worklist, never A's votes.
9. **Two-vote validation** — fails any `two_vote` claim lacking two
   reconstructible independent review records agreeing on conclusion AND
   reason. Exit 0 = bundle consumable by the certifier.
10. **Certify / revoke** — the ONLY path to `certified`. Inputs: typed facts +
    evidence bundles + (for two-vote rungs) validated artifacts. Outputs:
    append-only hash-chained `events.jsonl` + updated statuses. `--validate`
    re-walks a store and fails on chain gaps/tampering. Stores:
    `qamus/certification/…`, `qamus/examples/p007-li-pilot/certification/`.
11. **Projection compile** — compiles certified facts to projection rows
    (candidate plane; live bridge remains the old flat path until owner
    window). Tests: `tools/test_fd_compiler.py`.
12–13. **Parity** — recompute projection hashes across all appearances of each
    occurrence; identical modulo the closed 4-key presentation whitelist.
    Exit 0 = no forks. Reports: stdout + validator output files where written.
14. **Reverse trace** — verifies entry → occurrence → appearance → projection
    chain closure on the pilot. 15. **Tally recompute** — never quote p007
    numbers from prose; quote this validator.
16. **Fixtures** — red-first defect fixtures (يَٰٓأَيُّهَا word-offset family,
    truncated iʿrāb source, dagger-alef letter-count, loc-aliasing…) +
    the 12 entry-transclusion invariants. Exit: unittest `OK`.
17. **VN readiness** — builds/validates the VN readiness matrix
    (`vn-readiness-matrix.json`, VNPROP namespace preserved separately).
18. **Website payload validation** — validates
    `qamus.website_projection_payload.v1` samples against the handoff
    contract; parity is a renderer obligation.
20–21. **State refresh** — regenerate `docs/current-state.yaml` and
    `qamus/reports/pvn-rollout-map.jsonl`; both `--check` modes are wired into
    the harness so stale committed state fails CI.
22. **Ergonomics** — pretty JSON/JSONL+meta rules; gated by the harness.
23. **Public-boundary scan** — leak scan for private paths/sources; run before
    committing anything derived from private material.

## Rules

- If an operation is not in this table, there is no golden command for it —
  check the packet or ask, do not improvise.
- Never chain a GAP row into automation.
- When you add a real command for a GAP row, update this file and wire a
  check into `tools/check_regressions.py` in the same PR.
