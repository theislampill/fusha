# Drill — homograph regressions

These are the **exact pairs that shipped wrong** before the harakāt logic existed. Each row
is two surfaces whose *bare consonants are identical* (so `norm()` collapses them) but whose
*meaning differs*. The only thing that tells them apart is a **diacritic on the content
letter**, a **hamza seat**, or a **shadda**. Memorize the distinguishing feature, not the
spelling.

## The one principle

`tools/normalize_ar.norm()` strips tashkīl and the hamza seat. For short function words and
diacritic‑homographs that is exactly the information you need — so **`norm()` must never
decide a homograph.** Read the harakah on the **content letter**, which may sit *after* a
`و`/`ف` proclitic. Reading the *first* letter's vowel is the bug that glossed `وَمِنَ`
"and from" as "and whoever".

Use the shared helpers — do not re‑implement them:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # repo root
from tools.normalize_ar import (
    norm, norm_strict, bare, haraka_on, shadda_on, is_man_who, ends_tanwin_alef,
    KASRA, FATHA, DAMMA,
)
```

- `haraka_on(tok, "م")` → the short vowel on the **first `م`**, scanning past a proclitic.
- `shadda_on(tok, "م")` → is there a shadda on that letter's cluster?
- `is_man_who(tok)` → `مَن` "who" (no kasra on mīm, no shadda on nūn) vs `مِن` "from".
- `ends_tanwin_alef(tok)` → ـًا tanwīn‑alef (looks like stem+نا but isn't).

> **NFC robustness:** the helpers scan the whole harakāt cluster, so they survive the
> fatḥa↔shadda ordering quirks of NFC. Don't index a fixed offset yourself.

---

## The regression table

| # | Pair | Looks the same because… | Distinguishing feature | Correct decision |
|---|---|---|---|---|
| 1 | `مَن` "who" vs `مِن` "from" (incl. `وَمِنَ` "and from") | `norm()` drops the harakah | **harakah on the content letter `م`**: `مَن` = fatḥa/none, `مِن` = **kasra**. Read past the `و`/`ف` proclitic. | `is_man_who(tok)`; relative/interrogative vs preposition |
| 2 | `لِمَا` "for what" vs `لَمَّا` "when / not yet" | same consonants `لما` | **shadda on `م`**: `لَمَّا` has it, `لِمَا`/`لَمَا` do not | `shadda_on(tok,"م")` → `لَمَّا`; else `لِمَا` |
| 3 | `كُلّ` "all/every" vs `كَلَّا` "nay!" | both `كل…` | **harakah on `ك`**: `كُلّ`/`كُلًّا` = **ḍamma**; `كَلَّا` = **fatḥa** | `haraka_on(tok,"ك")` == DAMMA → "all"; == FATHA → "nay" |
| 4 | `نِعْمَ` "how excellent!" vs `نَعَمْ` "yes" | both `نعم` | **harakah on `ن`**: `نِعْمَ` = **kasra**; `نَعَمْ` = **fatḥa** | `haraka_on(tok,"ن")` distinguishes praise‑verb vs affirmation |
| 5 | `أَنِّي` "that I" vs `أَنَّى` "how / whence" | both `أن…ي/ى` | **shadda on `ن` + final `ي` vs `ى`**: `أَنِّي` ends `ي`; `أَنَّى` ends alif maqṣūra `ى` | keep `ي`≠`ى` (use `bare()`, which preserves the distinction) |
| 6 | `لَمْ` "did not" vs `لِمَ` "why?" | both `لم` | **harakah on `ل`**: `لَمْ` = **fatḥa** + sukūn on `م`; `لِمَ` = **kasra** | `haraka_on(tok,"ل")`: fatḥa → negation; kasra → interrogative |
| 7 | `إِيمَان` "faith" (root `أ م ن`) vs `أَيْمَان` "oaths" (root `ي م ن`) | `norm()` drops the hamza seat → identical key | **hamza seat + radical role**: `إِيمَان` initial hamza‑kasra, `ي` is a glide; `أَيْمَان` the `ي` is a **radical** | `norm_strict()` keeps them apart; certify root via QAC |
| 8 | `يَأْمُرُونَ` "they command" (root `أ م ر`) vs `يَمُرُّونَ` "they pass by" (root `م ر ر`) | `norm()` drops hamza + gemination | **hamza on first stem letter vs shadda on `ر`**: `يَأْمُرُونَ` has the `ء`; `يَمُرُّونَ` has the doubled `ر` | different roots, different glosses; never collapse |
| 9 | `إِلَيْنَا` "to us" (إلى + ـنا) vs root `ل ي ن` "to be soft" | `norm()` yields a `لين`‑shaped key | **it's a preposition + enclitic, not a triliteral stem**; hamza of `إلى` is dropped by `norm()` | parse the enclitic; do **not** certify root `ل ي ن` |

> Rows 7–9 are the cases where the killer is the **hamza seat**: `norm()` erases it, so the
> match key lies. Always re‑certify a hamza‑bearing token with `norm_strict()` / QAC.

---

## Why the *content* letter, not the first letter

A proclitic `و` "and" or `ف` "so" attaches in front of the word. Its own vowel is
irrelevant to which homograph this is. The signal lives on the **first radical of the
content word**:

```python
haraka_on("وَمِنَ", "م") == KASRA      # True  → it's مِن "from" → "and from"
is_man_who("وَمِنَ")                    # False → NOT مَن "whoever"
is_man_who("مَنْ")                      # True  → relative/interrogative "who"
is_man_who("مَنِ")                      # True  → liaison kasra on the END is still مَن "who"
is_man_who("مَنَّ")                     # False → verb مَنَّ "to bestow" (shadda on ن)
```

That last group is the subtle one: a **liaison kasra** (`مَنِ` before a sukūn) sits on the
mīm only as a connector and does **not** make it `مِن` — `is_man_who` already accounts for
this by also checking there's no shadda on the `ن`. Trust the helper; don't hand‑roll the
vowel read.

## Tanwīn‑alef vs stem + ـنا

`قُرْءَانًا` ends in **ʾalif al‑tanwīn** (`ـًا`), which *looks* like a stem ending in `نا`
("us") but is just accusative tanwīn on a long‑ā word. Glossing it as if `…ن + ا` carried a
1pl pronoun is wrong.

```python
ends_tanwin_alef("قُرْءَانًا")   # True  → ـًا tanwīn, NOT stem+نا; don't split off a pronoun
```

## Self‑check (mirrors `normalize_ar.__main__`)

You can verify the helpers behave on these exact pairs:

```python
assert is_man_who("مَنْ") and not is_man_who("مِنْ") and not is_man_who("وَمِنَ")
assert is_man_who("مَنِ") and not is_man_who("مَنَّ")
assert not shadda_on("لِمَا", "م") and shadda_on("لَمَّا", "م")
assert haraka_on("كُلًّا", "ك") == DAMMA and haraka_on("كَلَّا", "ك") == FATHA
assert norm_strict("إِيمَان") != norm_strict("أَيْمَان")   # seats keep root أمن ≠ يمن
assert ends_tanwin_alef("قُرْءَانًا")                       # ـًا is tanwīn, not +نا
print("homograph drill self-check OK")
```

## The standing order

For **every** short function word and every hamza/shadda‑bearing content word:

1. Run the relevant helper (`is_man_who`, `haraka_on`, `shadda_on`, `ends_tanwin_alef`),
   reading the **content** letter.
2. If the harakah is **absent** in the source text (undiacritized), you **cannot**
   disambiguate → **PENDING**. Do not pick the more common reading and hope.
3. Certify hamza‑bearing tokens with `norm_strict()` / QAC, never `norm()`.
4. Emit `{src:'qamus', kind:'authored'}` only when the reading is certain; otherwise leave
   the token plain.

**PENDING beats wrong** — and on these pairs, the wrong gloss is the one that flips the
meaning of the āyah.
