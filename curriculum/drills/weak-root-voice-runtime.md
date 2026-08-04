# Drill — weak-root and voice family runtime practice (assimilated, defective, geminate, hamzated, doubly weak, passive voice, deputy agent)

**Goal:** given a weak-root verb cell or a passive-voice/deputy-agent frame, name the weak-rule (or the voice
melody, or the deputy-agent's case and position) FIRST, then produce the form. A visible surface form, a
memorized paradigm, or a familiar-looking Arabic word never certifies the reason behind it: a correct surface
with the WRONG weak-rule, voice, or deputy-agent reason is unsafe and is never treated as auto-correct. This
drill covers the seven L4.M1 lessons on weak roots and the voice/deputy-agent family:

| lesson | grammatical family | Knowledge Component |
|---|---|---|
| `L4.M1.01` | assimilated (mithāl) verbs — Form I imperfect first-radical deletion, scoped to Form I only | `kc-assimilated-verb-radical-scope` |
| `L4.M1.02` | defective (nāqiṣ) verbs — subtype vowel, jussive deletion, suffix-triggered shift | `kc-defective-verb-suffix-and-jussive-shift` |
| `L4.M1.03` | geminate (muḍaʿʿaf) verbs — merger/separation licensing, two securely licensed jussive shapes (not asserted exhaustive) | `kc-geminate-verb-merger-licensing` |
| `L4.M1.04` | hamzated (mahmūz) verbs — carrier selection, stored irregular cells | `kc-hamzated-verb-carrier-and-imperfect` |
| `L4.M1.05` | doubly weak (lafīf) verbs — subtype composition (maqrūn vs. mafrūq) | `kc-doubly-weak-verb-subtype-composition` |
| `L4.M1.06` | passive voice melody (bināʾ lil-majhūl) and promoted-argument case/agreement | `kc-passive-voice-melody-and-argument-promotion` |
| `L4.M1.07` | deputy agent (nāʾib al-fāʿil) function discrimination | `kc-deputy-agent-function-discrimination` |

> Procedure-first, like every drill. Sarf routes:
> [`../../sarf/procedures/weak-root.md`](../../sarf/procedures/weak-root.md),
> [`../../sarf/procedures/doubled-root.md`](../../sarf/procedures/doubled-root.md),
> [`../../sarf/procedures/hamza-root.md`](../../sarf/procedures/hamza-root.md),
> [`../../sarf/procedures/verb-form.md`](../../sarf/procedures/verb-form.md).
> Nahw route for case/agreement in the voice and deputy-agent lessons:
> [`../../nahw/procedures/irab-case-mood.md`](../../nahw/procedures/irab-case-mood.md).

**Rule of the drill:** classify the weak-root class (or the voice melody / deputy-agent status) BEFORE you
touch the form. Assimilated, defective, geminate, hamzated, and doubly-weak (lafīf) verbs are five DISTINCT
classes with five distinct rule sets — a rule that is true of one class is not automatically true of another,
and a lafīf verb composes the assimilated-verb rule (its mafrūq subtype) with the defective-verb rule (its
jussive and plural-past behaviour) rather than inventing a sixth rule set. Voice (active vs. passive) lives
entirely in the verb's own vowel melody, never in argument marking alone; the deputy agent is found from case
and position, never from a by-phrase translation, and a following prepositional phrase is a separate genitive
constituent, never the deputy agent itself. No radical, hamza carrier, suffix, subject marker, or weak
realization may be swallowed by a hover-style shortcut answer.

---

## Items (name the rule, then produce the form, before answering)

These items are graded objectively against
[`keys/weak-root-voice-runtime.keys.jsonl`](keys/weak-root-voice-runtime.keys.jsonl) and each names a Knowledge
Component in `curriculum/kc-catalog.json`. A miss routes back to this drill and is held pending
(`two_vote_required`); a learner-declared second check never clears it. Every item is fresh, constructed Arabic
paradigm practice — no item claims an exact Qurʾānic occurrence (`quran_example` is `null` throughout).

### `L4.M1.01` — assimilated (mithāl) verbs — 4 items

| item id | misconception targeted | task |
|---|---|---|
| `WRV-01-mithal-imperative-no-hamza` | building a long imperative with a prosthetic hamza | Give the imperative of وَعَدَ and justify whether it needs a prosthetic hamza. |
| `WRV-02-mithal-imperfect-deletion` | carrying the first-position weak consonant into the Form I imperfect | Give the Form I imperfect of وَصَلَ and state what happens to the first radical. |
| `WRV-03-mithal-derived-form-retains-radical` | extending deletion to the derived forms | Give the Form IV imperfect of و-ص-ل and state whether deletion applies. |
| `WRV-04-mithal-retained-radical-not-form-i` | reading a retained weak consonant after the prefix as if the verb were still Form I | Correct a learner who misreads يُوعِدُ's retained wāw as evidence of Form I. |

### `L4.M1.02` — defective (nāqiṣ) verbs — 4 items

| item id | misconception targeted | task |
|---|---|---|
| `WRV-05-naqis-subtype-vowel-lexical` | exchanging the two subtype vowels in the imperfect | Give the imperfects of دَعَا and رَمَى and state whether their subtype vowels are interchangeable. |
| `WRV-06-naqis-plural-past-radical-shift` | forming the masculine plural past without the final-radical shift | Give the masculine plural past of رَمَى and justify the final-radical shift (this item's rule is reused, not re-authored, for the lafīf plural past in `L4.M1.05`). |
| `WRV-07-naqis-jussive-deletion` | keeping the final weak consonant under a jussive operator | Give the jussive of يَرْمِي after لَمْ. |
| `WRV-08-naqis-suffixed-past-no-long-alif` | writing a suffixed past cell with the long alif of the bare past | Give the past of رَمَى with the first-person suffix تُ. |

### `L4.M1.03` — geminate (muḍaʿʿaf) verbs — 5 items

| item id | misconception targeted | task |
|---|---|---|
| `WRV-09-mudaaf-imperfect-vowel-stored` | assuming one imperfect middle vowel for the whole class | Give the imperfects of مَدَّ and فَرَّ and state whether their vowels are predictable from the class. |
| `WRV-10-mudaaf-gemination-mark-not-optional` | dropping the gemination mark in the imperfect | Give the imperfect of مَدَّ and state what the shadda represents. |
| `WRV-11-mudaaf-separation-before-suffix` | keeping the geminate before a consonant-initial suffix | Give the past of مَدَّ with the suffix تُ. |
| `WRV-12-mudaaf-merger-default-no-trigger` | separating the radicals in a cell that should merge | Give the masculine-plural indicative (hum) of مَدَّ and state whether the radicals may separate before the plural suffix's own vowel. |
| `WRV-13-mudaaf-jussive-licensed-shapes` | writing the indicative shape after a jussive operator | Correct a learner's ḍamma-marked "jussive" of مَدَّ. |

### `L4.M1.04` — hamzated (mahmūz) verbs — 5 items

| item id | misconception targeted | task |
|---|---|---|
| `WRV-14-mahmuz-carrier-active-vs-passive-past` | choosing the wrong carrier for the hamza | Give the active and passive past of سَأَلَ and justify the two different carriers. |
| `WRV-15-mahmuz-three-stored-imperatives` | keeping the hamza in the three stored imperatives | Give the imperative of أَخَذَ. |
| `WRV-16-mahmuz-raa-irregular-imperfect` | restoring a hamza into the imperfect of the irregular member | Give the imperfect of رَأَى. |
| `WRV-17-mahmuz-not-a-weak-root` | treating a hamza-bearing root as a weak root | Correct a learner who runs سَأَلَ through the hollow-verb contraction rule. |
| `WRV-18-mahmuz-carrier-recheck-after-suffix` | using the singular carrier in the plural cells of a final-hamza verb | Give the singular and plural imperfect of قَرَأَ and justify the carrier change. |

### `L4.M1.05` — doubly weak (lafīf) verbs — 4 items (plus the reused `L4.M1.02` plural-past item)

| item id | misconception targeted | task |
|---|---|---|
| `WRV-19-lafif-subtype-from-radical-position` | conflating the two subtypes' imperfect shapes | Name the subtype of وَفَى and طَوَى from radical position and give each imperfect. |
| `WRV-20-lafif-jussive-final-radical-deletion` | keeping the final weak radical under a jussive operator | Give the jussive of طَوَى after لَمْ. |
| `WRV-21-lafif-mafruq-imperfect-first-radical-deletion` | restoring the first weak radical into the imperfect of the separated subtype | Give the imperfect of وَفَى. |
| `WRV-22-lafif-indefinite-participle-tanwin` | writing the indefinite active participle with a visible final radical | Give the indefinite active participle of طَوَى. |

`L4.M1.02`'s `WRV-06-naqis-plural-past-radical-shift` covers the identical final-radical-shift rule for this
lesson's masculine plural past as well — the rule is one and the same for a plain defective verb and a lafīf
verb's plural past, so it is reused here rather than re-authored as a second item.

### `L4.M1.06` — passive voice melody and argument promotion — 5 items

| item id | misconception targeted | task |
|---|---|---|
| `WRV-23-passive-hollow-own-melody` | applying the ordinary melody to a medial-weak stem | Give the passive past of قَالَ and justify why the sound-stem melody does not transfer. |
| `WRV-24-passive-agreement-nonhuman-plural` | failing to agree the passive verb with the promoted argument | Give the passive of بَاعَ with a non-human plural promoted argument. |
| `WRV-25-passive-imperfect-prefix-vowel` | keeping the active prefix vowel in the imperfect passive | Give the imperfect passive of قَالَ. |
| `WRV-26-passive-melody-not-just-marking` | leaving the active vowel melody in place while treating the sentence as passive | Correct a learner who keeps قَالَ active while marking الحَقُّ as promoted. |
| `WRV-27-passive-promoted-argument-nominative` | leaving the promoted argument in the accusative | Give the passive of بَاعَ and state the case of the promoted argument. |

### `L4.M1.07` — deputy agent (nāʾib al-fāʿil) function discrimination — 4 items

| item id | misconception targeted | task |
|---|---|---|
| `WRV-28-naib-pp-vs-deputy-agent` | confusing a following prepositional phrase with the deputy agent | Name the deputy agent of a passive sentence with a following instrumental PP. |
| `WRV-29-naib-agreement-nonhuman-plural` | failing to agree the passive verb with its deputy agent | Give the passive with a non-human plural deputy agent and justify the agreement. |
| `WRV-30-naib-promoted-element-nominative` | leaving the promoted element in the accusative | Give the passive of كَسَرَ and state the case of the promoted element. |
| `WRV-31-naib-melody-must-be-passive` | using an active verb melody with a nominative patient | Correct a learner who keeps كَسَرَ active while marking البَابُ as nominative. |

---

## Canonical-unit inputs consulted (candidate/instructional inputs, not edited by this drill)

`u-s01`, `u-s02`, `u-s06`, `u-s07`, `u-s09`, `u-n01`, `u-n03`, `u-n08`, `u-n09`, `u-n10`,
`cu-geminate-jussive-variants`, `cu-hamza-carrier-licensing`, `cu-weak-rule-composition`,
`cu-voice-melody-templates`, `cu-agent-vs-deputy-discrimination`.
