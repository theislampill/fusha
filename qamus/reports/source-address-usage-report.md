# Source-address usage report (Project-Xanadu graph)

Bidirectional links across the address families. Generator: `tools/build_decision_backlinks.py` (read-only). Full graph rebuildable on the server; committed counts reflect the state slice.

| family | nodes |
|---|---:|
| live-qamus entry nodes (`qamus:v/n/p###`) | 2092 |
| resolved key-states (`state:key:*`) with backlinks | 120 |
| split/quarantine keys | 159 |
| roots with >1 entry (intentional homograph splits) | 7 |

## The 10 graph queries (answered)

1. **Where is this Qamus entry used?** `root_to_entries` + each entry's `n_ayah_refs` → its āyāt (`quran:S:A`).
2. **Which āyāt use this token?** `key_to_decision[key].used_by` → `quran:S:A:W` addresses.
3. **Which hover glosses depend on this source entry?** entry root → keys authored from its āyāt (join `root_to_entries` ↔ resolved key-states).
4. **Which external references informed this decision?** internal-only `external:*` addresses — never exported publicly (public records are `src:"qamus"`).
5. **What public tokens change if this entry is repaired?** the entry's resolved keys' `used_by` sets.
6. **Which decisions are reused/transcluded?** a key-state is referenced by backlink, never copied — one node per key.
7. **Which homographs are intentionally split?** `split_keys` (159) + `root_to_entries` (7 roots).
8. **Which entries remain unverified by source photo?** 2092 entries (`needs_source_photo_review` = 190).
9. **Which pending tokens share the same blocker?** grouped in `qamus/reports/hover-token-completion.md` by reason; split keys by `decision_reason`.
10. **Which APKG/PDF/GrammarProblems rule supports a sarf/nahw decision?** the procedure cited by each transition links to its rules JSON + `nahw/evals/grammar-problems-*`.

**Orphan links: 0** (every resolved key has ≥1 `used_by`; every entry node has an address).
