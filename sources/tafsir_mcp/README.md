# Tafsir MCP — internal Qur'an grammar/morphology evidence layer

`https://mcp.tafsir.net/mcp` (server "Tafsir MCP" v1.27.1, protocol 2025-06-18, **no auth**) is an **internal
evidence source** for sarf/nahw decisions over Qur'anic examples. It is **never** a public data source — nothing
it returns ships to the live hover artifact, which stays `{src:"qamus", kind:"authored"}`.

> **Decoupled from the skills.** This is a **maintainer/build tool**. The `sarf/SKILL.md` and `nahw/SKILL.md`
> skills are self-contained — they cooperate with each other + the Qamus + the internal evidence ladder, and do
> **not** reference or depend on this MCP (a regression check enforces both SKILL.md files are MCP-free). The MCP
> is used *here* to help author/verify glosses + entries for qamus.dawah.wiki and `/fusha/qamus/` and to construct
> the skills' content — not as a runtime requirement of the skills.

## How we reach it
The Claude tool registry may or may not surface the connector's tools in a given runtime. Independent of that,
the connector tools here speak MCP streamable-HTTP (JSON-RPC 2.0) **directly** over `tools/call`, via
[`tools/tafsir_mcp_client.py`](../../tools/tafsir_mcp_client.py). Probe with
[`tools/tafsir_mcp_probe.py`](../../tools/tafsir_mcp_probe.py) (reports AVAILABLE + tool list, or the exact blocker).

## Tools we use (of 17 the server exposes)
- `analyze_word(surah, ayah, word_no, aspects=["meaning","irab","sarf","statistics","qeraat"])` → per-word
  morphology (`sarf`: POS, wazn, form I–X, voice, number, weak/hamza, مادة), syntax (`irab`: case/mood, role,
  governing particle, iḍāfa, hidden-verb estimate), `root`, `frequency`, `rasm_note`.
- `fetch_ayah(surah, ayah, include=["irab","gharib","tajweed",...])` → Uthmani text + āyah-level iʿrāb
  (`irab` = إعراب القرآن الكريم — الآيات) + gharīb.
- also available: `find_root_occurrences`, `get_root_stats`, `get_qeraat_variants`, `search_quran_text`, …

## Boundaries (hard)
- Raw cache (`cache/*.json`) is **gitignored**; only tiny redacted **examples/** are committed.
- Every cache record is **source-hashed** (`validate_tafsir_mcp_cache.py` fails closed on mismatch).
- Every MCP-backed decision records `internal_provenance.informed_by` including `tafsir-mcp` (internal only).
- **No public hover output may mention Tafsir MCP / Quran.com / QAC / Tanzil.** Public = `src:"qamus"`.
- MCP is **evidence, not authority**: if QAC and MCP disagree, do not auto-export; the GrammarProblems gate +
  key-aware 2-vote still apply. A correct-looking answer with no reasoning stays pending.

## Files
```
sources/tafsir_mcp/
  README.md            (this)
  schema.json          (cache record schema)
  examples/            (tiny redacted samples — committed)
  cache/               (.gitkeep; raw records gitignored)
  procedures/          (build-tooling docs: how the maintainer uses MCP — NOT skill procedures)
  evals/               (MCP extractor fixtures — outside sarf/ and nahw/ so the skills stay MCP-free)
tools/
  tafsir_mcp_client.py        (shared JSON-RPC client)
  tafsir_mcp_probe.py         (availability / exact blocker)
  fetch_tafsir_mcp_ayah.py    (ayah + irab, cached)
  analyze_tafsir_mcp_word.py  (word morphology+irab, cached)
  build_tafsir_mcp_cache.py   (batch + source-hash)
  validate_tafsir_mcp_cache.py(integrity + leak gate)
  mcp_to_language_state.py    (Arabic sarf/irab prose -> structured token-state evidence)
```
Lane status + acceptance: [`qamus/reports/tafsir-mcp-integration-report.md`](../../qamus/reports/tafsir-mcp-integration-report.md).
