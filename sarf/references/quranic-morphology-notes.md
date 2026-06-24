# Reference — Qur'anic morphology notes (gloss‑safety focused)

Concise ṣarf reference, scoped to **one job**: stopping a wrong hover gloss. Every section
ends with the *gloss‑safety consequence* — the mistake it prevents. This is not a grammar
course; it is the minimum morphology that keeps `{src:'qamus', kind:'authored'}` honest.

Throughout, "certify" means: confirm against the **Qamus entry / QAC**, never against
`norm()` alone (`norm()` drops hamza + harakāt and cannot decide form, root, or class).

---

## 1. The verb forms (awzān) I–X

Arabic verbs are built on a root (usually three radicals, shown abstractly as `ف ع ل`) cast
into numbered **forms**. The form changes the *meaning* in regular ways. The radicals stay
the same; the pattern carries the semantics.

| Form | Perfect | Imperfect | Maṣdar (typical) | Core sense shift | Example root |
|---|---|---|---|---|---|
| I | `فَعَلَ` | `يَفْعُلُ/يَفْعِلُ/يَفْعَلُ` | varied (`فَعْل`, `فُعُول`, …) | base meaning | `كَتَبَ` write |
| II | `فَعَّلَ` | `يُفَعِّلُ` | `تَفْعِيل` | intensive / causative | `عَلَّمَ` teach |
| III | `فَاعَلَ` | `يُفَاعِلُ` | `مُفَاعَلَة`/`فِعَال` | reciprocal / directed‑at | `جَاهَدَ` strive‑against |
| IV | `أَفْعَلَ` | `يُفْعِلُ` | `إِفْعَال` | causative | `أَنْزَلَ` send down |
| V | `تَفَعَّلَ` | `يَتَفَعَّلُ` | `تَفَعُّل` | reflexive of II | `تَبَيَّنَ` become clear |
| VI | `تَفَاعَلَ` | `يَتَفَاعَلُ` | `تَفَاعُل` | mutual / reflexive of III | `تَعَاوَنَ` cooperate |
| VII | `اِنْفَعَلَ` | `يَنْفَعِلُ` | `اِنْفِعَال` | passive / medio‑passive | `اِنْقَلَبَ` turn back |
| VIII | `اِفْتَعَلَ` | `يَفْتَعِلُ` | `اِفْتِعَال` | reflexive / middle | `اِخْتَلَفَ` differ |
| IX | `اِفْعَلَّ` | `يَفْعَلُّ` | `اِفْعِلَال` | colours / defects | `اِحْمَرَّ` redden |
| X | `اِسْتَفْعَلَ` | `يَسْتَفْعِلُ` | `اِسْتِفْعَال` | seek / consider | `اِسْتَغْفَرَ` seek forgiveness |

**What the prefixes/infixes are — and are NOT:**

- The `أ` of Form IV (`أَفْعَلَ`), the `ت` of Forms V/VI/VIII, the `ن` of Form VII, the
  `س ت` of Form X, and the connecting `ا` (hamzat al‑waṣl, `ٱ`) at the front of Forms
  VII–X are **augment letters**, not radicals. Reading them as radicals invents a bogus
  root.
- Same root, different form ⇒ often a **different English sense** (Form I `أَتَى` "come"
  vs Form IV `آتَى` "give"; Form I `نَزَلَ` "descend" vs Form IV `أَنْزَلَ` "send down").

**Gloss‑safety consequence.** A gloss must match the **form**, not merely the root. Bind to
the entry/sense whose form fits the surface; if the form is ambiguous in undiacritized text,
**PENDING**. Strip augment letters before proposing a root.

---

## 2. Weak letters (ḥurūf al‑ʿilla: `و ي ا`)

A radical that is `و` or `ي` (and the alif that derives from them) is **weak**: it
transforms or drops depending on the pattern. The four classic types:

| Type | Weak radical position | Example | Trap |
|---|---|---|---|
| **Miṯāl** | first (`و`/`ي`) | `وَعَدَ` → `يَعِدُ` (the `و` drops in the imperfect) | the missing first radical isn't really missing — it's the root's `و` |
| **Ajwaf (hollow)** | middle (`و`/`ي`) | `قَالَ` (root `ق و ل`), `بَاعَ` (root `ب ي ع`) | the surface `ا` **is** the middle radical, not an extra letter |
| **Nāqiṣ (defective)** | last (`و`/`ي`) | `دَعَا` (root `د ع و`), `رَمَى` (root `ر م ي`) | the final `ا`/`ى` is the third radical surfacing weak |
| **Lafīf** | two weak radicals | `وَقَى` (root `و ق ي`) | two transformations at once |

**Gloss‑safety consequence.** In a hollow verb the `ا` you see *is* the radical (`قَالَ` →
`ق و ل`) — do not read `ق ا ل`. In a defective verb the final `ا`/`ى` is the third radical —
recover it from QAC, since the surface hides whether it's `و` or `ي`. Getting this wrong
fabricates a root and lands a wrong entry.

---

## 3. Hamza and its seats (ء أ إ ؤ ئ)

Hamza (`ء`) is a full consonant, but it is **written on different seats** depending on the
surrounding vowels: `أ` (on alif), `إ` (on alif with kasra), `ؤ` (on wāw), `ئ` (on yāʾ), or
bare `ء`. The seat is orthographic; the consonant is the same hamza.

- **`norm()` deletes every hamza seat** (`أ إ ء → ∅`, `ؤ → و`, `ئ → ي`). That is why it can
  never certify a hamzated root. `norm_strict()` keeps the seat.
- A hamza may be a **radical** (root `أ م ر` in `أَمَرَ`; root `س أ ل` in `سَأَلَ`; root
  `ق ر أ` in `قَرَأَ`) or a **glide/augment** (the `إِ` of a Form IV maṣdar `إِيمَان`).
  Telling these apart is the whole game in §1 example 4 of the root‑detection drill.

**Canonical seat regressions (all live):**

- `إِيمَان` "faith" (root `أ م ن`) vs `أَيْمَان` "oaths" (root `ي م ن`) — `norm()` merges
  them; only the seat (+ QAC) separates them.
- `يَأْمُرُونَ` "they command" (`أ م ر`, hamza) vs `يَمُرُّونَ` "they pass" (`م ر ر`,
  shadda) — different roots entirely.
- `إِلَيْنَا` "to us" — the hamza of `إلى` vanishes under `norm()`, leaving a `لين`‑shaped
  key that is **not** root `ل ي ن`.

**Gloss‑safety consequence.** Any token containing a hamza **must** be certified with
`norm_strict()` / QAC, never `norm()`. When the seat is the only distinguisher and the
source is undiacritized/ambiguous → **PENDING**.

---

## 4. Tāʾ marbūṭa (`ة`) vs hāʾ (`ه`)

`ة` (tāʾ marbūṭa) is a word‑final `ت` written as a tied `ه`; `ه` is the consonant *hāʾ*.
They are **different letters** carrying different grammar:

- `ة` typically marks the **feminine** (`بَيِّنَة`, `أَمَانَة`, `مُتْعَة`), a *singular of a
  collective* (`ثَمَرَة`), or a maṣdar instance. It often signals a **noun**.
- `ه` is a radical or the 3rd‑person pronoun suffix (`كِتَابُهُ` "his book").

`norm()`/`norm_strict()` **fold `ة → ه`** (good for recall, lossy for grammar). **`bare()`
keeps `ة ≠ ه`** — use `bare()` when the tāʾ marbūṭa is grammatically load‑bearing (class /
enclitic detection).

**Gloss‑safety consequence.** Don't let the `ة → ه` fold erase the feminine‑noun signal and
let a verb gloss attach to a noun (`بَيِّنَة` "a clear proof" must not become "to make
clear"). Use `bare()` when the `ة` matters; never display‑normalize it.

---

## 5. Alif maqṣūra (`ى`) vs yāʾ (`ي`)

`ى` (alif maqṣūra, "dotless yāʾ") is a final long `ā` that derives from a weak `ي`/`و`
third radical (`رَمَى`, `هُدَى`, `أَنَّى`); `ي` is the consonant/long‑ī. They look almost
identical and are routinely confused in input.

- `norm()`/`norm_strict()` **fold `ى → ي`** (recall). **`bare()` keeps `ى ≠ ي`.**
- Pairs that hinge on it: `أَنَّى` "how/whence" (ends `ى`) vs `أَنِّي` "that I" (ends `ي`).
- In a defective verb, the final `ى` is the **weak third radical** surfacing as `ā`
  (`دَعَا`/`دَعَوْتُ` shows the `و`; `رَمَى`/`رَمَيْتُ` shows the `ي`).

**Gloss‑safety consequence.** When the final letter distinguishes two words (homograph
drill #5), use `bare()` so `ى` and `ي` stay apart; recover the underlying weak radical from
QAC before assigning a root.

---

## 6. Tanwīn‑alef (`ـًا`) — the false `+ نا`

Accusative tanwīn on many words is written with a **silent supporting alif**: `كِتَابًا`,
`قُرْءَانًا`, `رَسُولًا`. That trailing `ـًا` is **grammatical case marking**, not a stem
letter and **not** the 1pl enclitic `ـنا` "us".

- Helper: `ends_tanwin_alef(tok)` returns `True` for `قُرْءَانًا` — meaning "this `ا` is
  tanwīn, do not split off a pronoun."

**Gloss‑safety consequence.** Don't parse `قُرْءَانًا` as `قرءان + نا`. And note: a word
ending in tanwīn‑alef is typically an **indefinite noun in the accusative** — so `رَسُولًا`
is "a messenger", **not** the verb "to send"; `صَالِحًا` is "righteous" (adj.), **not** the
Prophet Ṣāliḥ. Class first.

---

## 7. The derived nominals: maṣdar, ism fāʿil, ism mafʿūl

Three deverbal noun types recur constantly and each has a **fixed pattern per form**.
Recognizing the pattern tells you the **class** (noun, not finite verb) and the **role**
(action / doer / done‑to).

| Type | Form I shape(s) | Derived‑form shape | Meaning | Example |
|---|---|---|---|---|
| **Maṣdar** (verbal noun) | varied: `فَعْل`, `فُعُول`, `فِعَالَة`, … | regular per form (`إِفْعَال` IV, `تَفْعِيل` II, `اِسْتِفْعَال` X) | the *action* itself | `قَوْل` "speech", `إِيمَان` "faith", `اِسْتِغْفَار` "seeking forgiveness" |
| **Ism fāʿil** (active participle) | `فَاعِل` | `مُـ…ـِ…` (`مُفْعِل` IV, `مُسْتَفْعِل` X) | the *doer* | `كَاتِب` "writer", `مُؤْمِن` "believer", `مَالِك` "owner" |
| **Ism mafʿūl** (passive participle) | `مَفْعُول` | `مُـ…ـَ…` (`مُفْعَل` IV) | the *done‑to* | `مَكْتُوب` "written", `مُنْزَل` "sent down" |

**Reading rules that prevent wrong glosses:**

- A **maṣdar is a noun**: `قَوْل` = "a saying", not "to say"; `إِيمَان` = "faith", not "to
  believe". The verb gloss ("to …") belongs only to finite verbs.
- **Ism fāʿil vs ism mafʿūl** differ by the **final stem vowel** in derived forms (kasra =
  doer, fatḥa = done‑to): `مُنْزِل` "one who sends down" vs `مُنْزَل` "what is sent down".
  The harakah is the whole distinction — `norm()` erases it.
- A participle can also be a **frozen noun or a proper name** (`مَالِك`, `مُحَمَّد`
  ["praised"], `صَالِح`). A proper name is **not** a verb and **not** its literal
  participle gloss — check context.

**Gloss‑safety consequence.** Classify the derived nominal *before* choosing gloss
vocabulary. Never put a verb gloss ("to …") on a maṣdar, an ism fāʿil, or an ism mafʿūl;
never treat a proper name as its underlying verb. If the doer/done‑to vowel is unmarked →
PENDING.

---

## 8. Quick decision flow (use before every gloss)

```
surface form
   │
   ├─ strip proclitics (و/ف/ال/بـ/كـ/لـ) and enclitics (ـه/ـها/ـنا/ـكم …)
   │     using bare()/norm() for detection — but watch ـًا (ends_tanwin_alef = tanwīn, not نا)
   │
   ├─ identify augment letters (Form II–X prefixes/infixes, hamzat al-waṣl ٱ) → NOT radicals
   │
   ├─ recover the 3 radicals (weak letters: ا may be a hollow middle radical;
   │     final ا/ى may be a defective third radical) → certify root via Qamus entry / QAC
   │
   ├─ hamza present? → certify with norm_strict()/QAC, never norm()
   │
   ├─ short function word OR diacritic-homograph? → run haraka_on / shadda_on / is_man_who
   │     on the CONTENT letter (homograph-regressions.md)
   │
   ├─ classify: verb (which form?) / maṣdar / ism fāʿil / ism mafʿūl / plain noun / particle
   │
   └─ bind to the Qamus entry whose root AND sense AND class match
         ├─ match → emit {src:'qamus', kind:'authored'}
         └─ any uncertainty (form, root, sense, missing harakah) → PENDING (leave plain)
```

---

## 9. Standing constraints (repeat from the pack)

- **Qur'an text is never altered.** Normalization keys are for *matching*, never display.
- **`norm()` cannot certify** — it drops hamza + harakāt. Certify with `norm_strict()`,
  `haraka_on`/`shadda_on`/`is_man_who`, QAC, or the entry itself.
- **Class gates vocabulary.** Verb gloss → finite verbs only; nouns/maṣādir/participles get
  noun glosses; proper names get neither.
- **External references are `informed_by`, never copied.** Public hover = only
  `{src:'qamus', kind:'authored'}`.
- **PENDING beats wrong.** A blank hover is correct; a flipped meaning is a defect.
- All helpers live in `tools/normalize_ar.py`. Reference them; do not redefine them.
