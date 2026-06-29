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

## D. RICH-CERT Morphology Gate

For each rich-cert row, decide whether the sarf state is proven or only previewed.

| state | learner action | reject |
|---|---|---|
| `pending` | name the missing sarf evidence or component-only blocker | "the English looks fine" |
| `preview_only` | use segment rows for study, but do not call it certified | "renderer metadata means live-ready" |
| `token_only_override` | keep the exact address and require owner/two-vote gates | surface-family propagation |

Examples: `يَسْأَلُكَ`, `فَأَهْلَكْنَاهُمْ`, `وَٱلشَّجَرُ`, and `بِبَدْرٍ` all teach useful
pieces, but none becomes family-wide or live-applyable from rich metadata alone.

## E. Visible Number And Derivative Shape

For each token, name the host, the visible number/derivative marker, and the display class that should teach it.

| token | required observations | reject |
|---|---|---|
| `بُرْهَٰنَانِ` | noun host plus visible dual ending; morphline says dual | one plain noun span with no dual note |
| `قاعدون` | participial/adjectival host plus sound masculine plural ending | gloss "sit" or "sitting" with no plural proof |
| `مُّطَاعٍۢ` | passive participle / ṣifa shape; derivative prefix belongs in the color layer | infinitive "to obey"; uncolored host-only span |
| `يُحْيِي` | imperfect prefix `يُ` plus lexical Form IV stem | single verb span that hides the prefix |
| `ٱلْغَٰلِبُونَ` | article + participial/adjectival host + plural ending | article or plural ending disappears |

Answer standard: role-aware color is instruction, not decoration. If the learner cannot see the dual/plural ending,
derivative prefix, or imperfect prefix in the hover breakdown, the row is still a rich-renderer backfill item.

## F. Source Text Before Sarf

Do not segment a Qurʾān example row until the displayed Arabic is deterministically sourced.

| defect | sarf action |
|---|---|
| lost hamza seat or maddah | block as `quran_display_text_mismatch`; refresh canonical display before morphology |
| missing diacritics on the cited word | block as `quran_display_text_mismatch`; do not infer morphology from a damaged display |
| selected card text differs from the source-backed example | block as `source_card_alignment_mismatch`; do not certify a hover on the wrong span |
| entry page groups display forms as separate senses without source support | block as `sense_alignment_mismatch`; repair the entry/sense graph before rich hover |

This is a sarf gate because broken display text can erase the very evidence used for root, pattern, number, voice,
or clitic decisions.
