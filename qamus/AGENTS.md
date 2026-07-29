# qamus/ — agent stub

Data, lattice, certification stores, reports and schemas for the Qamus plane.
Rules live in the root `AGENTS.md`; entry point `../START-HERE-FOR-CONTINUATION.md`.

- Everything here is **candidate/evidence/report** material — never a live surface.
- Certification stores (`certification/`, `examples/*/certification/`) are append-only,
  hash-chained; mutate them only through `tools/certify_typed_fact.py`.
- Row-record artifacts: JSONL + pretty `*.meta.json` sidecar naming the regenerating script
  (`tools/check_artifact_ergonomics.py` gates this).
- Tallies are quoted from validators (`tools/validate_p007_universe.py`, builder `--self-test`s),
  never from prose.
