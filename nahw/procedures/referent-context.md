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

## Dogfood finding: VN-00 referent and concept-prose guards

VN-00 reinforced that a populated hover can be semantically interesting and
still fail the token hover contract:

- `ٱلْجَنَّةَ` may be Garden/Paradise by context, but the garden/jinn/madness
  collision stays exact-address gated.
- `إِلَٰهٌ` / `إِلَٰهَ` are common nouns in no-god constructions; do not inherit
  the Allah proper-name entry.
- `ٱلْأَنْهَٰرُ` should not expose contextual phrase prose such as "in
  Paradise" unless the public hover is intentionally phrase-level and
  source-addressed.
- `ٱلْعَٰلَمِينَ` should not carry a concept paragraph in the hover slot.

Use referent context to select a concise token contribution or a precise
pending reason; put broader teaching notes in curriculum, not in the hover.

## Dogfood finding: VN-02 name/common and title context

VN-02 reinforced that proper-name context is a nahw gate, not merely sarf:

- `صَالِحًا` in a deed/action context is common/adjectival; in a prophet
  narrative it can be the name Ṣāliḥ. The exact āyah must decide.
- `يُحْيِي` is a finite verb in context even though a nearby name family
  `يَحْيَى` exists. POS and referent must agree before entry linkage.
- `عَادَ` as a verb must not inherit `عَاد` the people. Harakāt plus clause
  role matter.
- `ٱلْمَسِيحُ` is a title with article/case behavior; the hover may say "the
  Messiah", but the rich layer must show the title token rather than hiding it
  inside another proper-name entry.

When the context proof is missing, use `pending(referent_sensitive)` or
`human_review_required`; do not choose the more familiar name.

## Dogfood finding: VN-03 group and scripture referents

VN-03 added group/title referent guards:

- `هُود` rows can point to Jewish ethnonym forms or Prophet Hūd; context and
  source address decide.
- `وَدّ` / `وُدّ` rows can be a named object/person or common love; do not
  let one reading propagate.
- Scripture/book surfaces such as `زَبُورًا`, `زُبَر`, `صُحُفًا`, and
  `ٱلصُّحُفُ` vary between title, common plural, chunks, scrolls, and records.
  The hover needs exact context, not only a book-family entry.
- Collective and occupational nouns (`ٱلرُّومُ`, `قُرَيْشٍ`, `قِسِّيسِينَ`,
  `ٱلْأَحْبَارِ`) require number/class metadata before rich certification.

If the referent class is not certified, route to `human_review_required` rather
than a familiar title/group string.

## Dogfood finding: VN-05 body-part and root-family referent guards

VN-05 added another referent-sensitive cluster:

- `يَد` rows can mean physical hand, front/before (`بين يديه`), agency,
  idiom, or a sensitive divine-reference context. Number/suffix evidence is
  necessary but not sufficient; context chooses the actual hover.
- `وَجْه` rows can be face, direction, purpose/pleasure, time-of-day idiom, or
  a divine-reference construction. Omnibus hover text listing all possibilities
  is not a context decision.
- `ر ج ل` rows can be man/men, leg/feet, foot-soldier/on-foot usage, or a
  component-only noun inside a larger written token.

These rows stay `needs_nahw_review` or `needs_renderer_segments` until the
referent/construction is certified at the exact source address. Do not let a
safe-looking English lemma turn into parse-family propagation.
