# Particle-lane authored hover batch (PP1 — APPLIED LIVE)

The PP1 proving-pilot's production output: original qamus-style hover glosses for the highest-frequency pending
**content tokens in the p001–p100 example āyāt**, authored from understanding and certified through the same
four-gate pipeline proven in P13.

## Pipeline
30 authorable candidates (content words in particle āyāt; function-word tops like وَمَآ/لَمْ/أَمْ correctly left
pending as homograph/multi-function) → **empirical norm_strict key-collision probe** → **author + key-aware
2-vote** (shown the real same-key surface set) → **26 certified, 4 rejected**.

Rejected (the gate working — true homographs under the live key):
- هَدَيْنَا — key `هدينا` mixes هَدَىٰنَا "He guided us" (3sg+obj) vs هَدَيْنَا "We guided" (1pl subj) — different person.
- حَرَّمَ — key `حرم` mixes the verb حَرَّمَ "forbade" with the noun/adj حُرُم "sacred/inviolable".
- وَلَدٌ — key `ولد` mixes the noun "child" with the verb وَلَدَ "begot".
- (+1 more) — terminally classified pending.

## The 26 applied (key-safe, same-lemma, 2/2 certified)
ٱلصِّيَامِ "the fasting" · لِبَاسٌ "garment" · ٱلْمُؤْمِنُونَ "the believers" · ٱلرُّسُلِ "the messengers" · ٱلطَّيْرُ
"the birds" · مَثَلًا "a parable" · خَٰلِدُونَ "abiding forever" · يُنفِقُونَ "they spend" · يَتَّقُونَ "they are
mindful (of God)" · بِإِذْنِهِۦ "by His permission" · هَدَىٰكُمْ "He guided you" · أُحِلَّ "was made lawful" ·
ٱدْعُوا۟ "call upon / invoke" · وَقُل "and say" · وَٱبْتَغُوا۟ "and seek" · تَقْرَبُوهَا "approach it (prohibition)" ·
بَٰشِرُوهُنَّ "have relations with them" · وَعَفَا "and he pardoned" · يُحَاسِبْكُم "He will call you to account" ·
زِينَتَهُنَّ "their adornment" · إِخْوَٰنِهِنَّ "their brothers" · أَبْصَٰرِهِمْ "their eyes/sight" · عِلْمُهَا "its
knowledge" · طَيِّبَةً "good/wholesome" · وَكَثِيرٌ "a great many" · لَبِثْتَ "you stayed".

## Live result (one rebuild — also captured the كَظِيم entry repair)
- coverage **70.47% → 70.76%** · matched **35,166 → 35,307** (+141 / ~3 changed / −0 removed) · source_sha `65797d7d`.
- the 3 "changed" = the كَظِيم entry-repair gloss propagated to its 3 tokens (3:134, 16:58, 68:48): the verb
  "to suppress…" → the adjectival "(one) suppressing his grief…".
- `validate` PASS; health 200; screenshot of the repaired كَظِيم entry viewed.
- **Rollback:** `fusha-hover-decisions.tsv.bak-pp1` + `wbw-lookup.prev.json` (hover); كَظِيم entry `versions[]` v2 +
  `backups/qamus-20260624-084704.tar.gz` (entry).

Public records ship exactly `{src:"qamus",kind:"authored"}`; internal provenance `informed_by:[qac,quran-text]`.
Mirror: `qamus/candidates/qamus_2092/particle_hover_batch_001.{jsonl,provenance.jsonl}`.
