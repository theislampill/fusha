# drills — sentence context (nominal vs. verbal, governance, mood, contronyms)

Particle and clitic rules (the other two drills) decide *tokens*. This file decides the
cases where the **clause** is the only disambiguator: sentence type, the governing particle,
negation and verbal mood, and the contronyms / multi-sense roots that flip with context.
These are the `multi_sense` / `contronym` / `referent_unresolved` PENDING cases.

---

## 1. Nominal vs. verbal sentence (الْجُمْلَة الِاسْمِيَّة / الْفِعْلِيَّة)

| type | opens with | structure | parse effect |
|---|---|---|---|
| **nominal** (ism) | a noun/pronoun | mubtadaʾ (rafʿ) + khabar (rafʿ) | the first noun is the *topic*, not a verb's object |
| **verbal** (fiʿl) | a verb | fiʿl + fāʿil (rafʿ) + (mafʿūl, naṣb) | the first noun after the verb is the *doer* |

**Why it matters for the gloss:** the same surface noun glosses with a different English
role depending on sentence type, and a verb-vs-noun homograph is settled by position. If a
clause opens with `إِنَّ`/`أَنَّ` (nominal-emphatic), the next noun is its *subject* in naṣb
even though it heads a nominal clause — don't read it as a verb's object.

Heuristic for the gloss layer: identify the **first governing element** (verb, `إِنَّ`-family,
preposition, conditional) and let it assign roles before glossing any noun.

---

## 2. The governing particle decides the complement

| governor | forces on its complement | example | gloss effect |
|---|---|---|---|
| `إِنَّ` / `أَنَّ` | following noun → **naṣb** subject | `إِنَّ اللَّهَ` | 'indeed Allah' (subject, not object) |
| `أَنْ` (maṣdariyyah) | following verb → **subjunctive (naṣb)** | `أَنْ تَصُومُوا` | 'that you fast / to fast' |
| `لَمْ` | following verb → **jussive (jazm)**, past meaning | `لَمْ يَلِدْ` | 'did not beget' |
| `لَا` (nāhiyah) | following verb → **jussive** | `لَا تَحْزَنْ` | 'do not grieve' |
| `لَنْ` | following verb → **subjunctive**, future negation | `لَنْ نُؤْمِنَ` | 'we will never believe' |
| preposition | following noun → **jarr** | `فِي الْأَرْضِ` | 'in the earth' (noun, never verb) |

**Rule for the disambiguator:** read the governor first; it pins the POS and mood of what
follows. A candidate gloss whose POS/mood contradicts the governor is rejected
(`pending: pos_mismatch`).

---

## 3. Negation & mood

- `مَا` + past = 'did not' (declarative negation); `مَا` + present can be negation **or**
  relative — frame-decided (see `particles.md`; default `pending: multi_sense` when unclear).
- `لَمْ` + jussive = negated **past**; `لَنْ` + subjunctive = emphatic **future** negation;
  `لَا` + present = simple negation; `لَا` + jussive = **prohibition** ('do not').
- The verb's **mood ending** (rafʿ ـُ / naṣb ـَ / jazm sukūn-or-dropped-nūn) is itself a
  disambiguator: a jazm ending after `لَمْ` confirms the past negation reading; a naṣb ending
  after `أَنْ` confirms the maṣdariyyah 'to'.

These mood facts feed `references/quranic-nahw-notes.md` (case/mood section).

---

## 4. The homograph particle pairs that need the *clause*, not just a harakah

Some pairs are separated by a harakah (use the helpers), but the **choice of reading still
needs the clause**:

| pair | helper split | clause cue | glosses |
|---|---|---|---|
| `لِمَا` vs `لَمَّا` | `shadda_on(t,"م")` | `لَمَّا` heads a temporal/`not-yet` clause; `لِمَا` is لِـ+مَا | `لِمَا` 'for what / because' · `لَمَّا` 'when' or 'not yet' |
| `أَنِّي` vs `أَنَّى` | final ـِي vs ـَى (`norm_strict`) | `أَنَّى` is interrogative-initial | `أَنِّي` 'that I' · `أَنَّى` 'how / whence' |
| `كُلّ` vs `كَلَّا` | `haraka_on(t,"ك")` + `shadda_on(t,"ل")` | `كَلَّا` is a standalone rebuke | `كُلّ` 'each / all' · `كَلَّا` 'nay! / by no means' |
| `نِعْمَ` vs `نَعَمْ` | `haraka_on(t,"ن")` | `نِعْمَ` + a following noun of praise | `نِعْمَ` 'how excellent is' · `نَعَمْ` 'yes' |

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import shadda_on, haraka_on, KASRA, FATHA, DAMMA

assert shadda_on("لَمَّا", "م") and not shadda_on("لِمَا", "م")     # 'when' vs 'for what'
assert haraka_on("كُلًّا", "ك") == DAMMA and haraka_on("كَلَّا", "ك") == FATHA  # 'all' vs 'nay'
assert haraka_on("نِعْمَ", "ن") == KASRA and haraka_on("نَعَمْ", "ن") == FATHA  # 'excellent' vs 'yes'
```

---

## 5. Contronyms & multi-sense roots — resolved by context

A root with two (sometimes opposite) senses must read the clause. The gloss layer should
carry **all senses** as candidates and let context pick; if context does not decide, emit
`pending: multi_sense` (or `pending: contronym` for polarity flips). Never default to the
common sense when the clause points the other way.

### قدر — 'be able / decree' vs. **'restrict'** (contronym, context-pinned)

`يَقْدِرُ` defaults to 'is able / has power'. **But** when paired with its antonym `يَبْسُط`
('expands / gives abundantly'), the contrast frame flips it to **'restricts / straitens'**
(the rizq frame: *Allah expands provision for whom He wills and **restricts**…*).

| frame | gloss |
|---|---|
| `يَقْدِرُ` alone, power context | 'is able / has power' |
| `يَبْسُطُ … وَيَقْدِرُ` (provision contrast) | **'restricts / straitens'** |
| undecided | `pending: contronym` |

Rule: detect the `بسط`/`قدر` pairing in the same āyah → 'restricts'; else default 'is able';
if neither cue is present, `pending`.

### Polysemes pinned by their muḍāf / referent

| token | wrong default | correct (context) | cue |
|---|---|---|---|
| `الْمُلْك` | 'the angels' | **'the dominion / sovereignty'** | root م-ل-ك; 'angels' is `الْمَلَائِكَة`, a different form |
| `أَنْهَار` | 'daytime' (نهار) | **'rivers'** | root ن-ه-ر; plural-of-نَهْر, not نَهَار |
| `الصَّلَاة` | 'the link/connection' | **'the prayer'** | fixed religious sense in worship frames |

These are `multi_sense`: keep both candidates, pick by the surrounding nouns; if unsure,
`pending`.

---

## 6. Proper names are not their homographic verb/noun (`proper_name` guard)

A name that shares letters with a verb/noun root must **not** be glossed as that verb/noun.

| token | NOT | is | guard |
|---|---|---|---|
| `مُحَمَّد` | 'to praise' (ح-م-د verb) | the name **Muḥammad** | capital-name frame; subject/vocative position |
| `صَٰلِحًا` (as adjective) | the Prophet **Ṣāliḥ** | 'righteous (deed)' | lowercase attribute, `naṣb` after a verb (`عَمِلَ صَٰلِحًا`) |
| `صَالِح` (as name) | 'righteous' (adjective) | the Prophet **Ṣāliḥ** | name frame (sent to Thamūd) |
| `ٱبْن` / `بَنَات` | 'to build' (ب-ن-ي verb) | 'son' / 'daughters' (nouns) | nominal; `pending: pos_mismatch` for a verb gloss |
| `رَسُولًا` | 'to send' (ر-س-ل verb) | 'a messenger' (noun, naṣb) | nominal object; verb gloss rejected |

Rule: when a token is in name/attribute position (vocative, subject of a prophet narrative,
or an adjective in naṣb after a verb of doing), prefer the **name/noun/adjective** reading
and reject the verb gloss. `صَٰلِحًا` as an indefinite naṣb adjective ('a righteous deed') is
**not** the Prophet's name; the Prophet `صَالِح` is a definite name in a Thamūd narrative —
the case ending and frame decide. If the frame is ambiguous, `pending: proper_name`.

---

## 7. Attribute vs. Divine Name — the referent guard

The same adjective glosses differently by **who it describes**. A perfection-attribute of a
human is a human virtue; of Allah it is a Name — and the *gloss wording* should not import
Name-of-Allah connotations onto a human referent (or vice versa).

| token | referent = human | referent = Allah |
|---|---|---|
| `حَلِيمٌ` | **'forbearing'** (e.g. of Ibrāhīm: *Ibrāhīm was forbearing*) — a human virtue, **not** a Divine Name | 'the Forbearing' (a Name) |
| `رَحِيمٌ` | 'merciful / kind' (e.g. of the Prophet toward believers) | 'the Merciful' (a Name) |
| `عَزِيز` | 'mighty / dear' / a title ('the ʿAzīz' of Egypt) | 'the Almighty' (a Name) |

**Rule:** resolve the referent **before** choosing the gloss register. `حَلِيمٌ` describing
Ibrāhīm → 'forbearing' (plain adjective), **never** typeset as a Divine Name. If the referent
is not yet resolved, `pending: referent_unresolved` — do not default to the Name.

---

## Drill checklist

1. Find the **first governor** (verb / `إِنَّ`-family / preposition / conditional); let it
   assign POS, case, and mood before glossing nouns.
2. Use mood (rafʿ/naṣb/jazm) and negation (`مَا`/`لَمْ`/`لَنْ`/`لَا`) to fix the verb's reading.
3. For contronyms/polysemes (`قدر`, `الْمُلْك`, `أَنْهَار`), carry all senses; pick by the
   clause's partner words; else `pending: multi_sense` / `contronym`.
4. Names ≠ their homographic verb (`مُحَمَّد`, `صَالِح`, `ٱبْن`, `رَسُولًا`) → name/noun reading
   or `pending: proper_name`; never a verb gloss on a name/noun.
5. Resolve the **referent** before the register: human `حَلِيمٌ` = 'forbearing', not a Name.
6. Undecided ⇒ the most specific `pending:` reason. **PENDING beats a wrong gloss.**
