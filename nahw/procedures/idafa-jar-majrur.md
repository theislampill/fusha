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

## Dogfood finding: possessed majrūr hosts are two-layer tokens

The preposition/oath dogfood batch found hovers that recognized the host noun
but dropped the relation that made it majrūr, or dropped the possessor attached
to that host.

Handle these as layered grammar:

1. The preposition or oath particle governs the host as jar-majrūr.
2. The host may also carry iḍāfa or an attached possessive pronoun.
3. The PP or oath phrase still needs attachment/function review before
   parse-family propagation.

Examples:

- `بِذُنُوبِهِمْ`: bā' relation + "sins" + "their"; host-only `Sin.` fails.
- `بِذُنُوبِكُم`: bā' relation + "sins" + "your"; suffix-pending alone is too
  vague.
- `بِرُوحِ`: bā' relation + referent-sensitive host; route referent if unclear.
- `بِبَابِلَ`: bā' relation + place name; host-only `Babylon` fails.
- `وَطُورِ` / `وَهَٰذَا`: oath/coordinating frame must be named before the host
  text can propagate.

If the relation is clear, the learner hover must preserve it. If it is not
clear, use `preposition_role_uncertified`, `oath_function_uncertified`,
`pp_attachment_uncertified`, or `referent_unresolved` rather than a smooth
host-only gloss.
