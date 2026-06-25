# Project-Xanadu source-address completion report

source_sha `65797d7d5599fadd` · entries 2,092 · addresses **28,393** · āyāt 3,854 · decisions 2745 · repairs 132

**Orphan links: 0** (address→entry 0, spine→entry 0).

## The 10 graph queries (all answerable; see query_source_address_graph.py)

- 1. Which entry supports this hover word? → spine[S:A].entries + token gloss (query --token S:A:W)
- 2. Which hover words depend on this entry? → query --entry <id> --dependents (āyāt→tokens)
- 3. Which āyāt use this entry? → entry usage addresses qamus:<id>#usage=<S:A>
- 4. Which source photo/page supports this entry? → source-photo:<locator>#entry=<sk>
- 5. Which entries share this root? → by-root / query --root
- 6. Which decisions were rejected because of this homograph? → by_homograph_key[key].pending_ambiguous
- 7. Which pending words share this blocker? → by_blocker[blocker] (full list in P3 by-blocker)
- 8. Which repairs affect which tokens? → by_repair[*].affects_ayat
- 9. Which sarf/nahw rule was used for this decision? → by_decision[*].procedure
- 10. Which entry fields remain source-unverified? → qamus-entry-field-addresses (source_verified=false)

Entries with a source-photo-verified field: 3 / 2,092 (the rest carry `source-photo:unlocated#entry=<sk>` locators for P7).
