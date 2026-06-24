# Weak, hamzated, doubled & quadriliteral verbs — matching hazards

The irregular‑verb taxonomy below is the one the supplement charts cover (model verbs from the open‑source
**qutrub** roster; all Qurʾān‑relevant). The point here is **operational**: each class breaks naive
root/`norm()` matching in a specific way, and the sarf skill must know the hazard before it authors or resolves a
gloss.

| class | Arabic | radical pattern | model verb | hazard for matching |
|---|---|---|---|---|
| sound | الصحيح السالم | no weak letter, no hamza, no doubling | كَتَبَ / يَكْتُبُ | none — the easy case |
| hamzated | المهموز | a radical is ء (initial/medial/final) | أَخَذَ / يَأْخُذُ | hamza‑seat shifts (أ/إ/ؤ/ئ); `norm()` drops it — must use `norm_strict` |
| doubled (geminate) | المضاعف | C2 = C3 | رَدَّ / يَرُدُّ | idghām + shadda **hides the third radical**; رَدَّ looks bi‑consonantal |
| assimilated | المثال | C1 is و or ي | وَجَدَ / يَجِدُ | the C1 و **drops in the muḍāriʿ** (يَجِدُ, not *يَوجِدُ*) |
| hollow | الأجوف | C2 is و or ي | قَالَ / بَاعَ / نَامَ | medial weak letter **becomes a long alif** in the past; surfaces as a 2‑letter skeleton |
| defective | الناقص | C3 is و or ي | دَعَا / مَشَى / رَضِيَ | final weak letter shows as ا/ى/ي and **alternates**; the lemma's last radical is hidden |

## Concrete decision rules (encode these)

1. **Hollow verbs collapse to a long vowel.** قَالَ (root ق‑و‑ل) shows no و; بَاعَ (ب‑ي‑ع) shows no ي. When you
   see a CāC past or yaCūC/yaCīC/yaCāC present, suspect a hollow root and recover C2 from the muḍāriʿ
   (يَقُولُ → و, يَبِيعُ → ي, يَنَامُ → ا/و). Form IV/VIII/X of a hollow root drop the medial entirely
   (أَقَامَ < ق‑و‑م; اِسْتَعَانَ < ع‑و‑ن; اِسْتَطَاعَ < ط‑و‑ع). Never gloss أَقَامَ "established" as if from a sound root.
2. **Defective verbs hide C3.** دَعَا (د‑ع‑و) → يَدْعُو; مَشَى (م‑ش‑ي) → يَمْشِي; رَضِيَ (ر‑ض‑ي) → يَرْضَى. The
   final letter alternates ا/ى/و/ي across conjugation; do not treat ى/ي/ا as a stable last radical — recover it
   from the family. `bare()` keeps ى≠ي≠ا distinct, so do not certify a defective lemma on a `norm()` collapse.
3. **Assimilated verbs drop C1 و in the present.** وَجَدَ → يَجِدُ ("finds"); وَصَلَ → يَصِلُ. A present yaCiC with no
   visible و can still be a و‑initial root. Form VIII assimilates the و into ت: وقي → اِتَّقَى, وصل → اِتَّصَلَ.
4. **Doubled verbs wear a shadda.** رَدَّ (ر‑د‑د), مَدَّ (م‑د‑د), ضَلَّ (ض‑ل‑ل), أَحَبَّ (Form IV, ح‑ب‑ب). The shadda
   encodes the merged C2=C3; expand it before counting radicals so a triliteral is not mistaken for biliteral.
5. **Hamzated verbs need `norm_strict`.** أَخَذَ, سَأَلَ, قَرَأَ. The hamza seat (أ/إ/ؤ/ئ/ء) is meaning‑bearing and
   `norm()` discards it; any authored gloss/repair must pass `norm_strict` + QAC, never `norm()` alone. (See the
   sarf principle "never infer a root from `norm()` alone" and the regression `إيمان ≠ أيمان`.)
6. **Quadriliteral verbs are genuinely 4‑radical.** زَلْزَلَ (ز‑ل‑ز‑ل), وَسْوَسَ (و‑س‑و‑س). Do not force them into a
   triliteral root or read a reduplicated pair as a clitic.

## Hand‑off to qamus‑highlight

When a surface matches one of these hazard shapes and the root cannot be certified (Qamus entry → QAC →
triangulation), emit **pending** with the precise reason (`hollow_root_c2_hidden`, `defective_c3_alternation`,
`assimilated_c1_dropped`, `geminate_shadda`, `hamza_sensitive_homograph`, `quadriliteral`) rather than guessing —
this is exactly the discipline that prevented the `إِلَيْنَا ≠ ل ي ن` and `قُرْءَانًا ≠ stem+نا` regressions.

*Provenance:* verb‑class roster + model verbs observed in the supplement (qutrub‑sourced; catalogued under
`corpora/sarfnahw/`, licensing under review). Behaviour descriptions are standard morphology authored for this repo.
