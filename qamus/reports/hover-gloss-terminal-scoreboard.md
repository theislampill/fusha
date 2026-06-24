# Hover-gloss — terminal scoreboard

Live qamus-highlight, public beta, indexable. Public records carry only `{src:"qamus",kind:"authored"}` — 0
external provenance. Full per-token states: `hover-token-terminal-matrix.md`.

| metric | baseline | live now | after P5 apply |
|---|---:|---:|---:|
| total hover tokens | 49,900 | 49,900 | 49,900 |
| resolved (qamus-authored) | 25,708 | **29,943** | _filled on P5 apply_ |
| coverage % | 51.52 | **60.01** | _filled on P5 apply_ |
| pending total | 24,192 | 19,957 | _filled on P5 apply_ |

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
| authored glosses added — **P4 fusha batch** | _filled on P5 apply_ |

## P4/P5 — external-reference-assisted authored batch
The P4 engine authors concise, surface-stable **dominant-sense** glosses for the highest-frequency
`root_exists_form_unresolved` tokens (قَالَ "said" 236×, ءَامَنُوا "believed" 167×, ٱلنَّاسُ "the people" 119×,
ٱلْكِتَٰبَ "the Book" 92×…), QAC root + Qamus entry + sarf/nahw-guided, **2-vote verified**. Confirmed decisions
export to the gitignored `fusha-hover-decisions.tsv` consumed by the live expand.py `fusha` pass → rebuild.
External references inform the authoring internally; **nothing external ships** (public = `src:"qamus"`).

_This scoreboard's "after P5" column + the authored-batch count are filled when the verified batch is applied
and the live artifact rebuilt._
