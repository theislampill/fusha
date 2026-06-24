# Skill-installation report

The Fusha sarf/nahw engine is now **installable**, not just readable.

## Convention (investigated, not invented)
This machine uses the directory-per-skill convention: `~/.claude/skills/<name>/SKILL.md` (Claude) and
`~/.codex/skills/<name>/SKILL.md` (Codex), each a self-contained skill dir with YAML frontmatter
(`name`, `description`) + optional `procedures/`, `rules/`, etc. The canonical `sarf/SKILL.md` and `nahw/SKILL.md`
already carry valid frontmatter, so the installer copies their full trees into `fusha-sarf` / `fusha-nahw`.

## Artifacts
- `skills/sarf/`, `skills/nahw/` — installable wrappers + `manifest.json` (declares the tree to copy + invariants).
- `scripts/install_claude_skills.py` (dry-run supported), `scripts/install_codex_instructions.py`,
  `scripts/verify_skill_install.py`.
- `dist/codex/AGENTS.fusha.md` — a block to paste into a repo's `AGENTS.md`.
- `INSTALL.md` — install + usage (learning, entry authoring, hover authoring, corpus→Qamus, grammar audit).

## Dry-run + verification (passing)
- `install_claude_skills.py --dry-run` → would install `fusha-sarf`, `fusha-nahw` to `~/.claude/skills` (9 includes
  each: SKILL.md + procedures/rules/evals/curriculum/references/examples/drills). No files written in dry-run.
- `install_codex_instructions.py --dry-run` → same trees to `~/.codex/skills`; (re)writes `dist/codex/AGENTS.fusha.md`.
- `verify_skill_install.py` → **ALL CHECKS PASS**: manifests + wrappers + engine SKILL.md present; **sarf 13 /
  nahw 13 procedures accessible**; both SKILL.md **MCP-free**; regression fixtures accessible; **no raw-source/secret
  leak** in the skill trees.

## Verification contract (what the verifier guarantees)
skill files exist · procedures accessible (≥5 each) · regression fixtures accessible · no raw source leakage ·
**no MCP dependency in the skill itself** (the skill consults *available source adapters* only — `sources/README.md`).

## Acceptance
install docs exist ✓ · dry-run installer passes ✓ · verification script passes ✓ · README has user-facing +
agent-facing sections (`INSTALL.md` + `README.md` cart/engine section) ✓.
