# Dogfood Nahw Remediation Drills

These drills train the context/function failures repeatedly exposed by Qamus particle dogfood and rich-hover
metadata review.

## A. `مَا` And `وَمَا`

For each prompt, answer with function, not a fixed English gloss.

1. `وَمَا` is one written token. What are its grammar pieces?
   - Expected: wāw plus `ما`; `ما` function must be decided by context.
   - Reject: "always and what" or "always and not."
2. List four possible `ما` functions.
   - Expected: negative, relative, interrogative, maṣdariyyah; other accepted context functions may include
     laysa-like or preventive/kāffah.
3. If the clause frame is missing, what is the correct state?
   - Expected: pending with exact `ma_function_uncertified`-style reason.

## B. Preposition + Host

Explain the contribution of the attached preposition.

| token | required answer shape |
|---|---|
| `بِسَلَامٍ` | bāʾ + host noun; the relation must appear in gloss/explanation |
| `بِبَدْرٍ` | bāʾ + place-name host; locative/prepositional contribution cannot disappear |
| `لِتُضَيِّقُوا` | lām function plus governed verb/mood review |

## C. Token Contribution vs Adjacent Context

For each prompt, distinguish what the written token itself contributes from what the surrounding phrase supplies.

| item | required answer shape |
|---|---|
| `يَسْأَلُكَ النَّاسُ` | `يَسْأَلُكَ` contributes "ask you"; the following `النَّاسُ` supplies the subject "the people" |
| contextual hover says "they ask you" | accepted only if the subject source is recorded; do not read "they" as an attached pronoun inside `يَسْأَلُكَ` |
| rich preview row has phrase gloss and token gloss | both must be shown: contextual phrase gloss plus token contribution gloss |

Reject any answer that gets fluent English by hiding the source of the English subject, object, governor,
attachment, or pronoun referent.

## D. Hard Function Frames

For each, state why two independent checks may be required.

| item | reason |
|---|---|
| `إِلَّا` | exception frame, case, negative/positive environment |
| vocative `يَا أَيُّهَا` | addressee frame split across words |
| oath `وَ` | wāw may behave preposition-like and govern jarr |
| causal/result `فَ` | may govern mood or connect clause relation |

Pass only when the learner names the governor, governed item, or pending reason. Readable English without the
grammar reason fails the drill.

## E. RICH-CERT Nahw Gate

For each candidate, state the hidden function or relation that still blocks certification.

| example | nahw question | safe state |
|---|---|---|
| `وَمَا` | what does the wāw do, and which `ما` function applies? | pending until context is proven |
| `لِمَا` | what does lām govern, and what is `ما` doing? | two-vote required |
| `إِلَّا` | what is excepted, from what, and under which polarity/case frame? | two-vote required |
| `وَٱلشَّجَرُ` | is the wāw just coordination in this list, and is the case/role certified? | component-only pending |
| `بِبَدْرٍ` | what relation does bāʾ add to the place-name host? | exact-address token-only |

Do not mark a row rich-certified when the English is readable but the particle function, governor, attachment,
case/mood, or referent is still unresolved.

## F. Learner Explanation Versus Process Prose

A public hover explanation should teach the Arabic pieces and their relation. It should not explain the deployment
or evidence workflow.

| bad explanation shape | why it fails | repair |
|---|---|---|
| "the hover is authored from Qamus data and keeps internal evidence out of the public payload" | process/source-boundary prose is not a grammar lesson | explain the token pieces and their nahw relation |
| "public rollout still needs authorization" | admin gate, not learner-facing Arabic | keep gate text in reports/admin inspector only |
| "renderer metadata says this is safe" | renderer support is not grammar reasoning | state the particle function, governor, attachment, or pending reason |

Pass only when the final sentence says what the Arabic contributes: for example, "فَ links the clause", "بِ governs
the following noun", or "the following explicit noun supplies the subject."

## G. Source Text, Card Coverage, And Function Frames

Some RH-LIVE misses were not new grammar rules but failed routing discipline.

| issue | nahw consequence | safe state |
|---|---|---|
| display text lost hamza, maddah, diacritics, or word boundaries | case/mood/function evidence may be wrong | `quran_display_text_mismatch` before grammar certification |
| entry page shows a visible example card but report denominator excludes it | coverage claim hides a learner-visible flat card | card-level `blocked` or `partially_live`, not tranche complete |
| `إِنْ ... لَسَٰحِرَٰنِ` | particle function depends on the following lām/predicate frame | lightened `إِنَّ` only after phrase-level iʿrāb confirms the following emphatic lām; otherwise `pending`, not conditional/negation by surface alone |
| `كُلُّ شَيْءٍ قَدِيرٌ` | noun/adjective relation and agreement are the lesson | quantifier, noun, and adjective each need role/color and phrase relation |
| `وَقَدْ` | wāw relation plus qad function | explain "while/already" from the frame; do not add process prose |
