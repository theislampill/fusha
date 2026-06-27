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

## Dogfood finding: VN-00 noun family leakage

The VN-00 calibration tranche found populated noun hovers that had lexical
content but still failed sarf certification:

- plural hosts with possessive suffixes: `شَيَٰطِينِهِمْ`, `رَّبِّهِمْ`,
  `رَبَّكُمُ`, `رَبَّنَا`;
- dual/broken plural number loss: `ٱلْمَلَكَيْنِ`, `جَنَّٰتٍ`;
- proper/common or homograph collision: `إِبْلِيسَ`, `هَٰرُوتَ`, `مُلْك`,
  `مَلِك`, `مَٰلِكِ`;
- concept prose in the hover slot: `ٱلْعَٰلَمِينَ` and `ٱلشَّيَٰطِينُ`
  received explanatory entries instead of concise token contributions.

For these rows, a Qamus entry candidate or concept note is not a whole-token
hover. Record number, definiteness, suffix/possessive relation, and proper vs
common status first. If the row needs the concept note for curriculum, keep it
outside the public hover text.

## Dogfood finding: VN-05 body-part and life-stage noun richness

VN-05 exposed high-frequency noun rows whose visible English is populated but
not yet rich-certified:

- `ٱلْقُلُوبُ`, `قَلْبَهُۥ`, and related `قَلْب` rows must preserve article,
  plural/singular shape, and any possessor suffix before "heart" is trusted as
  a learner hover.
- `يَدَيْهِ`, `يَدَآ`, `يَدُ`, and `يَدٍۢ` mix singular, dual, idiomatic,
  and referent-sensitive hand/front/agency readings. Do not certify from one
  omnibus `يَد` gloss.
- `وُجُوهَهُمْ`, `وَجْهِهِۦ`, and other `وَجْه` rows need
  singular/plural/suffix and referent review before common, idiomatic, or
  divine-reference wording is chosen.
- `شَيْخًا`, `شُيُوخًا`, `شَيْبًۭا`, and `شِيبًا` distinguish person nouns,
  plural people nouns, and abstract/grey-hair state nouns. Slash glosses are
  not rich certification.

Article detection must be precise. A visible `ٱل`/`ال` article is different
from tanwin, case, or contextual definiteness. If the issue is state/case
without an article, use a state/case blocker rather than
`article_definiteness_requires_rich_segments`.
