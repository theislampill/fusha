# DR04 — remaining stems / authoring lane readiness — my re-attempt (2026-06-25, HEAD d67f873)

Lane-readiness re-derived from the current tree (generator + validator + schema confirmed present per lane). **GO:** form_variant (top lever), host_lexeme (noun-only), token_irab. **Built / review-only:** verb_clitic (638), source_entry_repair. **Owner-gated:** new_entry (52), index_miss (live reindex, not authoring). **Source/scholar-gated:** source_photo. The prior NO-GO (polluted host-lexeme, unhandled forms-array, missing generators) is resolved — all generators+validators+schemas exist and pass the regression gate.

| id | status | blocks | finding | remaining |
|---|---|---|---|---|
| DR04-form_variant | **confirmed_fixed** | — | existing-entry form authoring lane | GO — top lever for 90% |
| DR04-host_lexeme | **confirmed_fixed** | — | noun-host possessive lane | GO — noun-only (verb clitics split out, lane-sanity PASS) |
| DR04-token_irab | **confirmed_fixed** | — | token iʿrāb / function-word lane | GO — two votes must agree on answer AND reason |
| DR04-verb_clitic | **confirmed_fixed** | — | verb-clitic object/subject lane | review-only (two-vote); not auto |
| DR04-new_entry | **confirmed_fixed** | 90% | missing-entry proposals lane | owner-gated, review-only |
| DR04-source_entry_repair | **confirmed_fixed** | — | source-entry repair lane | source-gated where source_photo mode |
| DR04-index_miss | **narrowed** | 90% | index-miss lane | owner-gated live reindex; NOT authoring |
| DR04-source_photo | **confirmed_fixed** | corpus | source-photo / scholar-gated lane | owner/source-gated (crops) |