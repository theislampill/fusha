# Drills — advanced naḥw

Trains Stages 6–7 of [`zero-to-fluency-nahw.md`](zero-to-fluency-nahw.md): full **iʿrāb**
(case/mood assignment), the naṣb adverbials **ḥāl / tamyīz / badal**, **conditional vs.
emphatic** (`إِنْ` / `إِنَّ`, sharṭ + jawāb), and the **GrammarProblems failure classes** — the
cells where a general LLM collapses. Each item cites its āyah by address (`quran:S:A:W`); the
Qurʾān text is evidence only and never altered (see
[`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md)).

**This tier is gated.** Iʿrāb, case/mood, *lā al-nāfiyah lil-jins*, istithnāʾ, ambiguous
iḍāfa/jār-majrūr, conditional-vs-relative, multi-sense and referent-sensitive readings all
require **two independent checks that agree on conclusion AND reasoning** (`two_vote_required`),
and many are **`never_auto` for the hover** — see [`../procedures/grammar-risk-gate.md`](../procedures/grammar-risk-gate.md)
and [`../evals/grammar-problems-matrix.md`](../evals/grammar-problems-matrix.md). The headline
finding: a free general LLM scored **~33%** on Arabic naḥw and collapsed on deep / essay / iʿrāb
reasoning. **A correct-looking answer with wrong iʿrāb reasoning is unsafe and must not ship.**

---

## §1 — Iʿrāb: case & mood, and the tense flip

**A1.** `لَمْ يَلِدْ` — give the full iʿrāb of `يَلِدْ` and its English tense. *(`quran:112:3:1`)*
- **Reasoning:** `لَمْ` is a jāzim; `يَلِدْ` is muḍāriʿ **majzūm** (jazm shown by sukūn on the
  لام). `لَمْ` + jussive negates the **past**.
- **Answer:** present-form verb, jussive mood, **past meaning** → 'He did not beget'. The mood,
  set by the governor, overrides the surface tense ([`../references/irab-case-mood.md`](../references/irab-case-mood.md)).
- **Gate:** `two_vote_required` (case/mood). Both checks must agree the reading is past-jussive.

**A2.** `إِنَّ ٱللَّهَ غَفُورٌ` — assign the case of `ٱللَّهَ` and `غَفُورٌ`. *(`quran:2:173:18`)*
- **Reasoning:** `إِنَّ` puts its ism in **naṣb** (`ٱللَّهَ`); its khabar stays **rafʿ**
  (`غَفُورٌ`).
- **Answer:** `ٱللَّهَ` = naṣb (ism inna, but still the **subject**); `غَفُورٌ` = rafʿ (khabar
  inna). Do not read the naṣb noun as a verb's object.

**A3.** `أَنْ تَصُومُوا خَيْرٌ لَّكُمْ` — what mood does `أَنْ` impose, and what is the subject of
`خَيْرٌ`? *(`quran:2:184:14`)*
- **Reasoning:** `أَنْ` maṣdariyyah → following verb **subjunctive (naṣb)**; the `أَنْ`+verb is a
  maṣdar muʾawwal serving as the **mubtadaʾ**.
- **Answer:** `تَصُومُوا` = subjunctive (naṣb, nūn dropped) 'that you fast'; the whole clause is
  the topic, `خَيْرٌ` (rafʿ) the predicate → '[that] you fast is better for you'.

---

## §2 — Ḥāl / tamyīz / badal (the naṣb adverbials)

**A4.** `فَتَبَسَّمَ ضَاحِكًا` — what is `ضَاحِكًا`? *(`quran:27:19:1`)*
- **Reasoning:** an indefinite **naṣb** describing the **state** of the doer at the time of the
  act → **ḥāl** (circumstantial).
- **Answer:** ḥāl 'smiling / laughing' → 'so he smiled, laughing'. Not a second verb, not an
  object. The naṣb + indefinite + state-of-doer frame is the signature of a ḥāl.
- **Gate:** `two_vote_required`; a verb gloss on `ضَاحِكًا` is `pending: pos_mismatch`.

**A5.** `وَٱشْتَعَلَ ٱلرَّأْسُ شَيْبًا` — what is `شَيْبًا`? *(`quran:19:4:5`)*
- **Reasoning:** indefinite **naṣb** specifying **in what respect** the statement holds →
  **tamyīz** (specification).
- **Answer:** tamyīz 'with grey hair' → 'and the head has flared up **with** greyness'. Gloss
  the *respect* relation, not bare 'greyness' as an object.

**A6.** `ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ` then `صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ` — what is the
second `صِرَٰط`? *(`quran:1:7:1`)*
- **Reasoning:** it **renames / specifies** the prior noun `ٱلصِّرَٰطَ`, same case (naṣb) →
  **badal** (appositive substitute).
- **Answer:** badal of `ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ` → 'the path of those whom You have favored'.
  It is not a new object; it substitutes for the first.

---

## §3 — Conditional vs. emphatic (sharṭ + jawāb, and the seat)

**A7.** `إِن كُنتُمْ صَٰدِقِينَ` — is this `إِنْ` conditional or the negating `إِنْ`? *(`quran:2:23:13`)*
- **Reasoning:** `إِنْ` (kasra-seat, **no** shadda — distinct from emphatic `إِنَّ`) + a clause
  that wants an apodosis → **conditional 'if'**.
- **Answer:** conditional 'if you are truthful'; the jawāb is supplied by the surrounding
  command. Separated from `إِنَّ` by the **shadda on the nūn** (`shadda_on(t,"ن")` → False) and
  the seat (`norm_strict` keeps it). Bare `إِنْ` with an unclear frame → `pending: multi_sense`.

**A8.** `فَمَن يَعْمَلْ مِثْقَالَ ذَرَّةٍ خَيْرًا يَرَهُۥ` — identify the sharṭ, its jawāb, and
the moods. *(`quran:99:7:1`)*
- **Reasoning:** `مَنْ` is a **conditional** (relative-conditional) putting **two** verbs in
  **jussive**: the sharṭ `يَعْمَلْ` and the jawāb `يَرَ(هُ)`.
- **Answer:** sharṭ 'whoever does an atom's weight of good', jawāb 'will see it'; both jussive
  by `مَنْ`. `خَيْرًا` is naṣb (tamyīz/specification of `مِثْقَالَ ذَرَّةٍ`). Distinguishing
  conditional `مَنْ` from relative `مَنْ` is a **`two_vote` / conditional-vs-relative** cell.
- **Gate:** `two_vote_required`; if the jawāb's mood is unreadable → `pending`.

**A9.** `إِنَّمَا ٱلْمُؤْمِنُونَ إِخْوَةٌ` — what does `إِنَّمَا` do? *(`quran:49:10:1`)*
- **Reasoning:** `إِنَّ` + `مَا` kāffah (restrictive) = `إِنَّمَا` → **emphatic restriction**
  'only / none but'. Not a conditional.
- **Answer:** 'The believers are but brothers' (restriction). `ٱلْمُؤْمِنُونَ` rafʿ (the kāffah
  `مَا` neutralizes inna's naṣb-government), `إِخْوَةٌ` rafʿ khabar.

---

## §4 — The GrammarProblems failure classes (where the model collapses)

These are the cells the 2026 study flagged as the model's worst — deep, essay, iʿrāb, advanced.
Each is `two_vote_required` and most are **`never_auto`** for the hover.

**A10.** `لَا إِلَٰهَ إِلَّا ٱللَّهُ` — iʿrāb of `إِلَٰهَ` and the role of `إِلَّا`. *(istithnāʾ + lā lil-jins)*
- **Reasoning:** `لَا` of genus → `إِلَٰهَ` is **naṣb** (no tanwīn, mabnī on fatḥa as ism lā);
  `إِلَّا` is **istithnāʾ** (exception); `ٱللَّهُ` is **rafʿ** (badal from the maḥall of ism lā,
  the muthnā minhu being raised).
- **Answer:** 'there is no deity **except** Allah' — *lā al-nāfiyah lil-jins* + istithnāʾ.
- **Gate:** `two_vote_required` + **`never_auto`** (both *lā lil-jins* and istithnāʾ are the
  study's worst areas). `إِلَّا` (shadda on lām + hamza seat) is **not** `لَا`.

**A11.** `حَلِيمٌ` describing Ibrāhīm vs. as a Name — give the gloss register and the guard.
*(`quran:11:75:4` — `إِنَّهُۥ … حَلِيمٌ`)*
- **Reasoning:** **referent guard** — resolve who is described **before** choosing the register.
  Here the referent is Ibrāhīm (a human).
- **Answer:** 'forbearing' (a human virtue) — **never** typeset as a Divine Name when the
  referent is human. Referent = Allah elsewhere → 'the Forbearing' (a Name).
- **Gate:** `referent_unresolved` → `pending` if the referent is not fixed; **`never_auto`**.

**A12.** `يَبْسُطُ ٱلرِّزْقَ لِمَن يَشَآءُ وَيَقْدِرُ` — gloss `يَقْدِرُ`. *(`quran:13:26:4`)*
- **Reasoning:** **contronym** — `يَقْدِرُ` defaults to 'is able', but the contrast frame with
  `يَبْسُطُ` ('expands provision') flips it.
- **Answer:** **'restricts / straitens'** (the rizq contrast), not 'is able'. Detect the
  `بسط`/`قدر` pairing in the same āyah; absent the cue → `pending: contronym`.
- **Gate:** `two_vote_required` (multi-sense/contronym); never default to the common sense
  against the clause ([`../drills/sentence-context.md`](../drills/sentence-context.md) §5).

**A13.** `رَسُولًا` (e.g. `وَأَرْسَلْنَٰكَ … رَسُولًا`) — verb 'to send' or noun? *(`quran:4:79:9`)*
- **Reasoning:** **POS/iʿrāb guard** — `رَسُولًا` is an indefinite **naṣb noun** (object/ḥāl
  position), not the verb root ر-س-ل. A jarr/naṣb noun cannot take a *verb* gloss.
- **Answer:** 'a messenger' (noun, naṣb). A verb gloss is rejected → `pending: pos_mismatch`.
  Same class: `مُحَمَّد` ≠ 'to praise', `ٱبْن` ≠ 'to build', `صَٰلِحًا` (indef. naṣb adjective) ≠
  the Prophet Ṣāliḥ ([`../drills/sentence-context.md`](../drills/sentence-context.md) §6).
- **Gate:** proper-vs-common / pos_mismatch → **`never_auto`**.

---

## Advanced gate (clear before claiming Stage-7 fluency)

For each item you must produce, for the cited token, **all four**: (1) root/POS, (2) case/mood
with the **governor** that assigns it, (3) the syntactic role (subject / object / ḥāl / tamyīz /
badal / ism-or-khabar of a governor), and (4) the cited authored gloss — **or** the most
specific `pending:` reason.

| failure class | gate | hover |
|---|---|---|
| iʿrāb (case/mood) | `two_vote_required` | `never_auto` |
| *lā al-nāfiyah lil-jins* / istithnāʾ | `two_vote_required` | `never_auto` |
| conditional vs. relative | `two_vote_required` | `pending_if_reason_uncertain` |
| ḥāl / tamyīz / badal (naṣb adverbials) | `two_vote_required` | `pending_if_reason_uncertain` |
| contronym / multi-sense | `two_vote_required` | `pending_if_reason_uncertain` |
| referent / proper-vs-common | `two_vote_required` | `never_auto` |

**Pass condition:** no token carries a confident wrong reading, **and** for every gated cell the
two independent checks agree on **conclusion and reasoning** — the bar
[`../procedures/grammar-risk-gate.md`](../procedures/grammar-risk-gate.md) enforces. A
correct-looking answer with wrong iʿrāb reasoning **fails** the gate. **PENDING beats a wrong
gloss, always.**
