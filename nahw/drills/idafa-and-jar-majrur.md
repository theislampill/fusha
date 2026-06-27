# drills — iḍāfa (construct) & jār-majrūr (preposition + noun/pronoun)

Two construction types reshape the *wording* of a gloss, not just the head word. The hover
layer must produce the **combined** gloss, and must not let a clitic pronoun re-trigger a
wrong root match. This file is the lookup the disambiguator uses for both.

---

## 1. Iḍāfa — the construct chain (الْإِضَافَة)

A muḍāf (head) + muḍāf ilayh (possessor) forms one nominal unit: **"X of Y"**.

### How it changes the gloss

- The muḍāf **drops its tanwīn** and **drops its `ال`** (a noun with `ال` cannot be a muḍāf).
  → definiteness is a *parse signal*: tanwīn or `ال` on a noun ⇒ it is **not** the head of an
  iḍāfa, so do not chain it to the next word.
- The muḍāf ilayh is always **jarr** (genitive).
- The unit glosses as **"head of possessor"**: `كِتَابُ اللَّهِ` → 'the Book of Allah';
  `رَبِّ الْعَالَمِينَ` → 'Lord of the worlds'.

### Worked patterns

| surface | structure | combined gloss |
|---|---|---|
| `رَسُولُ اللَّهِ` | muḍāf `رَسُول` + muḍāf-ilayh `اللَّه` (jarr) | 'Messenger of Allah' |
| `يَوْمِ الدِّينِ` | `يَوْم` + `الدِّين` (jarr) | 'the Day of Judgment' |
| `أَهْلِ الْكِتَابِ` | `أَهْل` + `الْكِتَاب` | 'the People of the Book' |
| `بَيْنَ أَيْدِيهِمْ` | ẓarf `بَيْن` + `أَيْدِي` + clitic `هِمْ` | 'before them' (lit. between their hands) |

### Guard rails (do **not** mis-chain)

- **A muḍāf is a noun, never a verb.** If the head's only candidate gloss is a verb, the
  iḍāfa reading is impossible → `pending: pos_mismatch`. (`رَسُولًا` ≠ 'to send' — it is a
  noun 'a messenger'; the verbal root ر-س-ل does not license a verb gloss on this naṣb noun.)
- A token carrying tanwīn or `ال` cannot be a muḍāf — don't pull the following word into it.
- Don't gloss the muḍāf ilayh as a standalone subject; it is genitive *of* the head.

---

## 2. Jār-majrūr — preposition + noun

`preposition + noun(jarr)`. The noun is **always genitive**; therefore **a verb gloss after a
preposition is impossible** — this is one of nahw's strongest guards.

| jār-majrūr | gloss | note |
|---|---|---|
| `فِي الْأَرْضِ` | 'in the earth' | `الْأَرْض` is jarr → a noun, never a verb |
| `مِنَ النَّاسِ` | 'from the people' | `مِنَ` (kasra mīm) = 'from', not `مَنْ` 'who' |
| `عَلَى الْعَرْشِ` | 'on the Throne' | — |
| `بِالْحَقِّ` | 'with the truth / in truth' | bi- clitic + jarr noun |

**Guard:** after a preposition, the next content word is genitive. A candidate **verb** gloss
for that word → reject, `pending: pos_mismatch`. (E.g. a verb-root match for a noun that
follows `فِي`/`مِنْ`/`بِـ` is spurious.)

---

## 3. Preposition / ẓarf + **pronoun** clitic — the gloss-wording table

When the genitive slot is a *bound pronoun* (`ـهُ`, `ـهَا`, `ـهِمْ`, `ـنَا`, `ـكَ` …), the
preposition + pronoun fuse into one token whose gloss is a **two-word English phrase**. The
clitic must **not** be lemmatized as part of a root.

| token | preposition | clitic | recommended gloss |
|---|---|---|---|
| `بِهِ` | بِـ 'with/in' | ـهِ 'it/him' | **'with it' / 'in it'** (sense by clause) |
| `بِهَا` | بِـ | ـهَا | 'with it / in it' (fem. referent) |
| `لَهُ` | لِـ 'for/to' | ـهُ | **'for him' / 'to him'** |
| `لَهَا` | لِـ | ـهَا | 'for it / to it' (fem.) |
| `لَهُمْ` | لِـ | ـهُمْ | 'for them' |
| `بِهِمْ` | بِـ | ـهِمْ | 'with them' |
| `مِنْهُ` | مِنْ 'from' | ـهُ | 'from it / from him' |
| `مِنْهُمْ` | مِنْ | ـهُمْ | 'from them' |
| `عَلَيْهِ` | عَلَى 'on/against' | ـهِ | 'on him / against him' |
| `عَلَيْهِمْ` | عَلَى | ـهِمْ | 'on them / against them' |
| `إِلَيْهِ` | إِلَى 'to' | ـهِ | 'to him' |
| `إِلَيْهِمْ` | إِلَى | ـهِمْ | 'to them' |
| `فِيهِ` | فِي 'in' | ـهِ | 'in it / in him' |
| `فِيهَا` | فِي | ـهَا | 'in it' (fem.) |
| `بَيْنَهُمْ` | بَيْنَ 'between' | ـهُمْ | 'between them' |
| `عِنْدَهُ` | عِنْدَ 'with/near' | ـهُ | 'with him / in his sight' |

Notes:
- `بِهِ` = **'with it / in it'** — pick the sense from the verb it serves (`آمَنَ بِهِ` 'believed
  in it/him'; `كَتَبَ بِهِ` 'wrote with it'); if the clause does not decide, `pending: context`.
- `لَهُ` = **'for him / to him'** — benefactive vs. dative by clause; default 'for him'.
- The pronoun's English (it/him/them) tracks the **referent**, not the clitic shape alone —
  see the referent guard (§5) and `references/quranic-nahw-notes.md`.

---

## 4. `عِنْدَ` — the ẓarf that means more than "at"

`عِنْدَ` is a locative adverb (ẓarf makān) governing a genitive. Its English is **context-shaded**:

| frame | gloss |
|---|---|
| physical/temporal location | **'with' / 'near'** (`عِنْدَ الْبَابِ` 'at/near the door') |
| possession | 'in the possession of' (`مَا عِنْدَكُمْ` 'what you have') |
| in the presence/judgment of Allah | **'in the sight of'** (`عِنْدَ اللَّهِ` 'in the sight of Allah') |

Recommended: default gloss **'with / near'**; promote to **'in the sight of'** when the
muḍāf-ilayh is Allah and the frame is evaluative (reward, status, acceptance). When the
shade is unclear, prefer the broad **'with / near'** over a narrow guess.

---

## 5. The `إِلَيْنَا` guard — clitic must not flip the root (`seat_collapsed`)

This is the canonical clitic-induced false match. `إِلَيْنَا` = `إِلَى` ('to', root **ʾ-l-y**) +
`ـنَا` ('us'). It is **'to us'**. It is **not** root **ل-ي-ن** ('to be soft/lenient'), and not
'soft'. The trap: `norm()` *drops the hamza seat*, so `إِلَيْنَا` and a ل-ي-ن surface collapse
to the same key. `norm_strict()` keeps the seat and separates them.

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import norm, norm_strict

# norm() over-recalls: it would let إِلَيْنَا touch root ل-ي-ن
assert norm("إِلَيْنَا") != "" 
# norm_strict() keeps the hamza seat, so the ل-ي-ن candidate is NOT equal:
assert norm_strict("إِلَيْنَا") != norm_strict("لِينَا")

def reject_layin_for_ila(surface):
    """Return True if a root-ل-ي-ن candidate must be rejected for an إِلَى-family surface.
    Rule: if the strict key differs but only the lenient key matched, the seat was the
    distinguisher -> reject, pending: seat_collapsed."""
    s = norm_strict(surface)
    return s.startswith("ا") is False and s[:1] in ("إ", "ا") and "لي" in norm(surface)
```

**Rule:** for any `إِلَى` / `إِلَيْـ` form, never emit a ل-ي-ن ('soft') gloss; gloss the
preposition+clitic from the table (`إِلَيْنَا` → 'to us', `إِلَيْهِ` → 'to him'). If a candidate
only matched under `norm()` (seat dropped), reject it with `pending: seat_collapsed`.

---

## Drill checklist

1. Tanwīn / `ال` on a noun ⇒ it is **not** a muḍāf head; don't chain forward.
2. Word after a preposition is **jarr** ⇒ **no verb gloss** (`pending: pos_mismatch` if the
   only candidate is a verb).
3. Preposition/ẓarf + pronoun ⇒ emit the **two-word phrase** from the table; clitic is not a
   root letter.
4. `بِهِ`='with it/in it', `لَهُ`='for him/to him', `عِنْدَ`='with/near/in the sight of',
   `إِلَيْنَا`='to us' (**never** 'soft').
5. Unsure of the sense shade ⇒ broadest correct gloss, or `pending:` — never a narrow guess.

## VN-02 dogfood: bā', oath wāw, and nominal hosts

| token | visible pieces | unsafe hover |
|---|---|---|
| `بِٱلْمَعْرُوفِ` | `بِـ` + article + majrūr nominal host | treating component evidence as whole-token repair-ready |
| `بِدَيْنٍ` | attached bā' + majrūr noun "debt" | verb-derived "to be indebted to" |
| `دِينِ` | genitive/construct noun | verbal root infinitive |
| `وَوَالِدٍۢ` | oath/coordination wāw + majrūr nominal | birth/parent verb-family prose |
| `فَضْلِهِۦ` | genitive noun + 3ms possessive suffix | root-family "to favor" prose |

Rule: after a preposition or oath particle, a nominal host is not certified by a
verb entry. Preserve the relation and the case/possessor before polishing the
English.
