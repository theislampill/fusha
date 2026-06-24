# Drill — reading al-Nawawī's Forty (Level 10)

**Goal:** step from a single āyah to **classical prose** — the hadith matn of al-Arbaʿūn
al-Nawawiyyah — using the same root-and-pattern, sentence-frame discipline, plus the new
*hadith-technical* register. This is Level 10 of [`../README.md`](../README.md): the reading
widens from the Qurʾān's verse rhythm to running prose.

**Rule of the drill:** these drills point at the **Nawawī40 catalogue**, they do **not** reproduce
hadith text. The catalogue is a *review-only* vocabulary/grammar map over the matn (see the
catalogue summary at
[`../../corpora/nawawi40/nawawi40.summary.md`](../../corpora/nawawi40/nawawi40.summary.md)); it
emits candidate vocabulary, never a published gloss and never live Qamus. You study the **words
and grammar** it surfaces, then read the actual matn from a verified printed/edition copy with a
teacher.

> No full hadith matn is quoted here — each item names a **word or construction** from the
> catalogue and routes you to the procedure that resolves it. Vocabulary is bound to Qamus by
> address where an entry exists (`qamus:v###`/`n###`, per
> [`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md));
> roots in the catalogue's large "unknown" bucket await a human/QAC call and are **PENDING** —
> the catalogue flags them as low-confidence hints, never asserted roots. Ṣaḥīḥayn is a future,
> owner-gated expansion ([`../../corpora/sahihayn/PLAN.md`](../../corpora/sahihayn/PLAN.md)).

**The new register:** Nawawī40 prose adds *narration vocabulary* (the isnād words: "narrated,"
"reported," "on the authority of") that you will not have met in Qurʾānic verses. The catalogue
separates these as **hadith-technical** (low Qamus priority) so you learn them as a set.

---

## Items (study the word/construction → resolve via catalogue + Qamus)

### 1. The narration verb — root `ر و ي`
**From the catalogue:** the frequent narration verb (e.g. "narrated it / reported it"), root
`ر و ي` — a **weak** root (final `ي`). **Study task:** identify it as the isnād-frame verb that
opens most reports, not a content verb. It sits in the catalogue's **hadith-technical** set →
low Qamus priority; resolve the weak final radical via
[`../../sarf/procedures/weak-root.md`](../../sarf/procedures/weak-root.md). Status: a candidate,
**not** live Qamus.

### 2. The isnād connector — `عَنْ`
**From the catalogue:** the preposition `عَنْ` ("on the authority of / from"), the spine of every
chain ("X `عَنْ` Y `عَنْ` Z"). **Study task:** gloss it as the chain connector "on the authority
of"; it governs a jarr noun (the narrator). Particle logic:
[`../../nahw/drills/particles.md`](../../nahw/drills/particles.md) and
[`../../nahw/procedures/particle-decision.md`](../../nahw/procedures/particle-decision.md).

### 3. Authentication vocabulary — root `ص ح ح`
**From the catalogue:** `صَحِيح` ("sound / authentic"), root `ص ح ح` — a **doubled (geminate)**
root, the last two radicals identical (shown with shadda). **Study task:** read the shadda as a
geminate, **not** Form II; classify `صَحِيح` as the grading adjective. Doubled-root procedure:
[`../../sarf/procedures/doubled-root.md`](../../sarf/procedures/doubled-root.md). Hadith-technical
→ low Qamus priority.

### 4. The intention hadith's keyword — root `ن و ي`
**From the catalogue:** `نِيَّة` ("intention"), root `ن و ي` (weak final radical), the maṣdar at
the heart of the first hadith's theme. **Study task:** class it as a **noun (maṣdar)** — "an
intention," never "to intend." If an authored entry exists, bind to `qamus:n###`; if not, it is a
**candidate** for review (`new_lemma_existing_root` in the catalogue), **PENDING** until a human
authors it. Maṣdar shapes:
[`../../sarf/procedures/masdar-participle.md`](../../sarf/procedures/masdar-participle.md).

### 5. A construction, not a word — `إِنَّمَا`
**From the catalogue:** `إِنَّمَا` = `إِنَّ` ("indeed") + `مَا` (here restrictive) → "only / none
but," the restriction particle opening the intention hadith. **Study task:** resolve it as a
**construction** (two particles fused), glossed "only"; do not parse it as a single content word.
This is exactly the catalogue's *particle_or_construction_candidate* class — diacritic- and
context-sensitive, **never** resolved by `norm()`. See
[`quranic-function-words.md`](quranic-function-words.md) (items 12, 14) and
[`../../nahw/drills/particles.md`](../../nahw/drills/particles.md).

### 6. A high-priority content root — `ع م ل`
**From the catalogue:** `عَمَل` ("a deed / action"), root `ع م ل` — flagged **high Fusha-learning
priority** (a content word that recurs across the Qurʾān and the Sunnah). **Study task:** build
its family (verb `عَمِلَ` "he did," agent `عَامِل` "a doer," plural `أَعْمَال` "deeds") and bind
the noun to its Qamus address `qamus:n###` if authored. Family-building drill:
[`root-pattern-practice.md`](root-pattern-practice.md); root extraction:
[`../../sarf/procedures/root-decision.md`](../../sarf/procedures/root-decision.md).

---

## What the catalogue tells you about a word (so you triage like the reviewer)

The Nawawī40 catalogue tags each lexeme so you study in the right order — and so you never mistake
a *candidate* for live Qamus:

| catalogue signal | what it means for the learner |
|---|---|
| `already_in_qamus` | an **authored entry exists** — bind by address, study it via [`qamus-entry-drills.md`](qamus-entry-drills.md) |
| `new_lemma_existing_root` | known root, **new word** — a review candidate; study the root family, treat the gloss as **PENDING** |
| `new_root_or_unknown_root` | root **not yet certified** — the catalogue gives a *hint*, never an assertion → **PENDING**, await human/QAC |
| `hadith-technical` | isnād/narration register (`ر و ي`, `عَنْ`, `صَحِيح`) — learn as a set; **low** Qamus priority |
| `priority: high` | recurs in Qurʾān + Sunnah — **study first** |

Nothing in the catalogue is live Qamus until a human approves it via the bridge
([`../../qamus/reports/fusha-to-qamus-highlight-bridge.md`](../../qamus/reports/fusha-to-qamus-highlight-bridge.md)).
The learner reads the catalogue as a **study map**, not as authority.

---

## Checklist before you leave Nawawī40 reading

- [ ] Do I read the **isnād register** (`ر و ي`, `عَنْ`, `صَحِيح`) as a distinct set, separate
      from content vocabulary?
- [ ] Do I resolve **constructions** (`إِنَّمَا`) as fused particles by diacritics + frame, never
      by `norm()`?
- [ ] Do I **bind to a Qamus address** only when an authored entry exists, and treat
      `new_lemma`/`unknown_root` candidates as **PENDING**?
- [ ] Do I read weak (`ر و ي`, `ن و ي`) and doubled (`ص ح ح`) roots via their procedures, not by
      eyeballing the consonants?
- [ ] Do I remember the catalogue is **review-only** — no published gloss, no live Qamus, no full
      matn reproduced — and that I read the actual matn from a verified copy with a teacher?

This is the bridge to the open corpus: the same discipline carries into Level 11 (Ṣaḥīḥayn
preparation, owner-gated — [`../../corpora/sahihayn/PLAN.md`](../../corpora/sahihayn/PLAN.md)) and
Level 12 (independent reading). **Catalogue is a map, not authority — bind by address or stay
PENDING.**
