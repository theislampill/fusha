# Live public-entry crawl — live-vs-repo reconciliation (20260625)

> **COMPLETE — all repo entries crawled.**

| metric | value |
|---|---:|
| repo entries | 2,092 |
| crawled (read-only GET /e/<id>) | 2,092 (100.0%) |
| HTTP 200 | 2,092 |
| render errors | 0 |
| headword mismatches (norm) | 0 |
| crawled ids not in repo | 0 |
| hover tokens seen (resolved/total) | 103,141 / 109,108 |

## Method (read-only, polite)

GET `/e/<id>` only — no login, no POST, no private endpoints. Single-threaded, throttled, resumable from an append-only checkpoint. Entry id list is the committed repo dataset, so the crawl reconciles live render vs repo by construction.
