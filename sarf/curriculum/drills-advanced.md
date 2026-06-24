# Drills — advanced ṣarf

The top rung ([`zero-to-fluency-sarf.md`](zero-to-fluency-sarf.md), stage 7): the cases where
two readings collapse and the harakāt / hamza seat / pattern are the only thing standing between
a correct gloss and a shipped defect. Three skills: **(A) passive vs active reconstruction**,
**(B) doubled / hamzated edge cases**, and **(C) homograph disambiguation by pattern.**

Each drill names **which gate or rule applies** — the machine-checked tier a real decision must
carry ([`../SKILL.md`](../SKILL.md) §13b). At this level the answer is often **pending**; that
is not failure, it is the correct output when the distinguisher is unread. **PENDING beats
wrong.**

> Live key reality (carry it everywhere below): the production hover key is **`norm_strict`** —
> it keeps the `ال` article + the consonant skeleton + the hamza seat but **drops harakāt
> (including shadda)**. A surface-keyed gloss fires on *every* token sharing that key, so it is
> safe **iff** every same-key surface is the same word and same POS. Decide with an **empirical
> key-collision probe**, not bare-root reasoning. →
> [`../procedures/homograph-risk.md`](../procedures/homograph-risk.md).

---

## Part A — passive vs active reconstruction

The passive is a **vowel signature** (ḍamma–kasra in the perfect; ḍamma on the prefix +
fatḥa on the penult in the imperfect). Under `norm_strict` the harakāt are gone, so an
active/passive pair **shares one key** — the danger zone.

**Gate/rule:** [`../rules/verb-measure-gates.json`](../rules/verb-measure-gates.json) (voice is
sense-bearing → at least `two_vote_required`); voice rows in
[`../rules/verb-measures.json`](../rules/verb-measures.json).

| # | pair (active ↔ passive) | reconstruct | gate / decision |
|---|---|---|---|
| A1 | `خَلَقَ` ↔ `خُلِقَ` | active "created" ↔ passive "was created" | both share `norm_strict` key `خلق` → **two_vote / pending** unless harakāt or context fix voice |
| A2 | `يَعْلَمُ` ↔ `يُعْلَمُ` | "he knows" ↔ "it is known" | imperfect ḍamma-prefix = passive; key collides → **two_vote_required** |
| A3 | `قَتَلَ` ↔ `قُتِلَ` | "killed" ↔ "was killed" | one key, opposite agency → **pending** if vowels unread (the قَتَلَ↔قُتِلَ key lesson) |
| A4 | `كُذِبُوا۟` ↔ `كَذَّبُوا` | "they were disbelieved" ↔ "they denied" | also crosses Form I↔II (shadda); two axes collapse → **pending** (SKILL §13c) |

**Rule:** never let a single surface key carry both voices. If the ḍamma–kasra is unread and
context does not force agency → **pending**, never a guess.
[`../drills/verb-measures.md`](../drills/verb-measures.md) part B drills the bare signature.

---

## Part B — doubled / hamzated edge cases

These break naive radical-counting and `norm()` matching in specific ways
([`../references/weak-verbs.md`](../references/weak-verbs.md)).

**Gate/rule:** [`../rules/weak-root-gates.json`](../rules/weak-root-gates.json),
[`../rules/morphology-risk-rules.json`](../rules/morphology-risk-rules.json),
[`../rules/homograph-quarantines.json`](../rules/homograph-quarantines.json).

| # | surface | trap | resolution | gate / decision |
|---|---|---|---|---|
| B1 | `رَدَّ` | shadda hides C3; looks bi-consonantal | expand → `ر د د` (doubled); "returned/repelled" | `geminate_shadda`; safe once expanded |
| B2 | `خَفَّت` (src `qamus:v379#root=خ ف ف`) | shadda + fem. `ـت` | `خ ف ف`; "(she/it) became light" | `geminate_shadda`; certify via entry |
| B3 | `أَحَبَّ` | Form IV **of** a doubled root `ح ب ب` | hamza augment + merged C2=C3; "loved" | two augments stacked → **two_vote** |
| B4 | `إِيمَان` vs `أَيْمَان` | `norm()` merges them | seat: `إِيمَان` root `أ م ن` "faith" ≠ `أَيْمَان` root `ي م ن` "oaths" | `hamza_sensitive_homograph`; **never certify from `norm()`** (root-detection ex. 4) |
| B5 | `يَأْمُرُونَ` vs `يَمُرُّونَ` | hamza vs shadda, different roots | `أ م ر` "command" ≠ `م ر ر` "pass" | `hamza_sensitive` + `geminate`; distinct entries, no key share allowed |
| B6 | `قُرْءَانًا` | trailing `ـًا` looks like enclitic `+نا` | `ends_tanwin_alef` = accusative tanwīn, **not** "us" | clitic-strip guard; do **not** split a pronoun |
| B7 | `أَقَامَ` | Form IV of hollow `ق و م`, medial dropped | recover from family; "established", not a sound-root reading | `hollow_root_c2_hidden` + Form IV |

**Rule:** expand a shadda before counting; preserve the hamza seat (certify on `norm_strict` +
QAC); treat tanwīn-alef as case, never as `+نا`. A hamza-sensitive pair must **never** be
allowed to share one surface key.

---

## Part C — homograph disambiguation by pattern

Two words, one consonant skeleton; the **pattern + harakah** is the only distinguisher. The
decision is made on the **content letter**, not on `norm()`.

**Gate/rule:** [`../rules/homograph-quarantines.json`](../rules/homograph-quarantines.json),
[`../rules/pos-mismatch-rules.json`](../rules/pos-mismatch-rules.json),
[`../../nahw/rules/two-vote-required-rules.json`](../../nahw/rules/two-vote-required-rules.json);
full list in [`../drills/homograph-regressions.md`](../drills/homograph-regressions.md).

| # | homograph set | the distinguisher | decision · gate |
|---|---|---|---|
| C1 | `ذِكْر` (maṣdar "remembrance") ↔ `ذَكَر` ("male") ↔ `ذَكَرَ` ("he mentioned") | harakāt on `ذ-ك-ر` (one skeleton, three words/POS) | **pending** if harakāt unread → `multi_sense_root` + POS split (the P5 pull-back) |
| C2 | `ٱلْمُلْك` ("dominion") ↔ `ٱلْمَلِك` ("the king") | the vowel under `ل` (sukūn/ḍamma vs kasra) | true homograph, key collides → **pending** (SKILL §13c) |
| C3 | `مُلْك` / `مَلِك` / `مَلَك` / `مَالِك` (root `م ل ك`) | harakāt + length (`مَالِك` long ā) | sense from harakāt + context; `ٱلْمُلْك` is **never** "angels" (root-detection ex. 5) |
| C4 | `أَنْهَار` ("rivers") ↔ `نَهَار` ("daytime") | pattern + context (`أَفْعَال` broken plural of `نَهْر` vs the daytime noun) | **pending** if context doesn't disambiguate (root-detection ex. 6) |
| C5 | `هُدَى` (noun "guidance") ↔ `هَدَىٰ` (verb "He guided") | harakah + the final `ى` resolution | noun↔verb collision → **two_vote / pending** (SKILL §13c) |
| C6 | `وَعَدَ` (verb "promised") ↔ `وَعْد` (noun "a promise") | the wazn (`فَعَلَ` vs `فَعْل`) | POS split on one skeleton → **two_vote** (`pos-mismatch-rules.json`) |
| C7 | `صَٰلِحًا` ("righteous", adj.) ↔ Prophet **Ṣāliḥ** (proper name) | context + referent guard, not morphology | **pending / referent-guard**; a proper name is not its participle gloss (SKILL §13c) |
| C8 | `يَقْدِرُ` "restricts" (rizq context) ↔ "is able" | context fixes the sense on one form | **two_vote**; nahw `referent-context` decides → never a fixed surface gloss |

**Rule:** a surface-key gloss is `auto_safe` **only if** its `norm_strict` key is
collision-free; the moment the key mixes lemmas / POS / form / voice / sense, the answer is
`two_vote_required` or **pending**. A proper name that reads as a common noun (`ٱلْعَزِيز` ↔
ʿAzīz of Egypt) is the referent landmine — pending until context certifies.

---

## The decision the gates enforce (tier ladder)

Every real decision carries a `gate` no weaker than its triggers
([`../SKILL.md`](../SKILL.md) §13b;
[`tools/validate_linguistic_decisions.py`](../../tools/validate_linguistic_decisions.py) rejects
an under-gated decision):

```
auto_safe              QAC agrees · one sense · norm_strict key collision-free · no grammar dep
   ↓
two_vote_required      iʿrāb / derived-sense / multi-sense / voice / referent
   ↓
human_source_review    seeding a new root · source evidence needed
   ↓
never_auto_resolve     norm-only · OCR-only · copied gloss · QAC conflict
```

Most of Parts A–C land at **two_vote_required** or **pending** — that is the design. The
advanced skill is not "resolve more"; it is **knowing exactly when not to**.

---

## Checklist before you call an advanced drill "done"

- [ ] Did I decide on the **content-letter harakah / hamza seat / shadda** — never on `norm()`?
- [ ] Did I run (or reason out) the **empirical `norm_strict` key-collision probe** before
      shipping any surface-keyed gloss?
- [ ] For an active/passive pair, did I refuse to let one key carry **both voices**?
- [ ] For a hamza-sensitive or doubled pair, did I keep them on **distinct keys/entries**?
- [ ] For a homograph/proper-name/context case, did I apply the **right gate** (two_vote /
      human_review) or go **pending** with a precise reason?
- [ ] Is the proper name kept off its underlying-verb/participle gloss?
- [ ] Public emit is `{src:'qamus', kind:'authored'}` or nothing — `informed_by`/QAC names stay
      internal.

The graduation bar: across a mixed set, every `resolved` is right and **nothing wrong is
shipped.** A blank hover is recoverable; a flipped meaning in scripture-facing copy is not.
**PENDING beats wrong.**
