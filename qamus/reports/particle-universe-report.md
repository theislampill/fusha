# Particle Universe Report — example-āyah occurrence universe + P-00..P-05 candidate matrix

> **Updated 2026-08-05:** the owner renumbered the particle plan — the 49-entry P-03 long tail split into P-03 (question/response + operators, 16), P-04 (demonstratives + relatives, 18), P-05 (personal pronouns, 15); plan = P-00..P-05 at 12/17/22/16/18/15. SSOT: `qamus/data/particle-tranche-membership.json`. Tables below re-tallied from the relabeled matrix.

Date: 2026-07-28 · Lane: candidate-mode (no live mutation; all inputs are committed repo artifacts) · Builders: `tools/build_example_ayah_universe.py` v1.0.0, `tools/build_particle_occurrence_matrix.py` v1.0.0 · Validator: `tools/validate_example_universe.py` (wired into `tools/check_regressions.py`, "UNIVERSE" gates).

## 1. Global universe totals (`qamus/lattice/example-ayah-universe.jsonl` + `.occurrences.jsonl` + `.meta.json`)

One row per displayed-token appearance across every example card of every committed entry; the `.occurrences.jsonl` rollup preserves the unique-occurrence grain. The two denominators are different by design and are never collapsed.

| measure | value |
|---|---:|
| entries (pages) | 2,092 |
| pages with ≥1 example card | 2,091 (`n993` مَلْجَأ has none) |
| example cards | 7,700 |
| displayed tokens (incl. pause marks) | 117,117 |
| displayed words | 109,471 |
| pause-mark tokens (word_class=pause_mark) | 7,646 |
| selected words (match the entry's own usage forms, strict key) | 4,409 |
| context words | 105,062 |
| words aligned to a canonical loc | 109,018 |
| words unaligned (blockers recorded per row) | 453 |
| **unique canonical occurrences** | **50,041** |
| **appearances at those occurrences** | **109,018** |

Displayed words by hosting page type: v 94,522 · n 13,999 · p 950 (aligned: 94,286 / 13,833 / 899).

Card alignment basis (7,700 cards): contiguous_exact 1,942 · contiguous_strict 5,402 · contiguous_loose 122 · per_word_fallback 214 · ambiguous 4 · ref_unparsed 16.
Word match basis (109,471 words): exact 95,416 · strict 12,795 · strict_word_unique 630 · loose 135 · loose_word_unique 42 · ambiguous 82 · unaligned 232 · ref_unparsed 139. Loose bases are recall-tier candidates only, never a certification basis.

Relation to existing machinery: `qamus/indexes/occurrence-appearances.jsonl` (34,323 occurrences / 56,117 appearances) remains the whitelist-derived reader/entry-example index; the universe adds the per-displayed-word grain (all context words, display-local locs, selected-vs-context, fragments) that the whitelist surface cannot see, and backlinks into it via `wbw_present` / `appearance_index_entry_linked`.

## 2. Particle membership (committed table)

`qamus/data/particle-tranche-membership.json` encodes the owner-approved p001–p100 assignment: P-00 = 12, P-01 = 17, P-02 = 22, P-03 = 16, P-04 = 18, P-05 = 15 (sum 100; each source_key exactly once; every P-02 row carries `scholar_two_vote_required`; the `p_plan_renumber_2026_08_05` key records the split). Dual-family tensions and dogfood zero-row flags are carried per row.

## 3. Particle-occurrence candidate matrix (`qamus/lattice/particle-occurrence-matrix.jsonl`)

One row per particle-entry × candidate-occurrence over the universe. CANDIDATE lattice only: `certified` = `"none"` on every row; `function_candidates` is a list, never a winner; clitic-vs-free is a heuristic pending segmentation evidence.

| measure | value |
|---|---:|
| particles covered | 100 (all reported; 3 with zero aligned candidates, see §5) |
| matrix rows (particle × occurrence) | 50,263 |
| candidate appearances | 109,364 |
| unaligned candidate appearances (no canonical loc yet) | 396 |

Match kind/basis across rows: clitic_prefix_normalized 24,997 · free exact 5,800 · free normalized 9,528 · free_with_proclitic 5,305 · free loose 4,633.

### Page-appearance classes (candidate appearances)

| class | count |
|---|---:|
| selected-on-p | 133 |
| context-on-p | 840 |
| context-on-v | 95,171 |
| context-on-n | 13,220 |

### Per-tranche candidate occurrence counts

| tranche | particles | matrix occurrences | selected-on-p | context-on-p | context-on-v | context-on-n |
|---|---:|---:|---:|---:|---:|---:|
| P-00 | 12 | 21,662 | 21 | 335 | 41,559 | 6,173 |
| P-01 | 17 | 8,444 | 32 | 163 | 15,821 | 1,822 |
| P-02 | 22 | 9,723 | 36 | 155 | 18,250 | 2,391 |
| P-03 | 15† | 7,905 | 17 | 140 | 14,949 | 2,259 |
| P-04 | 16† | 1,451 | 19 | 16 | 2,722 | 336 |
| P-05 | 15 | 1,078 | 8 | 31 | 1,870 | 239 |

† particles column counts particles WITH candidate matrix rows; membership totals are P-03=16, P-04=18 (the difference = dogfood zero-row particles with no candidate occurrences).

Largest candidate spaces: p010 الْ 6,634 · p009 وَ 6,586 · p005 فَـ 3,288 · p007 لَـ/لِـ 2,999 · p002 بِـ 2,492 · p034 مِنْ 2,481 · p011 أَنَّ 2,291 · p100 مَنْ 2,088 · p012 إِنَّ 1,903 · p056 لَا 1,781.

## 4. The corrected particle denominator

The prior particle-page sweep counted **984 rendered context-word spans on the 100 particle pages only**. That is a page-render denominator, not the particle-occurrence denominator. Across ALL pages of the example-āyah universe the particle candidate space is:

- **50,263 candidate particle occurrences** (unique particle × canonical-occurrence pairs), carrying
- **109,364 candidate appearances**, of which only 973 (selected-on-p 133 + context-on-p 840) sit on particle pages at all — the other **108,391 candidate appearances (99.1%) live on verb/noun pages** and were invisible to the 984-span denominator.

## 5. Gaps needing follow-up

1. **Zero-aligned particles (3):** p001 أَ (interrogative hamza — affix-shaped, not strict-prefix discoverable without morphology; same for p008 نَّ/نْ which does get free matches), p096 اللَّذَانِ and p098 اللَّاتِي (their own example cards use curator-plain orthography — e.g. واللذان, اللاتي — whose shadda-vs-double-lām spelling cannot align to the Uthmani corpus surface even at the loose tier; candidates are discovered but land in `unaligned_candidates_by_particle`).
2. **453 unaligned displayed words** (0.41%) with per-row blockers: 16 cards with unparsable refs, 232 orthography-gap words, 82 ambiguous repeated-word abstentions, 139 words on ref_unparsed cards.
3. **Particle-page word delta:** the universe sees 950 displayed words on particle pages from the committed store vs 984 rendered context spans in the live sweep; the delta is a store-vs-render denominator difference (and one known non-rich defect at `2:91:3` on p048) to reconcile in the render-parity lane.
4. **Selected-word recall:** 4,409 selected words over 7,700 cards — cards whose declared forms differ orthographically from the displayed fragment produce zero selected words; candidates for a form-variant recall pass.
5. **Certification:** none in scope here — every matrix row is `certified: "none"`; all 22 P-02 particles carry `homograph_requires_scholar_two_vote`; clitic and normalized/loose bases carry their respective blockers.
6. **`n993` مَلْجَأ** is the single committed entry with no example cards (pages_with_cards 2,091 of 2,092).

## 6. Reproduction

```
python tools/build_example_ayah_universe.py
python tools/build_particle_occurrence_matrix.py
python tools/validate_example_universe.py
python -m unittest tools.test_example_ayah_universe -q
```

All inputs are committed repo artifacts (entry store export, Tanzil loc-surface index, occurrence-appearance index, membership table, funcword homograph rules); live pages were used only for read-only sample verification, never as a build source.
