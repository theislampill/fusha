# Build-tooling — sarf morphology via Tafsir MCP (maintainer evidence, NOT a skill dependency)

> This is **completion/build tooling**, not part of the sarf skill contract. The `sarf/SKILL.md` skill is
> self-contained — it cooperates with `nahw/` and the Qamus and uses the internal evidence ladder (Qamus entry →
> QAC → source-photo → heuristic). It does **not** call or depend on any external MCP. The maintainer uses the
> Tafsir MCP **here** as one extra internal witness while authoring/verifying glosses and entries for
> qamus.dawah.wiki and `/fusha/qamus/`. Nothing the MCP returns ships publicly.

**When the maintainer uses it:** resolving the sarf of a **Qur'anic** token (root/POS/wazn/form I–X/voice/
number/gender/derived-vs-jāmid/weak-letter) when QAC + the Qamus entry leave the form/voice unsettled.

**How:** `analyze_word(surah, ayah, word_no, aspects=["meaning","irab","sarf","statistics"])` via
[`tools/analyze_tafsir_mcp_word.py`](../../../tools/analyze_tafsir_mcp_word.py) (direct HTTP, cached, source-hashed);
extract structured fields with [`tools/mcp_to_language_state.py`](../../../tools/mcp_to_language_state.py).

**Guards the MCP provides while authoring (it confirms; it never overrides the Qamus entry, and never ships):**
- MCP says **noun** → don't author a verb gloss; MCP says **verb** → don't author a noun gloss.
- MCP says **passive** (مبني للمجهول) → don't author an active gloss (and vice-versa).
- MCP **form** (II/IV/VIII/X) disagrees with the gloss's implied form → keep pending (the نَزَّلَ II vs نَزَلَ I lesson).
- MCP shows an **attached pronoun/suffix** → the gloss reflects it or stays pending.
- **QAC vs MCP disagree on root/POS → do not auto-export**; route to the key-aware 2-vote / pending.

**Provenance:** an MCP-assisted decision records `internal_provenance.informed_by += ["tafsir-mcp"]` (internal
only). The public hover record stays `{src:"qamus",kind:"authored",lang:"en"}`. MCP prose is never copied into a gloss.

**Test:** [`../evals/sarf_cases.jsonl`](../evals/sarf_cases.jsonl) + [`../evals/morphology-eval.jsonl`](../evals/morphology-eval.jsonl);
cache integrity [`tools/validate_tafsir_mcp_cache.py`](../../../tools/validate_tafsir_mcp_cache.py).
