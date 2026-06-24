# Hover-gloss — terminal scoreboard

Live qamus-highlight, public beta, indexable. Public records carry only `{src:"qamus",kind:"authored"}` — 0
external provenance. Full per-token states: `hover-token-terminal-matrix.md`.

| metric | baseline | before P5 | LIVE after P5 | **LIVE after SN7** |
|---|---:|---:|---:|---:|
| total hover tokens | 49,900 | 49,900 | 49,900 | 49,900 |
| resolved (qamus-authored) | 25,708 | 29,943 | 34,459 | **34,472** |
| coverage % | 51.52 | 60.01 | 69.06 | **69.08** |
| pending total | 24,192 | 19,957 | 15,441 | **15,428** |
| build diff (occurrences) | — | — | +4,675 / −222 | **+13 / ~3 / −0** |

## P13 — reference-assisted authored batch (APPLIED LIVE)
| metric | LIVE after SN7 | **LIVE after P13** |
|---|---:|---:|
| resolved (qamus-authored) | 34,472 | **35,166** |
| coverage % | 69.08 | **70.47** |
| pending total | 15,428 | **14,734** |
| build diff (occurrences) | +13 / ~3 | **+694 / ~51 / −0** |

23 high-frequency Qurʾānic content-word glosses (ٱلْكِتَٰبَ "the Book", ٱلْءَاخِرَةِ "the Hereafter", يُؤْمِنُونَ
"they believe", ٱلصَّٰلِحَٰتِ "the righteous deeds", ٱلْقُرْءَانِ "the Qurʾan", بَيْنَ "between", ٱلرَّحْمَٰنَ "the
Most Gracious", …) authored from understanding (root + dominant sense), certified by **four gates**: author+2vote
→ empirical norm_strict key-collision probe → key-aware 2-vote re-verify (23/29) → apply. The ~51 "changed" are
verbose spread-glosses improved (basmala ٱلرَّحْمَٰنَ "to show mercy…" → "the Most Gracious"). 0 removed.
~21 true homographs / referent landmines / polysemy terminally classified as pending (the gate working).
Rollback: `fusha-hover-decisions.tsv.bak-p13` + `wbw-lookup.prev.json`. Mirror: `authored_gloss_batch_003_p13.*`.

## SN7 — sarf/nahw verb-form batch (APPLIED LIVE)
8 form-aware verb glosses from the sarf/nahw corpus ingest (أَخْرَجَ "brought forth", اِتَّقَىٰ "was mindful",
كَافِرُونَ "disbelievers", أَقَامُوا "established", اِسْتَغْفِرُوا "seek forgiveness", يَسْتَكْبِرُونَ "act
arrogantly", اِزْدَادُوا "increased", مَدَّ "extended") — certified by **2-vote adversarial + an empirical
norm_strict key-collision test** (13 candidates → 11 → 8 key-safe), applied via `fusha-hover-decisions.tsv` →
`rebuild.sh`. +13 occurrences resolved, 3 verbose spread-glosses improved, **0 removed**. Dropped by the gates:
نَزَّلَ (key `نزل` collides with نَزَلَ "descended"), إِنفَاق/مَخْلُوق (0 occ), تَذَكَّرَ/زَلْزَلَتِ (2-vote).
Rollback: `*.bak-sn7` + `wbw-lookup.prev.json`. Mirror: `qamus/candidates/qamus_2092/authored_gloss_batch_002_sarfnahw.*`.

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
