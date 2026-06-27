# Dogfood Sarf Remediation Drills

These drills use real Qamus dogfood failure shapes. They are Qamus-authored teaching prompts; they do not copy
external source wording.

## A. Finite Verb, Not Dictionary Infinitive

For each token, state: root, form, aspect/tense, voice, person/number/gender, suffix if any, and a token-shaped
English contribution.

| token | required observations | reject |
|---|---|---|
| `يَسْأَلُكَ` | Form I imperfect active 3ms + object `كَ` = you | `to ask, question`; `ask` with hidden suffix |
| `جَادَلُوكَ` | finite verb + plural subject marker + object `كَ` | `to argue` |
| `فَأَهْلَكْنَاهُمْ` | `فَ` component, Form IV perfect, `نا` subject, `هم` object; not applyable without gates | host-only destroy gloss |

Answer standard: the initial imperfect prefix is morphology, not a public lexical "he" when an explicit following
subject controls the contextual English. The attached object must be visible in the explanation.

## B. Article, Host, And False Splits

Segment the written token, then say what is morphology evidence versus whole-token certification.

| token | segmentation | certification rule |
|---|---|---|
| `وَالشَّجَرُ` | `وَ` + `ال` + host noun | display evidence only until function/case gate clears |
| `ٱلسُّفَهَاءُ` | one article + host noun | never `the + the foolish ones` |
| `بِسَلَامٍ` | bāʾ + host noun | host-only "peace" fails |

## C. Root Recovery

Recover the hidden radical and state why `norm()` is not enough.

| surface | issue |
|---|---|
| `قَالَ` | hollow root; alif represents a weak radical |
| `خَفَّت` | doubled root; shadda hides a repeated radical |
| `يَسْأَلُ` | hamza remains root evidence |

Pass only when the learner can name the morphology evidence and route uncertainty to pending instead of guessing.
