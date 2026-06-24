# Tafsir MCP integration report (TM1)

## Lane status: **AVAILABLE** (direct HTTP)
Probed live via [`tools/tafsir_mcp_probe.py`](../../tools/tafsir_mcp_probe.py):

| field | value |
|---|---|
| endpoint | `https://mcp.tafsir.net/mcp` |
| server | Tafsir MCP **v1.27.1** |
| protocol | 2025-06-18 (streamable-HTTP JSON-RPC 2.0) |
| auth | **none required** |
| tools | 17 — incl. `fetch_ayah`, `analyze_word`, `find_root_occurrences`, `get_root_stats`, `get_qeraat_variants`, `list_sources_for_ayah`, `search_quran_text` |

**Runtime note (honest):** the connector is enabled in the chat client, but its tools were **not surfaced in the
agent's native tool registry** this session (ToolSearch/ListMcpResources/registry all empty for it). That does not
block us: the connector tools here speak MCP **directly over HTTP** via
[`tools/tafsir_mcp_client.py`](../../tools/tafsir_mcp_client.py), independent of the Claude tool registry. Owner
chose the direct-HTTP path.

## What the API actually provides
- `analyze_word(s,a,w, aspects=[meaning,irab,sarf,statistics,qeraat])` → per-word `sarf` (POS, wazn, Form I–X,
  voice, number/person, مادة, إعلال/مهموز), `irab` (case/mood, role, governing particle, iḍāfa, hidden-verb
  estimate), `root`, `frequency`, `rasm_note`.
- `fetch_ayah(s,a, include=[irab,gharib,tajweed,qiraat_ayah,tadabbur])` → Uthmani text + āyah-level iʿrāb + gharīb.
- The prompt's `irab` / `markaz_irab` are **source identifiers** within the iʿrāb layer, not separate tools; we use
  the `irab` include / aspect.

## Acceptance — all met
- ✅ probe confirms MCP available (tool list captured).
- ✅ fetched, cached (source-hashed), and converted to fixtures:
  - `1:1` full āyah with `irab` (+ gharīb) — `sources/tafsir_mcp/examples/001_001.fetch_ayah.sample.json`;
  - `analyze_word` 1:1:1 (بسم) — `…/001_001_001.analyze_word.sample.json`;
  - problematic **particle** 2:6:1 إنّ ("حرف توكيد ونصب");
  - **verb-form** 2:3:2 يؤمنون ("فعل مضارع … من باب أَفْعَلَ" = Form IV active 3pl);
  - **noun/gender/plural** 2:5:8 المفلحون (plural noun).
- ✅ converted to decision fixtures —
  [`sources/tafsir_mcp/evals/sarf_cases.jsonl`](../../sources/tafsir_mcp/evals/sarf_cases.jsonl) (4/4 pass),
  [`sources/tafsir_mcp/evals/irab_cases.jsonl`](../../sources/tafsir_mcp/evals/irab_cases.jsonl) (3/3 pass) via
  [`tools/mcp_to_language_state.py`](../../tools/mcp_to_language_state.py).
- ✅ cache validator passes (`tools/validate_tafsir_mcp_cache.py` — schema + source-hash + no-public-leak).
- ✅ leakage scan clean — no Tafsir MCP / external provenance in any public artifact; public hover stays
  `{src:"qamus",kind:"authored"}`; raw cache gitignored (examples redacted).

## Extractor note (fixed during integration)
`mcp_to_language_state.py` first mislabelled the noun بسم as a verb because the **wazn name `(فِعْلٌ)`** appears in
its `sarf`. Fixed: POS is now read from the **leading classification token** (after the first `:`), not anywhere in
the prose. All fixtures pass.

## How it plugs into the program (a BUILD tool, not a skill dependency)
**Decoupled from the skills by design.** The `sarf/SKILL.md` and `nahw/SKILL.md` skills stay self-contained —
they cooperate with each other + the Qamus + the internal evidence ladder (Qamus entry → QAC → source-photo →
heuristic) and the GrammarProblems gate, and do **not** reference or depend on any external MCP
(`check_regressions.py` asserts both SKILL.md files are MCP-free). The Tafsir MCP is a **maintainer/completion
tool**: it helps author and verify glosses + entries for qamus.dawah.wiki and `/fusha/qamus/`, and helped
construct the skills' content — but it is never a runtime requirement of the skills.
- Build-tooling docs: [`sources/tafsir_mcp/procedures/sarf-morphology-via-mcp.md`](../../sources/tafsir_mcp/procedures/sarf-morphology-via-mcp.md)
  + [`nahw-irab-via-mcp.md`](../../sources/tafsir_mcp/procedures/nahw-irab-via-mcp.md).
- Used as internal evidence in the **B5 MCP-aware batch** to back grammar-risk verb/noun glosses (see
  `qamus/candidates/qamus_2092/tafsir_mcp_hover_batch_001.report.md`); MCP-assisted decisions carry
  `internal_provenance.informed_by += ["tafsir-mcp"]` only.
