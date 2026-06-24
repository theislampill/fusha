# Verbs proofing matrix (V1 sweep)

> **2026-06-24 (live 81.91%):** verb section example coverage **81.9%** (54/947 entries fully hover-complete; 888 with >=1 pending). Content batch_001 applied 7 verb glosses (وَعَدَ "promised" etc.); all homograph candidates (يَدْعُونَ call/shove, يَحِلُّونَ lawful/adorn) correctly 2-vote-rejected -> pending with exact blocker. Canonical totals in `hover-token-audit-full.jsonl`.

Per-entry audit for the 970 verbs entries (Fusha index class `v`). Hover coverage of each entry's example āyāt + a terminal status. **0 unknown.** Generator: `qamus/scripts/build_nv_matrices.py`.

| metric | value |
|---|---:|
| verbs entries | 970 |
| tokens in their āyāt | 103788 |
| resolved | 83684 |
| coverage % | 80.63 |
| hover-complete (āyāt fully glossed) | 52 |

## Status

| terminal state | n |
|---|---:|
| `needs_hover_authoring` | 903 |
| `needs_source_photo_review` | 52 |
| `needs_quran_ref_verification` | 10 |
| `deferred_missing_source` | 5 |

## Top 40 to finish next (most pending hover tokens)

| entry | root | headword | refs | tokens | resolved | pending | status |
|---|---|---|---:|---:|---:|---:|---|
| `141cbc3bd2bd` | و ل ي | أَوْلَى / مَوْلَى / تَوَلَّوْا / وَلَّى / تَوَلَّى / تَوَلَّاهُ | 50 | 1009 | 809 | 200 | needs_hover_authoring |
| `fbd04177b8dd` | ك ب ر | كَبِير / تَكَبَّرَ / اِسْتَكْبَرَ | 39 | 711 | 555 | 156 | needs_hover_authoring |
| `c59a0161fac8` | أ م ن | آمَنَ | 41 | 699 | 559 | 140 | needs_hover_authoring |
| `049756ecbbf9` | ح ق ق | حَقَّ | 30 | 562 | 436 | 126 | needs_quran_ref_verification |
| `259fe620e117` | خ ل ف | خَلَفَ / خَلْف / خِلَاف / اِخْتَلَفَ | 30 | 735 | 610 | 125 | needs_hover_authoring |
| `1d1155c1ea36` | ق د ر | قَدَرَ / قَدَّرَ | 30 | 569 | 448 | 121 | needs_hover_authoring |
| `4f666d15bb7e` | ح ر م | حَرَّمَ / حُرُمَات / مَحْرُوم | 20 | 520 | 406 | 114 | needs_hover_authoring |
| `89f4baadb89a` | ح ي ي | حَيِيَ / أَحْيَا / حَيَّاكَ | 24 | 551 | 438 | 113 | needs_hover_authoring |
| `543da5bcc248` | أ خ ر | أَخَّرَ / يَسْتَأْخِرُونَ / آخَر / آخِر | 27 | 525 | 416 | 109 | needs_hover_authoring |
| `088ebd5e2393` | س ل م | سَلِمَ / أَسْلَمَ / سَلَّمَ | 27 | 498 | 390 | 108 | needs_hover_authoring |
| `d5ac66156b8e` | أ م ر | أَمَرَ / يَأْتَمِرُونَ / أَمْر / إِمْرًا | 30 | 496 | 389 | 107 | needs_hover_authoring |
| `1a9f6df3889e` | م ت ع | يَتَمَتَّعُ / مَتَاعَهُمْ / مَتَاع / تَمَتُّع | 17 | 439 | 333 | 106 | needs_hover_authoring |
| `ecfc082ac2c5` | أ خ ذ | أَخَذَ / اِتَّخَذَ / يُؤَاخِذُ | 25 | 511 | 406 | 105 | needs_hover_authoring |
| `f92aeb1d59ae` | ح ل ل | حَلَال / ٱحْلُل / يَحِلُّ | 17 | 501 | 397 | 104 | needs_hover_authoring |
| `da61fd38733f` | ح ك م | حَكَمَ / يُحْكِمُ / حِكْمَة | 25 | 469 | 369 | 100 | needs_hover_authoring |
| `16dc0a87056e` | ش ه د | شَهِدَ / أَشْهَدَهُمْ / شُهَدَاء | 19 | 421 | 322 | 99 | needs_hover_authoring |
| `55dd18892bf9` | و ق ي | وَقَاهُ / اِتَّقَى | 23 | 473 | 375 | 98 | needs_hover_authoring |
| `97657fc0cb1c` | ح م ل | حَمَلَ / تَحْمِل | 17 | 378 | 280 | 98 | needs_hover_authoring |
| `f926e5fd94bb` | ن ع م | أَنْعَمَ / أَنْعَام / نِعْمَ / نَعَم | 17 | 332 | 238 | 94 | needs_hover_authoring |
| `2e2fa868686a` | ل ق ي | أَلْقَى / لَقِيَ / تَلَقَّى / تِلْقَاء | 32 | 429 | 338 | 91 | needs_hover_authoring |
| `51e9879b93ab` | ر د د | ٱرْتَدَّ / رَدَّ | 16 | 343 | 252 | 91 | needs_hover_authoring |
| `21d0c74b634d` | ك ت ب | كَتَبَ | 17 | 428 | 339 | 89 | needs_hover_authoring |
| `4cb26045b5b7` | ظ ه ر | ظَهَرَ / يُظْهِر / ظَهِيرَة / ظَهْر / ظِهَار | 23 | 503 | 414 | 89 | needs_hover_authoring |
| `5d89e690256d` | ت ب ع | اِتَّبَعَ / تُبَّع | 15 | 403 | 315 | 88 | needs_hover_authoring |
| `044c699bb45b` | ق ض ي | قَضَى | 19 | 386 | 299 | 87 | needs_hover_authoring |
| `0f79975eb71d` | ح س ن | حَسُنَ | 30 | 512 | 425 | 87 | needs_hover_authoring |
| `7947580aed3e` | ق ب ل | يَقْبَل | 22 | 373 | 286 | 87 | needs_hover_authoring |
| `f3726bc9f962` | م ث ل | تَمَثَّلَ / مِثْل / مَثَل | 24 | 412 | 325 | 87 | needs_hover_authoring |
| `9e4222baccd2` | ع د و | يَعْدُ / ٱعْتَدَى / عَادَيْتُمْ / عُدْوَة / عَادِيَات | 18 | 382 | 296 | 86 | needs_hover_authoring |
| `beae77dd607f` | ط ع م | طَعِمَ / يَطْعَمْهُ | 10 | 324 | 239 | 85 | needs_hover_authoring |
| `e0e500c4b7a5` | م ل ك | مَلَكَتْ / مَالِك / مَلَائِكَة | 18 | 361 | 277 | 84 | needs_hover_authoring |
| `191e9b80dfcd` | ب ل غ | بَلَغَ / أَبْلَغَ | 15 | 316 | 233 | 83 | needs_hover_authoring |
| `4f99a11c3127` | ض ر ر | يَضُرُّ / ٱضْطَرَّهُ | 11 | 389 | 306 | 83 | needs_hover_authoring |
| `1fd424ee1e74` | ر أ ى | رَأَى | 17 | 382 | 300 | 82 | needs_hover_authoring |
| `3041d6f44a27` | ق و م | قَامَ | 33 | 484 | 402 | 82 | needs_hover_authoring |
| `8f8d49c8fd17` | ع ل م | عَلِمَ | 28 | 447 | 365 | 82 | needs_hover_authoring |
| `d2eddd3dbdad` | ب ي ت | يُبَيِّتُون / بَيَّتَ / بَيْت / ٱلْبَيْت | 18 | 382 | 300 | 82 | needs_hover_authoring |
| `1015809f59b7` | ص د ق | صَدَقَ / صِدِّيق / صَدَّقَ / صَدِيق / تَصَدَّقَ | 22 | 347 | 266 | 81 | needs_hover_authoring |
| `cc013b361d1c` | ح ض ر | حَضَرَ | 13 | 380 | 299 | 81 | needs_hover_authoring |
| `dcf75e7f4b79` | م و ت | مَاتَ / مَيْت | 21 | 338 | 258 | 80 | needs_hover_authoring |
