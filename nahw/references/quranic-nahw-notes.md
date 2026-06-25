# references — Qurʾānic nahw notes (case, mood, conditionals, relatives, referent guard)

Concise, gloss-facing syntax reference for the disambiguator. Not a full grammar — only the
nahw facts that change a hover gloss or a PENDING reason. Cross-referenced from the drills.
All examples are evidence only; no external gloss text is reproduced (external corpora named
as `informed_by` only). The public hover artifact emits only `{src:'qamus', kind:'authored', lang:'en'}`.

---

## 1. Iʿrāb — case (for nouns) and mood (for verbs)

### Noun case (الْإِعْرَاب)

| case | name | typical marker | what it tells the gloss layer |
|---|---|---|---|
| **rafʿ** (nominative) | مَرْفُوع | ـُ / ـٌ (or ـُونَ، ـَانِ) | subject / mubtadaʾ / khabar — a *doer or topic*, not an object |
| **naṣb** (accusative) | مَنْصُوب | ـَ / ـً (or ـِينَ، ـَيْنِ) | object / ḥāl / the subject of `إِنَّ` — governed |
| **jarr** (genitive) | مَجْرُور | ـِ / ـٍ (or ـِينَ) | after a preposition **or** muḍāf ilayh ⇒ **a noun, never a verb** |

**Strongest single guard:** a token with a **jarr** ending (after a preposition or as muḍāf
ilayh) **cannot carry a verb gloss**. A verb-root candidate for a jarr noun → reject,
`pending: pos_mismatch`. (This is why `فِي … رَسُولًا` style verb-glosses are spurious, and why
`رَسُولًا` — naṣb, ـً — reads 'a messenger', not 'to send'.)

### Verb mood (when the verb is muḍāriʿ)

| mood | name | marker | trigger |
|---|---|---|---|
| **rafʿ** (indicative) | مَرْفُوع | ـُ / ـُونَ | default present, no governor |
| **naṣb** (subjunctive) | مَنْصُوب | ـَ / drop ـنَ | `أَنْ`, `لَنْ`, `كَيْ`, `حَتَّى` |
| **jazm** (jussive) | مَجْزُوم | sukūn / drop ـنَ | `لَمْ`, `لَا` (nāhiyah), conditional particles |

Mood reads back onto the particle: a **jazm** verb after `لَمْ` confirms negated-past
('did not …'); a **naṣb** verb after `أَنْ` confirms maṣdariyyah ('to …'). Use the mood to
*confirm* the particle gloss chosen in `particles.md`.

---

## 2. Conditional sentences (الشَّرْط)

Structure: **conditional particle + protasis (šarṭ) + apodosis (jawāb)**.

| particle | gloss | both clauses' verbs |
|---|---|---|
| `إِنْ` | 'if' | **jazm** (jussive) |
| `إِذَا` | 'when / if' (more certain) | usually past in form, future in sense |
| `مَنْ` (conditional) | 'whoever' | jazm |
| `مَا` (conditional) | 'whatever' | jazm |
| `لَوْ` | 'if (counterfactual)' | past; implies the apodosis did **not** happen |

Parse effects for the gloss layer:
- A **`فَـ`** at the head of the second clause is often the **apodosis fāʾ** ('then …') — a
  signal of where the jawāb starts; surface gloss stays 'then/so' (see `particles.md`).
- `لَوْ` flags a **counterfactual** — the clause states something contrary to fact; helpful
  context for senses but does not change individual word glosses.
- After a conditional `مَنْ` ('whoever') / `مَا` ('whatever'), the verb is **jazm** — confirm
  via the mood ending; this also confirms `مَنْ` is the conditional/relative reading, not the
  preposition `مِنْ` (`is_man_who` already separates them).

---

## 3. Relative pronouns (الْأَسْمَاء الْمَوْصُولَة)

A relative pronoun fills a noun slot and heads a relative clause (ṣilah). Its gloss is
'who / which / that', agreeing in number/gender:

| pronoun | gloss | number/gender |
|---|---|---|
| `الَّذِي` | 'the one who / which' | masc. sing. |
| `الَّتِي` | 'the one who / which' | fem. sing. |
| `الَّذِينَ` | 'those who' | masc. plural |
| `مَنْ` (relative) | 'the one who / whoever' | for persons |
| `مَا` (relative) | 'that which / what' | for non-persons |

Gloss-layer notes:
- `مَنْ` / `مَا` are *also* interrogative and (for `مَا`) negating — relative vs. the others is
  frame-decided (`particles.md`, `sentence-context.md`). When unclear → `pending: multi_sense`.
- The relative clause's verb often hosts a **return pronoun** (ʿāʾid) referring back to the
  antecedent; that clitic's English (it/him/them) tracks the antecedent, not the clitic shape
  alone (see referent guard, §4).
- `الَّذِي`-family are **not** broken to a root — they are function words; gloss as wholes.

---

## 4. The referent guard (الْمَرْجِع) — resolve *who/what* before the register

Two glosses for one surface, decided by the referent. This guard prevents the two worst
register errors: importing Divine-Name connotations onto a human, and importing a verb gloss
onto a proper name.

1. **Attribute → human vs. Allah.** A perfection-adjective glosses as a plain virtue for a
   human and as a Name for Allah. `حَلِيمٌ` of **Ibrāhīm** = **'forbearing'** (a human
   attribute, *not* a Divine Name); of Allah = 'the Forbearing'. Resolve the referent first;
   if unresolved, `pending: referent_unresolved` — never default to the Name.

2. **Proper name → not the homographic verb.** `مُحَمَّد` ≠ 'to praise'; `صَٰلِحًا` (indefinite
   naṣb adjective) = 'a righteous (deed)' and is **not** the Prophet **Ṣāliḥ** (a definite
   name in a Thamūd narrative). Name/attribute frame ⇒ name/adjective reading,
   `pending: proper_name` if ambiguous. (See `sentence-context.md` §6–§7.)

3. **Return/clitic pronoun → antecedent governs the English.** `بِهِ` 'with it / in it',
   `لَهُ` 'for him / to him' — the it/him choice follows the antecedent's gender/animacy, not
   the clitic alone (see `idafa-and-jar-majrur.md`).

---

## 5. The norm() / seat regressions — checklist (hard-won)

`norm()` is recall-only: it strips tashkīl **and drops the hamza seat**, folds ى→ي، ة→ه. It
**must not, on its own, certify a root, sense, or gloss.** Use `norm_strict()` (keeps the
seat) or QAC-style evidence to certify; prefer **PENDING** over a wrong gloss. The cases that
have actually bitten:

| input | wrong match | why | guard |
|---|---|---|---|
| `إِلَيْنَا` | root ل-ي-ن ('soft') | seat dropped; it is `إِلَى`+`نا` 'to us' | `norm_strict` keeps seat; `seat_collapsed` |
| `إيمان` ↔ `أيمان` | conflated | إِ vs أَ seat dropped ('faith' vs 'oaths') | `norm_strict` |
| `يَأْمُرُونَ` ↔ `يَمُرُّونَ` | conflated | hamza/shadda dropped ('command' vs 'pass by') | `norm_strict` / shadda |
| `رَسُولًا` | verb 'to send' | naṣb **noun** after a verb of doing | `pos_mismatch` (case) |
| `ٱبْن` / `بَنَات` | verb 'to build' | nouns 'son/daughters', not ب-ن-ي verb | `pos_mismatch` |
| `مُحَمَّد` | verb 'to praise' | proper name | `proper_name` |
| `صَٰلِحًا` | Prophet Ṣāliḥ | indefinite naṣb adjective 'righteous' | `proper_name` / case |
| `مَن` ↔ `مِن` (incl. `وَمِنَ`) | 'who' vs 'from' | harakah on the **content** م (after proclitic) | `is_man_who` |
| `لِمَا` ↔ `لَمَّا` | conflated | shadda on م | `shadda_on(t,"م")` |
| `كُلّ` ↔ `كَلَّا` | conflated | harakah on ك + shadda | `haraka_on`/`shadda_on` |
| `نِعْمَ` ↔ `نَعَمْ` | conflated | harakah on ن (kasra vs fatḥa) | `haraka_on(t,"ن")` |
| `أَنِّي` ↔ `أَنَّى` | conflated | final ـِي vs ـَى | `norm_strict` |
| `لَمْ` ↔ `لِمَ` | 'did not' vs 'why' | harakah on ل | `haraka_on(t,"ل")` |
| `ٱلْمُلْك` | 'the angels' | root م-ل-ك 'dominion'; angels = `الْمَلَائِكَة` | `multi_sense` |
| `أَنْهَٰر` | 'daytime' (نهار) | plural of نَهْر 'rivers' | `multi_sense` |
| `يَقْدِرُ` | 'is able' | with `يَبْسُط` partner = 'restricts' (rizq) | `contronym` |
| `حَلِيمٌ` (of Ibrāhīm) | a Divine Name | human attribute 'forbearing' | `referent_unresolved` |

### One reusable check (stdlib-only)

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import norm, norm_strict, is_man_who, shadda_on, haraka_on, KASRA, FATHA

def seat_collapsed(surface, candidate_surface):
    """True if surface and a candidate only match once the hamza seat is dropped — i.e. the
    lenient key collapses a distinction the strict key keeps. Then: reject, pending: seat_collapsed."""
    return norm(surface) == norm(candidate_surface) and norm_strict(surface) != norm_strict(candidate_surface)

if __name__ == "__main__":
    # إِلَيْنَا must NOT be certified as root ل-ي-ن
    assert seat_collapsed("إِلَيْنَا", "لِينَا"), "إِلَيْنَا vs ل-ي-ن must be seat_collapsed"
    # إيمان (faith) vs أيمان (oaths): strict keys differ
    assert norm_strict("إِيمَان") != norm_strict("أَيْمَان")
    # particle homographs resolved by the content-letter harakah
    assert is_man_who("مَنْ") and not is_man_who("وَمِنَ")
    assert shadda_on("لَمَّا", "م") and not shadda_on("لِمَا", "م")
    assert haraka_on("لَمْ", "ل") == FATHA and haraka_on("لِمَ", "ل") == KASRA
    print("quranic-nahw-notes self-check OK")
```

---

## 6. Decision order for the gloss layer (summary)

1. **Recall** with `norm` / `norm_strict` (strict to certify) → candidate set.
2. **Ṣarf** → candidate readings (root, pattern, POS).
3. **Nahw gates**, in order:
   a. **case/mood** (§1) — jarr ⇒ no verb gloss; mood confirms the particle.
   b. **governing particle** (`sentence-context.md` §2) — pins POS/case/mood of the complement.
   c. **homograph harakah** (`particles.md`) — content-letter vowel/seat/shadda via the helpers.
   d. **referent guard** (§4) — resolve who/what before the register.
4. One reading survives ⇒ emit `{src:'qamus', kind:'authored', lang:'en', gloss:…}`.
   Else ⇒ the **most specific** `pending:` reason (`homograph_haraka`, `pos_mismatch`,
   `multi_sense`, `contronym`, `referent_unresolved`, `proper_name`, `seat_collapsed`).
   **PENDING beats a wrong gloss, always.**
