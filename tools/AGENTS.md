# tools/ — agent stub

Builders, validators and the regression harness. Rules live in the root `AGENTS.md`;
canonical invocations in `../docs/golden-commands.md` (GAP-marked where no command exists).

- `check_regressions.py` is the only merge gate; new artifacts get red-first checks wired
  into it in the same PR.
- Builders are deterministic and regenerable (`--check` / `--self-test` where present);
  committed outputs must not hand-rot.
- stdlib-only; no network except the bounded Tafsir MCP evidence path; no live mutation, ever.
