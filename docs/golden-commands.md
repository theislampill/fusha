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
| 18 | Website payload validation | `python tools/validate_website_payload.py --self-test` then `python tools/validate_website_payload.py` (full 11-sample validation) |
| 19 | Website payload generation | p007-derived samples: `python tools/build_p007_website_payloads.py --self-test` then `--check`. Hand-assembled samples (`ma_*`, `verb_*`, `noun_*`, `no_entry_link_*`, `unresolved_ma_*`, `multi_entry_*`) have no generator, but their public-eligibility/evidence posture has a committed deterministic repair path — never a hand edit — via command 33 |
| 20 | Programme state refresh | `python tools/build_current_state.py` (freshness: `--check`) |
| 21 | P/V/N rollout map | `python tools/build_pvn_rollout_map.py` (freshness: `--check`; invariants: `--self-test`) |
| 22 | Artifact ergonomics | `python tools/check_artifact_ergonomics.py` |
| 23 | Public-boundary scan | `python tools/scan_public_boundary.py` |
| 24 | Deploy-packet prep | **GAP / LOCKED — owner-gated.** No command exists in this repo by design; a deploy packet is proposed only in an owner window after strata-complete evidence + website-agent contract confirmation (see `docs/decision-ledger.md`) |
| 25 | Task-packet validation | `python tools/validate_task_packets.py` |
| 26 | Ṣarf eval banks (all-bank run) | `python tools/run_sarf_evals.py --all --strict` (one bank: `--bank <path>`; machine-readable: `--json`) |
| 27 | Ṣarf eval runner gates | `python tools/run_sarf_evals.py --self-test` then `python -m unittest tools.test_run_sarf_evals` |
| 28 | Eval-bank coverage report | `python tools/fusha_eval_coverage.py` (Ṣarf gate: `--strict-sarf`; all banks incl. Naḥw: `--strict`) |
| 29 | Naḥw eval banks (all-bank run) | `python tools/run_nahw_evals.py` (one bank: `--bank <name>`; machine-readable, exactly one JSON document: `--json`) |
| 30 | Naḥw behavioural + mutation gates | `python tools/test_nahw_behavioural_gates.py` |
| 31 | Naḥw rule-consumer self-tests | `python tools/fusha_nahw_particle_rules.py --self-test` · `python tools/fusha_nahw_context_rules.py --self-test` · `python tools/fusha_nahw_gate_rules.py --self-test` |
| 32 | Naḥw consumption inventory | `python tools/fusha_nahw_particle_rules.py --status` (context/gate: same flag) · gate divergences: `python tools/fusha_nahw_gate_rules.py --divergences` |
| 33 | Website evidence fail-closed migration | `python tools/migrate_website_evidence_fail_closed.py --self-test` then `--check` (freshness) then, only to apply a new red, `--apply`. Deterministically downgrades a payload whose evidence no longer resolves as certification authority to `certification.status: unresolved` / `plane: review_required`, `public_projection_eligible: false`, `provenance_class: illustrative-from-live`, recomputing hashes — never a hand edit |
| 34 | Website public-eligibility migration | `python tools/migrate_website_public_eligibility.py --self-test` then `--check` (freshness) then, only to apply a new red, `--apply`. Deterministically sets an explicit `public_projection_eligible: false` on an already non-authoritative payload, byte-preserving every other field and recomputing hashes |
| 35 | Website evidence resolution (read-only) | `python tools/website_evidence_resolver.py` — focused proof of the repository-evidence resolver `tools/validate_website_payload.py` consults; never mutates a payload |

## Details per operation

### 29–32 · Naḥw consumers and eval banks (Burst A2)

`python tools/run_nahw_evals.py` runs **6 execution groups over 7 physical eval artifacts / 314 rows**
(the `function-polysemy` group decides two artifacts: `particle-function-eval.jsonl` and
`irab-polysemy-eval.jsonl`). Group count and artifact count are different numbers and are never added
together.

What it reports, kept apart on purpose:

- **13 rows** earn behavioural credit — the whole of
  `public-boundary-scanner-eval.jsonl` (10 rows, consumer `tools/leak_sot.py:LEAK_RE.search`) and
  `largelexicon-function-collision-safety.jsonl` (3 rows, consumer
  `tools/fusha_context_parser.py:collision_status`). Those are the only two artifacts declared
  `implemented_and_consumed`.
- **21 rows** are quarantined (9 `state-machine` + 12 `hover-context`) under typed `QUARANTINE-BINDING`
  packet authority, whose row sets, properties, dispositions and packet ids are compared for exact equality
  in both directions and whose authorizing packets are validated against the canonical task-packet schema.
- the remaining rows are structurally checked only: 5 artifacts are declared `fixture_only`, and the
  unowned axes (`gloss_if_safe`, production key selection, the typed grammatical state, structured
  wrong-reason keys) are reported, never counted.
- `consumer-invocation events: 52` is a **mixed-denominator** count (identity + ablation + mutation +
  routing + scanner + homograph checks, omitting the hover base comparisons). It is not a row coverage
  figure and must not be compared with 314 or with 13.

`--json` emits exactly one JSON document and a matching exit code — a trailing prose line is a defect.
Coverage is registered in `tools/fusha_eval_coverage.py` only from the INVOKED runner result, and the
reporter validates that result against its OWN ownership allowlist and its OWN row counts, so a runner
that misreported a path, a denominator, a consumer or a disposition would be rejected outright rather
than believed.


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
18. **Website payload validation** — `--self-test` is the red-first suite
    (missing entry links, iʿrāb prose leak, hash fork, non-authoritative
    `public_projection_eligible`); the bare command validates all 11
    committed `qamus.website_projection_payload.v1` samples against the
    handoff contract, including evidence resolution (command 35); parity is a
    renderer obligation.
20–21. **State refresh** — regenerate `docs/current-state.yaml` and
    `qamus/reports/pvn-rollout-map.jsonl`; both `--check` modes are wired into
    the harness so stale committed state fails CI.
22. **Ergonomics** — pretty JSON/JSONL+meta rules; gated by the harness.
23. **Public-boundary scan** — leak scan for private paths/sources; run before
    committing anything derived from private material.
25. **Task-packet validation** — executable twin of
    `qamus/schemas/task-packet.schema.json` (`qamus.task_packet.v1`). Inputs:
    `qamus/task-packets/*.json` (or explicit paths; red-first `--self-test`).
    Named checks: packet shape, id collision, write-scope conflict,
    server-path leak (RM-09), canary classes, method-not-conclusion,
    non-deployment, self-containment. Mutation: none. Exit:
    `TASK PACKET VALIDATION PASS`; wired into `tools/check_regressions.py`.
26. **Ṣarf eval banks** — runs every artifact under `sarf/evals/` through the
    contract `sarf/eval-runner-contract.json`. Four banks (142 of 392 rows) are
    decided by a production consumer named per bank in the contract and
    call-counted by proxies the runner installs; the other 250 rows are
    read, labelled `documentary` / `candidate_no_consumer` and packetized, and
    are reported as uncovered. Object-form `cases[]` / `assertions[]` count as
    rows. `--strict` is a **disposition-completeness** gate, not a coverage
    claim. An unknown `--bank` fails closed. Mutation: none (read-only unless
    `--report PATH`). Coverage is reported per property (24 covered, 4 uncovered) and the
    candidate/projector/public boundary line reads `verified` only on a full
    run — a targeted `--bank` run renders it `not_checked`. Exit:
    `SARF EVAL RUNNER PASS`. Wired into `tools/check_regressions.py`.
27. **Ṣarf eval runner gates** — `--self-test` runs the synthetic red/green plus
    the consumer-mutation proofs; the unittest module adds the positive,
    negative, adversarial and mutation gates that make
    `implemented_and_consumed` a claim a broken consumer cannot survive. It also
    asserts that `sarf@2.1`–`@2.4` remain CANDIDATE.
28. **Eval-bank coverage** — read-only census of `nahw/evals/` + `sarf/evals/`
    in both forms, taking execution only from an invoked registered entrypoint
    and separating `declared_disposition` (what the contract says) from
    `has_behavioral_runner` (what the invoked run proved). Exit behaviour, as it
    stands today: **default** exits 0 (it fails only on a bank that is
    unreadable, empty or malformed); **`--strict-sarf`** is a
    disposition-completeness gate over `sarf/evals/` and is green;
    **`--strict`** exits 1 because 6 of the 25 discovered banks still have no
    registered runner at all — `governor-dependency-lattice`,
    `grammar-problems-phase3p25-mining`, `irab-right-answer-wrong-reason`,
    `suffix-pronoun-eval`, `vn00-aggressive-false-closure` and
    `vn00-public-visual-andon`. The seven Naḥw artifacts listed under 29–32 are
    **no longer runnerless**: `tools/run_nahw_evals.py` is registered as an
    invoked contract runner under its own result schema. Neither flag asserts
    behavioural coverage; of those seven artifacts only 2 (13 rows) earn it.
33. **Website evidence fail-closed migration** — the committed, deterministic
    repair path for a website payload whose cited `evidence_refs` no longer
    resolve (command 35) as `authoritative_for_certification`: it rewrites
    exactly the closed four-file manifest, byte-preserving every field except
    `certification.status`/`plane`, `public_projection_eligible`,
    `provenance_class`, and the recomputed `projection_hash` (+ every
    reverse-appearance hash). `--check` reports staleness only; `--apply`
    writes; `git diff` after `--apply` is the audit trail. Refuses (does not
    best-effort mutate) any target whose identity, occurrence id, or
    already-certified status has drifted from the pinned manifest.
34. **Website public-eligibility migration** — the committed, deterministic
    repair path for a payload that is already honestly non-authoritative
    (`candidate` / `unresolved` / `review_required`) but omits, nulls, or
    mis-types `public_projection_eligible`: it sets exactly that one field to
    explicit `false` on the closed four-file manifest, byte-preserving every
    other field and recomputing `projection_hash` (+ reverse-appearance
    hashes). Same `--check`/`--apply` shape and refusal discipline as 33.
35. **Website evidence resolution** — read-only; resolves one
    `projection.evidence_refs` string against the committed typed-fact
    certification stores, the candidate proof-particle contract, two-vote
    artifact bundles, `cert-event:` history, and `dawahwiki:` custody
    manifests, and reports a closed effective state (`certified`,
    `review_required`, `revoked`, `dependency_failed`, `candidate`,
    `review_verified`, `certified_support`, `custody_verified`,
    `contradictory`, `evidence_unresolved`, or `unsupported_scheme`) —
    never a copied status string. `tools/validate_website_payload.py`
    consults it; a certified payload's every evidence ref must resolve
    `authoritative_for_certification`, and every non-authoritative posture
    must set `public_projection_eligible` to explicit `false` (commands 18,
    33, 34).

## Rules

- If an operation is not in this table, there is no golden command for it —
  check the packet or ask, do not improvise.
- Never chain a GAP row into automation.
- When you add a real command for a GAP row, update this file and wire a
  check into `tools/check_regressions.py` in the same PR.
