# Tafsir MCP-backed hover batch 001 (APPLIED LIVE, inside B5)

The first hover batch whose glosses were **grammar-confirmed by the Tafsir MCP** (internal evidence). 80 verb
candidates from the B5 pending tier were pre-enriched with `analyze_word` morphology (form I–X, voice, person/
number) before authoring; the author + key-aware 2-vote then used that morphology to write precise finite glosses.
**61 of these MCP-backed candidates certified** and are live (the rest hit form/voice/referent collisions the gate
rejected).

## How MCP was used (build tool, not skill dependency, never public)
1. for each verb candidate's example token, `fetch_ayah` → locate the word → `analyze_word(aspects=["sarf","irab",
   "meaning"])` (direct HTTP, cached + source-hashed);
2. `mcp_to_language_state.py` extracted POS / verb-form / voice / person-number / case;
3. the morphology was shown to the author + both verifiers as **MORPH_EVIDENCE (confirm, don't copy)**;
4. a gloss that contradicted the MCP voice/form/person → `gloss_ok=false` (rejected).

Examples (MORPH confirmed): يُقَٰتِلُونَكُمْ "they fight you" (Form III, active, pl); يُخْلِفَ "he breaks (a
promise)" (Form IV, active); يَبْغُونَ "they seek" (active, rafʿ); يَعْبُدُ "he worships" (Form I, active).

## Provenance (hard boundary held)
Public records carry ONLY `{src:"qamus", kind:"authored", lang:"en"}`. The MCP morphology lives in
`internal_provenance.mcp` with `informed_by:["qac","quran-text","tafsir-mcp"]` — **never shipped, never copied**.
No Tafsir MCP / Quran.com / QAC text appears in any public gloss.

## Result
- **61 MCP-backed glosses live** (subset of the 190-gloss B5 apply). Coverage contribution counted within B5
  (78.78% → 79.93%, +575 occ, −0 removed). Mirrors: `tafsir_mcp_hover_batch_001.{jsonl,provenance.jsonl}`.
- Rollback: `fusha-hover-decisions.tsv.bak-b5` + `wbw-lookup.prev.json`.
- Lane proof: the MCP is now a working internal evidence rung for the hard verb tail — see
  `qamus/reports/tafsir-mcp-integration-report.md`.
