# Coverage-yield ledger — path to 90% (Phase B)

Computed from the live artifact (read-only). **Do not chase one-off tokens** — this ranks the path by safe resolved-token yield.

| metric | value |
|---|---:|
| total pending tokens | 8,624 |
| distinct pending surfaces | 5,189 |
| **+resolves needed for 90%** | **3,634** |
| safe collision-free content surfaces | 741 |
| **cumulative SAFE surface-family yield (ceiling)** | **1,772** |
| function-word polysemy pending | 405 |
| content-homograph (collision) pending | 1868 (top-400 sample) |

## Lanes ranked by safe yield (top-400 surfaces)

| lane | families | pending tokens | gate |
|---|---:|---:|---|
| content_homograph (per-loc iʿrāb) | 278 | 1868 | per-loc iʿrāb 2-vote |
| function_word_polysemy | 5 | 405 | per-loc nahw 2-vote |
| safe_surface (author new) | 93 | 328 | 2-vote surface-gloss (collision-free) |
| safe_surface (dataset-hinted) | 24 | 169 | 2-vote surface-gloss + dataset |

## The frontier (proven)

- **Safe surface-family ceiling = 1,772 tokens** (one gloss per collision-free surface unlocks all its occurrences). This alone reaches ~86.3%.
- The remaining gap to 90% (+3,634) is dominated by **content-homograph + function-word polysemy** that are **per-loc iʿrāb only** — they cannot be glossed surface-wide safely (وما, وإن, الملك, هدى, كذبوا, صالحا, العزيز, أعلم …).
- **Therefore 90% is reachable only by resolving the per-loc iʿrāb pool** (≈3,060 collision + 409 function-word), at the proven 2-vote approval (~55–65%). Pure safe-surface authoring tops out near 85–86%.

## Highest-yield example families (top 25)

| count | collision-free | fn | dataset | qac_pos | surface | lane |
|---:|:--:|:--:|:--:|---|---|---|
| 312 | — | fn |  | P | وما | function_word_polysemy |
| 153 | — |  |  | P | وَإِن | content_homograph (per-loc iʿrāb) |
| 53 | ✓ |  | ds | N | أَلَمْ | safe_surface (dataset-hinted) |
| 43 | — | fn | ds | N | أَلَا | function_word_polysemy |
| 34 | — |  |  | P | وَأَن | content_homograph (per-loc iʿrāb) |
| 31 | ✓ |  | ds | N | أَعْلَمُ | safe_surface (dataset-hinted) |
| 30 | — |  |  | P | لَمَن | content_homograph (per-loc iʿrāb) |
| 28 | — | fn |  | P | فَمَا | function_word_polysemy |
| 25 | ✓ |  |  | P | بِمَآ | safe_surface (author new) |
| 24 | — |  | ds | N | حَقٌّۭ | content_homograph (per-loc iʿrāb) |
| 24 | — |  | ds | P | بِكُم | content_homograph (per-loc iʿrāb) |
| 23 | — |  | ds | N | الْمَلِكُ | content_homograph (per-loc iʿrāb) |
| 22 | — |  | ds | N | هَدَى | content_homograph (per-loc iʿrāb) |
| 22 | — |  |  | V | كَذَبُوا۟ | content_homograph (per-loc iʿrāb) |
| 20 | — |  | ds | N | سَوَاءٌ | content_homograph (per-loc iʿrāb) |
| 19 | — |  | ds | N | صَالِحًا | content_homograph (per-loc iʿrāb) |
| 19 | — |  |  | N | ٱلْعَزِيزُ | content_homograph (per-loc iʿrāb) |
| 19 | — |  |  | P | فَهُم | content_homograph (per-loc iʿrāb) |
| 19 | — | fn | ds | P | لَمَا | function_word_polysemy |
| 18 | — |  |  | P | وَأَنَا | content_homograph (per-loc iʿrāb) |
| 18 | — |  |  | N | عَزِيزٌ | content_homograph (per-loc iʿrāb) |
| 16 | — |  | ds | N | وَعْدٌ | content_homograph (per-loc iʿrāb) |
| 16 | — |  |  | N | أَكْثَرَ | content_homograph (per-loc iʿrāb) |
| 16 | — |  | ds | N | ٱلْهَدْىَ | content_homograph (per-loc iʿrāb) |
| 16 | — |  | ds | V | يَدَّعُونَ | content_homograph (per-loc iʿrāb) |
