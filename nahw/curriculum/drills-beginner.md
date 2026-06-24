# Drills — beginner naḥw

Trains Stages 1–2 and 5 of [`zero-to-fluency-nahw.md`](zero-to-fluency-nahw.md): **identify the
particle**, **find a preposition and its object**, and **split a nominal sentence into subject
(mubtadaʾ) and predicate (khabar)**. Every item is built from a real āyah, cited by word address
(`quran:S:A:W` — surah:ayah:word). The Qurʾān text is evidence only and never altered; the
address points back without copying (see [`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md)).

**Procedure first:** read the question, decide from the **content letter's harakah** and the
syntactic frame, then check the answer. When undiacritized input would collapse a homograph,
the correct beginner answer is `pending: homograph_haraka` — guessing is the failure.

> Cited so you can verify each form against its position: e.g. `quran:112:1:1` = Sūrah 112,
> āyah 1, word 1. Glosses are authored; the public render is `{src:'qamus', kind:'authored'}`.

---

## §1 — Identify the particle (read the content letter)

**B1.** `قُلْ هُوَ ٱللَّهُ أَحَدٌ` — classify `هُوَ`. *(`quran:112:1:3`)*
- **Answer:** detached pronoun (ḍamīr munfaṣil), 3rd-person masc. sing., mubtadaʾ here → 'He'.
  Mabnī (no iʿrāb). Not a particle proper, but the closed function-word set.

**B2.** `وَٱلْعَصْرِ` — is the `وَ` 'and' or an oath 'by'? *(`quran:103:1:1`)*
- **Answer:** **oath wāw** (wāw al-qasam): clause-initial, followed by a noun in **jarr**
  (`ٱلْعَصْرِ`) with no preceding verb → gloss **'by'**. Strip the proclitic before judging.

**B3.** `لَمْ يَلِدْ وَلَمْ يُولَدْ` — what is `لَمْ`? *(`quran:112:3:1`)*
- **Answer:** negation particle `لَمْ` (lām carries **fatḥa**, mīm **sukūn**) → 'did not'; it
  forces the following verb into the **jussive** with **past** meaning. Not `لِمَ` 'why' (which
  has kasra on the lām).

**B4.** `إِنَّ ٱلْإِنسَٰنَ لَفِى خُسْرٍ` — what is `إِنَّ`? *(`quran:103:2:1`)*
- **Answer:** emphatic `إِنَّ` (kasra-seat hamza + shadda on the nūn) → 'indeed / verily'; it
  puts the following noun (`ٱلْإِنسَٰنَ`) in **naṣb** as its subject. Not `أَنَّ` (fatḥa-seat).

**B5.** `وَمِنَ ٱلنَّاسِ` — 'and whoever' or 'and from'? *(`quran:2:8:1`)*
- **Answer:** **'and from'** — `وَ` + `مِنَ` (kasra on the **م**, no shadda). The first letter
  is the proclitic `و`; read the content letter. `is_man_who("وَمِنَ")` → False.

**B6.** `قَدْ أَفْلَحَ ٱلْمُؤْمِنُونَ` — what is `قَدْ` + past verb? *(`quran:23:1:1`)*
- **Answer:** particle of certainty `قَدْ` + a past verb → 'indeed / certainly' (have
  succeeded). With a present verb `قَدْ` means 'sometimes / may' — frame decides.

---

## §2 — A preposition and its object (the object is jarr)

**B7.** `بِسْمِ ٱللَّهِ` — name the preposition and its object. *(`quran:1:1:1`)*
- **Answer:** preposition `بِـ` ('in the name of' here) governs `ٱسْمِ` in **jarr**; the iḍāfa
  `ٱسْمِ ٱللَّهِ` makes it 'the name of Allah'. The object of a preposition can never be a verb.

**B8.** `فِى قُلُوبِهِم مَّرَضٌ` — preposition + its object. *(`quran:2:10:1`)*
- **Answer:** `فِى` 'in' governs `قُلُوبِ` (jarr) — itself a muḍāf to the pronoun `ـهِم`
  ('their hearts'). Phrase gloss: 'in their hearts'. `مَّرَضٌ` (rafʿ) is a separate word.

**B9.** `عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ` — render `عَلَيْهِمْ`. *(`quran:1:7:2`)*
- **Answer:** `عَلَى` + attached pronoun `ـهِمْ` → **'upon them / against them'**; the pronoun
  changes the wording, not the head sense. Object is jarr by the preposition.

**B10.** `إِلَيْنَا` (e.g. `… أُنزِلَ إِلَيْنَا`) — what root, what gloss? *(`quran:2:136:13`)*
- **Answer:** `إِلَى` + `نا` → **'to us'**, root **أ-ل-ي**. **Guard:** it is **not** root ل-ي-ن
  ('soft') — the hamza seat that `norm()` drops is load-bearing; certify on `norm_strict`. The
  final `ـنا` is a fixed pronoun, not a declensional ending.

**B11.** `لَهُۥ مُلْكُ ٱلسَّمَٰوَٰتِ` — render `لَهُ`. *(`quran:2:107:2`)*
- **Answer:** `لِـ` + `ـهُ` → **'for Him / to Him belongs'**; possessive frame. The lām of
  belonging takes a jarr pronoun. Gloss the relationship, not bare 'for'.

---

## §3 — Subject (mubtadaʾ) and predicate (khabar)

**B12.** `ٱللَّهُ نُورُ ٱلسَّمَٰوَٰتِ` — split mubtadaʾ / khabar. *(`quran:24:35:1`)*
- **Answer:** nominal sentence. **Mubtadaʾ:** `ٱللَّهُ` (rafʿ, the topic). **Khabar:** `نُورُ
  ٱلسَّمَٰوَٰتِ` (rafʿ, an iḍāfa). 'Allah is the Light of the heavens.'

**B13.** `وَٱللَّهُ غَفُورٌ رَّحِيمٌ` — find subject and predicate(s). *(`quran:2:173:18`)*
- **Answer:** mubtadaʾ `ٱللَّهُ` (rafʿ); two khabars `غَفُورٌ` and `رَّحِيمٌ` (both rafʿ,
  tanwīn) → 'And Allah is Forgiving, Merciful'. The `وَ` is the conjunction 'and'.

**B14.** `هُوَ ٱلْحَىُّ` — what is the structure? *(`quran:40:65:1`)*
- **Answer:** mubtadaʾ `هُوَ` (detached pronoun, mabnī, rafʿ position) + khabar `ٱلْحَىُّ`
  (rafʿ) → 'He is the Ever-Living'. Nominal sentence; no verb.

**B15.** `إِنَّ رَبَّكَ لَبِٱلْمِرْصَادِ` — does `إِنَّ` change the topic's case? *(`quran:89:14:1`)*
- **Answer:** yes — `إِنَّ` puts the topic in **naṣb** (`رَبَّكَ`, ism of inna) and its khabar
  is the jār-majrūr `بِٱلْمِرْصَادِ` (lām of emphasis prefixed) → 'Indeed your Lord is
  ever-watchful'. Even though it heads a nominal clause, do **not** read `رَبَّكَ` as an object.

---

## Beginner drill rule

1. **Strip proclitics** (`و`/`ف`/`بـ`/`لـ`) before reading the decisive harakah.
2. The **object of a preposition is always jarr** — a verb gloss after a preposition is wrong.
3. In a nominal sentence, the **first noun is the topic (mubtadaʾ)**, not a verb's object —
   unless `إِنَّ`-family precedes, which puts the topic in naṣb but keeps it the subject.
4. Undiacritized input that collapses a homograph (`مَن/مِن`, `لَمْ/لِمَ`) → `pending:
   homograph_haraka`. **A precise pending beats a guess.**

Climb to [`drills-intermediate.md`](drills-intermediate.md) after clearing Checkpoints 1, 2,
and 5 in [`zero-to-fluency-nahw.md`](zero-to-fluency-nahw.md).
