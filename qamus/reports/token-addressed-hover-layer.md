<!-- HISTORICAL: point-in-time record. Current canonical scoreboard: token-irab-polysemy-report.md + hover-gloss-terminal-scoreboard.md (current) -->

> **⚠ HISTORICAL** — point-in-time record; numbers below reflect when this landed. Current state: **token-irab-polysemy-report.md + hover-gloss-terminal-scoreboard.md (current)**.

# Token-addressed hover override layer (B6)

The surface-key TSV applies **one gloss per `norm_strict` key** to every matching token. That cannot represent a
homograph whose distinct readings share a key — لَمْ "did not" vs لِمَ "why" both key to `لم`. The token-addressed
layer fixes this: a per-token decision keyed by **`quran:S:A:W`** that overrides the surface-key pass for that
exact token.

## Precedence (backwards-compatible)
**token decision > surface-key TSV > pending.** The surface-key TSV remains the fallback; nothing else changes.

## Where it lives
- Schema: [`qamus/schemas/hover-token-decision.schema.json`](../schemas/hover-token-decision.schema.json).
- Exporter (read-only): [`tools/export_token_hover_decisions.py`](../../tools/export_token_hover_decisions.py).
- Validator (fail-closed, public-leak gate): [`tools/validate_token_hover_decisions.py`](../../tools/validate_token_hover_decisions.py).
- Runtime artifact (gitignored): `qamus-service/ref/fusha-hover-token-decisions.jsonl` (one decision per line).
- Renderer wiring: `qamus_wbw/expand.py` loads it as the **highest-precedence pass**, exempt from the homograph
  denylist + QAC drop (the per-token decision *is* the authority). The artifact `words` map is already keyed by
  loc, so `build.py` needs no change. Committed mirror: `qamus/candidates/qamus_2092/token_hover_decisions_batch_001.*`.

## Why it is safe
- The disambiguator is the **vocalized surface already in the artifact** — لَمْ vs لِمَ are different surfaces; only
  `norm_strict` collapsed them. The exporter assigns a gloss only when the surface unambiguously selects a reading;
  **same-surface polysemy** (وَمَا "and not"/"and what", bare إِنْ "if"/lightened-emphatic, لَمَّا "when"/"not yet")
  is left pending for per-token iʿrāb.
- Public record stays `{src:"qamus",kind:"authored",lang:"en"}`. `internal_provenance` may cite QAC/Tanzil/Tafsir-MCP; the
  validator rejects any external name in the public gloss text.

## Live result (B6 + B6A applied)
- **363 token decisions** applied: did not (112), who/whoever (159 incl. proclitics), or (65), mother (7), why (3),
  from (4), … . Coverage **80.68% → 81.41%** (+363 occ, **~0 changed, −0 removed**), validate PASS, health 200.
- **Precedence verified live**: لَمْ @ 46:11:13 → "did not"; لِمَ @ 61:5:6 → "why"; أُمّ @ 3:7:10 → "mother" — same
  `norm_strict` key `لم`/`ام`, **different per-token glosses**. The surface-key collision is resolved.
- Rollback: remove/empty the token JSONL + `rebuild.sh` (the layer is a no-op when the file is absent); artifact
  `wbw-lookup.prev.json`.

## What it unlocks
The function-word hard-tail that was a permanent surface-key blocker (لَمْ/لِمَ، مَن/مِن، إِنْ/إِنَّ، أَمْ/أُمّ) is
now resolvable per-token. Remaining blockers are genuine same-surface polysemy → per-token iʿrāb (the next tier).
