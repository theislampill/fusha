# Procedure — iḍāfa & jar-majrūr

**Invoke when:** the token heads/sits in a genitive construct or a preposition phrase.

**Checks:**
1. **Iḍāfa** ([`../references/idafa.md`](../references/idafa.md)): head loses tanwīn/ال; definiteness +
   relationship come from the second term (عِنْدَ ٱللَّهِ "in the sight of Allah", not bare "near"; بَيْتُ ٱللَّهِ
   is definite "the House of Allah"). A ẓarf (عِنْدَ/بَيْنَ/فَوْقَ/تَحْتَ) heads an iḍāfa of place/time — gloss the
   relation, not the adverb alone.
2. **Jar-majrūr** ([`jar-majrur.md` is `preposition-pronoun.md`]): gloss the phrase role; the genitive noun is
   "of …", governed by the preposition.

**Output:** the construct/phrase-level gloss (relationship + definiteness), or pending if the second term is
out of range.

**Forbidden:** glossing the bare head as indefinite when the construct is definite; asserting a relationship the
construct doesn't license.

**Gate:** ambiguous iḍāfa / jar-majrūr boundary → two_vote ([`../rules/irab-safety-gates.json`](../rules/irab-safety-gates.json)).
