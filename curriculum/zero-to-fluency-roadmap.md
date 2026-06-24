# Zero-to-fluency roadmap — the 12-level ladder

This is the full ladder the [`README.md`](README.md) indexes. Each level is one rung: a small,
checkable gain that unlocks more real text. Read it top to bottom; do not skip a rung you have
not cleared against [`mastery-checkpoints.md`](mastery-checkpoints.md). If you do not know
where to start, take the [`placement-test.md`](placement-test.md) first.

Each level is given as:

- **Goal** — the one thing this rung adds.
- **Ṣarf / nahw skills used** — the exact procedures to read *before* and lean on *during*.
- **Qamus entries used** — which addresses (`qamus:v###` / `n###` / `p###`) supply the words,
  drawn from [`../qamus/indexes/existing_qamus_index.json`](../qamus/indexes/existing_qamus_index.json).
- **Drill** — what to do, with original vowelized examples.
- **Checkpoint** — the pass bar (mirrored in [`mastery-checkpoints.md`](mastery-checkpoints.md)).

The arc: **Levels 1–8 build everything needed to read one short āyah.** Levels 9–12 widen that
reading from a single āyah to a root family, to classical prose, to the open corpus.

---

## Level 1 — Script & sounds

**Goal.** Read and write every Arabic letter in its four positions, and pronounce the short
vowels (fatḥa, kasra, ḍamma), sukūn, shadda, and tanwīn.

**Ṣarf / nahw skills used.** None yet — this is pre-grammar. But the *habit* that the whole
ladder depends on starts here: **always read the harakah, never just the consonants.** That
habit is what later lets you separate `مَن` from `مِن`
(see [`../sarf/drills/homograph-regressions.md`](../sarf/drills/homograph-regressions.md)).

**Qamus entries used.** None — words are too early. Use letters and nonsense syllables only.

**Drill.** Write each letter joined and unjoined. Then read these vowel contrasts aloud,
hearing the difference the harakah makes: `بَ بِ بُ` · `كَتَبَ` (he wrote) · `كُتِبَ` (it was
written) · `مَدْرَسَة` (school) with sukūn on the dāl and tāʾ marbūṭa at the end. Mark the
shadda: `رَبّ` (lord) is *not* `رَب`.

**Checkpoint.** Read any vowelized three-letter word aloud correctly on first sight, including
sukūn and shadda; write a dictated word. No meaning required yet.

---

## Level 2 — Core particles (ḥurūf)

**Goal.** Recognize and gloss the most common particles, which carry no root and glue every
sentence together: `فِي` (in), `مِنْ` (from), `إِلَىٰ` (to), `عَلَىٰ` (on), `عَنْ` (about/from),
`مَعَ` (with), `وَ` (and), `لَا` (no/not), `لَمْ` (did not).

**Ṣarf / nahw skills used.** [`../nahw/procedures/particle-decision.md`](../nahw/procedures/particle-decision.md)
and the inventory in [`../nahw/references/particles.md`](../nahw/references/particles.md). Key
rule learned now: a particle is glossed by the harakah on its **content** letter, not its
first letter — a `وَ`/`فَ` prefix shifts the reading rightward.

**Qamus entries used.** The particle class, `qamus:p###` (e.g. `qamus:p007`) — the small,
high-frequency closed set. Read each entry's single concise gloss.

**Drill.** Gloss each in isolation, then notice what changes nothing: `فِي الْبَيْتِ` (in the
house), `مِنَ الْمَسْجِدِ` (from the mosque), `إِلَى الْمَدْرَسَةِ` (to the school). Then the
trap: `لَمْ` (did not) vs `لِمَ` (why) — read the second letter's harakah.

**Checkpoint.** Gloss the nine particles above with no hint; correctly read `لَمْ` vs `لِمَ`.

---

## Level 3 — Nouns: gender, number, definiteness

**Goal.** Handle the noun: the definite article `الْ`, masculine vs feminine (tāʾ marbūṭa
`ة`), and the three numbers — singular, dual (`ـَانِ`/`ـَيْنِ`), and plural (sound and broken).

**Ṣarf / nahw skills used.** [`../sarf/procedures/noun-plural-gender.md`](../sarf/procedures/noun-plural-gender.md)
for plural shapes (the broken plural is *not* predictable from the singular — it is stored, not
derived), and the `مـ`-participle caution in
[`../sarf/references/masdar-participle-notes.md`](../sarf/references/masdar-participle-notes.md).

**Qamus entries used.** The noun class, `qamus:n###`, taken in frequency order so the commonest
nouns come first. Read each entry's `forms[]` to see the attested plural.

**Drill.** Build the trio for each: `كِتَاب` → dual `كِتَابَانِ` → broken plural `كُتُب`;
`مُسْلِم` → sound plural `مُسْلِمُونَ`; `بِنْت` (girl) → broken plural `بَنَات`. Definiteness:
`بَيْت` (a house) vs `الْبَيْت` (the house). Gender by the `ة`: `مُعَلِّم` (m.) /
`مُعَلِّمَة` (f.).

**Checkpoint.** For ten given singular nouns, state gender and the *attested* plural (from the
Qamus entry, not guessed); add and strip `الْ` correctly.

---

## Level 4 — Verbs & roots

**Goal.** See the three-radical **root** inside a word, read past (`فَعَلَ`) and present
(`يَفْعَلُ`) tense, and grasp that a *pattern* (wazn) sits on the root to make meaning.

**Ṣarf / nahw skills used.** [`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md)
(extract the root via the evidence ladder, not by eyeballing) and
[`../sarf/procedures/verb-form.md`](../sarf/procedures/verb-form.md) with the paradigm in
[`../sarf/references/verb-measures-table.md`](../sarf/references/verb-measures-table.md).

**Qamus entries used.** The verb class, `qamus:v###`, in printed-book frequency order — the
highest-yield verbs first. Read `root`, `forms[]`, and the senses.

**Drill.** From a surface, name the root and tense: `كَتَبَ` → root `ك ت ب`, past, "he wrote";
`يَكْتُبُ` → present, "he writes"; `نَصَرَ` → `ن ص ر`, "he helped". Then feel the wazn change
meaning on one root: `عَلِمَ` (he knew) → `عَلَّمَ` (he taught, Form II). Note the guard:
`رَسُول` (messenger) is a **noun**, not the verb "to send" — a noun never takes a verb gloss.

**Checkpoint.** Extract the correct root from twelve vowelized verbs and state past vs present;
do not assign a verb meaning to a noun.

---

## Level 5 — Iḍāfa & jār-majrūr

**Goal.** Read the two constructs that carry most of the grammar weight: **iḍāfa** (the
genitive construct, "the X of Y") and **jār-majrūr** (preposition + noun, and preposition +
pronoun).

**Ṣarf / nahw skills used.** [`../nahw/procedures/idafa-jar-majrur.md`](../nahw/procedures/idafa-jar-majrur.md)
and [`../nahw/procedures/preposition-pronoun.md`](../nahw/procedures/preposition-pronoun.md);
references [`../nahw/references/idafa.md`](../nahw/references/idafa.md) and
[`../nahw/references/jar-majrur.md`](../nahw/references/jar-majrur.md). Critical guard:
preposition + pronoun reshapes the *wording*, e.g. `إِلَيْنَا` = "to us" (root `أ ل ي`), **not**
the root `ل ي ن` ("soft").

**Qamus entries used.** Mixed `qamus:n###` heads + `qamus:p###` prepositions; read how a
preposition's gloss bends around its object.

**Drill.** Iḍāfa: `بَابُ الْبَيْتِ` (the door of the house), `كِتَابُ اللهِ` (the Book of
Allāh) — note the first noun drops `الْ` and the second takes jarr. Jār-majrūr: `فِي
الْبَيْتِ` (in the house); preposition + pronoun: `بِهِ` (with it / in it), `لَهُ` (for him),
`عِنْدَهُ` (with him / in his presence).

**Checkpoint.** Translate five iḍāfa phrases and five jār-majrūr (three with a pronoun
suffix); correctly render `إِلَيْنَا` as "to us," not as a "soft" root.

---

## Level 6 — Nominal & verbal sentences

**Goal.** Tell the two sentence types apart and parse each: the **nominal** sentence (starts
with a noun: mubtadaʾ + khabar) and the **verbal** sentence (starts with a verb: verb + doer +
object).

**Ṣarf / nahw skills used.** [`../nahw/procedures/referent-context.md`](../nahw/procedures/referent-context.md)
and [`../nahw/drills/sentence-context.md`](../nahw/drills/sentence-context.md); case/mood
basics in [`../nahw/references/irab-case-mood.md`](../nahw/references/irab-case-mood.md).

**Qamus entries used.** Verbs (`qamus:v###`) for the predicate of verbal sentences; nouns
(`qamus:n###`) for subject/predicate of nominal ones.

**Drill.** Nominal: `الْبَيْتُ كَبِيرٌ` (the house is big — note no verb "to be"); `اللهُ
غَفُورٌ` (Allāh is Forgiving). Verbal: `كَتَبَ الطَّالِبُ الدَّرْسَ` (the student wrote the
lesson — verb, then doer in rafʿ, then object in naṣb). Flip the same content between the two
types and watch the endings move.

**Checkpoint.** Label five sentences nominal vs verbal and identify the subject; in a verbal
sentence, point to the doer and the object by their endings.

---

## Level 7 — Qurʾānic function words

**Goal.** Master the high-frequency function words whose meaning turns on a single harakah or
on context — the words that decide whether you read an āyah right or wrong.

**Ṣarf / nahw skills used.** [`../nahw/procedures/particle-decision.md`](../nahw/procedures/particle-decision.md),
the homograph drill [`../sarf/drills/homograph-regressions.md`](../sarf/drills/homograph-regressions.md),
and [`../nahw/references/quranic-nahw-notes.md`](../nahw/references/quranic-nahw-notes.md).

**Qamus entries used.** `qamus:p###` particles plus the relative/conditional set; read each
entry's distinguishing note.

**Drill.** The exact pairs the gloss pipeline fights: `مَنْ` (who) vs `مِنْ`/`وَمِنَ` (from);
`مَا` (what / not) by context; `إِنَّ` (indeed) vs `أَنَّ` (that) by the hamza seat; `الَّذِي`
(the one who, m.) / `الَّتِي` (f.); the conditional `إِنْ` (if). Read each in a phrase and say
which reading holds and why.

**Checkpoint.** Disambiguate `مَنْ`/`مِنْ`, `إِنَّ`/`أَنَّ`, and `مَا` (relative vs negative)
in eight unmarked-by-meaning phrases, each time naming the deciding feature.

---

## Level 8 — Reading a short āyah

**Goal.** Read one full short āyah word by word, gloss each word, and assemble the meaning —
using the **hover layer** as a backstop, not a crutch.

**Ṣarf / nahw skills used.** Everything from Levels 2–7, plus the hover-application discipline
in [`../sarf/procedures/hover-application.md`](../sarf/procedures/hover-application.md).

**Qamus entries used.** Whatever the āyah's words resolve to. On `qamus.dawah.wiki`, hover or
tap each word: a covered word shows an **authored** gloss (`{src:'qamus', kind:'authored'}`);
an uncovered word shows nothing — that blank means "not yet certified," your cue to parse it
by procedure. Full method in [`qamus-learning-path.md`](qamus-learning-path.md).

**Drill.** Take a short, well-known āyah. Without hovering, gloss each word yourself; *then*
hover to check. Where the hover is blank, do not invent a gloss — write your PENDING reason
(homograph? root unclear? noun-vs-verb?) and route it to the matching procedure. Verify the
whole meaning against the muṣḥaf.

**Checkpoint.** Read a short āyah you have not seen, glossing each covered word and producing a
*named* PENDING for each uncovered one — zero confident wrong glosses.

---

## Level 9 — Qamus root study

**Goal.** Stop reading words one at a time and start reading a **root as a family** — all its
senses, its derived forms, and everywhere it is used.

**Ṣarf / nahw skills used.** [`../sarf/procedures/verb-form.md`](../sarf/procedures/verb-form.md)
to relate the forms of one root, and the source-address method in
[`../qamus/reports/source-address-model.md`](../qamus/reports/source-address-model.md).

**Qamus entries used.** A single entry studied in depth — e.g. open `qamus:v443`, read its
`root`, every sense, each `forms[]`, and follow every `usage_refs[]` (`quran:S:A:W`) to read
the word in its āyah. The address is your bookmark; `used_by` shows where it appears.

**Drill.** Pick a frequent root. Read its entry top to bottom. For each `usage_refs[]`, open
that āyah on `qamus.dawah.wiki` and read the form *in context* — watch one root carry related
but distinct senses across different āyāt. Method detailed in
[`qamus-learning-path.md`](qamus-learning-path.md).

**Checkpoint.** For a given root entry, list its senses and derived forms from memory and read
two of its usage āyāt aloud with correct meaning.

---

## Level 10 — Reading al-Nawawī's Forty

**Goal.** Step off the āyah and read **classical prose**: the matn of al-Arbaʿūn
al-Nawawiyyah, where sentences are longer and the vocabulary widens past the Qurʾān-centric
core.

**Ṣarf / nahw skills used.** All of ṣarf + nahw, applied to running prose; the grammar-safety
discipline in [`../nahw/procedures/grammar-risk-gate.md`](../nahw/procedures/grammar-risk-gate.md).

**Qamus entries used.** The 2,092 core, **plus** the review-only Nawawī40 candidate vocabulary
catalogued in [`../qamus/candidates/nawawi40/`](../qamus/candidates/nawawi40/) (see the summary
[`../corpora/nawawi40/nawawi40.summary.md`](../corpora/nawawi40/nawawi40.summary.md)). Note the
learner reads only *authored*, reviewed material — candidates not yet approved remain PENDING,
not invented glosses.

**Drill.** Read the famous first matn (`إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ`, "actions are but
by intentions") clause by clause: name each word's root/pattern, parse the iḍāfa and
jār-majrūr, then assemble. Mark every word not in your core as PENDING and look up whether a
reviewed entry covers it.

**Checkpoint.** Read one short Nawawī matn with full parsing and correct meaning, distinguishing
covered vocabulary from honestly-PENDING vocabulary.

---

## Level 11 — Ṣaḥīḥayn preparation

**Goal.** Acquire the **hadith-technical register** — the isnād and narration vocabulary that
saturates the two Ṣaḥīḥs but is rare in the Qurʾān — so you can read a full hadith with its
chain.

**Ṣarf / nahw skills used.** [`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md)
for the narration roots, and the honest-PENDING discipline throughout — many of these forms are
still in the unknown-root bucket pending human confirmation (see the SN8/P17 notes in
[`../corpora/nawawi40/nawawi40.summary.md`](../corpora/nawawi40/nawawi40.summary.md)).

**Qamus entries used.** Core entries plus the hadith-technical set flagged in the Nawawī40
pass — words like `رَوَاهُ` (he narrated it, root `ر و ي`), `إِسْنَاد` (chain of narration),
`صَحِيح` (sound). Ṣaḥīḥayn proper is a **future** corpus; its plan is
[`../corpora/sahihayn/PLAN.md`](../corpora/sahihayn/PLAN.md).

**Drill.** Read a short isnād aloud and gloss its frame: `حَدَّثَنَا` (he narrated to us),
`عَنْ فُلَانٍ` (on the authority of so-and-so), `قَالَ` (he said). Separate the *frame* (isnād)
from the *matn* (the report itself) before reading for meaning.

**Checkpoint.** Read a short hadith with its isnād, glossing the narration frame and reading
the matn — knowing which register each word belongs to.

---

## Level 12 — Independent fuṣḥā reading

**Goal.** Read **unseen** fuṣḥā text without the ladder — and, when stuck, diagnose your own
block with a precise PENDING reason and reach for the exact procedure that resolves it.

**Ṣarf / nahw skills used.** The whole repo, but now *self-directed*: the learner is the agent.
The pending-reason vocabulary of [`../nahw/README.md`](../nahw/README.md) (`homograph_haraka`,
`pos_mismatch`, `multi_sense`, `contronym`, `referent_unresolved`, `proper_name`,
`seat_collapsed`) becomes the learner's own self-diagnosis grid.

**Qamus entries used.** The whole index as a reference, plus the discipline of resolving a new
word to an address before trusting it
([`../qamus/reports/source-address-model.md`](../qamus/reports/source-address-model.md)).

**Drill.** Read a passage you have never seen. For each word you cannot resolve, do not guess:
write the *specific* PENDING reason and the procedure that clears it, resolve it, and continue.
Measure yourself by how *precise* your PENDINGs are, not by how few.

**Checkpoint.** Read an unseen fuṣḥā paragraph, producing for every block a named PENDING reason
and the procedure that resolves it — and clearing most of them yourself. This is fluency: not
"never stuck," but **always knowing exactly why, and what to do about it.**

---

## How to climb

One rung at a time. Each rung's **Checkpoint** is the gate, written out in full with its
remediation map in [`mastery-checkpoints.md`](mastery-checkpoints.md). The single rule that
holds across all twelve rungs — and across the whole repo — is the one the gloss pipeline
lives by: **a precise blank beats a confident wrong.**
