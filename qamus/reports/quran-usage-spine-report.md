# Qurʾān usage spine — report (PP1)

A single source-addressed token spine (`quran:S:A:W`) for every āyah used by the p001–p100 particle entries; entries and hover-gloss decisions **reuse** these nodes by backlink (Xanadu), they do not duplicate the āyah. Full data: `qamus/indexes/quran_usage_spine.json`. Generator: `qamus/scripts/build_particle_reports.py`.

| metric | value |
|---|---:|
| āyah nodes | 219 |
| token nodes (`quran:S:A:W`) | 3245 |
| resolved (have a `wbw:S:A:W` gloss) | 2362 |
| pending | 883 |

Each token node carries `{w, surface, state}`; resolved tokens link to a `wbw:S:A:W` gloss node, pending tokens carry a precise reason. 0 orphan: every token is classified.
