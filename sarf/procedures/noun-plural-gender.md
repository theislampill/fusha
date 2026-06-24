# Procedure — noun: plural / gender / role

**Invoke when:** the surface is a noun/adjective/participle/maṣdar/proper-noun.

**Input:** surface, root, QAC POS, optional Qamus entry (gender, forms, senses).

**Checks:**
1. **Role/shape:** maṣdar → nominal "the act of …" (ذِكْر "remembrance", never "he remembered"); ism fāʿil →
   agent ("believer"); ism mafʿūl → patient ("created"); a مُـ participle splits active/passive by the penult
   vowel ([`../references/masdar-participle-notes.md`](../references/masdar-participle-notes.md)).
2. **Plural:** sound (ـُونَ/ـِينَ/ـَاتٌ) is morphology, not the root; broken plural shares the root not the
   surface (كِتَاب→كُتُب) — match by lemma/entry plural field ([`../rules/root-pattern-risk-rules.json`](../rules/root-pattern-risk-rules.json)).
3. **Gender:** use the entry's gender (data, not a guess) for agreement/participle choice.
4. **Proper vs common / divine‑Name vs attribute:** referent guard (صَٰلِحًا "righteous" ≠ Prophet Ṣāliḥ;
   ٱلْحَقّ as divine Name vs "the truth"). Divine *attributes* (سَمِيع "All‑Hearing", غَفُور "Most Forgiving")
   are safe **adjectival** glosses; an exclusive **Name** that also reads as a common noun (ٱلْعَزِيز ↔ ʿAzīz of
   Egypt) → two‑vote/pending.

**Output:** nominal/adjectival gloss; never a "to …" verb gloss on a noun (رَسُولًا ≠ "to send").

**Forbidden:** verb gloss on a noun; surface‑key gloss when the `norm_strict` key mixes word/POS (أُمَّة↔أُمّهُ,
مُلْك↔مَلِك, البِرّ↔البَرّ).

**Test:** `examples/qamus-regressions.jsonl`; `tools/check_regressions.py` key‑collision checks.
