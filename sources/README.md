# Evidence source adapters

The sarf/nahw skills are **self-contained and MCP-free** — they cooperate with each other + the Qamus + the
internal evidence ladder, and they **name no external service**. When extra evidence helps (Qurʾānic iʿrāb,
morphology, root/POS, verbatim text), it is reached through a **declarative adapter** here, never hard-wired into
the skill. Each adapter is optional; the skill works without any of them.

## Contract
- Manifest schema: [`source-adapter.schema.json`](source-adapter.schema.json). Each adapter declares its
  `evidence_role`, `access` (mcp/http/local/package, endpoint via ENV — no secret committed), `availability`,
  `ladder_rank`, and two hard invariants: `public_exposable: false` and `required_by_skills: false`.
- **No adapter outranks the Qamus entry** (ladder rank 1). Adapters are confirmation/triangulation, not authority.
- **Nothing an adapter returns is ever public.** Public hover/entry records stay `{src:"qamus",kind:"authored",lang:"en"}`;
  adapter use is recorded only in `internal_provenance.informed_by`.

## Registered adapters
| adapter | role | access | availability |
|---|---|---|---|
| [`tafsir_mcp`](tafsir_mcp/adapter.json) | iʿrāb, morphology, root/POS, qiraat, text | MCP (direct HTTP) | available |
| [`qac`](qac/adapter.json) | root, POS, morphology | package (server) | available |
| [`tanzil`](tanzil/adapter.json) | verbatim Uthmani text | http | available |
| [`quran_com`](quran_com/adapter.json) | wbw gloss (build-time comparison only) | http | optional |

## How the skills refer to this (generic, no service names)
> "For a Qurʾānic token, consult any **available source adapter** through the evidence ladder (Qamus entry → QAC →
> source-photo → adapters). If an iʿrāb/morphology adapter is available, use it as confirmation; if QAC and an
> adapter disagree, do not auto-export. Adapters are never required and never public."

This keeps the skills portable: a different deployment can register different adapters (or none) without changing
`sarf/SKILL.md` / `nahw/SKILL.md`.
