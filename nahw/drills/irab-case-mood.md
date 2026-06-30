# Drills — iʿrāb case & mood

Recognition + production. Built from [`../evals/irab-polysemy-eval.jsonl`](../evals/irab-polysemy-eval.jsonl)
+ [`../references/irab-teaching-map.md`](../references/irab-teaching-map.md).

## 1. Noun cases (rafʿ / naṣb / jarr)
- ٱللَّهُ (mubtadaʾ) → rafʿ ḍamma. | ٱللَّهَ (mafʿūl/ism inna) → naṣb fatḥa. | ٱللَّهِ (after prep / muḍāf ilayh) → jarr kasra.
- Diptote: بِأَحْمَدَ → jarr sign is **fatḥa** (mamnūʿ min al-ṣarf), not kasra.

## 2. Verb moods (rafʿ / naṣb / jazm)
- يَكْتُبُ (unmarked) → rafʿ. | لَن يَكْتُبَ / أَن يَكْتُبَ → naṣb fatḥa. | لَمْ يَكْتُبْ / لَا تَكْتُبْ → jazm sukūn (لَمْ→past).

## 3. The flippers
- كَانَ زَيْدٌ قَائِمًا → kāna: ism **rafʿ**, khabar **naṣb**.
- إِنَّ زَيْدًا قَائِمٌ → inna: ism **naṣb**, khabar **rafʿ**.
- ظَنَنْتُ زَيْدًا قَائِمًا → ẓanna: **two** manṣūb objects.
- لَا رَجُلَ فِي ٱلدَّارِ → lā of genus: ism **mabnī** on fatḥ.
- تَكَادُ تَمَيَّزُ → kāda: ism kāda is hidden; khabar kāda is an imperfect verb in **rafʿ** unless
  another governor changes it.

## 4. The accusatives learners confuse
- طَابَ زَيْدٌ نَفْسًا → نفسًا = **tamyīz** (jāmid, fāʿil-convertible), not ḥāl.
- جَآءَ زَيْدٌ رَاكِبًا → راكبًا = **ḥāl** (mushtaqq, state).
- مَا جَآءَ إِلَّا زَيْدٌ → mufarragh istithnāʾ: زيد = **fāʿil marfūʿ** (إلا cancelled).
- تِسْعَةَ عَشَرَ → murakkab number: both numeric pieces are manṣūb; do not gloss either as a
  standalone dictionary noun.
- سَبْعُونَ ذِرَاعًا → ذراعًا = **tamyīz manṣūb**, specifying the measure.

## 5. Context-decided sense (iʿrāb over lexicon)
- يَبْسُطُ ٱلرِّزْقَ … وَيَقْدِرُ → يقدر = "**restricts**" (contrast), not just "is able".
- إِنَّ إِبْرَٰهِيمَ لَحَلِيمٌ → حليم = "**forbearing**" (human referent), not the divine Name.
- مَا بِصَاحِبِهِم مِّن جِنَّةٍ → جِنّة = "**madness**", not "garden".
- كَانَ أُمَّةً → أمّة = "**a model of excellence**", not just "community".

## 6. Governor justification — the VALUE is not enough (value vs reason)

A case **value** (rafʿ/naṣb/jarr) is unsafe on its own: it must be paired with the **governing element (ʿāmil) that licenses it**.
The case is a **consequence of the governor**, never read backwards. Naming the right ending with the wrong or absent governor is
`governor_not_justified` — **right answer, wrong reason** — and routes to scholar / two-vote review, **never `auto_safe`**. The engine
that enforces this is [`tools/fusha_governor.py`](../../tools/fusha_governor.py) (`build_dependency_lattice`); the oracle is
[`../evals/irab-right-answer-wrong-reason.jsonl`](../evals/irab-right-answer-wrong-reason.jsonl).

Pair every value with its **reason**:

| token | value | reason (the ʿāmil that licenses it) |
|---|---|---|
| ٱللَّهُ (in a nominal sentence) | rafʿ | **mubtadaʾ** — topic position (no preceding governor) |
| يَكْتُبُ | rafʿ | **no jāzim/nāṣib present** — the default mood, not a positive cause |
| ٱللَّهَ | naṣb | **mafʿūl bih** of a verb **OR** ism inna — *name which*; the two are different reasons |
| ٱللَّهِ | jarr | **after a preposition** OR **muḍāf ilayh** — *name which* |

### The "right answer, wrong reason" trap (do not fall in)
- `بِزَيْدٍ` — the kasra is **jarr by the preposition بِ**. Claiming "jarr because it is the muḍāf ilayh" is the **right value, wrong
  governor** → `governor_not_justified`. The value happens to be right; the reasoning is unsafe.
- A preposition **only ever governs the genitive.** A claim that a preposition "assigns accusative" is a contradiction →
  `governor_not_justified` (matches eval `RWR-002`). Route to review; never ship it as a resolved hover.
- If the governor is genuinely **undeterminable** from the available evidence, the row stays **pending** — do **not** assert a case
  with no governor.

**Two independent checks** (conclusion **and** reason) are required for any iʿrāb/case-mood decision (the GrammarProblems gate); a
single confident value is not evidence.
