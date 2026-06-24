# Hover-gloss — terminal scoreboard

Live qamus-highlight, public beta, indexable. Public records carry only `{src:"qamus",kind:"authored"}` — 0
external provenance. Full per-token states: `hover-token-terminal-matrix.md`.

> **CURRENT LIVE (reconciled): coverage 81.41% · 40,623 / 49,900 resolved · 9,277 pending · tsv 1,223 + 363 token decisions.**
> Trail: … B4 78.78 → B5 79.93 → particle-hardtail 80.68 → **B6 token-layer 81.41**.
> **MCP-backed decisions live: 61** · **token-addressed decisions live: 363** (per-`quran:S:A:W` overrides).
> **wrong-gloss open: 0** · **−0 removed across all batches.**

## B6 — token-addressed override layer (APPLIED LIVE)
The first layer that resolves **surface-key collisions** the TSV cannot: a per-token (`quran:S:A:W`) decision >
surface-key TSV > pending, wired into `qamus_wbw/expand.py` (exempt from the homograph denylist). **363 decisions**
disambiguated by vocalized harakāt: لَمْ "did not" (121) vs لِمَ "why" (3); مَنْ "who/whoever" (161) vs مِنْ "from"
(4); أَمْ "or" (65) vs أُمّ "mother" (7). **Precedence proven live**: same key `لم`, لَمْ@46:11:13→"did not",
لِمَ@61:5:6→"why". coverage **80.68% → 81.41%**, **+363 occ, −0 removed**. Same-surface polysemy (وَمَا, bare إِنْ,
لَمَّا) left pending for per-token iʿrāb. Detail: `token-addressed-hover-layer.md`. Mirror:
`token_hover_decisions_batch_001.*` / `particle_token_hover_batch_003.*`. Rollback: empty the token JSONL + rebuild.

## Particle hard-tail (APPLIED LIVE) — completes the p001–p100 example āyāt
**289 glosses** (311 safe-single content tokens in particle example āyāt → 289 certified, 22 rejected). The 157
function-word homograph keys (لَمْ/لِمَ, وَإِن/وَإِنَّ, وَمَنْ/وَمِنْ, أَمْ/أُمّ) are documented blockers,
**MCP iʿrāb-confirmed** (`particle-hover-audit.md`). Particle-āyah coverage **81.51% → 90.51%**. Overall
coverage **79.93% → 80.68%**, **+373 occ, −0 removed**. Mirror: `particle_hover_batch_002_tafsir_mcp.*`;
rollback `*.bak-bpart`.

## B5 — MCP-aware noun + verb sweep (APPLIED LIVE)
**190 glosses** (230 cand → 190 certified, 40 rejected; **61 MCP-backed**). First batch using Tafsir MCP as an
internal morphology witness (form/voice/person pre-confirmed for 80 verbs; author + key-aware 2-vote then
authored precise finite glosses). Verbs (they fight you, he worships, he breaks a promise, they seek), nouns
(wrongdoing, angels, women, the Holy Spirit), participles. 40 rejects = form/voice (سخر, يسبحون, يخلقون) +
referent (حملته, اتخذت) + lemma collisions. coverage **78.78% → 79.93%**, **+575 occ, −0 removed**. MCP morphology
is internal only (informed_by += tafsir-mcp); public stays `{src:"qamus"}`. Mirrors: `hover_batch_007_b5.*` +
`tafsir_mcp_hover_batch_001.*`; rollback `*.bak-b5`.

## B4 — deep-tail noun + verb sweep (APPLIED LIVE)
**181 glosses** (230 cand → 181 certified, 49 rejected; top occ now 5). نَزَّلَ/كَذَّبَ landmine keys (نزلنا,
كذبت, كذبا) empirically cleared (Form-II/noun-only in the corpus). coverage **77.31% → 78.78%**, **+732 occ, −0
removed**. Cumulative this tranche: **+526 glosses, +3,316 occ** (per-batch +1,571 → +1,013 → +732, diminishing as
the homograph-dense tail begins). Mirror: `hover_batch_006_b4.*`; rollback `*.bak-b4`.

## B3 — continued noun + verb sweep (APPLIED LIVE)
**186 glosses** (230 cand → 186 certified, 44 rejected; B2 rejects pre-excluded). Plurals/content nouns (faces,
the eyes, the matters), proper nouns (Lot, Midian), participles (the clear, most grateful, the criminals), finite
verbs (they are promised, We gave them, they were arrogant, and establish). 44 rejects = form/voice (يتبعون,
ذكروا, دعوا) + lemma (مثله, الذكر, حكما, بشرا) collisions. coverage **75.28% → 77.31%**, **+1,013 occ, −0
removed**. Cumulative this tranche: **+345 glosses, +2,584 occ**. Mirror: `hover_batch_005_b3.*`; rollback `*.bak-b3`.

## B2 — noun + verb + particle-cluster sweep (APPLIED LIVE)
**159 content-token glosses** (230 candidates → 159 certified, 71 rejected) via the four-gate pipeline (empirical
key-probe → author + key-aware 2-vote). Proper nouns (Adam, Abraham, Noah, David, Moses, the Torah), divine
attributes (the Merciful, All-Hearing, All-Seeing, All-Forgiving, the Living), case-variant content words, and
finite verbs (We seized, We sent down, you worship, they possess). The 71 rejections are the gate catching real
homographs: lemma collisions (الملك مُلْك/مَلِك, أمه community/mother), form/voice (كذبوا, يخرج), particle-sense
(وإن if/indeed, لم why/not), referent/polysemy (الدين religion/judgment, العزيز divine-Name/minister).
coverage **72.14% → 75.28%**, **+1,571 occ, ~50 improved, −0 removed**. Mirror: `hover_batch_004_b2.*`.
Rollback: `*.bak-b2` + `wbw-lookup.prev.json`.

## N1/V1 — noun + verb sweep (APPLIED LIVE)
**55 content-token glosses** (28 nouns + 27 verbs) from the global pending pool, certified via the four-gate
pipeline (empirical key-probe → author + key-aware 2-vote): **55/80 certified, 25 rejected** (true homographs:
أُمَّة↔أُمّهُ, مُلْك↔مَلَك↔مَلِك, فَضْل↔فَضَّلَ, يَخْرُجُ I↔IV, قُتِلَ voice, أَمَرَهُمْ verb↔noun, نَزَّلَ form…).
Nouns incl. divine *attributes* as adjectival glosses (سَمِيع "All-Hearing", خَبِير "All-Aware", غَفُور "Most
Forgiving"); verbs with finite person/number (خَلَقْنَا "We created", يَقُولُوا "they say", ٱدْخُلُوا "enter!").
coverage **70.76% → 72.14%**, +689 occ, **~0 changed, −0 removed**. Mirrors: `noun_hover_batch_001.*`,
`verb_hover_batch_001.*`. Rollback: `*.bak-nv` + `wbw-lookup.prev.json`.

## PP1 — particle-lane authored batch (APPLIED LIVE)
26 content-token glosses from the p001–p100 example āyāt (ٱلصِّيَامِ, ٱلْمُؤْمِنُونَ, ٱلرُّسُلِ, مَثَلًا, خَٰلِدُونَ,
يُنفِقُونَ, يَتَّقُونَ…) + the **كَظِيم entry repair** (Q2). coverage **70.47% → 70.76%**, +141 occ, ~3 changed
(كَظِيم verb→adjectival), −0 removed. 4 homographs (هَدَيْنَا/حَرَّمَ/وَلَدَ…) correctly pending. Mirror:
`particle_hover_batch_001.*`. Rollback: `*.bak-pp1` + `wbw-lookup.prev.json`.

| metric | baseline | before P5 | LIVE after P5 | LIVE after SN7 | **CURRENT (P13)** |
|---|---:|---:|---:|---:|---:|
| total hover tokens | 49,900 | 49,900 | 49,900 | 49,900 | 49,900 |
| resolved (qamus-authored) | 25,708 | 29,943 | 34,459 | 34,472 | **35,166** |
| coverage % | 51.52 | 60.01 | 69.06 | 69.08 | **70.47** |
| pending total | 24,192 | 19,957 | 15,441 | 15,428 | **14,734** |
| build diff (occurrences) | — | — | +4,675 / −222 | +13 / ~3 / −0 | **+694 / ~51 / −0** |

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

## Pending by reason (live now — from `export_audit_state.py` at 81.41%)
| reason | n |
|---|---:|
| `pending_needs_sarf` (root exists, form/sense unresolved — the authorable lever) | 7,981 |
| `pending_no_qamus_entry` (no entry: particles / proper nouns) | 1,236 |
| `pending_source_data_issue` | 47 |
| `pending_proper_noun` | 13 |
| **total pending** | **9,277** |

`pending_no_qamus_entry` fell 1,590 → **1,236** (the token layer resolved the function-word homographs). Distinct
pending surfaces 6,422 → **5,433**. State graph (key-level): 1,222 resolved / 156 quarantine / 11,345 pending; the
token layer resolves **per-loc within collision keys** (sub-key), so it lifts coverage without changing key counts.

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
