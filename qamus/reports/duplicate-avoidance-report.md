# Duplicate-avoidance report

Project-Xanadu rule: **reuse before minting.** One node per key/entry; decisions are reused by backlink, not copied. >1 entry per root is an *intentional* sense/homograph split, confirmed — not a duplicate.

| metric | value |
|---|---:|
| entry nodes | 2092 |
| distinct roots | 1091 |
| roots with multiple entries (intentional splits) | 7 |
| duplicated/copied decisions | **0** (key-states referenced, never duplicated) |

## Sample intentional splits (root → entries)

| root | entries |
|---|---|
| ر و د | 213945255c3b, 29587bc586c7 |
| ذ م م | 25460db4e3ce, d99748318ce0 |
| ص ر ر | 2fee38d0e6c0, 6bb15cbe2246 |
| ف ر ج | 3b927026b88a, 57c90af7e9e8 |
| ط ر ف | 53bbf2c4975a, 8cf8aaa84b2a |
| ص ل ي | 5999a42d7bdd, 8bb806510d1d |
| ز ر ع | ce909b563637, d0eac6ef4f78 |
