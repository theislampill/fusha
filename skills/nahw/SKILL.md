---
name: fusha-nahw
description: Arabic syntax (nahw) engine — particle/pronoun/case-mood/context decisions and the GrammarProblems reasoning gate, before authoring or applying a Qamus gloss. Decides what a token means in its sentence (or an honest pending). MCP-free; cooperates with fusha-sarf + the Qamus. Use whenever sarf alone cannot pick the sense, a particle is multi-function, or a gloss is lexically valid but contextually wrong.
---

# Fusha nahw engine (installable wrapper)

This is the installable entry point for the Fusha **nahw** (syntax) engine. The full operational skill is the
canonical `nahw/SKILL.md` + `nahw/procedures/` + `nahw/rules/` + `nahw/evals/` + `nahw/curriculum/` +
`nahw/references/` in this repo; the installer copies that whole tree into the skill directory so the installed
skill is **self-contained**.

It can: decide context-dependent senses, classify pronoun attachment (possessive vs subject/object), gate
grammar-affecting decisions on correct reasoning (not fluent-sounding answers), and keep a token pending with a
precise blocker when evidence is insufficient. It is **MCP-free** — it consults *available source adapters*
(`sources/README.md`) only as optional internal evidence, never as a dependency; **nothing external is ever
public**. Public hover records stay `{src:"qamus",kind:"authored",lang:"en"}`. QAC grammar screenshots and
concept-map metadata are internal routing/curriculum aids only; see `qamus/procedures/grammar-resource-usage.md`.
Never use them as hover text or public provenance. See `INSTALL.md` for install + usage; `sarf/SKILL.md` is
its morphology partner.
