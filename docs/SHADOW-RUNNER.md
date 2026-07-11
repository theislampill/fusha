# Shadow compiler runner (T9B)

ARCHITECTURAL COMMITMENT: `tools/run_shadow_compile.py` operates the canonical hover
compiler **in shadow mode only** — it compiles from pinned, recorded inputs, compares
against the deployed baseline whitelist, and writes private immutable run records. It
never replaces, feeds, mutates, or shadow-writes the public whitelist; never touches
request handling; never changes a database; never exposes placeholder append content
publicly. Shadow evidence is an input to a later explicit owner adoption decision
(ADR-003 G8), not a substitute for it.

## Invocation

```
python tools/run_shadow_compile.py --config <external-config.json>
python tools/run_shadow_compile.py --self-test
```

The config lives **outside this repository** (operator-private): the deployed-whitelist
path, records directory, optional pinned `expected_source_head`, and the optional
explicit leak-overlay path all arrive via the config. Nothing production-specific is
committed here, and the overlay is never discovered implicitly (explicit-only loader
semantics, T2.1).

## Per-run behavior

1. Construct compiler-input rows from the accepted crosswalk (harness-G1 construction;
   live-content parity for locations shared with the deployed baseline; synthetic
   carrier preview, counted `pending`, for modeled-only locations).
2. Build, then **compile twice** — the two packet hashes must match (in-run
   reproducibility proof) — then run the G8 adoption reporter against the baseline.
3. Write `run-<UTC>/record.json` (sha256-chained to the previous record; mode 0400)
   with: fusha commit, compiler version, input identities and hashes, schema versions,
   live-whitelist hash, packet hash, start/end time, and the full count set
   (no_op, append, live-only, modify, conflict, blocked, leak-false-block,
   build-level carrier conflicts). Append one summary line to `shadow-ledger.jsonl`.
4. Evaluate the alert classes (below) against the previous ledger row and the
   operator-maintained `expected-changes.jsonl`; on any alert write `ALERT-<UTC>.json`
   and exit 1.
5. Retention: full row-level diffs kept for the most recent `keep_rowdiff_runs` runs;
   summaries kept forever; every `snapshot_every`-th record copied to `snapshots/`.

## Alert classes

`reproducibility_failure` · `packet_hash_drift` (identical inputs, different packet) ·
`unexpected_modify` · `unexpected_conflict_blocked` · `leak_false_block` ·
`no_op_decrease` · `live_only_increase` (unexplained by a recorded content change) ·
`schema_mismatch` · `source_head_mismatch` · `binding_disappearance`.

Known append / live-only queue rows never page — they are tracked work queues
(T10/T11). Only unexplained count or identity changes alert. A deployed-baseline
change is *explained* by appending a row naming the new whitelist sha256 to
`expected-changes.jsonl`; crosswalk/input changes are explained by the repo commit
itself (the record carries the head).

## Verification

`--self-test` (also run by the regression harness as the `T9B shadow runner self-test`
check) proves every alert class fires on its violation and stays silent on a clean
steady-state run, plus an end-to-end synthetic micro-pipeline (construction → build →
double compile → G8 classification) using temp-dir fixtures only.
