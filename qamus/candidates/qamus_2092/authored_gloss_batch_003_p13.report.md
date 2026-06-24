# Authored-gloss batch 003 — P13 reference-assisted hover batch (APPLIED LIVE)

The main P13 production batch: original qamus-style hover glosses for the highest-frequency pending Qurʾānic
content words, authored from understanding (root + dominant sense), applied via the established
`fusha-hover-decisions.tsv` → `rebuild.sh` path. External references (QAC root/POS, Quran.com/Tanzil for
ref-verification) informed the authoring internally; **nothing external ships** — public records are exactly
`{src:"qamus",kind:"authored",lang:"en"}`.

## Pipeline (four gates)

44 top pending content-word surfaces (from `hover-token-completion.json`) →
1. **Author + 2-vote** (each surface authored, then 2 independent skeptics refute-test): 3 certified, 41 flagged.
2. **Empirical key-collision probe** against the live corpus: revealed the first 2-vote pass reasoned about the
   *bare root* (e.g. ktb) but the live key is `norm_strict` which **keeps `ال` + case endings**, so most "MULTI"
   keys are case/orthographic variants of ONE word (ٱلْكِتَٰبِ/ٱلْكِتَٰبَ/ٱلْكِتَٰبُ = "the Book"), genuinely
   key-safe — while a real subset are true homographs.
3. **Key-aware re-verify** (2-vote, shown the actual same-key surface set): **23 certified, 6 correctly rejected**
   — أَعْلَمُ ("knows best" elative ↔ "I know" verb), سَوَآءٌ ("equal" ↔ "midst"), أَكْثَرَ (verb ↔ elative),
   ٱلْحَقِّ / عَزِيز (divine-Name / ʿAzīz-of-Egypt referent), سُوٓء.
4. **Apply** the 23 key-safe + 2/2-certified glosses live.

## Live result (rebuild verified)

- coverage **69.08% → 70.47%** · matched **34,472 → 35,166** · diff **+694 added / ~51 improved / −0 removed**.
- the ~51 "changed" are verbose spread-glosses replaced by the concise certified ones — e.g. ٱلرَّحْمَٰنَ at the
  basmala positions: "to show mercy and compassion to" → **"the Most Gracious (ar-Rahman)"** (an improvement).
- `validate` PASS (schema + licensing); health 200; light+dark screenshots viewed (page intact).
- **Rollback:** `fusha-hover-decisions.tsv.bak-p13` + `wbw-lookup.prev.json` + flag-off.

## The 23 applied (key-safe, dominant-sense, case-variant verified)

ٱلْكِتَٰبَ "the Book" · ٱلْءَاخِرَةِ "the Hereafter" · يُؤْمِنُونَ "they believe" · بِٱلْحَقِّ "with the truth" ·
ٱلصَّٰلِحَٰتِ "the righteous deeds" · رَّحِيمٌ "Most Merciful" · جَمِيعًۭا "all together" · أَنفُسَهُم "themselves" ·
أَحَدَ "anyone/one" · نَفْسَهُۥ "himself" · ٱلْقُرْءَانِ "the Qur'an" · شَدِيدُ "severe" · ءَايَةًۭ "a sign" ·
أَوْلِيَآءُ "allies/protectors" · ٱلْحَرَامِ "the Sacred" · جَزَآءُ "recompense" · ٱبْنِ "son" · ٱلرَّحْمَٰنَ
"the Most Gracious" · ٱلْعِلْمِ "the knowledge" · عَدُوٌّۭ "an enemy" · بَيْنَ "between" · أَشَدَّ "stronger" ·
مُؤْمِنَيْنِ "believers".

## Terminally classified (NOT applied — pending with evidence)

The ~21 not applied stay pending for precise reasons (the gate working): **true homographs** under the live key
(أُمّ↔أَمْ "or", رَبِّ vocative↔رَبُّ construct, ٱلْمُلْكُ↔ٱلْمَلِك "King", هُدَى noun↔هَدَى verb, وَعَدَ verb↔وَعْد
noun, كُذِبُوا۟↔كَذَّبُوا "denied", ٱلْهُدَى↔هَدْي offering, يَدْعُونَ active↔passive, أَمْرُ noun↔أَمَرَ verb,
حَقٌّ noun↔حَقَّ verb, كِتَٰبَ indefinite multi-sense, أُمَّة↔"his mother"), **referent landmines** (صَٰلِحًا ↔
Prophet Ṣāliḥ; ٱلْحَقّ / ٱلْعَزِيز divine-Name vs common), and **polysemy** (سَوَآء, أَعْلَمُ, أَكْثَرَ). These
require phrase-aware/two-vote resolution, not a surface key — recorded in `sarfnahw_review_queue` lineage.
