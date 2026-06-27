# Curriculum — zero to fluency in ṣarf (for ʿajamī learners)

A staged morphology path for a learner with **no Arabic** at the start. The goal is not
exam-passing; it is the same goal the rest of this pack serves: **see a Qurʾānic surface form
and recover its root, its pattern, and its class confidently enough to bind it to a Qamus
entry — or to know that it does not yet earn a gloss.** Fluency here means the reflex of
classifying *before* glossing.

Each stage gives: **what you learn → the procedure that does the work → the drill that proves
it → live Qamus examples to read → the mastery checkpoint you must pass before moving on.**
Do the stages in order; a later stage assumes the earlier reflex is automatic.
From Stage 1 onward, a rich-hover answer must also be able to produce the morphology side of
the parse-key/color contract: visible pieces, compact `parse_key.key`, and scrubbed display
classes. See
[`../drills/clitic-and-host-morphology.md`](../drills/clitic-and-host-morphology.md) and
[`../../curriculum/qamus-hover-parse-key-and-color.md`](../../curriculum/qamus-hover-parse-key-and-color.md).
For a dogfood-derived map of repeated morphology failures and where to remediate them, use
[`dogfood-sarf-map.md`](dogfood-sarf-map.md) with
[`../drills/dogfood-sarf-remediation.md`](../drills/dogfood-sarf-remediation.md).

> One discipline runs through every stage: **`norm()` proposes, it never certifies.** It drops
> the hamza seat and all harakāt, so it can widen recall but can never decide a root, a form, or
> a class. You certify from a Qamus entry / QAC / the harakāt — see
> [`../README.md`](../README.md) (the evidence ladder) and
> [`../procedures/root-decision.md`](../procedures/root-decision.md).

---

## Stage 0 — the script: letters, harakāt, sukūn, shadda

**Learn.** The 28 letters and their joined/initial/medial/final shapes; the three short vowels
(fatḥa `ـَ` = *a*, kasra `ـِ` = *i*, ḍamma `ـُ` = *u*); sukūn `ـْ` (no vowel); shadda `ـّ`
(doubled consonant); tanwīn `ـً ـٍ ـٌ` (final *-an/-in/-un*); the long vowels `ا و ي`. Learn to
*see* a harakah, because the harakah — not the consonant skeleton — is what separates two words
that look identical.

**Why it is the foundation, not decoration.** `قَالَ` "he said" and `قُلْ` "say!" share three
letters; the vowels are the whole difference. `مَلِك` "king" and `مَلَك` "angel" differ by a
single fatḥa. If you cannot read harakāt, you cannot do ṣarf — you can only guess.

- **Procedure:** none yet — this is pre-procedure literacy.
- **Read live:** open any entry on the public Qamus dictionary and read the **vowelled
  headword aloud**, e.g. `qamus:v509` headword `زَاغَ` (root `ز ي غ`); `qamus:v379` headword
  `خَفَّت` (root `خ ف ف`, note the shadda).
- **Mastery checkpoint:** read 20 fully-vowelled words aloud with every harakah, sukūn, and
  shadda correct, and write the harakāt onto an un-vowelled word from dictation. You must be
  able to *hear the difference* between `مَلِك` and `مَلَك`.

---

## Stage 1 — the root (jiḏr): three radicals carry the meaning

**Learn.** Almost every Arabic word grows from a **root** of (usually) three consonants — the
radicals — written abstractly as `ف ع ل` (*f-ʿ-l*). The root carries the core idea; everything
else (vowels, prefixes, suffixes) is pattern laid over it. `ك ت ب` underlies `كَتَبَ` "he
wrote", `كِتَاب` "book", `كَاتِب` "writer", `مَكْتُوب` "written".

**The skill to build:** strip a surface back to its radicals by the **evidence ladder**, never
by eyeballing — affixed letters masquerade as radicals and weak letters drop.

- **Procedure:** [`../procedures/root-decision.md`](../procedures/root-decision.md).
- **Drill:** [`drills-beginner.md`](drills-beginner.md) (parts A–B: identify the 3 radicals;
  strip a proclitic) and
  [`../drills/clitic-and-host-morphology.md`](../drills/clitic-and-host-morphology.md) (name
  every visible attached piece before accepting a host gloss).
- **Read live:** `qamus:v147` `كَسَبَ` (root `ك س ب`, all three radicals visible — the easy
  sound case); `qamus:v188` `يَصْدُر / صَدْر` (root `ص د ر`).
- **Mastery checkpoint:** given 15 **sound-root** Qurʾānic surfaces (no weak letter, no hamza,
  no doubling), name the three radicals for each and find the matching Qamus root, recording
  which rung of the ladder certified it. If the token has a bā', lām, kāf, wāw, fā', article,
  or suffix pronoun attached, segment it before naming the root. Zero "I read it off the
  surface" answers.

---

## Stage 2 — patterns (awzān): the same root, different shape, different word

**Learn.** A **wazn** (pattern/template) is the vowel-and-consonant mould the root is poured
into. `فَعَلَ` is one mould, `فَاعِل` another, `مَفْعُول` another. The mould, not the root,
tells you the *kind* of word and a large part of its meaning. `كَتَبَ` (`فَعَلَ`) is a verb
"he wrote"; `كَاتِب` (`فَاعِل`) is a noun "writer"; `مَكْتُوب` (`مَفْعُول`) is a noun "written".

**The reflex to build:** read the wazn first. The wazn answers *"is this a verb or a noun?"*
before you ever pick English words — and class gates the gloss vocabulary.

- **Procedure:** [`../procedures/noun-plural-gender.md`](../procedures/noun-plural-gender.md)
  (role/shape), with the pattern reference
  [`../references/quranic-morphology-notes.md`](../references/quranic-morphology-notes.md).
- **Drill:** [`drills-beginner.md`](drills-beginner.md) (part C: match a surface to its wazn
  and name verb-vs-noun).
- **Read live:** the four words of one root in
  [`../drills/root-detection.md`](../drills/root-detection.md) example 5 — `مُلْك` /
  `مَلِك` / `مَلَك` / `مَالِك` (root `م ل ك`): one root, four patterns, four meanings.
- **Mastery checkpoint:** given 12 surfaces of known roots, name the wazn and state
  **verb or noun** for each. Correctly separate the four `م ل ك` words by pattern; never call
  `ٱلْمُلْك` "angels".

---

## Stage 3 — Form I (the base verb): perfect, imperfect, voice

**Learn.** The base verb is **Form I**: perfect `فَعَلَ` ("he did", past), imperfect
`يَفْعُلُ/يَفْعِلُ/يَفْعَلُ` ("he does", present). Person, number, and gender are carried in the
conjugation — `قَالَ` "he said", `قَالَتْ` "she said", `قَالُوا` "they said" — so the English
must be **finite**, never a bare infinitive on a conjugated verb. And the **passive** is a
vowel signature: ḍamma–kasra `خُلِقَ` "was created" vs active `خَلَقَ` "created".

- **Procedure:** [`../procedures/verb-form.md`](../procedures/verb-form.md) (measure, voice,
  person/number).
- **Drill:** [`drills-intermediate.md`](drills-intermediate.md) (parts A–B: name the form;
  active vs passive reconstruction), building on
  [`../drills/verb-measures.md`](../drills/verb-measures.md) parts A–B and the verb-suffix rows
  in [`../drills/clitic-and-host-morphology.md`](../drills/clitic-and-host-morphology.md).
- **Read live:** `qamus:v147` `كَسَبَ` "earned" (Form I, sound, active); contrast the passive
  signature drilled at [`../drills/verb-measures.md`](../drills/verb-measures.md) part B
  (`خَلَقَ` ↔ `خُلِقَ`).
- **Mastery checkpoint:** for 12 Form-I surfaces, give the finite English (with the right
  person/number/gender) and flag active vs passive from the harakāt. Never emit
  "to …" on a conjugated verb; never drop an attached object pronoun; never read `خُلِقَ` as
  active.

---

## Stage 4 — Forms II–X (the derived verbs): the augment changes the verb

**Learn.** Adding a shadda (II `فَعَّلَ`), a hamza (IV `أَفْعَلَ`), a `تـ` (V/VI/VIII), a `نـ`
(VII), or `اِسْتَـ` (X) builds a **new verb of the same root** with a regularly-shifted sense:
II/IV are often causative/intensive, V/VI reflexive/mutual, VII passive-ish, VIII middle, X
"seek/consider". The augment letters and the connecting hamzat al-waṣl `ٱ` are **not
radicals** — reading them as radicals invents a bogus root.

**The non-negotiable:** never gloss a derived form with the Form I sense. `نَزَلَ` (I)
"descended" ≠ `نَزَّلَ` (II) "sent down gradually" ≠ `أَنزَلَ` (IV) "sent down".

- **Procedure:** [`../procedures/verb-form.md`](../procedures/verb-form.md), with the paradigm
  [`../references/verb-measures-table.md`](../references/verb-measures-table.md) and machine
  rules [`../rules/verb-measures.json`](../rules/verb-measures.json) /
  [`../rules/verb-measure-gates.json`](../rules/verb-measure-gates.json).
- **Drill:** [`drills-intermediate.md`](drills-intermediate.md) (part A, derived-form rows) and
  [`../drills/verb-measures.md`](../drills/verb-measures.md) part A.
- **Read live:** the Form I↔IV contrast in
  [`../drills/root-detection.md`](../drills/root-detection.md) example 2 — `يَأْتِي` (I,
  "comes") vs `ءَاتَىٰ` (IV, "gave"), same root `أ ت ى`, different English.
- **Mastery checkpoint:** for the triad `نَزَلَ / نَزَّلَ / أَنزَلَ` and the triad
  `عَلِمَ / عَلَّمَ / اِسْتَعْلَمَ`, name each form and give a distinct, form-correct English.
  Strip every augment letter before proposing the root.

---

## Stage 5 — weak roots, hamza, doubled roots (the hidden radical)

**Learn.** A radical that is `و`/`ي` (or a hamza, or a doubled C2=C3) **hides** in the surface:
- **hollow** (C2 weak): `قَالَ` shows `ا`, not `و` (root `ق و ل`); the `ا` *is* the radical.
- **defective** (C3 weak): `دَعَا` ends in `ا` (root `د ع و`); `رَمَى` ends in `ى` (root `ر م ي`).
- **assimilated** (C1 weak): `وَجَدَ` → present `يَجِدُ`; the `و` drops in the imperfect.
- **doubled** (C2=C3): `رَدَّ` wears a shadda hiding the third radical (root `ر د د`).
- **hamzated**: the seat (`أ إ ؤ ئ ء`) is meaning-bearing and `norm()` deletes it.

**The reflex:** when a radical is missing or fused, **recover it from the family** (the
muḍāriʿ / QAC), never let `norm()` decide it.

- **Procedure:** [`../procedures/root-decision.md`](../procedures/root-decision.md) (weak-root
  recovery branch), reference
  [`../references/weak-verbs.md`](../references/weak-verbs.md), gates
  [`../rules/weak-root-gates.json`](../rules/weak-root-gates.json).
- **Drill:** [`drills-intermediate.md`](drills-intermediate.md) (part C: weak-root recovery)
  and the advanced edge cases in [`drills-advanced.md`](drills-advanced.md).
- **Read live:** `qamus:v509` `زَاغَ` (hollow, root `ز ي غ` — the `ا` is the medial `ي`
  surfacing); `qamus:v379` `خَفَّت` (doubled, root `خ ف ف` — the shadda hides C3);
  `qamus:n575` `حَاشَ لِلَّه` (root `ح ش ي`, defective C3).
- **Mastery checkpoint:** for 10 weak/hamzated/doubled surfaces, recover the **true three
  radicals** and name the class (`hollow_root_c2_hidden`, `defective_c3_alternation`,
  `assimilated_c1_dropped`, `geminate_shadda`, `hamza_sensitive`). Never assert a weak root
  from a `norm()` collapse; when the seat is the only distinguisher and the source is
  ambiguous → PENDING.

---

## Stage 6 — nominal derivation: maṣdar, ism fāʿil, ism mafʿūl, plurals

**Learn.** Roots also throw off **nouns** with fixed patterns: the **maṣdar** (verbal noun —
the *action*: `ذِكْر` "remembrance", `إِيمَان` "faith", `اِسْتِغْفَار` "seeking forgiveness"),
the **ism fāʿil** (active participle — the *doer*: `كَاتِب` "writer", `مُؤْمِن` "believer"), and
the **ism mafʿūl** (passive participle — the *done-to*: `مَكْتُوب` "written", `مَخْلُوق`
"created thing"). Plurals come **sound** (`ـُونَ/ـِينَ/ـَاتٌ`, morphology not root) or **broken**
(`كِتَاب → كُتُب`, sharing the root not the surface).

**The cardinal rule:** a maṣdar/participle is a **noun** — it takes a noun gloss, never
"to …". `رَسُولًا` is "a messenger", not "to send". Derived مُـ participles split active/passive
by the **penult vowel**: `مُعَلِّم` "teacher" (kasra) vs `مُعَلَّم` "taught one" (fatḥa).

- **Procedure:** [`../procedures/noun-plural-gender.md`](../procedures/noun-plural-gender.md),
  reference [`../references/masdar-participle-notes.md`](../references/masdar-participle-notes.md),
  gates [`../rules/masdar-participle-gates.json`](../rules/masdar-participle-gates.json).
- **Drill:** [`drills-intermediate.md`](drills-intermediate.md) (part B: maṣdar vs participle)
  and [`../drills/verb-measures.md`](../drills/verb-measures.md) part C.
- **Read live:** `qamus:n300` `بَغْضَاء` (maṣdar-shaped noun "intense hatred", root `ب غ ض`);
  `qamus:n621` `شَطْأَهُ` ("its shoot", a plant noun — never a verb gloss). Read each as a
  **noun**.
- **Mastery checkpoint:** for 12 derived nominals, label each `masdar` / `ism_fa3il` /
  `ism_mafʿul` / `plain noun` and give a **nominal** gloss; split `مُعَلِّم` from `مُعَلَّم` by
  the vowel; match one broken plural to its singular's entry. Zero "to …" glosses on a noun.

---

## Stage 7 — fluency: classify-before-gloss as a reflex (homographs, proper names, context)

**Learn.** Fluency is not more rules — it is the rules fused into one fast gate. The remaining
traps are where two readings collapse:
- **diacritic homographs** decided on the content-letter harakah (`مَن`/`مِن`, `ذِكْر`/`ذَكَر`,
  `ٱلْمُلْك`/`ٱلْمَلِك`) — see [`../drills/homograph-regressions.md`](../drills/homograph-regressions.md);
- **proper names** that only *look* like verbs/participles (`مُحَمَّد` is not "to praise";
  `صَٰلِحًا` is "righteous", not the Prophet Ṣāliḥ);
- **same-root polysemy** that only **context** resolves (`أَنْهَار` "rivers" vs `نَهَار`
  "daytime"; `يَقْدِرُ` "restricts" vs "is able").

This is the point of the whole path: a token earns a gloss **iff** root + pattern + class +
sense all agree on a Qamus entry; otherwise it stays plain. **PENDING beats wrong.**
QAC concept metadata may flag that a surface is semantically a person, place, people, plant,
book, or body part, but it is not morphology and not a translation source. Use it as a review
flag for proper-name/common-word collisions; let sarf and nahw certify the token.

- **Procedure:** [`../procedures/homograph-risk.md`](../procedures/homograph-risk.md) (the
  `norm_strict` surface-key safety probe) and the apply path
  [`../procedures/hover-application.md`](../procedures/hover-application.md).
- **Drill:** [`drills-advanced.md`](drills-advanced.md) (homograph disambiguation by pattern;
  passive reconstruction; doubled/hamzated edge cases) and
  [`../drills/homograph-regressions.md`](../drills/homograph-regressions.md), plus
  [`../drills/clitic-and-host-morphology.md`](../drills/clitic-and-host-morphology.md) for the
  host-only hover failure class.
- **Read live:** the same-root polysemy walk-throughs in
  [`../drills/root-detection.md`](../drills/root-detection.md) examples 6–7 (`ن ه ر`,
  `ر ج ل`).
- **Mastery checkpoint:** run a mixed 20-token set (verbs, derived forms, weak roots, nominals,
  homographs, one proper name, one context-bound polyseme) and for each emit a defensible
  decision **`resolved | pending | quarantine`** with the rung used and the precise pending
  reason. The graduation bar: every `resolved` is right, and nothing wrong is shipped — wrong
  costs more than blank.

---

## The arc in one table

| Stage | You can now … | Procedure | Drill | Checkpoint (pass to advance) |
|---|---|---|---|---|
| 0 | read harakāt/shadda/sukūn | — | — | read 20 vowelled words aloud; hear `مَلِك`≠`مَلَك` |
| 1 | recover the 3 radicals | [root-decision](../procedures/root-decision.md) | [beginner A–B](drills-beginner.md) | 15 sound roots, rung recorded |
| 2 | read the wazn, name verb/noun | [noun-plural-gender](../procedures/noun-plural-gender.md) | [beginner C](drills-beginner.md) | 12 patterns; the four `م ل ك` words apart |
| 3 | Form I + voice + person | [verb-form](../procedures/verb-form.md) | [intermediate A–B](drills-intermediate.md) | 12 finite glosses; active≠passive |
| 4 | Forms II–X distinctly | [verb-form](../procedures/verb-form.md) | [intermediate A](drills-intermediate.md) | `نَزَلَ/نَزَّلَ/أَنزَلَ` distinct |
| 5 | recover hidden radicals | [root-decision](../procedures/root-decision.md) | [intermediate C](drills-intermediate.md) | 10 weak/hamzated/doubled, class named |
| 6 | maṣdar/participle/plural → noun gloss | [noun-plural-gender](../procedures/noun-plural-gender.md) | [intermediate B](drills-intermediate.md) | 12 nominals; no "to …" on a noun |
| 7 | classify-before-gloss reflex | [homograph-risk](../procedures/homograph-risk.md) | [advanced](drills-advanced.md) | 20-token mixed set; nothing wrong shipped |

> **Standing constraints (carried from [`../README.md`](../README.md) and
> [`../SKILL.md`](../SKILL.md)):** Qurʾān text is never altered; `norm()` cannot certify;
> class gates the gloss vocabulary; external references are `informed_by`, never copied; the
> public emit is exactly `{src:'qamus', kind:'authored', lang:'en'}` — or nothing. When in doubt at any
> stage: **PENDING beats wrong.**
