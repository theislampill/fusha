# Drill — the jarr clitic لِـ on noun hosts (P00 pilot family)

**Goal:** recognize the little lām that puts the next word in jarr — and refuse its three
look-alikes. Built from the first fully certified particle family (p007 لِـ, entry
`b10a1ee04666`, sense 2): every item cites its āyah **source-address** (`quran:S:A:W`, per
[`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md));
the Qurʾān text is evidence only and never altered.

**Rule of the drill:** read the **host**, not the lām. A لِ with kasra is only the jarr
preposition when the word after it is a noun; a lexical word (لِبَاسٌ), a verb (لِيَغِيظَ), or a
pronoun (لِى) each changes the answer. Skill rules:
`sarf-li-kasra-noun-host-clitic-carve`, `sarf-lexical-initial-lam-madda-guard`,
`nahw-lam-talil-vs-jarr-host-pos` (@2.4 candidates,
[`../../qamus/skills/rule-registry-increment-24.jsonl`](../../qamus/skills/rule-registry-increment-24.jsonl)).
For rich-hover work the clitic's class is `qg-particle-jarr-clitic`, never a generic particle
color, and the clitic/host boundary must be visible at rest.

---

## Items

### 1. Jarr-clitic recognition — `لِلْمَلَٰٓئِكَةِ` — `quran:2:34:3`
"وَإِذْ قُلْنَا **لِلْمَلَٰٓئِكَةِ** ٱسْجُدُوا۟" — carve the token and name each piece's job.
- **Procedure:** strip the لِ (kasra, before a noun) → host الملائكة with the assimilated
  article's lām written. Three spans: clitic لِ ∣ article ل ∣ host. The lām governs the noun into
  **jarr, sign kasra**; the governor of الملائكة is **the preposition itself**.
- **Answer:** "to the angels" — لِ = "to/for" (jarr clitic), host = "the angels" (majrūr,
  kasra). A hover showing only "angels" hides the lesson.
- **Test yourself:** same carve for `لِلَّهِ` (`quran:12:31:24`) — where does the clitic's span
  end? → after its OWN lām+kasra only (لِ ∣ لَّهِ); the fused writing of the Name owns the rest.

### 2. Lexical-lām contrast — `لِبَاسٌ` vs `لِلنَّاسِ` — `quran:2:187:9` / `quran:2:187:63`
The SAME āyah carries both: "هُنَّ **لِبَاسٌ** لَّكُمْ … أُحِلَّ **لِلنَّاسِ**" (host phrases).
Which initial lām is the preposition?
- **Procedure:** check the host's مادة. لِبَاسٌ is ONE noun — the lām is the first ROOT radical
  of ل ب س (wazn فِعَال), and the iʿrāb shows a khabar with **no jarr clause**: no carve, no
  particle. لِلنَّاسِ = لِ + ٱلنَّاسِ (مادة ن و س): a real jarr clitic over "the people".
- **Answer:** لِبَاسٌ = "a garment" (whole word, tanwīn ḍamma — rafʿ); لِلنَّاسِ = "for the
  people" (jarr, kasra). **Never** gloss لِبَاسٌ as "to + بَاس".
- **Test yourself:** `لِيَغِيظَ` (`quran:48:29:42`) — noun? → No: a verb (muḍāriʿ manṣūb), so
  the lām is **purpose** ("so that he may enrage"), not jarr. And `لِى` (`quran:31:14:14`)? →
  jarr over a **pronoun**: real preposition, but no noun host and no root anywhere in the token.

### 3. Diptote sign — `لِءَادَمَ` — `quran:2:34:5`
"ٱسْجُدُوا۟ **لِءَادَمَ**" — the lām puts آدم in jarr… so why is the last vowel a **fatḥa**?
- **Procedure:** آدم is a ممنوع من الصرف (diptote) proper name: it takes no tanwīn and shows its
  jarr with a **fatḥa** instead of a kasra. The government is unchanged — لِ still governs the
  name in jarr; only the SIGN differs.
- **Answer:** "to Adam" — jarr whose sign is fatḥa **because the name is a diptote**. A hover
  that says "kasra" here by template is wrong; a hover that says "fatḥa" without the *because*
  teaches nothing.
- **Test yourself:** in `لِلْمَلَٰٓئِكَةِ` (item 1) the sign IS a kasra — state both rules in one
  sentence: *jarr shows as kasra, except a diptote shows it as fatḥa.*
