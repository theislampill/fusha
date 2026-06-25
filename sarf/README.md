# sarf — Arabic morphology support

`sarf/` is the **morphology (ṣarf) support pack** for Fusha. It is the layer an agent
consults *before* it authors a new Qamus gloss, repairs an existing one, or classifies a
Nawawī‑40 candidate token. The main playbook is `sarf/SKILL.md` (authored separately);
the files here are the concrete drills, references, and decision rules that the skill
points at.

The job of ṣarf here is narrow and defensive: **get the root and the pattern right so a
hover gloss never lands on the wrong word.** Everything in this pack exists because a
specific wrong gloss once shipped (a verb gloss on a noun, a preposition glossed as a
relative pronoun, a proper name treated as a verb). The drills encode those scars.

## What this is for

A Qamus gloss is a tiny, high‑confidence claim: *this surface form, in this āyah, means
this in English, and the evidence is this Qamus entry.* Morphology is how we keep the
claim honest. Two surface forms can share every consonant and still be different words;
two words can share a root and still mean opposite things. Before you assert a gloss you
must be able to answer:

1. **What is the root?** (the three/four radicals — `ق و ل`, `أ م ن`)
2. **What pattern is this surface in?** (Form I–X verb, maṣdar, ism fāʿil, ism mafʿūl,
   broken plural, …)
3. **Does the candidate Qamus entry actually cover *this* word in *this* sense?**

If any of those is uncertain, the rule is **PENDING, not a guess**. A blank hover is
correct; a wrong hover is a defect.

## How an agent uses this pack

Use it in this order. Do not skip to the bottom.

1. **Root detection** — `drills/root-detection.md`. Strip the surface to its radicals via
   the evidence ladder (below), not by eyeballing. Worked examples for the roots that
   recur in the corpus.
2. **Homograph check** — `drills/homograph-regressions.md`. If the surface is a short
   function word or a diacritic‑homograph of a content word, the consonants are *not*
   enough. Read the harakah on the **content letter**, the hamza seat, the shadda. This is
   the drill of the exact pairs we fought (`مَن`/`مِن`, `لِمَا`/`لَمَّا`, `إِيمَان`/`أَيْمَان`,
   `يَأْمُرُونَ`/`يَمُرُّونَ`, …).
3. **Pattern check** — `references/quranic-morphology-notes.md`. Confirm the surface's form
   so a verb gloss does not land on a noun and a participle is not read as a finite verb.
4. **Certify against an entry** — only now bind the surface to a Qamus entry, and only if
   the entry's root *and* sense match. Emit `{src:'qamus', kind:'authored', lang:'en'}` or emit
   nothing.

### The evidence ladder (root + sense)

Certify a root/sense from the **highest rung you can reach**, and record which rung you
used. Never certify from a lower rung when a higher one disagrees.

| Rung | Source | Use |
|---|---|---|
| 1 | **Qamus entry** (`qamus:vNNN/nNNN/pNNN`) — our own authored data | The lemma + sense we are matching against. Highest authority for *our* gloss. |
| 2 | **QAC root** (Quranic Arabic Corpus morphology) | Cross‑check the radicals for *this* token position. `informed_by`, never copied as gloss text. |
| 3 | **Photographed source** (the owner's physical root‑dictionary scan) | When seeding a new root, the page is the authority for root, headword, senses. |
| 4 | **External reference** (Quran.com, Tanzil, sunnah.com) | Internal evidence only — corroborate a reading. **Never** copy its gloss prose. |
| 5 | **Heuristic** (`tools/normalize_ar.py`, pattern matching) | Last resort, for recall/triage only. Never sufficient on its own to ship a gloss. |

> The single hardest‑won rule: `tools/normalize_ar.norm()` **drops the hamza and all
> harakāt**, so it can only *propose* a match — it can never *certify* a root or sense.
> `إِلَيْنَا` normalizes toward `لينا` but is **not** root `ل ي ن`; `إيمان` ≠ `أيمان`;
> `يَأْمُرُونَ` ≠ `يَمُرُّونَ`. Use `norm_strict()` / QAC to certify, `norm()` only to widen recall.

## How it feeds qamus‑highlight

`qamus-highlight` is the public hover layer: hover/tap a Qur'anic word → an English gloss
plaque. The **only** thing it may ever render is `{src:'qamus', kind:'authored', lang:'en'}` — our own
content. The ṣarf pack is the gate that decides whether a token *earns* a gloss:

- A token gets a gloss **iff** root detection + homograph check + pattern check all agree
  on a Qamus entry whose sense fits the āyah.
- Otherwise the token stays **plain** (no plaque). Coverage grows as entries grow; it never
  grows by lowering the bar.
- The public artifact carries no external gloss text and no provenance beyond
  `{src:'qamus', kind:'authored', lang:'en'}`. External references named in build scripts are
  `informed_by` labels for *our* internal audit only.

Hard precedence, learned in production: **prefer PENDING over a wrong gloss.** A verb gloss
must not land on a noun (`رَسُولًا` is not "to send"; `ٱبْن`/`بَنَات` is not "to build"). A
proper name is not a verb (`مُحَمَّد` is not "to praise"; `صَٰلِحًا` is not "the Prophet
Ṣāliḥ"). Same‑root polysemes need context (`ٱلْمُلْك` is not "angels"; `أَنْهَٰر` is not
"daytime"; `يَقْدِرُ` in a rizq context is "restricts", not "is able").

## How it feeds Nawawī‑40 candidate classification

Nawawī‑40 candidate tokens are triaged into **verb / noun / particle** before any gloss is
proposed (the same `v`/`n`/`p` classing used by the Qamus index builder). Ṣarf is the
classifier:

- **Pattern → class.** A Form I–X template, a maṣdar, an ism fāʿil/mafʿūl resolve the
  class; a short closed‑set token is a particle and goes through the homograph drill, not
  the verb pipeline.
- **Class gates the gloss vocabulary.** A token classed `n` may not receive a verb gloss
  ("to …"); a token classed `p` is glossed from the particle senses, distinguished by the
  harakah on its content letter.
- **Low confidence → PENDING.** An unresolved class is a candidate for human review, not a
  shipped gloss.

This keeps the corpus honest in both directions: scripture text is never altered, and a
token only ever shows the gloss its morphology actually licenses.

## Files in this pack

```
sarf/
  README.md                              ← you are here
  SKILL.md                               ← the playbook (authored separately)
  drills/
    root-detection.md                    ← find the root via the evidence ladder; worked examples
    homograph-regressions.md             ← the exact homographs we fought + the distinguishing feature
    verb-measures.md                     ← drills: read the form/voice/gloss-shape before glossing
    clitic-and-host-morphology.md         ← visible proclitics/suffixes must not vanish into host-only hovers
  references/
    quranic-morphology-notes.md          ← forms I–X, weak letters, hamza seats, tāʾ marbūṭa, …
    verb-measures-table.md               ← forms I–X paradigm table + qamus-relevance payoff
    weak-verbs.md                        ← hollow/defective/assimilated/hamzated/doubled/quadriliteral hazards
    masdar-participle-notes.md           ← the gloss-shape rule: maṣdar/participle ≠ finite verb
  rules/
    morphology-risk-rules.json           ← the risk_flags vocabulary for a sarf decision
    root-pattern-risk-rules.json         ← wazn/plural-shape traps (broken plural, مـ participle, …)
    pos-mismatch-rules.json  root-decision-rules.json  homograph-quarantines.json
    verb-measures.json                   ← machine-readable forms I–X paradigm
  examples/
    qamus-regressions.jsonl  root-form-decisions.jsonl
    verb-measure-examples.jsonl          ← per-form decisions (form/voice/gloss-shape)
```

> The verb-measure + weak-verb + plural-pattern material was distilled from the SN corpus ingest
> (AMAU decks + 1995 verb-charts; catalogued under `corpora/sarfnahw/`, licensing under review). The
> chart Arabic (a non-Unicode legacy font) was **not** extracted/copied — all Arabic patterns are
> standard morphology authored for this repo.

## Hard rules (non‑negotiable)

- **Qur'an text is never altered.** Ṣarf reads the surface; it does not normalize it for
  display.
- **PENDING beats wrong.** When the root, the pattern, or the sense is uncertain, emit no
  gloss.
- **`norm()` cannot certify.** It drops hamza + harakāt; it widens recall only. Certify
  with `norm_strict()`, the harakāt helpers, QAC, or the Qamus entry.
- **External references are `informed_by`, never copied.** The public hover shows only
  `{src:'qamus', kind:'authored', lang:'en'}`.
- **Use the shared module.** Normalization and harakāt logic live in
  `tools/normalize_ar.py` (`norm`, `norm_strict`, `bare`, `haraka_on`, `shadda_on`,
  `is_man_who`, `ends_tanwin_alef`). Reference it; do not re‑implement it.
