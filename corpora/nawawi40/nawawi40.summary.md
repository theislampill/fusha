# Nawawī40 catalogue-first pilot — summary

**Catalogue-first, review-only.** This pass reads the 42 hadith of al-Arbaʿūn al-Nawawiyyah, tokenizes the
Arabic matn, diffs every lexeme against the existing Qamus 2,092, and emits **candidate** additions/augmentations
for human review. **It does not write live Qamus.** Authored gloss drafts (where present) are original and carry
internal provenance only; nothing ships publicly from this pass.

## Access method
Arabic matn from an **openly-licensed JSON edition** of An-Nawawī's Forty (public-domain classical hadith text);
loaded locally via `--src corpora/nawawi40/nawawi40.matn.jsonl`. No scraping in the pipeline; no copyrighted gloss
text ingested — only the classical Arabic matn (treated read-only, never altered).

## Stats (acceptance)
| metric | n |
|---|---:|
| Qamus entries loaded (baseline) | **2,092** |
| Nawawī40 refs scanned | **42** |
| total raw token occurrences | **2,818** |
| distinct lexeme candidates | **1,183** |
| unique normalized tokens | **1,048** |
| already_in_qamus | **394** |
| new_surface_for_existing_lemma | 6 |
| new_lemma_existing_root | 272 |
| new_root_or_unknown_root | 499 |
| particle_or_construction_candidate | 6 |
| uncertain_needs_review | 6 |
| **new-entry candidates** (review-only) | **720** |
| occurrence-augmentation candidates | 6 |
| **review-queue** | **789** |
| live website writes | **0** |
| in-run / already-in-Qamus duplicates blocked | 51 / 0 |

## Outputs
Full JSONL outputs are regenerable under the gitignored `corpora/nawawi40/out/` (raw_tokens, lexeme_candidates,
diff_against_quran_qamus, new_entries.candidate, occurrence_augments.candidate, review_queue). Committed
**samples** live in `qamus/candidates/nawawi40/`. Regenerate:
```
python qamus/scripts/catalogue_nawawi40.py --src corpora/nawawi40/nawawi40.matn.jsonl --out corpora/nawawi40/out
python qamus/scripts/diff_against_qamus.py  --lex corpora/nawawi40/out/nawawi40.lexeme_candidates.jsonl --out corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl
python qamus/scripts/make_candidate_payloads.py --diff corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl --out corpora/nawawi40/out --draft-glosses
```

## SN8 refinement (upgraded skills) — reviewer signals, classification unchanged

`qamus/scripts/refine_nawawi40.py` re-runs the diff through the upgraded sarf/nahw layer to add **reviewer
signals**, not to re-bucket. An automated weak-aware root tie was prototyped to shrink the big
`new_root_or_unknown_root` bucket, but a spot-check measured it at **~50% precision** (وَمَنْ→أمن, هُرَيْرَةَ→هور,
الْأَمْرِ→ألم were spurious ties). Asserting those roots would mislead the reviewer — worse than leaving them
unknown — so **the classification is left exactly as the conservative diff had it** (the same discipline as the
S7/P6 `impossible_root` re-diagnosis). What SN8 *does* add (regenerable to `corpora/nawawi40/out/`):

| signal | value |
|---|---|
| classification | unchanged (already_in_qamus 394 · new_lemma_existing_root 272 · unknown 499 · …) |
| weak-root **hints** (low-conf, QAC/human confirms) | 189 flagged, never asserted |
| POS guess (wazn) | 112 morphologically classified (38 ism fāʿil · 58 derived verb · 11 maṣdar · 4 Form X · 1 ism mafʿūl) |
| Fusha-learning priority | 205 high · 558 medium · 420 low |
| hadith-technical (low Qamus priority) | 14 (روى/إسناد/صحيح…) |
| likely to recur in Ṣaḥīḥayn | 166 |

Net effect: better triage (priority + recurrence + hadith-domain separation + honest hints) without a single
false root claim. Root confirmation for the weak/unknown bucket remains a human/QAC task. No live writes.

## Notes for the reviewer (apply the sarf + nahw skills)
- The big `new_root_or_unknown_root` bucket (499) is dominated by hadith-frequent forms not in a Qurʾān-centric
  Qamus (e.g. رَوَاهُ "narrated it" ر و ي, إِسْنَاد, صَحِيح) — these need a human root/POS call per `sarf/SKILL.md`.
- Particles/constructions stay diacritic- and context-sensitive (`nahw/SKILL.md`); do not resolve homographs by
  `norm()`.
- No candidate is an addition to live Qamus until a human approves it via
  `qamus/reports/fusha-to-qamus-highlight-bridge.md`. Ṣaḥīḥayn is a **future** expansion (see
  `corpora/sahihayn/PLAN.md`), owner-gated.
