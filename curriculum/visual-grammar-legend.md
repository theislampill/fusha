# Visual grammar legend (learner-facing colour + parse-key key)

A standalone, printable reference a learner can keep open while reading a rich-hover page.
Flywheeled with the D7 colour-key legend (2026-07-07). The **colours are grammar roles, not
provenance** — see [../docs/parser/qamus-grammar-v1-class-map.md](../docs/parser/qamus-grammar-v1-class-map.md)
and [dark-mode-accessibility-pedagogy.md](dark-mode-accessibility-pedagogy.md).

## 1. Colour legend (why each role gets its colour)

Colours are semantic anchors, not decoration — the point is that a learner can recall the grammar
rule from the visual memory. The public legend shows the swatch in the **exact colour the word is
painted in the current theme** (light-mode verb/noun render dark; dark-mode render pale) so the
chip always matches running text.

| Role (qg class) | Learner meaning | Why the cue |
|---|---|---|
| Verb (`qg-verb-stem`) | an action / state word carrying tense + agreement | the engine of the clause — find it first |
| Verb prefix / subject (`qg-verb-prefix`) | the letter marking who/when on the verb | person/tense lives on the edge of the verb |
| Noun (`qg-noun-stem`) | a person, thing, or idea | the participants in the clause |
| Adjective (`qg-adjective`) | a describing word agreeing with its noun | follows and matches its noun |
| Proper noun (`qg-proper-noun`) | a name (person, place, Book) | not translated by root; a label |
| Number (`qg-number`) | a counting word | agreement + case are special |
| Article (`qg-article`) | "the" (definiteness) | `ال` fused to the front of a noun |
| Preposition (`qg-preposition`) | a spatial/relational word (in, with, to) | governs the noun after it into the genitive |
| Conjunction (`qg-conjunction`) | a linker ("and", "then") | joins words/clauses; `و`/`ف`/`ثم` |
| Negation (`qg-negation`) | "not" / "never" | changes truth of the clause; nāfiya ≠ nāhiya |
| Relative (`qg-relative`) | "who / which / that" | heads a describing clause |
| Conditional (`qg-conditional`) | "if / when" | sets up a condition→result frame |
| Exception (`qg-exception`) | "except / only" | carves out from a set |
| Emphasis (`qg-emphasis`) | "indeed / truly" | strengthens the statement |
| Pronoun (`qg-pronoun`) | a stand-in for a person/thing | attached or standalone; carries person/number |

Accessibility rule: each swatch must clear WCAG contrast against the panel in **both** themes, or
carry a neutral border/ring so the chip is visible even when its fill is pale. Colour is never the
*only* channel — the label text always states the role in words.

## 2. Parse-key key (learner-facing abbreviations)

The `parse_key.summary` is compact learner ASCII — **never** an internal parser id, node id, or
parse-hash. Read it as:

| Token | Reads as |
|---|---|
| `V:I:PERF:ACT` | verb, Form I, perfect, active |
| `V:IV:IMPF:PASS` | verb, Form IV, imperfect, passive |
| `N:DEF:GEN` | noun, definite, genitive |
| `ADJ:INDEF:ACC` | adjective, indefinite, accusative |
| `P:bi` / `P:li` / `P:min` | preposition bi- / li- / min |
| `ART` | the article `ال` |
| `PRON:2MS` | pronoun, 2nd person masc. sing. |
| `PART:neg` / `PART:cond` / `PART:rel` | particle: negation / conditional / relative |

## 3. How to teach with it

1. Point at a coloured word; name the role from the colour; confirm from the label.
2. Read the token's own gloss (its contribution), then the phrase gloss (with neighbours).
3. For a function word, say *which* function fired here (this `ما` is relative, not negation).
4. If a colour is unreadable in your theme, that is a **bug to file**, not a thing to squint past —
   the legend must be legible in light and dark (D7 lesson).
