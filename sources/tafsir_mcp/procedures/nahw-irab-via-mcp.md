# Build-tooling — nahw iʿrāb via Tafsir MCP (maintainer evidence, NOT a skill dependency)

> This is **completion/build tooling**, not part of the nahw skill contract. The `nahw/SKILL.md` skill is
> self-contained — it cooperates with `sarf/` and the Qamus and uses the internal evidence ladder + the
> GrammarProblems gate. It does **not** call or depend on any external MCP. The maintainer uses the Tafsir MCP
> **here** as one extra internal iʿrāb witness while authoring/verifying glosses and entries. Nothing the MCP
> returns ships publicly.

**When the maintainer uses it:** a Qur'anic token whose gloss depends on **syntax** — case/mood, governing
particle, iḍāfa, jar-majrūr, ḥāl/badal/khabar/mafʿūl, a hidden (محذوف) verb, or sentence attachment.

**How (direct HTTP, cached, source-hashed):**
- per-word: `analyze_word(..., aspects=["irab","sarf","meaning"])`
  ([`tools/analyze_tafsir_mcp_word.py`](../../../tools/analyze_tafsir_mcp_word.py));
- per-āyah: `fetch_ayah(surah, ayah, include=["irab"])` (إعراب القرآن الكريم — الآيات)
  ([`tools/fetch_tafsir_mcp_ayah.py`](../../../tools/fetch_tafsir_mcp_ayah.py));
- extract case/mood + role with [`tools/mcp_to_language_state.py`](../../../tools/mcp_to_language_state.py).

**Guards while authoring (the GrammarProblems reasoning gate still applies — MCP is not an exemption):**
- iʿrāb missing/contradictory → keep the token **pending** with a precise reason.
- A referent-sensitive role (pronoun whose مرجع shifts the sense) stays pending unless context fixes it.
- MCP iʿrāb is internal evidence, never public, never copied into a gloss.

**Provenance:** `internal_provenance.informed_by += ["tafsir-mcp"]` (internal only); public hover stays
`{src:"qamus",kind:"authored",lang:"en"}`.

**Test:** [`../evals/irab_cases.jsonl`](../evals/irab_cases.jsonl) + [`../evals/irab-eval.jsonl`](../evals/irab-eval.jsonl).
