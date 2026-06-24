# Drill — reading a Qamus entry (Level 9)

**Goal:** study a **root as the Qamus stores it** — read one entry top to bottom and answer
questions about its root, forms, senses, and usage. This is Level 9 of
[`../README.md`](../README.md): the reading widens from a single āyah to a *root family* held in a
structured record you can revisit by its address.

**Rule of the drill:** read the **whole entry as one object** — root, headword, section, the
ordered `senses[]`, the `forms[]`, the `usage[]` with example āyāt and `surah:ayah` refs — before
you answer. The entry's own fields are the source of truth; do not import a sense the entry does
not list, and do not gloss a form against a sense it is not attached to.

> Each entry has a stable address (`qamus:v###` / `n###` / `p###`, per
> [`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md));
> a sense is `…#sense=N`, a form `…#form=…`, a ref `…#ref=S:A`. To author or repair an entry the
> agent follows
> [`../../sarf/procedures/qamus-entry-authoring.md`](../../sarf/procedures/qamus-entry-authoring.md)
> — the learner only *reads* it. All entry content is `{src:'qamus', kind:'authored'}`; nothing
> external is reproduced.

**The shape you are reading** (one entry):

```
root        ق و ل                      ← the three radicals
headword    قَالَ                       ← the citation form
translit    qāla
section     verb                       ← class
category    Form I (hollow)
definition  to say, to speak
total_uses  <count from usage>
senses[]    [ {sense=0: "to say / utter"},
              {sense=1: "to declare / assert"} ]
forms[]     [ قَالَ, يَقُولُ, قَوْل, قَائِل ]
usage[]     [ {form: قَالَ,  ref 2:30, ...},
              {form: يَقُولُ, ref 2:8,  ...} ]
notes       weak middle radical (و → ا in past)
```

(The values above are an illustrative reading of the `ق و ل` family — open the live entry on
qamus.dawah.wiki for its real senses/usage. The schema mirrors a real entry; see
[`../../sarf/procedures/qamus-entry-authoring.md`](../../sarf/procedures/qamus-entry-authoring.md).)

---

## Items (read the entry, then answer)

### 1. Name the root from the headword
**Q:** The entry's `headword` is `قَالَ` and `notes` say "weak middle radical." What is the
**root**, and why isn't it `ق ا ل`?
**A:** Root `ق و ل`. The `ا` in `قَالَ` is the **weak middle radical `و`** surfacing as a long
ā in Form I past; it returns as `و` in `يَقُولُ`/`قَوْل`. The alif is not a radical. (Weak roots:
[`../../sarf/procedures/weak-root.md`](../../sarf/procedures/weak-root.md).)

### 2. Class before gloss
**Q:** The `forms[]` list includes `قَوْل`. Which **section/class** is it, and how should it be
glossed?
**A:** `قَوْل` is a **maṣdar (noun)** — "a saying / word," **not** "to say." A form inherits the
root's theme but the *pattern* sets the class; gloss the noun as a noun. (See
[`root-pattern-practice.md`](root-pattern-practice.md).)

### 3. Bind a form to the right sense
**Q:** An entry lists `sense=0: "to say / utter"` and `sense=1: "to declare / assert."` A usage
row carries `form: يَقُولُ, ref 2:8`. Which **sense address** does that usage attach to, and how
do you decide?
**A:** You read the example āyah at `qamus:…#ref=2:8` and pick the sense the **context** supports
— you do **not** default to `sense=0`. The form-to-sense binding lives in the `usage[]` row, not
in the form alone. If the context is unclear → **PENDING**.

### 4. Count uses from usage, not memory
**Q:** Where does `total_uses` come from, and may you cite a higher number you "remember"?
**A:** `total_uses` reconciles to the entry's own `usage[]` rows (and the addresses they point
at). Never hardcode or inflate a count — cite what the entry stores. (Same data-honesty rule the
scoreboards enforce: [`../../qamus/reports/hover-gloss-scoreboard.md`](../../qamus/reports/hover-gloss-scoreboard.md).)

### 5. Distinguish two senses on one root
**Q:** A noun entry for root `ن ه ر` lists `sense: "river"` with forms `نَهْر`/`أَنْهَار`, and a
separate `sense: "daytime"` with form `نَهَار`. A reader meets `أَنْهَار`. Which sense?
**A:** "rivers" — `أَنْهَار` is the **broken plural of `نَهْر`** (river), bound to the *river*
sense; it is not a form of "daytime." Pick the sense from the **form's** attachment + context,
never from the shared consonants. (See
[`../../sarf/drills/root-detection.md`](../../sarf/drills/root-detection.md).)

### 6. Read a usage ref as an address
**Q:** A `usage[]` row says `ref 2:255`. What does that address point at, and what may you do
with it?
**A:** It is `qamus:…#ref=2:255` → the Qurʾān **position** `quran:2:255` where this form occurs.
You may *open and read* the verbatim āyah there (it is a pointer); you may **not** alter the text
or copy an external gloss for it. (Address model:
[`../../qamus/reports/source-address-model.md`](../../qamus/reports/source-address-model.md).)

### 7. Spot a missing-form gap (honest blank)
**Q:** You read a verse and meet a form (say a Form II `قَوَّلَ`-type derivative) that the entry's
`forms[]` does **not** list. What is the correct learner move?
**A:** Treat it as **uncovered** — the hover would read blank. Route to procedure
([`../../sarf/procedures/verb-form.md`](../../sarf/procedures/verb-form.md)) to identify the form,
and (for the agent) it becomes a **repair candidate** against the address, never a guessed gloss.
A blank is a feature, not a failure.

### 8. Read `notes` as a guard, not decoration
**Q:** An `أ م ن` entry's `notes` warn: "root `أ م ن`; do **not** confuse `إِيمَان` (faith) with
`أَيْمَان` 'oaths' (root `ي م ن`)." Why is that note in the entry, and how do you use it?
**A:** Because the two collide under `norm()` (the hamza seat is dropped). The note is a
**certification guard**: when you meet `إِيمَان`/`أَيْمَان`, confirm the root by the **hamza seat
+ harakāt** (`norm_strict`/QAC), not the bare consonants — exactly the regression class in
[`../../sarf/drills/homograph-regressions.md`](../../sarf/drills/homograph-regressions.md).

---

## Checklist before you leave Qamus-entry reading

- [ ] Can I name the **root** from the headword, accounting for weak/hamzated/doubled radicals?
- [ ] Do I read **section/class** and gloss a form *as its class* (maṣdar = noun, participle =
      person/thing)?
- [ ] Do I bind each **form to the sense** its `usage[]` row attaches it to, via the verse — not
      by defaulting to `sense=0`?
- [ ] Do I take **`total_uses`** and refs from the entry's own fields, never inflating them?
- [ ] When I meet a **form not in `forms[]`**, do I treat it as an honest blank and route to
      procedure?
- [ ] Do I read the entry's **`notes`** as certification guards against homograph traps?

Next, take the same read-the-record discipline to classical prose vocabulary in
[`nawawi40-reading-drills.md`](nawawi40-reading-drills.md). **Read the whole entry, bind form to
sense, blank beats wrong.**
