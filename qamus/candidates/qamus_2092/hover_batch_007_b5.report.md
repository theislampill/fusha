# Batch-5 (B5) — MCP-aware noun + verb sweep (APPLIED LIVE)

Fifth production sweep, and the first **MCP-aware** one: the 80 verb candidates were pre-enriched with Tafsir MCP
morphology (form/voice/person) before authoring. Same four-gate pipeline (key-probe → author → key-aware 2-vote),
with the MCP morphology shown to author+verifiers as confirm-don't-copy evidence.

## Result
- **230 candidates → 190 certified (61 MCP-backed), 40 rejected.** tsv **744 → 934 lines**, backup `*.bak-b5`.
- Rebuild: **coverage 78.78% → 79.93%** (matched 39,312 → 39,887, **+575 occ, ~0 changed, −0 removed**),
  validate PASS, health 200, smoke OK. Light screenshot verified.

## Certified (190) — examples
Verbs with MCP-confirmed morphology (they fight you · he worships · he breaks a promise · they seek · we follow ·
he found · go forth · came to you), case-variant nouns (wrongdoing, angels, women, the night, their plot, the
Holy [Spirit]), participles/adjectives (returning ones, the ignorant ones, more rightly guided, most kind), and
stable particle composites (and that they · so today · O Noah).

## Rejected (40) — gate still biting
- **form_voice_collision**: سخر, يسبحون, يخلقون (form/voice mixed under one key).
- **referent_sensitive**: حملته, اتخذت (pronoun referent shifts the sense).
- **lemma_collision**: أولو and others.
Recorded as forbidden transitions.

## Cumulative (B2–B5)
72.14 → 75.28 → 77.31 → 78.78 → **79.93%** — **+716 glosses, +3,891 occ, −0 removed**. Per-batch gain
+1,571 → +1,013 → +732 → +575 (diminishing as the homograph-dense tail deepens). nouns 81.39%, verbs 79.78%.
Mirrors: `hover_batch_007_b5.*` + `tafsir_mcp_hover_batch_001.*`; rollback `*.bak-b5`.
