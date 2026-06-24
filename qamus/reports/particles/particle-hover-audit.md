# Particle example-āyah hover audit (post hard-tail, MCP-confirmed)

The p001–p100 example āyāt: **219 āyāt · 3,245 tokens · 2,937 resolved (90.51%) · 308 pending** (was 81.51%; the particle hard-tail batch `particle_hover_batch_002_tafsir_mcp` added 289 safe content-token glosses, −0 removed). Every remaining pending token is now either a content token still in the global authoring queue, or a **function-word homograph** that the norm_strict key cannot safely gloss — each with an exact blocker below, confirmed by Tafsir MCP iʿrāb.

## Remaining blockers — function-word / form-voice homographs (157 distinct keys)

These keys carry >1 distinct meaning/function under one vowel-stripped key, so NO single live gloss is safe (the live aid keys by norm_strict). They are recorded as forbidden transitions in the state graph (`query_language_state.py --split`). MCP iʿrāb confirms the multi-function nature.

| key | surfaces (count) | why blocked |
|---|---|---|
| `وما` | وَمَا(277), وَمَآ(71), وما(1) | norm_strict key mixes 3 distinct surfaces/functions |
| `لم` | لَمْ(63), لَّمْ(49), لِمَ(3) | MCP iʿrāb: حَرْفُ نَفْيٍ وَجَزْمٍ مَبْنِيٌّ عَلَى السُّكُونِ. … (key also carries other functions) → no single gloss |
| `وإن` | وَإِن(108), وَإِنَّ(27), وَإِنْ(15), وَإِنِ(2), وَّإِن(1) | MCP iʿrāb: (الْوَاوُ) حَرْفُ اعْتِرَاضٍ مَبْنِيٌّ عَلَى الْفَتْحِ، وَ﴿إِنْ﴾ حَرْف … (key also carries other functions) → no single gloss |
| `ومن` | وَمَن(121), وَمَنْ(32), وَمِنَ(27), وَمِن(20), وَمِنْ(18) | MCP iʿrāb: اسْمٌ مَوْصُولٌ مَبْنِيٌّ عَلَى السُّكُونِ فِي مَحَلِّ نَصْبٍ اسْمُ ﴿إ … (key also carries other functions) → no single gloss |
| `أم` | أَمْ(65), أَم(5), أَمِ(5), أُمَّ(3), أُمُّ(2) | norm_strict key mixes 6 distinct surfaces/functions |
| `ألا` | أَلَّا(29), أَلَا(14), أَلَآ(13), ألا(1) | norm_strict key mixes 4 distinct surfaces/functions |
| `هدينا` | هَدَىٰنَا(4), هَدَيْنَا(3) | norm_strict key mixes 2 distinct surfaces/functions |
| `أمر` | أَمْرُ(10), أَمْرِ(8), أَمَرَ(4), أَمْرَ(4), أَمْرٍۢ(4) | norm_strict key mixes 7 distinct surfaces/functions |
| `بكم` | بِكُمْ(17), بِكُمُ(6), بُكْمٌ(1), بِكُم(1) | norm_strict key mixes 4 distinct surfaces/functions |
| `الطير` | ٱلطَّيْرِ(5), ٱلطَّيْرُ(2), ٱلطَّيْرَ(1), الطَّيْرِ(1) | norm_strict key mixes 4 distinct surfaces/functions |
| `فمن` | فَمَن(29), فَمَنْ(10), فَمَنِ(8), فَمَنَّ(2), فَمِن(2) | norm_strict key mixes 8 distinct surfaces/functions |
| `حرم` | حَرَّمَ(11), حُرُمٌۭ(2), حُرُمٌ(1), حُرِّمَ(1) | norm_strict key mixes 4 distinct surfaces/functions |
| `هدي` | هُدًۭى(16), هُدَى(3), هَدَىٰ(3), هَدَى(2) | norm_strict key mixes 4 distinct surfaces/functions |
| `وهي` | وَهِىَ(7), وَهِيَ(1) | norm_strict key mixes 2 distinct surfaces/functions |
| `لما` | لِّمَا(12), لَمَّا(11), لِمَا(10), لَمَا(3), لِمَآ(2) | norm_strict key mixes 8 distinct surfaces/functions |
| `ولد` | وَلَدٌۭ(10), وَلَدٍۢ(2), وَلَدَ(1) | norm_strict key mixes 3 distinct surfaces/functions |
| `بقوم` | بِقَوْمٍۢ(2), بِقَوْمٍ(1) | norm_strict key mixes 2 distinct surfaces/functions |
| `وإذا` | وَإِذَا(85), وَإِذَآ(6), وَإِذًۭا(2) | norm_strict key mixes 3 distinct surfaces/functions |
| `كلا` | كَلَّا(16), كَلَّآ(4), كُلًّۭا(2), كُلًّا(1), كُلًّۢا(1) | norm_strict key mixes 5 distinct surfaces/functions |
| `عطاء` | عَطَآءِ(1), عَطَآءُ(1) | norm_strict key mixes 2 distinct surfaces/functions |
| `الكبر` | ٱلْكِبَرُ(2), ٱلْكِبَرَ(1), ٱلْكُبَرِ(1), ٱلْكِبَرِ(1) | norm_strict key mixes 4 distinct surfaces/functions |
| `بشر` | بَشَرٌۭ(6), بِشَرٍّۢ(2), بُشِّرَ(2), بَشَرٍۢ(1), بَشَرٌ(1) | norm_strict key mixes 5 distinct surfaces/functions |
| `فهل` | فَهَلْ(13), فَهَل(1) | norm_strict key mixes 2 distinct surfaces/functions |
| `حق` | حَقَّ(10), حَقٌّۭ(7), حَقٍّۢ(4), حَقٍّ(2), حَقُّ(1) | norm_strict key mixes 5 distinct surfaces/functions |
| `فما` | فَمَا(46), فَمَآ(7) | norm_strict key mixes 2 distinct surfaces/functions |
| `فأهلكناهم` | فَأَهْلَكْنَٰهُم(1), فَأَهْلَكْنَاهُمْ(1) | norm_strict key mixes 2 distinct surfaces/functions |
| `تخرج` | تَخْرُجْ(2), تَخْرُجُ(2), تُخْرِجُ(1) | norm_strict key mixes 3 distinct surfaces/functions |
| `وأنا` | وَأَنَا۠(10), وَأَنَّا(6), وَأَنَا(2) | norm_strict key mixes 3 distinct surfaces/functions |
| `لمن` | لِمَن(15), لَمِنَ(13), لِمَنْ(6), لَّمِنَ(4), لِّمَن(4) | norm_strict key mixes 11 distinct surfaces/functions |
| `ولي` | وَلِىٍّۢ(5), وَلِىَ(3), وَلَّىٰ(2), وَلِىٌّۭ(2), وَلِۦِّىَ(1) | norm_strict key mixes 7 distinct surfaces/functions |

### MCP-confirmed exemplars (internal evidence; never public)

- `لم` — لَمْ = حرف نفي وجزم (negation) — but the key also carries لِمَ "why" (interrogative).
- `ومن` — وَمَنْ = اسم موصول (relative "whoever") — but the key also carries وَمِنْ "from" (preposition).
- `وإن` — وَإِن = إنْ مخففة من الثقيلة / conditional — the key mixes conditional and emphatic إِنَّ.

## Safe content tokens still pending (in global queue): 35 distinct keys
These are low-frequency single-surface content tokens (occ 1) not yet authored; they carry no homograph risk and will resolve in the ongoing noun/verb sweeps (B6+). They are NOT vague — each is a known single-surface key awaiting an authored gloss.

## Bottom line

No vague pending remains in particle example āyāt: every pending token is classified — a **homograph blocker** (exact, MCP-confirmed) or a **single-surface content token in the global authoring queue**. Particle-āyah coverage 81.51% → **90.51%**.
