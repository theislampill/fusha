---
name: fusha-sarf
description: Arabic morphology (sarf) engine — root/form/POS/clitic decisions before authoring or applying a Qamus gloss; hover-gloss authoring, Qamus entry/candidate generation, learner-drill generation. MCP-free; cooperates with fusha-nahw + the Qamus + the internal evidence ladder. Use whenever deciding an Arabic word-form, repairing a root/form, resolving a hover token, or turning a corpus into Qamus candidates.
---

# Fusha sarf engine (installable wrapper)

This is the installable entry point for the Fusha **sarf** (morphology) engine. The full operational skill is the
canonical `sarf/SKILL.md` + `sarf/procedures/` + `sarf/rules/` + `sarf/evals/` + `sarf/curriculum/` +
`sarf/references/` in this repo; the installer (`scripts/install_claude_skills.py` /
`scripts/install_codex_instructions.py`) copies that whole tree into the skill directory so the installed skill is
**self-contained**.

It can: pull/extend the existing Qamus, generate new Qamus entry candidates from a corpus, author hover glosses,
resolve the suffix/pronoun and homograph classes, decide when a token must stay **pending**, and teach ajami
learners. It is **MCP-free** — it consults *available source adapters* (`sources/README.md`) only as optional
internal evidence, never as a dependency, and **nothing external is ever public** (public gloss record stays
`{src:"qamus",kind:"authored",lang:"en"}`). QAC grammar screenshots and concept-map metadata are internal
routing/curriculum aids only; see `qamus/procedures/grammar-resource-usage.md`. Never use them as hover text
or public provenance. Sarf decisions must also preserve token composition for rich hovers: produce a compact
`parse_key` and scrubbed `qamus-grammar-v1` display classes for visible roots/forms/clitics, or defer with an
exact blocker. See `INSTALL.md` for install + usage; `nahw/SKILL.md` is its syntax partner.
