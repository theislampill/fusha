# Maṣdar vs. participle vs. finite verb — the gloss‑shape rule

The single most common wrong‑gloss class in qamus‑highlight is **putting a finite‑verb gloss on a word that is
morphologically a noun** (a maṣdar or a participle). The charts make the distinction explicit by giving each its
own column ("verbal idea in the form of a noun", "person who does the act", "person/thing the act is intended
toward"). Encode the distinction as a gloss‑shape contract.

## The three nominal derivations

| derivation | Arabic | pattern (Form I) | gloss shape | example |
|---|---|---|---|---|
| maṣdar (verbal noun) | المصدر | *samāʿī* for I; قياسي for II–X | "the act/state of …" (a noun) | ذِكْر "remembrance", عِلْم "knowledge", اِسْتِغْفَار "seeking forgiveness" |
| ism fāʿil (active participle) | اسم الفاعل | فَاعِل (I); مُفْعِل/مُفَعِّل… (derived) | "the one who …" / "…‑ing one" | كَاتِب "writer", مُؤْمِن "believer", مُسْلِم "one who submits" |
| ism mafʿūl (passive participle) | اسم المفعول | مَفْعُول (I); مُفْعَل/مُفَعَّل… (derived) | "the one/thing …‑ed" | مَكْتُوب "written/decreed", مَخْلُوق "created", مَرْحُوم "shown mercy" |

## Decision rules

1. **A maṣdar is a noun. Gloss it nominally.** ذِكْر → "remembrance" (never "he remembered"); تَحْرِير → "freeing"
   (never "to free"); إِنفَاق → "spending". If you have a maṣdar surface and the candidate gloss is a finite verb,
   the gloss is wrong — re‑shape it or mark pending.
2. **A participle is an agent/patient noun.** مُؤْمِنُونَ → "believers" (not "they believe"); كَافِرِينَ →
   "disbelievers"; مَخْلُوق → "created thing". A verb infinitive on a participle is the §principle‑3 POS‑mismatch
   blocker (`رَسُولًا ≠ "to send"`).
3. **Derived‑form participles share the مُـ prefix** but split active/passive by the **last‑radical vowel**:
   مُعَلِّم "teacher" (kasra, fāʿil) vs مُعَلَّم "taught one" (fatḥa, mafʿūl); مُنزِل "sender‑down" vs مُنزَل "sent
   down". Read the vowel before choosing the gloss.
4. **Maṣdar ↔ verb homographs are vowel‑only.** ذِكْر (maṣdar, "remembrance") vs ذَكَر ("male") vs ذَكَرَ ("he
   mentioned") — same skeleton ذ‑ك‑ر, three different words. Decide on the harakāt; if undecidable → pending. (This
   is the exact P5 homograph that had to be pulled back from the live batch.)
5. **The Form‑I maṣdar is *samāʿī*** (not predictable) — it must be learned per verb from the Qamus entry, never
   generated. Forms II–X maṣdars are *qiyāsī* (regular per [`verb-measures.json`](../rules/verb-measures.json)).

## Hand‑off

`pos` in the sarf output object must carry `masdar` / `ism_fa3il` / `ism_maf3ul` (not just `verb`/`noun`) when the
shape is one of these, so the authoring step picks the right gloss shape and the QAC POS filter can drop a "to …"
verb gloss landing on a derived noun.
