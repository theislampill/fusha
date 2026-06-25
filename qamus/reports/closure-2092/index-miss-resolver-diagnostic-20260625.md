# Index-miss resolver diagnostic — 2026-06-25

Current live-synced baseline: **43,787 / 49,900 = 87.75%**, pending **6,113**.

This report diagnoses the residual `already_entry_form_present_index_miss` lane after the live deterministic +198 apply. It is resolver/index evidence, not a public hover payload.

## Rollup

| metric | count |
|---|---:|
| residual index-miss rows | 846 |
| strict auto-rule rows remaining | 1 |
| match_type `exact_form` | 638 |
| match_type `root_match` | 208 |
| POS `mismatch` | 640 |
| POS `agree` | 192 |
| POS `unknown` | 14 |

## Why This Is Not A Free Reindex

Live `formext` already requires a single stored-form `(gloss, root)` pair, skips sense-ambiguous/function-word surfaces, and requires root consistency. The residual pool is therefore mostly rows that the resolver is correctly withholding or rows that need authored form/token decisions.

| reason | count |
|---|---:|
| `entry section POS mismatch — needs authored repair/review` | 436 |
| `(root_match_or_no_form_sense)` | 208 |
| `homograph — per-loc context required` | 117 |
| `form maps to 2 senses — ambiguous` | 62 |
| `form maps to 3 senses — ambiguous` | 8 |
| `cross-POS: verb token, nominal sense gloss — needs verbal authoring` | 6 |
| `non-content POS requires function/context review` | 6 |
| `function/proper — context required` | 2 |
| `single sense, POS-agree, no homograph` | 1 |

## Samples

### `strict_auto_remaining` — 1

| loc | surface | qac_pos | entry | match | pos | reason |
|---|---|---|---|---|---|---|
| `20:121:10` | وَرَقِ | `N` | وَرَق | `exact_form` | `agree` | single sense, POS-agree, no homograph |

### `exact_form_pos_agree_not_auto` — 107

| loc | surface | qac_pos | entry | match | pos | reason |
|---|---|---|---|---|---|---|
| `108:2:1` | فَصَلِّ | `V` | فَصَلَ / فِصَال / فَصِيلَتِهِ / يَفْصِل / فَصَّلَ | `exact_form` | `agree` | homograph — per-loc context required |
| `10:39:11` | كَذَّبَ | `V` | كَذَبَ / كَذَّبَ | `exact_form` | `agree` | form maps to 2 senses — ambiguous |
| `111:1:7` | أَبِى | `N` | أَب | `exact_form` | `agree` | homograph — per-loc context required |
| `111:2:2` | أَغْنَىٰ | `V` | أَغْنَى / تَغْنَ | `exact_form` | `agree` | form maps to 2 senses — ambiguous |
| `111:3:3` | ذَاتَ | `N` | ذُو | `exact_form` | `agree` | homograph — per-loc context required |
| `11:10:8` | ذَهَبَ | `V` | ذَهَبَ / أَذْهَبَ / ذَهَب | `exact_form` | `agree` | form maps to 2 senses — ambiguous |
| `11:73:14` | مَّجِيدٌۭ | `N` | مَجِيد | `exact_form` | `agree` | form maps to 2 senses — ambiguous |
| `12:21:5` | مِّصْرَ | `N` | مِصْر | `exact_form` | `agree` | function/proper — context required |

### `exact_form_pos_mismatch` — 524

| loc | surface | qac_pos | entry | match | pos | reason |
|---|---|---|---|---|---|---|
| `10:107:6` | كَاشِفَ | `N` | كَشَفَ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `10:22:32` | مُخْلِصِينَ | `N` | خَلَصَ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `10:2:18` | صِدْقٍ | `N` | صَدَقَ / صِدِّيق / صَدَّقَ / صَدِيق / تَصَدَّقَ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `10:55:12` | حَقٌّۭ | `N` | حَقَّ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `10:71:13` | مَّقَامِى | `N` | قَامَ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `10:90:23` | بَنُوٓا۟ | `N` | بَنَاهَا | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `10:93:6` | صِدْقٍۢ | `N` | صَدَقَ / صِدِّيق / صَدَّقَ / صَدِيق / تَصَدَّقَ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |
| `114:4:3` | الْوَسْوَاسِ | `N` | وَسْوَسَ | `exact_form` | `mismatch` | entry section POS mismatch — needs authored repair/review |

### `root_match_review` — 208

| loc | surface | qac_pos | entry | match | pos | reason |
|---|---|---|---|---|---|---|
| `10:22:34` | ٱلدِّينَ | `N` | دِين / دَيْن | `root_match` | `mismatch` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `10:5:9` | مَنَازِلَ | `N` | نَزَلَ | `root_match` | `mismatch` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `10:84:3` | آمَنْتُمْ | `None` | قَامَ | `root_match` | `unknown` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `10:87:12` | قِبْلَةًۭ | `N` | يَقْبَل | `root_match` | `mismatch` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `10:90:13` | ٱلْغَرَقُ | `N` | أَغْرَقْنَا | `root_match` | `mismatch` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `114:2:1` | مَلِكِ | `N` | مَلَكَتْ / مَالِك / مَلَائِكَة | `root_match` | `mismatch` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `11:1:12` | لَّدُنْ | `N` | مِن لَدُن | `root_match` | `agree` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |
| `11:27:19` | بَادِىَ | `N` | بَدَا | `root_match` | `mismatch` | already_entry_form_present_index_miss: requires form_variant with two_vote gate |

## Action

- Do not bulk-relax the live resolver for this pool.
- Fold the one strict auto-rule row (`20:121:10`, `وَرَقِ`, “tree leaves”) into the next certified token apply or a tiny deterministic follow-up only if bundled with larger certified rows.
- Route the rest through two-vote form/token/verb-clitic lanes or owner/source/scholar blockers according to the refreshed triangulation table.
