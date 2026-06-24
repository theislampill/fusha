# Procedure — Tafsir MCP morphology (internal evidence)

**Invoke when:** resolving the sarf of a **Qur'anic** token (root/POS/wazn/form/voice/number/gender/derived-vs-
jāmid/weak-letter) and you want an independent morphology witness beyond QAC + the Qamus entry.

**Input:** the token's `quran_loc` (S:A:W). Call `analyze_word(surah, ayah, word_no, aspects=["meaning","irab",
"sarf","statistics"])` via [`tools/analyze_tafsir_mcp_word.py`](../../tools/analyze_tafsir_mcp_word.py) (direct
HTTP; cached + source-hashed). Convert to structured fields with
[`tools/mcp_to_language_state.py`](../../tools/mcp_to_language_state.py).

**Evidence ladder (MCP sits beside QAC, never above the Qamus entry):**
1. Qamus entry root/sense — highest authority for OUR gloss.
2. QAC root/POS — internal evidence.
3. **Tafsir MCP `sarf`** — confirms POS, wazn/باب (Form I–X), voice (مبني للمعلوم/للمجهول), number/person
   (للغائبين…), مادة, weak/hamza behaviour (إعلال/مهموز), derived vs jāmid.
4. photographed source page (seeding only).
5. heuristic (`normalize_ar`) — never sufficient.

**Decision rules (the MCP guards):**
- If MCP says **noun**, do NOT export a verb gloss; if MCP says **verb**, do NOT export a noun gloss.
- If MCP says **passive** (مبني للمجهول), do NOT export an active gloss (and vice-versa).
- If MCP identifies an **attached pronoun/suffix**, the gloss must reflect it or stay pending.
- If MCP **form** (II/IV/VIII/X) disagrees with the gloss's implied form, stay pending (the نَزَّلَ II vs نَزَلَ I
  lesson — read the wazn before glossing).
- **If QAC and MCP disagree on root/POS, do NOT auto-export** — route to two-vote / pending.
- MCP is evidence, not authority: a gloss still needs the key-aware 2-vote and (for grammar-affecting calls) the
  GrammarProblems gate. MCP prose is **never copied** into the public gloss.

**Output:** the sarf decision object (see [`SKILL.md`](../SKILL.md) §3) with
`evidence.tafsir_mcp = {used:true, sarf_pos, verb_form, voice, number, root}` and
`internal_provenance.informed_by += ["tafsir-mcp"]`. Public hover record stays `{src:"qamus",kind:"authored"}`.

**Examples (real MCP `sarf`, internal):**
- `2:3:2` يؤمنون → "فعل مضارع للغائبين، مبني للمعلوم، رباعي مزيد … من باب أَفْعَلَ" ⇒ verb · Form IV · active ·
  3pl ⇒ safe finite gloss "they believe".
- `1:1:1` بسم → "اسم، مذكر، مفرد، جامد … من مادة (سمو)" ⇒ noun (the wazn name "(فِعْلٌ)" is a *pattern*, not a verb).
- `2:6:1` إنّ → "حرف توكيد ونصب" ⇒ particle (emphatic) — do not treat as the conditional إِنْ.

**Forbidden:** copying MCP text into a public gloss; exporting against an MCP POS/voice/form signal; treating MCP
as public authority (it is internal only).

**Test:** [`sarf/evals/tafsir_mcp_sarf_cases.jsonl`](../evals/tafsir_mcp_sarf_cases.jsonl) +
[`tafsir-mcp-morphology-eval.jsonl`](../evals/tafsir-mcp-morphology-eval.jsonl);
cache integrity `tools/validate_tafsir_mcp_cache.py`.

**Feeds:** /qamus/ entry authoring (form/voice/number for usage rows) · hover-gloss resolution (POS/voice guard) ·
ajami learners (a worked morphology breakdown per token).
