# Drill — nawāsikh governor families (kāna/laysa, continuative, inna, qalb-verbs, stacked scope)

**Goal:** given a nominal-predication or cognition-verb frame, name the governing family FIRST, then justify
the case pattern it imposes. This drill covers five coherent nawāsikh families: **kāna and her sisters**
(including the defective negator **laysa**), **polarity-licensed continuative kāna-sisters** (`مَا زَالَ`-type),
**inna and her sisters**, **qalb-verbs** (verbs of the heart, complement count by sense), and **stacked
abrogators** (more than one governor in one span). A right case ending named without its governor — or with
the WRONG family's governor — is unsafe and is never treated as auto-correct.

> Procedure-first, like every drill. Routes to the nahw single source of truth:
> [`../../nahw/procedures/nawasikh-government.md`](../../nahw/procedures/nawasikh-government.md), which documents
> the regime table, the abstention vocabulary (`marking_unknown`, `sense_dependent_gate`, `licenser_absent`,
> `bracketing_ambiguous`, `regime_undetermined`), and the discrimination-before-expectation invariant. For the
> general case/mood contract also see
> [`../../nahw/procedures/irab-case-mood.md`](../../nahw/procedures/irab-case-mood.md).

**Rule of the drill:** classify the FAMILY before you touch a case ending. Kāna's family and inna's family are
exact mirror images (kāna: ism nominative / khabar accusative; inna: ism accusative / khabar nominative) —
swapping them produces a fully well-formed-looking sentence with both exponents wrong. A qalb-verb's complement
count depends on its SENSE (judgemental vs. literal-perception), never on the lemma alone. Two governors stacked
in one span each keep their own separate scope.

---

## The five families in this drill

| family | signature | closed-class members drilled here |
|---|---|---|
| **kāna & laysa government** | ism nominative, khabar accusative | كان، ليس، أصبح، بات |
| **continuative licensing** | khabar accusative, but ONLY with its licensing negator | ما زال، ما دام |
| **inna-family government** | ism accusative, khabar nominative (mirror of kāna) | إنّ، أنّ، كأنّ، لَٰكِنَّ (heavy) / لَٰكِنْ (light), ليت |
| **qalb-verb transitivity** | one object (literal sense) vs. two accusative objects (judgemental sense) | ظنّ، حسِب، رأى، وجد |
| **stacked-governor scope** | each governor governs only its own pair | إنّ ... كان ... |

A sixth candidate area from the same batch — the MODAL FORCE each inna-sister carries (كأنّ = figurative
resemblance, ليت = an unlikely/unattainable wish, لعلّ = an attainable hope) — is drilled here (items 16–17) as
an ordinary reasoning item, but it carries **no bound Knowledge Component**: it is a gloss-facing distinction,
not a case/government fact the checker emits a diagnostic for, so no drill-key row here claims a KC binding for
it. Detecting the RIGHT particle for the intended stance is still worth practicing; it is just not (yet) a
machine-checkable governor claim.

---

## Items (name the family, then the case pattern, before answering)

These items are graded objectively against
[`keys/nawasikh-governor-families.keys.jsonl`](keys/nawasikh-governor-families.keys.jsonl) and each names a
Knowledge Component in `curriculum/kc-catalog.json` (items 16–17 are the modal-force exception noted above —
instructional only, no bound KC). A miss routes back to this drill and is held pending (`two_vote_required`); a
learner-declared second check never clears it. The task column poses the question; it does not give the answer.

### 1–6, 24. Kāna & laysa government

| item id | stimulus | task |
|---|---|---|
| `NGF-01` | لَيْسَ conjugated like an ordinary verb as `يَلِيسُ` | Explain why this imperfective form is impossible and state what لَيْسَ actually inflects for. |
| `NGF-02` | `كَانَ الطَّالِبُ مُجْتَهِدٌ` (خبر left nominative) | Name the governor, the error, and the corrected sentence. |
| `NGF-03` | `أَصْبَحَ الجَوُّ بَارِدًا` (ism marked accusative instead) | Explain which slot actually takes the accusative and why the learner's marking produces the WRONG family's pattern. |
| `NGF-04` | `لَيْسَ يَكْتُبُ الطَّالِبُ` (لَيْسَ stacked before a finite verb) | Explain why this is wrong and give the correct way to negate a verbal sentence. |
| `NGF-05` | `لَيْسَ الطَّالِبُ كَتَبَ الدَّرْسَ` (لَيْسَ used for past-time negation) | Explain why لَيْسَ cannot carry this meaning and state the correct construction. |
| `NGF-06` | `بَاتَ الطِّفْلُ نَائِمًا`, with بَاتَ glossed as the noun بَيْت | Explain the category error and identify بَاتَ correctly. |
| `NGF-24` | `كَانَ الجَوُّ حَارًّا`, with كَانَ's ism/khabar signature swapped for inna-family's | Explain the swap and give the corrected sentence. |

### 7–9. Continuative licensing

| item id | stimulus | task |
|---|---|---|
| `NGF-07` | `مَا زَالَ الطَّقْسُ مُعْتَدِلٌ` (خبر left nominative) | Explain why the two-token continuative governor governs exactly like a single-token kāna-sister, and give the corrected sentence. |
| `NGF-08` | `زَالَ المَطَرُ نَازِلًا` (licensing مَا dropped) | Explain the reversal and give the corrected sentence. |
| `NGF-09` | `مَا دَامَ المَطَرُ نَازِلًا` read as an ordinary negated sentence | Explain the correct reading and what is missing. |

### 10–15. Inna-family government

| item id | stimulus | task |
|---|---|---|
| `NGF-10` | `عَلِمْتُ إِنَّ الخَبَرَ صَحِيحٌ` (إِنَّ used where a subordinator is required) | Explain the selection rule and give the corrected sentence. |
| `NGF-11` | `إِنَّ السَّمَاءُ صَافِيَةٌ` (ism left nominative) | Name the governor, the error, and the corrected sentence. |
| `NGF-12` | `إِنَّ السَّمَاءَ صَافِيَةً` (khabar marked accusative) | Explain the error and the corrected sentence. |
| `NGF-13` | `جَاءَ زَيْدٌ لَٰكِنَّ ذَهَبَ عَمْرٌو` (geminate لَٰكِنَّ before a finite verb) | Explain why this fails and give the corrected sentence. |
| `NGF-14` | `كَأَنَّ القَمَرُ مِصْبَاحٌ` (ism left nominative) | Explain the error using the same family signature as إِنَّ and give the corrected sentence. |
| `NGF-15` | `لَيْتَ الشَّبَابَ عَائِدًا` (khabar marked accusative) | Explain the error and the corrected sentence. |

### 16–17. Inna-sister modal force (no bound KC — instructional only)

| item id | stimulus | task |
|---|---|---|
| `NGF-16` | `كَأَنَّ هَـذَا الكِتَابَ أَكْبَرُ مِنْ ذَٰلِكَ` (neutral size comparison) | Explain why كَأَنَّ is the wrong choice here. |
| `NGF-17` | `لَيْتَ الطَّبيبَ يَصِلُ قَريبًا` (an outcome that is actually likely) | Explain why لَيْتَ misrepresents this and name the correct member. |

### 18–22, 25. Qalb-verb transitivity (complement count by sense)

| item id | stimulus | task |
|---|---|---|
| `NGF-18` | `ظَنَنْتُ الجَوَّ بَارِدٌ` (inna-family's split assignment applied to ظَنَّ) | Explain the error and the corrected sentence. |
| `NGF-19` | `رَأَيْتُ الهِلَالَ طَالِعًا`, with طَالِعًا insisted to be a forced second object | Explain the sense-dependent gate and the correct role of طَالِعًا. |
| `NGF-20` | `حَسِبْتُ الأَمْرَ سَهْلٌ` (only the first complement of حَسِبَ marked accusative) | Explain the defining property of this family and give the corrected sentence. |
| `NGF-21` | ظَنَّ used interchangeably with عَلِمَ to claim certain knowledge | Explain the epistemic-stance distinction. |
| `NGF-22` | `وَجَدْتُ المِفْتَاحَ تَحْتَ الطَّاوِلَةِ حَاضِرًا` (an unneeded second accusative added) | Explain why the sense must be settled before counting complements. |
| `NGF-25` | `حَسِبَ الطَّالِبُ الدَّرْسَ سَهْلًا`, with الطَّالِبُ marked as a third accusative complement | Explain why the agent is not part of the absorbed predication. |

### 23. Stacked-governor scope

| item id | stimulus | task |
|---|---|---|
| `NGF-23` | `إِنَّ الطَّالِبَ كَانَ مُجْتَهِدًا`, with inna's signature applied across the whole span | Explain why each governor keeps its own separate scope. |

---

## Checklist before you leave this drill

- [ ] Do I name the governing FAMILY (kāna, continuative, inna, qalb-verb, stacked) before touching any case
      ending?
- [ ] For a kāna/inna-family construction, do I check ism vs. khabar and confirm I have not swapped the two
      mirror-image signatures?
- [ ] For a continuative kāna-sister, do I check for its required licensing negator before reading the
      continuative sense?
- [ ] For a qalb-verb, do I settle the SENSE (literal vs. judgemental) before counting complements, and keep
      the agent separate from the complements?
- [ ] When more than one governor is present in a span, do I resolve each one's scope separately instead of
      applying one family's signature across the whole thing?
- [ ] When the evidence for a case, a sense, or a licenser is genuinely missing, do I abstain instead of
      forcing a reading the evidence cannot license?

Next rung: put these families over real scripture, token by token, once a source-addressed occurrence is
reviewed — this drill's items are authored practice, never a Qurʾānic occurrence claim
(`quran_example: null` throughout). **Family first, then case.**
