# Drill — root detection

**Goal:** given a Qur'anic surface form, recover its **root** (the radicals) reliably enough
to bind it to a Qamus entry — or to decide it earns no gloss yet.

**Rule of the drill:** climb the evidence ladder; never eyeball. The consonants you *see*
are not always the radicals you *want* — weak letters drop, hamza changes seat, an affixed
letter masquerades as a radical, and `norm()` throws away exactly the marks that would have
told you apart.

## The ladder (apply top‑down, record the rung)

1. **Qamus entry** — does an existing entry's `root` + `headword` already cover this surface
   and sense? If yes, you're done: bind to it.
2. **QAC root** — cross‑check the radicals for *this token position* against the Quranic
   Arabic Corpus morphology. `informed_by` only.
3. **Photographed source** — for a not‑yet‑seeded root, the owner's physical
   root‑dictionary page is the authority for root, headword, senses.
4. **External reference** (Quran.com / Tanzil / sunnah.com) — corroborate a reading;
   **never** copy gloss prose.
5. **Heuristic** (`tools/normalize_ar.py` + pattern sense) — recall/triage only; never the
   sole basis for a shipped gloss.

> If a lower rung disagrees with a higher one, the higher one wins. If nothing above rung 5
> resolves it, the answer is **PENDING**.

## Why eyeballing fails (the trap this drill defends)

`norm()` strips tashkīl **and drops the hamza seat**, folding `ى→ي`, `ة→ه`. That is great
for recall and fatal for certification:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # repo root → import tools.*
from tools.normalize_ar import norm, norm_strict, bare

# إِلَيْنَا "to us" is preposition إلى + ـنا. It is NOT root ل ي ن.
norm("إِلَيْنَا")          # → "الينا"-ish recall key; the hamza of إلى is gone
norm_strict("إِلَيْنَا")   # → keeps the hamza seat, so it will not masquerade as ل ي ن
# Certify the root from QAC / the Qamus entry, never from norm() alone.
```

So: use `norm()` to *propose* candidate entries (wide net), then **certify with
`norm_strict()` / QAC / the entry's own root**. A `norm()` collision is a question, not an
answer.

## Worked examples

Each example: the surfaces → the root → how the ladder resolves it → the gloss‑safety note.

---

### 1. `ق و ل` — `قَالَ` / `يَقُولُ` / `قَوْل`

- **Surfaces.** `قَالَ` "he said" (Form I perfect, hollow), `يَقُولُ` "he says"
  (imperfect), `قَوْل` "a saying / speech" (maṣdar).
- **Root.** `ق و ل` — a **hollow** root (middle radical `و`). The `و` surfaces as `ا` in
  `قَالَ`, returns as `و` in `يَقُولُ` and `قَوْل`.
- **Ladder.** Rung 1: a Qamus verb entry `root = "ق و ل"` covers all three. The `ا` in
  `قَالَ` is the weak middle radical, not a stray alif — confirm with QAC if unsure.
- **Gloss safety.** `قَوْل` is a **noun** (maṣdar): gloss it "a saying / word", **not**
  "to say". The verb gloss belongs only to the finite verb surfaces. Class first, gloss
  second.

### 2. `أ ت ى` — `يَأْتِي` / `ءَاتَىٰ`

- **Surfaces.** `يَأْتِي` "he comes" (Form I), `ءَاتَىٰ` / `آتَى` "he gave / brought"
  (Form IV, causative).
- **Root.** `أ ت ى` — **hamzated first radical** (`أ`) **and weak last radical**
  (`ى`/alif maqṣūra). Two weaknesses in one root.
- **Ladder.** Rung 2 is decisive here: QAC distinguishes Form I `أتى` "to come" from
  Form IV `آتى` "to give". The initial `آ`/`ءَا` of `ءَاتَىٰ` is the Form IV prosthetic +
  hamza, **not** an extra radical. Do not read `ا ت ى`.
- **Gloss safety.** The two forms have **different English senses** ("come" vs "give") on
  the *same* root. A gloss must respect the form, not just the root — bind to the entry/sense
  whose form matches. Note the hamza seat: `norm()` would erase it, so certify with
  `norm_strict()` / QAC.

### 3. `ب ي ن` — `بَيِّنَة` / `تَبَيَّنَ`

- **Surfaces.** `بَيِّنَة` "a clear proof" (noun, fem.), `تَبَيَّنَ` "it became clear /
  he ascertained" (Form V).
- **Root.** `ب ي ن` — middle radical `ي`. The shadda in `بَيِّنَة` and the doubled `ي` of
  `تَبَيَّنَ` are gemination of that middle radical, not extra letters.
- **Ladder.** Rung 1/2: one root, two patterns. `بَيِّنَة` is `فَعِّلَة`‑shaped (noun);
  `تَبَيَّنَ` is Form V (تَفَعَّلَ).
- **Gloss safety.** `بَيِّنَة` is a **noun** → "a clear proof / evidence". `تَبَيَّنَ` is a
  **verb** → "to become clear / verify". Same root, different class → different gloss
  vocabulary. The tāʾ marbūṭa (`ة`) marks the noun; don't let `bare()`/`norm()` fold it into
  `ه` and lose the signal — use `bare()` only for enclitic detection, not class.

### 4. `أ م ن` — `إِيمَان` / `أَمْن` / `أَمَانَة` (contrast `أَيْمَان` "oaths")

- **Surfaces (root `أ م ن`).** `إِيمَان` "faith / belief" (Form IV maṣdar), `أَمْن`
  "safety / security" (Form I maṣdar), `أَمَانَة` "a trust" (noun).
- **The contrast.** `أَيْمَان` "oaths" is **root `ي م ن`** (plural of `يَمِين`), **not**
  `أ م ن`. They collide brutally under `norm()`.
- **Root.** `أ م ن` is **hamzated first radical**. In `إِيمَان` the first‑radical hamza +
  kasra surfaces as a long `ـِي` (`إِ` + `ي`); the radical is still hamza, the `ي` here is the
  glide, the second radical is `م`, the third `ن`.
- **Ladder.** Rung 2 is mandatory. `norm("إيمان")` and `norm("أيمان")` collapse together
  (hamza dropped); only `norm_strict()` / QAC keep `إِيمَان` (root `أ م ن`) apart from
  `أَيْمَان` (root `ي م ن`). **Never certify `أ م ن` from `norm()`.**
- **Gloss safety.** Glossing `أَيْمَان` "oaths" as "faith" is the canonical regression.
  Distinguish by hamza seat + the `ي` as a *radical* (in `يمن`) vs *glide* (in `إيمان`).
  When unsure → PENDING.

```python
from tools.normalize_ar import norm, norm_strict
norm("إِيمَان") == norm("أَيْمَان")          # True  → recall collision, NOT identity
norm_strict("إِيمَان") != norm_strict("أَيْمَان")  # True  → seats keep them apart; certify here
```

### 5. `م ل ك` — `مُلْك` / `مَلِك` / `مَلَك` / `مَالِك`

- **Surfaces, one root `م ل ك`, four words.**
  - `مُلْك` "dominion / sovereignty" (maṣdar) — **not** "angels".
  - `مَلِك` "a king" (noun, `فَعِل`).
  - `مَلَك` "an angel" (noun, `فَعَل`).
  - `مَالِك` "an owner / Mālik" (ism fāʿil; also a proper name in some contexts).
- **Root.** `م ل ك` for all four; they differ **only** by harakāt + length.
- **Ladder.** Rung 1/2: the root is uncontested; the *sense* is everything. The harakāt are
  the whole signal — `مُلْك` (ḍamma‑sukūn) vs `مَلِك` (fatḥa‑kasra) vs `مَلَك`
  (fatḥa‑fatḥa) vs `مَالِك` (long ā + kasra).
- **Gloss safety.** This is the textbook same‑root polysemy trap: `ٱلْمُلْك` is **not**
  "angels". `norm()` flattens all four to the same key — so a root match alone licenses
  **no** gloss here. You must certify the *sense* from harakāt + context + the matching
  entry, or go PENDING. `مَالِك` as a proper name is **not** a verb and **not** generic
  "owner" — check context.

### 6. `ن ه ر` — `نَهْر` / `نَهَار` / `أَنْهَار`

- **Surfaces.** `نَهْر` "a river" (noun), `أَنْهَار` "rivers" (broken plural of `نَهْر`),
  `نَهَار` "daytime" (noun).
- **Root.** `ن ه ر` for all three — but two distinct meanings ("river" vs "daytime") share
  the consonants.
- **Ladder.** Rung 2 + context. `أَنْهَار` is the **plural of river**, not a form of
  "daytime". `نَهَار` "daytime" pairs with `لَيْل` "night" in context.
- **Gloss safety.** Canonical regression: `أَنْهَٰر` glossed "daytime". The distinguisher is
  pattern + context, not consonants. `أَنْهَار` = `أَفْعَال` broken plural → "rivers".
  `نَهَار` = the daytime sense. If context doesn't disambiguate → PENDING.

### 7. `ر ج ل` — `رَجُل` / `رِجَال` / `أَرْجُل`

- **Surfaces.** `رَجُل` "a man" (sing.), `رِجَال` "men" (broken plural, `فِعَال`),
  `أَرْجُل` "feet / legs" (plural of `رِجْل`).
- **Root.** All `ر ج ل`, but **two different singulars**: `رَجُل` "man" and `رِجْل`
  "foot/leg". `رِجَال` is the plural of *man*; `أَرْجُل` is the plural of *foot*.
- **Ladder.** Rung 2 + the harakāt on the singular: `رَجُل` (fatḥa‑ḍamma, "man") vs `رِجْل`
  (kasra‑sukūn, "foot"). The plurals diverge accordingly.
- **Gloss safety.** Do not gloss `أَرْجُل` "men" or `رِجَال` "feet". Same root, two object
  meanings, separated by the singular's harakāt and the plural pattern. Bind each plural to
  the entry whose singular it actually pluralizes.

### 8. `م ت ع` — `مَتَٰع` / `متعة`

- **Surfaces.** `مَتَاع` / `مَتَٰع` "goods / provision / enjoyment" (noun), `مُتْعَة`
  "enjoyment / a provision" (noun, `فُعْلَة`).
- **Root.** `م ت ع` for both. Note `مَتَٰع` uses the **dagger alef** (`ٰ`, U+0670) for the
  long `ā`; `norm()`/`norm_strict()`/`bare()` already map it to `ا`, so it will not look
  like a separate radical — but never display‑normalize it.
- **Ladder.** Rung 1/2: one root, two nouns differing by pattern (`مَفْعَال`‑ish vs
  `فُعْلَة`).
- **Gloss safety.** Both are **nouns** → "provision / enjoyment", **never** a verb gloss.
  The tāʾ marbūṭa in `مُتْعَة` marks the `فُعْلَة` noun; keep it distinct from a bare‑`ه`
  reading. Choose the sense ("worldly goods" vs "enjoyment/provision") from context + entry.

---

## Checklist before you bind a root → entry

- [ ] Did I climb the ladder and **record the rung** I certified from?
- [ ] If I used `norm()` to find the candidate, did I **re‑certify** with `norm_strict()` /
      QAC / the entry (hamza seat + harakāt intact)?
- [ ] Is the surface's **pattern/class** (verb vs noun vs participle) consistent with the
      gloss vocabulary I'm about to use?
- [ ] For a **same‑root polyseme** (`م ل ك`, `ن ه ر`, `ر ج ل`), did context pick the
      sense — or is it PENDING?
- [ ] Is this a **proper name** that only *looks* like a verb/derivative? (If so, not a verb
      gloss.)
- [ ] Public emit is `{src:'qamus', kind:'authored', lang:'en'}` or **nothing**. No external prose.

When in doubt at any box: **PENDING beats wrong.**
