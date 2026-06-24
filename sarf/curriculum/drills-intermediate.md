# Drills — intermediate ṣarf

The middle rung ([`zero-to-fluency-sarf.md`](zero-to-fluency-sarf.md), stages 3–6). Three
skills: **(A) name the verb form I–X**, **(B) maṣdar vs participle (gloss-shape)**, and
**(C) weak-root recovery (recover the hidden radical)**. You should already recover sound
radicals and read a wazn ([`drills-beginner.md`](drills-beginner.md)).

Each drill names the **procedure that solves it** — not as a footnote but as the method you run.
Cover the answer; decide form / shape / root; then check the reasoning *and* the procedure.

> The form, the voice, and the class each change the English. A root match is **necessary, not
> sufficient** — bind to the entry/sense whose **form** fits. Carry the discipline of
> [`../README.md`](../README.md): `norm()` proposes, harakāt/QAC certify.

---

## Part A — name the verb form (I–X)

The augment letters select the verb: shadda → II, hamza → IV, `اِسْتَـ` → X, `نـ` → VII,
infixed `ت` → VIII. Same root, different augment, **different verb** — never the Form I sense.

**Procedure:** [`../procedures/verb-form.md`](../procedures/verb-form.md) (measure → voice →
person/number), paradigm
[`../references/verb-measures-table.md`](../references/verb-measures-table.md), machine rules
[`../rules/verb-measures.json`](../rules/verb-measures.json).

| # | surface | root | answer | reasoning · procedure step |
|---|---|---|---|---|
| A1 | `نَزَلَ` | `ن ز ل` | **Form I** — "descended" | bare `فَعَلَ` stem, no augment → base sense. *verb-form §1* |
| A2 | `نَزَّلَ` | `ن ز ل` | **Form II** — "sent down (gradually)" | shadda on C2 = `فَعَّلَ` → causative/intensive; never the I sense. *§1 (shadda)* |
| A3 | `أَنزَلَ` | `ن ز ل` | **Form IV** — "sent down" | initial hamza `أَفْعَلَ` → causative; the `أ` is an augment, not a radical. *§1 (hamza)* |
| A4 | `عَلَّمَ` | `ع ل م` | **Form II** — "taught" | shadda → causative of `عَلِمَ` "knew". *§1* |
| A5 | `اِسْتَعْلَمَ` | `ع ل م` | **Form X** — "sought to know / enquired" | `اِسْتَـ` prefix = `اِسْتَفْعَلَ` → "seek/consider". *§1 (استَ)* |
| A6 | `اِخْتَلَفَ` | `خ ل ف` | **Form VIII** — "differed" | infixed `ت` after C1 = `اِفْتَعَلَ`; the connecting `ٱ` is hamzat al-waṣl, not a radical. *§1* |
| A7 | `اِنقَلَبَ` | `ق ل ب` | **Form VII** — "turned back" | `نـ` after the waṣl-alif = `اِنفَعَلَ` → medio-passive. *§1* |

**Rule:** strip the augment(s) to the root, then read the augment to fix the form and sense.
A Form-I gloss on a derived form is the canonical defect →
[`../rules/verb-measure-gates.json`](../rules/verb-measure-gates.json) (gate it `two_vote` when
the form drives the sense).

---

## Part B — maṣdar vs participle (gloss-shape)

A maṣdar and a participle are **nouns**: they take a noun gloss, never "to …". The derived
مُـ participles split active/passive by the **penult (last-radical) vowel**.

**Procedure:** [`../procedures/noun-plural-gender.md`](../procedures/noun-plural-gender.md),
reference [`../references/masdar-participle-notes.md`](../references/masdar-participle-notes.md),
gates [`../rules/masdar-participle-gates.json`](../rules/masdar-participle-gates.json).

| # | surface | shape | gloss-shape | reasoning · procedure step |
|---|---|---|---|---|
| B1 | `ذِكْر` | maṣdar (`فِعْل`) | "remembrance" (noun) | maṣdar = the *action as a noun*; **never** "he remembered". *noun §1* |
| B2 | `اِسْتِغْفَار` | maṣdar (X, `اِسْتِفْعَال`) | "seeking forgiveness" | qiyāsī maṣdar of Form X; nominal. *masdar-notes §5* |
| B3 | `كَاتِب` | ism fāʿil (`فَاعِل`) | "writer / one who writes" | active participle = the *doer*; noun. *noun §1* |
| B4 | `مُؤْمِنُونَ` | ism fāʿil (Form IV, sound pl.) | "believers" | doer-noun + sound masc. plural `ـُونَ`; **never** "they believe". *noun §1–2* |
| B5 | `مَخْلُوق` | ism mafʿūl (`مَفْعُول`) | "created thing" | passive participle = the *done-to*; noun. *noun §1* |
| B6 | `مُعَلِّم` / `مُعَلَّم` | fāʿil / mafʿūl (Form II) | "teacher" / "taught one" | same مُـ skeleton; **penult vowel decides** (kasra = doer, fatḥa = done-to). *masdar-notes §3* |
| B7 | `بَغْضَاء` (src `qamus:n300`) | noun (`فَعْلَاء`) | "intense hatred" | nominal pattern, class `n`; a "to hate" gloss is a POS-mismatch. *noun §1* |

**Rule:** classify the nominal (`masdar` / `ism_fa3il` / `ism_mafʿul`) **before** choosing
vocabulary; a finite-verb gloss on any of them is the §3 POS-mismatch blocker (`رَسُولًا` ≠
"to send").

---

## Part C — weak-root recovery (recover the hidden radical)

A weak/hamzated/doubled radical hides in the surface. Recover it from the **family** (the
muḍāriʿ / QAC / the entry), never from a `norm()` collapse.

**Procedure:** [`../procedures/root-decision.md`](../procedures/root-decision.md) (weak-root
branch), reference [`../references/weak-verbs.md`](../references/weak-verbs.md), gates
[`../rules/weak-root-gates.json`](../rules/weak-root-gates.json).

| # | surface | class | recovered root | how to recover · procedure step |
|---|---|---|---|---|
| C1 | `قَالَ` | hollow (C2) | `ق و ل` | CāC past hides C2; muḍāriʿ `يَقُولُ` reveals `و`. *weak-verbs rule 1* |
| C2 | `زَاغَ` (src `qamus:v509`) | hollow (C2) | `ز ي غ` | the `ا` is medial `ي`; muḍāriʿ `يَزِيغُ` reveals `ي` — entry certifies. *rule 1* |
| C3 | `أَقَامَ` | hollow + Form IV | `ق و م` | Form IV of a hollow root **drops the medial**; recover from family, gloss "established". *rule 1* |
| C4 | `يَجِدُ` | assimilated (C1) | `و ج د` | present `يَفْعِل` with no visible C1 → suspect a `و`-initial root that drops in the muḍāriʿ. *rule 3* |
| C5 | `دَعَا` | defective (C3) | `د ع و` | final `ا` is the weak C3; `دَعَوْتُ` shows the `و`. Don't treat `ا/ى/ي` as a stable last radical. *rule 2* |
| C6 | `خَفَّت` (src `qamus:v379`) | doubled (geminate) | `خ ف ف` | shadda merges C2=C3; expand before counting — triliteral, not biliteral. *rule 4* |
| C7 | `حَاشَ لِلَّه` (src `qamus:n575`) | defective (C3) | `ح ش ي` | the final weak radical `ي` is hidden in the surface; the entry's root certifies it. *rule 2* |

**Rule:** never assert a weak root by **subsequence match** (the Nawawī40 ~50% false-tie
lesson — [`../procedures/root-decision.md`](../procedures/root-decision.md) *Forbidden*). When
the radical stays hidden and no family form/QAC certifies it, emit **pending** with the precise
reason (`hollow_root_c2_hidden`, `defective_c3_alternation`, `assimilated_c1_dropped`,
`geminate_shadda`).

---

## Bonus — negation rewrites the tense

A governing negative, not the surface tense, sets the English. (Cross-skill into nahw.)

| # | surface | answer | reasoning |
|---|---|---|---|
| D1 | `لَمْ يَلِدْ` | "He did not beget" (PAST) | `لَمْ` + jussive → past meaning, despite the imperfect shape. |
| D2 | `لَنْ يَفْعَلُوا` | "they will never do" (FUTURE) | `لَنْ` + subjunctive → emphatic future. |

→ [`../../nahw/rules/negation-rules.json`](../../nahw/rules/negation-rules.json).

---

## Checklist before you call an intermediate drill "done"

- [ ] Did I **strip every augment** to the root, then **read the augment** to set the form?
- [ ] Did I give a **finite** English with the right person/number/gender (Part A) — not a bare
      infinitive on a conjugated verb?
- [ ] Did I check the **voice** (ḍamma–kasra = passive) before wording?
- [ ] For a maṣdar/participle, is the gloss **nominal** (never "to …")? Did the **penult vowel**
      pick active vs passive (Part B6)?
- [ ] Did I **recover** the hidden radical from the family/QAC, not from `norm()` (Part C)?
- [ ] Where form/voice/sense was uncertain, did I gate at `two_vote` or go **pending**?

Advance to [`drills-advanced.md`](drills-advanced.md) only when Parts A–C are reliable. When in
doubt: **PENDING beats wrong.**
