# Hover-gloss — terminal scoreboard

Live qamus-highlight, public beta, indexable. Public records carry only `{src:"qamus",kind:"authored"}` — 0
external provenance. Full per-token states: `hover-token-terminal-matrix.md`.

| metric | baseline | before P5 | **LIVE after P5** |
|---|---:|---:|---:|
| total hover tokens | 49,900 | 49,900 | 49,900 |
| resolved (qamus-authored) | 25,708 | 29,943 | **34,459** |
| coverage % | 51.52 | 60.01 | **69.06** |
| pending total | 24,192 | 19,957 | **15,441** |
| build diff (occurrences) | — | — | **+4,675 / −222** |

## Pending by reason (live now)
| reason | n |
|---|---:|
| root_exists_form_unresolved | 17,398 |
| no_qamus_entry (proper nouns / particles) | 2,451 |
| source_data_issue | 108 |

## Correctness (this program, across C12–C14 + P-tranche)
| metric | n |
|---|---:|
| **known wrong public glosses OPEN** | **0** (every 2-vote-confirmed wrong fixed/quarantined) |
| wrong glosses fixed | 3,378 QAC root+POS drops + ~110 curated/diacritic quarantines |
| quarantines (sense + homograph) | ~110 |
| authored glosses added — fnauth function words | 2,583 (live) |
| authored glosses added — **P4/P5 fusha batch** | **106 surfaces → 4,835 token records live** (2-vote verified) |
| pre-existing data-error wrongs FIXED by the override | عَلِيمٌ "to be in pain"→"All-Knowing"; عِند "stubborn"→"with/near" |

## P4/P5 — external-reference-assisted authored batch
The P4 engine authors concise, surface-stable **dominant-sense** glosses for the highest-frequency
`root_exists_form_unresolved` tokens (قَالَ "said" 236×, ءَامَنُوا "believed" 167×, ٱلنَّاسُ "the people" 119×,
ٱلْكِتَٰبَ "the Book" 92×…), QAC root + Qamus entry + sarf/nahw-guided, **2-vote verified**. Confirmed decisions
export to the gitignored `fusha-hover-decisions.tsv` consumed by the live expand.py `fusha` pass → rebuild.
External references inform the authoring internally; **nothing external ships** (public = `src:"qamus"`).

**P5 applied (live):** the 109-surface batch is deployed — coverage **60.01% → 69.06% (+9.05)**, health 200,
0 provenance leaks, 41 tests + validate PASS, prev.json rollback. The override additionally fixed pre-existing
data-error wrongs. A post-deploy 2-vote confirmatory scan over the fusha records gates any residual.
