# Corpus → Qamus pipeline

The completed sarf/nahw engine is meant to **pull the Qamus cart**: point it at a corpus and get a reviewable
Qamus catalogue + hover worklist — never a live write. This is that pipeline.

## Tools (read-only, offline)

- [`tools/corpus_to_qamus_candidates.py`](../../tools/corpus_to_qamus_candidates.py) — corpus → entry/occurrence
  candidates, classified and deduped through the index.
- [`tools/corpus_to_hover_decisions.py`](../../tools/corpus_to_hover_decisions.py) — corpus → hover-decision
  worklist with a key-safety verdict + the gate each decision must clear.

## Pipeline (9 steps)

1. tokenize the corpus (jsonl `{ref, ar}` rows or `--plain` text);
2. create a source-address node per token (`corpus:<ref>:<idx>`);
3. run the sarf state decision (root/form via [`sarf/procedures/root-decision.md`](../../sarf/procedures/root-decision.md));
4. run the nahw state decision (role/particle via [`nahw/procedures/particle-decision.md`](../../nahw/procedures/particle-decision.md));
5. look up the existing Qamus (`qamus/indexes/existing_qamus_index.json`);
6. classify: `already_in_qamus` / `occurrence_augment` / `new_surface_existing_lemma` / `new_lemma_existing_root`
   / `new_root` / `particle_or_construction` / `review_needed`;
7. author original gloss candidates **only through the certified author + key-aware 2-vote pipeline** (the corpus
   tools never author final glosses themselves);
8. emit candidate entries / occurrence augments / hover decisions as JSONL for human review;
9. **never write the live store** (`live_write: false` on every row).

## Supported corpus modes

current Qamus Qur'an examples · **Nawawī40** (`corpora/nawawi40/nawawi40.matn.jsonl`) · later Ṣaḥīḥayn (plan only —
no hadith text bundled) · arbitrary Arabic text (`--plain`).

## Proof runs

**Fixture / Nawawī40 sample** (first 5 aḥādīth):

| tool | result |
|---|---|
| `corpus_to_qamus_candidates` | 5 rows → tokens: 191 already-in-Qamus · 190 new-root · 55 new-surface-existing-lemma · 36 particle · 14 review → **196 distinct candidates · 0 live writes** |
| `corpus_to_hover_decisions` | **272 distinct keys** → 250 pending-needs-authoring · 14 quarantine-homograph · 8 particle · **0 live writes** |

Committed sample: [`qamus/examples/corpus_to_qamus.sample.jsonl`](../examples/corpus_to_qamus.sample.jsonl).

## Dedupe through the source graph

Candidates are deduped by `norm_strict` key against the index (reuse before minting); intentional homograph
splits are preserved (see [`duplicate-avoidance-report.md`](duplicate-avoidance-report.md)). A token already in
Qamus produces no new entry — at most an occurrence augment attaching the new `corpus:<ref>:<idx>` address to the
entry's usage. Homograph keys are routed to the 2-vote, never auto-glossed.
