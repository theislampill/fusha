# Procedure — referent / context guard

**Invoke when:** the gloss could depend on WHO/WHAT the verse is about, or a multi-sense root needs context.

**Checks:**
1. **Referent guard** ([`../rules/referent-guard-rules.json`](../rules/referent-guard-rules.json)): do not carry
   a divine-Name sense onto a human attribute (حَلِيمٌ of Ibrāhīm = "forbearing", not a Name); a Prophet's name
   onto a common adjective (صَٰلِحًا = "righteous"); a proper-noun sense onto a common noun, or vice-versa.
2. **Divine attribute vs exclusive Name:** adjectival attributes shared by creation (سَمِيع "All-Hearing",
   غَفُور "Most Forgiving") are safe adjectival glosses; a Name that also reads as a common noun in some āyāt
   (ٱلْعَزِيز ↔ ʿAzīz of Egypt; ٱلْحَقّ ↔ "the truth") → two_vote/pending.
3. **Contronyms / multi-sense roots:** the object/construction fixes the sense (يَقْدِرُ in a rizq context with
   يَبْسُط = "restricts"; أَتَى by object).

**Output:** the context-correct gloss, or pending(referent_sensitive / multi_sense_root).

**Forbidden:** a Name/Prophet/proper-noun sense on a common word (or vice-versa) without context certifying it.

**Gate:** referent-sensitive / multi-sense → two_vote ([`grammar-risk-gate.md`](grammar-risk-gate.md)).
