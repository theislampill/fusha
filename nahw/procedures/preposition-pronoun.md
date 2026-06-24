# Procedure — preposition + pronoun (jar-majrūr wording)

**Invoke when:** surface is a preposition, or preposition+attached pronoun.

**Input:** surface, referent context.

**Checks:**
1. Render by referent: بِهِ "in it / in him / by it"; لَهُ "for him / belongs to him"; إِلَيْنَا "to us";
   فِيهِ "in it"; عَلَيْهِمْ "upon them"; بِإِذْنِهِ "by His permission" ([`../rules/preposition-pronoun-rules.json`](../rules/preposition-pronoun-rules.json)).
2. The attached pronoun (ـه/ـها/ـهم/ـكم/ـنا) changes wording, not the head sense, and never invents a stem.
3. **Hard guard:** إِلَيْنَا = إِلَى + نا (root أ‑ل‑ي), **NOT** root ل‑ي‑ن; a final ـًا is tanwīn‑alef
   (قُرْءَانًا), not the pronoun نا (`ends_tanwin_alef`).

**Output:** the phrase-role gloss; pending(referent_unresolved) if the referent is out of range.

**Forbidden:** glossing the preposition as a content word; reading إِلَيْنَا as ل‑ي‑ن; `norm()` certification.

**Test:** `examples/function-word-decisions.jsonl` (بِهِ, إِلَيْنَا, عَلَيْهِمْ, فِيهِ); regression إِلَيْنَا≠لين.
