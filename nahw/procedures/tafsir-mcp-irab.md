# Procedure — Tafsir MCP iʿrāb (internal evidence)

**Invoke when:** a Qur'anic token's correct gloss depends on **syntax** — case/mood, governing particle, iḍāfa,
jar-majrūr, ḥāl/badal/khabar/mafʿūl, a hidden (محذوف) verb, or sentence attachment — and you need an iʿrāb witness.

**Input:** the token's `quran_loc`. Two complementary calls (direct HTTP, cached, source-hashed):
- per-word: `analyze_word(..., aspects=["irab","sarf","meaning"])` → role + case/mood for that word
  ([`tools/analyze_tafsir_mcp_word.py`](../../tools/analyze_tafsir_mcp_word.py));
- per-āyah: `fetch_ayah(surah, ayah, include=["irab"])` → full iʿrāb (إعراب القرآن الكريم — الآيات)
  ([`tools/fetch_tafsir_mcp_ayah.py`](../../tools/fetch_tafsir_mcp_ayah.py)).
Extract structured signals (case/mood, role) with [`tools/mcp_to_language_state.py`](../../tools/mcp_to_language_state.py).

**Use iʿrāb to decide:** syntactic role (فاعل/مفعول/مبتدأ/خبر/نعت/بدل/حال/تمييز), case/mood (مرفوع/منصوب/مجرور/مجزوم),
governing particle, iḍāfa (مضاف / مضاف إليه), jar-majrūr attachment, and hidden-verb estimates (لفعل محذوف تقديره …).

**Decision rules (the gate stays on):**
- If iʿrāb reasoning is **missing or self-contradictory**, the token stays **pending** (precise reason).
- The **GrammarProblems gate remains active**: a grammar-affecting decision needs final-answer AND reasoning AND
  evidence-ladder AND two-vote (when required) — MCP evidence does **not** remove the reasoning check
  ([`grammar-risk-gate.md`](grammar-risk-gate.md), [`tools/grade_grammar_reasoning.py`](../../tools/grade_grammar_reasoning.py)).
- A referent-sensitive role (e.g. a pronoun whose خبر/مرجع shifts the sense) stays pending unless context fixes it.
- MCP iʿrāb is **internal evidence**, never public; never copied into a gloss.

**Output:** the nahw decision object with `evidence.tafsir_mcp = {used:true, case_mood, role, governing}` and
`internal_provenance.informed_by += ["tafsir-mcp"]`. Public hover stays `{src:"qamus",kind:"authored"}`.

**Examples (real MCP `irab`, internal):**
- `1:1:1` بسم → "الباء حرف جرّ … اسم مجرور … وهو مضاف … شبه الجملة في محل نصب مفعول به مقدم لفعل محذوف تقديره
  (أبتدئ)" ⇒ a jar-majrūr + iḍāfa + a hidden governing verb — the gloss must reflect "in the name of", not a
  standalone verb.
- `2:3:2` يؤمنون → "فعل مضارع مرفوع … ثبوت النون … واو الجماعة … فاعل" ⇒ indicative, the wāw is the subject ⇒ "they
  believe" is safe.

**Forbidden:** exporting a role/sense the iʿrāb contradicts; shipping when iʿrāb is absent; copying iʿrāb text;
exposing Tafsir MCP publicly.

**Test:** [`nahw/evals/tafsir_mcp_irab_cases.jsonl`](../evals/tafsir_mcp_irab_cases.jsonl) +
[`tafsir-mcp-irab-eval.jsonl`](../evals/tafsir-mcp-irab-eval.jsonl).

**Feeds:** /qamus/ entry authoring (usage-row syntax notes) · hover-gloss resolution (role/case guard) · ajami
learners (āyah-level iʿrāb walk-throughs).
