# Installing the Fusha sarf/nahw engine

Fusha is the **engine** (Arabic morphology + syntax intelligence). The Qamus is the **cart** (the lexicon it
pulls). This installs the engine as a skill for Claude or Codex, or you can use the repo directly.

## Install for Claude
Claude Code reads skills from `~/.claude/skills/<name>/SKILL.md`. The installer copies the full, self-contained
sarf and nahw engine trees:

```bash
python scripts/install_claude_skills.py --dry-run     # preview (no writes)
python scripts/install_claude_skills.py               # install to ~/.claude/skills/fusha-sarf, fusha-nahw
python scripts/install_claude_skills.py --target /custom/skills/dir
python scripts/verify_skill_install.py --dir ~/.claude/skills/fusha-sarf   # verify an installed skill
```

After install, the skills appear as `fusha-sarf` and `fusha-nahw` (procedures, rules, evals, curriculum included).

## Use with Codex
Codex reads skills from `~/.codex/skills/<name>/SKILL.md` and instructions from `AGENTS.md`:

```bash
python scripts/install_codex_instructions.py --dry-run
python scripts/install_codex_instructions.py          # install + (re)write dist/codex/AGENTS.fusha.md
```

Then include `dist/codex/AGENTS.fusha.md` in your repo's `AGENTS.md` (copy the block between the
`<!-- BEGIN/END fusha-engine -->` markers) so Codex consults the engine before any Arabic gloss/entry work.

## Use the repo directly (no install)
Read `sarf/SKILL.md` and `nahw/SKILL.md`; open the procedure named by the gate; run the tools under `tools/`.

## What you can do with it
- **Learn Fusha (ajami → fluency):** `curriculum/` (12-level roadmap, qamus/quran/hadith paths, drills,
  placement test) + `curriculum/qamus-driven-fluency-engine.md`.
- **Author Qamus entries from a corpus:** `tools/corpus_to_qamus_candidates.py` (Nawawī40-proven, 0 live writes)
  + `sarf/procedures/qamus-entry-authoring.md` + `nahw/procedures/qamus-entry-authoring.md`.
- **Author hover glosses:** `sarf/procedures/hover-application.md`, the four-gate pipeline, the token-addressed +
  suffix/pronoun layers (`qamus/reports/token-addressed-hover-layer.md`, `suffix-pronoun-hover-report.md`).
- **Generate learner drills from live Qamus/hover state:** `curriculum/drills/` + the proofing matrices.
- **Audit grammar safely:** `tools/run_grammar_evals.py` + `tools/grade_grammar_reasoning.py` (the GrammarProblems
  gate: correct answer AND correct reasoning, else reject).
- **Repair entries from source photos:** the `tools/source_photo_*` pipeline (rescue-first, not retake-first).

## Invariants (always)
MCP-free skills (external sources are optional internal evidence via `sources/README.md`, never a dependency,
never public); public gloss record stays `{src:"qamus",kind:"authored",lang:"en"}`; no raw source/media/secret committed;
Qurʾān text unaltered; when uncertain, stay pending with a precise blocker.
