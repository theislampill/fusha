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

## C. Hard Function Frames

For each, state why two independent checks may be required.

| item | reason |
|---|---|
| `إِلَّا` | exception frame, case, negative/positive environment |
| vocative `يَا أَيُّهَا` | addressee frame split across words |
| oath `وَ` | wāw may behave preposition-like and govern jarr |
| causal/result `فَ` | may govern mood or connect clause relation |

Pass only when the learner names the governor, governed item, or pending reason. Readable English without the
grammar reason fails the drill.

## D. RICH-CERT Nahw Gate

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
