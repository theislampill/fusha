# drills — particles (الْحُرُوف)

The ḥurūf are short, high-frequency, and the worst offenders for the hover-gloss: `norm()`
collapses most of them onto a homograph, and a verb/noun gloss can wrongly attach to one.
Each entry below gives: **functions**, the **disambiguator** (the harakah on the *content*
letter and/or the syntactic context), and a **recommended gloss** or `pending: <reason>`.

**Read the content letter, not the first letter.** A `و`/`ف` proclitic shifts the
decisive harakah one position right: `وَمِنَ` is *and + from*, not *and + whoever*. Use
`from tools.normalize_ar import haraka_on, shadda_on, is_man_who, norm_strict` — never
re-derive these. Helpers used below:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import haraka_on, shadda_on, is_man_who, norm_strict, KASRA, FATHA, DAMMA
# haraka_on(tok, "م") -> the short vowel on the FIRST م (after any proclitic); '' if none
# shadda_on(tok, "م") -> True if that letter carries shadda
# is_man_who(tok)     -> True for relative/interrogative مَن, False for مِن / وَمِنَ / مَنَّ
```

---

## وَ (wāw) — proclitic, multi-function

| function | context cue | gloss |
|---|---|---|
| conjunction *and* | joins two nouns/clauses of equal rank | `and` |
| oath *by…* (wāw al-qasam) | clause-initial + following noun in jarr, no preceding verb (`وَالْعَصْرِ`) | `by` (oath) |
| circumstantial *while* (wāw al-ḥāl) | introduces a ḥāl clause, often + pronoun (`وَهُوَ`) | `while` |

**Disambiguator:** the wāw is a *proclitic* — strip it before reading the next word's
harakah. Default gloss `and`; mark `pending: oath_vs_conj` only when clause-initial before a
jarr noun with no governing verb. Never let the wāw absorb the next word's reading.

## الْ (definite article) — proclitic `ال`

| function | context cue | gloss |
|---|---|---|
| definite article *the* | prefixes a noun; sun-letter assimilation is phonetic only | `the` |
| relative *that which* (mawṣūliyyah, rare/poetic) | on a participle acting as a clause | `pending: context` |

**Disambiguator:** `ال` is not a standalone token — it is part of the noun. Its only job in
the gloss layer is to mark definiteness; it must **not** produce its own hover gloss as a
word. Recommended: **no independent gloss** (fold into the noun); definiteness feeds the
iḍāfa logic (a noun with `ال` cannot be a muḍāf — see `idafa-and-jar-majrur.md`).

## مِنْ / مَنْ — the canonical homograph (same `norm()`)

| token | harakah on **م** | shadda on **ن** | reading | gloss |
|---|---|---|---|---|
| `مِنْ` / `مِنَ` / `وَمِنَ` | **kasra** | no | preposition | `from` |
| `مَنْ` / `مَنِ` | **fatḥa / none** | no | relative or interrogative *who* | `who` / `whoever` |
| `مَنَّ` | (fatḥa) | **yes** | verb *to bestow/favor* | verb gloss (root م-ن-ن) |

**Disambiguator:** `is_man_who(tok)` is the single source of truth — it returns True only
when the mīm has **no kasra** *and* the nūn has **no shadda**. The liaison form `مَنِ`
(kasra appears on the nūn for sandhi) is still *who*; `وَمِنَ` is still *from*. **Never read
the first letter** — for `وَمِنَ` the first letter is `و`.

```python
assert is_man_who("مَنْ") and is_man_who("مَنِ")
assert not is_man_who("مِنْ") and not is_man_who("وَمِنَ") and not is_man_who("مَنَّ")
```

Gloss: `مِنْ` → `from` · `مَنْ` (interrogative, clause-initial / after `أَ`) → `who` ·
`مَنْ` (relative, after a noun or `كُلّ`) → `whoever, the one who`. If undiacritized input
leaves the mīm bare, emit `pending: homograph_haraka`.

## بِـ (bāʾ) — proclitic preposition

| function | context cue | gloss |
|---|---|---|
| *with / by means of* (istiʿānah) | instrument (`بِالْقَلَمِ`) | `with, by` |
| *in / at* | location/time | `in` |
| *in (the name of)* | `بِسْمِ` | `in the name of` |
| oath *by* (bāʾ al-qasam) | + name of Allah | `by` |
| adheres a verb's object (taʿdiyah) | verb subcategorizes for bi- (`آمَنَ بِـ`) | fold into the verb's gloss |

**Disambiguator:** bi- is a clitic; the object is always **jarr**. When bi- carries the
verb's transitivity (`آمَنَ بِاللَّهِ` 'believed *in* Allah'), the gloss belongs to the
verb+bi unit, not to bi- alone. Default standalone gloss `with, in`. For `بِهِ`/`بِهَا`
see the clitic-pronoun table in `idafa-and-jar-majrur.md` (`بِهِ` = 'with it / in it').

## فَـ (fāʾ) — proclitic connector

| function | context cue | gloss |
|---|---|---|
| sequential *then / so* | narrative succession | `then, so` |
| causal *so / therefore* | result clause | `so` |
| apodosis fāʾ (fāʾ al-jawāb) | heads the answer of a conditional (`… فَـ…`) | `then` (apodosis) |

**Disambiguator:** like wāw, a *proclitic* — strip before reading the next word. Default
gloss `so, then`. The apodosis sense matters for sentence parsing (it marks where a
conditional's answer begins — see `sentence-context.md`) but the surface gloss stays `then`.

## لَا — negation / prohibition particle

| function | context cue | gloss |
|---|---|---|
| simple negation *not* (nafy) | + present verb | `not` |
| absolute negation *there is no* (lā al-nāfiyah lil-jins) | `لَا` + indefinite naṣb noun, no tanwīn (`لَا إِلَٰهَ`) | `there is no` |
| prohibition *do not* (lā al-nāhiyah) | + jussive (majzūm) verb | `do not` |
| coordinating *and not / nor* | after a positive then `وَلَا` | `nor` |

**Disambiguator:** the **mood of the following verb** decides nāfiyah (no jazm → `not`) vs.
nāhiyah (jazm → `do not`); a following indefinite naṣb noun with no tanwīn → `there is no`.
Recommended: gloss by the resolved branch; if the following word's iʿrāb is unknown, emit
`pending: context` rather than guessing `not` vs `do not`.

## مَا — the heaviest multi-function particle

| function | context cue | gloss |
|---|---|---|
| negation *not / did not* | + past or present verb, declarative | `did not` / `not` |
| interrogative *what?* | clause-initial question (`مَا هَٰذَا`) | `what` |
| relative *that which* (mawṣūlah) | + clause, fills a noun slot (`مَا عِنْدَكُمْ`) | `that which, what` |
| maṣdariyyah *the fact that / -ing* | nominalizes the following verb (`بِمَا كَسَبُوا`) | fold into clause |
| conditional *whatever* | + jazm verb | `whatever` |
| emphatic / redundant (zāʾidah) | after some particles | no independent gloss |

**Disambiguator:** `مَا` has **no diacritic homograph**, so the harakah does not help — the
*syntactic frame* does. Heuristics: question-initial → `what`; before a verb in a
declarative → `not`; filling a noun slot before a clause → `that which`. When the frame is
genuinely ambiguous (very common), emit **`pending: multi_sense`** — `مَا` is the canonical
case where a precise PENDING beats a coin-flip gloss.

## إِلَى — preposition (terminal/goal)

| function | context cue | gloss |
|---|---|---|
| *to / toward / up to* | goal of motion or limit | `to, toward` |
| *until* (limit) | with a time/quantity terminus | `until` |

**Disambiguator:** root is **ʾ-l-y** (hamza + lām + yāʾ). Critically, `إِلَى` and its clitic
form `إِلَيْنَا` ('to us'), `إِلَيْهِ` ('to him') are **not** root ل-ي-ن ('soft/lenient') — the
hamza seat is load-bearing and `norm()` *drops* it, producing the false ل-ي-ن match.
`norm_strict()` keeps the seat. **Guard:** never gloss any `إِلَى…` form from root ل-ي-ن.

```python
assert norm_strict("إِلَيْنَا") != norm_strict("لِينَ")   # seat kept → distinct
# if a candidate from root ل-ي-ن matches only under norm() (seat dropped) -> reject, pending: seat_collapsed
```

Gloss: `إِلَى` → `to, toward`; `إِلَيْنَا` → `to us`; `إِلَيْهِ` → `to him` (clitic table in
`idafa-and-jar-majrur.md`).

## إِلَّا — exception particle (do not confuse with لَا)

| function | context cue | gloss |
|---|---|---|
| *except / but* (istithnāʾ) | after a negation or general noun (`لَا إِلَٰهَ إِلَّا اللَّهُ`) | `except, but` |
| *if not / unless* (= إِنْ + لَا) | conditional reduction | `pending: context` (rare) |

**Disambiguator:** `إِلَّا` carries a **shadda on the lām** and a hamza seat; `لَا` has
neither. `norm()` could blur them, so use the seat + shadda. Default gloss `except`.

## أَنْ / إِنَّ (and أَنَّ) — seat- and shadda-distinguished

| token | seat | shadda on **ن** | function | gloss |
|---|---|---|---|---|
| `أَنْ` | hamza-on-ʾalif, **fatḥa** | no | maṣdariyyah *to / that* (+ subjunctive verb) | `to, that` |
| `أَنَّ` | hamza-on-ʾalif, **fatḥa** | **yes** | *that* (+ noun clause, naṣb subject) | `that` |
| `إِنَّ` | hamza-on-ʾalif, **kasra** | **yes** | emphatic *indeed / verily* | `indeed` |
| `إِنْ` | hamza, **kasra** | no | conditional *if* / negating *not* | `if` (or `pending`) |

**Disambiguator:** two axes — the **hamza seat's harakah** (fatḥa → ʾan/ʾanna 'to/that';
kasra → ʾinna/ʾin) and the **shadda on the nūn** (present → ʾanna/ʾinna heavy; absent →
ʾan/ʾin light). `norm_strict()` keeps the seat; `shadda_on(tok, "ن")` checks the shadda.

```python
assert norm_strict("أَنْ") != norm_strict("إِنَّ")   # fatḥa-seat vs kasra-seat kept distinct
assert shadda_on("إِنَّ", "ن") and not shadda_on("أَنْ", "ن")
```

Glosses: `أَنْ` → `to, that` (verb follows, naṣb) · `أَنَّ` → `that` (clause follows) ·
`إِنَّ` → `indeed, verily` · `إِنْ` → `if` (conditional) or, before a verb in some frames,
negation — emit `pending: multi_sense` for bare `إِنْ` when the frame is unclear.
The famous pair `أَنِّي` 'that I' vs `أَنَّى` 'how / whence' is a separate homograph: same
`norm()`, separated by the final ـِي (yāʾ+kasra) vs ـَى (ʾalif maqṣūra) — see
`sentence-context.md`.

## عَلَى — preposition (super-position / obligation)

| function | context cue | gloss |
|---|---|---|
| *on / upon* | physical/abstract super-position | `on, upon` |
| *against* | adversative (`عَلَيْهِمْ`) | `against` |
| *incumbent on / owed by* (obligation) | duty frame (`عَلَى النَّاسِ حِجُّ`) | `upon (as a duty)` |

**Disambiguator:** root **ʿ-l-w/y**; written with ʾalif maqṣūra `ى`. Object is always jarr.
Default gloss `on, upon`; the 'against' / 'duty' senses are context-driven — choose by the
clause, else default `upon`. Clitic forms (`عَلَيْهِ` 'on him / against him') in the clitic
table.

## فِي — preposition (containment)

| function | context cue | gloss |
|---|---|---|
| *in / within* | location/time containment | `in, within` |
| *concerning / about* | topic frame (`فِي شَأْنِكُمْ`) | `concerning` |
| *during* | temporal span | `during` |

**Disambiguator:** unambiguous spelling (fāʾ + yāʾ). Object is jarr. Default gloss `in`;
'concerning'/'during' by clause context, else `in`.

## لَمْ / لِمَ — negation vs. interrogative (same `norm()`)

| token | harakah on **ل** | following word | reading | gloss |
|---|---|---|---|---|
| `لَمْ` | **fatḥa**, mīm has **sukūn** | jussive (majzūm) verb | negates past | `did not` |
| `لِمَ` | **kasra**, mīm has **fatḥa** | (= لِـ + مَا shortened) | *why?* | `why` |

**Disambiguator:** `norm()` collapses both to `لم`. The split is the **lām's harakah**:
fatḥa + a jazm verb after → `لَمْ` 'did not'; kasra + question frame → `لِمَ` 'why'.

```python
assert haraka_on("لَمْ", "ل") == FATHA   # negation
assert haraka_on("لِمَ", "ل") == KASRA   # 'why'
```

Gloss: `لَمْ` → `did not` (and it forces the next verb to past-jussive — a parse signal for
`sentence-context.md`) · `لِمَ` → `why`. If the lām is bare (undiacritized), emit
`pending: homograph_haraka`.

---

## Cross-reference: other diacritic-homograph particles (full treatment elsewhere)

These follow the same "harakah on the content letter" rule; covered with worked examples in
`sentence-context.md` and `references/quranic-nahw-notes.md`:

| pair | distinguisher | helper |
|---|---|---|
| `لِمَا` (for what) vs `لَمَّا` (when / not yet) | shadda on the **م** | `shadda_on(t, "م")` |
| `كُلّ` (each/all) vs `كَلَّا` (nay!) | harakah on the **ك** (ḍamma vs fatḥa) + shadda | `haraka_on(t,"ك")`, `shadda_on(t,"ل")` |
| `نِعْمَ` (how excellent) vs `نَعَمْ` (yes) | harakah on the **ن** (kasra vs fatḥa) | `haraka_on(t, "ن")` |
| `أَنِّي` (that I) vs `أَنَّى` (how/whence) | final ـِي vs ـَى | `norm_strict` keeps them distinct |

## Drill rule

For every particle: (1) strip proclitics, (2) read the **content** letter's harakah / seat /
shadda with the `tools.normalize_ar` helpers, (3) check the syntactic frame, (4) emit the
resolved gloss **or** the most specific `pending:` reason. A wrong particle gloss poisons the
whole āyah's parse — **PENDING beats a guess.**
