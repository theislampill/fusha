# nahw — syntax (iʿrāb + context) support

**Ṣarf tells you what a word *could* be. Nahw tells you what it *is here*.**

Ṣarf (morphology) is mostly token-local: a pattern, a root, a stem. It can list the
*candidate* readings of a surface form. But many Arabic surface forms — and almost all
of the high-frequency ones — are genuinely ambiguous in isolation. The ambiguity is only
resolved by **syntax**: the governing particle, the case ending, the verbal mood, the
sentence type (nominal vs. verbal), the referent of a pronoun, the contronym's polarity.

This directory is the **nahw-support layer**. It is *not* a grammar textbook; it is a set
of decision rules that let an automated hover-gloss / lemmatizer say, for each token,
**"this gloss" or "pending: context"** — and never a confidently *wrong* gloss.

> The main skill entry point is `nahw/SKILL.md` (authored separately). These files are its
> evidence and drill material. Everything here is **original authored content**; external
> corpora (Quran.com, QAC, Tanzil, sunnah.com) are internal evidence only — named as
> `informed_by` labels, never copied as gloss text. The public hover artifact emits only
> `{src:'qamus', kind:'authored', lang:'en'}`.

---

## What nahw adds beyond ṣarf

| Layer | Question it answers | Failure if used alone |
|---|---|---|
| **norm / match** (`tools/normalize_ar.py`) | "which entries could this surface touch?" | over-recall: `إِلَيْنَا` matches root ل-ي-ن; `يَأْمُرُونَ` matches `يَمُرُّونَ` |
| **ṣarf** | "what pattern / root / stem is this?" | gives a *set*; verb-gloss can land on a noun (`رَسُولًا` ≠ 'to send') |
| **nahw** (here) | "which of those readings holds *in this āyah*?" | — (this is the disambiguator) |

Ṣarf narrows; **nahw decides**. The two together gate the gloss; if nahw cannot decide,
the token stays **PENDING**.

### The recurring shapes nahw resolves

1. **Diacritic homographs** — short function words that `norm()` collapses but a harakah on
   the *content* letter separates: `مَن` ('who') vs `مِن`/`وَمِنَ` ('from'); `لِمَا` vs `لَمَّا`;
   `كُلّ` vs `كَلَّا`; `نِعْمَ` vs `نَعَمْ`; `أَنِّي` vs `أَنَّى`; `لَمْ` ('not') vs `لِمَ` ('why').
   → see `drills/particles.md`. Read the **content** letter's harakah, not the first letter
   (a `و`/`ف` proclitic shifts it right). Use `haraka_on`, `shadda_on`, `is_man_who`.
2. **Construct + clitic reshaping** — iḍāfa and *preposition + pronoun* change the *wording*
   of the gloss, not just the head noun: `بِهِ` 'with it / in it', `لَهُ` 'for him / to him',
   `عِنْدَ` 'with / near / in the sight of', `إِلَيْنَا` 'to us' (root ʾ-l-y, **not** ل-ي-ن 'soft').
   → see `drills/idafa-and-jar-majrur.md`.
3. **Sentence-level sense selection** — contronyms and multi-sense roots fixed by what
   governs them: `يَقْدِرُ` paired with `يَبْسُط` = 'restricts' (not 'is able'); `حَلِيمٌ` with
   referent Ibrāhīm = 'forbearing' (a human attribute, **not** a divine Name).
   → see `drills/sentence-context.md`.

---

## How it feeds hover-gloss disambiguation

The hover pipeline is a gate. Nahw sits at the **decision** stage:

```
surface token
  └─ norm / norm_strict  → candidate entry set         (recall; tools/normalize_ar.py)
       └─ ṣarf           → candidate readings (root, pattern, POS)
            └─ NAHW      → pick ONE reading or PENDING   (this directory)
                 └─ emit {src:'qamus', kind:'authored', lang:'en', gloss:…}  OR  pending
```

Nahw contributes three guard rails, each documented in `references/quranic-nahw-notes.md`:

- **case/mood guard (iʿrāb)** — naṣb/jarr/rafʿ and verbal mood constrain POS and sense.
  A jarr ending after a preposition means the token is a noun in a jār-majrūr, so a
  *verb* gloss is impossible; `لَمْ` + jazm means the following verb is a negated past.
- **governing-particle guard** — `إِنَّ`/`أَنَّ`/`أَنْ`, `لَا`, `مَا`, conditionals: each forces a
  reading of its complement and disambiguates the particle itself (`أَنْ` maṣdariyyah vs.
  `إِنَّ` emphatic — distinguished by the hamza seat, which `norm_strict()` keeps).
- **referent guard** — a pronoun or attribute glosses differently by who/what it points to.
  This is what stops `حَلِيمٌ` of a human from being read as a divine Name, and what makes
  `إِلَيْنَا` resolve to 'to us', not to the root ل-ي-ن.

## How it feeds **pending-reason refinement**

A PENDING is only useful if its *reason* is precise enough to (a) route to a human and
(b) be auto-cleared later. Nahw turns a vague "ambiguous" into a structured reason code.
The reason vocabulary used across the drills and `references/`:

| reason code | meaning | example trigger |
|---|---|---|
| `homograph_haraka` | two words share `norm()`; need the content-letter harakah | `مَن` vs `مِن` when input is undiacritized |
| `pos_mismatch` | candidate gloss POS conflicts with iʿrāb here | verb gloss on a jarr noun (`رَسُولًا`) |
| `multi_sense` | one root, several senses; context not yet decisive | `قدر`: 'be able' vs 'restrict' |
| `contronym` | sense flips polarity by context | `قدر` with `يَبْسُط` partner |
| `referent_unresolved` | gloss depends on an unidentified referent | bare pronoun, ambiguous attribute |
| `proper_name` | token is a name, not the homographic verb/noun | `مُحَمَّد` ≠ 'to praise'; `صَٰلِحًا` ≠ Prophet Ṣāliḥ |
| `seat_collapsed` | `norm()` dropped a hamza/ʾalif distinction | `إيمان` ≠ `أيمان`; `إِلَيْنَا` ≠ ل-ي-ن |

Refinement rule: **always prefer the most specific PENDING reason over a guessed gloss.**
A wrong gloss is a regression; a precise PENDING is progress. (This is the hard-won lesson
of the qamus-highlight work — see the regression list in `references/quranic-nahw-notes.md`.)

---

## Files

- `drills/particles.md` — the ḥurūf: each particle's functions, the
  diacritic/context that disambiguates it, and a recommended concise gloss or `pending`.
- `drills/idafa-and-jar-majrur.md` — how iḍāfa and *preposition + pronoun* reshape the
  gloss wording; the `إِلَيْنَا` ≠ 'soft' guard.
- `drills/sentence-context.md` — nominal vs. verbal sentences, the governing particle,
  negation/mood, and contronyms / multi-sense roots resolved by context.
- `drills/grammar-routing-hard-cases.md` — the June 25 hard-tail routing cases: `ما`, `و`,
  `ف`, governing particles, PP attachment, conditionals, hāl, vocatives, and exceptions.
- `references/quranic-nahw-notes.md` — concise iʿrāb (jarr / naṣb / rafʿ), conditionals,
  relative pronouns, and the referent guard, with the regression checklist.
- `references/particles.md` — the closed particle/preposition/pronoun inventory (corpus-attested)
  + the content-letter-harakah rule.
- `references/jar-majrur.md` — preposition + pronoun rendering by referent; the `إِلَيْنَا` ≠ ل-ي-ن guard.
- `references/idafa.md` — genitive constructs; gloss the relationship + definiteness.
- `references/irab-case-mood.md` — case/mood endings; **لَمْ + jussive → past meaning**.
- `rules/*.json` — particle-context, preposition-pronoun, negation, context-sense, referent-guard
  decision tables (machine-readable; consumed with `tools/normalize_ar`).

## Governor / dependency lattice (the P2 grammar-checker engine)

Beyond the guard rails above, `nahw/SKILL.md` now drives a conservative **governor / iʿrāb dependency lattice** — the executable form
of the case/mood **value vs governor justification** discipline: a correct ending with an absent/wrong governor is
`governor_not_justified` (right answer, wrong reason) → scholar/two-vote, **never `auto_safe`**; PP-attachment stays unresolved unless
justified; iḍāfa keeps its alternatives; a coordinating wāw is headless. Procedures
[`procedures/governor-dependency-lattice.md`](procedures/governor-dependency-lattice.md),
[`procedures/irab-right-answer-wrong-reason.md`](procedures/irab-right-answer-wrong-reason.md),
[`procedures/suggestion-gating-for-irab.md`](procedures/suggestion-gating-for-irab.md); fields
[`references/dependency-candidate-fields.md`](references/dependency-candidate-fields.md); evals
[`evals/governor-dependency-lattice.jsonl`](evals/governor-dependency-lattice.jsonl) +
[`evals/irab-right-answer-wrong-reason.jsonl`](evals/irab-right-answer-wrong-reason.jsonl); engine
[`../tools/fusha_governor.py`](../tools/fusha_governor.py). Drilled in [`drills/irab-case-mood.md`](drills/irab-case-mood.md) §6.

## Largelexicon function-token routing

Largelexicon rollout work must not promote grammar-sensitive rows merely because a surface
or English gloss looks familiar. Use
[`procedures/largelexicon-function-token-routing.md`](procedures/largelexicon-function-token-routing.md)
to decide whether a qword is a source-clean hover candidate, a source-crosswalk packet, an
owner packet, or a scholar/iʿrāb packet. This is where `ما`, `وما`, preposition + majrūr
hosts, particle clusters, and right-answer/wrong-reason cases get routed before public
projection.

### Plan 15 / all-qword source gates

For Qamus rollout, nahw starts after the graph spine is stable: qword denominator row,
source-card repair status, source-crosswalk status, and rendered/readback trace decide whether
function analysis can become a hover. If the row is only `source_crosswalk_packet_ready`, it is
a packet, not a function-token certification.

Use `procedures/plan15-nahw-route-families.md` for `governor_irab_fixture_needed` and
`particle_function_rule_needed`. These route `أَمْ`, `لَهُمْ`, `وَمَا`, preposition+host,
particle clusters, and right-gloss/wrong-iʿrāb cases into exact packets instead of generic
pending states.

Transclusion is bidirectional: a nahw decision quoted into many hovers must remain traceable
back to the entry/card/qword/source decision that produced it and forward to the rendered span.

## Hard rules honored here

- Qurʾān text is never altered; it appears as evidence only.
- No external gloss text is copied; external corpora are named as `informed_by` only.
- The public hover artifact shows only `{src:'qamus', kind:'authored', lang:'en'}`.
- Python is stdlib-only and imports from `tools.normalize_ar` (never re-implements norm).
- **PENDING beats a wrong gloss, always.**
