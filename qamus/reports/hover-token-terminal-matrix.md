# Hover-token terminal matrix (qamus-highlight, live 60.01%)

Every one of the **49,900** rendered Qurʾān usage-āyah tokens has exactly one terminal state — **no silent
unknown bucket.** Regenerate the full per-token JSONL with `qamus/scripts/export_hover_state.py` (kept under the
gitignored `out/`; the per-token file is large). Source: the deployed `wbw-lookup.json` + QAC root/POS reference.

## State breakdown (reconciles to 49,900)
| state | n | meaning |
|---|---:|---|
| resolved (high conf) | 4,967 | curator primary/exact form-match |
| resolved (med conf) | 10,281 | propagated / form-extension |
| resolved (low conf) | 14,695 | qacext / clitic / suffix / **fnauth function-word authoring** |
| **pending: root_exists_form_unresolved** | **17,398** | QAC gives a root but no gloss yet — **the P4 authoring target** |
| pending: no_qamus_entry | 2,451 | QAC marks it rootless / no Qamus entry (many are proper nouns / particles) |
| pending: source_data_issue | 108 | QAC has no entry for the token (~0.2%; curator-spelling divergence) |
| **resolved total** | **29,943** | **coverage 60.01%** |
| **pending total** | **19,957** | |
| **known wrong public glosses OPEN** | **0** | every 2-vote-confirmed wrong across the C12–C14 scans is fixed/quarantined |

## How a pending token becomes resolved (the production pipeline)
1. `pending: root_exists_form_unresolved` → **P4 authored-gloss batch**: QAC root → Qamus entry → author the
   concise dominant-sense gloss (sarf/nahw-guided, surface-stable) → 2-vote verify → live rebuild. The top
   pending surfaces are fundamental vocabulary (قَالَ "said" 236×, ءَامَنُوا "believed" 167×, ٱلنَّاسُ "the people"
   119×, ٱلْكِتَٰبَ "the Book" 92×, يَوْمِ "day" 140×).
2. `pending: no_qamus_entry` → mostly proper nouns + particles; particle compounds get a grammatical gloss,
   proper nouns stay pending (or get a name gloss only with certainty).
3. `pending: source_data_issue` → curator-spelling vs Uthmani divergence; resolve via `norm_strict` review.

## Top pending surfaces (P4 candidates, ranked by frequency)
The top-400 are in `qamus/candidates/qamus_2092/` (enriched with QAC root/POS + the Qamus entry's senses).
A surface-keyed authored gloss is safe only when the surface's meaning is **stable across contexts** — a
context-sensitive homograph/polyseme stays pending per `nahw/SKILL.md`.

## Invariant
The matrix carries no `informed_by`, QAC name, OCR snippet, or source path — it is a state ledger of public
qamus-authored glosses + honest pending reasons.
