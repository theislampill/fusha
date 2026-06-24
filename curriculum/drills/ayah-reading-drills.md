# Drill — āyah reading (token by token)

**Goal:** read a **short āyah** the way the hover layer reads it — one token at a time, each token
classified (particle / verb / noun / pronoun) and glossed, then assembled into a sentence. This is
Level 8 of [`../README.md`](../README.md): the first eight rungs built the machinery to read *one*
āyah, and here you use it.

**Rule of the drill:** every token gets an **address** and a **class** before it gets a gloss.
Each word is addressed `quran:S:A:W` (surah:ayah:word, per
[`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md)) — a
pointer at the verbatim word, never an edit of it. Glosses are the authored hover values
(`{src:'qamus', kind:'authored'}`); a word with no certified gloss reads **blank** on the live app,
and a blank is honest — it means *route to procedure*, not *invent a meaning*.

> Qurʾān text is never altered. The diacritics here serve reading; the muṣḥaf is the authority.
> Particle calls follow [`../../nahw/drills/particles.md`](../../nahw/drills/particles.md);
> root/class calls follow
> [`../../sarf/procedures/root-decision.md`](../../sarf/procedures/root-decision.md). Verify
> meaning against the muṣḥaf and a qualified teacher — this is a *language* drill.

**How to do each item:** cover the gloss column, read the Arabic token aloud (Level 1), name its
class (Levels 2–7), then uncover and check. Read the assembled sentence last.

---

### 1. `quran:108:1` — `إِنَّا أَعْطَيْنَاكَ ٱلْكَوْثَرَ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:108:1:1` | `إِنَّا` | particle + pronoun | indeed + we (`إِنَّ` + `نا`) |
| `quran:108:1:2` | `أَعْطَيْنَا` | verb (Form IV) + `نا` | we gave |
| `quran:108:1:3` | `كَ` | clitic pronoun | you (object) |
| `quran:108:1:4` | `ٱلْكَوْثَرَ` | noun (definite) | al-Kawthar (abundance) |

**Assembled:** "Indeed We have given you al-Kawthar." Note `إِنَّا` = `إِنَّ` ("indeed") fused
with the clitic `ـنا` ("we"); the verb `أَعْطَيْنَا` already carries "we" again as its subject.

### 2. `quran:112:1` — `قُلْ هُوَ ٱللَّهُ أَحَدٌ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:112:1:1` | `قُلْ` | verb (imperative) | say |
| `quran:112:1:2` | `هُوَ` | detached pronoun | He |
| `quran:112:1:3` | `ٱللَّهُ` | noun (proper) | Allah |
| `quran:112:1:4` | `أَحَدٌ` | noun (predicate) | One |

**Assembled:** "Say: He is Allah, One." A nominal sentence inside the command: `هُوَ` (mubtadaʾ)
+ `ٱللَّهُ أَحَدٌ` — no verb between subject and predicate (Level 6).

### 3. `quran:112:2` — `ٱللَّهُ ٱلصَّمَدُ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:112:2:1` | `ٱللَّهُ` | noun (mubtadaʾ) | Allah |
| `quran:112:2:2` | `ٱلصَّمَدُ` | noun (khabar) | the Eternal Refuge |

**Assembled:** "Allah, the Eternal Refuge." A two-word nominal sentence; note `ٱلصَّمَد` is a
**sun-letter** word — `ٱل` assimilates ("aṣ-ṣamad," shadda on `ص`), as drilled in
[`alphabet-and-sounds.md`](alphabet-and-sounds.md).

### 4. `quran:103:1` — `وَٱلْعَصْرِ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:103:1:1` | `وَ` | particle (oath wāw) | by (oath) |
| `quran:103:1:2` | `ٱلْعَصْرِ` | noun (jarr) | the (passing) time / ʿaṣr |

**Assembled:** "By time." Here the wāw is **wāw al-qasam** (oath), not "and": it is
clause-initial before a jarr noun with no governing verb — the exact frame from
[`../../nahw/drills/particles.md`](../../nahw/drills/particles.md). The kasra on `ٱلْعَصْرِ` is
the oath's jarr.

### 5. `quran:103:2` — `إِنَّ ٱلْإِنسَانَ لَفِي خُسْرٍ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:103:2:1` | `إِنَّ` | particle (emphasis) | indeed |
| `quran:103:2:2` | `ٱلْإِنسَانَ` | noun (ism inna, naṣb) | mankind |
| `quran:103:2:3` | `لَ` | particle (lām of emphasis) | surely |
| `quran:103:2:4` | `فِي` | preposition | in |
| `quran:103:2:5` | `خُسْرٍ` | noun (jarr) | loss |

**Assembled:** "Indeed mankind is in loss." After `إِنَّ`, `ٱلْإِنسَانَ` takes **naṣb** (fatḥa)
as the *ism inna* (Level 6, item 7); the predicate is the jār-majrūr `(لَ)فِي خُسْرٍ`. The `لَ`
is emphatic ("surely"), fused onto `فِي`.

### 6. `quran:1:1` — `بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:1:1:1` | `بِسْمِ` | preposition + noun | in the name of |
| `quran:1:1:2` | `ٱللَّهِ` | noun (jarr, muḍāf ilayhi) | Allah |
| `quran:1:1:3` | `ٱلرَّحْمَٰنِ` | adjective (intensive) | the Most Merciful |
| `quran:1:1:4` | `ٱلرَّحِيمِ` | adjective (intensive) | the Bestower of mercy |

**Assembled:** "In the name of Allah, the Most Merciful, the Bestower of mercy." `بِسْمِ
ٱللَّهِ` is an iḍāfa governed by `بِـ`; `ٱلرَّحْمَٰنِ`/`ٱلرَّحِيمِ` are two **intensive
adjectives** of root `ر ح م` (see
[`root-pattern-practice.md`](root-pattern-practice.md), item 5), both in jarr to agree.

### 7. `quran:1:2` — `ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَالَمِينَ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:1:2:1` | `ٱلْحَمْدُ` | noun (mubtadaʾ) | (all) praise |
| `quran:1:2:2` | `لِلَّهِ` | `لِـ` + noun (predicate) | (is) for Allah |
| `quran:1:2:3` | `رَبِّ` | noun (muḍāf) | Lord (of) |
| `quran:1:2:4` | `ٱلْعَالَمِينَ` | noun (muḍāf ilayhi, jarr) | the worlds |

**Assembled:** "All praise is for Allah, Lord of the worlds." Nominal sentence: mubtadaʾ
`ٱلْحَمْدُ`, predicate the jār-majrūr `لِلَّهِ`. `رَبِّ ٱلْعَالَمِينَ` is an **iḍāfa** ("of" is
implied, no written particle — see
[`quranic-function-words.md`](quranic-function-words.md), item 4).

### 8. `quran:1:5` — `إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ`

| addr | token | class | gloss |
|---|---|---|---|
| `quran:1:5:1` | `إِيَّاكَ` | object pronoun (fronted) | You alone |
| `quran:1:5:2` | `نَعْبُدُ` | verb (present, "we") | we worship |
| `quran:1:5:3` | `وَإِيَّاكَ` | `وَ` + object pronoun | and You alone |
| `quran:1:5:4` | `نَسْتَعِينُ` | verb (Form X, "we") | we seek help |

**Assembled:** "You alone we worship, and You alone we seek help." The object `إِيَّاكَ`
("You") is **fronted** before its verb for restriction ("…alone"); strip the wāw on
`وَإِيَّاكَ` to read the second clause. `نَسْتَعِينُ` is **Form X** (`ٱسْتَفْعَلَ`, root `ع و ن`,
"seek help") — a derived-form verb (Level 4).

---

## Checklist before you leave āyah reading

- [ ] Do I give every token an **address** and a **class** *before* a gloss?
- [ ] Can I split fused tokens (`إِنَّا` = `إِنَّ` + `نا`; `بِسْمِ` = `بِـ` + `ٱسْمِ`) into their
      pieces?
- [ ] Do I recognize **fronting** (`إِيَّاكَ`) and **oath wāw** (`وَٱلْعَصْرِ`) from the frame,
      not the default?
- [ ] Do I read **derived-form verbs** (Form IV `أَعْطَيْنَا`, Form X `نَسْتَعِينُ`) as such?
- [ ] After labeling, do I assemble the tokens into the right **sentence type** (Level 6)?
- [ ] For any token whose class/sense I cannot certify, do I leave it **blank/PENDING** rather
      than guess?

Carry this token-by-token discipline into longer reading — study a root as a family in
[`qamus-entry-drills.md`](qamus-entry-drills.md), then prose hadith in
[`nawawi40-reading-drills.md`](nawawi40-reading-drills.md). **Address, class, gloss — in that
order; blank beats wrong.**
