# Particle hard-tail batch (particle_hover_batch_002_tafsir_mcp) — APPLIED LIVE

Completes the p001–p100 particle example āyāt. Audited every token in the 219 particle example āyāt; the safe
single-surface content tokens were authored (author + key-aware 2-vote), and the function-word homographs were
**confirmed as blockers by Tafsir MCP iʿrāb** (internal evidence).

## Result
- Particle-āyah audit: 219 āyāt · 3,245 tokens · pending 600 → **308** (90.51% resolved, was 81.51%).
- **311 safe-single content candidates → 289 certified, 22 rejected.** tsv 934 → 1,223, backup `*.bak-bpart`.
- Rebuild: **coverage 79.93% → 80.68%** (+373 occ, ~0 changed, **−0 removed**), validate PASS, health 200.

## What MCP did in this lane (build tool, internal, never public)
The 289 certified safe glosses were authored from understanding + 2-vote (single-surface content words — no MCP
needed). The Tafsir MCP `analyze_word`/`fetch_ayah(include=["irab"])` was used to **confirm the function-word
homograph BLOCKERS** so they are documented with evidence, not hand-waved:
- لَمْ → "حرف نفي وجزم" (negation) — key also carries لِمَ "why" (interrogative) → blocked.
- وَمَنْ → "اسم موصول" (relative "whoever") — key also carries وَمِنْ "from" (preposition) → blocked.
- وَإِن → "إنْ مخففة من الثقيلة" — key mixes conditional إِنْ and emphatic إِنَّ → blocked.

## Blockers (the honest floor for particle āyāt)
157 function-word homograph keys (لَمْ/لِمَ, وَإِن/وَإِنَّ, وَمَنْ/وَمِنْ, أَمْ/أُمّ, …) cannot take a single
live gloss because the live aid keys by `norm_strict`, which collapses their distinct functions. They are
forbidden transitions in the state graph (`query_language_state.py --split`) and listed in
[`../../reports/particles/particle-hover-audit.md`](../../reports/particles/particle-hover-audit.md). The other 35
pending are single-surface content tokens (occ 1) in the global authoring queue (B6+).

## Provenance
Public records carry ONLY `{src:"qamus",kind:"authored",lang:"en"}`. MCP iʿrāb stayed internal (used for blocker analysis,
never copied, never shipped). Mirror: `particle_hover_batch_002_tafsir_mcp.{jsonl,provenance.jsonl}`. Rollback:
`*.bak-bpart` + `wbw-lookup.prev.json`.
