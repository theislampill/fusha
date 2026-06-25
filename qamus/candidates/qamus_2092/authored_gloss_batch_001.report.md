# Authored-gloss batch 001 — report

**External-reference-assisted, original qamus-authored.** The Fusha decision engine selected the highest-yield
safe pending tokens (top of `root_exists_form_unresolved`, ranked by frequency), gathered internal evidence
(Qamus entry senses + QAC root/POS + āyah context), and authored **concise, form-aware, dominant-sense** English
glosses — sarf/nahw-guided, **not copied** from any external source. Each was **2-vote verified** for
surface-wide stability.

## Batch
| metric | n |
|---|---:|
| candidates processed | 160 (top pending surfaces) |
| authored | 156 |
| **2-vote confirmed → applied** | **109** |
| held pending (context-sensitive / ambiguous) | 51 |
| applied to live qamus-highlight | yes — see `fusha-production-bridge-status.md` |

## Selection
Top pending vocabulary by frequency: قَالَ "he said" (236×), ءَامَنُوا "they believed" (167×), كُلّ "all/each"
(163×), قُلْ "say! (command)" (161×), يَوْمِ "day (of)" (140×), ٱلنَّاسُ "the people / mankind" (119×),
ٱلْكِتَٰبَ "the Book / Scripture" (92×), ٱلْمُؤْمِنِينَ "the believers", ٱلْقِيَٰمَةِ "the Resurrection",
ٱلصَّلَوٰةَ "the prayer", وَرَسُولِهِ "and His Messenger", وَمِنَ "and among / and from" (preposition, kasra).

## Authoring rules honored (sarf/nahw)
- Concise hover gloss (1–5 words), **original wording** — the verbose Qamus gloss was distilled, not copied.
- **Form-aware** (قَالَ "he said" vs قُلْ "say!"), surface-stable only; context-sensitive surfaces → pending.
- Diacritic homographs respected (وَمِنَ kasra "from" ≠ وَمَن fatha "who" — guarded at assembly).
- **No external gloss text copied; `informed_by` is internal only** (see `authored_gloss_batch_001.provenance.jsonl`,
  labels qac/qamus/quran-context). The public hover record is exactly `{src:"qamus",kind:"authored",lang:"en"}`.

## Provenance & public boundary
`authored_gloss_batch_001.jsonl` = the confirmed decisions. `*.provenance.jsonl` = internal provenance (source
labels + the public record) — **never shipped**. Live export: `export_hover_decisions.py` →
`fusha-hover-decisions.tsv` (gitignored runtime ref) → live `expand.py` fusha pass. Verified live: 0 provenance
leaks, coverage 60.01% → 69.18%.
